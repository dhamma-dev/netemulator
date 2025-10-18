"""Scenario and impairment data models."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ScenarioType(str, Enum):
    """Scenario types."""
    PERSISTENT = "persistent"
    TRANSIENT = "transient"


class NetemSpec(BaseModel):
    """Netem impairment specification."""
    delay: Optional[str] = Field(None, description="Delay (e.g., '50ms')")
    delay_variation: Optional[str] = Field(None, description="Delay variation/jitter (e.g., '10ms')")
    delay_correlation: Optional[float] = Field(None, description="Delay correlation (0-100%)", ge=0, le=100)
    distribution: Optional[str] = Field(None, description="Delay distribution (normal, pareto, paretonormal)")
    
    loss: Optional[str] = Field(None, description="Loss percentage (e.g., '2%', '0.5%')")
    loss_correlation: Optional[float] = Field(None, description="Loss correlation (0-100%)", ge=0, le=100)
    
    duplicate: Optional[str] = Field(None, description="Duplication percentage (e.g., '1%')")
    corrupt: Optional[str] = Field(None, description="Corruption percentage (e.g., '0.1%')")
    reorder: Optional[str] = Field(None, description="Reordering percentage (e.g., '5%')")
    reorder_correlation: Optional[float] = Field(None, description="Reorder correlation (0-100%)", ge=0, le=100)
    
    rate: Optional[str] = Field(None, description="Rate limit (e.g., '1mbit')")
    
    jitter: Optional[Dict[str, str]] = Field(None, description="Jitter spec with mean/stddev")

    def to_tc_command(self) -> List[str]:
        """Convert to tc netem command arguments."""
        args = []
        
        if self.delay:
            args.extend(["delay", self.delay])
            if self.delay_variation:
                args.append(self.delay_variation)
                if self.delay_correlation:
                    args.append(f"{self.delay_correlation}%")
            if self.distribution:
                args.extend(["distribution", self.distribution])
        
        if self.jitter:
            mean = self.jitter.get("mean", "0ms")
            stddev = self.jitter.get("stddev", "0ms")
            args.extend(["delay", mean, stddev])
        
        if self.loss:
            args.extend(["loss", self.loss])
            if self.loss_correlation:
                args.append(f"{self.loss_correlation}%")
        
        if self.duplicate:
            args.extend(["duplicate", self.duplicate])
        
        if self.corrupt:
            args.extend(["corrupt", self.corrupt])
        
        if self.reorder:
            args.extend(["reorder", self.reorder])
            if self.reorder_correlation:
                args.append(f"{self.reorder_correlation}%")
        
        if self.rate:
            args.extend(["rate", self.rate])
        
        return args


class QdiscSpec(BaseModel):
    """Queue discipline specification."""
    type: str = Field("htb", description="Qdisc type (htb, tbf, pfifo, fq_codel)")
    rate: Optional[str] = Field(None, description="Rate limit (e.g., '100mbit')")
    ceil: Optional[str] = Field(None, description="Maximum rate ceiling")
    burst: Optional[str] = Field(None, description="Burst size")
    cburst: Optional[str] = Field(None, description="Cell burst size")
    limit: Optional[int] = Field(None, description="Queue limit in packets")
    latency: Optional[str] = Field(None, description="Maximum latency (for TBF)")


class ControlPlaneEvent(BaseModel):
    """Control plane event specification."""
    bgp_flap: Optional[Dict[str, Any]] = Field(None, description="BGP flap config")
    bgp_withdraw: Optional[Dict[str, Any]] = Field(None, description="BGP route withdrawal")
    ospf_cost_change: Optional[Dict[str, Any]] = Field(None, description="OSPF cost change")
    interface_flap: Optional[Dict[str, Any]] = Field(None, description="Interface down/up")


class SecurityFault(BaseModel):
    """Security/content fault specification."""
    dns_error: Optional[str] = Field(None, description="DNS error type (NXDOMAIN, SERVFAIL, timeout)")
    tls_error: Optional[str] = Field(None, description="TLS error type (expired, sni_mismatch, handshake_delay)")
    http_status: Optional[int] = Field(None, description="Force HTTP status code")
    packet_filter: Optional[str] = Field(None, description="iptables/nftables rule")


class ImpairmentSpec(BaseModel):
    """Complete impairment specification."""
    netem: Optional[NetemSpec] = Field(None, description="Netem impairments")
    qdisc: Optional[QdiscSpec] = Field(None, description="Queue discipline")
    control_plane: Optional[ControlPlaneEvent] = Field(None, description="Control plane events")
    security: Optional[SecurityFault] = Field(None, description="Security/content faults")


class Scenario(BaseModel):
    """Scenario definition."""
    id: str = Field(..., description="Unique scenario identifier")
    type: ScenarioType = Field(ScenarioType.TRANSIENT, description="Scenario type")
    applies_to: str = Field(..., description="Target (link:x->y, path:x->y->z, node:x)")
    impairments: ImpairmentSpec = Field(..., description="Impairment specification")
    
    # Scheduling (for transient scenarios)
    schedule: Optional[str] = Field(None, description="RRULE or cron schedule")
    duration: Optional[str] = Field(None, description="Duration (ISO 8601, e.g., PT15M)")
    priority: int = Field(100, description="Priority (higher = more important)")
    
    # Metadata
    description: Optional[str] = Field(None, description="Scenario description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator("schedule")
    def validate_schedule(cls, v, values):
        """Validate schedule is provided for transient scenarios."""
        if values.get("type") == ScenarioType.TRANSIENT and not v:
            raise ValueError("Schedule is required for transient scenarios")
        return v

    @validator("impairments", pre=True)
    def parse_impairments(cls, v):
        """Parse impairments from various formats."""
        if isinstance(v, dict):
            # Handle flat format where netem/qdisc/etc are at top level
            if any(k in v for k in ["netem", "qdisc", "control_plane", "security"]):
                return v
            # Handle flat netem format
            if any(k in v for k in ["delay", "loss", "jitter", "duplicate", "corrupt"]):
                return {"netem": v}
        return v

    def parse_target(self) -> Dict[str, Any]:
        """Parse the applies_to target specification."""
        if self.applies_to.startswith("link:"):
            # link:node1->node2
            parts = self.applies_to[5:].split("->")
            return {"type": "link", "src": parts[0], "dst": parts[1] if len(parts) > 1 else None}
        elif self.applies_to.startswith("path:"):
            # path:node1->node2->node3
            nodes = self.applies_to[5:].split("->")
            return {"type": "path", "nodes": nodes}
        elif self.applies_to.startswith("node:"):
            # node:node1
            return {"type": "node", "id": self.applies_to[5:]}
        else:
            raise ValueError(f"Invalid applies_to format: {self.applies_to}")


class ScenarioSet(BaseModel):
    """Collection of scenarios."""
    persistent: List[Scenario] = Field(default_factory=list, description="Persistent scenarios")
    transient: List[Scenario] = Field(default_factory=list, description="Transient scenarios")

    @validator("persistent", pre=True)
    def parse_persistent(cls, v):
        """Parse persistent scenarios."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                item["type"] = ScenarioType.PERSISTENT
                # Flatten impairment spec if needed
                if "netem" in item and not "impairments" in item:
                    item["impairments"] = {"netem": item.pop("netem")}
                if "qdisc" in item and "impairments" not in item:
                    item["impairments"] = {"qdisc": item.pop("qdisc")}
                result.append(Scenario(**item))
            else:
                result.append(item)
        return result

    @validator("transient", pre=True)
    def parse_transient(cls, v):
        """Parse transient scenarios."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                item["type"] = ScenarioType.TRANSIENT
                # Flatten impairment spec if needed
                if "netem" in item and "impairments" not in item:
                    item["impairments"] = {"netem": item.pop("netem")}
                if "qdisc" in item and "impairments" not in item:
                    item["impairments"] = {"qdisc": item.pop("qdisc")}
                if "control_plane" in item and "impairments" not in item:
                    item["impairments"] = {"control_plane": item.pop("control_plane")}
                result.append(Scenario(**item))
            else:
                result.append(item)
        return result

