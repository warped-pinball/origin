#!/bin/bash
set -e

# Install dependencies if not already installed (useful for local run outside docker)
# pip install -r requirements.txt

# Run pytest (uses the default SQLite database unless DATABASE_URL is provided)

echo "Running tests..."
python -m playwright install --with-deps
export PYTHONPATH=$PYTHONPATH:.
pytest tests/ -v
