"""
Memory management and protection mechanisms for the secure VM.

This module implements a detailed memory model with various protection mechanisms
including memory permissions, boundary checking, and protection levels.
"""

from __future__ import annotations
import random
import struct
from enum import Enum, Flag, auto
from typing import Dict, List, Optional, Set, Tuple, Union, Any

# Import common library components
from common.core.memory_base import MemoryBase, MemorySegment as CommonMemorySegment, MemoryAccess
from common.core.state import MemoryPermission as CommonMemoryPermission
from common.utils.exceptions import MemoryException, MemoryAccessViolation


# Use common MemoryPermission but provide aliases for compatibility
class MemoryPermission(Flag):
    """Memory access permissions flags (extended from common)."""
    NONE = 0
    READ = 1  # Match CommonMemoryPermission.READ.value
    WRITE = 2  # Match CommonMemoryPermission.WRITE.value 
    EXECUTE = 4  # Match CommonMemoryPermission.EXECUTE.value
    READ_WRITE = READ | WRITE
    READ_EXECUTE = READ | EXECUTE
    WRITE_EXECUTE = WRITE | EXECUTE
    READ_WRITE_EXECUTE = READ | WRITE | EXECUTE
    FULL = READ | WRITE | EXECUTE
    


class MemoryProtectionLevel(Enum):
    """Protection enforcement levels for memory operations."""
    NONE = 0  # No protection, all operations permitted
    MINIMAL = 1  # Basic boundary checking
    STANDARD = 2  # Permission enforcement without additional protections
    ENHANCED = 3  # Permission checks plus basic integrity protections
    MAXIMUM = 4  # All protections enabled with strict enforcement

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        return NotImplemented


class ProtectionBypassAttempt:
    """Records an attempt to bypass memory protection mechanisms."""
    
    def __init__(
        self,
        address: int,
        access_type: str,
        current_permission: MemoryPermission,
        required_permission: MemoryPermission,
        instruction_pointer: int,
        context: Dict[str, Any],
    ):
        self.address = address
        self.access_type = access_type
        self.current_permission = current_permission
        self.required_permission = required_permission
        self.instruction_pointer = instruction_pointer
        self.context = context
        self.timestamp = 0  # Will be set by the forensic logger
    
    def __str__(self) -> str:
        return (
            f"Protection bypass attempt at 0x{self.address:08x} "
            f"(IP: 0x{self.instruction_pointer:08x}): "
            f"{self.access_type} operation, "
            f"required {self.required_permission.name}, "
            f"had {self.current_permission.name}"
        )


class MemorySegment(CommonMemorySegment):
    """Security-enhanced memory segment with protection attributes."""
    
    def __init__(
        self,
        base_address: int,
        size: int,
        permission: MemoryPermission = MemoryPermission.READ_WRITE,
        name: str = "unnamed",
    ):
        # Convert to common permission format
        if isinstance(permission, MemoryPermission):
            common_perm = CommonMemoryPermission(permission.value)
        else:
            common_perm = permission
            
        super().__init__(
            name=name,
            start=base_address,
            size=size,
            permissions=common_perm
        )
        
        # Security-specific attributes
        self.base_address = base_address  # Alias for compatibility
        self.end_address = base_address + size - 1
        self.permission = permission  # Keep original permission for compatibility
        
        # For memory integrity checks
        self._shadow_data: Optional[bytearray] = None
        self._canaries: Dict[int, bytes] = {}
    
    def contains_address(self, address: int) -> bool:
        """Check if this segment contains the given address."""
        return self.contains(address)  # Use common implementation
    
    def relative_address(self, address: int) -> int:
        """Convert an absolute address to an offset within this segment."""
        if not self.contains_address(address):
            raise ValueError(f"Address 0x{address:08x} is outside segment {self.name}")
        return self.get_offset(address)  # Use common implementation
    
    def check_permission(self, address: int, required_permission: MemoryPermission) -> bool:
        """Check if the segment has the required permission for the given address."""
        if not self.contains_address(address):
            return False
        return (self.permission & required_permission) == required_permission
    
    def place_canary(self, offset: int, value: Optional[bytes] = None) -> bytes:
        """Place a canary value at the specified offset."""
        if offset < 0 or offset >= self.size:
            raise ValueError(f"Offset {offset} is outside segment bounds")
        
        # Generate a random canary value if none is provided
        if value is None:
            value = bytes(random.getrandbits(8) for _ in range(4))
        
        self._canaries[offset] = value
        # Write the canary to the actual memory
        for i, b in enumerate(value):
            if offset + i < self.size:
                self.data[offset + i] = b
                
        return value
    
    def check_canaries(self) -> List[Tuple[int, bytes, bytes]]:
        """Check all canaries and return a list of corrupted ones."""
        corrupted = []
        for offset, expected in self._canaries.items():
            actual = bytes(self.data[offset:offset + len(expected)])
            if actual != expected:
                corrupted.append((offset, expected, actual))
        return corrupted
    
    def enable_shadow_memory(self) -> None:
        """Enable shadow memory for this segment to detect unauthorized changes."""
        self._shadow_data = bytearray(self.data)
    
    def check_shadow_memory(self) -> List[int]:
        """Check for differences between shadow memory and actual memory."""
        if self._shadow_data is None:
            return []
        
        differences = []
        for i, (shadow, actual) in enumerate(zip(self._shadow_data, self.data)):
            if shadow != actual:
                differences.append(self.base_address + i)
        
        return differences
    
    def update_shadow_memory(self) -> None:
        """Update shadow memory to match current memory state."""
        if self._shadow_data is not None:
            self._shadow_data = bytearray(self.data)


class Memory(MemoryBase):
    """Security-enhanced memory subsystem with protection mechanisms and access controls."""
    
    def __init__(
        self,
        protection_level: MemoryProtectionLevel = MemoryProtectionLevel.STANDARD,
        enable_dep: bool = True,
        enable_aslr: bool = False,
        aslr_entropy: int = 8,  # bits of randomness for ASLR
        size: int = 65536,
        **kwargs
    ):
        super().__init__(size=size, **kwargs)
        
        # Security-specific attributes
        self.protection_level = protection_level
        self.enable_dep = enable_dep
        self.enable_aslr = enable_aslr
        self.aslr_entropy = aslr_entropy
        self.protection_events: List[ProtectionBypassAttempt] = []
        
        # ASLR offset for each memory region type
        self.aslr_offsets: Dict[str, int] = {}
        
        # Performance tracking (in addition to common base)
        self.protection_check_time = 0
        self.access_count = 0  # For compatibility
        
    def add_segment(
        self,
        segment: MemorySegment,
        apply_aslr: bool = True
    ) -> MemorySegment:
        """Add a memory segment with optional ASLR applied."""
        # Apply ASLR if enabled and requested
        if self.enable_aslr and apply_aslr:
            # Get or create an ASLR offset for this segment type
            if segment.name not in self.aslr_offsets:
                max_offset = (1 << self.aslr_entropy) - 1
                self.aslr_offsets[segment.name] = random.randint(0, max_offset) * 16
            
            offset = self.aslr_offsets[segment.name]
            segment.base_address += offset
            segment.start += offset  # Update common attribute
            segment.end_address += offset
        
        # Use common add_segment method
        super().add_segment(segment)
        return segment
    
    def find_segment(self, address: int) -> Optional[MemorySegment]:
        """Find the memory segment containing the given address."""
        return super().find_segment(address)  # Use common implementation
    
    def read(self, address: int, size: int = 4) -> int:
        """Read data from memory (MemoryBase interface)."""
        if size == 1:
            return self.read_byte(address)
        elif size == 4:
            return self.read_word(address)
        else:
            # Read multiple bytes and combine
            value = 0
            for i in range(size):
                value |= self.read_byte(address + i) << (i * 8)
            return value
    
    def write(self, address: int, value: int, size: int = 4) -> bool:
        """Write data to memory (MemoryBase interface)."""
        try:
            if size == 1:
                self.write_byte(address, value)
            elif size == 4:
                self.write_word(address, value)
            else:
                # Write multiple bytes
                for i in range(size):
                    byte_val = (value >> (i * 8)) & 0xFF
                    self.write_byte(address + i, byte_val)
            return True
        except MemoryError:
            return False
    
    def reset(self) -> None:
        """Reset memory to initial state."""
        super().reset()
        # Reset security-specific state
        self.protection_events.clear()
        self.aslr_offsets.clear()
        
        # Clear all segment data
        for segment in self.segments:
            segment.data = bytearray(segment.size)
            segment._shadow_data = None
            segment._canaries.clear()
    
    def read_byte(self, address: int, context: Dict[str, Any] = None) -> int:
        """Read a single byte from memory, enforcing memory protections."""
        self.access_count += 1
        # Log access for base class
        if self.enable_logging:
            self.log_access(MemoryAccess(
                cycle=0,  # Will be updated by caller
                address=address,
                size=1,
                access_type='read'
            ))
        context = context or {}
        
        # Find the segment containing this address
        segment = self.find_segment(address)
        if segment is None:
            self._record_protection_event(
                address, "read", MemoryPermission.NONE, 
                MemoryPermission.READ, context.get("instruction_pointer", 0), context
            )
            raise MemoryError(f"Segmentation fault: address 0x{address:08x} not mapped")
        
        # Check read permission if protection is enabled
        if (self.protection_level != MemoryProtectionLevel.NONE and 
                not segment.check_permission(address, MemoryPermission.READ)):
            self._record_protection_event(
                address, "read", segment.permission, 
                MemoryPermission.READ, context.get("instruction_pointer", 0), context
            )
            if self.protection_level >= MemoryProtectionLevel.STANDARD:
                raise MemoryError(f"Memory protection violation: cannot read from 0x{address:08x}")
        
        # Compute the offset within the segment
        offset = segment.relative_address(address)
        return segment.data[offset]
    
    def write_byte(self, address: int, value: int, context: Dict[str, Any] = None) -> None:
        """Write a single byte to memory, enforcing memory protections."""
        self.access_count += 1
        # Log access for base class
        if self.enable_logging:
            self.log_access(MemoryAccess(
                cycle=0,  # Will be updated by caller
                address=address,
                size=1,
                access_type='write',
                value=value
            ))
        context = context or {}
        
        # Find the segment containing this address
        segment = self.find_segment(address)
        if segment is None:
            self._record_protection_event(
                address, "write", MemoryPermission.NONE, 
                MemoryPermission.WRITE, context.get("instruction_pointer", 0), context
            )
            raise MemoryError(f"Segmentation fault: address 0x{address:08x} not mapped")
        
        # Check write permission if protection is enabled
        if (self.protection_level != MemoryProtectionLevel.NONE and 
                not segment.check_permission(address, MemoryPermission.WRITE)):
            self._record_protection_event(
                address, "write", segment.permission, 
                MemoryPermission.WRITE, context.get("instruction_pointer", 0), context
            )
            if self.protection_level >= MemoryProtectionLevel.STANDARD:
                raise MemoryError(f"Memory protection violation: cannot write to 0x{address:08x}")
        
        # Compute the offset within the segment
        offset = segment.relative_address(address)
        segment.data[offset] = value & 0xFF
    
    def execute(self, address: int, context: Dict[str, Any] = None) -> int:
        """Execute code at the given address, enforcing DEP and other protections."""
        self.access_count += 1
        # Log access for base class
        if self.enable_logging:
            self.log_access(MemoryAccess(
                cycle=0,  # Will be updated by caller
                address=address,
                size=1,
                access_type='execute'
            ))
        context = context or {}
        
        # Find the segment containing this address
        segment = self.find_segment(address)
        if segment is None:
            self._record_protection_event(
                address, "execute", MemoryPermission.NONE, 
                MemoryPermission.EXECUTE, context.get("instruction_pointer", 0), context
            )
            raise MemoryError(f"Segmentation fault: address 0x{address:08x} not mapped")
        
        # Check execute permission if DEP is enabled
        if (self.enable_dep and self.protection_level != MemoryProtectionLevel.NONE and 
                not segment.check_permission(address, MemoryPermission.EXECUTE)):
            self._record_protection_event(
                address, "execute", segment.permission, 
                MemoryPermission.EXECUTE, context.get("instruction_pointer", 0), context
            )
            if self.protection_level >= MemoryProtectionLevel.STANDARD:
                raise MemoryError(f"DEP violation: cannot execute code at 0x{address:08x}")
        
        # Read the instruction byte (assuming the simplest case of 1-byte instructions)
        offset = segment.relative_address(address)
        return segment.data[offset]
    
    def read_bytes(self, address: int, count: int, context: Dict[str, Any] = None) -> bytes:
        """Read multiple bytes from memory, enforcing memory protections."""
        result = bytearray(count)
        for i in range(count):
            result[i] = self.read_byte(address + i, context)
        return bytes(result)
    
    def write_bytes(self, address: int, data: bytes, context: Dict[str, Any] = None) -> None:
        """Write multiple bytes to memory, enforcing memory protections."""
        for i, b in enumerate(data):
            self.write_byte(address + i, b, context)
    
    def read_word(self, address: int, context: Dict[str, Any] = None) -> int:
        """Read a 32-bit word from memory, enforcing memory protections."""
        data = self.read_bytes(address, 4, context)
        return struct.unpack("<I", data)[0]
    
    def write_word(self, address: int, value: int, context: Dict[str, Any] = None) -> None:
        """Write a 32-bit word to memory, enforcing memory protections."""
        data = struct.pack("<I", value)
        self.write_bytes(address, data, context)
    
    def _record_protection_event(
        self,
        address: int,
        access_type: str,
        current_permission: MemoryPermission,
        required_permission: MemoryPermission,
        instruction_pointer: int,
        context: Dict[str, Any],
    ) -> None:
        """Record an attempt to bypass memory protection."""
        event = ProtectionBypassAttempt(
            address=address,
            access_type=access_type,
            current_permission=current_permission,
            required_permission=required_permission,
            instruction_pointer=instruction_pointer,
            context=context,
        )
        self.protection_events.append(event)
    
    def place_stack_canaries(self, stack_segment: MemorySegment, interval: int = 64) -> List[Tuple[int, bytes]]:
        """Place canaries at regular intervals in the stack segment."""
        canaries = []
        for offset in range(0, stack_segment.size, interval):
            value = stack_segment.place_canary(offset)
            canaries.append((stack_segment.base_address + offset, value))
        return canaries
    
    def check_segment_canaries(self, segment: MemorySegment) -> List[Tuple[int, bytes, bytes]]:
        """Check canaries in the given segment and return corrupted ones."""
        return segment.check_canaries()
    
    def enable_shadow_memory(self, segment: MemorySegment) -> None:
        """Enable shadow memory for the given segment."""
        segment.enable_shadow_memory()
    
    def check_shadow_memory(self, segment: MemorySegment) -> List[int]:
        """Check for unexpected changes in the segment using shadow memory."""
        return segment.check_shadow_memory()
    
    def get_protection_stats(self) -> Dict[str, Any]:
        """Get statistics about memory protection operations."""
        return {
            "access_count": self.access_count,
            "protection_check_time": self.protection_check_time,
            "protection_events": len(self.protection_events),
            "memory_segments": len(self.segments),
        }
    
    def get_memory_map(self) -> List[Dict[str, Any]]:
        """Get a detailed map of memory segments and their properties."""
        return [
            {
                "name": segment.name,
                "base_address": segment.base_address,
                "size": segment.size,
                "end_address": segment.end_address,
                "permission": segment.permission.name,
            }
            for segment in self.segments
        ]


class MemoryProtection:
    """Configurable memory protection system with various security mechanisms."""
    
    def __init__(
        self,
        level: MemoryProtectionLevel = MemoryProtectionLevel.STANDARD,
        dep_enabled: bool = True,
        aslr_enabled: bool = False,
        aslr_entropy: int = 8,
        stack_canaries: bool = False,
        shadow_memory: bool = False,
    ):
        self.level = level
        self.dep_enabled = dep_enabled
        self.aslr_enabled = aslr_enabled
        self.aslr_entropy = aslr_entropy
        self.stack_canaries = stack_canaries
        self.shadow_memory = shadow_memory
    
    def apply_to_memory(self, memory: Memory) -> None:
        """Apply these protection settings to a Memory instance."""
        memory.protection_level = self.level
        memory.enable_dep = self.dep_enabled
        memory.enable_aslr = self.aslr_enabled
        memory.aslr_entropy = self.aslr_entropy
    
    def apply_to_segment(self, segment: MemorySegment, memory: Memory) -> None:
        """Apply segment-specific protections."""
        if self.stack_canaries and segment.name == "stack":
            memory.place_stack_canaries(segment)
        
        if self.shadow_memory:
            memory.enable_shadow_memory(segment)
    
    def get_protection_description(self) -> Dict[str, Any]:
        """Get a description of the current protection configuration."""
        return {
            "protection_level": self.level.name,
            "dep_enabled": self.dep_enabled,
            "aslr_enabled": self.aslr_enabled,
            "aslr_entropy": self.aslr_entropy,
            "stack_canaries": self.stack_canaries,
            "shadow_memory": self.shadow_memory,
        }