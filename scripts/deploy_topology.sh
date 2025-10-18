#!/bin/bash
# Deploy a topology to NetEmulator

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <topology.yaml>"
    exit 1
fi

TOPOLOGY_FILE="$1"
API_URL="${API_URL:-http://localhost:8080}"

if [ ! -f "$TOPOLOGY_FILE" ]; then
    echo "Error: Topology file not found: $TOPOLOGY_FILE"
    exit 1
fi

echo "Deploying topology from: $TOPOLOGY_FILE"
echo "API URL: $API_URL"
echo ""

# Read YAML file
YAML_CONTENT=$(cat "$TOPOLOGY_FILE")

# Deploy topology
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/topologies" \
    -H "Content-Type: text/plain" \
    --data-binary "@$TOPOLOGY_FILE")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool

# Extract topology name
TOPO_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', 'unknown'))")

echo ""
echo "=== Topology Deployed ==="
echo "Name: $TOPO_NAME"
echo ""
echo "Check status:"
echo "  curl $API_URL/api/v1/topologies/$TOPO_NAME"
echo ""
echo "View events:"
echo "  curl $API_URL/api/v1/events?topology_name=$TOPO_NAME"
echo ""

