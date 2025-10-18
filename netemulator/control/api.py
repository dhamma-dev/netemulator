"""
REST API Control Plane - Manages topologies, scenarios, and monitoring points.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import yaml

from ..models.topology import Topology
from ..models.scenario import Scenario, ScenarioSet
from ..models.event import Event, EventType, EventSeverity
from ..control.compiler import TopologyCompiler
from ..dataplane.mininet_topo import NetworkTopology, create_network
from ..control.scheduler import ScenarioScheduler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# API Models
class TopologyCreate(BaseModel):
    """Request model for creating topology."""
    yaml_content: str


class TopologyStatus(BaseModel):
    """Response model for topology status."""
    name: str
    status: str
    nodes: Dict[str, int]
    links: int
    created_at: datetime


class ScenarioCreate(BaseModel):
    """Request model for creating scenario."""
    scenario: Dict[str, Any]


class ValidationResult(BaseModel):
    """Response model for validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    resource_estimate: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    uptime_seconds: float


# Global state (in production, use proper state management)
class APIState:
    """API global state."""
    def __init__(self):
        self.topologies: Dict[str, NetworkTopology] = {}
        self.schedulers: Dict[str, ScenarioScheduler] = {}
        self.events: List[Event] = []
        self.start_time = datetime.utcnow()


state = APIState()
app = FastAPI(
    title="NetEmulator API",
    description="Continuous Internet Testbed for AppNeta",
    version="0.1.0"
)


# Event logger
class EventLogger:
    """Simple event logger."""
    
    def __init__(self):
        self.events: List[Event] = []
    
    def log(self, event: Event):
        """Log an event."""
        self.events.append(event)
        logger.info(f"Event: {event.type.value} - {event.message}")
    
    def get_events(self, limit: int = 100, 
                   event_type: Optional[EventType] = None,
                   topology_name: Optional[str] = None) -> List[Event]:
        """Get events with optional filtering."""
        filtered = self.events
        
        if event_type:
            filtered = [e for e in filtered if e.type == event_type]
        
        if topology_name:
            filtered = [e for e in filtered if e.topology_name == topology_name]
        
        return filtered[-limit:]


event_logger = EventLogger()


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    uptime = (datetime.utcnow() - state.start_time).total_seconds()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        uptime_seconds=uptime
    )


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return await root()


@app.post("/api/v1/topologies", status_code=status.HTTP_201_CREATED)
async def create_topology(yaml_content: str = Body(..., media_type="text/plain")):
    """
    Create and deploy a network topology from YAML.
    
    Args:
        yaml_content: YAML topology definition
        
    Returns:
        Topology status
    """
    try:
        # Compile topology
        compiler = TopologyCompiler()
        data = yaml.safe_load(yaml_content)
        topology = compiler.load_from_dict(data)
        
        # Validate
        validation = compiler.validate()
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid topology: {validation['errors']}"
            )
        
        # Check if topology already exists
        if topology.name in state.topologies:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Topology '{topology.name}' already exists"
            )
        
        # Create network
        logger.info(f"Creating topology: {topology.name}")
        network = create_network(topology, auto_start=True)
        state.topologies[topology.name] = network
        
        # Create scheduler
        scheduler = ScenarioScheduler(network, event_logger=event_logger)
        state.schedulers[topology.name] = scheduler
        
        # Add scenarios if present
        if compiler.scenarios:
            scheduler.add_scenarios(compiler.scenarios)
        
        # Log event
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.TOPOLOGY_CREATED,
            severity=EventSeverity.INFO,
            topology_name=topology.name,
            message=f"Topology '{topology.name}' created and started"
        )
        event_logger.log(event)
        
        return {
            "name": topology.name,
            "status": "running",
            "nodes": network.get_status()["nodes"],
            "links": len(network.links),
            "scenarios": len(scheduler.scenarios) if compiler.scenarios else 0
        }
        
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to create topology: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create topology: {str(e)}"
        )


@app.get("/api/v1/topologies")
async def list_topologies():
    """List all topologies."""
    return {
        "topologies": [
            {
                "name": name,
                "status": network.get_status()
            }
            for name, network in state.topologies.items()
        ]
    }


@app.get("/api/v1/topologies/{name}")
async def get_topology(name: str):
    """Get topology details."""
    if name not in state.topologies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topology '{name}' not found"
        )
    
    network = state.topologies[name]
    scheduler = state.schedulers.get(name)
    
    return {
        "name": name,
        "status": network.get_status(),
        "scheduler": scheduler.get_status() if scheduler else None
    }


@app.delete("/api/v1/topologies/{name}")
async def delete_topology(name: str):
    """Tear down a topology."""
    if name not in state.topologies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topology '{name}' not found"
        )
    
    try:
        network = state.topologies[name]
        scheduler = state.schedulers.get(name)
        
        # Shutdown scheduler
        if scheduler:
            scheduler.shutdown()
            del state.schedulers[name]
        
        # Stop network
        network.stop()
        del state.topologies[name]
        
        # Log event
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.TOPOLOGY_DELETED,
            severity=EventSeverity.INFO,
            topology_name=name,
            message=f"Topology '{name}' deleted"
        )
        event_logger.log(event)
        
        return {"message": f"Topology '{name}' deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete topology: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete topology: {str(e)}"
        )


@app.post("/api/v1/topologies/{name}/validate", response_model=ValidationResult)
async def validate_topology(name: str, yaml_content: str = Body(..., media_type="text/plain")):
    """Validate a topology without deploying it."""
    try:
        compiler = TopologyCompiler()
        data = yaml.safe_load(yaml_content)
        topology = compiler.load_from_dict(data)
        
        validation = compiler.validate()
        resource_estimate = compiler.estimate_resources()
        
        return ValidationResult(
            valid=validation["valid"],
            errors=validation["errors"],
            warnings=validation["warnings"],
            resource_estimate=resource_estimate
        )
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[str(e)],
            warnings=[]
        )


@app.post("/api/v1/scenarios")
async def create_scenario(topology_name: str, scenario_data: Dict[str, Any]):
    """Create and add a scenario to a topology."""
    if topology_name not in state.schedulers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topology '{topology_name}' not found"
        )
    
    try:
        scenario = Scenario(**scenario_data)
        scheduler = state.schedulers[topology_name]
        scheduler.add_scenario(scenario)
        
        return {
            "scenario_id": scenario.id,
            "status": "scheduled",
            "type": scenario.type.value
        }
        
    except Exception as e:
        logger.error(f"Failed to create scenario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario: {str(e)}"
        )


@app.get("/api/v1/scenarios/{scenario_id}/events")
async def get_scenario_events(scenario_id: str, limit: int = 100):
    """Get events for a specific scenario."""
    events = [
        e.to_log_dict()
        for e in event_logger.events
        if e.scenario_id == scenario_id
    ]
    return {"events": events[-limit:]}


@app.post("/api/v1/scenarios/{scenario_id}/trigger")
async def trigger_scenario(topology_name: str, scenario_id: str):
    """Manually trigger a scenario."""
    if topology_name not in state.schedulers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topology '{topology_name}' not found"
        )
    
    scheduler = state.schedulers[topology_name]
    if scenario_id not in scheduler.scenarios:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found"
        )
    
    scenario = scheduler.scenarios[scenario_id]
    duration = scheduler._parse_duration(scenario.duration or "PT15M")
    scheduler._start_scenario(scenario, duration)
    
    return {"message": f"Scenario '{scenario_id}' triggered"}


@app.get("/api/v1/events")
async def get_events(limit: int = 100, topology_name: Optional[str] = None):
    """Get system events."""
    events = event_logger.get_events(
        limit=limit,
        topology_name=topology_name
    )
    return {
        "events": [e.to_log_dict() for e in events]
    }


@app.get("/api/v1/metrics")
async def get_metrics():
    """
    Get Prometheus-style metrics.
    
    Returns metrics in text format for Prometheus scraping.
    """
    metrics = []
    
    # Topology metrics
    metrics.append(f"netemulator_topologies_total {len(state.topologies)}")
    
    for name, network in state.topologies.items():
        status_info = network.get_status()
        if status_info["status"] == "running":
            metrics.append(f'netemulator_topology_status{{name="{name}"}} 1')
            metrics.append(f'netemulator_topology_nodes{{name="{name}"}} {status_info["nodes"]["total"]}')
            metrics.append(f'netemulator_topology_links{{name="{name}"}} {status_info["links"]}')
    
    # Scenario metrics
    for name, scheduler in state.schedulers.items():
        status_info = scheduler.get_status()
        metrics.append(f'netemulator_scenarios_total{{topology="{name}"}} {status_info["total_scenarios"]}')
        metrics.append(f'netemulator_scenarios_active{{topology="{name}"}} {status_info["active_scenarios"]}')
    
    # Event metrics
    metrics.append(f"netemulator_events_total {len(event_logger.events)}")
    
    return "\n".join(metrics) + "\n"


def main():
    """Main entry point for API server."""
    import uvicorn
    
    logger.info("Starting NetEmulator API server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )


if __name__ == "__main__":
    main()

