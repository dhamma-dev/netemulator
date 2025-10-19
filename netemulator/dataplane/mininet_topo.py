"""
Mininet Topology Builder - Creates and manages Mininet networks from compiled topologies.
"""

import logging
from typing import Dict, Optional, Any, List
from mininet.net import Mininet
from mininet.node import OVSSwitch, Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

from ..models.topology import Topology, NodeType
from .router import FRRRouter
from .host import ServiceHost
from ..utils.routing import compute_static_routes, assign_node_ips, generate_static_route_commands

logger = logging.getLogger(__name__)


class NetworkTopology:
    """Manages a Mininet network instance from a topology definition."""

    def __init__(self, topology: Topology):
        """
        Initialize network topology.
        
        Args:
            topology: Topology definition
        """
        self.topology = topology
        self.net: Optional[Mininet] = None
        self.nodes: Dict[str, Any] = {}
        self.links: Dict[str, Any] = {}
        self.node_ips: Dict[str, str] = {}
        self.static_routes: Dict[str, List] = {}
        
    def build(self) -> Mininet:
        """Build the Mininet network."""
        logger.info(f"Building network topology: {self.topology.name}")
        
        # Create Mininet instance
        self.net = Mininet(
            topo=None,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=True,
            autoStaticArp=True,
            waitConnected=True
        )
        
        # Add nodes
        for node in self.topology.nodes:
            self._add_node(node)
        
        # Add links
        for link in self.topology.links:
            self._add_link(link)
        
        logger.info(f"Built topology with {len(self.nodes)} nodes and {len(self.links)} links")
        return self.net
    
    def _add_node(self, node):
        """Add a node to the network."""
        node_id = node.id
        
        if node.type == NodeType.SWITCH:
            # Add OVS switch
            mininet_node = self.net.addSwitch(
                node_id,
                cls=OVSSwitch,
                failMode='standalone'
            )
            logger.debug(f"Added switch: {node_id}")
            
        elif node.type == NodeType.ROUTER:
            # Add FRR router
            mininet_node = self.net.addHost(
                node_id,
                cls=FRRRouter,
                asn=node.asn,
                daemons=node.daemons,
                config=node.config
            )
            logger.debug(f"Added router: {node_id} (AS{node.asn})")
            
        elif node.type == NodeType.HOST:
            # Add service host
            if node.services:
                mininet_node = self.net.addHost(
                    node_id,
                    cls=ServiceHost,
                    services=node.services,
                    config=node.config
                )
                logger.debug(f"Added service host: {node_id} with services {node.services}")
            else:
                mininet_node = self.net.addHost(node_id, cls=Host)
                logger.debug(f"Added host: {node_id}")
        else:
            raise ValueError(f"Unknown node type: {node.type}")
        
        self.nodes[node_id] = mininet_node
    
    def _add_link(self, link):
        """Add a link between nodes."""
        src_node = self.nodes.get(link.src)
        dst_node = self.nodes.get(link.dst)
        
        if not src_node or not dst_node:
            logger.error(f"Cannot create link {link.src}->{link.dst}: node not found")
            return
        
        # Convert link parameters
        params = {}
        link_params = link.params
        
        if link_params.bw:
            # Convert bandwidth to Mbps
            bw_str = link_params.bw.lower()
            if 'g' in bw_str:
                params['bw'] = float(bw_str.replace('g', '')) * 1000
            elif 'm' in bw_str:
                params['bw'] = float(bw_str.replace('m', ''))
            elif 'k' in bw_str:
                params['bw'] = float(bw_str.replace('k', '')) / 1000
        
        if link_params.delay:
            params['delay'] = link_params.delay
        
        if link_params.loss:
            params['loss'] = link_params.loss
        
        if link_params.jitter:
            params['jitter'] = link_params.jitter
        
        if link_params.max_queue_size:
            params['max_queue_size'] = link_params.max_queue_size
        
        if link_params.use_htb:
            params['use_htb'] = True
        
        # Create link
        mininet_link = self.net.addLink(src_node, dst_node, cls=TCLink, **params)
        link_id = f"{link.src}-{link.dst}"
        self.links[link_id] = mininet_link
        
        logger.debug(f"Added link: {link_id} with params {params}")
    
    def start(self):
        """Start the network."""
        if not self.net:
            raise RuntimeError("Network not built yet")
        
        logger.info("Starting network...")
        self.net.start()
        
        # Assign IPs to link endpoints
        logger.info("Assigning IP addresses to link endpoints...")
        self.link_ips = assign_node_ips(self.topology)
        
        # Apply IPs to interfaces (skip switches - they work at L2)
        for link_id, ip_config in self.link_ips.items():
            src_node_id = ip_config['src_node']
            dst_node_id = ip_config['dst_node']
            src_ip = ip_config['src']
            dst_ip = ip_config['dst']
            prefix = ip_config['prefix']
            
            # Get node types
            src_node = self.topology.get_node(src_node_id)
            dst_node = self.topology.get_node(dst_node_id)
            
            # Find the link object to get interface references
            if link_id in self.links:
                link = self.links[link_id]
                
                # Get interfaces from the link
                # Mininet link has .intf1 and .intf2
                if hasattr(link, 'intf1') and hasattr(link, 'intf2'):
                    # Only assign IPs to non-switch nodes
                    if src_node and src_node.type.value != 'switch':
                        logger.info(f"  {src_node_id}:{link.intf1.name} = {src_ip}/{prefix}")
                        link.intf1.node.cmd(f'ip addr add {src_ip}/{prefix} dev {link.intf1.name}')
                    
                    if dst_node and dst_node.type.value != 'switch':
                        logger.info(f"  {dst_node_id}:{link.intf2.name} = {dst_ip}/{prefix}")
                        link.intf2.node.cmd(f'ip addr add {dst_ip}/{prefix} dev {link.intf2.name}')
        
        # Build node -> primary IP mapping for routing
        node_primary_ips = {}
        for link_id, ip_config in self.link_ips.items():
            src_node = ip_config['src_node']
            dst_node = ip_config['dst_node']
            
            # Use the first IP we encounter as the "primary" for routing
            if src_node not in node_primary_ips:
                node_primary_ips[src_node] = ip_config['src']
            if dst_node not in node_primary_ips:
                node_primary_ips[dst_node] = ip_config['dst']
        
        # Compute static routes
        logger.info("Computing static routes...")
        self.static_routes = compute_static_routes(self.topology)
        
        # Add static routes to nodes
        logger.info("Adding static routes to nodes...")
        route_count = 0
        for node_id in self.static_routes:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                commands = generate_static_route_commands(node_id, self.static_routes, node_primary_ips)
                logger.info(f"  {node_id}: adding {len(commands)} routes")
                for cmd in commands:
                    logger.info(f"    -> {cmd}")
                    result = node.cmd(cmd)
                    if result:
                        logger.info(f"       Output: {result.strip()}")
                    route_count += 1
        logger.info(f"✓ Added {route_count} total static routes")
        
        # Configure routers
        for node in self.topology.nodes:
            if node.type == NodeType.ROUTER:
                router = self.nodes[node.id]
                if hasattr(router, 'configure'):
                    router.configure()
        
        # Start services
        for node in self.topology.nodes:
            if node.type == NodeType.HOST and node.services:
                host = self.nodes[node.id]
                if hasattr(host, 'start_services'):
                    host.start_services()
        
        logger.info("Network started successfully with static routing")
    
    def stop(self):
        """Stop the network."""
        if self.net:
            logger.info("Stopping network...")
            self.net.stop()
            logger.info("Network stopped")
    
    def get_node(self, node_id: str):
        """Get a Mininet node by ID."""
        return self.nodes.get(node_id)
    
    def get_link(self, src: str, dst: str):
        """Get a link between two nodes."""
        link_id = f"{src}-{dst}"
        link = self.links.get(link_id)
        if not link:
            # Try reverse direction
            link_id = f"{dst}-{src}"
            link = self.links.get(link_id)
        return link
    
    def get_interface(self, node_id: str, peer_id: str) -> Optional[str]:
        """
        Get the interface name on node_id that connects to peer_id.
        
        Args:
            node_id: Source node ID
            peer_id: Peer node ID
            
        Returns:
            Interface name (e.g., 'r1-eth0') or None
        """
        node = self.get_node(node_id)
        peer = self.get_node(peer_id)
        
        if not node or not peer:
            return None
        
        # Find interface connected to peer
        for intf in node.intfList():
            if hasattr(intf, 'link'):
                link = intf.link
                if link:
                    intf1, intf2 = link.intf1, link.intf2
                    if intf1.node == node and intf2.node == peer:
                        return intf1.name
                    if intf2.node == node and intf1.node == peer:
                        return intf2.name
        
        return None
    
    def cli(self):
        """Start Mininet CLI for debugging."""
        if self.net:
            CLI(self.net)
    
    def ping_all(self) -> Dict[str, Any]:
        """Run ping test between all hosts."""
        if not self.net:
            return {"error": "Network not started"}
        
        logger.info("Running ping test...")
        loss = self.net.pingAll()
        
        return {
            "packet_loss_percent": loss,
            "success": loss < 100
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get network status."""
        if not self.net:
            return {"status": "not_started"}
        
        return {
            "status": "running",
            "topology_name": self.topology.name,
            "nodes": {
                "total": len(self.nodes),
                "switches": sum(1 for n in self.topology.nodes if n.type == NodeType.SWITCH),
                "routers": sum(1 for n in self.topology.nodes if n.type == NodeType.ROUTER),
                "hosts": sum(1 for n in self.topology.nodes if n.type == NodeType.HOST),
            },
            "links": len(self.links),
        }


def create_network(topology: Topology, auto_start: bool = True) -> NetworkTopology:
    """
    Convenience function to create and start a network.
    
    Args:
        topology: Topology definition
        auto_start: Whether to start the network immediately
        
    Returns:
        NetworkTopology instance
    """
    setLogLevel('info')
    
    net_topo = NetworkTopology(topology)
    net_topo.build()
    
    if auto_start:
        net_topo.start()
    
    return net_topo

