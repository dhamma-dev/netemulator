"""FRRouting router node implementation."""

import logging
import os
import tempfile
from typing import List, Dict, Any
from mininet.node import Node

logger = logging.getLogger(__name__)


class FRRRouter(Node):
    """A Mininet node running FRRouting daemons."""

    def __init__(self, name: str, asn: int = None, daemons: List[str] = None, 
                 config: Dict[str, Any] = None, **params):
        """
        Initialize FRR router.
        
        Args:
            name: Router name
            asn: Autonomous System Number
            daemons: List of FRR daemons to run (e.g., ['ospf', 'bgp'])
            config: Additional configuration
            **params: Additional Mininet node parameters
        """
        super().__init__(name, **params)
        self.asn = asn or 65000 + hash(name) % 1000
        self.daemons = daemons or []
        self.router_config = config or {}
        self.config_dir = None
        self.frr_processes = []
        
    def config(self, **params):
        """Configure the router."""
        super().config(**params)
        
        # Enable IP forwarding
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('sysctl -w net.ipv6.conf.all.forwarding=1')
        
        # Disable ICMP redirects
        self.cmd('sysctl -w net.ipv4.conf.all.send_redirects=0')
        
    def configure(self):
        """Configure and start FRR daemons."""
        if not self.daemons:
            logger.debug(f"Router {self.name}: No daemons configured")
            return
        
        # Create configuration directory
        self.config_dir = tempfile.mkdtemp(prefix=f"frr_{self.name}_")
        logger.info(f"Router {self.name}: Config dir: {self.config_dir}")
        
        # Generate router ID from first interface IP or use synthetic
        router_id = f"192.0.2.{self.asn % 256}"
        
        # Write FRR configuration
        config_lines = [
            "frr version 8.0",
            "frr defaults traditional",
            f"hostname {self.name}",
            "log file /tmp/frr.log",
            "log syslog informational",
            "no ipv6 forwarding",
            "service integrated-vtysh-config",
            "!",
        ]
        
        # OSPF configuration
        if "ospf" in self.daemons:
            config_lines.extend([
                "router ospf",
                f"  ospf router-id {router_id}",
                "  redistribute connected",
            ])
            # Add all interfaces to OSPF area 0
            for intf in self.intfList():
                if intf.name != 'lo':
                    config_lines.append(f"  network {intf.IP()}/32 area 0.0.0.0")
            config_lines.append("!")
        
        # BGP configuration
        if "bgp" in self.daemons:
            config_lines.extend([
                f"router bgp {self.asn}",
                f"  bgp router-id {router_id}",
                "  bgp log-neighbor-changes",
                "  no bgp ebgp-requires-policy",
                "  no bgp default ipv4-unicast",
                "  !",
                "  address-family ipv4 unicast",
                "    redistribute connected",
                "  exit-address-family",
                "!",
            ])
        
        config_lines.append("line vty\n!")
        
        frr_conf = "\n".join(config_lines)
        config_file = os.path.join(self.config_dir, "frr.conf")
        
        with open(config_file, 'w') as f:
            f.write(frr_conf)
        
        logger.debug(f"Router {self.name}: Wrote FRR config to {config_file}")
        
        # Write daemons file
        daemons_file = os.path.join(self.config_dir, "daemons")
        daemon_config = []
        for daemon in ['zebra', 'bgpd', 'ospfd', 'ospf6d', 'ripd', 'ripngd', 'isisd']:
            if daemon == 'zebra' or daemon[:-1] in self.daemons:
                daemon_config.append(f"{daemon}=yes")
            else:
                daemon_config.append(f"{daemon}=no")
        
        with open(daemons_file, 'w') as f:
            f.write("\n".join(daemon_config) + "\n")
        
        # Create vtysh.conf
        vtysh_conf = os.path.join(self.config_dir, "vtysh.conf")
        with open(vtysh_conf, 'w') as f:
            f.write("service integrated-vtysh-config\n")
        
        # Start FRR daemons (simplified - in production use proper FRR start)
        # Note: This is a simplified version. Production would use /usr/lib/frr scripts
        logger.info(f"Router {self.name}: FRR configured with daemons: {self.daemons}")
        
    def start_daemon(self, daemon: str):
        """Start a specific FRR daemon."""
        # Simplified daemon start - production would properly manage FRR
        logger.info(f"Router {self.name}: Starting daemon {daemon}")
        # In real implementation, would exec actual FRR daemon binaries
        
    def stop_daemons(self):
        """Stop all FRR daemons."""
        for proc in self.frr_processes:
            try:
                proc.kill()
            except:
                pass
        self.frr_processes = []
        
    def terminate(self):
        """Terminate the router."""
        self.stop_daemons()
        super().terminate()
        
    def add_bgp_neighbor(self, neighbor_ip: str, neighbor_asn: int):
        """Add a BGP neighbor."""
        if "bgp" not in self.daemons:
            logger.warning(f"Router {self.name}: BGP not enabled")
            return
        
        # Use vtysh to configure
        cmd = f"""
        vtysh -c 'conf t' -c 'router bgp {self.asn}' \\
              -c 'neighbor {neighbor_ip} remote-as {neighbor_asn}' \\
              -c 'address-family ipv4 unicast' \\
              -c 'neighbor {neighbor_ip} activate' \\
              -c 'exit-address-family'
        """
        result = self.cmd(cmd)
        logger.info(f"Router {self.name}: Added BGP neighbor {neighbor_ip} AS{neighbor_asn}")
        return result
    
    def show_bgp_summary(self) -> str:
        """Show BGP summary."""
        return self.cmd("vtysh -c 'show ip bgp summary'")
    
    def show_routes(self) -> str:
        """Show routing table."""
        return self.cmd("ip route show")
    
    def show_ospf_neighbors(self) -> str:
        """Show OSPF neighbors."""
        return self.cmd("vtysh -c 'show ip ospf neighbor'")

