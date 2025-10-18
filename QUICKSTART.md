# NetEmulator Quick Start Guide

Get NetEmulator up and running in 5 minutes!

## Prerequisites

- Linux system (Ubuntu 20.04+ recommended)
- Root/sudo access
- Python 3.9+
- 8GB+ RAM

## Step 1: Install

```bash
# Clone repository
git clone https://github.com/appneta/netemulator.git
cd netemulator

# Install dependencies (requires sudo)
sudo make install

# Activate virtual environment
source venv/bin/activate
```

## Step 2: Start Services

```bash
# Start NetEmulator
make start
```

This starts the API server on port 8080.

## Step 3: Deploy a Topology

Deploy the example dual-ISP topology:

```bash
# Deploy topology
make deploy
```

Or manually:

```bash
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: text/plain" \
  --data-binary @examples/dual_isp_topology.yaml
```

## Step 4: Verify

Check that the topology is running:

```bash
curl http://localhost:8080/api/v1/topologies
```

You should see output like:

```json
{
  "topologies": [
    {
      "name": "dual_isp_branch_to_cdn",
      "status": {
        "status": "running",
        "nodes": {
          "total": 6,
          "switches": 1,
          "routers": 3,
          "hosts": 1
        },
        "links": 6
      }
    }
  ]
}
```

## Step 5: Monitor Events

Watch for scenario events:

```bash
# Get all events
curl http://localhost:8080/api/v1/events

# Get events for specific topology
curl "http://localhost:8080/api/v1/events?topology_name=dual_isp_branch_to_cdn"
```

## Step 6: View Metrics

View Prometheus-format metrics:

```bash
curl http://localhost:8080/api/v1/metrics
```

## Common Operations

### Create a Simple Topology

Create `my_topology.yaml`:

```yaml
topology:
  name: my_network
  
  nodes:
    - id: host1
      type: host
      services: [http]
    
    - id: router1
      type: router
      asn: 65100
      daemons: [ospf]
    
    - id: host2
      type: host
  
  links:
    - [host1, router1, {bw: 100m, delay: 10ms}]
    - [router1, host2, {bw: 100m, delay: 10ms}]

scenarios:
  persistent:
    - id: baseline_latency
      applies_to: link:host1->router1
      impairments:
        netem:
          delay: 20ms
          loss: 1%
```

Deploy it:

```bash
./scripts/deploy_topology.sh my_topology.yaml
```

### Manually Trigger a Scenario

```bash
curl -X POST "http://localhost:8080/api/v1/scenarios/lunch_loss_burst/trigger?topology_name=dual_isp_branch_to_cdn"
```

### Stop a Topology

```bash
curl -X DELETE http://localhost:8080/api/v1/topologies/dual_isp_branch_to_cdn
```

### Validate Before Deploying

```bash
curl -X POST "http://localhost:8080/api/v1/topologies/my_network/validate" \
  -H "Content-Type: text/plain" \
  --data-binary @my_topology.yaml
```

## Troubleshooting

### Services won't start

```bash
# Clean up any stale Mininet state
sudo mn -c

# Check logs
tail -f logs/api.log
```

### "Permission denied" errors

Make sure you're running with sufficient privileges:
```bash
# Some operations require root
sudo -E python3 -m netemulator.control.api
```

### Topologies fail to create

Check validation:
```bash
curl -X POST "http://localhost:8080/api/v1/topologies/test/validate" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/dual_isp_topology.yaml
```

## Next Steps

- Read the [full README](README.md) for architecture details
- Explore [example topologies](examples/)
- Check the [deployment guide](deployment/README.md) for production setup
- Review the [API documentation](#) (coming soon)
- Try the [WireGuard MP onboarding](#) for external monitoring points

## Getting Help

- File issues on GitHub
- Check logs in `logs/`
- Review documentation in `docs/`
- Contact AppNeta support

## Clean Up

Stop services and clean up:

```bash
# Stop services
make stop

# Clean up Mininet state
make clean
```

## Pro Tips

1. **Use the Makefile**: `make install`, `make start`, `make deploy`, etc.
2. **Monitor logs**: `tail -f logs/api.log` in another terminal
3. **Start simple**: Begin with `simple_3node.yaml` before complex topologies
4. **Validate first**: Always validate before deploying
5. **Check metrics**: Use `/api/v1/metrics` to monitor system health

Happy emulating! 🚀

