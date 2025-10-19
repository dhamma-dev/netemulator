#!/bin/bash
# Explore and interact with a deployed topology

set -e

TOPOLOGY_NAME="${1:-simple_3node}"
API_URL="${API_URL:-http://localhost:8080}"

echo "=========================================="
echo "  NetEmulator Topology Explorer"
echo "=========================================="
echo ""

# Get topology status
echo "📊 Topology Status:"
echo "-------------------"
curl -s "$API_URL/api/v1/topologies/$TOPOLOGY_NAME" | python3 -m json.tool
echo ""
echo ""

# Get recent events
echo "📝 Recent Events:"
echo "-----------------"
curl -s "$API_URL/api/v1/events?topology_name=$TOPOLOGY_NAME&limit=10" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
events = data.get('events', [])
for event in events[-10:]:
    print(f\"{event['timestamp'][:19]} - {event['event_type']:30s} - {event['message']}\")
"
echo ""
echo ""

# Test network connectivity
echo "🔬 Testing Network (requires sudo):"
echo "-----------------------------------"
echo "Available Mininet nodes:"
sudo mn -c 2>/dev/null || true
echo ""
echo "To interact with the network, use:"
echo "  sudo mn --test pingall    # Test connectivity between all nodes"
echo ""
echo "Or get a Mininet CLI:"
echo "  sudo mn"
echo "  Then try: h1 ping -c 3 h2"
echo ""
echo ""

# Show how to test with curl
echo "🌐 Testing Services:"
echo "-------------------"
echo "The network has these services running:"
echo "  - h1: Basic host"
echo "  - r1: Router with OSPF"
echo "  - h2: Host with DNS service"
echo ""
echo "To test from inside the network:"
echo "  1. Get network namespace: sudo ip netns list"
echo "  2. Run commands in namespace: sudo ip netns exec <name> ping <ip>"
echo ""

echo "=========================================="
echo "Next steps:"
echo "  - Deploy more complex topology: examples/dual_isp_topology.yaml"
echo "  - View metrics: curl $API_URL/api/v1/metrics"
echo "  - Check logs: tail -f logs/api.log"
echo "=========================================="

