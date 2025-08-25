"""Common VM library for unified virtual machine implementations."""

# Core components
from .core import (
    VMState,
    ProcessorState,
    ThreadState,
    MemoryPermission,
    InstructionType,
    ExecutionStats,
    RegisterFile,
    Instruction,
    InstructionSet,
    create_common_instruction_set,
    Program,
    ProgramBuilder,
    parse_assembly,
    VMBase,
    ProcessorBase,
    Flags,
    MemoryBase,
    MemorySegment,
    MemoryAccess,
    SimpleMemory
)

# Execution components
from .execution import (
    ExecutionContext,
    ExecutionResult,
    ThreadContext,
    SecurityContext,
    GlobalClock,
    CycleTimer,
    TraceEventType,
    TraceEvent,
    ExecutionTrace
)

# Memory components
from .memory import (
    MemoryInterface,
    ProtectedMemoryInterface,
    CachedMemoryInterface,
    AtomicMemoryInterface,
    AccessPattern,
    MemoryAccessTracker
)

# Analysis components
from .analysis import (
    EventType,
    Event,
    EventLogger,
    Metric,
    StatisticsCollector,
    PerformanceMonitor
)

# Utility components
from .utils import (
    VMException,
    ExecutionException,
    MemoryException,
    VMConfig,
    ParallelVMConfig,
    SecureVMConfig,
    ConfigManager
)

__version__ = "1.0.0"

__all__ = [
    # Core
    'VMState', 'ProcessorState', 'ThreadState', 'MemoryPermission',
    'InstructionType', 'ExecutionStats', 'RegisterFile', 'Instruction',
    'InstructionSet', 'create_common_instruction_set', 'Program',
    'ProgramBuilder', 'parse_assembly', 'VMBase', 'ProcessorBase',
    'Flags', 'MemoryBase', 'MemorySegment', 'MemoryAccess', 'SimpleMemory',
    
    # Execution
    'ExecutionContext', 'ExecutionResult', 'ThreadContext', 'SecurityContext',
    'GlobalClock', 'CycleTimer', 'TraceEventType', 'TraceEvent', 'ExecutionTrace',
    
    # Memory
    'MemoryInterface', 'ProtectedMemoryInterface', 'CachedMemoryInterface',
    'AtomicMemoryInterface', 'AccessPattern', 'MemoryAccessTracker',
    
    # Analysis
    'EventType', 'Event', 'EventLogger', 'Metric', 'StatisticsCollector',
    'PerformanceMonitor',
    
    # Utils
    'VMException', 'ExecutionException', 'MemoryException', 'VMConfig',
    'ParallelVMConfig', 'SecureVMConfig', 'ConfigManager'
]
