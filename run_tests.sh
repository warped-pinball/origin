#!/bin/bash
set -e

echo "Building and starting services..."
docker-compose up -d --build

echo "Waiting for services to be ready..."
# Simple wait, the test itself has retry logic but this helps
sleep 10

echo "Running tests..."
# We run pytest inside a temporary container or locally?
# Since we need to access localhost:8000 and localhost:5000, running locally is fine
# IF the user has python installed.
# But for CI, we might want to run it in a container.
# Let's run it locally for now as per the plan, assuming python env is set up or we use a test container.
# Actually, better to run it in a container to ensure dependencies are there.
# But the plan said "run_tests.sh" would run pytest.
# Let's assume we run pytest locally for simplicity as the user asked for a script "we can also use locally".

# Install test dependencies if not present (optional, might be slow)
# pip install pytest httpx asyncpg

pytest tests/test_integration.py

echo "Tearing down services..."
docker-compose down
