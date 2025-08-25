"""Utility functions and models for the task scheduler."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

from pydantic import BaseModel, Field

T = TypeVar("T")


class TimeRange(BaseModel):
    """A time range with start and end times."""

    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    
    def duration(self) -> timedelta:
        """Get the duration of this time range."""
        return self.end_time - self.start_time
    
    def contains(self, time: datetime) -> bool:
        """Check if this range contains the specified time."""
        return self.start_time <= time <= self.end_time
    
    def overlaps(self, other: TimeRange) -> bool:
        """Check if this range overlaps with another range."""
        return (self.start_time <= other.end_time and 
                self.end_time >= other.start_time)
    
    def intersection(self, other: TimeRange) -> Optional[TimeRange]:
        """Get the intersection of this range with another range."""
        if not self.overlaps(other):
            return None
        
        start = max(self.start_time, other.start_time)
        end = min(self.end_time, other.end_time)
        
        return TimeRange(start_time=start, end_time=end)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


def datetime_parser(json_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Parse datetime strings in JSON data."""
    for key, value in json_dict.items():
        if isinstance(value, str) and len(value) > 10:
            try:
                json_dict[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
    return json_dict


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix."""
    random_part = ''.join(random.choices('0123456789abcdef', k=16))
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{random_part}" if prefix else f"{timestamp}_{random_part}"


class Result(BaseModel, Generic[T]):
    """A result that can be either successful or an error."""
    
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    
    # Allow extra fields
    class Config:
        extra = "allow"
    
    @classmethod
    def ok(cls, value: T) -> Result[T]:
        """Create a successful result."""
        return cls(success=True, value=value)
    
    @classmethod
    def err(cls, error: str) -> Result[T]:
        """Create an error result."""
        return cls(success=False, error=error)


class SystemEvent(BaseModel):
    """An event in the system that requires attention or logging."""
    
    id: str = Field(default_factory=lambda: generate_id("event"))
    event_time: datetime = Field(default_factory=datetime.now)
    event_type: str
    severity: str  # info, warning, error, critical
    source: str
    details: Dict[str, Any] = Field(default_factory=dict)
    related_ids: Dict[str, str] = Field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_time: Optional[datetime] = None
    
    def acknowledge(self, user_id: str) -> None:
        """Acknowledge this event."""
        self.acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_time = datetime.now()
    
    def is_critical(self) -> bool:
        """Check if this is a critical event."""
        return self.severity == "critical"


class PerformanceMetric(BaseModel):
    """A performance metric for the system."""
    
    metric_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    value: float
    unit: str
    context: Dict[str, str] = Field(default_factory=dict)
    
    def is_within_threshold(self, threshold: float, higher_is_better: bool = True) -> bool:
        """Check if the metric is within the specified threshold."""
        if higher_is_better:
            return self.value >= threshold
        return self.value <= threshold