# NetEmulator - Continuous Internet Testbed for AppNeta

A continuously running, orchestrated Mininet-based "Internet-in-a-box" for AppNeta monitoring point validation, fault injection, and performance testing.

## Overview

NetEmulator provides:
- **Multi-domain network emulation**: LANs, WAN edges, multi-hop transit, public services
- **Scheduled impairments**: Loss, latency, jitter, reorder, bandwidth caps, BGP/OSPF events
- **External MP connectivity**: Real monitoring points via WireGuard/OpenVPN/GRE
- **24×7 continuous operation**: Persistent and transient scenario calendars
- **Full observability**: Prometheus, Grafana, Loki integration with time-aligned events

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Control Plane                          │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ REST API │  │   Topology   │  │     Scenario       │   │
│  │    &     │──│   Compiler   │  │    Scheduler       │   │
│  │   UI     │  │   (YAML→Net) │  │  (RRULE/Cron)      │   │
│  └──────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                        Data Plane                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Mininet Runtime (OVS + FRR Routers)                 │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐  │  │
│  │  │ Switch │──│ Router │──│ Router │──│ Services │  │  │
│  │  │  (OVS) │  │  (FRR) │  │  (FRR) │  │  Pods    │  │  │
│  │  └────────┘  └────────┘  └────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Impairment Engine (tc/netem, iptables, BGP events) │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Ingress/Edge Layer                        │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │  WireGuard   │  │  Policy Engine (VRF/Namespace      │  │
│  │ Concentrator │──│  isolation per MP)                 │  │
│  └──────────────┘  └────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Observability                           │
│  Prometheus + Exporters | Grafana | Loki | Event Timeline   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Linux host (Ubuntu 20.04+ or similar) with kernel 5.4+
- Python 3.9+
- Mininet 2.3.0+
- FRRouting 8.0+
- Open vSwitch 2.15+
- WireGuard tools
- Docker (for service stubs)

### Installation

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch python3-pip wireguard

# Install FRRouting
curl -s https://deb.frrouting.org/frr/keys.asc | sudo apt-key add -
echo "deb https://deb.frrouting.org/frr $(lsb_release -sc) frr-stable" | sudo tee /etc/apt/sources.list.d/frr.list
sudo apt-get update
sudo apt-get install -y frr frr-pythontools

# Install Python dependencies
pip3 install -r requirements.txt

# Configure system
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1
```

### Running the System

```bash
# Start the control plane
python3 -m netemulator.control.api

# In another terminal, deploy a topology
curl -X POST http://localhost:8080/api/v1/topologies \
  -H "Content-Type: application/yaml" \
  --data-binary @examples/dual_isp_topology.yaml

# Start the scheduler
python3 -m netemulator.control.scheduler

# View logs and metrics
python3 -m netemulator.observability.dashboard
```

## Topology DSL

Define network topologies in YAML:

```yaml
topology:
  name: dual_isp_branch_to_cdn
  nodes:
    - id: br1-sw1
      type: switch
    - id: br1-r1
      type: router
      asn: 65001
      daemons: [ospf, bgp]
    - id: ispA
      type: router
      asn: 64512
      daemons: [bgp]
    - id: cdn-pop1
      type: host
      services: [http3, dns]
  
  links:
    - [br1-sw1, br1-r1, {bw: 1g, delay: 1ms}]
    - [br1-r1, ispA, {bw: 200m, delay: 10ms}]
    - [ispA, cdn-pop1, {bw: 10g, delay: 5ms}]

scenarios:
  persistent:
    - id: baseline_qos
      applies_to: link:br1-r1->ispA
      netem: {loss: 0.3%, jitter: {mean: 8ms, stddev: 3ms}}
  
  transient:
    - id: lunch_loss_burst
      schedule: "RRULE:FREQ=DAILY;BYHOUR=19;BYMINUTE=0;DURATION=PT15M"
      applies_to: path:br1-r1->ispA->cdn-pop1
      netem: {loss: 2%}

mp_ingress:
  type: wireguard
  assign:
    - mp_id: mp-sea-01
      attach_to: br1-r1
      vrf: branch01
```

## API Reference

### Topologies

- `POST /api/v1/topologies` - Create/update topology
- `GET /api/v1/topologies/{name}` - Get topology details
- `DELETE /api/v1/topologies/{name}` - Tear down topology
- `POST /api/v1/topologies/{name}/validate` - Dry-run validation

### Scenarios

- `POST /api/v1/scenarios` - Create scenario
- `PUT /api/v1/scenarios/{id}` - Update scenario
- `POST /api/v1/scenarios/{id}/trigger` - Manually trigger
- `GET /api/v1/scenarios/{id}/events` - Get event history

### Monitoring Points

- `POST /api/v1/mp/onboard` - Onboard new MP
- `GET /api/v1/mp/{id}/config` - Get WireGuard config
- `GET /api/v1/mp/{id}/health` - Check MP connectivity

### Observability

- `GET /api/v1/events` - Query event timeline
- `GET /api/v1/metrics` - Prometheus metrics endpoint
- `GET /api/v1/dashboards` - List Grafana dashboards

## Project Structure

```
netemulator/
├── control/              # Control plane
│   ├── api.py           # REST API server
│   ├── compiler.py      # Topology YAML → Mininet compiler
│   ├── scheduler.py     # Scenario scheduler (RRULE)
│   └── validator.py     # Topology & scenario validation
├── dataplane/           # Data plane orchestration
│   ├── mininet_topo.py  # Mininet topology builder
│   ├── router.py        # FRR router nodes
│   ├── switch.py        # OVS switch nodes
│   └── host.py          # Host/service nodes
├── impairments/         # Fault injection engine
│   ├── netem.py         # tc/netem impairments
│   ├── qdisc.py         # Queue discipline/shaping
│   ├── routing.py       # BGP/OSPF events
│   └── security.py      # Firewall/DNS/TLS faults
├── ingress/             # External MP connectivity
│   ├── wireguard.py     # WireGuard concentrator
│   ├── policy.py        # VRF/namespace isolation
│   └── vpn_manager.py   # VPN lifecycle
├── services/            # Service stubs
│   ├── dns_server.py    # DNS with fault injection
│   ├── http_server.py   # HTTP/2/3 with TLS
│   └── cdn_stub.py      # Anycast-like CDN
├── observability/       # Monitoring & logging
│   ├── metrics.py       # Prometheus exporters
│   ├── events.py        # Event logging
│   └── dashboard.py     # Grafana integration
├── models/              # Data models
│   ├── topology.py      # Topology schema
│   ├── scenario.py      # Scenario schema
│   └── event.py         # Event schema
└── utils/               # Utilities
    ├── network.py       # Network helpers
    ├── time_utils.py    # Time alignment
    └── resource.py      # Resource quotas
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Linting
pylint netemulator/

# Type checking
mypy netemulator/

# Format
black netemulator/
```

## Deployment

See [deployment/README.md](deployment/README.md) for production deployment instructions.

## Roadmap

- [x] Phase 0: Spike with basic Mininet + FRR + tc/netem
- [ ] Phase 1: MVP with DSL, API, scheduler, service pods
- [ ] Phase 2: BGP/OSPF events, multi-lab federation, canary
- [ ] Phase 3: Multi-tenant RBAC, self-service UI, analytics

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

Proprietary - AppNeta Internal Use Only

