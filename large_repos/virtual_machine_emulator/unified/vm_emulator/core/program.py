"""Program representation for the virtual machine."""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

from common.core.program import Program as BaseProgram
from vm_emulator.core.instruction import Instruction, InstructionSet


class Program(BaseProgram):
    """
    VM-specific program extending common program.
    A program contains a list of instructions and metadata.
    """
    
    def __init__(self, name: str = "", instructions: List[Instruction] = None, 
                 entry_point: int = 0, data_segment: Dict[int, int] = None, 
                 symbols: Dict[str, int] = None):
        # Initialize base program
        super().__init__(
            instructions=instructions or [],
            data=data_segment or {},
            symbols=symbols or {},
            entry_point=entry_point,
            metadata={"name": name}
        )
        self.name = name
        self.data_segment = self.data  # Alias for backward compatibility
    
    def get_instruction(self, pc: int) -> Optional[Instruction]:
        """Get the instruction at the given program counter."""
        if 0 <= pc < len(self.instructions):
            return self.instructions[pc]
        return None
    
    def get_instruction_count(self) -> int:
        """Get the total number of instructions in the program."""
        return len(self.instructions)
    
    def add_instruction(self, instruction: Instruction) -> int:
        """
        Add an instruction to the program and return its position.
        
        Args:
            instruction: The instruction to add
            
        Returns:
            The position (PC) of the added instruction
        """
        pos = len(self.instructions)
        self.instructions.append(instruction)
        return pos
    
    def add_data(self, address: int, value: int) -> None:
        """
        Add a value to the data segment.
        
        Args:
            address: The memory address
            value: The value to store
        """
        super().add_data(address, value)
        self.data_segment[address] = value  # Keep alias updated
    
    def add_symbol(self, name: str, address: int) -> None:
        """
        Add a symbol (label) to the program.
        
        Args:
            name: The symbol name
            address: The corresponding address (usually a PC value)
        """
        super().add_symbol(name, address)
    
    def get_symbol_address(self, name: str) -> Optional[int]:
        """
        Get the address for a symbol.
        
        Args:
            name: The symbol name
            
        Returns:
            The address or None if the symbol doesn't exist
        """
        return self.resolve_symbol(name)
    
    def to_dict(self) -> Dict:
        """
        Convert the program to a dictionary representation.
        
        Returns:
            A dictionary representing the program
        """
        # Use base class to_dict and add VM-specific fields
        result = super().to_dict()
        result["name"] = self.name
        result["data_segment"] = self.data_segment  # For backward compatibility
        return result
    
    def to_json(self) -> str:
        """
        Convert the program to a JSON string.
        
        Returns:
            A JSON string representing the program
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Program":
        """
        Create a program from a dictionary representation.
        
        Args:
            data: A dictionary representing the program
            
        Returns:
            A new Program instance
        """
        from common.core.state import InstructionType
        
        # Convert instruction data to Instruction objects
        instructions = []
        for instr_data in data["instructions"]:
            # Handle both old and new instruction type formats
            if "type" in instr_data:
                try:
                    instr_type = getattr(InstructionType, instr_data["type"])
                except AttributeError:
                    # Try to map from old format
                    type_mapping = {
                        "COMPUTE": InstructionType.ARITHMETIC,
                        "MEMORY": InstructionType.MEMORY,
                        "BRANCH": InstructionType.BRANCH,
                        "SYNC": InstructionType.SYNC,
                        "SYSTEM": InstructionType.SYSTEM,
                    }
                    instr_type = type_mapping.get(instr_data["type"], InstructionType.NOP)
            else:
                instr_type = InstructionType.NOP
            
            instr = Instruction(
                opcode=instr_data["opcode"],
                type=instr_type,
                operands=instr_data.get("operands", []),
                latency=instr_data.get("latency", 1),
            )
            instructions.append(instr)
        
        return cls(
            name=data.get("name", ""),
            entry_point=data.get("entry_point", 0),
            instructions=instructions,
            data_segment=data.get("data_segment", data.get("data", {})),
            symbols=data.get("symbols", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Program":
        """
        Create a program from a JSON string.
        
        Args:
            json_str: A JSON string representing the program
            
        Returns:
            A new Program instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def create_simple_program(cls, name: str, instructions_data: List[Tuple[str, List[Union[str, int]]]]) -> "Program":
        """
        Create a program from a simple format of opcode and operands.
        
        Args:
            name: The program name
            instructions_data: List of tuples with (opcode, operands)
            
        Returns:
            A new Program instance
        """
        instructions = []
        for opcode, operands in instructions_data:
            instr = InstructionSet.create_instruction(opcode, operands)
            instructions.append(instr)
        
        return cls(name=name, instructions=instructions)