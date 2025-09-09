#!/bin/sh
# Start the HTTP server
# Ensure minified and gzipped assets exist for the frontend
python scripts/build_static.py >/dev/null 2>&1

# Run the API server in the foreground so the container stays alive
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
