"""
Tests for the memory subsystem of the secure VM.

This module tests the memory model, memory protection mechanisms, 
and related security features.
"""

import pytest
from secure_vm.memory import (
    Memory, MemorySegment, MemoryPermission, MemoryProtectionLevel, MemoryProtection
)


def test_memory_segment_creation():
    """Test creating a memory segment with specific attributes."""
    segment = MemorySegment(
        base_address=0x1000,
        size=0x1000,
        permission=MemoryPermission.READ_WRITE,
        name="test_segment"
    )
    
    assert segment.base_address == 0x1000
    assert segment.size == 0x1000
    assert segment.end_address == 0x1FFF
    assert segment.permission == MemoryPermission.READ_WRITE
    assert segment.name == "test_segment"
    assert len(segment.data) == 0x1000


def test_memory_segment_contains_address():
    """Test checking if a segment contains a given address."""
    segment = MemorySegment(base_address=0x1000, size=0x1000)
    
    assert segment.contains_address(0x1000) is True
    assert segment.contains_address(0x1FFF) is True
    assert segment.contains_address(0x1500) is True
    assert segment.contains_address(0x0FFF) is False
    assert segment.contains_address(0x2000) is False


def test_memory_segment_relative_address():
    """Test converting absolute addresses to segment offsets."""
    segment = MemorySegment(base_address=0x1000, size=0x1000)
    
    assert segment.relative_address(0x1000) == 0
    assert segment.relative_address(0x1500) == 0x500
    assert segment.relative_address(0x1FFF) == 0xFFF
    
    with pytest.raises(ValueError):
        segment.relative_address(0x0FFF)
    
    with pytest.raises(ValueError):
        segment.relative_address(0x2000)


def test_memory_segment_permission_check():
    """Test segment permission checking."""
    segment = MemorySegment(
        base_address=0x1000, 
        size=0x1000, 
        permission=MemoryPermission.READ_WRITE
    )
    
    assert segment.check_permission(0x1500, MemoryPermission.READ) is True
    assert segment.check_permission(0x1500, MemoryPermission.WRITE) is True
    assert segment.check_permission(0x1500, MemoryPermission.EXECUTE) is False
    assert segment.check_permission(0x1500, MemoryPermission.READ_WRITE) is True
    
    # Address outside segment should return False
    assert segment.check_permission(0x0FFF, MemoryPermission.READ) is False


def test_memory_segment_canaries():
    """Test stack canary placement and verification."""
    segment = MemorySegment(base_address=0x1000, size=0x1000)
    
    # Place a canary
    canary_value = segment.place_canary(0x100)
    assert len(canary_value) == 4
    
    # Verify that the canary was written to memory
    for i, b in enumerate(canary_value):
        assert segment.data[0x100 + i] == b
    
    # Check that the canary is intact
    corrupted = segment.check_canaries()
    assert len(corrupted) == 0
    
    # Corrupt the canary
    segment.data[0x101] = (segment.data[0x101] + 1) % 256
    
    # Check that corruption is detected
    corrupted = segment.check_canaries()
    assert len(corrupted) == 1
    assert corrupted[0][0] == 0x100


def test_memory_creation():
    """Test creating the memory subsystem with different protection settings."""
    # Default settings
    memory = Memory()
    assert memory.protection_level == MemoryProtectionLevel.STANDARD
    assert memory.enable_dep is True
    assert memory.enable_aslr is False
    
    # Custom settings
    memory = Memory(
        protection_level=MemoryProtectionLevel.MAXIMUM,
        enable_dep=False,
        enable_aslr=True,
        aslr_entropy=12
    )
    assert memory.protection_level == MemoryProtectionLevel.MAXIMUM
    assert memory.enable_dep is False
    assert memory.enable_aslr is True
    assert memory.aslr_entropy == 12


def test_memory_add_segment():
    """Test adding segments to memory."""
    memory = Memory()
    
    segment1 = memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, name="segment1")
    )
    segment2 = memory.add_segment(
        MemorySegment(base_address=0x2000, size=0x1000, name="segment2")
    )
    
    assert len(memory.segments) == 2
    assert memory.segments[0] is segment1
    assert memory.segments[1] is segment2


def test_memory_find_segment():
    """Test finding a segment containing a given address."""
    memory = Memory()
    
    segment1 = memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, name="segment1")
    )
    segment2 = memory.add_segment(
        MemorySegment(base_address=0x2000, size=0x1000, name="segment2")
    )
    
    assert memory.find_segment(0x1500) is segment1
    assert memory.find_segment(0x2500) is segment2
    assert memory.find_segment(0x3000) is None


def test_memory_read_write_byte():
    """Test reading and writing individual bytes to memory."""
    memory = Memory()
    
    segment = memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, permission=MemoryPermission.READ_WRITE)
    )
    
    # Write a byte
    memory.write_byte(0x1100, 0xAA)
    
    # Read it back
    assert memory.read_byte(0x1100) == 0xAA
    
    # Check it was stored in the segment's data
    assert segment.data[0x100] == 0xAA


def test_memory_read_write_word():
    """Test reading and writing 32-bit words to memory."""
    memory = Memory()
    
    memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, permission=MemoryPermission.READ_WRITE)
    )
    
    # Write a word
    memory.write_word(0x1100, 0x12345678)
    
    # Read it back
    assert memory.read_word(0x1100) == 0x12345678


def test_memory_read_write_protection():
    """Test memory access protection enforcement."""
    # Create memory with standard protection
    memory = Memory(protection_level=MemoryProtectionLevel.STANDARD)
    
    # Add a read-only segment
    memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, permission=MemoryPermission.READ)
    )
    
    # Reading should succeed
    assert memory.read_byte(0x1100) == 0
    
    # Writing should fail with protection error
    with pytest.raises(MemoryError, match="Memory protection violation"):
        memory.write_byte(0x1100, 0xAA)


def test_memory_execute_protection():
    """Test DEP (Data Execution Prevention) enforcement."""
    # Create memory with DEP enabled
    memory = Memory(enable_dep=True)
    
    # Add a non-executable segment
    memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, permission=MemoryPermission.READ_WRITE)
    )
    
    # Executing should fail with DEP violation
    with pytest.raises(MemoryError, match="DEP violation"):
        memory.execute(0x1100)
    
    # Add an executable segment
    memory.add_segment(
        MemorySegment(base_address=0x2000, size=0x1000, permission=MemoryPermission.READ_EXECUTE)
    )
    
    # Executing from this segment should succeed
    memory.execute(0x2100)


def test_memory_stack_canaries():
    """Test stack canary placement and checking."""
    memory = Memory()
    
    stack_segment = memory.add_segment(
        MemorySegment(base_address=0x8000, size=0x1000, name="stack")
    )
    
    # Place canaries
    canaries = memory.place_stack_canaries(stack_segment, interval=128)
    assert len(canaries) > 0
    
    # Check canaries (should be intact)
    corrupted = memory.check_segment_canaries(stack_segment)
    assert len(corrupted) == 0
    
    # Corrupt a canary
    stack_segment.data[128] = (stack_segment.data[128] + 1) % 256
    
    # Check canaries again (should detect corruption)
    corrupted = memory.check_segment_canaries(stack_segment)
    assert len(corrupted) > 0


def test_memory_protection_applies_settings():
    """Test that MemoryProtection correctly applies settings to Memory."""
    protection = MemoryProtection(
        level=MemoryProtectionLevel.MAXIMUM,
        dep_enabled=True,
        aslr_enabled=True,
        aslr_entropy=10,
        stack_canaries=True,
        shadow_memory=True
    )
    
    memory = Memory()
    protection.apply_to_memory(memory)
    
    assert memory.protection_level == MemoryProtectionLevel.MAXIMUM
    assert memory.enable_dep is True
    assert memory.enable_aslr is True
    assert memory.aslr_entropy == 10


def test_memory_get_protection_stats():
    """Test retrieving memory protection statistics."""
    memory = Memory()
    
    memory.add_segment(MemorySegment(base_address=0x1000, size=0x1000))
    memory.add_segment(MemorySegment(base_address=0x2000, size=0x1000))
    
    # Perform some memory operations
    memory.write_byte(0x1100, 0xAA)
    memory.read_byte(0x1100)
    
    # Get stats
    stats = memory.get_protection_stats()
    
    assert stats["access_count"] == 2
    assert stats["memory_segments"] == 2


def test_memory_aslr():
    """Test Address Space Layout Randomization (ASLR)."""
    # Create memory with ASLR enabled
    memory = Memory(enable_aslr=True, aslr_entropy=8)
    
    segment1 = MemorySegment(base_address=0x1000, size=0x1000, name="code")
    segment2 = MemorySegment(base_address=0x2000, size=0x1000, name="code")
    
    # Add segments with ASLR
    actual_segment1 = memory.add_segment(segment1, apply_aslr=True)
    actual_segment2 = memory.add_segment(segment2, apply_aslr=True)
    
    # Segments with the same name should receive the same offset
    offset = actual_segment1.base_address - 0x1000
    assert actual_segment2.base_address == 0x2000 + offset
    
    # Non-randomized segment
    segment3 = MemorySegment(base_address=0x3000, size=0x1000, name="fixed")
    actual_segment3 = memory.add_segment(segment3, apply_aslr=False)
    assert actual_segment3.base_address == 0x3000


def test_memory_protection_log():
    """Test that protection violations are logged."""
    memory = Memory(protection_level=MemoryProtectionLevel.STANDARD)
    
    memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000, permission=MemoryPermission.READ)
    )
    
    # Attempt to write to read-only memory (will fail)
    try:
        memory.write_byte(0x1100, 0xAA)
    except MemoryError:
        pass
    
    # Check that the violation was logged
    assert len(memory.protection_events) == 1
    event = memory.protection_events[0]
    assert event.address == 0x1100
    assert event.access_type == "write"
    assert event.current_permission == MemoryPermission.READ
    assert event.required_permission == MemoryPermission.WRITE


def test_memory_shadow_memory():
    """Test shadow memory for detecting unauthorized changes."""
    memory = Memory()
    
    segment = memory.add_segment(
        MemorySegment(base_address=0x1000, size=0x1000)
    )
    
    # Enable shadow memory
    memory.enable_shadow_memory(segment)
    
    # Make authorized changes
    memory.write_byte(0x1100, 0xAA)
    memory.write_byte(0x1200, 0xBB)
    
    # Update shadow memory to match current state
    segment.update_shadow_memory()
    
    # No differences should be detected
    differences = memory.check_shadow_memory(segment)
    assert len(differences) == 0
    
    # Make unauthorized changes (directly modify segment data)
    segment.data[0x300] = 0xCC
    
    # Check for differences
    differences = memory.check_shadow_memory(segment)
    assert len(differences) == 1
    assert differences[0] == 0x1300