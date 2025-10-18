"""Tests for scenario parsing and scheduling."""

import pytest
from netemulator.models.scenario import Scenario, ScenarioType, NetemSpec


def test_netem_spec():
    """Test netem specification."""
    spec = NetemSpec(
        delay="50ms",
        loss="2%",
        jitter={"mean": "10ms", "stddev": "5ms"}
    )
    
    args = spec.to_tc_command()
    assert "50ms" in args
    assert "loss" in args
    assert "2%" in args


def test_scenario_parsing():
    """Test scenario parsing."""
    scenario_dict = {
        "id": "test_scenario",
        "type": "transient",
        "applies_to": "link:h1->r1",
        "impairments": {
            "netem": {
                "delay": "50ms",
                "loss": "1%"
            }
        },
        "schedule": "RRULE:FREQ=DAILY;BYHOUR=12",
        "duration": "PT15M"
    }
    
    scenario = Scenario(**scenario_dict)
    
    assert scenario.id == "test_scenario"
    assert scenario.type == ScenarioType.TRANSIENT
    assert scenario.schedule is not None
    assert scenario.impairments.netem is not None
    assert scenario.impairments.netem.delay == "50ms"


def test_target_parsing():
    """Test target parsing."""
    # Link target
    scenario = Scenario(
        id="test1",
        applies_to="link:h1->r1",
        impairments={"netem": {"delay": "10ms"}}
    )
    target = scenario.parse_target()
    assert target["type"] == "link"
    assert target["src"] == "h1"
    assert target["dst"] == "r1"
    
    # Path target
    scenario = Scenario(
        id="test2",
        applies_to="path:h1->r1->h2",
        impairments={"netem": {"delay": "10ms"}}
    )
    target = scenario.parse_target()
    assert target["type"] == "path"
    assert target["nodes"] == ["h1", "r1", "h2"]
    
    # Node target
    scenario = Scenario(
        id="test3",
        applies_to="node:r1",
        impairments={"netem": {"delay": "10ms"}}
    )
    target = scenario.parse_target()
    assert target["type"] == "node"
    assert target["id"] == "r1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

