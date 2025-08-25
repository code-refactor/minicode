"""Utility components."""

from .exceptions import (
    VMException,
    ExecutionException,
    MemoryException,
    MemoryAccessViolation,
    SegmentationFault,
    PermissionDenied,
    InvalidInstruction,
    PrivilegeViolation,
    StackOverflow,
    DivisionByZero,
    Breakpoint,
    HaltException,
    ThreadException,
    DeadlockDetected,
    SynchronizationException,
    TimeoutException
)

from .config import (
    VMConfig,
    ParallelVMConfig,
    SecureVMConfig,
    ConfigManager
)

__all__ = [
    # Exceptions
    'VMException',
    'ExecutionException',
    'MemoryException',
    'MemoryAccessViolation',
    'SegmentationFault',
    'PermissionDenied',
    'InvalidInstruction',
    'PrivilegeViolation',
    'StackOverflow',
    'DivisionByZero',
    'Breakpoint',
    'HaltException',
    'ThreadException',
    'DeadlockDetected',
    'SynchronizationException',
    'TimeoutException',
    
    # Configuration
    'VMConfig',
    'ParallelVMConfig',
    'SecureVMConfig',
    'ConfigManager'
]