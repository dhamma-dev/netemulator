"""Control plane impairments (BGP/OSPF events)."""

import logging
import time
from typing import Dict, Any
from ..dataplane.router import FRRRouter

logger = logging.getLogger(__name__)


class RoutingImpairment:
    """Manages routing protocol impairments."""

    def __init__(self, node):
        """
        Initialize routing impairment manager.
        
        Args:
            node: Router node
        """
        self.node = node
        
    def bgp_flap(self, neighbor_ip: str = None, down_seconds: int = 60) -> bool:
        """
        Trigger a BGP session flap.
        
        Args:
            neighbor_ip: Specific neighbor to flap (None for all)
            down_seconds: How long to keep session down
            
        Returns:
            True if successful
        """
        try:
            if not isinstance(self.node, FRRRouter):
                logger.error(f"Node {self.node.name} is not a FRR router")
                return False
            
            # Shutdown BGP neighbor(s)
            if neighbor_ip:
                cmd = f"vtysh -c 'conf t' -c 'router bgp {self.node.asn}' -c 'neighbor {neighbor_ip} shutdown'"
                self.node.cmd(cmd)
                logger.info(f"Shutdown BGP neighbor {neighbor_ip} on {self.node.name}")
            else:
                # Shutdown all BGP neighbors
                cmd = f"vtysh -c 'conf t' -c 'router bgp {self.node.asn}' -c 'bgp shutdown'"
                self.node.cmd(cmd)
                logger.info(f"Shutdown all BGP neighbors on {self.node.name}")
            
            # Wait for specified duration
            time.sleep(down_seconds)
            
            # Bring BGP back up
            if neighbor_ip:
                cmd = f"vtysh -c 'conf t' -c 'router bgp {self.node.asn}' -c 'no neighbor {neighbor_ip} shutdown'"
                self.node.cmd(cmd)
                logger.info(f"Re-enabled BGP neighbor {neighbor_ip} on {self.node.name}")
            else:
                cmd = f"vtysh -c 'conf t' -c 'router bgp {self.node.asn}' -c 'no bgp shutdown'"
                self.node.cmd(cmd)
                logger.info(f"Re-enabled all BGP neighbors on {self.node.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"BGP flap failed: {e}")
            return False
    
    def bgp_withdraw_route(self, prefix: str) -> bool:
        """
        Withdraw a BGP route.
        
        Args:
            prefix: IP prefix to withdraw (e.g., '10.0.0.0/24')
            
        Returns:
            True if successful
        """
        try:
            if not isinstance(self.node, FRRRouter):
                logger.error(f"Node {self.node.name} is not a FRR router")
                return False
            
            # Add a route filter to deny the prefix
            cmd = (f"vtysh -c 'conf t' -c 'router bgp {self.node.asn}' "
                   f"-c 'address-family ipv4 unicast' "
                   f"-c 'network {prefix} route-map DENY'")
            self.node.cmd(cmd)
            
            logger.info(f"Withdrew BGP route {prefix} on {self.node.name}")
            return True
            
        except Exception as e:
            logger.error(f"BGP route withdrawal failed: {e}")
            return False
    
    def ospf_cost_change(self, interface: str, cost: int) -> bool:
        """
        Change OSPF cost on an interface.
        
        Args:
            interface: Interface name
            cost: New OSPF cost
            
        Returns:
            True if successful
        """
        try:
            if not isinstance(self.node, FRRRouter):
                logger.error(f"Node {self.node.name} is not a FRR router")
                return False
            
            cmd = (f"vtysh -c 'conf t' -c 'interface {interface}' "
                   f"-c 'ip ospf cost {cost}'")
            self.node.cmd(cmd)
            
            logger.info(f"Set OSPF cost to {cost} on {self.node.name}:{interface}")
            return True
            
        except Exception as e:
            logger.error(f"OSPF cost change failed: {e}")
            return False
    
    def interface_flap(self, interface: str, down_seconds: int = 30) -> bool:
        """
        Flap an interface (down/up).
        
        Args:
            interface: Interface name
            down_seconds: How long to keep interface down
            
        Returns:
            True if successful
        """
        try:
            # Bring interface down
            self.node.cmd(f"ip link set {interface} down")
            logger.info(f"Interface {interface} down on {self.node.name}")
            
            # Wait
            time.sleep(down_seconds)
            
            # Bring interface up
            self.node.cmd(f"ip link set {interface} up")
            logger.info(f"Interface {interface} up on {self.node.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Interface flap failed: {e}")
            return False

