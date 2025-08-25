"""Common instruction representation and framework."""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Callable
from enum import Enum
from .state import InstructionType


@dataclass
class Instruction:
    """Common instruction representation."""
    
    opcode: str
    operands: List[Any] = field(default_factory=list)
    instruction_type: InstructionType = InstructionType.NOP
    latency: int = 1
    size: int = 4  # Default instruction size in bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of instruction."""
        if not self.operands:
            return self.opcode
        
        # Format operands
        formatted_operands = []
        for op in self.operands:
            if isinstance(op, int):
                # Format as hex if large, decimal otherwise
                if abs(op) > 9:
                    formatted_operands.append(f"0x{op:x}" if op >= 0 else f"-0x{-op:x}")
                else:
                    formatted_operands.append(str(op))
            else:
                formatted_operands.append(str(op))
        
        return f"{self.opcode} {', '.join(formatted_operands)}"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Instruction(opcode='{self.opcode}', operands={self.operands}, type={self.instruction_type.name})"
    
    def encode(self) -> int:
        """Encode instruction to binary format (can be overridden)."""
        # Simple encoding scheme for common use
        # This can be overridden by specific implementations
        encoded = hash(self.opcode) & 0xFF  # 8-bit opcode
        
        # Encode operands (simplified)
        for i, op in enumerate(self.operands[:3]):  # Max 3 operands
            if isinstance(op, str):
                # Register reference
                if op.startswith('R'):
                    reg_num = int(op[1:]) if len(op) > 1 and op[1:].isdigit() else 0
                    encoded |= (reg_num & 0xFF) << (8 * (i + 1))
            elif isinstance(op, int):
                # Immediate value (truncated to 8 bits per operand)
                encoded |= (op & 0xFF) << (8 * (i + 1))
        
        return encoded & 0xFFFFFFFF
    
    @classmethod
    def decode(cls, encoded: int) -> 'Instruction':
        """Decode instruction from binary format (can be overridden)."""
        # This is a placeholder - implementations should override
        opcode_num = encoded & 0xFF
        return cls(opcode=f"OP_{opcode_num:02x}", operands=[])
    
    def is_branch(self) -> bool:
        """Check if instruction is a branch."""
        return self.instruction_type == InstructionType.BRANCH
    
    def is_memory_access(self) -> bool:
        """Check if instruction accesses memory."""
        return self.instruction_type == InstructionType.MEMORY
    
    def is_privileged(self) -> bool:
        """Check if instruction requires privileges."""
        return self.instruction_type == InstructionType.PRIVILEGED


@dataclass
class InstructionSet:
    """Collection of instruction definitions."""
    
    instructions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def define_instruction(
        self,
        opcode: str,
        instruction_type: InstructionType,
        latency: int = 1,
        operand_count: int = 0,
        privileged: bool = False,
        description: str = ""
    ) -> None:
        """Define a new instruction."""
        self.instructions[opcode] = {
            'type': instruction_type,
            'latency': latency,
            'operand_count': operand_count,
            'privileged': privileged,
            'description': description
        }
    
    def get_instruction_info(self, opcode: str) -> Optional[Dict[str, Any]]:
        """Get information about an instruction."""
        return self.instructions.get(opcode)
    
    def create_instruction(self, opcode: str, operands: List[Any]) -> Instruction:
        """Create an instruction instance."""
        info = self.instructions.get(opcode, {})
        
        # Determine instruction type
        inst_type = info.get('type', InstructionType.NOP)
        if info.get('privileged'):
            inst_type = InstructionType.PRIVILEGED
        
        return Instruction(
            opcode=opcode,
            operands=operands,
            instruction_type=inst_type,
            latency=info.get('latency', 1),
            metadata={'privileged': info.get('privileged', False)}
        )
    
    def is_valid_opcode(self, opcode: str) -> bool:
        """Check if opcode is valid."""
        return opcode in self.instructions
    
    def get_all_opcodes(self) -> List[str]:
        """Get list of all defined opcodes."""
        return list(self.instructions.keys())


def create_common_instruction_set() -> InstructionSet:
    """Create a basic instruction set common to most VMs."""
    iset = InstructionSet()
    
    # Arithmetic instructions
    for op in ['ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'INC', 'DEC', 'NEG']:
        iset.define_instruction(op, InstructionType.ARITHMETIC, latency=1, operand_count=2)
    
    # Logic instructions  
    for op in ['AND', 'OR', 'XOR', 'NOT', 'SHL', 'SHR', 'ROL', 'ROR']:
        iset.define_instruction(op, InstructionType.LOGIC, latency=1, operand_count=2)
    
    # Memory instructions
    for op in ['LOAD', 'STORE', 'PUSH', 'POP']:
        iset.define_instruction(op, InstructionType.MEMORY, latency=2, operand_count=2)
    
    # Branch instructions
    for op in ['JMP', 'JZ', 'JNZ', 'JE', 'JNE', 'JL', 'JG', 'JLE', 'JGE', 'CALL', 'RET']:
        iset.define_instruction(op, InstructionType.BRANCH, latency=1, operand_count=1)
    
    # System instructions
    for op in ['NOP', 'HALT', 'INT', 'IRET']:
        iset.define_instruction(op, InstructionType.SYSTEM, latency=1, operand_count=0)
    
    # Comparison
    iset.define_instruction('CMP', InstructionType.ARITHMETIC, latency=1, operand_count=2)
    iset.define_instruction('TEST', InstructionType.LOGIC, latency=1, operand_count=2)
    
    # Move instruction
    iset.define_instruction('MOV', InstructionType.ARITHMETIC, latency=1, operand_count=2)
    
    return iset