#!/bin/bash
# Install NetEmulator dependencies on Ubuntu/Debian

set -e

echo "=== Installing NetEmulator Dependencies ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update package list
echo "Updating package list..."
apt-get update

# Install system dependencies
echo "Installing system packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    build-essential \
    openvswitch-switch \
    wireguard \
    wireguard-tools \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    ethtool

# Install Mininet
if ! command -v mn &> /dev/null; then
    echo "Installing Mininet..."
    apt-get install -y mininet
else
    echo "Mininet already installed"
fi

# Install FRRouting
if ! command -v vtysh &> /dev/null; then
    echo "Installing FRRouting..."
    
    # Add FRR GPG key
    curl -s https://deb.frrouting.org/frr/keys.asc | apt-key add -
    
    # Add FRR repository
    FRRVER="frr-stable"
    echo "deb https://deb.frrouting.org/frr $(lsb_release -sc) $FRRVER" | tee /etc/apt/sources.list.d/frr.list
    
    # Update and install
    apt-get update
    apt-get install -y frr frr-pythontools
    
    # Enable daemons
    sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons
    sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons
    
    systemctl restart frr
else
    echo "FRRouting already installed"
fi

# Configure system settings
echo "Configuring system settings..."

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Make permanent
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.d/99-netemulator.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.d/99-netemulator.conf

# Increase network buffers
echo "net.core.rmem_max=134217728" >> /etc/sysctl.d/99-netemulator.conf
echo "net.core.wmem_max=134217728" >> /etc/sysctl.d/99-netemulator.conf

# Apply settings
sysctl -p /etc/sysctl.d/99-netemulator.conf

# Create Python virtual environment
echo "Setting up Python environment..."
cd "$(dirname "$0")/.."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To start NetEmulator:"
echo "  python3 -m netemulator.control.api"
echo ""

