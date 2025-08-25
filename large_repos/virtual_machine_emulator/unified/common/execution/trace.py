"""Execution tracing framework."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class TraceEventType(Enum):
    """Types of trace events."""
    INSTRUCTION = "instruction"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    REGISTER_CHANGE = "register_change"
    BRANCH_TAKEN = "branch_taken"
    EXCEPTION = "exception"
    SYSCALL = "syscall"
    CONTEXT_SWITCH = "context_switch"
    SYNCHRONIZATION = "synchronization"
    INTERRUPT = "interrupt"


@dataclass
class TraceEvent:
    """Single trace event."""
    
    cycle: int
    event_type: TraceEventType
    processor_id: Optional[int] = None
    thread_id: Optional[int] = None
    address: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        """String representation."""
        addr_str = f" @0x{self.address:x}" if self.address is not None else ""
        return f"TraceEvent({self.cycle}: {self.event_type.value}{addr_str})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cycle': self.cycle,
            'type': self.event_type.value,
            'processor_id': self.processor_id,
            'thread_id': self.thread_id,
            'address': self.address,
            'data': self.data
        }


class ExecutionTrace:
    """Execution trace collector."""
    
    def __init__(self, max_events: Optional[int] = None):
        """Initialize trace collector."""
        self.events: List[TraceEvent] = []
        self.max_events = max_events
        self.enabled = True
        self.filters: List[TraceEventType] = []
        
    def add_event(self, event: TraceEvent) -> None:
        """Add an event to the trace."""
        if not self.enabled:
            return
        
        # Apply filters
        if self.filters and event.event_type not in self.filters:
            return
        
        self.events.append(event)
        
        # Limit trace size
        if self.max_events and len(self.events) > self.max_events:
            self.events.pop(0)
    
    def add_instruction(
        self,
        cycle: int,
        address: int,
        instruction: str,
        processor_id: Optional[int] = None,
        thread_id: Optional[int] = None
    ) -> None:
        """Add instruction execution event."""
        self.add_event(TraceEvent(
            cycle=cycle,
            event_type=TraceEventType.INSTRUCTION,
            processor_id=processor_id,
            thread_id=thread_id,
            address=address,
            data={'instruction': instruction}
        ))
    
    def add_memory_access(
        self,
        cycle: int,
        address: int,
        size: int,
        value: int,
        is_write: bool,
        processor_id: Optional[int] = None,
        thread_id: Optional[int] = None
    ) -> None:
        """Add memory access event."""
        event_type = TraceEventType.MEMORY_WRITE if is_write else TraceEventType.MEMORY_READ
        self.add_event(TraceEvent(
            cycle=cycle,
            event_type=event_type,
            processor_id=processor_id,
            thread_id=thread_id,
            address=address,
            data={'size': size, 'value': value}
        ))
    
    def add_branch(
        self,
        cycle: int,
        from_address: int,
        to_address: int,
        taken: bool,
        processor_id: Optional[int] = None,
        thread_id: Optional[int] = None
    ) -> None:
        """Add branch event."""
        if taken:
            self.add_event(TraceEvent(
                cycle=cycle,
                event_type=TraceEventType.BRANCH_TAKEN,
                processor_id=processor_id,
                thread_id=thread_id,
                address=from_address,
                data={'target': to_address}
            ))
    
    def add_exception(
        self,
        cycle: int,
        exception_type: str,
        message: str,
        processor_id: Optional[int] = None,
        thread_id: Optional[int] = None
    ) -> None:
        """Add exception event."""
        self.add_event(TraceEvent(
            cycle=cycle,
            event_type=TraceEventType.EXCEPTION,
            processor_id=processor_id,
            thread_id=thread_id,
            data={'type': exception_type, 'message': message}
        ))
    
    def enable(self) -> None:
        """Enable tracing."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable tracing."""
        self.enabled = False
    
    def set_filters(self, event_types: List[TraceEventType]) -> None:
        """Set event type filters."""
        self.filters = event_types
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        self.filters = []
    
    def clear(self) -> None:
        """Clear all events."""
        self.events.clear()
    
    def get_events(
        self,
        event_type: Optional[TraceEventType] = None,
        processor_id: Optional[int] = None,
        thread_id: Optional[int] = None,
        start_cycle: Optional[int] = None,
        end_cycle: Optional[int] = None
    ) -> List[TraceEvent]:
        """Get filtered events."""
        result = self.events
        
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        
        if processor_id is not None:
            result = [e for e in result if e.processor_id == processor_id]
        
        if thread_id is not None:
            result = [e for e in result if e.thread_id == thread_id]
        
        if start_cycle is not None:
            result = [e for e in result if e.cycle >= start_cycle]
        
        if end_cycle is not None:
            result = [e for e in result if e.cycle <= end_cycle]
        
        return result
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert trace to list of dictionaries."""
        return [event.to_dict() for event in self.events]
    
    def __len__(self) -> int:
        """Get number of events."""
        return len(self.events)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ExecutionTrace({len(self.events)} events)"