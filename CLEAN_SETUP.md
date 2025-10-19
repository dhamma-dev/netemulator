# NetEmulator Clean Setup Guide

This guide provides a reproducible, clean setup from scratch.

## 🎯 Overview

This replaces all the manual fixes we made. Use this for:
- Fresh installations
- Resetting to a known-good state
- Documenting what actually works

## 📋 Prerequisites

- **Multipass VM** with Ubuntu 22.04 or 24.04
- **4 CPU cores, 8GB RAM minimum**
- **Mac with WireGuard** for external monitoring

## 🚀 Complete Setup (30 minutes)

### Step 1: Create Fresh VM

```bash
# On your Mac:
multipass delete netemulator --purge  # If starting over
multipass launch --name netemulator --cpus 4 --memory 8G --disk 50G 22.04
multipass shell netemulator
```

### Step 2: Clone and Install Dependencies

```bash
# In the VM:
git clone https://github.com/YOUR_USERNAME/netemulator.git
cd netemulator
sudo ./scripts/install_dependencies.sh
```

**Wait ~10 minutes for installation to complete**

### Step 3: Complete System Setup

```bash
# In the VM (still in netemulator directory):
sudo ./scripts/setup_complete_system.sh
```

This script:
- ✅ Creates venv with system-site-packages
- ✅ Installs Python dependencies  
- ✅ Configures IP forwarding
- ✅ Creates systemd service for API
- ✅ Starts API as root
- ✅ Sets up WireGuard server
- ✅ Prints configuration info

**Save the WireGuard server public key** that's printed!

### Step 4: Deploy a Topology

```bash
# In the VM:
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: text/plain" \
  --data-binary @examples/dual_isp_topology.yaml | python3 -m json.tool
```

### Step 5: Connect Mininet to Host

```bash
# In the VM:
sudo ./scripts/connect_mininet_to_host.sh
```

This:
- ✅ Finds the OVS bridge
- ✅ Adds IP 10.0.0.254 to bridge
- ✅ Adds route to 10.0.0.0/8
- ✅ Tests connectivity

### Step 6: Onboard Your Monitoring Point

```bash
# In the VM:
sudo ./scripts/onboard_mp.sh appneta-mac-01
```

This will:
- ✅ Generate WireGuard keys
- ✅ Add peer to server
- ✅ Set up forwarding rules
- ✅ Print client configuration

**Copy the client config it prints!**

### Step 7: Connect from Your Mac

```bash
# On your Mac:
# Install WireGuard (if not already)
brew install wireguard-tools

# Create config file
nano ~/appneta-mac-01.conf
# Paste the config from step 6

# Connect
sudo wg-quick up ~/appneta-mac-01.conf

# Test
ping 10.100.0.1  # WireGuard server
ping 10.0.0.1    # Mininet network
```

### Step 8: Configure AppNeta Agent

Point your AppNeta agent to:
- **Primary target**: `10.0.0.1` (branch router)
- **Optional**: `10.0.0.2`, `10.0.0.3`, `10.0.0.4`, `10.0.0.5`

## ✅ Verification Checklist

Run these to verify everything works:

```bash
# In the VM:
✓ systemctl status netemulator-api          # Should be active (running)
✓ curl http://localhost:8080/api/v1/health  # Should return healthy
✓ ip addr show wg0                          # Should show 10.100.0.1/24
✓ ping -c 2 10.0.0.1                        # Should succeed
✓ wg show                                    # Should show peer

# From your Mac:
✓ ping 10.100.0.1                           # Should succeed
✓ ping 10.0.0.1                             # Should succeed  
✓ traceroute 10.0.0.1                       # Should show 2 hops
```

## 🔧 Service Management

```bash
# Check API status
sudo systemctl status netemulator-api

# View API logs
sudo journalctl -u netemulator-api -f

# Restart API
sudo systemctl restart netemulator-api

# Stop API
sudo systemctl stop netemulator-api

# Start WireGuard
sudo wg-quick up wg0

# Stop WireGuard  
sudo wg-quick down wg0
```

## 🧹 Clean State Commands

### Reset Everything

```bash
# In the VM:
# Stop services
sudo systemctl stop netemulator-api
sudo wg-quick down wg0 2>/dev/null || true

# Clean Mininet
sudo mn -c

# Remove topologies
curl -X DELETE http://localhost:8080/api/v1/topologies/dual_isp_branch_to_cdn
curl -X DELETE http://localhost:8080/api/v1/topologies/simple_3node

# Restart clean
sudo systemctl start netemulator-api
```

### Start Fresh (Nuclear Option)

```bash
# On your Mac:
multipass delete netemulator --purge
# Then follow setup from Step 1
```

## 📊 Target IPs Reference

### Dual-ISP Topology (most interesting):
- `10.0.0.1` - br1-r1 (branch router)
- `10.0.0.2` - ispA (primary ISP)
- `10.0.0.3` - ispB (backup ISP, has 0.3% loss)
- `10.0.0.4` - transit1 (transit provider)
- `10.0.0.5` - cdn-pop1 (CDN endpoint)

### Simple 3-Node:
- `10.0.0.1` - h1 (host)
- `10.0.0.2` - r1 (router)
- `10.0.0.3` - h2 (host with DNS)

## 🐛 Troubleshooting

### API won't start
```bash
sudo journalctl -u netemulator-api -n 50
# Check for import errors or permission issues
```

### Can't reach Mininet from VM
```bash
# Re-run bridge connection
sudo ./scripts/connect_mininet_to_host.sh
```

### Can't reach Mininet from Mac
```bash
# In VM, check forwarding rules:
sudo iptables -L -n -v | grep wg0
sudo iptables -t nat -L -n -v

# Re-run onboarding to fix:
sudo ./scripts/onboard_mp.sh appneta-mac-01
```

### WireGuard not working
```bash
# In VM:
sudo wg-quick down wg0
sudo wg-quick up wg0
sudo wg show

# On Mac:
sudo wg-quick down ~/appneta-mac-01.conf
sudo wg-quick up ~/appneta-mac-01.conf
```

## 📝 What Changed from Manual Setup

The clean setup automates all these manual fixes we made:

1. ✅ **venv with --system-site-packages** - Required for Mininet access
2. ✅ **API runs as root via systemd** - Required for network namespaces
3. ✅ **Bridge gets host IP automatically** - Connects Mininet to host
4. ✅ **WireGuard iptables rules** - Forwards traffic to Mininet
5. ✅ **Proper startup order** - API → Deploy → Connect → Onboard

## 🎉 Success Criteria

You know it's working when:
1. AppNeta agent shows `10.0.0.1` as reachable
2. RTT is ~10-30ms (depending on impairments)
3. Packet loss shows up (0.3% on ISP B path)
4. Scheduled scenarios appear in NetEmulator events
5. AppNeta measurements correlate with NetEmulator impairments

---

**This is your reproducible baseline!** Bookmark this page.

