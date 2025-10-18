#!/bin/bash
# Start NetEmulator services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Run install_dependencies.sh first."
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "Starting NetEmulator services..."

# Start API server
echo "Starting API server on port 8080..."
python3 -m netemulator.control.api > logs/api.log 2>&1 &
API_PID=$!
echo "API server PID: $API_PID"

# Wait a bit for API to start
sleep 2

echo ""
echo "=== NetEmulator Services Started ==="
echo ""
echo "API Server: http://localhost:8080"
echo "  - Health check: http://localhost:8080/api/v1/health"
echo "  - Metrics: http://localhost:8080/api/v1/metrics"
echo ""
echo "Logs:"
echo "  - API: logs/api.log"
echo ""
echo "To stop services:"
echo "  kill $API_PID"
echo ""
echo "Or use: ./scripts/stop_services.sh"
echo ""

# Save PIDs
echo "$API_PID" > logs/api.pid

echo "Services are running. Press Ctrl+C to view logs or use 'tail -f logs/api.log'"

