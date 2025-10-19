#!/bin/bash
# Quick script to restart API in VM

set -e

echo "Restarting NetEmulator API in VM..."

# Kill old processes
multipass exec netemulator -- sudo pkill -f 'python.*netemulator.control.api' 2>/dev/null || true

sleep 2

# Start new API
multipass exec netemulator -- bash -c "
cd ~/netemulator && \
source venv/bin/activate && \
nohup sudo -E env PATH=\$PATH python3 -m netemulator.control.api > ~/api.log 2>&1 < /dev/null &
"

sleep 4

# Check health
echo "Checking API health..."
multipass exec netemulator -- curl -s http://localhost:8080/api/v1/health | python3 -m json.tool

echo "✓ API restarted"

