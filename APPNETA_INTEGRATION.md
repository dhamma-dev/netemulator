# AppNeta Monitoring Point Integration Guide

Connect your AppNeta monitoring agent to NetEmulator via WireGuard.

## 🎯 Overview

This guide shows you how to:
1. Set up WireGuard VPN between your Mac and the NetEmulator VM
2. Get target IPs from the emulated network
3. Configure AppNeta agent to monitor those targets
4. See real network metrics affected by impairments

## 📋 Prerequisites

- NetEmulator running in Multipass VM
- AppNeta agent installed on your Mac
- WireGuard tools on your Mac: `brew install wireguard-tools`

## 🚀 Step-by-Step Setup

### Step 1: Deploy a Topology (In the VM)

First, make sure you have a topology running:

```bash
# In the VM:
cd ~/netemulator

# Deploy the dual-ISP topology (most interesting)
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: text/plain" \
  --data-binary @examples/dual_isp_topology.yaml | python3 -m json.tool

# Verify it's running
curl http://localhost:8080/api/v1/topologies | python3 -m json.tool
```

### Step 2: Set Up WireGuard Server (In the VM)

```bash
# In the VM, pull latest scripts:
cd ~/netemulator
git pull

# Run the WireGuard setup script
sudo ./scripts/setup_wireguard_mp.sh mac-mp-01 dual_isp_branch_to_cdn

# This will:
# - Generate server and client keys
# - Configure WireGuard interface wg0
# - Start the VPN server
# - Print client configuration
```

**Save the client configuration** that gets printed! It looks like:

```ini
[Interface]
PrivateKey = <YOUR_PRIVATE_KEY>
Address = 10.100.0.2/24
DNS = 8.8.8.8

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
Endpoint = 192.168.64.3:51820
AllowedIPs = 10.100.0.0/24, 10.0.0.0/8
PersistentKeepalive = 25
```

### Step 3: Get Target IPs from Mininet (In the VM)

Now we need to find out what IPs are assigned to the emulated hosts:

```bash
# In the VM, check what network namespaces exist:
sudo ip netns list

# You should see: br1-sw1, br1-r1, ispA, ispB, transit1, cdn-pop1

# Get IP addresses for each:
for ns in $(sudo ip netns list | awk '{print $1}'); do
    echo "=== $ns ==="
    sudo ip netns exec $ns ip addr show | grep "inet " | grep -v "127.0.0.1"
done
```

Example output:
```
=== cdn-pop1 ===
    inet 10.0.0.6/8
=== transit1 ===
    inet 10.0.0.5/8
=== ispB ===
    inet 10.0.0.4/8
=== ispA ===
    inet 10.0.0.3/8
=== br1-r1 ===
    inet 10.0.0.2/8
=== br1-sw1 ===
    inet 10.0.0.1/8
```

**Save these IPs** - these are your monitoring targets!

### Step 4: Connect from Your Mac

On your Mac:

```bash
# Install WireGuard if you haven't
brew install wireguard-tools

# Create the config file
# Copy the client config from Step 2 into a file:
nano ~/mac-mp-01.conf
# Paste the configuration and save

# Connect to the VPN
sudo wg-quick up ~/mac-mp-01.conf

# Verify connection
ping 10.100.0.1  # Should reach the VM

# Test reaching the emulated network
ping 10.0.0.6    # Should reach cdn-pop1 (might have delays/loss due to impairments!)
```

### Step 5: Configure AppNeta Agent

Now configure your AppNeta agent to monitor these targets:

**Target Configuration:**
- **cdn-pop1** (10.0.0.6) - The CDN endpoint
- **transit1** (10.0.0.5) - Transit provider
- **ispA** (10.0.0.3) - ISP A router
- **ispB** (10.0.0.4) - ISP B router

**What You'll See:**

With the dual-ISP topology, the agent should measure:

1. **Persistent Impairments:**
   - Link `br1-r1 -> ispB`: 0.3% loss, ~8ms jitter

2. **Scheduled Impairments (if you wait for them):**
   - **Daily at 12:00 PM PT** (7:00 PM UTC): 2% loss, 20ms extra delay for 15 minutes
   - **Weekly Monday at 9:00 AM PT** (4:00 PM UTC): BGP flap for 3 minutes
   - **Every hour**: Jitter spike on ISP A link for 5 minutes

## 📊 Expected Results

Your AppNeta agent should show:

### Baseline (No Transient Scenarios):
- **Path via ISP A**: ~50ms RTT, <0.1% loss
- **Path via ISP B**: ~80ms RTT, ~0.3% loss (persistent impairment)

### During "Lunch Loss Burst" (12:00-12:15 PM PT):
- **Path via ISP A**: ~70ms RTT (+20ms), 2% loss
- Traffic may shift to ISP B if your routing detects the degradation

### During BGP Flap (Monday 9:00 AM PT):
- **ISP A path**: Down for 90 seconds
- Traffic shifts to ISP B
- Recovery and convergence

## 🔍 Viewing the Impairments

While your AppNeta agent is monitoring, you can verify impairments are active:

```bash
# In the VM, check what impairments are applied:
sudo tc qdisc show | grep netem

# View events:
curl http://localhost:8080/api/v1/events?limit=20 | python3 -m json.tool

# Watch for scenario changes in real-time:
watch -n 2 'curl -s http://localhost:8080/api/v1/events?limit=5 | python3 -m json.tool'
```

## 🎨 Network Diagram

```
Your Mac (AppNeta Agent)
         |
         | WireGuard VPN (10.100.0.0/24)
         |
    [NetEmulator VM - 10.100.0.1]
         |
         | Connects to Mininet network (10.0.0.0/8)
         |
    ┌────────────────────────────────────────┐
    │  Emulated Network                      │
    │                                        │
    │  br1-r1 (10.0.0.2)                    │
    │     ├─[ISP A]→ transit1 → cdn-pop1    │
    │     │  (fast, but unstable)           │
    │     │                                  │
    │     └─[ISP B]→ transit1 → cdn-pop1    │
    │        (slower, 0.3% loss)            │
    └────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Can't Connect to WireGuard

```bash
# On VM, check WireGuard status:
sudo wg show

# Check if port is listening:
sudo ss -ulnp | grep 51820

# Check firewall:
sudo ufw status
sudo ufw allow 51820/udp
```

### Can Reach VM but Not Mininet Network

```bash
# On VM, check IP forwarding:
sudo sysctl net.ipv4.ip_forward
# Should be 1

# Check iptables rules:
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Make sure routing is correct:
ip route show

# Try manually adding route:
sudo ip route add 10.0.0.0/8 dev wg0
```

### AppNeta Agent Not Seeing Targets

```bash
# From your Mac, test basic connectivity:
ping 10.100.0.1  # VM
ping 10.0.0.6    # cdn-pop1

# Traceroute to see the path:
traceroute 10.0.0.6

# Test from VM to ensure Mininet is reachable:
# On VM:
sudo ip netns exec cdn-pop1 ping -c 3 10.100.0.2
```

## 🎯 What to Monitor

### Primary Targets (Most Interesting):
1. **cdn-pop1 (10.0.0.6)** - End destination with services
2. **transit1 (10.0.0.5)** - Transit provider
3. **ispA (10.0.0.3)** - Primary ISP (fast but flappy)
4. **ispB (10.0.0.4)** - Backup ISP (stable but lossy)

### Metrics to Watch:
- **Latency**: Should increase during scheduled impairments
- **Loss**: 0.3% baseline on ISP B, 2% during lunch burst
- **Jitter**: ~8ms baseline on ISP B, spikes hourly on ISP A
- **Path Changes**: During BGP flaps, watch routing shifts

## 🔧 Disconnect When Done

```bash
# On your Mac:
sudo wg-quick down ~/mac-mp-01.conf

# On VM (to stop WireGuard):
sudo wg-quick down wg0
```

## 🎉 Success Criteria

You'll know it's working when:
1. ✅ AppNeta agent shows the target hosts as reachable
2. ✅ Baseline metrics show expected latency/loss
3. ✅ During scheduled impairments, metrics change accordingly
4. ✅ You can correlate AppNeta measurements with NetEmulator events

---

**This is the real power of NetEmulator!** Your AppNeta agent is now measuring a controlled, repeatable network environment where you can test how it responds to various conditions.

