"""
Scenario Scheduler - Manages persistent and transient impairment scenarios.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from icalendar import Calendar, Event as ICalEvent
import recurring_ical_events
from dateutil import parser as date_parser

from ..models.scenario import Scenario, ScenarioType, ScenarioSet
from ..models.event import Event, EventType, EventSeverity
from ..impairments.netem import ImpairmentEngine

logger = logging.getLogger(__name__)


class ScenarioScheduler:
    """Schedules and executes network impairment scenarios."""

    def __init__(self, network_topology, event_logger=None):
        """
        Initialize scenario scheduler.
        
        Args:
            network_topology: NetworkTopology instance
            event_logger: Optional event logger
        """
        self.network = network_topology
        self.impairment_engine = ImpairmentEngine(network_topology)
        self.event_logger = event_logger
        
        self.scheduler = BackgroundScheduler()
        self.scenarios: Dict[str, Scenario] = {}
        self.active_scenarios: Dict[str, Dict[str, Any]] = {}
        
        self.scheduler.start()
        logger.info("Scenario scheduler started")
    
    def add_scenario(self, scenario: Scenario):
        """
        Add a scenario to the scheduler.
        
        Args:
            scenario: Scenario definition
        """
        self.scenarios[scenario.id] = scenario
        
        if scenario.type == ScenarioType.PERSISTENT:
            # Apply persistent scenarios immediately
            self._apply_scenario(scenario)
        elif scenario.type == ScenarioType.TRANSIENT:
            # Schedule transient scenarios
            self._schedule_transient(scenario)
        
        logger.info(f"Added scenario: {scenario.id} ({scenario.type.value})")
    
    def add_scenarios(self, scenario_set: ScenarioSet):
        """Add multiple scenarios from a scenario set."""
        for scenario in scenario_set.persistent:
            self.add_scenario(scenario)
        
        for scenario in scenario_set.transient:
            self.add_scenario(scenario)
    
    def _schedule_transient(self, scenario: Scenario):
        """Schedule a transient scenario."""
        if not scenario.schedule:
            logger.error(f"Scenario {scenario.id} has no schedule")
            return
        
        # Parse schedule
        if scenario.schedule.startswith("RRULE:"):
            # RRULE format
            self._schedule_rrule(scenario)
        elif scenario.schedule.startswith("FREQ="):
            # RRULE without prefix
            self._schedule_rrule(scenario, rrule_str=f"RRULE:{scenario.schedule}")
        else:
            # Try cron format
            self._schedule_cron(scenario)
    
    def _schedule_rrule(self, scenario: Scenario, rrule_str: str = None):
        """Schedule scenario using RRULE."""
        try:
            # Create iCalendar event from RRULE
            rrule = rrule_str or scenario.schedule
            
            # Parse duration
            duration_seconds = self._parse_duration(scenario.duration or "PT15M")
            
            # Schedule job to check and trigger at regular intervals
            # For RRULE, we check every minute if we should trigger
            job_id = f"rrule_{scenario.id}"
            
            self.scheduler.add_job(
                func=self._check_rrule_trigger,
                trigger='interval',
                minutes=1,
                id=job_id,
                args=[scenario, rrule, duration_seconds],
                replace_existing=True
            )
            
            logger.info(f"Scheduled RRULE scenario: {scenario.id} - {rrule}")
            
        except Exception as e:
            logger.error(f"Failed to schedule RRULE scenario {scenario.id}: {e}")
    
    def _schedule_cron(self, scenario: Scenario):
        """Schedule scenario using cron expression."""
        try:
            # Parse cron expression
            trigger = CronTrigger.from_crontab(scenario.schedule)
            
            duration_seconds = self._parse_duration(scenario.duration or "PT15M")
            
            # Schedule start job
            job_id = f"cron_start_{scenario.id}"
            self.scheduler.add_job(
                func=self._start_scenario,
                trigger=trigger,
                id=job_id,
                args=[scenario, duration_seconds],
                replace_existing=True
            )
            
            logger.info(f"Scheduled cron scenario: {scenario.id} - {scenario.schedule}")
            
        except Exception as e:
            logger.error(f"Failed to schedule cron scenario {scenario.id}: {e}")
    
    def _check_rrule_trigger(self, scenario: Scenario, rrule: str, duration_seconds: int):
        """Check if RRULE scenario should trigger now."""
        # Simple implementation - in production, use proper RRULE library
        # For now, just trigger based on simplified parsing
        
        if scenario.id in self.active_scenarios:
            # Already running
            return
        
        # Check if we should trigger (simplified)
        # In production, properly parse RRULE and check against current time
        logger.debug(f"Checking RRULE trigger for {scenario.id}")
        
        # For demo purposes, we'll trigger based on simple time checks
        # Real implementation would use dateutil.rrule or similar
    
    def _start_scenario(self, scenario: Scenario, duration_seconds: int):
        """Start a transient scenario."""
        if scenario.id in self.active_scenarios:
            logger.warning(f"Scenario {scenario.id} already active")
            return
        
        logger.info(f"Starting scenario: {scenario.id}")
        
        # Apply impairments
        success = self._apply_scenario(scenario)
        
        if success:
            # Track active scenario
            start_time = datetime.utcnow()
            self.active_scenarios[scenario.id] = {
                "scenario": scenario,
                "start_time": start_time,
                "end_time": start_time + timedelta(seconds=duration_seconds)
            }
            
            # Log event
            self._log_event(EventType.SCENARIO_STARTED, scenario)
            
            # Schedule end
            self.scheduler.add_job(
                func=self._end_scenario,
                trigger='date',
                run_date=start_time + timedelta(seconds=duration_seconds),
                id=f"end_{scenario.id}",
                args=[scenario],
                replace_existing=True
            )
        else:
            self._log_event(EventType.SCENARIO_FAILED, scenario, 
                          severity=EventSeverity.ERROR)
    
    def _end_scenario(self, scenario: Scenario):
        """End a transient scenario."""
        if scenario.id not in self.active_scenarios:
            logger.warning(f"Scenario {scenario.id} not active")
            return
        
        logger.info(f"Ending scenario: {scenario.id}")
        
        # Remove impairments
        self._remove_scenario(scenario)
        
        # Remove from active scenarios
        del self.active_scenarios[scenario.id]
        
        # Log event
        self._log_event(EventType.SCENARIO_ENDED, scenario)
    
    def _apply_scenario(self, scenario: Scenario) -> bool:
        """Apply scenario impairments."""
        try:
            # Parse target
            target = scenario.parse_target()
            
            # Apply impairments based on target type
            if scenario.impairments.netem:
                if target["type"] == "link":
                    success = self.impairment_engine.apply_to_link(
                        target["src"], target["dst"], scenario.impairments.netem
                    )
                elif target["type"] == "path":
                    success = self.impairment_engine.apply_to_path(
                        target["nodes"], scenario.impairments.netem
                    )
                elif target["type"] == "node":
                    success = self.impairment_engine.apply_to_node(
                        target["id"], scenario.impairments.netem
                    )
                else:
                    logger.error(f"Unknown target type: {target['type']}")
                    return False
                
                if success:
                    self._log_event(EventType.IMPAIRMENT_APPLIED, scenario)
                
                return success
            
            # TODO: Handle other impairment types (qdisc, control_plane, security)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply scenario {scenario.id}: {e}")
            return False
    
    def _remove_scenario(self, scenario: Scenario) -> bool:
        """Remove scenario impairments."""
        try:
            target = scenario.parse_target()
            
            if scenario.impairments.netem:
                if target["type"] == "link":
                    success = self.impairment_engine.clear_link(
                        target["src"], target["dst"]
                    )
                elif target["type"] == "path":
                    success = self.impairment_engine.clear_path(
                        target["nodes"]
                    )
                elif target["type"] == "node":
                    success = self.impairment_engine.clear_node(
                        target["id"]
                    )
                else:
                    return False
                
                if success:
                    self._log_event(EventType.IMPAIRMENT_REMOVED, scenario)
                
                return success
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove scenario {scenario.id}: {e}")
            return False
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration to seconds.
        
        Args:
            duration_str: Duration string (e.g., 'PT15M', 'PT1H30M')
            
        Returns:
            Duration in seconds
        """
        # Simple parser for common formats
        duration_str = duration_str.upper()
        if not duration_str.startswith('PT'):
            # Try parsing as integer seconds
            return int(duration_str)
        
        duration_str = duration_str[2:]  # Remove 'PT'
        seconds = 0
        
        # Parse hours
        if 'H' in duration_str:
            hours, duration_str = duration_str.split('H', 1)
            seconds += int(hours) * 3600
        
        # Parse minutes
        if 'M' in duration_str:
            minutes, duration_str = duration_str.split('M', 1)
            seconds += int(minutes) * 60
        
        # Parse seconds
        if 'S' in duration_str:
            secs, _ = duration_str.split('S', 1)
            seconds += int(secs)
        
        return seconds
    
    def _log_event(self, event_type: EventType, scenario: Scenario, 
                   severity: EventSeverity = EventSeverity.INFO):
        """Log an event."""
        if not self.event_logger:
            return
        
        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            severity=severity,
            scenario_id=scenario.id,
            topology_name=self.network.topology.name,
            message=f"{event_type.value}: {scenario.id}",
            details={"scenario": scenario.dict()}
        )
        
        self.event_logger.log(event)
    
    def remove_scenario(self, scenario_id: str):
        """Remove a scenario from the scheduler."""
        if scenario_id not in self.scenarios:
            return
        
        scenario = self.scenarios[scenario_id]
        
        # Remove from active scenarios
        if scenario_id in self.active_scenarios:
            self._end_scenario(scenario)
        
        # Remove scheduled jobs
        for job in self.scheduler.get_jobs():
            if scenario_id in job.id:
                self.scheduler.remove_job(job.id)
        
        # Remove from scenarios
        del self.scenarios[scenario_id]
        
        logger.info(f"Removed scenario: {scenario_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "total_scenarios": len(self.scenarios),
            "active_scenarios": len(self.active_scenarios),
            "scheduled_jobs": len(self.scheduler.get_jobs()),
            "scenarios": {
                sid: {
                    "type": s.type.value,
                    "active": sid in self.active_scenarios
                }
                for sid, s in self.scenarios.items()
            }
        }
    
    def shutdown(self):
        """Shutdown the scheduler."""
        logger.info("Shutting down scenario scheduler")
        
        # End all active scenarios
        for scenario_id in list(self.active_scenarios.keys()):
            scenario = self.scenarios[scenario_id]
            self._end_scenario(scenario)
        
        # Shutdown scheduler
        self.scheduler.shutdown(wait=False)


def main():
    """Main entry point for standalone scheduler."""
    import sys
    from ..control.compiler import TopologyCompiler
    from ..dataplane.mininet_topo import create_network
    
    if len(sys.argv) < 2:
        print("Usage: python -m netemulator.control.scheduler <topology.yaml>")
        sys.exit(1)
    
    # Load topology
    compiler = TopologyCompiler()
    compiler.load_from_yaml(sys.argv[1])
    
    # Create network
    network = create_network(compiler.topology, auto_start=True)
    
    # Create and start scheduler
    scheduler = ScenarioScheduler(network)
    
    if compiler.scenarios:
        scheduler.add_scenarios(compiler.scenarios)
    
    print(f"Scheduler running with {len(scheduler.scenarios)} scenarios")
    print("Press Ctrl+C to stop...")
    
    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        scheduler.shutdown()
        network.stop()


if __name__ == "__main__":
    main()

