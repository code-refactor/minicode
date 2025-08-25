"""Core components of the common VM library."""

from .state import (
    VMState,
    ProcessorState,
    ThreadState,
    MemoryPermission,
    InstructionType,
    ExecutionStats
)

from .registers import RegisterFile

from .instruction import (
    Instruction,
    InstructionSet,
    create_common_instruction_set
)

from .program import (
    Program,
    ProgramBuilder,
    parse_assembly
)

from .vm_base import VMBase

from .processor_base import ProcessorBase, Flags

from .memory_base import (
    MemoryBase,
    MemorySegment,
    MemoryAccess,
    SimpleMemory
)

__all__ = [
    # State enums and classes
    'VMState',
    'ProcessorState', 
    'ThreadState',
    'MemoryPermission',
    'InstructionType',
    'ExecutionStats',
    
    # Core components
    'RegisterFile',
    'Instruction',
    'InstructionSet',
    'create_common_instruction_set',
    'Program',
    'ProgramBuilder',
    'parse_assembly',
    
    # Base classes
    'VMBase',
    'ProcessorBase',
    'Flags',
    'MemoryBase',
    'MemorySegment',
    'MemoryAccess',
    'SimpleMemory'
]