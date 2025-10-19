"""
Routing utilities for static route calculation.
"""

import networkx as nx
from typing import Dict, List, Tuple, Optional
import ipaddress


def build_topology_graph(topology):
    """
    Build a NetworkX graph from topology.
    
    Args:
        topology: Topology object
        
    Returns:
        NetworkX Graph with nodes and edges
    """
    G = nx.Graph()
    
    # Add nodes
    for node in topology.nodes:
        G.add_node(node.id, type=node.type.value)
    
    # Add edges (links)
    for link in topology.links:
        G.add_edge(link.src, link.dst, link_obj=link)
    
    return G


def compute_static_routes(topology):
    """
    Compute static routes for all nodes using shortest path.
    
    Args:
        topology: Topology object
        
    Returns:
        Dict[node_id, List[Tuple[destination_network, next_hop]]]
    """
    G = build_topology_graph(topology)
    routes = {}
    
    # For each node, compute routes to all other nodes
    for src_node in topology.nodes:
        if src_node.type.value == 'switch':
            # Switches don't need routes (L2 learning)
            continue
            
        node_routes = []
        src_id = src_node.id
        
        # Find shortest path to every other node
        for dst_node in topology.nodes:
            dst_id = dst_node.id
            
            if src_id == dst_id:
                continue  # Skip self
                
            if dst_node.type.value == 'switch':
                continue  # Switches aren't routing destinations
            
            try:
                # Get shortest path
                path = nx.shortest_path(G, src_id, dst_id)
                
                if len(path) > 1:
                    # Next hop is the node after source in the path
                    next_hop_id = path[1]
                    
                    # Skip if next hop is a switch (will forward anyway)
                    next_hop_node = topology.get_node(next_hop_id)
                    if next_hop_node and next_hop_node.type.value == 'switch':
                        if len(path) > 2:
                            next_hop_id = path[2]
                        else:
                            continue
                    
                    # Route format: (destination_node_id, next_hop_node_id)
                    node_routes.append((dst_id, next_hop_id))
                    
            except nx.NetworkXNoPath:
                # No path to destination
                continue
        
        routes[src_id] = node_routes
    
    return routes


def assign_node_ips(topology, base_network='10.0.0.0/16'):
    """
    Assign IP addresses to link endpoints.
    
    - Links with switches use /24 (LAN segments)
    - Router-to-router links use /30 (point-to-point)
    
    Args:
        topology: Topology object
        base_network: Base network to assign from
        
    Returns:
        Dict[link_id, {src_ip, dst_ip, prefix}] - IP assignments per link
    """
    network = ipaddress.ip_network(base_network)
    
    # Separate iterators for different subnet sizes
    subnets_24 = network.subnets(new_prefix=24)  # For switch links
    subnets_30 = network.subnets(new_prefix=30)  # For router links
    
    link_ips = {}
    
    for link in topology.links:
        # Check if either end is a switch
        src_node = topology.get_node(link.src)
        dst_node = topology.get_node(link.dst)
        
        is_switch_link = (
            (src_node and src_node.type.value == 'switch') or
            (dst_node and dst_node.type.value == 'switch')
        )
        
        try:
            if is_switch_link:
                # Use /24 for switch links (LAN segment)
                subnet = next(subnets_24)
                prefix = 24
            else:
                # Use /30 for router-to-router links
                subnet = next(subnets_30)
                prefix = 30
            
            hosts = list(subnet.hosts())
            
            # Assign first usable IP to src, second to dst
            link_id = f"{link.src}-{link.dst}"
            link_ips[link_id] = {
                'src': str(hosts[0]),
                'dst': str(hosts[1]),
                'prefix': prefix,
                'src_node': link.src,
                'dst_node': link.dst
            }
        except StopIteration:
            raise ValueError(f"Ran out of subnets in {base_network}")
    
    return link_ips


def generate_static_route_commands(node_id, routes, node_ips):
    """
    Generate Linux commands to add static routes.
    
    Args:
        node_id: ID of the node to generate routes for
        routes: Dict of routes from compute_static_routes()
        node_ips: Dict of node IPs from assign_node_ips()
        
    Returns:
        List of command strings
    """
    commands = []
    
    if node_id not in routes:
        return commands
    
    for dst_id, next_hop_id in routes[node_id]:
        dst_ip = node_ips.get(dst_id)
        next_hop_ip = node_ips.get(next_hop_id)
        
        if dst_ip and next_hop_ip:
            # Add route: ip route add <dest>/32 via <next_hop>
            cmd = f"ip route add {dst_ip}/32 via {next_hop_ip}"
            commands.append(cmd)
    
    return commands

