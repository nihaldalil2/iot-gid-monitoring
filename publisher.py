import json
import time
import uuid
import os
import re
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
PORT = 1883
TOPIC = "jenkins/builds/events"

LOG_FILES = [
    "/logs/access_log.log",
    "/logs/server_log.log",
    "/logs/gid_log.log"
]

event_counter = [0]

def get_event_time():
    event_counter[0] += 1
    base = datetime(2026, 5, 29, 21, 30, 0, tzinfo=timezone.utc)
    ts = base.timestamp() + (event_counter[0] * 0.5)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def detect_anomaly(event):
    msg = event.get("message", "").lower()
    level = event.get("level", "INFO")
    http_status = event.get("http_status", 0)
    if level in ["ERROR", "FATAL"]:
        return True, "Error detected"
    if level == "WARN":
        return True, "Warning detected"
    if http_status >= 500:
        return True, "Server error HTTP 5xx"
    if http_status >= 400:
        return True, "Client error HTTP 4xx"
    if "exception" in msg or "erreur" in msg:
        return True, "Exception detected"
    if "timeout" in msg:
        return True, "Timeout detected"
    if "failed" in msg or "failure" in msg:
        return True, "Failure detected"
    return False, "Normal"

def parse_access_log(line):
    match = re.match(r'(\S+) - - \[([^\]]+)\] "(\S+) (\S+) HTTP/[^"]+"\s+(\d+)\s+(\d+)', line)
    if match:
        ip, date, method, path, status, size = match.groups()
        status = int(status)
        level = "INFO"
        if status >= 500: level = "ERROR"
        elif status >= 400: level = "WARN"
        event = {
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "source": "App1.Web.Access",
            "event_type": "http_request",
            "raw_log": line[:200],
            "level": level,
            "message": f"HTTP {method} {path} status={status}",
            "mqtt_topic": TOPIC,
            "http_status": status,
            "endpoint": path,
            "event_time": get_event_time()
        }
        is_anomaly, reason = detect_anomaly(event)
        event["is_anomaly"] = is_anomaly
        event["anomaly_reason"] = reason
        return event
    return None

def parse_server_log(line):
    parts = line.split("|")
    if len(parts) >= 8:
        level = parts[6].strip()
        if level not in ["INFO","WARN","ERROR","DEBUG","FATAL"]:
            level = "INFO"
        message = parts[7].strip() if len(parts) > 7 else ""
        if not message or len(message) < 3:
            return None
        event = {
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "source": "App1.Web.Server",
            "event_type": "server_log",
            "raw_log": line[:200],
            "level": level,
            "message": message[:200],
            "mqtt_topic": TOPIC,
            "event_time": get_event_time()
        }
        is_anomaly, reason = detect_anomaly(event)
        event["is_anomaly"] = is_anomaly
        event["anomaly_reason"] = reason
        return event
    return None

def parse_gid_log(line):
    parts = line.split("|")
    if len(parts) >= 8:
        level = parts[6].strip()
        if level not in ["INFO","WARN","ERROR","DEBUG","FATAL"]:
            level = "INFO"
        message = parts[7].strip() if len(parts) > 7 else ""
        endpoint = parts[4].strip() if len(parts) > 4 else ""
        user = parts[3].split(";")[0].strip() if len(parts) > 3 else ""
        if not message or len(message) < 3:
            return None
        event = {
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "source": "App1.Web.GID",
            "event_type": "application_log",
            "raw_log": line[:200],
            "level": level,
            "message": message[:200],
            "endpoint": endpoint,
            "user": user,
            "mqtt_topic": TOPIC,
            "event_time": get_event_time()
        }
        is_anomaly, reason = detect_anomaly(event)
        event["is_anomaly"] = is_anomaly
        event["anomaly_reason"] = reason
        return event
    return None

def parse_log_line(line, log_file):
    line = line.strip().replace("\r", "")
    if not line or len(line) < 5:
        return None
    if "access_log" in log_file:
        return parse_access_log(line)
    elif "server_log" in log_file:
        return parse_server_log(line)
    elif "gid_log" in log_file:
        return parse_gid_log(line)
    return None

def connect_mqtt():
    client = mqtt.Client()
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            print("Connected to MQTT broker")
            return client
        except Exception as e:
            print(f"MQTT failed: {e} retrying...")
            time.sleep(5)

print("Waiting 15 seconds for Mosquitto to start...")
time.sleep(15)
client = connect_mqtt()
print("Publisher started - reading 3 real TGR log files")

for log_file in LOG_FILES:
    if os.path.exists(log_file):
        print(f"Reading: {log_file}")
        count = 0
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                event = parse_log_line(line, log_file)
                if event:
                    client.publish(TOPIC, json.dumps(event))
                    count += 1
                    if count % 5000 == 0:
                        print(f"Published {count} events from {log_file}")
                    time.sleep(0.001)
        print(f"DONE {log_file}: {count} events published")
    else:
        print(f"NOT FOUND: {log_file}")

print("All logs published to MQTT")
print("Watching for new lines...")

positions = {f: os.path.getsize(f) if os.path.exists(f) else 0 for f in LOG_FILES}

while True:
    try:
        for log_file in LOG_FILES:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(positions[log_file])
                    new_lines = f.readlines()
                    positions[log_file] = f.tell()
                for line in new_lines:
                    event = parse_log_line(line, log_file)
                    if event:
                        client.publish(TOPIC, json.dumps(event))
    except Exception as e:
        print(f"Error: {e}")
        client = connect_mqtt()
    time.sleep(5)
