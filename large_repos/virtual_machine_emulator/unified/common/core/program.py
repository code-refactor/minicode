"""Common program representation and loading."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from .instruction import Instruction


@dataclass
class Program:
    """Common program representation."""
    
    instructions: List[Instruction] = field(default_factory=list)
    data: Dict[int, int] = field(default_factory=dict)  # Address -> Value
    symbols: Dict[str, int] = field(default_factory=dict)  # Label -> Address
    entry_point: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_instruction(self, instruction: Instruction) -> None:
        """Add an instruction to the program."""
        self.instructions.append(instruction)
    
    def add_data(self, address: int, value: int) -> None:
        """Add data at a specific address."""
        self.data[address] = value
    
    def add_symbol(self, name: str, address: int) -> None:
        """Add a symbol/label."""
        self.symbols[name] = address
    
    def get_instruction(self, index: int) -> Optional[Instruction]:
        """Get instruction at index."""
        if 0 <= index < len(self.instructions):
            return self.instructions[index]
        return None
    
    def get_instruction_at_address(self, address: int) -> Optional[Instruction]:
        """Get instruction at memory address (assuming 4-byte instructions)."""
        index = address // 4
        return self.get_instruction(index)
    
    def resolve_symbol(self, symbol: str) -> Optional[int]:
        """Resolve a symbol to its address."""
        return self.symbols.get(symbol)
    
    def size(self) -> int:
        """Get program size in instructions."""
        return len(self.instructions)
    
    def memory_size(self) -> int:
        """Get total memory footprint."""
        # Instructions + data
        instruction_size = len(self.instructions) * 4  # 4 bytes per instruction
        data_size = len(self.data) * 4  # 4 bytes per data word
        return instruction_size + data_size
    
    def __str__(self) -> str:
        """String representation of program."""
        lines = [f"Program (entry=0x{self.entry_point:x}, {len(self.instructions)} instructions)"]
        
        # Show first few instructions
        for i, inst in enumerate(self.instructions[:10]):
            lines.append(f"  {i:04d}: {inst}")
        
        if len(self.instructions) > 10:
            lines.append(f"  ... ({len(self.instructions) - 10} more instructions)")
        
        if self.data:
            lines.append(f"Data segment: {len(self.data)} words")
        
        if self.symbols:
            lines.append(f"Symbols: {', '.join(self.symbols.keys())}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert program to dictionary for serialization."""
        return {
            'instructions': [
                {
                    'opcode': inst.opcode,
                    'operands': inst.operands,
                    'type': inst.instruction_type.name,
                    'latency': inst.latency
                }
                for inst in self.instructions
            ],
            'data': self.data,
            'symbols': self.symbols,
            'entry_point': self.entry_point,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Program':
        """Create program from dictionary."""
        from .state import InstructionType
        
        program = cls()
        
        # Load instructions
        for inst_data in data.get('instructions', []):
            inst = Instruction(
                opcode=inst_data['opcode'],
                operands=inst_data.get('operands', []),
                instruction_type=InstructionType[inst_data.get('type', 'NOP')],
                latency=inst_data.get('latency', 1)
            )
            program.add_instruction(inst)
        
        # Load data segment
        program.data = data.get('data', {})
        
        # Load symbols
        program.symbols = data.get('symbols', {})
        
        # Set entry point
        program.entry_point = data.get('entry_point', 0)
        
        # Load metadata
        program.metadata = data.get('metadata', {})
        
        return program


class ProgramBuilder:
    """Helper class for building programs."""
    
    def __init__(self):
        """Initialize program builder."""
        self.program = Program()
        self.current_address = 0
        self.pending_labels: Dict[str, List[int]] = {}  # Label -> instruction indices that reference it
    
    def add_instruction(self, opcode: str, *operands) -> 'ProgramBuilder':
        """Add an instruction."""
        # Convert operands - resolve labels if needed
        resolved_operands = []
        for op in operands:
            if isinstance(op, str) and not op.startswith('R'):
                # Might be a label
                if op in self.program.symbols:
                    resolved_operands.append(self.program.symbols[op])
                else:
                    # Record that this instruction needs label resolution
                    if op not in self.pending_labels:
                        self.pending_labels[op] = []
                    self.pending_labels[op].append(len(self.program.instructions))
                    resolved_operands.append(0)  # Placeholder
            else:
                resolved_operands.append(op)
        
        inst = Instruction(opcode=opcode, operands=resolved_operands)
        self.program.add_instruction(inst)
        self.current_address += 4
        return self
    
    def label(self, name: str) -> 'ProgramBuilder':
        """Add a label at current position."""
        self.program.add_symbol(name, self.current_address)
        
        # Resolve any pending references to this label
        if name in self.pending_labels:
            for inst_idx in self.pending_labels[name]:
                inst = self.program.instructions[inst_idx]
                # Update operands that reference this label
                for i, op in enumerate(inst.operands):
                    if op == 0:  # Our placeholder
                        inst.operands[i] = self.current_address
            del self.pending_labels[name]
        
        return self
    
    def data(self, address: int, value: int) -> 'ProgramBuilder':
        """Add data at address."""
        self.program.add_data(address, value)
        return self
    
    def entry_point(self, address: int) -> 'ProgramBuilder':
        """Set entry point."""
        self.program.entry_point = address
        return self
    
    def build(self) -> Program:
        """Build and return the program."""
        # Check for unresolved labels
        if self.pending_labels:
            unresolved = list(self.pending_labels.keys())
            raise ValueError(f"Unresolved labels: {unresolved}")
        
        return self.program


def parse_assembly(text: str) -> Program:
    """Parse simple assembly text into a program."""
    builder = ProgramBuilder()
    
    for line in text.strip().split('\n'):
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        
        # Handle labels
        if line.endswith(':'):
            builder.label(line[:-1])
            continue
        
        # Parse instruction
        parts = line.replace(',', ' ').split()
        if not parts:
            continue
        
        opcode = parts[0].upper()
        operands = []
        
        for part in parts[1:]:
            # Try to parse as integer
            if part.startswith('0x'):
                operands.append(int(part, 16))
            elif part.isdigit() or (part[0] == '-' and part[1:].isdigit()):
                operands.append(int(part))
            else:
                # Register or label
                operands.append(part)
        
        builder.add_instruction(opcode, *operands)
    
    return builder.build()