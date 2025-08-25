"""Time utilities for the backup system."""

import time
from datetime import datetime
from typing import Optional


def get_timestamp() -> float:
    """
    Get current Unix timestamp.
    
    Returns:
        Current time as Unix timestamp
    """
    return time.time()


def format_timestamp(timestamp: float, format_str: Optional[str] = None) -> str:
    """
    Format Unix timestamp as string.
    
    Args:
        timestamp: Unix timestamp
        format_str: Format string (default: ISO format)
    
    Returns:
        Formatted timestamp string
    """
    dt = datetime.fromtimestamp(timestamp)
    if format_str:
        return dt.strftime(format_str)
    return dt.isoformat()


def parse_timestamp(timestamp_str: str, format_str: Optional[str] = None) -> float:
    """
    Parse timestamp string to Unix timestamp.
    
    Args:
        timestamp_str: Timestamp string
        format_str: Format string (default: ISO format)
    
    Returns:
        Unix timestamp
    """
    if format_str:
        dt = datetime.strptime(timestamp_str, format_str)
    else:
        dt = datetime.fromisoformat(timestamp_str)
    return dt.timestamp()