# NetEmulator Testing Guide

A practical guide to understanding and testing your deployed topologies.

## 🎯 Quick Start: See What's Running

### 1. Check Deployed Topologies

```bash
# In the VM:
curl http://localhost:8080/api/v1/topologies | python3 -m json.tool
```

### 2. Understand Your Network

The **simple_3node** topology you deployed looks like this:

```
h1 (host) ←→ r1 (router with OSPF) ←→ h2 (host)
   
- Link h1↔r1: 100Mbps, 5ms delay, PLUS 10ms extra delay + 1% loss (scenario)
- Link r1↔h2: 100Mbps, 5ms delay
- Total latency h1→h2: ~20ms (5+10+5)
```

## 🧪 Actually Testing the Network

### Option 1: Use Mininet CLI (Most Interactive)

```bash
# In the VM, get into the Mininet network:
sudo python3 << 'EOF'
from mininet.net import Mininet
from mininet.cli import CLI

# This won't work with our running network, so let's use a different approach
EOF
```

**Problem**: Our network is managed by the API, so we can't easily get a CLI into it.

### Option 2: Test Via Network Namespaces

```bash
# In the VM, list network namespaces:
sudo ip netns list

# You should see namespaces for h1, r1, h2
# Test connectivity:
sudo ip netns exec h1 ping -c 3 <h2-ip>
```

### Option 3: Use Mininet's Python API (Best for our setup)

Create a test script:

```python
# test_network.py
import requests
import subprocess
import json

# Get topology info
response = requests.get('http://localhost:8080/api/v1/topologies/simple_3node')
topo = response.json()
print("Topology Status:", json.dumps(topo, indent=2))

# Test network namespaces
result = subprocess.run(['sudo', 'ip', 'netns', 'list'], 
                       capture_output=True, text=True)
print("\nNetwork Namespaces:")
print(result.stdout)

# Try to ping between hosts
print("\nTesting connectivity h1 → h2:")
# Note: You need to know the IPs, typically 10.0.0.1, 10.0.0.2, etc.
```

## 🎨 Visualizing Your Network

### View the Topology Structure

```bash
# Get detailed topology info:
curl http://localhost:8080/api/v1/topologies/simple_3node | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
status = data.get('status', {})
print('Topology:', data['name'])
print('Status:', status.get('status'))
print('Nodes:', status.get('nodes'))
print('Links:', status.get('links'))

scheduler = data.get('scheduler', {})
if scheduler:
    print('\\nScenarios:')
    print('  Total:', scheduler.get('total_scenarios'))
    print('  Active:', scheduler.get('active_scenarios'))
"
```

### View Active Impairments

```bash
# Check which scenarios are running:
curl http://localhost:8080/api/v1/events?topology_name=simple_3node | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for event in data['events']:
    if 'impairment' in event['event_type']:
        print(f\"{event['timestamp'][:19]} - {event['message']}\")
"
```

## 🔬 Practical Tests You Can Do

### Test 1: Check Network Interfaces

```bash
# In the VM:
sudo ovs-vsctl show  # Shows Open vSwitch configuration
ip link show         # Shows all network interfaces
```

You should see interfaces like: `h1-eth0`, `r1-eth0`, `r1-eth1`, `h2-eth0`

### Test 2: Verify Traffic Control (Impairments)

```bash
# Check if netem is applied:
sudo tc qdisc show | grep netem

# Should show something like:
# qdisc netem ... delay 10ms loss 1%
```

### Test 3: Check Router Configuration

```bash
# If you can access the router namespace:
sudo ip netns exec r1 ip route show
sudo ip netns exec r1 ip addr show
```

### Test 4: Monitor Traffic

```bash
# Capture traffic on a link:
sudo tcpdump -i h1-eth0 -n

# In another terminal, generate some traffic
```

## 🚀 Better Approach: Deploy Interactive Topology

Let's create a better test topology with actual services you can hit:

```yaml
# examples/test_with_services.yaml
topology:
  name: interactive_test
  
  nodes:
    - id: client
      type: host
    
    - id: router
      type: router
      asn: 65100
      daemons: [ospf]
    
    - id: webserver
      type: host
      services: [http]
  
  links:
    - [client, router, {bw: 100m, delay: 10ms}]
    - [router, webserver, {bw: 100m, delay: 10ms}]

scenarios:
  persistent:
    - id: baseline_delay
      applies_to: link:client->router
      impairments:
        netem:
          delay: 50ms
          loss: 2%
```

Deploy it:

```bash
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: text/plain" \
  --data-binary @examples/test_with_services.yaml
```

Then you can actually test HTTP:
```bash
# Get the webserver's IP and test:
sudo ip netns exec webserver curl http://localhost:8000
```

## 📊 Understanding the Metrics

```bash
# View all metrics:
curl http://localhost:8080/api/v1/metrics

# Key metrics to watch:
# - netemulator_topologies_total: How many topologies running
# - netemulator_scenarios_active: How many scenarios active
# - netemulator_topology_nodes: Nodes per topology
```

## 🐛 Troubleshooting: Can't See Network Activity?

The issue is that NetEmulator creates the network, but you need to actively use it to see activity. Options:

### Option A: Use our CLI Tool (Coming Soon)

```bash
netemulator exec simple_3node h1 ping h2
```

### Option B: Deploy Test Traffic Generator

Add a test node that continuously generates traffic.

### Option C: Connect an External Monitoring Point

This is the REAL use case - connect an actual AppNeta monitoring point via WireGuard!

## 🎯 Recommended Next Steps

1. **Deploy the dual-ISP topology** - It's more interesting:
   ```bash
   curl -X POST http://localhost:8080/api/v1/topologies \
     -H "Content-Type: text/plain" \
     --data-binary @examples/dual_isp_topology.yaml
   ```

2. **Watch the scheduled scenarios** - The dual-ISP has time-based impairments

3. **Set up Prometheus + Grafana** - Visualize what's happening

4. **Onboard a monitoring point** - This is the real goal!

## 💡 Key Insight

NetEmulator creates the **infrastructure** (network topology with impairments), but you need to either:
- Generate test traffic through it
- Connect actual monitoring points to it
- Use it programmatically via API

The **real value** comes when you connect AppNeta monitoring points and they start measuring the network conditions you've created!

---

Want help with any of these next steps? Let me know! 🚀

