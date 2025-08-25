"""Time utilities for the unified task scheduling library."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List, Tuple
import time
import calendar


def now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc).timestamp()


def from_timestamp(timestamp: float, tz: Optional[timezone] = None) -> datetime:
    """Convert timestamp to datetime."""
    if tz is None:
        tz = timezone.utc
    return datetime.fromtimestamp(timestamp, tz)


def to_timestamp(dt: datetime) -> float:
    """Convert datetime to timestamp."""
    return dt.timestamp()


def format_duration(duration: timedelta) -> str:
    """Format a timedelta as a human-readable string."""
    total_seconds = int(duration.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def parse_duration(duration_str: str) -> timedelta:
    """Parse a duration string into a timedelta."""
    # Simple parsing for formats like "1h30m", "2d", "45s"
    total_seconds = 0
    current_number = ""
    
    for char in duration_str.lower():
        if char.isdigit():
            current_number += char
        elif char in "dhms":
            if current_number:
                num = int(current_number)
                if char == 'd':
                    total_seconds += num * 86400
                elif char == 'h':
                    total_seconds += num * 3600
                elif char == 'm':
                    total_seconds += num * 60
                elif char == 's':
                    total_seconds += num
                current_number = ""
    
    return timedelta(seconds=total_seconds)


def business_hours_duration(start: datetime, end: datetime,
                          business_start: int = 9, business_end: int = 17,
                          weekdays_only: bool = True) -> timedelta:
    """Calculate duration considering only business hours."""
    if start >= end:
        return timedelta(0)
    
    total_seconds = 0
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    while current < end:
        # Skip weekends if weekdays_only
        if weekdays_only and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        
        # Calculate business hours for this day
        day_start = max(current.replace(hour=business_start), start)
        day_end = min(current.replace(hour=business_end), end)
        
        if day_start < day_end:
            total_seconds += (day_end - day_start).total_seconds()
        
        current += timedelta(days=1)
    
    return timedelta(seconds=total_seconds)


def next_business_day(dt: datetime, business_start: int = 9) -> datetime:
    """Get the next business day at business start time."""
    next_day = dt + timedelta(days=1)
    
    # Skip weekends
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    
    return next_day.replace(hour=business_start, minute=0, second=0, microsecond=0)


def time_until_next_occurrence(target_time: tuple, reference: Optional[datetime] = None) -> timedelta:
    """Calculate time until next occurrence of a specific time (hour, minute)."""
    if reference is None:
        reference = now()
    
    hour, minute = target_time
    target_today = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if target_today > reference:
        return target_today - reference
    else:
        # Target time has passed today, calculate for tomorrow
        target_tomorrow = target_today + timedelta(days=1)
        return target_tomorrow - reference


class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Start the timer."""
        self.start_time = time.perf_counter()
        self.end_time = None
    
    def stop(self) -> float:
        """Stop the timer and return elapsed time in seconds."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        self.end_time = time.perf_counter()
        return self.end_time - self.start_time
    
    def elapsed(self) -> float:
        """Get elapsed time without stopping the timer."""
        if self.start_time is None:
            return 0.0
        
        current_time = time.perf_counter()
        return current_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0,
                      backoff_factor: float = 2.0, max_delay: float = 60.0):
    """Retry a function with exponential backoff."""
    delay = base_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            time.sleep(min(delay, max_delay))
            delay *= backoff_factor


def schedule_at_interval(interval: timedelta, max_iterations: Optional[int] = None):
    """Decorator to schedule a function to run at regular intervals."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            iteration = 0
            while max_iterations is None or iteration < max_iterations:
                start_time = time.perf_counter()
                
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    print(f"Error in scheduled function: {e}")
                    result = None
                
                elapsed = time.perf_counter() - start_time
                sleep_time = max(0, interval.total_seconds() - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                iteration += 1
                
                if max_iterations == 1:
                    return result
            
            return None
        
        return wrapper
    
    return decorator