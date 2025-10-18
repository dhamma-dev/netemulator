"""Time synchronization and alignment utilities."""

import time
from datetime import datetime, timedelta
from typing import Optional


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.utcnow()


def get_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def parse_iso_duration(duration_str: str) -> timedelta:
    """
    Parse ISO 8601 duration to timedelta.
    
    Args:
        duration_str: ISO 8601 duration string (e.g., 'PT15M', 'PT1H30M')
        
    Returns:
        timedelta object
    """
    duration_str = duration_str.upper()
    if not duration_str.startswith('PT'):
        raise ValueError(f"Invalid ISO duration format: {duration_str}")
    
    duration_str = duration_str[2:]  # Remove 'PT'
    
    hours = 0
    minutes = 0
    seconds = 0
    
    # Parse hours
    if 'H' in duration_str:
        hours_str, duration_str = duration_str.split('H', 1)
        hours = int(hours_str)
    
    # Parse minutes
    if 'M' in duration_str:
        minutes_str, duration_str = duration_str.split('M', 1)
        minutes = int(minutes_str)
    
    # Parse seconds
    if 'S' in duration_str:
        seconds_str, _ = duration_str.split('S', 1)
        seconds = int(seconds_str)
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def format_duration(td: timedelta) -> str:
    """
    Format timedelta as human-readable string.
    
    Args:
        td: timedelta object
        
    Returns:
        Formatted string (e.g., '1h 30m 15s')
    """
    total_seconds = int(td.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def sleep_until(target_time: datetime) -> bool:
    """
    Sleep until a target time.
    
    Args:
        target_time: Target datetime (UTC)
        
    Returns:
        True if slept, False if target time already passed
    """
    now = get_utc_now()
    if target_time <= now:
        return False
    
    sleep_seconds = (target_time - now).total_seconds()
    time.sleep(sleep_seconds)
    return True


def align_to_second_boundary(offset_ms: int = 0) -> None:
    """
    Sleep until the next second boundary (plus optional offset).
    
    Args:
        offset_ms: Millisecond offset from second boundary
    """
    now = time.time()
    next_second = int(now) + 1
    target = next_second + (offset_ms / 1000.0)
    sleep_time = target - now
    
    if sleep_time > 0:
        time.sleep(sleep_time)

