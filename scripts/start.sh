#!/bin/sh
# Start HTTP and WebSocket servers on separate ports
# Ensure minified and gzipped assets exist for the frontend
python scripts/build_static.py >/dev/null 2>&1
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
uvicorn app.ws_app:app --host 0.0.0.0 --port 8001
