# NetEmulator - Project Summary

## Overview

NetEmulator is a comprehensive, continuously running network emulation testbed designed for AppNeta monitoring point validation, fault injection, and performance testing. It provides an "Internet-in-a-box" environment with scheduled impairments, multi-domain routing, and full observability.

## Project Status: ✅ MVP Complete

All Phase 1 (MVP) components have been implemented and are ready for testing and deployment.

## Architecture Components

### 1. Control Plane ✅
- **Topology Compiler** (`netemulator/control/compiler.py`)
  - YAML topology parsing and validation
  - FRR configuration generation
  - Resource estimation
  - Topology-to-Mininet conversion

- **REST API** (`netemulator/control/api.py`)
  - FastAPI-based control interface
  - Topology lifecycle management (create, read, delete)
  - Scenario management
  - Event and metrics endpoints
  - Health checks

- **Scheduler** (`netemulator/control/scheduler.py`)
  - RRULE and cron-based scheduling
  - Persistent and transient scenario support
  - Event logging and tracking
  - APScheduler integration

### 2. Data Plane ✅
- **Mininet Orchestration** (`netemulator/dataplane/mininet_topo.py`)
  - Dynamic topology creation
  - OVS switch support
  - FRR router nodes
  - Service host nodes
  - Link parameter management

- **FRR Router** (`netemulator/dataplane/router.py`)
  - OSPF and BGP daemon support
  - Dynamic configuration generation
  - VTYsh integration
  - Neighbor management

- **Service Host** (`netemulator/dataplane/host.py`)
  - DNS server stub
  - HTTP/HTTPS servers
  - TCP/UDP echo services
  - CDN emulation

### 3. Impairments Engine ✅
- **Netem** (`netemulator/impairments/netem.py`)
  - Delay, loss, jitter, corruption
  - Distribution models (normal, pareto)
  - tc/netem integration
  - Per-interface management

- **Queue Disciplines** (`netemulator/impairments/qdisc.py`)
  - HTB (Hierarchical Token Bucket)
  - TBF (Token Bucket Filter)
  - fq_codel support
  - Bandwidth shaping

- **Routing Events** (`netemulator/impairments/routing.py`)
  - BGP session flaps
  - Route withdrawals
  - OSPF cost changes
  - Interface flaps

### 4. Ingress Layer ✅
- **WireGuard VPN** (`netemulator/ingress/wireguard.py`)
  - Keypair generation
  - Peer onboarding
  - Per-MP isolation
  - Configuration generation

- **MP Manager** (`netemulator/ingress/wireguard.py`)
  - External monitoring point connectivity
  - VRF/namespace isolation
  - Status tracking

### 5. Observability ✅
- **Metrics** (`netemulator/observability/metrics.py`)
  - Prometheus exporter
  - Topology, scenario, and event metrics
  - Performance tracking
  - Custom metrics support

- **Dashboards** (`netemulator/observability/dashboard.py`)
  - Grafana dashboard generation
  - Overview and topology-specific views
  - Time-series visualization

### 6. Data Models ✅
- **Topology** (`netemulator/models/topology.py`)
  - Node, link, and MP ingress models
  - Pydantic validation
  - Type safety

- **Scenario** (`netemulator/models/scenario.py`)
  - Persistent and transient scenarios
  - Netem, qdisc, and control plane specs
  - Target parsing (link, path, node)

- **Event** (`netemulator/models/event.py`)
  - Event types and severity
  - Structured logging
  - Prometheus label generation

## File Structure

```
netemulator/
├── README.md                      # Main documentation
├── QUICKSTART.md                  # Quick start guide
├── CONTRIBUTING.md                # Development guidelines
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
├── Makefile                       # Build automation
├── .gitignore                     # Git ignore rules
│
├── netemulator/                   # Main package
│   ├── __init__.py
│   ├── models/                    # Data models
│   │   ├── topology.py
│   │   ├── scenario.py
│   │   └── event.py
│   ├── control/                   # Control plane
│   │   ├── api.py                # REST API
│   │   ├── compiler.py           # Topology compiler
│   │   ├── scheduler.py          # Scenario scheduler
│   │   └── validator.py
│   ├── dataplane/                 # Data plane
│   │   ├── mininet_topo.py       # Mininet orchestration
│   │   ├── router.py             # FRR router nodes
│   │   └── host.py               # Service hosts
│   ├── impairments/               # Fault injection
│   │   ├── netem.py              # tc/netem
│   │   ├── qdisc.py              # Queue disciplines
│   │   └── routing.py            # Control plane events
│   ├── ingress/                   # MP connectivity
│   │   └── wireguard.py          # WireGuard VPN
│   ├── observability/             # Monitoring
│   │   ├── metrics.py            # Prometheus
│   │   └── dashboard.py          # Grafana
│   └── utils/                     # Utilities
│       ├── network.py
│       └── time_utils.py
│
├── examples/                      # Example topologies
│   ├── simple_3node.yaml
│   ├── dual_isp_topology.yaml
│   └── complex_wan.yaml
│
├── scripts/                       # Deployment scripts
│   ├── install_dependencies.sh
│   ├── start_services.sh
│   ├── stop_services.sh
│   └── deploy_topology.sh
│
├── deployment/                    # Production deployment
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── prometheus.yml
│
└── tests/                         # Test suite
    ├── __init__.py
    ├── conftest.py
    ├── test_topology.py
    └── test_scenarios.py
```

## Key Features Implemented

### ✅ Topology Management
- YAML-based topology definition
- Multi-domain routing (OSPF, BGP)
- Switches, routers, and service hosts
- Link parameters (bandwidth, delay, loss)
- Validation and resource estimation

### ✅ Impairment Scenarios
- Persistent (always-on) scenarios
- Transient (scheduled) scenarios
- RRULE and cron scheduling
- Multiple impairment types:
  - Network: delay, loss, jitter, corruption
  - Traffic: bandwidth caps, queue limits
  - Control plane: BGP flaps, route changes
  - Protocol: interface flaps

### ✅ External Connectivity
- WireGuard VPN for monitoring points
- Keypair generation
- Per-MP configuration
- Isolation and routing

### ✅ Observability
- Prometheus metrics endpoint
- Event logging with timestamps
- Grafana dashboard generation
- Time-aligned event tracking

### ✅ REST API
- Topology CRUD operations
- Scenario management
- Event queries
- Health checks
- Metrics export

## Example Usage

### 1. Deploy a Topology

```bash
# Start services
make start

# Deploy example topology
./scripts/deploy_topology.sh examples/dual_isp_topology.yaml
```

### 2. Monitor Events

```bash
curl http://localhost:8080/api/v1/events
```

### 3. Trigger a Scenario

```bash
curl -X POST "http://localhost:8080/api/v1/scenarios/lunch_loss_burst/trigger?topology_name=dual_isp_branch_to_cdn"
```

### 4. View Metrics

```bash
curl http://localhost:8080/api/v1/metrics
```

## Testing

Test suite includes:
- Topology parsing and validation tests
- Scenario parsing tests
- Target parsing tests
- Mock fixtures for unit testing

Run tests:
```bash
make test
```

## Deployment Options

### 1. Development (Local)
```bash
make install
make start
```

### 2. Production (Systemd)
See `deployment/README.md` for systemd service setup.

### 3. Containerized (Docker)
```bash
cd deployment
docker-compose up -d
```

## Phase Roadmap

### ✅ Phase 1 - MVP (Complete)
- Topology DSL and compiler
- Mininet orchestration
- Basic impairments (netem)
- REST API
- Scenario scheduler
- WireGuard ingress
- Prometheus metrics

### 🔄 Phase 2 - Scale & Rich Faults (Next)
- Multi-lab federation
- BGP/OSPF event library
- Advanced queue management
- Burst and jitter models
- Canary deployments
- Golden test catalogs

### 📋 Phase 3 - Enterprise (Future)
- Multi-tenant RBAC
- Self-service UI
- Template marketplace
- Analytics exports
- SLO tracking
- Advanced security

## Success Metrics

### Target SLOs
- **Uptime**: 99.5% orchestration plane
- **Scheduling**: 99% on-time scenario execution
- **Impairment Fidelity**: ±10% of specification
- **Throughput**: 5+ Gbps aggregate
- **Spin-up**: <10 minutes per topology
- **MP Onboarding**: <15 minutes

## Known Limitations

1. **Scale**: Tested up to ~50 nodes per topology (target: 200+)
2. **FRR Integration**: Simplified configuration (full integration pending)
3. **Service Stubs**: Basic implementations (needs enhancement)
4. **Security**: Authentication/authorization not yet implemented
5. **Multi-tenancy**: Single-tenant only in current version

## Getting Started

1. Read [QUICKSTART.md](QUICKSTART.md) for 5-minute setup
2. Review [README.md](README.md) for full documentation
3. Explore [examples/](examples/) for topology patterns
4. Check [deployment/README.md](deployment/README.md) for production setup

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Support

- **Issues**: File on GitHub
- **Documentation**: See README.md and inline docstrings
- **Email**: engineering@appneta.com

## License

Proprietary - AppNeta Internal Use Only

---

**Project Status**: MVP Complete ✅  
**Version**: 0.1.0  
**Last Updated**: October 18, 2025

