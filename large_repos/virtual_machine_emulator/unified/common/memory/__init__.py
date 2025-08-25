"""Memory management components."""

from .interface import (
    MemoryInterface,
    ProtectedMemoryInterface,
    CachedMemoryInterface,
    AtomicMemoryInterface
)

from .tracking import (
    AccessPattern,
    MemoryAccessTracker
)

__all__ = [
    'MemoryInterface',
    'ProtectedMemoryInterface',
    'CachedMemoryInterface',
    'AtomicMemoryInterface',
    'AccessPattern',
    'MemoryAccessTracker'
]