"""Common register file implementation for VM processors."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class RegisterFile:
    """Common register file implementation."""
    
    # Standard general-purpose registers
    general_registers: Dict[str, int] = field(default_factory=lambda: {
        f'R{i}': 0 for i in range(16)
    })
    
    # Special registers
    program_counter: int = 0
    stack_pointer: int = 0
    frame_pointer: int = 0
    flags: int = 0
    
    # Additional special registers (can be extended by implementations)
    special_registers: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize register aliases."""
        # Create aliases for common register names
        self.aliases = {
            'PC': 'program_counter',
            'SP': 'stack_pointer',
            'FP': 'frame_pointer',
            'FLAGS': 'flags',
            # R0-R15 are already in general_registers
        }
    
    def get_register(self, name: str) -> int:
        """Get register value by name."""
        # Check if it's an alias
        if name in self.aliases:
            attr_name = self.aliases[name]
            return getattr(self, attr_name)
        
        # Check general registers
        if name in self.general_registers:
            return self.general_registers[name]
        
        # Check special registers
        if name in self.special_registers:
            return self.special_registers[name]
        
        # Check direct attributes
        if hasattr(self, name.lower()):
            return getattr(self, name.lower())
        
        raise ValueError(f"Unknown register: {name}")
    
    def set_register(self, name: str, value: int) -> None:
        """Set register value by name."""
        # Ensure value is within valid range (32-bit for compatibility)
        value = value & 0xFFFFFFFF
        
        # Check if it's an alias
        if name in self.aliases:
            attr_name = self.aliases[name]
            setattr(self, attr_name, value)
            return
        
        # Check general registers
        if name in self.general_registers:
            self.general_registers[name] = value
            return
        
        # Check special registers
        if name in self.special_registers:
            self.special_registers[name] = value
            return
        
        # Check direct attributes
        if hasattr(self, name.lower()):
            setattr(self, name.lower(), value)
            return
        
        raise ValueError(f"Unknown register: {name}")
    
    def reset(self) -> None:
        """Reset all registers to zero."""
        for reg in self.general_registers:
            self.general_registers[reg] = 0
        
        self.program_counter = 0
        self.stack_pointer = 0
        self.frame_pointer = 0
        self.flags = 0
        
        for reg in self.special_registers:
            self.special_registers[reg] = 0
    
    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of current register state."""
        return {
            'general': dict(self.general_registers),
            'pc': self.program_counter,
            'sp': self.stack_pointer,
            'fp': self.frame_pointer,
            'flags': self.flags,
            'special': dict(self.special_registers)
        }
    
    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore register state from snapshot."""
        self.general_registers = dict(snapshot['general'])
        self.program_counter = snapshot['pc']
        self.stack_pointer = snapshot['sp']
        self.frame_pointer = snapshot['fp']
        self.flags = snapshot['flags']
        self.special_registers = dict(snapshot.get('special', {}))
    
    def get_all_registers(self) -> Dict[str, int]:
        """Get all register values as a dictionary."""
        result = dict(self.general_registers)
        result['PC'] = self.program_counter
        result['SP'] = self.stack_pointer
        result['FP'] = self.frame_pointer
        result['FLAGS'] = self.flags
        result.update(self.special_registers)
        return result
    
    def __repr__(self) -> str:
        """String representation of register file."""
        lines = ["RegisterFile:"]
        
        # General registers in rows
        for i in range(0, 16, 4):
            regs = [f"R{j}={self.general_registers[f'R{j}']:08x}" for j in range(i, min(i+4, 16))]
            lines.append("  " + " ".join(regs))
        
        # Special registers
        lines.append(f"  PC={self.program_counter:08x} SP={self.stack_pointer:08x}")
        lines.append(f"  FP={self.frame_pointer:08x} FLAGS={self.flags:08x}")
        
        if self.special_registers:
            for name, value in self.special_registers.items():
                lines.append(f"  {name}={value:08x}")
        
        return "\n".join(lines)