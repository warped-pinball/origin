#!/bin/bash
# run the build static script
python scripts/build_static.py

# start the docker container
docker compose down
docker compose -f docker-compose.local.yml up --build --remove-orphans --watch