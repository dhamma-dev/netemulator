# NetEmulator Phase 2 Plan

## 🎯 Executive Summary

**Phase 1 (v0.1.0) Status**: ✅ **MVP Complete & Validated**

We successfully proved the core concept:
- Emulated networks with scheduled impairments work
- External monitoring points can connect via WireGuard
- AppNeta agents can monitor emulated targets
- Infrastructure is reproducible and documented

**Phase 2 Goal**: Transform from proof-of-concept to production-ready multi-hop network emulator with full routing capabilities.

## 📊 Phase 1 Achievements

### ✅ What Works Well

1. **Infrastructure**
   - Mininet orchestration (switches, basic routing)
   - Impairment engine (tc/netem, qdisc)
   - Scenario scheduling with RRULE/cron
   - REST API with CRUD operations

2. **External Connectivity**
   - WireGuard VPN for monitoring points
   - Automated onboarding scripts
   - Per-MP isolation capability

3. **Observability**
   - Prometheus metrics export
   - Event logging with timestamps
   - Grafana dashboard templates

4. **Developer Experience**
   - YAML topology DSL
   - Reproducible setup scripts
   - Comprehensive documentation

### ⚠️ Discovered Limitations

1. **Multi-Hop Routing** (Critical)
   - ❌ FRR routers don't properly peer with each other
   - ❌ BGP/OSPF configuration not automatically set up
   - ❌ Routes not exchanged between segments
   - **Impact**: Can only monitor first-hop nodes, not end-to-end paths
   - **User Experience**: "Why can't I ping the CDN endpoint?"

2. **Service Stubs** (Medium)
   - ❌ HTTP/DNS services are very basic
   - ❌ No real HTTP/2 or HTTP/3 implementation
   - ❌ Services don't respond realistically
   - **Impact**: Limited application-layer testing

3. **Bandwidth Limits** (Low)
   - ⚠️ Mininet bandwidth >1Gbps gets capped/ignored
   - ⚠️ HTB quantum warnings on high bandwidth links
   - **Impact**: Can't properly emulate 10G+ links

4. **Network Namespace Access** (Medium)
   - ❌ Can't easily execute commands inside nodes
   - ❌ No CLI for interactive debugging
   - **Impact**: Hard to troubleshoot routing issues

## 🎯 Phase 2 Objectives

### Primary Goals (Must Have)

1. **Full Multi-Hop Routing** ⭐⭐⭐⭐⭐
   - Enable end-to-end connectivity across complex topologies
   - Automatic FRR router peering and route exchange
   - Support for BGP, OSPF, and static routing
   - **Success**: Can ping any node from any other node

2. **Enhanced FRR Integration** ⭐⭐⭐⭐⭐
   - Automatic interface IP assignment
   - BGP neighbor auto-configuration
   - OSPF area setup
   - Route advertisement and propagation
   - **Success**: Dual-ISP and complex_wan topologies work end-to-end

3. **Production Readiness** ⭐⭐⭐⭐
   - Multi-topology support (multiple labs)
   - Resource quotas and limits
   - Canary deployments
   - Automated testing and validation
   - **Success**: Can run 5+ topologies simultaneously

### Secondary Goals (Should Have)

4. **Better Service Stubs** ⭐⭐⭐
   - Real HTTP/2 and HTTP/3 servers
   - Realistic DNS with caching/TTL
   - TCP/UDP echo with proper responses
   - Basic SaaS API mock (OAuth, REST)
   - **Success**: AppNeta can test application-layer metrics

5. **Enhanced Impairments** ⭐⭐⭐
   - Burst loss models (Gilbert-Elliott)
   - Advanced jitter (pareto, normal distributions)
   - Packet reordering scenarios
   - DNS failures, TLS errors
   - **Success**: More realistic network conditions

6. **Debugging Tools** ⭐⭐⭐
   - CLI to exec into nodes: `netemulator exec <topo> <node> <cmd>`
   - Packet capture: `netemulator pcap <topo> <link>`
   - Route inspection: `netemulator routes <topo> <node>`
   - **Success**: Easy troubleshooting

### Nice to Have

7. **Multi-Lab Federation** ⭐⭐
   - Horizontal scaling across multiple hosts
   - Lab-to-lab connectivity
   - Load balancing

8. **Web UI** ⭐⭐
   - Visual topology editor
   - Real-time monitoring
   - Scenario management

9. **Template Marketplace** ⭐
   - Pre-built topology templates
   - Scenario libraries
   - Community contributions

## 🔧 Phase 2 Implementation Plan

### Sprint 1: Multi-Hop Routing (Critical) - 3 weeks

**Goal**: Enable end-to-end connectivity in complex topologies

**Tasks**:

1. **FRR Router IP Auto-Configuration**
   ```python
   # Auto-assign IPs to router interfaces based on links
   # Example: r1-eth0 gets 10.0.1.1/24, r2-eth0 gets 10.0.1.2/24
   ```
   - Parse topology links
   - Assign subnets to each link
   - Configure interface IPs on both ends
   - Add to FRR config generation

2. **BGP Neighbor Auto-Discovery**
   ```python
   # For routers with BGP daemon, auto-configure neighbors
   # Based on direct link connections
   ```
   - Detect adjacent routers
   - Generate BGP neighbor statements
   - Set up eBGP/iBGP based on ASNs
   - Configure route advertisements

3. **OSPF Area Auto-Configuration**
   ```python
   # For routers with OSPF, auto-assign areas
   # Default: all interfaces in area 0.0.0.0
   ```
   - Add all interfaces to OSPF
   - Configure proper network statements
   - Enable OSPF on router

4. **Static Route Fallback**
   ```python
   # If no routing daemons, add static routes
   # Compute shortest paths and add routes
   ```
   - Implement Dijkstra for path computation
   - Add static routes for unreachable networks
   - Fallback when BGP/OSPF not configured

**Acceptance Criteria**:
- [ ] Can ping 10.0.0.5 (cdn-pop1) from host in dual_isp topology
- [ ] Can ping 10.0.0.11 (cloud-app1) in complex_wan topology
- [ ] Traceroute shows correct multi-hop paths
- [ ] Routes appear in `ip route` on all nodes
- [ ] BGP peers show as "Established" in `vtysh`

**Deliverables**:
- Updated `router.py` with auto-configuration
- Enhanced `compiler.py` with IP assignment logic
- Test suite for multi-hop connectivity
- Documentation on routing architecture

---

### Sprint 2: Enhanced Impairments & Services - 2 weeks

**Goal**: More realistic network conditions and application testing

**Tasks**:

1. **Advanced Loss Models**
   - Gilbert-Elliott model (burst loss)
   - Conditional loss based on packet size
   - Loss correlation over time

2. **Real HTTP Services**
   - Use nginx or Python HTTP servers
   - Support HTTP/2 and HTTP/3
   - TLS with proper certificates
   - Configurable response times/sizes

3. **DNS Server Enhancement**
   - Use dnsmasq or bind
   - Proper zone files
   - TTL and caching behavior
   - Fault injection (NXDOMAIN, SERVFAIL, timeouts)

4. **More Control Plane Events**
   - BGP route dampening
   - OSPF cost manipulation
   - Interface flaps with configurable timing
   - Route hijacking scenarios

**Acceptance Criteria**:
- [ ] Can measure HTTP/2 and HTTP/3 latency from AppNeta
- [ ] DNS queries show realistic caching behavior
- [ ] Burst loss models create realistic loss patterns
- [ ] BGP events visible in FRR logs and AppNeta

---

### Sprint 3: Debugging & Production Features - 2 weeks

**Goal**: Make system production-ready and debuggable

**Tasks**:

1. **CLI Enhancements**
   ```bash
   netemulator exec <topo> <node> <command>
   netemulator pcap <topo> <link> -o capture.pcap
   netemulator routes <topo> <node>
   netemulator logs <topo> --follow
   ```

2. **Multi-Topology Support**
   - Resource isolation per topology
   - CPU/memory quotas
   - Bandwidth allocation
   - Namespace collision prevention

3. **Canary Deployments**
   - Rolling updates for topologies
   - Health checks before cutover
   - Automatic rollback on failure

4. **Golden Test Suite**
   - End-to-end connectivity tests
   - Impairment verification tests
   - Performance regression tests
   - Run on every commit (CI/CD)

**Acceptance Criteria**:
- [ ] Can run 5 topologies simultaneously without interference
- [ ] Can exec into any node and run commands
- [ ] Packet captures work on all links
- [ ] Automated test suite passes 100%

---

## 📋 Detailed: Multi-Hop Routing Implementation

### Technical Design

#### Problem Statement
Currently, FRR routers are created but:
1. Interfaces don't get IP addresses
2. Routers don't know about their neighbors
3. No routes are exchanged
4. Packets can't traverse multiple hops

#### Solution Architecture

**1. Topology Compilation Phase**

```python
class TopologyCompiler:
    def compile_routing(self, topology):
        # Step 1: Assign subnet to each link
        link_subnets = self._assign_link_subnets(topology.links)
        
        # Step 2: Assign IPs to interfaces
        interface_ips = self._assign_interface_ips(link_subnets)
        
        # Step 3: Generate FRR configs
        for node in topology.nodes:
            if node.type == NodeType.ROUTER:
                config = self._generate_frr_config(node, interface_ips)
                node.config['frr_config'] = config
        
        return topology
    
    def _assign_link_subnets(self, links):
        """Assign /30 subnets to each link"""
        subnets = {}
        subnet_base = ipaddress.ip_network('10.0.0.0/8')
        available = subnet_base.subnets(new_prefix=30)
        
        for link in links:
            link_id = f"{link.src}-{link.dst}"
            subnets[link_id] = next(available)
        
        return subnets
    
    def _generate_frr_config(self, router, interface_ips):
        """Generate complete FRR config with interfaces and routing"""
        config = []
        
        # Interface configuration
        for intf, ip in interface_ips[router.id].items():
            config.append(f"interface {intf}")
            config.append(f"  ip address {ip}")
        
        # BGP configuration
        if 'bgp' in router.daemons:
            config.extend(self._generate_bgp_config(router))
        
        # OSPF configuration
        if 'ospf' in router.daemons:
            config.extend(self._generate_ospf_config(router))
        
        return "\n".join(config)
```

**2. Router Node Enhancement**

```python
class FRRRouter(Node):
    def configure(self):
        """Apply FRR configuration"""
        # Apply interface IPs from config
        for intf, ip in self.interface_ips.items():
            self.cmd(f'ip addr add {ip} dev {intf}')
            self.cmd(f'ip link set {intf} up')
        
        # Write FRR config
        self._write_frr_config()
        
        # Start FRR daemons
        self._start_frr_daemons()
        
        # Wait for convergence
        self._wait_for_routes()
    
    def _wait_for_routes(self, timeout=30):
        """Wait for routing protocol to converge"""
        start = time.time()
        while time.time() - start < timeout:
            # Check if routes are learned
            routes = self.cmd('ip route show')
            if self._has_default_route(routes):
                return True
            time.sleep(1)
        return False
```

**3. Validation Tests**

```python
def test_multihop_connectivity():
    """Test end-to-end connectivity in dual-ISP topology"""
    compiler = TopologyCompiler()
    topology = compiler.load_from_yaml('examples/dual_isp_topology.yaml')
    
    network = create_network(topology)
    
    # Test connectivity from br1-r1 to cdn-pop1
    result = network.get_node('br1-r1').cmd('ping -c 3 10.0.0.5')
    
    assert '0% packet loss' in result
    assert 'ttl=' in result  # Received responses
    
    # Verify route exists
    routes = network.get_node('br1-r1').cmd('ip route show')
    assert '10.0.0.5' in routes or '0.0.0.0/0' in routes
```

### Implementation Steps

1. **Week 1**: IP assignment and interface configuration
   - Implement `_assign_link_subnets()`
   - Implement `_assign_interface_ips()`
   - Test: interfaces get correct IPs

2. **Week 2**: BGP auto-configuration
   - Implement neighbor discovery
   - Generate BGP configs
   - Test: BGP peers establish

3. **Week 3**: OSPF and validation
   - Implement OSPF configuration
   - Add routing convergence waits
   - End-to-end testing

---

## 🎯 Success Metrics

### Phase 2 Completion Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Multi-hop connectivity | 100% | All example topologies: can ping any node from any node |
| Topology convergence time | <30s | Time from deploy to all routes present |
| Concurrent topologies | 5+ | Deploy 5 topologies, all work independently |
| Impairment accuracy | ±5% | Measured loss/latency vs configured |
| Service response rate | 99%+ | HTTP/DNS services respond correctly |
| Documentation coverage | 100% | Every new feature documented |

### AppNeta Integration Validation

- [ ] Can monitor end-to-end paths (e.g., Mac → cdn-pop1)
- [ ] Measures match expected impairments within ±10%
- [ ] Scheduled scenarios visible in AppNeta timeline
- [ ] Path changes detected during BGP events
- [ ] Application-layer metrics (HTTP timing) accurate

---

## 🚀 Getting Started with Phase 2

### For Immediate Start

```bash
# Create Phase 2 branch
git checkout -b phase-2/multi-hop-routing

# Start with routing enhancement
vim netemulator/control/compiler.py
# Add IP assignment logic

# Create test
vim tests/test_multihop_routing.py
```

### Priority Order

**Week 1-3**: Multi-hop routing (CRITICAL)
- Blocks everything else
- Highest user pain point
- Enables true end-to-end testing

**Week 4-5**: Enhanced services and impairments
- Improves realism
- Better AppNeta testing

**Week 6-7**: Production readiness
- Multiple topologies
- Debugging tools
- Automated testing

---

## 💭 Open Questions for Alignment

1. **Routing Protocol Priority**
   - Should we focus on BGP, OSPF, or static routes first?
   - Recommendation: **Static routes** (simplest) → **OSPF** (auto-discovery) → **BGP** (flexibility)

2. **IP Address Space**
   - Continue with 10.0.0.0/8 or use separate subnets per topology?
   - Recommendation: **10.X.0.0/16** where X = topology ID

3. **FRR vs Static**
   - Should simple topologies use static routes instead of FRR?
   - Recommendation: **Auto-detect** - use static if no daemons specified

4. **Service Stubs Priority**
   - Which service is most important: HTTP/2, HTTP/3, or DNS?
   - Recommendation: **HTTP/2** first (most common), then DNS

5. **Timeline**
   - Is 7 weeks reasonable for Phase 2?
   - Can compress to 4-5 weeks if needed

---

## 📝 Next Actions

**To proceed with Phase 2:**

1. **Review and approve this plan**
2. **Prioritize: Which Sprint to start with?**
3. **Create Phase 2 branch**: `git checkout -b phase-2-routing`
4. **Start implementation**: Begin with Sprint 1, Task 1
5. **Set up tracking**: Create GitHub issues for each task

**Quick Win Option:**
Start with static routes implementation (easier than full FRR) to prove multi-hop works, then enhance with dynamic routing.

---

## 🎓 Lessons from Phase 1

**What worked well:**
- ✅ Incremental development with real testing
- ✅ Documentation-driven design
- ✅ Early validation with actual monitoring tools
- ✅ Reproducible setup scripts

**What to improve:**
- ⚠️ More upfront testing of complex scenarios
- ⚠️ Earlier integration testing (not just unit tests)
- ⚠️ Better error messages and debugging output

**Apply to Phase 2:**
- Test multi-hop routing EARLY in Sprint 1
- Add integration tests before considering feature "done"
- Include troubleshooting in every feature

---

**Ready to proceed? Which Sprint should we start with?** 🚀

