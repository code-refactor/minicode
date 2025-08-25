"""Execution context and result classes."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from ..core.state import ExecutionStats


@dataclass
class ExecutionContext:
    """Context for instruction execution."""
    
    cycle: int = 0
    processor_id: int = 0
    thread_id: Optional[int] = None
    instruction_address: int = 0
    privilege_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def copy(self) -> 'ExecutionContext':
        """Create a copy of the context."""
        return ExecutionContext(
            cycle=self.cycle,
            processor_id=self.processor_id,
            thread_id=self.thread_id,
            instruction_address=self.instruction_address,
            privilege_level=self.privilege_level,
            metadata=dict(self.metadata)
        )


@dataclass
class ExecutionResult:
    """Result of program execution."""
    
    success: bool = True
    cycles: int = 0
    instructions_executed: int = 0
    final_state: Dict[str, Any] = field(default_factory=dict)
    output: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    statistics: ExecutionStats = field(default_factory=ExecutionStats)
    events: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    
    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return f"ExecutionResult(success=True, cycles={self.cycles}, instructions={self.instructions_executed})"
        else:
            return f"ExecutionResult(success=False, error='{self.error}')"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'cycles': self.cycles,
            'instructions_executed': self.instructions_executed,
            'final_state': self.final_state,
            'output': self.output,
            'error': self.error,
            'statistics': self.statistics.to_dict() if self.statistics else {},
            'event_count': len(self.events),
            'trace_length': len(self.trace)
        }


@dataclass
class ThreadContext:
    """Context for thread execution in parallel VMs."""
    
    thread_id: int
    priority: int = 0
    affinity: Optional[int] = None  # Preferred processor
    state: str = "NEW"
    registers: Dict[str, int] = field(default_factory=dict)
    stack: List[int] = field(default_factory=list)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ThreadContext(id={self.thread_id}, state={self.state}, priority={self.priority})"


@dataclass  
class SecurityContext:
    """Context for security-aware execution."""
    
    privilege_level: int = 0
    uid: int = 0
    gid: int = 0
    capabilities: List[str] = field(default_factory=list)
    sandboxed: bool = False
    memory_limits: Dict[str, int] = field(default_factory=dict)
    allowed_syscalls: List[str] = field(default_factory=list)
    
    def has_capability(self, capability: str) -> bool:
        """Check if context has a capability."""
        return capability in self.capabilities
    
    def can_execute_syscall(self, syscall: str) -> bool:
        """Check if syscall is allowed."""
        return not self.allowed_syscalls or syscall in self.allowed_syscalls