"""
Network Emulation (netem) impairment implementation using tc.
"""

import logging
import subprocess
from typing import Dict, Any, Optional, List
from ..models.scenario import NetemSpec

logger = logging.getLogger(__name__)


class NetemImpairment:
    """Manages tc netem-based network impairments."""

    def __init__(self, node, interface: str):
        """
        Initialize netem impairment manager.
        
        Args:
            node: Mininet node
            interface: Interface name to apply impairments to
        """
        self.node = node
        self.interface = interface
        self.active_rules = []
        
    def apply(self, spec: NetemSpec) -> bool:
        """
        Apply netem impairments.
        
        Args:
            spec: Netem specification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear any existing netem on this interface
            self.clear()
            
            # Build tc netem command
            args = spec.to_tc_command()
            if not args:
                logger.warning(f"No netem parameters specified for {self.interface}")
                return True
            
            # Apply netem
            cmd = f"tc qdisc add dev {self.interface} root netem {' '.join(args)}"
            result = self.node.cmd(cmd)
            
            logger.info(f"Applied netem to {self.node.name}:{self.interface}: {' '.join(args)}")
            
            self.active_rules.append({
                "type": "netem",
                "spec": spec,
                "command": cmd
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply netem to {self.node.name}:{self.interface}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all netem impairments from the interface.
        
        Returns:
            True if successful
        """
        try:
            # Delete root qdisc (removes netem)
            cmd = f"tc qdisc del dev {self.interface} root"
            self.node.cmd(cmd)
            
            logger.debug(f"Cleared netem from {self.node.name}:{self.interface}")
            self.active_rules = []
            return True
            
        except Exception as e:
            # It's okay if there was no qdisc to delete
            logger.debug(f"No netem to clear on {self.node.name}:{self.interface}: {e}")
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current netem status.
        
        Returns:
            Dictionary with current qdisc information
        """
        try:
            cmd = f"tc qdisc show dev {self.interface}"
            output = self.node.cmd(cmd)
            
            return {
                "interface": self.interface,
                "qdisc_output": output,
                "active_rules": len(self.active_rules),
            }
        except Exception as e:
            logger.error(f"Failed to get netem status: {e}")
            return {"error": str(e)}


class ImpairmentEngine:
    """Central engine for managing network impairments across the topology."""

    def __init__(self, network_topology):
        """
        Initialize impairment engine.
        
        Args:
            network_topology: NetworkTopology instance
        """
        self.network = network_topology
        self.impairments: Dict[str, NetemImpairment] = {}
        
    def apply_to_link(self, src: str, dst: str, spec: NetemSpec) -> bool:
        """
        Apply impairments to a link.
        
        Args:
            src: Source node ID
            dst: Destination node ID
            spec: Netem specification
            
        Returns:
            True if successful
        """
        # Get interface on src node that connects to dst
        interface = self.network.get_interface(src, dst)
        
        if not interface:
            logger.error(f"Could not find interface on {src} connecting to {dst}")
            return False
        
        # Get or create impairment manager
        key = f"{src}:{interface}"
        if key not in self.impairments:
            node = self.network.get_node(src)
            self.impairments[key] = NetemImpairment(node, interface)
        
        # Apply impairment
        return self.impairments[key].apply(spec)
    
    def apply_to_path(self, nodes: List[str], spec: NetemSpec) -> bool:
        """
        Apply impairments to all links in a path.
        
        Args:
            nodes: List of node IDs forming the path
            spec: Netem specification
            
        Returns:
            True if all applications successful
        """
        success = True
        for i in range(len(nodes) - 1):
            src, dst = nodes[i], nodes[i + 1]
            if not self.apply_to_link(src, dst, spec):
                success = False
                logger.error(f"Failed to apply impairment to link {src}->{dst}")
        
        return success
    
    def apply_to_node(self, node_id: str, spec: NetemSpec) -> bool:
        """
        Apply impairments to all interfaces on a node.
        
        Args:
            node_id: Node ID
            spec: Netem specification
            
        Returns:
            True if successful
        """
        node = self.network.get_node(node_id)
        if not node:
            logger.error(f"Node {node_id} not found")
            return False
        
        success = True
        for intf in node.intfList():
            if intf.name != 'lo':
                key = f"{node_id}:{intf.name}"
                if key not in self.impairments:
                    self.impairments[key] = NetemImpairment(node, intf.name)
                
                if not self.impairments[key].apply(spec):
                    success = False
        
        return success
    
    def clear_link(self, src: str, dst: str) -> bool:
        """Clear impairments from a link."""
        interface = self.network.get_interface(src, dst)
        if not interface:
            return False
        
        key = f"{src}:{interface}"
        if key in self.impairments:
            return self.impairments[key].clear()
        
        return True
    
    def clear_path(self, nodes: List[str]) -> bool:
        """Clear impairments from all links in a path."""
        success = True
        for i in range(len(nodes) - 1):
            src, dst = nodes[i], nodes[i + 1]
            if not self.clear_link(src, dst):
                success = False
        return success
    
    def clear_node(self, node_id: str) -> bool:
        """Clear impairments from all interfaces on a node."""
        node = self.network.get_node(node_id)
        if not node:
            return False
        
        success = True
        for intf in node.intfList():
            if intf.name != 'lo':
                key = f"{node_id}:{intf.name}"
                if key in self.impairments:
                    if not self.impairments[key].clear():
                        success = False
        
        return success
    
    def clear_all(self) -> bool:
        """Clear all impairments."""
        success = True
        for impairment in self.impairments.values():
            if not impairment.clear():
                success = False
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all impairments."""
        return {
            key: imp.get_status()
            for key, imp in self.impairments.items()
        }


def apply_netem(node, interface: str, delay: str = None, loss: float = None,
                jitter: str = None, rate: str = None) -> bool:
    """
    Convenience function to apply netem impairments.
    
    Args:
        node: Mininet node
        interface: Interface name
        delay: Delay (e.g., '50ms')
        loss: Loss percentage (0-100)
        jitter: Jitter (e.g., '10ms')
        rate: Rate limit (e.g., '1mbit')
        
    Returns:
        True if successful
    """
    spec = NetemSpec(
        delay=delay,
        loss=f"{loss}%" if loss is not None else None,
        delay_variation=jitter,
        rate=rate
    )
    
    imp = NetemImpairment(node, interface)
    return imp.apply(spec)

