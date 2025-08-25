"""Tests for memory coherence protocols."""

import pytest

from vm_emulator.memory.cache import (
    Cache, MESICache, MESIState, CoherenceProtocol,
    CacheLine
)
from vm_emulator.memory.coherence import (
    MemoryBus, CoherentMemorySystem, BusOperation, BusRequest
)


class TestCache:
    """Test the basic cache implementation."""
    
    def test_initialization(self):
        """Test cache initialization."""
        cache = Cache(cache_id=0, size=128, line_size=8, associativity=4)
        
        assert cache.cache_id == 0
        assert cache.size == 128
        assert cache.line_size == 8
        assert cache.associativity == 4
        assert cache.num_sets == 4  # 128 / (8 * 4)
        assert len(cache.sets) == 4
        assert len(cache.sets[0]) == 4  # 4-way
        assert cache.reads == 0
        assert cache.writes == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_read_miss(self):
        """Test cache read miss."""
        cache = Cache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Cache is empty, so read should miss
        result = cache.read(address=100)
        
        assert result is None
        assert cache.reads == 1
        assert cache.hits == 0
        assert cache.misses == 1
    
    def test_read_hit(self):
        """Test cache read hit after allocation."""
        cache = Cache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate a cache line
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data)  # Aligned address 96-103
        
        # Read should hit
        result = cache.read(address=100)
        
        assert result == 4  # data[4] = 4
        assert cache.reads == 1
        assert cache.hits == 1
        assert cache.misses == 0
    
    def test_write(self):
        """Test cache write."""
        cache = Cache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate a cache line
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data)  # Aligned address 96-103
        
        # Write to cache
        cache.write(address=100, value=42)
        
        # Read to verify
        result = cache.read(address=100)
        
        assert result == 42
        assert cache.writes == 1
        assert cache.reads == 1
        assert cache.hits == 2  # 1 for write, 1 for read
    
    def test_eviction(self):
        """Test cache line eviction."""
        # Create a cache with 2 sets, 1 way each, each line is 8 words
        cache = Cache(cache_id=0, size=16, line_size=8, associativity=1)
        
        # Allocate first line to set 0
        data1 = [i for i in range(8)]
        evicted, dirty = cache.allocate_line(address=0, data=data1)  # Set 0
        
        assert evicted is None
        assert not dirty
        
        # Write to make it dirty
        cache.write(address=0, value=42)
        
        # Allocate second line to set 1 (should not evict)
        data2 = [i + 10 for i in range(8)]
        evicted, dirty = cache.allocate_line(address=8, data=data2)  # Set 1
        
        assert evicted is None  # Different set, no eviction
        
        # Allocate third line to set 0 (should evict the first line)
        data3 = [i + 20 for i in range(8)]
        evicted, dirty = cache.allocate_line(address=16, data=data3)  # Back to set 0
        
        assert evicted is not None
        assert dirty
        assert evicted.address == 0
        assert evicted.data[0] == 42
        
        # First line should be evicted
        result = cache.read(address=0)
        assert result is None
        
        # Second line should still be there
        result = cache.read(address=8)
        assert result == 10
    
    def test_statistics(self):
        """Test cache statistics."""
        cache = Cache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate a cache line
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data)
        
        # Perform some operations
        cache.read(address=96)  # Hit
        cache.read(address=0)   # Miss
        cache.write(address=96, value=42)  # Hit
        
        # Get statistics
        stats = cache.get_statistics()
        
        assert stats["cache_id"] == 0
        assert stats["size"] == 128
        assert stats["line_size"] == 8
        assert stats["associativity"] == 4
        assert stats["reads"] == 2
        assert stats["writes"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3 * 100  # 66.67%


class TestMESICache:
    """Test the MESI protocol cache implementation."""
    
    def test_initialization(self):
        """Test MESI cache initialization."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        assert cache.cache_id == 0
        assert cache.line_states is not None
        
        # All lines should start INVALID
        for set_idx in range(cache.num_sets):
            for line_idx in range(cache.associativity):
                assert cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
    
    def test_read_exclusive(self):
        """Test read with exclusive state."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Read miss, should return need for shared read
        value, bus_op = cache.read(address=100)
        
        assert value is None
        assert bus_op == "read_shared"
        
        # Allocate line in exclusive state
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data, state=MESIState.EXCLUSIVE)
        
        # Read should now hit with no bus operation
        value, bus_op = cache.read(address=100)
        
        assert value == 4  # data[4] = 4
        assert bus_op == "none"
        
        # Check state didn't change
        line, set_idx, line_idx = cache._find_line(address=100)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.EXCLUSIVE
    
    def test_read_shared(self):
        """Test read with shared state."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate line in shared state
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data, state=MESIState.SHARED)
        
        # Read should hit with no bus operation
        value, bus_op = cache.read(address=100)
        
        assert value == 4
        assert bus_op == "none"
        
        # Check state didn't change
        line, set_idx, line_idx = cache._find_line(address=100)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.SHARED
    
    def test_read_modified(self):
        """Test read with modified state."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate line in modified state
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data, state=MESIState.MODIFIED)
        
        # Read should hit with no bus operation
        value, bus_op = cache.read(address=100)
        
        assert value == 4
        assert bus_op == "none"
        
        # Check state didn't change
        line, set_idx, line_idx = cache._find_line(address=100)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.MODIFIED
    
    def test_write_exclusive(self):
        """Test write with exclusive state."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate line in exclusive state
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data, state=MESIState.EXCLUSIVE)
        
        # Write should transition to modified without bus operation
        bus_op = cache.write(address=100, value=42)
        
        assert bus_op == "none"
        
        # Check state changed to modified
        line, set_idx, line_idx = cache._find_line(address=100)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.MODIFIED
        
        # Check value was written
        value, _ = cache.read(address=100)
        assert value == 42
    
    def test_write_shared(self):
        """Test write with shared state."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate line in shared state
        data = [i for i in range(8)]
        cache.allocate_line(address=96, data=data, state=MESIState.SHARED)
        
        # Write should transition to modified with invalidate bus operation
        bus_op = cache.write(address=100, value=42)
        
        assert bus_op == "invalidate"
        
        # Check state changed to modified
        line, set_idx, line_idx = cache._find_line(address=100)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.MODIFIED
        
        # Check value was written
        value, _ = cache.read(address=100)
        assert value == 42
    
    def test_write_miss(self):
        """Test write miss."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Write miss, should return need for exclusive read
        bus_op = cache.write(address=100, value=42)
        
        assert bus_op == "read_exclusive"
    
    def test_bus_read_handling(self):
        """Test handling of bus read from another cache."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate line in different states and test bus read handling
        
        # Modified state
        data = [i for i in range(8)]
        cache.allocate_line(address=0, data=data, state=MESIState.MODIFIED)
        
        # Bus read should transition to shared and return data
        should_respond, response_data = cache.handle_bus_read(address=0)
        
        assert should_respond
        assert response_data == data
        
        # Check state changed to shared
        line, set_idx, line_idx = cache._find_line(address=0)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.SHARED
        
        # Exclusive state
        data = [i for i in range(8)]
        cache.allocate_line(address=8, data=data, state=MESIState.EXCLUSIVE)
        
        # Bus read should transition to shared and return data
        should_respond, response_data = cache.handle_bus_read(address=8)
        
        assert should_respond
        assert response_data == data
        
        # Check state changed to shared
        line, set_idx, line_idx = cache._find_line(address=8)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.SHARED
        
        # Shared state
        data = [i for i in range(8)]
        cache.allocate_line(address=16, data=data, state=MESIState.SHARED)
        
        # Bus read with shared state should just return data, no state change
        should_respond, response_data = cache.handle_bus_read(address=16)
        
        assert should_respond
        assert response_data == data
        
        # Check state remained shared
        line, set_idx, line_idx = cache._find_line(address=16)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.SHARED
    
    def test_bus_read_exclusive_handling(self):
        """Test handling of bus read exclusive from another cache."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate lines in different states
        
        # Modified state
        data1 = [i for i in range(8)]
        cache.allocate_line(address=0, data=data1, state=MESIState.MODIFIED)
        
        # Bus read exclusive should invalidate line and return data
        should_respond, response_data = cache.handle_bus_read_exclusive(address=0)
        
        assert should_respond
        assert response_data == data1
        
        # Check state changed to invalid
        line, set_idx, line_idx = cache._find_line(address=0)
        assert line is None or cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
        
        # Exclusive state
        data2 = [i + 10 for i in range(8)]
        cache.allocate_line(address=8, data=data2, state=MESIState.EXCLUSIVE)
        
        # Bus read exclusive should invalidate line but not return data
        should_respond, response_data = cache.handle_bus_read_exclusive(address=8)
        
        assert not should_respond
        assert response_data is None
        
        # Check state changed to invalid
        line, set_idx, line_idx = cache._find_line(address=8)
        assert line is None or cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
        
        # Shared state
        data3 = [i + 20 for i in range(8)]
        cache.allocate_line(address=16, data=data3, state=MESIState.SHARED)
        
        # Bus read exclusive should invalidate line but not return data
        should_respond, response_data = cache.handle_bus_read_exclusive(address=16)
        
        assert not should_respond
        assert response_data is None
        
        # Check state changed to invalid
        line, set_idx, line_idx = cache._find_line(address=16)
        assert line is None or cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
    
    def test_bus_invalidate_handling(self):
        """Test handling of bus invalidate from another cache."""
        cache = MESICache(cache_id=0, size=128, line_size=8, associativity=4)
        
        # Allocate lines in different states
        
        # Exclusive state
        data1 = [i for i in range(8)]
        cache.allocate_line(address=0, data=data1, state=MESIState.EXCLUSIVE)
        
        # Bus invalidate should invalidate line
        invalidated = cache.handle_bus_invalidate(address=0)
        
        assert invalidated
        
        # Check state changed to invalid
        line, set_idx, line_idx = cache._find_line(address=0)
        assert line is None or cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
        
        # Shared state
        data2 = [i + 10 for i in range(8)]
        cache.allocate_line(address=8, data=data2, state=MESIState.SHARED)
        
        # Bus invalidate should invalidate line
        invalidated = cache.handle_bus_invalidate(address=8)
        
        assert invalidated
        
        # Check state changed to invalid
        line, set_idx, line_idx = cache._find_line(address=8)
        assert line is None or cache.line_states[(set_idx, line_idx)] == MESIState.INVALID
        
        # Modified state (shouldn't be invalidated by bus invalidate)
        data3 = [i + 20 for i in range(8)]
        cache.allocate_line(address=16, data=data3, state=MESIState.MODIFIED)
        
        # Bus invalidate should not invalidate modified line
        invalidated = cache.handle_bus_invalidate(address=16)
        
        assert not invalidated
        
        # Check state remained modified
        line, set_idx, line_idx = cache._find_line(address=16)
        assert cache.line_states[(set_idx, line_idx)] == MESIState.MODIFIED


class TestMemoryBus:
    """Test the memory bus implementation."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a main memory system
        self.main_memory = MockMemorySystem(size=256)
        
        # Create a memory bus with MESI protocol
        self.bus = MemoryBus(self.main_memory, CoherenceProtocol.MESI, latency=2)
        
        # Create and connect caches
        self.cache1 = MESICache(cache_id=0, size=64, line_size=8, associativity=2)
        self.cache2 = MESICache(cache_id=1, size=64, line_size=8, associativity=2)
        
        self.bus.connect_cache(self.cache1)
        self.bus.connect_cache(self.cache2)
    
    def test_initialization(self):
        """Test memory bus initialization."""
        assert self.bus.main_memory == self.main_memory
        assert self.bus.protocol == CoherenceProtocol.MESI
        assert self.bus.latency == 2
        assert len(self.bus.caches) == 2
        assert 0 in self.bus.caches
        assert 1 in self.bus.caches
    
    def test_read_shared_request(self):
        """Test READ_SHARED bus request."""
        # Initialize main memory
        for i in range(8):
            self.main_memory.memory[i] = i + 1
        
        # Create a read shared request
        request = BusRequest(
            operation=BusOperation.READ_SHARED,
            address=0,
            processor_id=0,
            thread_id="thread1",
        )
        
        # Submit the request
        self.bus.request(request)
        
        # Process the request (tick twice for latency)
        completed = self.bus.tick(timestamp=0)
        assert len(completed) == 0  # Not completed yet
        
        completed = self.bus.tick(timestamp=1)
        assert len(completed) == 1  # Completed
        assert completed[0] == request
        assert completed[0].completed
        
        # Check the result
        assert completed[0].result is not None
        assert "data" in completed[0].result
        assert completed[0].result["data"] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert "state" in completed[0].result
        assert completed[0].result["state"] == MESIState.EXCLUSIVE  # No other cache has it
    
    def test_read_exclusive_request(self):
        """Test READ_EXCLUSIVE bus request."""
        # Initialize main memory
        for i in range(8):
            self.main_memory.memory[i] = i + 1
        
        # Create a read exclusive request
        request = BusRequest(
            operation=BusOperation.READ_EXCLUSIVE,
            address=0,
            processor_id=0,
            thread_id="thread1",
        )
        
        # Submit the request
        self.bus.request(request)
        
        # Process the request (tick twice for latency)
        self.bus.tick(timestamp=0)
        completed = self.bus.tick(timestamp=1)
        
        # Check the result
        assert completed[0].result is not None
        assert "data" in completed[0].result
        assert completed[0].result["data"] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert "state" in completed[0].result
        assert completed[0].result["state"] == MESIState.EXCLUSIVE
    
    def test_write_back_request(self):
        """Test WRITE_BACK bus request."""
        # Create a write back request
        data = [10, 20, 30, 40, 50, 60, 70, 80]
        request = BusRequest(
            operation=BusOperation.WRITE_BACK,
            address=0,
            processor_id=0,
            thread_id="thread1",
            data=data,
        )
        
        # Submit the request
        self.bus.request(request)
        
        # Process the request
        self.bus.tick(timestamp=0)
        completed = self.bus.tick(timestamp=1)
        
        # Check the result
        assert completed[0].result is not None
        assert "success" in completed[0].result
        assert completed[0].result["success"]
        
        # Check that the data was written to main memory
        for i in range(8):
            assert self.main_memory.memory[i] == data[i]
    
    def test_invalidate_request(self):
        """Test INVALIDATE bus request."""
        # First, let cache1 and cache2 share a line
        data = [1, 2, 3, 4, 5, 6, 7, 8]
        self.cache1.allocate_line(address=0, data=data, state=MESIState.SHARED)
        self.cache2.allocate_line(address=0, data=data, state=MESIState.SHARED)
        
        # Create an invalidate request from cache1
        request = BusRequest(
            operation=BusOperation.INVALIDATE,
            address=0,
            processor_id=0,  # From cache1
            thread_id="thread1",
        )
        
        # Submit the request
        self.bus.request(request)
        
        # Process the request
        self.bus.tick(timestamp=0)
        completed = self.bus.tick(timestamp=1)
        
        # Check the result
        assert completed[0].result is not None
        assert "success" in completed[0].result
        assert completed[0].result["success"]
        
        # Check that cache2's line was invalidated
        line, set_idx, line_idx = self.cache2._find_line(address=0)
        assert line is None or self.cache2.line_states[(set_idx, line_idx)] == MESIState.INVALID
    
    def test_coherence_protocol(self):
        """Test full coherence protocol with multiple caches."""
        # Initialize main memory
        for i in range(16):
            self.main_memory.memory[i] = i
        
        # Cache1 reads address 0
        req1 = BusRequest(
            operation=BusOperation.READ_SHARED,
            address=0,
            processor_id=0,
            thread_id="thread1",
        )
        
        self.bus.request(req1)
        self.bus.tick(timestamp=0)
        completed1 = self.bus.tick(timestamp=1)
        
        # Cache1 should have the line in EXCLUSIVE state
        data1 = completed1[0].result["data"]
        self.cache1.allocate_line(address=0, data=data1, state=MESIState.EXCLUSIVE)
        
        # Cache2 reads the same address
        req2 = BusRequest(
            operation=BusOperation.READ_SHARED,
            address=0,
            processor_id=1,
            thread_id="thread2",
        )
        
        self.bus.request(req2)
        self.bus.tick(timestamp=2)
        completed2 = self.bus.tick(timestamp=3)
        
        # Both caches should now have the line in SHARED state
        data2 = completed2[0].result["data"]
        self.cache2.allocate_line(address=0, data=data2, state=MESIState.SHARED)
        
        # Check that cache1's state was updated to SHARED
        line1, set1_idx, line1_idx = self.cache1._find_line(address=0)
        assert self.cache1.line_states[(set1_idx, line1_idx)] == MESIState.SHARED
        
        # Cache1 wants to write to the address
        req3 = BusRequest(
            operation=BusOperation.INVALIDATE,
            address=0,
            processor_id=0,
            thread_id="thread1",
        )
        
        self.bus.request(req3)
        self.bus.tick(timestamp=4)
        completed3 = self.bus.tick(timestamp=5)
        
        # Cache1 can now modify its line
        self.cache1.set_state(address=0, state=MESIState.MODIFIED)
        
        # Cache2's line should be invalidated
        line2, set2_idx, line2_idx = self.cache2._find_line(address=0)
        assert line2 is None or self.cache2.line_states[(set2_idx, line2_idx)] == MESIState.INVALID
        
        # Cache1 writes back the modified line
        modified_data = data1.copy()
        modified_data[0] = 100
        
        req4 = BusRequest(
            operation=BusOperation.WRITE_BACK,
            address=0,
            processor_id=0,
            thread_id="thread1",
            data=modified_data,
        )
        
        self.bus.request(req4)
        self.bus.tick(timestamp=6)
        completed4 = self.bus.tick(timestamp=7)
        
        # Check that the data was written to main memory
        assert self.main_memory.memory[0] == 100
    
    def test_statistics(self):
        """Test bus statistics."""
        # Generate some bus traffic
        
        # Read shared
        self.bus.request(BusRequest(
            operation=BusOperation.READ_SHARED,
            address=0,
            processor_id=0,
            thread_id="thread1",
        ))
        
        # Read exclusive
        self.bus.request(BusRequest(
            operation=BusOperation.READ_EXCLUSIVE,
            address=8,
            processor_id=1,
            thread_id="thread2",
        ))
        
        # Invalidate
        self.bus.request(BusRequest(
            operation=BusOperation.INVALIDATE,
            address=0,
            processor_id=1,
            thread_id="thread2",
        ))
        
        # Write back
        self.bus.request(BusRequest(
            operation=BusOperation.WRITE_BACK,
            address=8,
            processor_id=1,
            thread_id="thread2",
            data=[10] * 8,
        ))
        
        # Process all requests
        for i in range(8):
            self.bus.tick(timestamp=i)
        
        # Get statistics
        stats = self.bus.get_statistics()
        
        assert stats["protocol"] == "MESI"
        assert stats["latency"] == 2
        assert stats["connected_caches"] == 2
        assert stats["total_requests"] == 4
        assert stats["read_requests"] == 2
        assert stats["write_requests"] == 1
        assert stats["invalidation_requests"] == 1
        assert stats["bus_cycles_busy"] >= 4  # At least 4 cycles


class MockMemorySystem:
    """Mock memory system for testing."""
    
    def __init__(self, size):
        """Initialize the mock memory system."""
        self.size = size
        self.memory = [0] * size


class TestCoherentMemorySystem:
    """Test the coherent memory system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.memory_system = CoherentMemorySystem(
            size=256,
            protocol=CoherenceProtocol.MESI,
            bus_latency=1,
            cache_size=64,
            cache_line_size=8,
            cache_associativity=2,
        )
    
    def test_initialization(self):
        """Test coherent memory system initialization."""
        assert self.memory_system.main_memory.size == 256
        assert self.memory_system.protocol == CoherenceProtocol.MESI
        assert self.memory_system.bus.latency == 1
        assert self.memory_system.cache_size == 64
        assert self.memory_system.cache_line_size == 8
        assert self.memory_system.cache_associativity == 2
        assert len(self.memory_system.caches) == 0
    
    def test_cache_creation(self):
        """Test processor cache creation."""
        self.memory_system.create_cache(processor_id=0)
        self.memory_system.create_cache(processor_id=1)
        
        assert len(self.memory_system.caches) == 2
        assert 0 in self.memory_system.caches
        assert 1 in self.memory_system.caches
        
        # Check that caches are connected to the bus
        assert len(self.memory_system.bus.caches) == 2
        assert 0 in self.memory_system.bus.caches
        assert 1 in self.memory_system.bus.caches
    
    def test_memory_read(self):
        """Test memory read with caching."""
        # Create caches
        self.memory_system.create_cache(processor_id=0)
        self.memory_system.create_cache(processor_id=1)
        
        # Initialize main memory
        for i in range(256):
            self.memory_system.main_memory.memory[i] = i
        
        # Read from processor 0
        value0 = self.memory_system.read(
            address=10,
            processor_id=0,
            thread_id="thread1",
            timestamp=0,
        )
        
        assert value0 == 10
        
        # Read from processor 1
        value1 = self.memory_system.read(
            address=10,
            processor_id=1,
            thread_id="thread2",
            timestamp=1,
        )
        
        assert value1 == 10
        
        # Both caches should have the line in SHARED state
        cache0 = self.memory_system.caches[0]
        cache1 = self.memory_system.caches[1]
        
        line0, set0_idx, line0_idx = cache0._find_line(address=10)
        line1, set1_idx, line1_idx = cache1._find_line(address=10)
        
        assert cache0.line_states[(set0_idx, line0_idx)] == MESIState.SHARED
        assert cache1.line_states[(set1_idx, line1_idx)] == MESIState.SHARED
    
    def test_memory_write(self):
        """Test memory write with cache coherence."""
        # Create caches
        self.memory_system.create_cache(processor_id=0)
        self.memory_system.create_cache(processor_id=1)
        
        # Initialize main memory
        for i in range(256):
            self.memory_system.main_memory.memory[i] = i
        
        # Both processors read the same address
        self.memory_system.read(address=20, processor_id=0, thread_id="thread1", timestamp=0)
        self.memory_system.read(address=20, processor_id=1, thread_id="thread2", timestamp=1)
        
        # Processor 0 writes to the address
        self.memory_system.write(
            address=20,
            value=100,
            processor_id=0,
            thread_id="thread1",
            timestamp=2,
        )
        
        # Processor 0's cache should have the line in MODIFIED state
        cache0 = self.memory_system.caches[0]
        line0, set0_idx, line0_idx = cache0._find_line(address=20)
        assert cache0.line_states[(set0_idx, line0_idx)] == MESIState.MODIFIED
        
        # Processor 1's cache should have invalidated the line
        cache1 = self.memory_system.caches[1]
        line1, set1_idx, line1_idx = cache1._find_line(address=20)
        assert line1 is None or cache1.line_states[(set1_idx, line1_idx)] == MESIState.INVALID
        
        # Processor 1 reads again, should get the updated value
        value1 = self.memory_system.read(
            address=20,
            processor_id=1,
            thread_id="thread2",
            timestamp=3,
        )
        
        assert value1 == 100
        
        # Both caches should have the line in SHARED state again
        line0, set0_idx, line0_idx = cache0._find_line(address=20)
        line1, set1_idx, line1_idx = cache1._find_line(address=20)
        
        assert cache0.line_states[(set0_idx, line0_idx)] == MESIState.SHARED
        assert cache1.line_states[(set1_idx, line1_idx)] == MESIState.SHARED
    
    def test_flush_caches(self):
        """Test flushing all caches."""
        # Create caches
        self.memory_system.create_cache(processor_id=0)
        self.memory_system.create_cache(processor_id=1)
        
        # Initialize main memory
        for i in range(256):
            self.memory_system.main_memory.memory[i] = i
        
        # Read and modify data in caches
        self.memory_system.read(address=30, processor_id=0, thread_id="thread1", timestamp=0)
        self.memory_system.write(address=30, value=200, processor_id=0, thread_id="thread1", timestamp=1)
        
        self.memory_system.read(address=40, processor_id=1, thread_id="thread2", timestamp=2)
        self.memory_system.write(address=40, value=300, processor_id=1, thread_id="thread2", timestamp=3)
        
        # Main memory should still have original values
        assert self.memory_system.main_memory.memory[30] == 30
        assert self.memory_system.main_memory.memory[40] == 40
        
        # Flush caches
        self.memory_system.flush_caches()
        
        # Main memory should now have updated values
        assert self.memory_system.main_memory.memory[30] == 200
        assert self.memory_system.main_memory.memory[40] == 300
    
    def test_access_history(self):
        """Test tracking memory access history."""
        # Create cache
        self.memory_system.create_cache(processor_id=0)
        
        # Perform some accesses
        self.memory_system.read(address=50, processor_id=0, thread_id="thread1", timestamp=0)
        self.memory_system.write(address=50, value=500, processor_id=0, thread_id="thread1", timestamp=1)
        self.memory_system.read(address=60, processor_id=0, thread_id="thread1", timestamp=2)
        
        # Get access history
        history = self.memory_system.get_access_history()
        
        assert len(history) == 3
        
        assert history[0]["address"] == 50
        assert history[0]["type"] == "read"
        assert history[0]["processor_id"] == 0
        assert history[0]["thread_id"] == "thread1"
        assert history[0]["timestamp"] == 0
        
        assert history[1]["address"] == 50
        assert history[1]["type"] == "write"
        assert history[1]["value"] == 500
        
        assert history[2]["address"] == 60
        assert history[2]["type"] == "read"
        
        # Test filtering
        addr50_history = self.memory_system.get_access_history(address=50)
        assert len(addr50_history) == 2
        
        write_history = self.memory_system.get_access_history(access_type="write")
        assert len(write_history) == 1
        assert write_history[0]["address"] == 50
    
    def test_statistics(self):
        """Test cache and bus statistics."""
        # Create caches
        self.memory_system.create_cache(processor_id=0)
        self.memory_system.create_cache(processor_id=1)
        
        # Perform some accesses
        self.memory_system.read(address=70, processor_id=0, thread_id="thread1", timestamp=0)
        self.memory_system.read(address=70, processor_id=0, thread_id="thread1", timestamp=1)  # Cache hit
        self.memory_system.write(address=70, value=700, processor_id=0, thread_id="thread1", timestamp=2)
        
        self.memory_system.read(address=70, processor_id=1, thread_id="thread2", timestamp=3)
        
        # Get cache statistics
        cache_stats = self.memory_system.get_cache_statistics()
        
        assert 0 in cache_stats
        assert 1 in cache_stats
        
        # Cache 0 should have 2 hits (1 read, 1 write) and 1 miss
        assert cache_stats[0]["hits"] >= 2
        assert cache_stats[0]["misses"] >= 1
        
        # Get bus statistics
        bus_stats = self.memory_system.get_bus_statistics()
        
        assert bus_stats["protocol"] == "MESI"
        assert bus_stats["connected_caches"] == 2
        
        # Bus should have handled at least read, invalidate, and read requests
        assert bus_stats["total_requests"] >= 2


if __name__ == "__main__":
    pytest.main(["-v", "test_coherence.py"])