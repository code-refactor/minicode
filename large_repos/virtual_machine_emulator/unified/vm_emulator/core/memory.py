"""Basic memory system for the virtual machine."""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union

from common.core.memory_base import MemoryBase, MemoryAccess as BaseMemoryAccess


class MemoryAccessType(Enum):
    """Types of memory accesses."""
    READ = auto()
    WRITE = auto()
    READ_MODIFY_WRITE = auto()  # For atomic operations like CAS


class MemoryAccess(BaseMemoryAccess):
    """VM-specific memory access extending common memory access."""
    
    def __init__(
        self,
        address: int,
        access_type: MemoryAccessType,
        processor_id: int,
        thread_id: str,
        timestamp: int,
        value: Optional[int] = None,
    ):
        # Map VM access type to common access type
        type_mapping = {
            MemoryAccessType.READ: 'read',
            MemoryAccessType.WRITE: 'write',
            MemoryAccessType.READ_MODIFY_WRITE: 'write'  # Close enough
        }
        common_type = type_mapping.get(access_type, 'read')
        
        super().__init__(
            cycle=timestamp,
            address=address,
            size=4,  # Default word size
            access_type=common_type,
            value=value,
            processor_id=processor_id
        )
        
        # Keep VM-specific attributes for compatibility
        self.access_type = access_type
        self.thread_id = thread_id
        self.timestamp = timestamp
    
    def __str__(self) -> str:
        action = self.access_type.name
        if self.value is not None:
            return f"[{self.timestamp}] P{self.processor_id} T{self.thread_id} {action} addr={self.address} value={self.value}"
        return f"[{self.timestamp}] P{self.processor_id} T{self.thread_id} {action} addr={self.address}"


class MemorySystem(MemoryBase):
    """
    VM-specific memory system extending common memory base.
    
    This is a simple memory model with no caching. More complex models
    implementing cache coherence protocols will extend this.
    """
    
    def __init__(self, size: int = 2**16, **kwargs):
        """
        Initialize the memory system.
        
        Args:
            size: Size of the memory in words (not bytes)
        """
        super().__init__(size * 4, **kwargs)  # Convert words to bytes for base class
        self.size = size  # Keep word-based size for compatibility
        self.memory = [0] * size  # Word-based memory array
        self.vm_access_log: List[MemoryAccess] = []  # VM-specific access log
    
    def read(self, address: int, size: int = 4) -> int:
        """
        Read data from memory (base class interface).
        
        Args:
            address: Byte address to read from
            size: Size in bytes (always 4 for word access)
            
        Returns:
            Value read from memory
        """
        word_address = address // 4
        if not 0 <= word_address < self.size:
            raise IndexError(f"Memory address out of bounds: {address}")
        
        return self.memory[word_address]
    
    def vm_read(
        self, address: int, processor_id: int, thread_id: str, timestamp: int
    ) -> int:
        """
        VM-specific read with thread tracking.
        
        Args:
            address: Memory address to read from (word-based)
            processor_id: ID of the processor performing the read
            thread_id: ID of the thread performing the read
            timestamp: Current global clock value
            
        Returns:
            Value read from memory
        """
        if not 0 <= address < self.size:
            raise IndexError(f"Memory address out of bounds: {address}")
        
        value = self.memory[address]
        
        # Log the VM-specific memory access
        access = MemoryAccess(
            address=address,
            access_type=MemoryAccessType.READ,
            processor_id=processor_id,
            thread_id=thread_id,
            timestamp=timestamp,
        )
        self.vm_access_log.append(access)
        
        # Also log in base class
        self.log_access(BaseMemoryAccess(
            cycle=timestamp,
            address=address * 4,  # Convert to byte address
            size=4,
            access_type='read',
            value=None,
            processor_id=processor_id
        ))
        
        return value
    
    def write(self, address: int, value: int, size: int = 4) -> bool:
        """
        Write data to memory (base class interface).
        
        Args:
            address: Byte address to write to
            value: Value to write
            size: Size in bytes (always 4 for word access)
            
        Returns:
            True on success
        """
        word_address = address // 4
        if not 0 <= word_address < self.size:
            raise IndexError(f"Memory address out of bounds: {address}")
        
        self.memory[word_address] = value & 0xFFFFFFFF  # Ensure 32-bit
        return True
    
    def vm_write(
        self, address: int, value: int, processor_id: int, thread_id: str, timestamp: int
    ) -> None:
        """
        VM-specific write with thread tracking.
        
        Args:
            address: Memory address to write to (word-based)
            value: Value to write
            processor_id: ID of the processor performing the write
            thread_id: ID of the thread performing the write
            timestamp: Current global clock value
        """
        if not 0 <= address < self.size:
            raise IndexError(f"Memory address out of bounds: {address}")
        
        self.memory[address] = value & 0xFFFFFFFF  # Ensure 32-bit
        
        # Log the VM-specific memory access
        access = MemoryAccess(
            address=address,
            access_type=MemoryAccessType.WRITE,
            processor_id=processor_id,
            thread_id=thread_id,
            timestamp=timestamp,
            value=value,
        )
        self.vm_access_log.append(access)
        
        # Also log in base class
        self.log_access(BaseMemoryAccess(
            cycle=timestamp,
            address=address * 4,  # Convert to byte address
            size=4,
            access_type='write',
            value=value,
            processor_id=processor_id
        ))
    
    def compare_and_swap(
        self,
        address: int,
        expected: int,
        new_value: int,
        processor_id: int,
        thread_id: str,
        timestamp: int,
    ) -> bool:
        """
        Atomic compare-and-swap operation.
        
        Args:
            address: Memory address to operate on
            expected: Expected current value
            new_value: New value to set if current matches expected
            processor_id: ID of the processor performing the operation
            thread_id: ID of the thread performing the operation
            timestamp: Current global clock value
            
        Returns:
            True if the swap was performed, False otherwise
        """
        if not 0 <= address < self.size:
            raise IndexError(f"Memory address out of bounds: {address}")
        
        # Perform the CAS operation atomically
        current = self.memory[address]
        success = current == expected
        
        if success:
            self.memory[address] = new_value
        
        # Log the VM-specific memory access
        access = MemoryAccess(
            address=address,
            access_type=MemoryAccessType.READ_MODIFY_WRITE,
            processor_id=processor_id,
            thread_id=thread_id,
            timestamp=timestamp,
            value=new_value if success else None,
        )
        self.vm_access_log.append(access)
        
        # Also log in base class
        self.log_access(BaseMemoryAccess(
            cycle=timestamp,
            address=address * 4,  # Convert to byte address
            size=4,
            access_type='write',
            value=new_value if success else None,
            processor_id=processor_id
        ))
        
        return success
    
    def get_access_history(
        self,
        address: Optional[int] = None,
        processor_id: Optional[int] = None,
        thread_id: Optional[str] = None,
    ) -> List[MemoryAccess]:
        """
        Get a filtered history of memory accesses.
        
        Args:
            address: Filter by memory address
            processor_id: Filter by processor ID
            thread_id: Filter by thread ID
            
        Returns:
            List of memory access logs matching the filters
        """
        result = self.vm_access_log
        
        if address is not None:
            result = [access for access in result if access.address == address]
        
        if processor_id is not None:
            result = [access for access in result if access.processor_id == processor_id]
        
        if thread_id is not None:
            result = [access for access in result if access.thread_id == thread_id]
        
        return result
    
    def clear_logs(self) -> None:
        """Clear all access logs."""
        self.vm_access_log = []
        super().clear_access_log()
    
    def reset(self) -> None:
        """Reset memory to initial state."""
        super().reset()
        self.memory = [0] * self.size
        self.vm_access_log = []
        
    def get_memory_dump(self, start: int = 0, length: Optional[int] = None) -> List[int]:
        """
        Get a dump of memory contents.
        
        Args:
            start: Starting address
            length: Number of words to include, or None for all remaining memory
            
        Returns:
            List of memory values
        """
        if length is None:
            length = self.size - start
            
        end = min(start + length, self.size)
        return self.memory[start:end]