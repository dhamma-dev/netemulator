"""
Prometheus metrics exporters for network emulator.
"""

import logging
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Exports Prometheus metrics for the network emulator."""

    def __init__(self):
        """Initialize metrics exporter."""
        self.registry = CollectorRegistry()
        
        # Topology metrics
        self.topologies_total = Gauge(
            'netemulator_topologies_total',
            'Total number of active topologies',
            registry=self.registry
        )
        
        self.topology_nodes = Gauge(
            'netemulator_topology_nodes',
            'Number of nodes in topology',
            ['topology', 'type'],
            registry=self.registry
        )
        
        self.topology_links = Gauge(
            'netemulator_topology_links',
            'Number of links in topology',
            ['topology'],
            registry=self.registry
        )
        
        # Scenario metrics
        self.scenarios_total = Gauge(
            'netemulator_scenarios_total',
            'Total number of scenarios',
            ['topology', 'type'],
            registry=self.registry
        )
        
        self.scenarios_active = Gauge(
            'netemulator_scenarios_active',
            'Number of active scenarios',
            ['topology'],
            registry=self.registry
        )
        
        self.scenario_executions = Counter(
            'netemulator_scenario_executions_total',
            'Total scenario executions',
            ['topology', 'scenario_id', 'status'],
            registry=self.registry
        )
        
        # Impairment metrics
        self.impairments_active = Gauge(
            'netemulator_impairments_active',
            'Number of active impairments',
            ['topology', 'type'],
            registry=self.registry
        )
        
        self.impairment_operations = Counter(
            'netemulator_impairment_operations_total',
            'Total impairment operations',
            ['topology', 'operation', 'status'],
            registry=self.registry
        )
        
        # MP metrics
        self.mps_connected = Gauge(
            'netemulator_mps_connected',
            'Number of connected monitoring points',
            ['topology'],
            registry=self.registry
        )
        
        self.mp_traffic_bytes = Counter(
            'netemulator_mp_traffic_bytes_total',
            'MP traffic in bytes',
            ['topology', 'mp_id', 'direction'],
            registry=self.registry
        )
        
        # Event metrics
        self.events_total = Counter(
            'netemulator_events_total',
            'Total number of events',
            ['event_type', 'severity'],
            registry=self.registry
        )
        
        # Performance metrics
        self.api_request_duration = Histogram(
            'netemulator_api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
    def update_topology_metrics(self, topology_name: str, network_status: Dict[str, Any]):
        """Update topology metrics."""
        nodes = network_status.get('nodes', {})
        
        self.topology_nodes.labels(topology=topology_name, type='switch').set(
            nodes.get('switches', 0)
        )
        self.topology_nodes.labels(topology=topology_name, type='router').set(
            nodes.get('routers', 0)
        )
        self.topology_nodes.labels(topology=topology_name, type='host').set(
            nodes.get('hosts', 0)
        )
        
        self.topology_links.labels(topology=topology_name).set(
            network_status.get('links', 0)
        )
    
    def update_scenario_metrics(self, topology_name: str, scheduler_status: Dict[str, Any]):
        """Update scenario metrics."""
        self.scenarios_active.labels(topology=topology_name).set(
            scheduler_status.get('active_scenarios', 0)
        )
        
        # Count by type
        scenarios = scheduler_status.get('scenarios', {})
        persistent_count = sum(1 for s in scenarios.values() if s['type'] == 'persistent')
        transient_count = sum(1 for s in scenarios.values() if s['type'] == 'transient')
        
        self.scenarios_total.labels(topology=topology_name, type='persistent').set(persistent_count)
        self.scenarios_total.labels(topology=topology_name, type='transient').set(transient_count)
    
    def record_scenario_execution(self, topology_name: str, scenario_id: str, status: str):
        """Record a scenario execution."""
        self.scenario_executions.labels(
            topology=topology_name,
            scenario_id=scenario_id,
            status=status
        ).inc()
    
    def record_impairment_operation(self, topology_name: str, operation: str, status: str):
        """Record an impairment operation."""
        self.impairment_operations.labels(
            topology=topology_name,
            operation=operation,
            status=status
        ).inc()
    
    def record_event(self, event_type: str, severity: str):
        """Record an event."""
        self.events_total.labels(
            event_type=event_type,
            severity=severity
        ).inc()
    
    def generate_metrics(self) -> bytes:
        """
        Generate Prometheus metrics in text format.
        
        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)


# Global metrics exporter instance
metrics_exporter = MetricsExporter()

