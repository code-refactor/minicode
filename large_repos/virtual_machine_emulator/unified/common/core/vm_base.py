"""Abstract base class for virtual machine implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from .state import VMState, ExecutionStats
from .program import Program


class VMBase(ABC):
    """Abstract base class for all VM implementations."""
    
    def __init__(self, **kwargs):
        """Initialize base VM components."""
        self.state = VMState.IDLE
        self.stats = ExecutionStats()
        self.program: Optional[Program] = None
        self.max_cycles = kwargs.get('max_cycles', 1000000)
        self.debug = kwargs.get('debug', False)
        self.events: List[Dict[str, Any]] = []
        
    @abstractmethod
    def load_program(self, program: Program) -> None:
        """Load a program into the VM."""
        self.program = program
        self.state = VMState.IDLE
        self.stats = ExecutionStats()
        self.events.clear()
    
    @abstractmethod
    def step(self) -> bool:
        """Execute a single step/cycle. Returns True if execution continues."""
        pass
    
    @abstractmethod
    def run(self, max_cycles: Optional[int] = None) -> ExecutionStats:
        """Run the VM until completion or max cycles."""
        if max_cycles is None:
            max_cycles = self.max_cycles
        
        self.state = VMState.RUNNING
        cycles = 0
        
        while cycles < max_cycles and self.state == VMState.RUNNING:
            if not self.step():
                break
            cycles += 1
            self.stats.cycles = cycles
        
        if self.state == VMState.RUNNING:
            self.state = VMState.FINISHED
        
        return self.stats
    
    @abstractmethod
    def reset(self) -> None:
        """Reset VM to initial state."""
        self.state = VMState.IDLE
        self.stats = ExecutionStats()
        self.events.clear()
    
    def pause(self) -> None:
        """Pause execution."""
        if self.state == VMState.RUNNING:
            self.state = VMState.PAUSED
    
    def resume(self) -> None:
        """Resume execution."""
        if self.state == VMState.PAUSED:
            self.state = VMState.RUNNING
    
    def stop(self) -> None:
        """Stop execution."""
        self.state = VMState.FINISHED
    
    def get_state(self) -> VMState:
        """Get current VM state."""
        return self.state
    
    def get_statistics(self) -> ExecutionStats:
        """Get execution statistics."""
        return self.stats
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event for analysis."""
        event = {
            'cycle': self.stats.cycles,
            'type': event_type,
            'data': data
        }
        self.events.append(event)
        
        if self.debug:
            print(f"[{self.stats.cycles}] {event_type}: {data}")
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logged events, optionally filtered by type."""
        if event_type is None:
            return self.events
        return [e for e in self.events if e['type'] == event_type]
    
    def is_running(self) -> bool:
        """Check if VM is running."""
        return self.state == VMState.RUNNING
    
    def is_finished(self) -> bool:
        """Check if VM has finished execution."""
        return self.state == VMState.FINISHED
    
    @abstractmethod
    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get execution trace for analysis."""
        pass
    
    def __repr__(self) -> str:
        """String representation of VM."""
        return f"{self.__class__.__name__}(state={self.state.name}, cycles={self.stats.cycles})"