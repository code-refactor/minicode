"""Common state definitions and enums for VM implementations."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any, Optional


class VMState(Enum):
    """Virtual machine execution states."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()
    ERROR = auto()


class ProcessorState(Enum):
    """Processor execution states."""
    IDLE = auto()
    EXECUTING = auto()
    WAITING = auto()
    HALTED = auto()


class ThreadState(Enum):
    """Thread execution states."""
    NEW = auto()
    READY = auto()
    RUNNING = auto()
    BLOCKED = auto()
    WAITING = auto()
    TERMINATED = auto()


class MemoryPermission(Enum):
    """Memory access permissions."""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4
    READ_WRITE = 3
    READ_EXECUTE = 5
    WRITE_EXECUTE = 6
    READ_WRITE_EXECUTE = 7


class InstructionType(Enum):
    """Common instruction categories."""
    NOP = auto()
    ARITHMETIC = auto()
    LOGIC = auto()
    MEMORY = auto()
    BRANCH = auto()
    SYSTEM = auto()
    SYNC = auto()
    PRIVILEGED = auto()


@dataclass
class ExecutionStats:
    """Common execution statistics."""
    cycles: int = 0
    instructions_executed: int = 0
    memory_reads: int = 0
    memory_writes: int = 0
    branches_taken: int = 0
    exceptions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'cycles': self.cycles,
            'instructions_executed': self.instructions_executed,
            'memory_reads': self.memory_reads,
            'memory_writes': self.memory_writes,
            'branches_taken': self.branches_taken,
            'exceptions': self.exceptions
        }
    
    def update(self, other: 'ExecutionStats') -> None:
        """Update statistics with values from another instance."""
        self.cycles += other.cycles
        self.instructions_executed += other.instructions_executed
        self.memory_reads += other.memory_reads
        self.memory_writes += other.memory_writes
        self.branches_taken += other.branches_taken
        self.exceptions += other.exceptions