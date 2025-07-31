#!/bin/sh
# Start HTTP and WebSocket servers on separate ports
# Ensure a minified JS bundle exists for the frontend
python scripts/minify_js.py app/static/app.js >/dev/null 2>&1
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
uvicorn app.websocket_app:app --host 0.0.0.0 --port 8001
