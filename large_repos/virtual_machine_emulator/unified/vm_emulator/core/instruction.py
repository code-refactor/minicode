"""Instruction set for the virtual machine."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# Import common instruction classes
from common.core.instruction import Instruction as BaseInstruction, InstructionSet as BaseInstructionSet
from common.core.state import InstructionType


# Map vm_emulator specific types to common types
class VMInstructionType(Enum):
    """VM-specific instruction type mappings."""
    COMPUTE = InstructionType.ARITHMETIC  # Arithmetic/logic operations
    MEMORY = InstructionType.MEMORY   # Memory read/write operations
    BRANCH = InstructionType.BRANCH   # Conditional and unconditional jumps
    SYNC = InstructionType.SYNC       # Synchronization operations
    SYSTEM = InstructionType.SYSTEM   # System calls and VM control


# Extend the common instruction class for VM-specific functionality
class Instruction(BaseInstruction):
    """VM-specific instruction extending common instruction."""
    
    def __init__(self, opcode: str, type: Union[InstructionType, VMInstructionType], operands: List[Any], latency: int):
        # Convert VM-specific type to common type if needed
        if isinstance(type, VMInstructionType):
            instruction_type = type.value
        else:
            instruction_type = type
        
        super().__init__(
            opcode=opcode,
            operands=operands,
            instruction_type=instruction_type,
            latency=latency
        )
        self.type = instruction_type  # Keep for backward compatibility
    
    def __str__(self) -> str:
        operand_str = ", ".join(str(op) for op in self.operands)
        return f"{self.opcode} {operand_str}"


class InstructionSet(BaseInstructionSet):
    """VM-specific instruction set extending common instruction set."""
    
    # Compute operations
    ADD = "ADD"       # Add
    SUB = "SUB"       # Subtract
    MUL = "MUL"       # Multiply
    DIV = "DIV"       # Divide
    MOD = "MOD"       # Modulo
    AND = "AND"       # Logical AND
    OR = "OR"         # Logical OR
    XOR = "XOR"       # Logical XOR
    NOT = "NOT"       # Logical NOT
    SHL = "SHL"       # Shift left
    SHR = "SHR"       # Shift right
    
    # Memory operations
    LOAD = "LOAD"     # Load from memory
    STORE = "STORE"   # Store to memory
    
    # Branch operations
    JMP = "JMP"       # Unconditional jump
    JZ = "JZ"         # Jump if zero
    JNZ = "JNZ"       # Jump if not zero
    JGT = "JGT"       # Jump if greater than
    JLT = "JLT"       # Jump if less than
    
    # Synchronization operations
    LOCK = "LOCK"     # Acquire lock
    UNLOCK = "UNLOCK" # Release lock
    FENCE = "FENCE"   # Memory fence
    CAS = "CAS"       # Compare and swap
    
    # System operations
    HALT = "HALT"     # Stop execution
    YIELD = "YIELD"   # Yield to scheduler
    SPAWN = "SPAWN"   # Create new thread
    JOIN = "JOIN"     # Wait for thread completion
    
    def __init__(self):
        super().__init__()
        self._define_vm_instructions()
    
    def _define_vm_instructions(self):
        """Define VM-specific instructions."""
        # Compute operations
        compute_ops = [
            ('ADD', 1), ('SUB', 1), ('MUL', 3), ('DIV', 5), ('MOD', 5),
            ('AND', 1), ('OR', 1), ('XOR', 1), ('NOT', 1), ('SHL', 1), ('SHR', 1)
        ]
        for op, latency in compute_ops:
            self.define_instruction(op, InstructionType.ARITHMETIC, latency, 2)
        
        # Memory operations
        for op, latency in [('LOAD', 2), ('STORE', 2)]:
            self.define_instruction(op, InstructionType.MEMORY, latency, 2)
        
        # Branch operations
        branch_ops = ['JMP', 'JZ', 'JNZ', 'JGT', 'JLT']
        for op in branch_ops:
            self.define_instruction(op, InstructionType.BRANCH, 1, 1)
        
        # Synchronization operations
        sync_ops = [('LOCK', 10), ('UNLOCK', 5), ('FENCE', 10), ('CAS', 8)]
        for op, latency in sync_ops:
            self.define_instruction(op, InstructionType.SYNC, latency, 1)
        
        # System operations
        system_ops = [('HALT', 1), ('YIELD', 5), ('SPAWN', 50), ('JOIN', 5)]
        for op, latency in system_ops:
            self.define_instruction(op, InstructionType.SYSTEM, latency, 0)
    
    # Mapping of instruction opcodes to their types and latencies (for backward compatibility)
    @property
    def INSTRUCTION_SPECS(self) -> Dict[str, Tuple[InstructionType, int]]:
        """Get instruction specifications for backward compatibility."""
        specs = {}
        for opcode, info in self.instructions.items():
            # Map back to VMInstructionType for compatibility
            vm_type = None
            if info['type'] == InstructionType.ARITHMETIC:
                vm_type = VMInstructionType.COMPUTE.value
            elif info['type'] == InstructionType.MEMORY:
                vm_type = VMInstructionType.MEMORY.value
            elif info['type'] == InstructionType.BRANCH:
                vm_type = VMInstructionType.BRANCH.value
            elif info['type'] == InstructionType.SYNC:
                vm_type = VMInstructionType.SYNC.value
            elif info['type'] == InstructionType.SYSTEM:
                vm_type = VMInstructionType.SYSTEM.value
            else:
                vm_type = info['type']
            
            specs[opcode] = (vm_type, info['latency'])
        return specs
    
    def create_instruction_instance(self, opcode: str, operands: List[Any]) -> Instruction:
        """Create an instruction with the given opcode and operands."""
        if not self.is_valid_opcode(opcode):
            raise ValueError(f"Unknown opcode: {opcode}")
        
        info = self.get_instruction_info(opcode)
        return Instruction(
            opcode=opcode,
            type=info['type'],
            operands=operands,
            latency=info['latency']
        )
    
    @classmethod
    def create_instruction(cls, opcode: str, operands: List[Any]) -> Instruction:
        """Create an instruction with the given opcode and operands (backward compatibility)."""
        # For backward compatibility, create a default instance and use it
        instance = cls()
        return instance.create_instruction_instance(opcode, operands)