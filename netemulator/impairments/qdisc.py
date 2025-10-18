"""Queue discipline (qdisc) management for traffic shaping."""

import logging
from typing import Dict, Any
from ..models.scenario import QdiscSpec

logger = logging.getLogger(__name__)


class QdiscManager:
    """Manages queue disciplines for traffic shaping."""

    def __init__(self, node, interface: str):
        """
        Initialize qdisc manager.
        
        Args:
            node: Mininet node
            interface: Interface name
        """
        self.node = node
        self.interface = interface
        
    def apply_htb(self, spec: QdiscSpec) -> bool:
        """
        Apply HTB (Hierarchical Token Bucket) qdisc.
        
        Args:
            spec: Qdisc specification
            
        Returns:
            True if successful
        """
        try:
            # Add HTB root qdisc
            cmd = f"tc qdisc add dev {self.interface} root handle 1: htb default 10"
            self.node.cmd(cmd)
            
            # Add HTB class with rate limit
            if spec.rate:
                rate = spec.rate
                ceil = spec.ceil or rate
                burst = spec.burst or "15k"
                cburst = spec.cburst or "15k"
                
                cmd = (f"tc class add dev {self.interface} parent 1: classid 1:10 htb "
                       f"rate {rate} ceil {ceil} burst {burst} cburst {cburst}")
                self.node.cmd(cmd)
                
                logger.info(f"Applied HTB qdisc to {self.node.name}:{self.interface}: "
                           f"rate={rate} ceil={ceil}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply HTB qdisc: {e}")
            return False
    
    def apply_tbf(self, spec: QdiscSpec) -> bool:
        """
        Apply TBF (Token Bucket Filter) qdisc.
        
        Args:
            spec: Qdisc specification
            
        Returns:
            True if successful
        """
        try:
            if not spec.rate:
                logger.error("TBF requires rate parameter")
                return False
            
            rate = spec.rate
            burst = spec.burst or "32kbit"
            latency = spec.latency or "50ms"
            
            cmd = (f"tc qdisc add dev {self.interface} root tbf "
                   f"rate {rate} burst {burst} latency {latency}")
            self.node.cmd(cmd)
            
            logger.info(f"Applied TBF qdisc to {self.node.name}:{self.interface}: "
                       f"rate={rate}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply TBF qdisc: {e}")
            return False
    
    def apply_fq_codel(self, spec: QdiscSpec) -> bool:
        """
        Apply fq_codel (Fair Queueing with Controlled Delay) qdisc.
        
        Args:
            spec: Qdisc specification
            
        Returns:
            True if successful
        """
        try:
            cmd = f"tc qdisc add dev {self.interface} root fq_codel"
            
            if spec.limit:
                cmd += f" limit {spec.limit}"
            
            self.node.cmd(cmd)
            
            logger.info(f"Applied fq_codel qdisc to {self.node.name}:{self.interface}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply fq_codel qdisc: {e}")
            return False
    
    def apply(self, spec: QdiscSpec) -> bool:
        """
        Apply qdisc based on spec type.
        
        Args:
            spec: Qdisc specification
            
        Returns:
            True if successful
        """
        if spec.type == "htb":
            return self.apply_htb(spec)
        elif spec.type == "tbf":
            return self.apply_tbf(spec)
        elif spec.type == "fq_codel":
            return self.apply_fq_codel(spec)
        else:
            logger.error(f"Unknown qdisc type: {spec.type}")
            return False
    
    def clear(self) -> bool:
        """Clear qdisc."""
        try:
            cmd = f"tc qdisc del dev {self.interface} root"
            self.node.cmd(cmd)
            logger.debug(f"Cleared qdisc from {self.node.name}:{self.interface}")
            return True
        except Exception as e:
            logger.debug(f"No qdisc to clear: {e}")
            return True
    
    def show(self) -> str:
        """Show current qdisc configuration."""
        cmd = f"tc qdisc show dev {self.interface}"
        return self.node.cmd(cmd)

