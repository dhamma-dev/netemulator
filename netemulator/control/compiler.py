"""
Topology Compiler - Converts YAML topology definitions to Mininet networks.
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from ..models.topology import Topology, NodeType
from ..models.scenario import ScenarioSet


class TopologyCompiler:
    """Compiles topology YAML to executable network configurations."""

    def __init__(self):
        self.topology: Optional[Topology] = None
        self.scenarios: Optional[ScenarioSet] = None

    def load_from_yaml(self, yaml_path: str) -> Topology:
        """Load and parse topology from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return self.load_from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> Topology:
        """Load and parse topology from dictionary."""
        # Extract topology
        if "topology" not in data:
            raise ValueError("Missing 'topology' key in configuration")
        
        topo_data = data["topology"]
        self.topology = Topology(**topo_data)
        
        # Extract scenarios if present
        if "scenarios" in data:
            self.scenarios = ScenarioSet(**data["scenarios"])
        
        return self.topology

    def validate(self) -> Dict[str, Any]:
        """
        Validate topology for correctness and feasibility.
        
        Returns:
            Dict with validation results: {"valid": bool, "errors": [], "warnings": []}
        """
        if not self.topology:
            return {"valid": False, "errors": ["No topology loaded"], "warnings": []}
        
        errors = []
        warnings = []
        
        # Check for duplicate node IDs
        node_ids = [node.id for node in self.topology.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Duplicate node IDs found")
        
        # Validate link endpoints
        node_id_set = set(node_ids)
        for link in self.topology.links:
            if link.src not in node_id_set:
                errors.append(f"Link source '{link.src}' not found in nodes")
            if link.dst not in node_id_set:
                errors.append(f"Link destination '{link.dst}' not found in nodes")
        
        # Check for isolated nodes
        linked_nodes = set()
        for link in self.topology.links:
            linked_nodes.add(link.src)
            linked_nodes.add(link.dst)
        
        isolated = node_id_set - linked_nodes
        if isolated:
            warnings.append(f"Isolated nodes with no links: {isolated}")
        
        # Validate router configurations
        for node in self.topology.nodes:
            if node.type == NodeType.ROUTER:
                if node.daemons and "bgp" in node.daemons and not node.asn:
                    errors.append(f"Router {node.id} has BGP daemon but no ASN")
        
        # Validate scenario targets if scenarios loaded
        if self.scenarios:
            for scenario in self.scenarios.persistent + self.scenarios.transient:
                try:
                    target = scenario.parse_target()
                    if target["type"] == "node":
                        if target["id"] not in node_id_set:
                            errors.append(f"Scenario {scenario.id} targets unknown node {target['id']}")
                    elif target["type"] == "link":
                        # Validate link exists
                        link_found = False
                        for link in self.topology.links:
                            if link.src == target["src"] and link.dst == target["dst"]:
                                link_found = True
                                break
                        if not link_found:
                            errors.append(f"Scenario {scenario.id} targets unknown link {target['src']}->{target['dst']}")
                except Exception as e:
                    errors.append(f"Scenario {scenario.id} has invalid target: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def generate_frr_config(self, node_id: str) -> str:
        """Generate FRRouting configuration for a router node."""
        if not self.topology:
            raise ValueError("No topology loaded")
        
        node = self.topology.get_node(node_id)
        if not node or node.type != NodeType.ROUTER:
            raise ValueError(f"Node {node_id} is not a router")
        
        config_lines = [
            "frr version 8.0",
            "frr defaults traditional",
            f"hostname {node_id}",
            "log syslog informational",
            "no ipv6 forwarding",
            "service integrated-vtysh-config",
            "!",
        ]
        
        # Router ID (use ASN or generate)
        router_id = f"192.0.2.{node.asn % 256 if node.asn else 1}"
        
        # OSPF configuration
        if "ospf" in node.daemons:
            config_lines.extend([
                "router ospf",
                f"  ospf router-id {router_id}",
                "  network 0.0.0.0/0 area 0.0.0.0",
                "!",
            ])
        
        # BGP configuration
        if "bgp" in node.daemons and node.asn:
            config_lines.extend([
                f"router bgp {node.asn}",
                f"  bgp router-id {router_id}",
                "  bgp log-neighbor-changes",
                "  no bgp ebgp-requires-policy",
                "!",
            ])
        
        config_lines.append("line vty\n!")
        
        return "\n".join(config_lines)

    def estimate_resources(self) -> Dict[str, Any]:
        """
        Estimate resource requirements for the topology.
        
        Returns:
            Dict with estimated CPU, memory, and network requirements
        """
        if not self.topology:
            raise ValueError("No topology loaded")
        
        # Rough estimates
        cpu_per_node = {
            NodeType.SWITCH: 0.1,
            NodeType.ROUTER: 0.5,
            NodeType.HOST: 0.2,
        }
        
        mem_per_node = {
            NodeType.SWITCH: 32,    # MB
            NodeType.ROUTER: 128,
            NodeType.HOST: 64,
        }
        
        total_cpu = sum(cpu_per_node.get(node.type, 0.2) for node in self.topology.nodes)
        total_mem = sum(mem_per_node.get(node.type, 64) for node in self.topology.nodes)
        
        # Add overhead for links and services
        total_cpu += len(self.topology.links) * 0.05
        
        # Count services
        service_count = sum(len(node.services) for node in self.topology.nodes)
        total_cpu += service_count * 0.3
        total_mem += service_count * 128
        
        return {
            "estimated_cpu_cores": round(total_cpu, 2),
            "estimated_memory_mb": int(total_mem),
            "node_count": len(self.topology.nodes),
            "link_count": len(self.topology.links),
            "service_count": service_count,
            "router_count": sum(1 for n in self.topology.nodes if n.type == NodeType.ROUTER),
        }

    def to_mininet_dict(self) -> Dict[str, Any]:
        """
        Convert topology to Mininet-compatible dictionary format.
        
        Returns:
            Dictionary that can be used by Mininet topology builder
        """
        if not self.topology:
            raise ValueError("No topology loaded")
        
        return {
            "name": self.topology.name,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type.value,
                    "asn": node.asn,
                    "daemons": node.daemons,
                    "services": node.services,
                    "config": node.config,
                }
                for node in self.topology.nodes
            ],
            "links": [
                {
                    "src": link.src,
                    "dst": link.dst,
                    "params": link.params.to_dict(),
                }
                for link in self.topology.links
            ],
            "mp_ingress": self.topology.mp_ingress.dict() if self.topology.mp_ingress else None,
        }


def compile_topology(yaml_source: str) -> Topology:
    """
    Convenience function to compile a topology from YAML.
    
    Args:
        yaml_source: Path to YAML file or YAML string
        
    Returns:
        Compiled Topology object
    """
    compiler = TopologyCompiler()
    
    # Check if it's a file path
    if Path(yaml_source).exists():
        return compiler.load_from_yaml(yaml_source)
    else:
        # Try parsing as YAML string
        data = yaml.safe_load(yaml_source)
        return compiler.load_from_dict(data)

