"""Tests for topology parsing and compilation."""

import pytest
from netemulator.control.compiler import TopologyCompiler
from netemulator.models.topology import Topology, NodeType


def test_simple_topology():
    """Test parsing a simple topology."""
    yaml_data = """
topology:
  name: test_topo
  nodes:
    - id: h1
      type: host
    - id: r1
      type: router
      asn: 65100
      daemons: [ospf]
    - id: h2
      type: host
  links:
    - [h1, r1, {bw: 100m, delay: 5ms}]
    - [r1, h2, {bw: 100m, delay: 5ms}]
"""
    
    compiler = TopologyCompiler()
    topology = compiler.load_from_dict(__import__('yaml').safe_load(yaml_data))
    
    assert topology.name == "test_topo"
    assert len(topology.nodes) == 3
    assert len(topology.links) == 2
    
    # Check nodes
    assert topology.nodes[0].id == "h1"
    assert topology.nodes[0].type == NodeType.HOST
    assert topology.nodes[1].type == NodeType.ROUTER
    assert topology.nodes[1].asn == 65100


def test_topology_validation():
    """Test topology validation."""
    yaml_data = """
topology:
  name: test_topo
  nodes:
    - id: h1
      type: host
    - id: r1
      type: router
      asn: 65100
  links:
    - [h1, r1, {bw: 100m}]
    - [r1, h3, {bw: 100m}]  # h3 doesn't exist
"""
    
    compiler = TopologyCompiler()
    topology = compiler.load_from_dict(__import__('yaml').safe_load(yaml_data))
    
    validation = compiler.validate()
    assert not validation["valid"]
    assert len(validation["errors"]) > 0
    assert any("h3" in error for error in validation["errors"])


def test_resource_estimation():
    """Test resource estimation."""
    yaml_data = """
topology:
  name: test_topo
  nodes:
    - id: h1
      type: host
    - id: r1
      type: router
      asn: 65100
      daemons: [ospf, bgp]
    - id: s1
      type: switch
  links:
    - [h1, s1]
    - [s1, r1]
"""
    
    compiler = TopologyCompiler()
    topology = compiler.load_from_dict(__import__('yaml').safe_load(yaml_data))
    
    resources = compiler.estimate_resources()
    
    assert resources["node_count"] == 3
    assert resources["link_count"] == 2
    assert resources["router_count"] == 1
    assert resources["estimated_cpu_cores"] > 0
    assert resources["estimated_memory_mb"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

