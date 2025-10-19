#!/bin/bash
# Connect Mininet network to host system
# Run this AFTER deploying a topology

set -e

echo "================================================"
echo "  Connecting Mininet Network to Host"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Find the OVS bridge (first one that's not ovs-system)
BRIDGE=$(ovs-vsctl list-br | grep -v "ovs-system" | head -1)

if [ -z "$BRIDGE" ]; then
    echo "Error: No OVS bridge found. Is a topology deployed?"
    echo "Deploy a topology first:"
    echo "  curl -X POST http://localhost:8080/api/v1/topologies -H 'Content-Type: text/plain' --data-binary @examples/dual_isp_topology.yaml"
    exit 1
fi

echo "Found bridge: $BRIDGE"
echo ""

# Add IP to bridge if not already present
if ! ip addr show "$BRIDGE" | grep -q "10.0.0.254"; then
    echo "Adding IP 10.0.0.254/8 to $BRIDGE..."
    ip link set "$BRIDGE" up
    ip addr add 10.0.0.254/8 dev "$BRIDGE"
else
    echo "Bridge already has IP"
fi

# Add route if not present
if ! ip route show | grep -q "10.0.0.0/8 dev $BRIDGE"; then
    echo "Adding route to 10.0.0.0/8 via $BRIDGE..."
    ip route add 10.0.0.0/8 dev "$BRIDGE" 2>/dev/null || true
fi

# Test connectivity
echo ""
echo "Testing connectivity to Mininet network..."
if ping -c 2 -W 2 10.0.0.1 > /dev/null 2>&1; then
    echo "✓ Can reach 10.0.0.1"
else
    echo "✗ Cannot reach 10.0.0.1 (this might be normal if no node at that IP)"
fi

echo ""
echo "================================================"
echo "  Mininet Network Connected!"
echo "================================================"
echo ""
echo "Bridge: $BRIDGE"
echo "Host IP: 10.0.0.254/8"
echo ""
echo "You can now ping Mininet nodes from this host."
echo "Example: ping 10.0.0.1"
echo ""
echo "To connect from external monitoring points:"
echo "  1. Start WireGuard: wg-quick up wg0"
echo "  2. Add iptables rules: sudo $0 --setup-forwarding"
echo ""

