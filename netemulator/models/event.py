"""Event logging data models."""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types."""
    TOPOLOGY_CREATED = "topology.created"
    TOPOLOGY_UPDATED = "topology.updated"
    TOPOLOGY_DELETED = "topology.deleted"
    
    SCENARIO_CREATED = "scenario.created"
    SCENARIO_STARTED = "scenario.started"
    SCENARIO_ENDED = "scenario.ended"
    SCENARIO_FAILED = "scenario.failed"
    
    IMPAIRMENT_APPLIED = "impairment.applied"
    IMPAIRMENT_REMOVED = "impairment.removed"
    
    LINK_UP = "link.up"
    LINK_DOWN = "link.down"
    
    ROUTER_UP = "router.up"
    ROUTER_DOWN = "router.down"
    
    BGP_SESSION_UP = "bgp.session_up"
    BGP_SESSION_DOWN = "bgp.session_down"
    BGP_ROUTE_ADVERTISED = "bgp.route_advertised"
    BGP_ROUTE_WITHDRAWN = "bgp.route_withdrawn"
    
    OSPF_NEIGHBOR_UP = "ospf.neighbor_up"
    OSPF_NEIGHBOR_DOWN = "ospf.neighbor_down"
    
    MP_CONNECTED = "mp.connected"
    MP_DISCONNECTED = "mp.disconnected"
    
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class EventSeverity(str, Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Event(BaseModel):
    """Event record."""
    id: str = Field(..., description="Unique event ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp (UTC)")
    type: EventType = Field(..., description="Event type")
    severity: EventSeverity = Field(EventSeverity.INFO, description="Event severity")
    
    # Context
    topology_name: Optional[str] = Field(None, description="Related topology name")
    scenario_id: Optional[str] = Field(None, description="Related scenario ID")
    node_id: Optional[str] = Field(None, description="Related node ID")
    link_id: Optional[str] = Field(None, description="Related link ID")
    
    # Event details
    message: str = Field(..., description="Human-readable message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")
    
    # Tracing
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")
    span_id: Optional[str] = Field(None, description="Span ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_prometheus_labels(self) -> Dict[str, str]:
        """Convert to Prometheus metric labels."""
        labels = {
            "event_type": self.type.value,
            "severity": self.severity.value,
        }
        if self.topology_name:
            labels["topology"] = self.topology_name
        if self.scenario_id:
            labels["scenario"] = self.scenario_id
        if self.node_id:
            labels["node"] = self.node_id
        return labels

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to structured log dictionary."""
        log_dict = {
            "event_id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.topology_name:
            log_dict["topology_name"] = self.topology_name
        if self.scenario_id:
            log_dict["scenario_id"] = self.scenario_id
        if self.node_id:
            log_dict["node_id"] = self.node_id
        if self.link_id:
            log_dict["link_id"] = self.link_id
        if self.trace_id:
            log_dict["trace_id"] = self.trace_id
        if self.details:
            log_dict["details"] = self.details
        return log_dict

