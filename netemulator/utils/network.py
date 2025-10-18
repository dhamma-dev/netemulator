"""Network utility functions."""

import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def parse_bandwidth(bw_str: str) -> float:
    """
    Parse bandwidth string to Mbps.
    
    Args:
        bw_str: Bandwidth string (e.g., '1g', '100m', '10k')
        
    Returns:
        Bandwidth in Mbps
    """
    bw_str = bw_str.lower().strip()
    
    if 'g' in bw_str:
        return float(bw_str.replace('g', '')) * 1000
    elif 'm' in bw_str:
        return float(bw_str.replace('m', ''))
    elif 'k' in bw_str:
        return float(bw_str.replace('k', '')) / 1000
    else:
        # Assume Mbps
        return float(bw_str)


def parse_delay(delay_str: str) -> float:
    """
    Parse delay string to milliseconds.
    
    Args:
        delay_str: Delay string (e.g., '50ms', '1s', '100us')
        
    Returns:
        Delay in milliseconds
    """
    delay_str = delay_str.lower().strip()
    
    if 'ms' in delay_str:
        return float(delay_str.replace('ms', ''))
    elif 's' in delay_str:
        return float(delay_str.replace('s', '')) * 1000
    elif 'us' in delay_str:
        return float(delay_str.replace('us', '')) / 1000
    else:
        # Assume milliseconds
        return float(delay_str)


def check_interface_exists(interface: str) -> bool:
    """
    Check if a network interface exists.
    
    Args:
        interface: Interface name
        
    Returns:
        True if interface exists
    """
    try:
        result = subprocess.run(
            ['ip', 'link', 'show', interface],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to check interface {interface}: {e}")
        return False


def get_interface_stats(interface: str) -> Optional[Dict[str, Any]]:
    """
    Get interface statistics.
    
    Args:
        interface: Interface name
        
    Returns:
        Dictionary with interface stats or None
    """
    try:
        result = subprocess.run(
            ['ip', '-s', 'link', 'show', interface],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse output (simplified)
        lines = result.stdout.split('\n')
        stats = {}
        
        for i, line in enumerate(lines):
            if 'RX:' in line:
                # Next line has RX stats
                if i + 1 < len(lines):
                    rx_parts = lines[i + 1].split()
                    if len(rx_parts) >= 2:
                        stats['rx_bytes'] = int(rx_parts[0])
                        stats['rx_packets'] = int(rx_parts[1])
            elif 'TX:' in line:
                # Next line has TX stats
                if i + 1 < len(lines):
                    tx_parts = lines[i + 1].split()
                    if len(tx_parts) >= 2:
                        stats['tx_bytes'] = int(tx_parts[0])
                        stats['tx_packets'] = int(tx_parts[1])
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats for {interface}: {e}")
        return None


def ping(host: str, count: int = 4, timeout: int = 5) -> Dict[str, Any]:
    """
    Ping a host and return statistics.
    
    Args:
        host: Host to ping
        count: Number of pings
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with ping statistics
    """
    try:
        result = subprocess.run(
            ['ping', '-c', str(count), '-W', str(timeout), host],
            capture_output=True,
            text=True,
            check=False
        )
        
        output = result.stdout
        
        # Parse statistics
        stats = {
            'success': result.returncode == 0,
            'packets_transmitted': 0,
            'packets_received': 0,
            'packet_loss': 100.0,
            'min_rtt': None,
            'avg_rtt': None,
            'max_rtt': None,
        }
        
        # Parse output
        for line in output.split('\n'):
            if 'packets transmitted' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    stats['packets_transmitted'] = int(parts[0].split()[0])
                    stats['packets_received'] = int(parts[1].split()[0])
                if len(parts) >= 3 and '%' in parts[2]:
                    stats['packet_loss'] = float(parts[2].split('%')[0].split()[-1])
            elif 'rtt min/avg/max' in line or 'round-trip min/avg/max' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    rtt_parts = parts[1].strip().split('/')
                    if len(rtt_parts) >= 3:
                        stats['min_rtt'] = float(rtt_parts[0])
                        stats['avg_rtt'] = float(rtt_parts[1])
                        stats['max_rtt'] = float(rtt_parts[2].split()[0])
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to ping {host}: {e}")
        return {'success': False, 'error': str(e)}

