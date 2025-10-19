#!/bin/bash
# Setup WireGuard for external monitoring point access

set -e

MP_NAME="${1:-mac-mp-01}"
TOPOLOGY_NAME="${2:-dual_isp_branch_to_cdn}"
SERVER_PORT="${3:-51820}"
VPN_SUBNET="10.100.0.0/24"

echo "=========================================="
echo "  WireGuard MP Setup"
echo "=========================================="
echo ""
echo "MP Name: $MP_NAME"
echo "Topology: $TOPOLOGY_NAME"
echo "VPN Subnet: $VPN_SUBNET"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Generate server keys if they don't exist
SERVER_KEY_DIR="/etc/wireguard/keys"
mkdir -p "$SERVER_KEY_DIR"

if [ ! -f "$SERVER_KEY_DIR/server_private.key" ]; then
    echo "Generating server keys..."
    wg genkey | tee "$SERVER_KEY_DIR/server_private.key" | wg pubkey > "$SERVER_KEY_DIR/server_public.key"
fi

SERVER_PRIVATE=$(cat "$SERVER_KEY_DIR/server_private.key")
SERVER_PUBLIC=$(cat "$SERVER_KEY_DIR/server_public.key")

# Generate client keys
CLIENT_KEY_DIR="/tmp/wg_${MP_NAME}"
mkdir -p "$CLIENT_KEY_DIR"

echo "Generating client keys for $MP_NAME..."
wg genkey | tee "$CLIENT_KEY_DIR/private.key" | wg pubkey > "$CLIENT_KEY_DIR/public.key"

CLIENT_PRIVATE=$(cat "$CLIENT_KEY_DIR/private.key")
CLIENT_PUBLIC=$(cat "$CLIENT_KEY_DIR/public.key")

# Get server's public IP (or use the Multipass IP)
SERVER_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
echo "Server IP: $SERVER_IP"

# Server VPN IP
SERVER_VPN_IP="10.100.0.1"
CLIENT_VPN_IP="10.100.0.2"

# Create server config
echo "Creating WireGuard server config..."
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE
Address = $SERVER_VPN_IP/24
ListenPort = $SERVER_PORT
SaveConfig = false

# Enable IP forwarding
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

PostDown = iptables -D FORWARD -i wg0 -j ACCEPT 2>/dev/null || true
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT 2>/dev/null || true
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true

# Client: $MP_NAME
[Peer]
PublicKey = $CLIENT_PUBLIC
AllowedIPs = $CLIENT_VPN_IP/32
EOF

chmod 600 /etc/wireguard/wg0.conf

# Start WireGuard
echo "Starting WireGuard..."
wg-quick down wg0 2>/dev/null || true
wg-quick up wg0

# Show status
echo ""
echo "WireGuard server is running!"
wg show

echo ""
echo "=========================================="
echo "  Client Configuration for $MP_NAME"
echo "=========================================="
echo ""

# Create client config
CLIENT_CONFIG_FILE="$CLIENT_KEY_DIR/${MP_NAME}.conf"
cat > "$CLIENT_CONFIG_FILE" << EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE
Address = $CLIENT_VPN_IP/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC
Endpoint = $SERVER_IP:$SERVER_PORT
AllowedIPs = 10.100.0.0/24, 10.0.0.0/8
PersistentKeepalive = 25
EOF

echo "Client config saved to: $CLIENT_CONFIG_FILE"
echo ""
cat "$CLIENT_CONFIG_FILE"
echo ""

echo "=========================================="
echo "  Target IPs for AppNeta Monitoring"
echo "=========================================="
echo ""
echo "After connecting via WireGuard, you can target:"
echo ""

# Get Mininet host IPs
echo "Mininet Network (10.0.0.0/8):"
echo "  - Check with: sudo mn --version"
echo "  - Typical IPs: 10.0.0.1, 10.0.0.2, 10.0.0.3, etc."
echo ""
echo "WireGuard Server:"
echo "  - $SERVER_VPN_IP (this VM)"
echo ""

echo "=========================================="
echo "  Next Steps on Your Mac"
echo "=========================================="
echo ""
echo "1. Install WireGuard:"
echo "   brew install wireguard-tools"
echo "   Or download WireGuard app from App Store"
echo ""
echo "2. Copy the config above to your Mac:"
echo "   scp $CLIENT_CONFIG_FILE <your-mac>:~/"
echo ""
echo "3. Connect:"
echo "   sudo wg-quick up ~/${MP_NAME}.conf"
echo ""
echo "4. Test connectivity:"
echo "   ping $SERVER_VPN_IP"
echo ""
echo "5. Configure AppNeta agent to monitor:"
echo "   - Server: $SERVER_VPN_IP"
echo "   - Mininet hosts: 10.0.0.1, 10.0.0.2, etc."
echo ""
echo "=========================================="

