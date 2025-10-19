# Changelog

All notable changes to NetEmulator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-18

### Added

#### Core Infrastructure
- Complete MVP implementation of NetEmulator continuous testbed
- Topology DSL with YAML parser and validator
- Pydantic-based data models for topology, scenarios, and events
- Resource estimation for topology validation

#### Data Plane
- Mininet orchestration layer with dynamic topology building
- FRR router nodes with OSPF and BGP daemon support
- Service host nodes with DNS, HTTP/HTTPS, TCP/UDP echo services
- Open vSwitch integration for switching

#### Impairment Engine
- tc/netem integration for delay, loss, jitter, corruption
- Queue discipline management (HTB, TBF, fq_codel)
- Routing protocol event injection (BGP flaps, route withdrawals, OSPF cost changes)
- Interface flap simulation
- Link, path, and node-level targeting

#### Scenario Management
- Scenario scheduler with RRULE and cron expression support
- Persistent (always-on) scenarios
- Transient (scheduled) scenarios with duration control
- Event logging with time alignment
- Priority-based scenario conflict resolution

#### External Connectivity
- WireGuard VPN manager for monitoring point ingress
- Automatic keypair generation
- Per-MP isolation with VRF support
- Self-service onboarding workflow

#### Control Plane
- FastAPI-based REST API
- Topology lifecycle management (create, read, delete, validate)
- Scenario management endpoints
- Event query API
- Health check and status endpoints

#### Observability
- Prometheus metrics exporter
- Grafana dashboard generator
- Structured event logging
- Time-aligned impairment tracking
- Performance metrics (API latency, scenario execution)

#### CLI & Tools
- Rich CLI with deploy, list, status, events, metrics commands
- Installation script for Ubuntu dependencies
- Start/stop service management scripts
- Deployment helper scripts
- Makefile for common operations

#### Deployment
- Docker support with Dockerfile
- docker-compose stack with Prometheus and Grafana
- systemd service templates
- Cloud-init examples for automated VM setup

#### Documentation
- Comprehensive README with architecture overview
- Quick Start guide (5-minute setup)
- Project summary with technical deep dive
- Deployment guide for production environments
- Contributing guidelines
- Three example topologies (simple, dual-ISP, complex WAN)

#### Testing
- pytest test suite with fixtures
- Topology parsing and validation tests
- Scenario parsing tests
- Mock objects for unit testing

### Fixed
- Removed mininet from pip requirements (installed via apt)
- Added Body parameter for text/plain YAML uploads in FastAPI
- Virtual environment now uses --system-site-packages for Mininet access

### Tested
- Ubuntu 22.04 LTS
- Ubuntu 24.04 LTS
- Multipass VM deployment
- Simple 3-node topology
- Dual-ISP topology with scheduled impairments
- Complex multi-site WAN topology

### Known Limitations
- Scale tested up to ~50 nodes (target: 200+)
- FRR configuration simplified (full integration pending)
- Service stubs are basic implementations
- Authentication/authorization not implemented
- Single-tenant only

## [Unreleased]

### Planned for v0.2.0 (Phase 2)
- Multi-lab federation for horizontal scaling
- Enhanced BGP/OSPF event library
- Advanced queue management and burst models
- Authentication and RBAC
- Canary deployments
- Golden test catalog
- Enhanced service stubs (full HTTP/2, HTTP/3)

### Planned for v1.0.0 (Phase 3)
- Multi-tenant support
- Self-service web UI
- Template marketplace
- Analytics exports and reporting
- SLO tracking and alerting
- Advanced security features

---

[0.1.0]: https://github.com/YOUR_USERNAME/netemulator/releases/tag/v0.1.0

