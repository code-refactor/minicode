"""Abstract base class for processor implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .state import ProcessorState
from .instruction import Instruction
from .registers import RegisterFile


class ProcessorBase(ABC):
    """Abstract base class for processor implementations."""
    
    def __init__(self, processor_id: int = 0, **kwargs):
        """Initialize base processor components."""
        self.processor_id = processor_id
        self.state = ProcessorState.IDLE
        self.registers = RegisterFile()
        self.cycle_count = 0
        self.instruction_count = 0
        self.current_instruction: Optional[Instruction] = None
        self.debug = kwargs.get('debug', False)
        
    @abstractmethod
    def execute_instruction(self, instruction: Instruction) -> bool:
        """Execute a single instruction. Returns True on success."""
        pass
    
    def fetch_decode_execute(self, instruction: Instruction) -> bool:
        """Common fetch-decode-execute cycle."""
        # Fetch
        self.current_instruction = instruction
        self.cycle_count += 1
        
        # Decode (handled by instruction object)
        
        # Execute
        success = self.execute_instruction(instruction)
        
        if success:
            self.instruction_count += 1
            # Update PC unless it was modified by the instruction
            if instruction.instruction_type.name not in ['BRANCH', 'SYSTEM']:
                self.registers.program_counter += instruction.size
        
        return success
    
    def reset(self) -> None:
        """Reset processor to initial state."""
        self.state = ProcessorState.IDLE
        self.registers.reset()
        self.cycle_count = 0
        self.instruction_count = 0
        self.current_instruction = None
    
    def get_state(self) -> ProcessorState:
        """Get current processor state."""
        return self.state
    
    def set_state(self, state: ProcessorState) -> None:
        """Set processor state."""
        self.state = state
    
    def get_register(self, name: str) -> int:
        """Get register value."""
        return self.registers.get_register(name)
    
    def set_register(self, name: str, value: int) -> None:
        """Set register value."""
        self.registers.set_register(name, value)
    
    def get_program_counter(self) -> int:
        """Get program counter."""
        return self.registers.program_counter
    
    def set_program_counter(self, value: int) -> None:
        """Set program counter."""
        self.registers.program_counter = value
    
    def get_flags(self) -> int:
        """Get flags register."""
        return self.registers.flags
    
    def set_flags(self, value: int) -> None:
        """Set flags register."""
        self.registers.flags = value
    
    def set_flag(self, flag_bit: int, value: bool) -> None:
        """Set or clear a specific flag bit."""
        if value:
            self.registers.flags |= (1 << flag_bit)
        else:
            self.registers.flags &= ~(1 << flag_bit)
    
    def get_flag(self, flag_bit: int) -> bool:
        """Get a specific flag bit."""
        return bool(self.registers.flags & (1 << flag_bit))
    
    def snapshot(self) -> Dict[str, Any]:
        """Create processor state snapshot."""
        return {
            'processor_id': self.processor_id,
            'state': self.state.name,
            'registers': self.registers.snapshot(),
            'cycle_count': self.cycle_count,
            'instruction_count': self.instruction_count,
            'current_instruction': str(self.current_instruction) if self.current_instruction else None
        }
    
    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore processor state from snapshot."""
        self.processor_id = snapshot['processor_id']
        self.state = ProcessorState[snapshot['state']]
        self.registers.restore(snapshot['registers'])
        self.cycle_count = snapshot['cycle_count']
        self.instruction_count = snapshot['instruction_count']
        # Note: current_instruction is not restored as it's transient
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            'processor_id': self.processor_id,
            'cycles': self.cycle_count,
            'instructions': self.instruction_count,
            'ipc': self.instruction_count / max(1, self.cycle_count),
            'state': self.state.name
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Processor{self.processor_id}(state={self.state.name}, PC=0x{self.registers.program_counter:x})"


# Common flag bit definitions
class Flags:
    """Common processor flag definitions."""
    ZERO = 0      # Zero flag
    SIGN = 1      # Sign/negative flag  
    CARRY = 2     # Carry flag
    OVERFLOW = 3  # Overflow flag
    PARITY = 4    # Parity flag
    INTERRUPT = 5 # Interrupt enable
    DIRECTION = 6 # Direction flag
    TRAP = 7      # Trap flag