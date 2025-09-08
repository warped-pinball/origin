#!/bin/sh
# Start HTTP server and MQTT message handler
# Ensure minified and gzipped assets exist for the frontend
python scripts/build_static.py >/dev/null 2>&1
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
python app/mqtt_app.py
