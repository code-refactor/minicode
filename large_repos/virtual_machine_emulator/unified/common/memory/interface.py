"""Memory access interfaces and abstractions."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..core.memory_base import MemoryAccess


class MemoryInterface(ABC):
    """Standard interface for memory access."""
    
    @abstractmethod
    def read(self, address: int, size: int = 4) -> int:
        """Read data from memory."""
        pass
    
    @abstractmethod
    def write(self, address: int, value: int, size: int = 4) -> bool:
        """Write data to memory."""
        pass
    
    @abstractmethod
    def execute(self, address: int) -> Optional[int]:
        """Fetch instruction from memory for execution."""
        pass
    
    @abstractmethod
    def allocate(self, size: int) -> Optional[int]:
        """Allocate memory and return base address."""
        pass
    
    @abstractmethod
    def free(self, address: int) -> bool:
        """Free previously allocated memory."""
        pass


class ProtectedMemoryInterface(MemoryInterface):
    """Interface for memory with protection mechanisms."""
    
    @abstractmethod
    def check_permission(self, address: int, permission: str) -> bool:
        """Check if address has specified permission."""
        pass
    
    @abstractmethod
    def set_permission(self, address: int, size: int, permission: int) -> bool:
        """Set permissions for memory range."""
        pass
    
    @abstractmethod
    def get_protection_level(self) -> int:
        """Get current protection level."""
        pass
    
    @abstractmethod
    def set_protection_level(self, level: int) -> None:
        """Set protection level."""
        pass


class CachedMemoryInterface(MemoryInterface):
    """Interface for memory with caching."""
    
    @abstractmethod
    def cache_read(self, address: int, cache_id: int) -> Optional[int]:
        """Read through cache."""
        pass
    
    @abstractmethod  
    def cache_write(self, address: int, value: int, cache_id: int) -> bool:
        """Write through cache."""
        pass
    
    @abstractmethod
    def flush_cache(self, cache_id: Optional[int] = None) -> None:
        """Flush cache(s)."""
        pass
    
    @abstractmethod
    def invalidate_cache_line(self, address: int, cache_id: Optional[int] = None) -> None:
        """Invalidate cache line."""
        pass


class AtomicMemoryInterface(MemoryInterface):
    """Interface for memory supporting atomic operations."""
    
    @abstractmethod
    def compare_and_swap(self, address: int, expected: int, new_value: int) -> bool:
        """Atomic compare and swap."""
        pass
    
    @abstractmethod
    def fetch_and_add(self, address: int, value: int) -> int:
        """Atomic fetch and add."""
        pass
    
    @abstractmethod
    def fetch_and_or(self, address: int, value: int) -> int:
        """Atomic fetch and OR."""
        pass
    
    @abstractmethod
    def fetch_and_and(self, address: int, value: int) -> int:
        """Atomic fetch and AND."""
        pass
    
    @abstractmethod
    def atomic_exchange(self, address: int, value: int) -> int:
        """Atomic exchange."""
        pass