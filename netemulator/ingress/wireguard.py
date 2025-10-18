"""
WireGuard VPN Manager - Manages WireGuard connections for external monitoring points.
"""

import logging
import subprocess
import ipaddress
from typing import Dict, Optional, Any
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import base64

logger = logging.getLogger(__name__)


class WireGuardManager:
    """Manages WireGuard VPN for external MP connectivity."""

    def __init__(self, interface: str = "wg0", subnet: str = "10.100.0.0/24",
                 listen_port: int = 51820):
        """
        Initialize WireGuard manager.
        
        Args:
            interface: WireGuard interface name
            subnet: VPN subnet (e.g., '10.100.0.0/24')
            listen_port: UDP port for WireGuard
        """
        self.interface = interface
        self.subnet = ipaddress.ip_network(subnet)
        self.listen_port = listen_port
        
        self.server_private_key: Optional[str] = None
        self.server_public_key: Optional[str] = None
        self.next_ip_index = 2  # .1 is server, start clients at .2
        
        self.peers: Dict[str, Dict[str, Any]] = {}
        
    def generate_keypair(self) -> tuple[str, str]:
        """
        Generate a WireGuard keypair.
        
        Returns:
            Tuple of (private_key, public_key) as base64 strings
        """
        # Generate private key
        private_key = x25519.X25519PrivateKey.generate()
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize to base64
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_b64 = base64.b64encode(private_bytes).decode('ascii')
        
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_b64 = base64.b64encode(public_bytes).decode('ascii')
        
        return private_b64, public_b64
    
    def initialize_server(self) -> bool:
        """
        Initialize WireGuard server.
        
        Returns:
            True if successful
        """
        try:
            # Generate server keypair
            self.server_private_key, self.server_public_key = self.generate_keypair()
            
            logger.info(f"Generated WireGuard server keys")
            logger.info(f"Server public key: {self.server_public_key}")
            
            # Create WireGuard config
            server_ip = list(self.subnet.hosts())[0]
            
            config = f"""[Interface]
PrivateKey = {self.server_private_key}
Address = {server_ip}/{self.subnet.prefixlen}
ListenPort = {self.listen_port}
SaveConfig = false

# Enable IP forwarding
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i {self.interface} -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

PostDown = iptables -D FORWARD -i {self.interface} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
"""
            
            # Write config
            config_path = f"/etc/wireguard/{self.interface}.conf"
            logger.info(f"WireGuard server config (would write to {config_path}):")
            logger.info(config)
            
            # In production, would actually write and start WireGuard
            # subprocess.run(['wg-quick', 'up', self.interface], check=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WireGuard server: {e}")
            return False
    
    def onboard_peer(self, mp_id: str, attach_to: str) -> Dict[str, Any]:
        """
        Onboard a new monitoring point peer.
        
        Args:
            mp_id: Monitoring point identifier
            attach_to: Node ID to attach MP to
            
        Returns:
            Peer configuration including WireGuard config
        """
        if mp_id in self.peers:
            raise ValueError(f"MP {mp_id} already onboarded")
        
        # Generate peer keypair
        peer_private_key, peer_public_key = self.generate_keypair()
        
        # Allocate IP
        peer_ip = list(self.subnet.hosts())[self.next_ip_index]
        self.next_ip_index += 1
        
        # Store peer info
        self.peers[mp_id] = {
            "public_key": peer_public_key,
            "ip": str(peer_ip),
            "attach_to": attach_to,
            "allowed_ips": f"{peer_ip}/32"
        }
        
        # Generate peer config for MP
        server_ip = list(self.subnet.hosts())[0]
        peer_config = f"""[Interface]
PrivateKey = {peer_private_key}
Address = {peer_ip}/{self.subnet.prefixlen}
DNS = 8.8.8.8

[Peer]
PublicKey = {self.server_public_key}
Endpoint = <SERVER_PUBLIC_IP>:{self.listen_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        
        # Add peer to server config
        self._add_peer_to_server(peer_public_key, f"{peer_ip}/32")
        
        logger.info(f"Onboarded MP {mp_id} with IP {peer_ip}, attached to {attach_to}")
        
        return {
            "mp_id": mp_id,
            "ip": str(peer_ip),
            "attach_to": attach_to,
            "config": peer_config,
            "public_key": peer_public_key
        }
    
    def _add_peer_to_server(self, peer_public_key: str, allowed_ips: str):
        """Add peer to server configuration."""
        peer_config = f"""
# Peer
[Peer]
PublicKey = {peer_public_key}
AllowedIPs = {allowed_ips}
"""
        logger.info(f"Add peer config: {peer_config}")
        
        # In production, would run: wg set {interface} peer {public_key} allowed-ips {allowed_ips}
    
    def remove_peer(self, mp_id: str) -> bool:
        """
        Remove a monitoring point peer.
        
        Args:
            mp_id: Monitoring point identifier
            
        Returns:
            True if successful
        """
        if mp_id not in self.peers:
            logger.warning(f"MP {mp_id} not found")
            return False
        
        peer = self.peers[mp_id]
        
        # Remove from server
        # subprocess.run(['wg', 'set', self.interface, 'peer', peer['public_key'], 'remove'])
        
        del self.peers[mp_id]
        logger.info(f"Removed MP {mp_id}")
        
        return True
    
    def get_peer_status(self, mp_id: str) -> Optional[Dict[str, Any]]:
        """Get peer status."""
        if mp_id not in self.peers:
            return None
        
        peer = self.peers[mp_id]
        
        # In production, would get actual WireGuard stats
        return {
            "mp_id": mp_id,
            "ip": peer["ip"],
            "attach_to": peer["attach_to"],
            "connected": True,  # Would check actual connection status
            "last_handshake": None,
            "rx_bytes": 0,
            "tx_bytes": 0
        }
    
    def list_peers(self) -> Dict[str, Dict[str, Any]]:
        """List all peers."""
        return {
            mp_id: self.get_peer_status(mp_id)
            for mp_id in self.peers.keys()
        }
    
    def shutdown(self):
        """Shutdown WireGuard server."""
        logger.info("Shutting down WireGuard server")
        # In production: subprocess.run(['wg-quick', 'down', self.interface])


class MPIngressManager:
    """Manages external monitoring point ingress across multiple VPN types."""

    def __init__(self, topology_name: str):
        """
        Initialize MP ingress manager.
        
        Args:
            topology_name: Associated topology name
        """
        self.topology_name = topology_name
        self.wireguard: Optional[WireGuardManager] = None
        self.vpn_type = "wireguard"  # Default
        
    def initialize(self, vpn_type: str = "wireguard", **kwargs):
        """
        Initialize VPN infrastructure.
        
        Args:
            vpn_type: VPN type (wireguard, openvpn, gre)
            **kwargs: VPN-specific parameters
        """
        self.vpn_type = vpn_type
        
        if vpn_type == "wireguard":
            self.wireguard = WireGuardManager(**kwargs)
            self.wireguard.initialize_server()
        else:
            raise NotImplementedError(f"VPN type {vpn_type} not yet implemented")
        
        logger.info(f"Initialized {vpn_type} ingress for topology {self.topology_name}")
    
    def onboard_mp(self, mp_id: str, attach_to: str) -> Dict[str, Any]:
        """
        Onboard a monitoring point.
        
        Args:
            mp_id: MP identifier
            attach_to: Node to attach to
            
        Returns:
            MP configuration
        """
        if self.vpn_type == "wireguard" and self.wireguard:
            return self.wireguard.onboard_peer(mp_id, attach_to)
        else:
            raise RuntimeError("VPN not initialized")
    
    def remove_mp(self, mp_id: str) -> bool:
        """Remove a monitoring point."""
        if self.vpn_type == "wireguard" and self.wireguard:
            return self.wireguard.remove_peer(mp_id)
        return False
    
    def get_mp_status(self, mp_id: str) -> Optional[Dict[str, Any]]:
        """Get MP status."""
        if self.vpn_type == "wireguard" and self.wireguard:
            return self.wireguard.get_peer_status(mp_id)
        return None
    
    def list_mps(self) -> Dict[str, Dict[str, Any]]:
        """List all monitoring points."""
        if self.vpn_type == "wireguard" and self.wireguard:
            return self.wireguard.list_peers()
        return {}

