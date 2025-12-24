#!/usr/bin/env bash
set -euo pipefail

# A helper to start/stop local docker-compose services safely.
# Usage: ./scripts/run_local.sh [start|stop|restart|clean]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

ACTION="${1:-}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/run_local.sh [start|stop|restart|clean]

start    Stop any stale containers and start the stack in detached mode.
stop     Stop and remove containers (keeps named volumes).
restart  Restart the stack by invoking stop then start.
clean    Remove containers, orphans, and named volumes for a fresh start.
USAGE
}

if [[ -z "$ACTION" ]]; then
  usage
  exit 1
fi

# Ensure the Compose project name is set so we don't collide with prior runs.
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-the-box-dev}"

case "$ACTION" in
  start)
    echo "Stopping any existing stack (keeping volumes) to avoid stale ContainerConfig..."
    docker-compose down --remove-orphans
    echo "Starting stack..."
    docker-compose up --build
    ;;
  stop)
    echo "Stopping stack and removing containers (keeping volumes)..."
    docker-compose down --remove-orphans
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  clean)
    echo "Removing containers, orphans, and named volumes for a clean slate..."
    docker-compose down --volumes --remove-orphans
    ;;
  *)
    usage
    exit 1
    ;;
 esac
