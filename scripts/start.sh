#!/bin/sh
# Start HTTP and WebSocket servers on separate ports
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
uvicorn app.websocket_app:app --host 0.0.0.0 --port 8001
