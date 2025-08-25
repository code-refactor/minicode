"""Abstract base classes for memory system implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from .state import MemoryPermission


@dataclass
class MemorySegment:
    """Common memory segment representation."""
    
    name: str
    start: int
    size: int
    permissions: MemoryPermission = MemoryPermission.READ_WRITE
    data: bytearray = field(default_factory=bytearray)
    
    def __post_init__(self):
        """Initialize data array if not provided."""
        if not self.data:
            self.data = bytearray(self.size)
    
    def contains(self, address: int) -> bool:
        """Check if address is within this segment."""
        return self.start <= address < self.start + self.size
    
    def get_offset(self, address: int) -> int:
        """Get offset within segment for address."""
        return address - self.start
    
    def can_read(self) -> bool:
        """Check if segment is readable."""
        return self.permissions.value & MemoryPermission.READ.value != 0
    
    def can_write(self) -> bool:
        """Check if segment is writable."""
        return self.permissions.value & MemoryPermission.WRITE.value != 0
    
    def can_execute(self) -> bool:
        """Check if segment is executable."""
        return self.permissions.value & MemoryPermission.EXECUTE.value != 0
    
    def __repr__(self) -> str:
        """String representation."""
        perms = []
        if self.can_read(): perms.append('R')
        if self.can_write(): perms.append('W')
        if self.can_execute(): perms.append('X')
        perm_str = ''.join(perms) if perms else '-'
        
        return f"MemorySegment({self.name}, 0x{self.start:x}-0x{self.start+self.size:x}, {perm_str})"


@dataclass
class MemoryAccess:
    """Record of a memory access."""
    
    cycle: int
    address: int
    size: int
    access_type: str  # 'read', 'write', 'execute'
    value: Optional[int] = None
    processor_id: Optional[int] = None
    instruction: Optional[str] = None
    success: bool = True
    
    def __repr__(self) -> str:
        """String representation."""
        val_str = f"={self.value:x}" if self.value is not None else ""
        return f"MemoryAccess(@{self.cycle}, {self.access_type} 0x{self.address:x}{val_str})"


class MemoryBase(ABC):
    """Abstract base class for memory system implementations."""
    
    def __init__(self, size: int = 65536, **kwargs):
        """Initialize base memory system."""
        self.size = size
        self.segments: List[MemorySegment] = []
        self.access_log: List[MemoryAccess] = []
        self.enable_logging = kwargs.get('enable_logging', True)
        self.debug = kwargs.get('debug', False)
        
    @abstractmethod
    def read(self, address: int, size: int = 4) -> int:
        """Read data from memory."""
        pass
    
    @abstractmethod
    def write(self, address: int, value: int, size: int = 4) -> bool:
        """Write data to memory. Returns True on success."""
        pass
    
    def read_byte(self, address: int) -> int:
        """Read a single byte."""
        return self.read(address, 1)
    
    def write_byte(self, address: int, value: int) -> bool:
        """Write a single byte."""
        return self.write(address, value & 0xFF, 1)
    
    def read_word(self, address: int) -> int:
        """Read a 32-bit word."""
        return self.read(address, 4)
    
    def write_word(self, address: int, value: int) -> bool:
        """Write a 32-bit word."""
        return self.write(address, value & 0xFFFFFFFF, 4)
    
    def add_segment(self, segment: MemorySegment) -> None:
        """Add a memory segment."""
        # Check for overlaps
        for existing in self.segments:
            if (segment.start < existing.start + existing.size and
                segment.start + segment.size > existing.start):
                raise ValueError(f"Segment {segment.name} overlaps with {existing.name}")
        
        self.segments.append(segment)
        self.segments.sort(key=lambda s: s.start)
    
    def find_segment(self, address: int) -> Optional[MemorySegment]:
        """Find segment containing address."""
        for segment in self.segments:
            if segment.contains(address):
                return segment
        return None
    
    def log_access(self, access: MemoryAccess) -> None:
        """Log a memory access."""
        if self.enable_logging:
            self.access_log.append(access)
            
            if self.debug:
                print(f"Memory: {access}")
    
    def get_access_log(self) -> List[MemoryAccess]:
        """Get memory access log."""
        return self.access_log
    
    def clear_access_log(self) -> None:
        """Clear memory access log."""
        self.access_log.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {
            'size': self.size,
            'segments': len(self.segments),
            'accesses': len(self.access_log)
        }
        
        # Count access types
        reads = sum(1 for a in self.access_log if a.access_type == 'read')
        writes = sum(1 for a in self.access_log if a.access_type == 'write')
        execs = sum(1 for a in self.access_log if a.access_type == 'execute')
        
        stats['reads'] = reads
        stats['writes'] = writes
        stats['executes'] = execs
        
        return stats
    
    @abstractmethod
    def reset(self) -> None:
        """Reset memory to initial state."""
        self.access_log.clear()
    
    def dump(self, start: int, size: int) -> bytes:
        """Dump memory contents."""
        result = bytearray()
        for i in range(size):
            try:
                result.append(self.read_byte(start + i))
            except:
                result.append(0)
        return bytes(result)
    
    def load_data(self, address: int, data: bytes) -> None:
        """Load data into memory."""
        for i, byte in enumerate(data):
            self.write_byte(address + i, byte)
    
    def __repr__(self) -> str:
        """String representation."""
        seg_info = f"{len(self.segments)} segments" if self.segments else "no segments"
        return f"{self.__class__.__name__}(size=0x{self.size:x}, {seg_info})"


class SimpleMemory(MemoryBase):
    """Simple memory implementation without protection."""
    
    def __init__(self, size: int = 65536, **kwargs):
        """Initialize simple memory."""
        super().__init__(size, **kwargs)
        self.data = bytearray(size)
        
    def read(self, address: int, size: int = 4) -> int:
        """Read from memory."""
        if address < 0 or address + size > self.size:
            raise ValueError(f"Memory access out of bounds: 0x{address:x}")
        
        value = 0
        for i in range(size):
            value |= self.data[address + i] << (i * 8)
        
        if self.enable_logging:
            self.log_access(MemoryAccess(
                cycle=0,  # Will be set by VM
                address=address,
                size=size,
                access_type='read',
                value=value
            ))
        
        return value
    
    def write(self, address: int, value: int, size: int = 4) -> bool:
        """Write to memory."""
        if address < 0 or address + size > self.size:
            raise ValueError(f"Memory access out of bounds: 0x{address:x}")
        
        for i in range(size):
            self.data[address + i] = (value >> (i * 8)) & 0xFF
        
        if self.enable_logging:
            self.log_access(MemoryAccess(
                cycle=0,  # Will be set by VM
                address=address,
                size=size,
                access_type='write',
                value=value
            ))
        
        return True
    
    def reset(self) -> None:
        """Reset memory."""
        super().reset()
        self.data = bytearray(self.size)