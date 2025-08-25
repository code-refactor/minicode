"""Event logging and management framework."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from collections import defaultdict


class EventType(Enum):
    """Common event types."""
    # Execution events
    INSTRUCTION_EXECUTE = "instruction_execute"
    INSTRUCTION_FETCH = "instruction_fetch"
    INSTRUCTION_DECODE = "instruction_decode"
    
    # Memory events
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    MEMORY_ALLOCATE = "memory_allocate"
    MEMORY_FREE = "memory_free"
    
    # Control flow events
    BRANCH_TAKEN = "branch_taken"
    BRANCH_NOT_TAKEN = "branch_not_taken"
    CALL = "call"
    RETURN = "return"
    
    # System events
    EXCEPTION = "exception"
    INTERRUPT = "interrupt"
    SYSCALL = "syscall"
    TRAP = "trap"
    
    # Thread/Process events
    THREAD_CREATE = "thread_create"
    THREAD_TERMINATE = "thread_terminate"
    THREAD_BLOCK = "thread_block"
    THREAD_UNBLOCK = "thread_unblock"
    CONTEXT_SWITCH = "context_switch"
    
    # Synchronization events
    LOCK_ACQUIRE = "lock_acquire"
    LOCK_RELEASE = "lock_release"
    LOCK_WAIT = "lock_wait"
    SEMAPHORE_WAIT = "semaphore_wait"
    SEMAPHORE_SIGNAL = "semaphore_signal"
    BARRIER_WAIT = "barrier_wait"
    
    # Security events
    PRIVILEGE_CHANGE = "privilege_change"
    PERMISSION_VIOLATION = "permission_violation"
    SECURITY_CHECK = "security_check"
    
    # Performance events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    TLB_HIT = "tlb_hit"
    TLB_MISS = "tlb_miss"
    
    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """Base event class."""
    
    timestamp: int  # Cycle or time
    event_type: EventType
    source: str  # Component that generated the event
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Event({self.timestamp}: {self.event_type.value} from {self.source})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'type': self.event_type.value,
            'source': self.source,
            'data': self.data,
            'metadata': self.metadata
        }


class EventLogger:
    """Centralized event logging system."""
    
    def __init__(self, max_events: Optional[int] = None):
        """Initialize event logger."""
        self.events: List[Event] = []
        self.max_events = max_events
        self.enabled = True
        self.filters: List[EventType] = []
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_counts: Dict[EventType, int] = defaultdict(int)
        
    def log(self, event: Event) -> None:
        """Log an event."""
        if not self.enabled:
            return
        
        # Apply filters
        if self.filters and event.event_type not in self.filters:
            return
        
        # Add event
        self.events.append(event)
        self.event_counts[event.event_type] += 1
        
        # Enforce max events
        if self.max_events and len(self.events) > self.max_events:
            self.events.pop(0)
        
        # Notify subscribers
        self._notify_subscribers(event)
    
    def log_event(
        self,
        timestamp: int,
        event_type: EventType,
        source: str,
        **data
    ) -> None:
        """Convenience method to log an event."""
        event = Event(
            timestamp=timestamp,
            event_type=event_type,
            source=source,
            data=data
        )
        self.log(event)
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type."""
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from events."""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
    
    def _notify_subscribers(self, event: Event) -> None:
        """Notify subscribers of an event."""
        for callback in self.subscribers[event.event_type]:
            try:
                callback(event)
            except Exception:
                # Ignore errors in subscribers
                pass
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Event]:
        """Get filtered events."""
        result = self.events
        
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        
        if source is not None:
            result = [e for e in result if e.source == source]
        
        if start_time is not None:
            result = [e for e in result if e.timestamp >= start_time]
        
        if end_time is not None:
            result = [e for e in result if e.timestamp <= end_time]
        
        return result
    
    def get_event_counts(self) -> Dict[str, int]:
        """Get count of events by type."""
        return {k.value: v for k, v in self.event_counts.items()}
    
    def set_filters(self, event_types: List[EventType]) -> None:
        """Set event type filters."""
        self.filters = event_types
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        self.filters = []
    
    def enable(self) -> None:
        """Enable logging."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable logging."""
        self.enabled = False
    
    def clear(self) -> None:
        """Clear all events."""
        self.events.clear()
        self.event_counts.clear()
    
    def export(self) -> List[Dict[str, Any]]:
        """Export events as list of dictionaries."""
        return [event.to_dict() for event in self.events]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logger statistics."""
        return {
            'total_events': len(self.events),
            'event_types': len(self.event_counts),
            'enabled': self.enabled,
            'has_filters': bool(self.filters),
            'subscriber_count': sum(len(subs) for subs in self.subscribers.values()),
            'event_counts': self.get_event_counts()
        }
    
    def __len__(self) -> int:
        """Get number of events."""
        return len(self.events)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"EventLogger({len(self.events)} events, {len(self.event_counts)} types)"