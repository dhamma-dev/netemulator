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


def assign_node_ips(topology, base_network='10.0.0.0/24'):
    """
    Assign IP addresses to nodes.
    
    Simple scheme: Sequential IPs starting from base_network.
    
    Args:
        topology: Topology object
        base_network: Base network to assign from
        
    Returns:
        Dict[node_id, ip_address_string]
    """
    network = ipaddress.ip_network(base_network)
    hosts = list(network.hosts())
    
    node_ips = {}
    ip_index = 0
    
    for node in topology.nodes:
        if node.type.value != 'switch':  # Switches don't need IPs
            node_ips[node.id] = str(hosts[ip_index])
            ip_index += 1
            
            if ip_index >= len(hosts):
                raise ValueError(f"Ran out of IPs in {base_network}")
    
    return node_ips


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

