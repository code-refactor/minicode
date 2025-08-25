"""Thread implementation for the VM."""

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union

from vm_emulator.core.processor import ProcessorState


class ThreadPriority(Enum):
    """Thread priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    REAL_TIME = 3


@dataclass
class Thread:
    """
    Enhanced thread representation with additional features
    for the thread management system.
    """
    thread_id: str
    program_id: str
    pc: int  # Program counter
    registers: Dict[str, int] = field(default_factory=dict)
    stack: List[int] = field(default_factory=list)
    state: ProcessorState = ProcessorState.WAITING
    processor_id: Optional[int] = None  # Processor running this thread
    parent_thread_id: Optional[str] = None
    creation_time: int = 0
    execution_cycles: int = 0
    priority: ThreadPriority = ThreadPriority.NORMAL
    
    # Thread statistics
    context_switches: int = 0
    cpu_bursts: List[int] = field(default_factory=list)  # Duration of each CPU burst
    wait_times: List[int] = field(default_factory=list)  # Duration of each wait period
    lock_acquisitions: int = 0
    lock_contentions: int = 0
    barrier_waits: int = 0
    
    # For deterministic execution
    random_seed: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Initialize with default registers if not provided."""
        if not self.registers:
            # General purpose registers R0-R15
            for i in range(16):
                self.registers[f"R{i}"] = 0
            
            # Special registers
            self.registers["SP"] = 0  # Stack pointer
            self.registers["FP"] = 0  # Frame pointer
            self.registers["FLAGS"] = 0  # Status flags
    
    def is_running(self) -> bool:
        """Check if thread is running."""
        return self.state == ProcessorState.RUNNING
    
    def is_waiting(self) -> bool:
        """Check if thread is waiting."""
        return self.state == ProcessorState.WAITING
    
    def is_blocked(self) -> bool:
        """Check if thread is blocked."""
        return self.state == ProcessorState.BLOCKED
    
    def is_terminated(self) -> bool:
        """Check if thread is terminated."""
        return self.state == ProcessorState.TERMINATED
    
    def calculate_cpu_usage(self, total_cycles: int) -> float:
        """
        Calculate CPU usage percentage.
        
        Args:
            total_cycles: Total clock cycles elapsed
            
        Returns:
            CPU usage as percentage (0-100)
        """
        if total_cycles == 0:
            return 0.0
        
        return (self.execution_cycles / total_cycles) * 100
    
    def calculate_average_wait_time(self) -> float:
        """
        Calculate average wait time.
        
        Returns:
            Average wait time in cycles
        """
        if not self.wait_times:
            return 0.0
        
        return sum(self.wait_times) / len(self.wait_times)
    
    def calculate_average_cpu_burst(self) -> float:
        """
        Calculate average CPU burst time.
        
        Returns:
            Average CPU burst in cycles
        """
        if not self.cpu_bursts:
            return 0.0
        
        return sum(self.cpu_bursts) / len(self.cpu_bursts)
    
    def get_statistics(self) -> Dict[str, Union[int, float, List[int]]]:
        """
        Get thread statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "thread_id": self.thread_id,
            "program_id": self.program_id,
            "state": self.state.name,
            "execution_cycles": self.execution_cycles,
            "context_switches": self.context_switches,
            "cpu_bursts": self.cpu_bursts,
            "wait_times": self.wait_times,
            "lock_acquisitions": self.lock_acquisitions,
            "lock_contentions": self.lock_contentions,
            "barrier_waits": self.barrier_waits,
            "average_wait_time": self.calculate_average_wait_time(),
            "average_cpu_burst": self.calculate_average_cpu_burst(),
            "priority": self.priority.name,
        }
    
    def apply_state_snapshot(self, snapshot: Dict) -> None:
        """
        Apply a state snapshot to restore thread state.
        
        Args:
            snapshot: Thread state snapshot dictionary
        """
        self.pc = snapshot["pc"]
        self.registers = snapshot["registers"].copy()
        self.stack = snapshot["stack"].copy()
        self.state = ProcessorState[snapshot["state"]]
        self.processor_id = snapshot["processor_id"]
        self.execution_cycles = snapshot["execution_cycles"]
        self.priority = ThreadPriority[snapshot["priority"]]
    
    def create_state_snapshot(self) -> Dict:
        """
        Create a snapshot of the thread's state.
        
        Returns:
            Thread state snapshot dictionary
        """
        return {
            "thread_id": self.thread_id,
            "program_id": self.program_id,
            "pc": self.pc,
            "registers": self.registers.copy(),
            "stack": self.stack.copy(),
            "state": self.state.name,
            "processor_id": self.processor_id,
            "parent_thread_id": self.parent_thread_id,
            "creation_time": self.creation_time,
            "execution_cycles": self.execution_cycles,
            "priority": self.priority.name,
        }