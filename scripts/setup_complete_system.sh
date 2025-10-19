#!/bin/bash
# Complete NetEmulator setup with AppNeta MP integration
# Run this script after fresh install to get a working system

set -e

echo "================================================"
echo "  NetEmulator Complete System Setup"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

WORK_DIR="/home/ubuntu/netemulator"
cd "$WORK_DIR" || exit 1

echo "Step 1: Setting up Python virtual environment with system packages..."
# Remove old venv if exists
rm -rf venv

# Create venv WITH system-site-packages (required for Mininet)
python3 -m venv venv --system-site-packages

# Activate and install packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 2: Configuring system networking..."
# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Make it permanent
grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf || \
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

echo ""
echo "Step 3: Creating systemd service for NetEmulator API..."
cat > /etc/systemd/system/netemulator-api.service << 'EOF'
[Unit]
Description=NetEmulator API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/netemulator
Environment="PATH=/home/ubuntu/netemulator/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/ubuntu/netemulator/venv/bin/python3 -m netemulator.control.api
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/ubuntu/netemulator/logs/api.log
StandardError=append:/home/ubuntu/netemulator/logs/api.log

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory
mkdir -p logs

# Reload systemd
systemctl daemon-reload

echo ""
echo "Step 4: Starting NetEmulator API..."
systemctl enable netemulator-api
systemctl restart netemulator-api

# Wait for API to start
sleep 5

# Check if running
if systemctl is-active --quiet netemulator-api; then
    echo "✓ API is running"
else
    echo "✗ API failed to start. Check: journalctl -u netemulator-api"
    exit 1
fi

echo ""
echo "Step 5: Setting up WireGuard for AppNeta MP access..."
# WireGuard keys
mkdir -p /etc/wireguard/keys
if [ ! -f /etc/wireguard/keys/server_private.key ]; then
    wg genkey | tee /etc/wireguard/keys/server_private.key | wg pubkey > /etc/wireguard/keys/server_public.key
fi

SERVER_PRIVATE=$(cat /etc/wireguard/keys/server_private.key)
SERVER_PUBLIC=$(cat /etc/wireguard/keys/server_public.key)

# Get server IP
SERVER_IP=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')

# Create basic WireGuard config (clients will be added later)
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE
Address = 10.100.0.1/24
ListenPort = 51820
SaveConfig = false

PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

PostDown = iptables -D FORWARD -i wg0 -j ACCEPT 2>/dev/null || true
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT 2>/dev/null || true
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true
EOF

chmod 600 /etc/wireguard/wg0.conf

echo ""
echo "================================================"
echo "  Setup Complete!"
echo "================================================"
echo ""
echo "Server Public Key: $SERVER_PUBLIC"
echo "Server IP: $SERVER_IP"
echo ""
echo "Next Steps:"
echo ""
echo "1. Deploy a topology:"
echo "   curl -X POST http://localhost:8080/api/v1/topologies \\"
echo "     -H 'Content-Type: text/plain' \\"
echo "     --data-binary @examples/dual_isp_topology.yaml"
echo ""
echo "2. Connect Mininet network to host (run after topology is deployed):"
echo "   sudo $WORK_DIR/scripts/connect_mininet_to_host.sh"
echo ""
echo "3. Onboard AppNeta monitoring point:"
echo "   sudo $WORK_DIR/scripts/onboard_mp.sh <mp_name>"
echo ""
echo "4. Check status:"
echo "   systemctl status netemulator-api"
echo "   curl http://localhost:8080/api/v1/health"
echo ""
echo "================================================"

