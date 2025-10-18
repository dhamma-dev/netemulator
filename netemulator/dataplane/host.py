"""Service host node implementation."""

import logging
from typing import List, Dict, Any
from mininet.node import Host

logger = logging.getLogger(__name__)


class ServiceHost(Host):
    """A Mininet host that runs network services."""

    def __init__(self, name: str, services: List[str] = None, 
                 config: Dict[str, Any] = None, **params):
        """
        Initialize service host.
        
        Args:
            name: Host name
            services: List of services to run (e.g., ['dns', 'http3'])
            config: Service-specific configuration
            **params: Additional Mininet node parameters
        """
        super().__init__(name, **params)
        self.services = services or []
        self.service_config = config or {}
        self.service_processes = []
        
    def start_services(self):
        """Start all configured services."""
        for service in self.services:
            self.start_service(service)
    
    def start_service(self, service: str):
        """Start a specific service."""
        logger.info(f"Host {self.name}: Starting service {service}")
        
        if service == "dns":
            self._start_dns()
        elif service in ["http", "https", "http2", "http3"]:
            self._start_http(service)
        elif service == "tcp_echo":
            self._start_tcp_echo()
        elif service == "udp_echo":
            self._start_udp_echo()
        elif service == "cdn":
            self._start_cdn()
        else:
            logger.warning(f"Host {self.name}: Unknown service {service}")
    
    def _start_dns(self):
        """Start DNS server."""
        # Simplified - would run actual DNS server (dnsmasq, bind, etc.)
        port = self.service_config.get('dns_port', 53)
        
        # Start simple DNS responder using Python
        dns_script = f"""
import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', {port}))
print('DNS server listening on port {port}')

while True:
    data, addr = s.recvfrom(512)
    # Simple response - just echo query with NXDOMAIN
    response = data[:2]  # Transaction ID
    response += b'\\x81\\x83'  # Flags: response, NXDOMAIN
    response += data[4:6]  # Questions
    response += b'\\x00\\x00\\x00\\x00\\x00\\x00'  # Answers, Authority, Additional
    response += data[12:]  # Original question
    s.sendto(response, addr)
"""
        
        # Write and run DNS script in background
        self.cmd(f'python3 -c "{dns_script}" > /tmp/{self.name}_dns.log 2>&1 &')
        logger.info(f"Host {self.name}: DNS server started on port {port}")
    
    def _start_http(self, protocol: str):
        """Start HTTP server."""
        port_map = {
            "http": 80,
            "https": 443,
            "http2": 8080,
            "http3": 8443,
        }
        
        port = self.service_config.get(f'{protocol}_port', port_map.get(protocol, 8000))
        
        # Start Python HTTP server
        if protocol == "http":
            self.cmd(f'python3 -m http.server {port} > /tmp/{self.name}_http.log 2>&1 &')
            logger.info(f"Host {self.name}: HTTP server started on port {port}")
        elif protocol == "https":
            # Would use proper HTTPS server with certificates
            logger.info(f"Host {self.name}: HTTPS server (placeholder) on port {port}")
        else:
            logger.info(f"Host {self.name}: {protocol.upper()} server (placeholder) on port {port}")
    
    def _start_tcp_echo(self):
        """Start TCP echo server."""
        port = self.service_config.get('tcp_echo_port', 7)
        
        echo_script = f"""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', {port}))
s.listen(5)
print('TCP echo server listening on port {port}')

while True:
    conn, addr = s.accept()
    data = conn.recv(4096)
    if data:
        conn.sendall(data)
    conn.close()
"""
        
        self.cmd(f'python3 -c "{echo_script}" > /tmp/{self.name}_tcp_echo.log 2>&1 &')
        logger.info(f"Host {self.name}: TCP echo server started on port {port}")
    
    def _start_udp_echo(self):
        """Start UDP echo server."""
        port = self.service_config.get('udp_echo_port', 7)
        
        echo_script = f"""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', {port}))
print('UDP echo server listening on port {port}')

while True:
    data, addr = s.recvfrom(4096)
    s.sendto(data, addr)
"""
        
        self.cmd(f'python3 -c "{echo_script}" > /tmp/{self.name}_udp_echo.log 2>&1 &')
        logger.info(f"Host {self.name}: UDP echo server started on port {port}")
    
    def _start_cdn(self):
        """Start CDN-like service."""
        # CDN would be a more sophisticated HTTP server with caching
        self._start_http("http")
        logger.info(f"Host {self.name}: CDN service started")
    
    def stop_services(self):
        """Stop all running services."""
        # Kill all background processes
        self.cmd('pkill -P $$')
        logger.info(f"Host {self.name}: Stopped all services")
    
    def terminate(self):
        """Terminate the host."""
        self.stop_services()
        super().terminate()

