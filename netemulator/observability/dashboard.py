"""
Grafana dashboard generation and management.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class GrafanaDashboard:
    """Generates Grafana dashboards for network emulator."""

    def __init__(self, title: str = "NetEmulator Overview"):
        """
        Initialize dashboard.
        
        Args:
            title: Dashboard title
        """
        self.title = title
        self.panels = []
        self.next_panel_id = 1
        
    def add_panel(self, title: str, panel_type: str, targets: List[Dict[str, Any]],
                  grid_pos: Dict[str, int] = None) -> int:
        """
        Add a panel to the dashboard.
        
        Args:
            title: Panel title
            panel_type: Panel type (graph, stat, table, etc.)
            targets: Prometheus query targets
            grid_pos: Panel grid position {x, y, w, h}
            
        Returns:
            Panel ID
        """
        panel_id = self.next_panel_id
        self.next_panel_id += 1
        
        if grid_pos is None:
            # Auto-layout in rows of 2
            row = (panel_id - 1) // 2
            col = (panel_id - 1) % 2
            grid_pos = {
                "x": col * 12,
                "y": row * 8,
                "w": 12,
                "h": 8
            }
        
        panel = {
            "id": panel_id,
            "title": title,
            "type": panel_type,
            "targets": targets,
            "gridPos": grid_pos,
            "datasource": "Prometheus"
        }
        
        self.panels.append(panel)
        return panel_id
    
    def to_json(self) -> Dict[str, Any]:
        """
        Convert dashboard to Grafana JSON format.
        
        Returns:
            Dashboard JSON
        """
        return {
            "dashboard": {
                "title": self.title,
                "panels": self.panels,
                "timezone": "utc",
                "schemaVersion": 16,
                "version": 0,
                "refresh": "5s"
            },
            "overwrite": True
        }
    
    def export(self, filename: str):
        """Export dashboard to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.to_json(), f, indent=2)
        logger.info(f"Exported dashboard to {filename}")


def create_overview_dashboard() -> GrafanaDashboard:
    """Create main overview dashboard."""
    dashboard = GrafanaDashboard("NetEmulator Overview")
    
    # Topology status
    dashboard.add_panel(
        title="Active Topologies",
        panel_type="stat",
        targets=[{
            "expr": "netemulator_topologies_total",
            "legendFormat": "Topologies"
        }]
    )
    
    # Active scenarios
    dashboard.add_panel(
        title="Active Scenarios",
        panel_type="stat",
        targets=[{
            "expr": "sum(netemulator_scenarios_active)",
            "legendFormat": "Scenarios"
        }]
    )
    
    # Events over time
    dashboard.add_panel(
        title="Events Rate",
        panel_type="graph",
        targets=[{
            "expr": "rate(netemulator_events_total[5m])",
            "legendFormat": "{{event_type}}"
        }]
    )
    
    # Scenario executions
    dashboard.add_panel(
        title="Scenario Executions",
        panel_type="graph",
        targets=[{
            "expr": "rate(netemulator_scenario_executions_total[5m])",
            "legendFormat": "{{scenario_id}} - {{status}}"
        }]
    )
    
    return dashboard


def create_topology_dashboard(topology_name: str) -> GrafanaDashboard:
    """Create topology-specific dashboard."""
    dashboard = GrafanaDashboard(f"Topology: {topology_name}")
    
    # Node count
    dashboard.add_panel(
        title="Nodes by Type",
        panel_type="graph",
        targets=[{
            "expr": f'netemulator_topology_nodes{{topology="{topology_name}"}}',
            "legendFormat": "{{type}}"
        }]
    )
    
    # Link count
    dashboard.add_panel(
        title="Links",
        panel_type="stat",
        targets=[{
            "expr": f'netemulator_topology_links{{topology="{topology_name}"}}',
            "legendFormat": "Links"
        }]
    )
    
    # Active impairments
    dashboard.add_panel(
        title="Active Impairments",
        panel_type="graph",
        targets=[{
            "expr": f'netemulator_impairments_active{{topology="{topology_name}"}}',
            "legendFormat": "{{type}}"
        }]
    )
    
    # Connected MPs
    dashboard.add_panel(
        title="Connected Monitoring Points",
        panel_type="stat",
        targets=[{
            "expr": f'netemulator_mps_connected{{topology="{topology_name}"}}',
            "legendFormat": "MPs"
        }]
    )
    
    return dashboard


def main():
    """Generate and export default dashboards."""
    import sys
    
    # Overview dashboard
    overview = create_overview_dashboard()
    overview.export("dashboards/overview.json")
    print("Generated overview dashboard")
    
    # Example topology dashboard
    if len(sys.argv) > 1:
        topology_name = sys.argv[1]
        topo_dash = create_topology_dashboard(topology_name)
        topo_dash.export(f"dashboards/{topology_name}.json")
        print(f"Generated dashboard for topology: {topology_name}")


if __name__ == "__main__":
    main()

