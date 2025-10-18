#!/bin/bash
# Stop NetEmulator services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Stopping NetEmulator services..."

# Stop API server
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if ps -p "$API_PID" > /dev/null 2>&1; then
        echo "Stopping API server (PID: $API_PID)..."
        kill "$API_PID"
        rm logs/api.pid
    else
        echo "API server not running"
        rm logs/api.pid
    fi
else
    echo "No PID file found for API server"
fi

# Clean up any lingering Mininet processes
echo "Cleaning up Mininet..."
sudo mn -c > /dev/null 2>&1 || true

echo "Services stopped."

