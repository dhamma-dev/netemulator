#!/bin/bash
# Get IP addresses of all Mininet nodes

echo "=========================================="
echo "  Mininet Node IP Addresses"
echo "=========================================="
echo ""

if [ ! -d "/var/run/netns" ]; then
    echo "Error: No network namespaces found. Is a topology running?"
    exit 1
fi

# Get all network namespaces
NAMESPACES=$(sudo ip netns list 2>/dev/null | awk '{print $1}')

if [ -z "$NAMESPACES" ]; then
    echo "No network namespaces found."
    echo "Make sure a topology is deployed and running."
    exit 1
fi

echo "Found network namespaces (nodes):"
echo ""

for ns in $NAMESPACES; do
    echo "┌─ Node: $ns"
    
    # Get all IP addresses (excluding loopback)
    IPS=$(sudo ip netns exec $ns ip -4 addr show 2>/dev/null | \
          grep "inet " | grep -v "127.0.0.1" | \
          awk '{print $2}')
    
    if [ -n "$IPS" ]; then
        echo "$IPS" | while read ip; do
            INTERFACE=$(sudo ip netns exec $ns ip -4 addr show | \
                       grep -B 2 "$ip" | head -1 | awk '{print $2}' | tr -d ':')
            echo "│  ├─ Interface: $INTERFACE"
            echo "│  └─ IP: $ip"
        done
    else
        echo "│  └─ No IPv4 addresses found"
    fi
    echo ""
done

echo "=========================================="
echo "  Target Configuration for AppNeta"
echo "=========================================="
echo ""
echo "Use these IPs as monitoring targets:"
echo ""

for ns in $NAMESPACES; do
    IP=$(sudo ip netns exec $ns ip -4 addr show 2>/dev/null | \
         grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d/ -f1)
    if [ -n "$IP" ]; then
        echo "  $ns → $IP"
    fi
done

echo ""
echo "=========================================="
echo ""
echo "Note: You'll need WireGuard VPN configured to reach these IPs from your Mac"
echo "See APPNETA_INTEGRATION.md for setup instructions"

