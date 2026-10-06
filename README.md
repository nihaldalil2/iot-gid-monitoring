# IoT Real-Time Monitoring Pipeline
**Case Study: GID System — Trésorerie Générale du Royaume, Morocco**

## Problem
771,000+ daily log lines unread in real time — structural risk 
for a system managing public finances for 940,000 civil servants.

## Solution
Real-time monitoring platform processing **256,911 real operational 
events** using IoT architectural patterns — same TIG stack used by CERN.

## Architecture
```
Log Files → publisher.py → Mosquitto MQTT → Telegraf → InfluxDB → Grafana
```

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Data Ingestion | Python 3.11 + paho-mqtt |
| Message Broker | Eclipse Mosquitto MQTT |
| Data Agent | Telegraf 1.28 |
| Time-Series DB | InfluxDB 2.7 |
| Visualization | Grafana 10 |
| Deployment | Docker Compose |

## Key Results
- ✅ 256,911 real events processed
- ✅ 3 log formats handled (Apache, Java/Hibernate, GID)
- ✅ Anomaly detection in seconds vs. hours
- ✅ 8/8 functional tests passed
- ✅ GID Anomaly Alert FIRING — severity=critical
- ✅ Same TIG stack used by CERN

## Run It
```bash
git clone https://github.com/nihaldalil/iot-gid-monitoring
cd iot-gid-monitoring
sudo docker-compose up -d
```

## Author
**Nihal DALIL** — Master Business Analytics & Data Science  
Rabat Business School — Mention Très Bien 2026
