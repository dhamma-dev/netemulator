"""Pytest configuration and fixtures."""

import pytest
import yaml
from netemulator.control.compiler import TopologyCompiler
from netemulator.models.topology import Topology


@pytest.fixture
def simple_topology_yaml():
    """Simple topology YAML for testing."""
    return """
topology:
  name: test_simple
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


@pytest.fixture
def simple_topology(simple_topology_yaml):
    """Compiled simple topology."""
    compiler = TopologyCompiler()
    data = yaml.safe_load(simple_topology_yaml)
    return compiler.load_from_dict(data)


@pytest.fixture
def scenario_yaml():
    """Scenario YAML for testing."""
    return """
scenarios:
  persistent:
    - id: baseline
      applies_to: link:h1->r1
      impairments:
        netem:
          delay: 10ms
          loss: 1%
  
  transient:
    - id: spike
      applies_to: link:r1->h2
      schedule: "RRULE:FREQ=HOURLY"
      duration: PT5M
      impairments:
        netem:
          loss: 5%
"""


@pytest.fixture
def mock_mininet_node():
    """Mock Mininet node for testing."""
    class MockNode:
        def __init__(self, name):
            self.name = name
            self._cmd_output = ""
        
        def cmd(self, command):
            """Mock command execution."""
            return self._cmd_output
        
        def intfList(self):
            """Mock interface list."""
            return []
    
    return MockNode

