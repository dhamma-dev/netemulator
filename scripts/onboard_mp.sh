#!/bin/bash
# Onboard an AppNeta monitoring point via WireGuard
# Usage: sudo ./onboard_mp.sh <mp_name> [client_number]

set -e

MP_NAME="${1:-appneta-mp-01}"
CLIENT_NUM="${2:-2}"

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "================================================"
echo "  AppNeta Monitoring Point Onboarding"
echo "================================================"
echo ""
echo "MP Name: $MP_NAME"
echo "Client VPN IP: 10.100.0.$CLIENT_NUM"
echo ""

# Check prerequisites
if [ ! -f /etc/wireguard/keys/server_public.key ]; then
    echo "Error: WireGuard server not set up. Run setup_complete_system.sh first"
    exit 1
fi

# Start WireGuard if not already running
if ! ip link show wg0 > /dev/null 2>&1; then
    echo "Starting WireGuard..."
    wg-quick up wg0
fi

# Generate client keys
CLIENT_DIR="/tmp/wg_${MP_NAME}"
mkdir -p "$CLIENT_DIR"

echo "Generating keys for $MP_NAME..."
wg genkey | tee "$CLIENT_DIR/private.key" | wg pubkey > "$CLIENT_DIR/public.key"

CLIENT_PRIVATE=$(cat "$CLIENT_DIR/private.key")
CLIENT_PUBLIC=$(cat "$CLIENT_DIR/public.key")
SERVER_PUBLIC=$(cat /etc/wireguard/keys/server_public.key)
SERVER_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')

# Add peer to server
echo "Adding peer to WireGuard server..."
wg set wg0 peer "$CLIENT_PUBLIC" allowed-ips "10.100.0.$CLIENT_NUM/32"

# Set up forwarding between WireGuard and Mininet
BRIDGE=$(ovs-vsctl list-br | grep -v "ovs-system" | head -1)

if [ -n "$BRIDGE" ]; then
    echo "Setting up forwarding rules..."
    # Allow forwarding from WireGuard to Mininet
    iptables -A FORWARD -i wg0 -o "$BRIDGE" -j ACCEPT 2>/dev/null || true
    iptables -A FORWARD -i "$BRIDGE" -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    
    # NAT for return traffic
    iptables -t nat -A POSTROUTING -s 10.100.0.0/24 -d 10.0.0.0/8 -j MASQUERADE 2>/dev/null || true
fi

# Create client config
CONFIG_FILE="$CLIENT_DIR/${MP_NAME}.conf"
cat > "$CONFIG_FILE" << EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE
Address = 10.100.0.$CLIENT_NUM/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC
Endpoint = $SERVER_IP:51820
AllowedIPs = 10.100.0.0/24, 10.0.0.0/8
PersistentKeepalive = 25
EOF

echo ""
echo "================================================"
echo "  Monitoring Point Onboarded Successfully!"
echo "================================================"
echo ""
echo "Client configuration saved to: $CONFIG_FILE"
echo ""
echo "--- Client Config (copy to Mac) ---"
cat "$CONFIG_FILE"
echo "--- End Config ---"
echo ""
echo "================================================"
echo "  Instructions for Mac:"
echo "================================================"
echo ""
echo "1. Install WireGuard:"
echo "   brew install wireguard-tools"
echo ""
echo "2. Copy the config above to: ~/${MP_NAME}.conf"
echo ""
echo "3. Connect:"
echo "   sudo wg-quick up ~/${MP_NAME}.conf"
echo ""
echo "4. Test connectivity:"
echo "   ping 10.100.0.1  # WireGuard server"
echo "   ping 10.0.0.1    # First Mininet node"
echo ""
echo "5. Configure AppNeta to monitor:"
echo "   Target IPs: 10.0.0.1, 10.0.0.2, 10.0.0.3, etc."
echo ""
echo "6. Disconnect when done:"
echo "   sudo wg-quick down ~/${MP_NAME}.conf"
echo ""
echo "================================================"

