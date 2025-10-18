"""
Command-line interface for NetEmulator.
"""

import click
import requests
import yaml
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


@click.group()
@click.option('--api-url', default='http://localhost:8080', envvar='NETEMULATOR_API_URL',
              help='NetEmulator API URL')
@click.pass_context
def cli(ctx, api_url):
    """NetEmulator CLI - Network Emulation Testbed"""
    ctx.ensure_object(dict)
    ctx.obj['API_URL'] = api_url


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health status."""
    api_url = ctx.obj['API_URL']
    
    try:
        response = requests.get(f"{api_url}/api/v1/health", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        rprint(f"[green]✓[/green] API is healthy")
        rprint(f"  Version: {data.get('version')}")
        rprint(f"  Uptime: {data.get('uptime_seconds', 0):.1f} seconds")
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] API is not accessible: {e}")
        raise click.Abort()


@cli.command()
@click.argument('topology_file', type=click.Path(exists=True))
@click.pass_context
def deploy(ctx, topology_file):
    """Deploy a topology from YAML file."""
    api_url = ctx.obj['API_URL']
    
    with console.status(f"[bold green]Deploying {topology_file}..."):
        with open(topology_file, 'r') as f:
            yaml_content = f.read()
        
        try:
            response = requests.post(
                f"{api_url}/api/v1/topologies",
                data=yaml_content,
                headers={'Content-Type': 'text/plain'},
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            rprint(f"[green]✓[/green] Topology deployed successfully")
            rprint(f"  Name: {data.get('name')}")
            rprint(f"  Status: {data.get('status')}")
            rprint(f"  Nodes: {data.get('nodes', {}).get('total', 0)}")
            rprint(f"  Links: {data.get('links', 0)}")
            rprint(f"  Scenarios: {data.get('scenarios', 0)}")
            
        except requests.exceptions.RequestException as e:
            rprint(f"[red]✗[/red] Failed to deploy: {e}")
            if hasattr(e.response, 'text'):
                rprint(f"  Error: {e.response.text}")
            raise click.Abort()


@cli.command()
@click.pass_context
def list(ctx):
    """List all topologies."""
    api_url = ctx.obj['API_URL']
    
    try:
        response = requests.get(f"{api_url}/api/v1/topologies", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        topologies = data.get('topologies', [])
        
        if not topologies:
            rprint("[yellow]No topologies found[/yellow]")
            return
        
        table = Table(title="Active Topologies")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Nodes", justify="right")
        table.add_column("Links", justify="right")
        
        for topo in topologies:
            name = topo.get('name', 'unknown')
            status_info = topo.get('status', {})
            status = status_info.get('status', 'unknown')
            nodes = status_info.get('nodes', {}).get('total', 0)
            links = status_info.get('links', 0)
            
            table.add_row(name, status, str(nodes), str(links))
        
        console.print(table)
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] Failed to list topologies: {e}")
        raise click.Abort()


@cli.command()
@click.argument('topology_name')
@click.pass_context
def status(ctx, topology_name):
    """Get topology status."""
    api_url = ctx.obj['API_URL']
    
    try:
        response = requests.get(f"{api_url}/api/v1/topologies/{topology_name}", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        rprint(f"[bold]Topology: {data.get('name')}[/bold]")
        
        status_info = data.get('status', {})
        rprint(f"  Status: [green]{status_info.get('status')}[/green]")
        
        nodes = status_info.get('nodes', {})
        rprint(f"  Nodes:")
        rprint(f"    Total: {nodes.get('total', 0)}")
        rprint(f"    Switches: {nodes.get('switches', 0)}")
        rprint(f"    Routers: {nodes.get('routers', 0)}")
        rprint(f"    Hosts: {nodes.get('hosts', 0)}")
        
        rprint(f"  Links: {status_info.get('links', 0)}")
        
        scheduler = data.get('scheduler')
        if scheduler:
            rprint(f"  Scenarios:")
            rprint(f"    Total: {scheduler.get('total_scenarios', 0)}")
            rprint(f"    Active: {scheduler.get('active_scenarios', 0)}")
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] Failed to get status: {e}")
        raise click.Abort()


@cli.command()
@click.argument('topology_name')
@click.confirmation_option(prompt='Are you sure you want to delete this topology?')
@click.pass_context
def delete(ctx, topology_name):
    """Delete a topology."""
    api_url = ctx.obj['API_URL']
    
    with console.status(f"[bold red]Deleting {topology_name}..."):
        try:
            response = requests.delete(f"{api_url}/api/v1/topologies/{topology_name}", timeout=30)
            response.raise_for_status()
            
            rprint(f"[green]✓[/green] Topology '{topology_name}' deleted")
            
        except requests.exceptions.RequestException as e:
            rprint(f"[red]✗[/red] Failed to delete: {e}")
            raise click.Abort()


@cli.command()
@click.option('--topology', help='Filter by topology name')
@click.option('--limit', default=20, help='Number of events to show')
@click.pass_context
def events(ctx, topology, limit):
    """View recent events."""
    api_url = ctx.obj['API_URL']
    
    params = {'limit': limit}
    if topology:
        params['topology_name'] = topology
    
    try:
        response = requests.get(f"{api_url}/api/v1/events", params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        events_list = data.get('events', [])
        
        if not events_list:
            rprint("[yellow]No events found[/yellow]")
            return
        
        table = Table(title=f"Recent Events (last {limit})")
        table.add_column("Time", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity")
        table.add_column("Message")
        
        for event in events_list:
            timestamp = event.get('timestamp', '')[:19]  # Truncate microseconds
            event_type = event.get('event_type', '').split('.')[-1]
            severity = event.get('severity', 'info')
            message = event.get('message', '')
            
            severity_style = {
                'debug': 'dim',
                'info': 'white',
                'warning': 'yellow',
                'error': 'red',
                'critical': 'bold red'
            }.get(severity, 'white')
            
            table.add_row(
                timestamp,
                event_type,
                f"[{severity_style}]{severity}[/{severity_style}]",
                message
            )
        
        console.print(table)
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] Failed to get events: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def metrics(ctx):
    """View current metrics."""
    api_url = ctx.obj['API_URL']
    
    try:
        response = requests.get(f"{api_url}/api/v1/metrics", timeout=5)
        response.raise_for_status()
        
        # Parse Prometheus text format
        lines = response.text.strip().split('\n')
        
        rprint("[bold]Current Metrics:[/bold]\n")
        for line in lines:
            if line and not line.startswith('#'):
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    metric, value = parts
                    rprint(f"  {metric}: [cyan]{value}[/cyan]")
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] Failed to get metrics: {e}")
        raise click.Abort()


@cli.command()
@click.argument('topology_file', type=click.Path(exists=True))
@click.pass_context
def validate(ctx, topology_file):
    """Validate a topology without deploying."""
    api_url = ctx.obj['API_URL']
    
    with open(topology_file, 'r') as f:
        yaml_content = f.read()
        topo_data = yaml.safe_load(yaml_content)
        topo_name = topo_data.get('topology', {}).get('name', 'unknown')
    
    try:
        response = requests.post(
            f"{api_url}/api/v1/topologies/{topo_name}/validate",
            data=yaml_content,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('valid'):
            rprint(f"[green]✓[/green] Topology is valid")
        else:
            rprint(f"[red]✗[/red] Topology validation failed")
        
        errors = data.get('errors', [])
        if errors:
            rprint("\n[red]Errors:[/red]")
            for error in errors:
                rprint(f"  • {error}")
        
        warnings = data.get('warnings', [])
        if warnings:
            rprint("\n[yellow]Warnings:[/yellow]")
            for warning in warnings:
                rprint(f"  • {warning}")
        
        estimate = data.get('resource_estimate')
        if estimate:
            rprint("\n[bold]Resource Estimate:[/bold]")
            rprint(f"  CPU cores: {estimate.get('estimated_cpu_cores')}")
            rprint(f"  Memory: {estimate.get('estimated_memory_mb')} MB")
            rprint(f"  Nodes: {estimate.get('node_count')}")
            rprint(f"  Links: {estimate.get('link_count')}")
        
        if not data.get('valid'):
            raise click.Abort()
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]✗[/red] Failed to validate: {e}")
        raise click.Abort()


if __name__ == '__main__':
    cli()

