"""Topology data models."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class NodeType(str, Enum):
    """Network node types."""
    SWITCH = "switch"
    ROUTER = "router"
    HOST = "host"


class Node(BaseModel):
    """Network node definition."""
    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Node type")
    asn: Optional[int] = Field(None, description="AS number for routers")
    daemons: List[str] = Field(default_factory=list, description="FRR daemons (ospf, bgp, etc.)")
    services: List[str] = Field(default_factory=list, description="Services to run (dns, http3, etc.)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional node configuration")

    @validator("asn")
    def validate_asn(cls, v, values):
        """Validate ASN is provided for routers."""
        if values.get("type") == NodeType.ROUTER and v is None:
            # Default to private ASN range
            return 65000
        if v is not None and not (1 <= v <= 4294967295):
            raise ValueError("ASN must be between 1 and 4294967295")
        return v

    @validator("daemons")
    def validate_daemons(cls, v, values):
        """Validate daemons are only for routers."""
        if v and values.get("type") != NodeType.ROUTER:
            raise ValueError("Daemons can only be specified for router nodes")
        valid_daemons = {"ospf", "ospf6", "bgp", "isis", "rip", "ripng", "pimd", "ldpd"}
        for daemon in v:
            if daemon not in valid_daemons:
                raise ValueError(f"Invalid daemon: {daemon}. Must be one of {valid_daemons}")
        return v

    @validator("services")
    def validate_services(cls, v, values):
        """Validate services are only for hosts."""
        if v and values.get("type") != NodeType.HOST:
            raise ValueError("Services can only be specified for host nodes")
        valid_services = {"dns", "http", "https", "http2", "http3", "tcp_echo", "udp_echo", "cdn"}
        for service in v:
            if service not in valid_services:
                raise ValueError(f"Invalid service: {service}. Must be one of {valid_services}")
        return v


class LinkParams(BaseModel):
    """Link parameters."""
    bw: Optional[str] = Field(None, description="Bandwidth (e.g., '1g', '100m', '10k')")
    delay: Optional[str] = Field(None, description="Propagation delay (e.g., '10ms', '100us')")
    loss: Optional[float] = Field(None, description="Loss percentage (0-100)", ge=0, le=100)
    jitter: Optional[str] = Field(None, description="Jitter (e.g., '5ms')")
    max_queue_size: Optional[int] = Field(None, description="Maximum queue size")
    use_htb: bool = Field(True, description="Use HTB for bandwidth limiting")
    use_tbf: bool = Field(False, description="Use TBF for traffic shaping")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, filtering out None values."""
        return {k: v for k, v in self.dict().items() if v is not None}


class Link(BaseModel):
    """Network link definition."""
    src: str = Field(..., description="Source node ID")
    dst: str = Field(..., description="Destination node ID")
    params: LinkParams = Field(default_factory=LinkParams, description="Link parameters")

    @classmethod
    def from_list(cls, link_list: List) -> "Link":
        """Create Link from list format [src, dst, params]."""
        if len(link_list) < 2:
            raise ValueError("Link must have at least source and destination")
        src, dst = link_list[0], link_list[1]
        params = LinkParams(**link_list[2]) if len(link_list) > 2 else LinkParams()
        return cls(src=src, dst=dst, params=params)


class MPIngress(BaseModel):
    """Monitoring Point ingress configuration."""
    mp_id: str = Field(..., description="Monitoring point identifier")
    attach_to: str = Field(..., description="Node ID to attach to")
    vrf: Optional[str] = Field(None, description="VRF name for isolation")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class MPIngressConfig(BaseModel):
    """Overall MP ingress configuration."""
    type: str = Field("wireguard", description="VPN type (wireguard, openvpn, gre)")
    assign: List[MPIngress] = Field(default_factory=list, description="MP assignments")


class Topology(BaseModel):
    """Complete topology definition."""
    name: str = Field(..., description="Topology name")
    nodes: List[Node] = Field(..., description="Network nodes")
    links: List[Link] = Field(..., description="Network links")
    mp_ingress: Optional[MPIngressConfig] = Field(None, description="MP ingress configuration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator("links", pre=True)
    def parse_links(cls, v):
        """Parse links from list or dict format."""
        if not v:
            return []
        result = []
        for link in v:
            if isinstance(link, list):
                result.append(Link.from_list(link))
            elif isinstance(link, dict):
                result.append(Link(**link))
            else:
                result.append(link)
        return result

    @validator("links")
    def validate_links(cls, v, values):
        """Validate link endpoints exist."""
        if "nodes" not in values:
            return v
        node_ids = {node.id for node in values["nodes"]}
        for link in v:
            if link.src not in node_ids:
                raise ValueError(f"Link source '{link.src}' not found in nodes")
            if link.dst not in node_ids:
                raise ValueError(f"Link destination '{link.dst}' not found in nodes")
        return v

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_links_for_node(self, node_id: str) -> List[Link]:
        """Get all links connected to a node."""
        return [link for link in self.links if link.src == node_id or link.dst == node_id]

