"""Cache implementation for the memory system."""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Any


class CacheLine:
    """Represents a single cache line."""
    
    def __init__(self, address: int, size: int = 8):
        """
        Initialize a cache line.
        
        Args:
            address: Memory address mapped to this line
            size: Number of words in the cache line
        """
        self.address = address
        self.size = size
        self.tag = address // size  # Address tag
        self.data = [0] * size      # Cache line data
        self.valid = False          # Whether the line contains valid data
        self.dirty = False          # Whether the line has been modified
        self.last_access = 0        # Timestamp of last access (for LRU)
        
    def __str__(self) -> str:
        """String representation of the cache line."""
        state = "V" if self.valid else "-"
        state += "D" if self.dirty else "-"
        return f"Line[{self.tag:#x}] {state} {self.data}"
    
    def read(self, offset: int) -> int:
        """
        Read a word from the cache line.
        
        Args:
            offset: Offset within the cache line
            
        Returns:
            The value at the specified offset
        """
        if not self.valid:
            raise ValueError("Reading from invalid cache line")
        
        if not 0 <= offset < self.size:
            raise ValueError(f"Offset {offset} out of range for cache line size {self.size}")
        
        return self.data[offset]
    
    def write(self, offset: int, value: int) -> None:
        """
        Write a word to the cache line.
        
        Args:
            offset: Offset within the cache line
            value: Value to write
        """
        if not self.valid:
            raise ValueError("Writing to invalid cache line")
        
        if not 0 <= offset < self.size:
            raise ValueError(f"Offset {offset} out of range for cache line size {self.size}")
        
        self.data[offset] = value
        self.dirty = True
    
    def invalidate(self) -> None:
        """Invalidate the cache line."""
        self.valid = False
        self.dirty = False
    
    def update(self, data: List[int]) -> None:
        """
        Update the cache line with new data.
        
        Args:
            data: New data for the cache line
        """
        if len(data) != self.size:
            raise ValueError(f"Data size {len(data)} does not match cache line size {self.size}")
        
        self.data = data.copy()
        self.valid = True
        self.dirty = False
    
    def is_hit(self, address: int) -> bool:
        """
        Check if the given address hits this cache line.
        
        Args:
            address: Memory address to check
            
        Returns:
            True if the address hits this cache line
        """
        return self.valid and address // self.size == self.tag


class MESIState(Enum):
    """MESI cache coherence protocol states."""
    MODIFIED = auto()   # Modified: Line has been modified, only copy
    EXCLUSIVE = auto()  # Exclusive: Line has not been modified, only copy
    SHARED = auto()     # Shared: Line has not been modified, other copies exist
    INVALID = auto()    # Invalid: Line is not valid


class MOESIState(Enum):
    """MOESI cache coherence protocol states."""
    MODIFIED = auto()   # Modified: Line has been modified, only copy
    OWNED = auto()      # Owned: Line has been modified, other copies exist
    EXCLUSIVE = auto()  # Exclusive: Line has not been modified, only copy
    SHARED = auto()     # Shared: Line has not been modified, other copies exist
    INVALID = auto()    # Invalid: Line is not valid


class DragonState(Enum):
    """Dragon cache coherence protocol states."""
    EXCLUSIVE_CLEAN = auto()    # Exclusive, not modified
    EXCLUSIVE_MODIFIED = auto() # Exclusive, modified
    SHARED_CLEAN = auto()       # Shared, not modified
    SHARED_MODIFIED = auto()    # Shared, modified
    INVALID = auto()            # Invalid


class CoherenceProtocol(Enum):
    """Available cache coherence protocols."""
    NONE = auto()    # No coherence protocol
    MESI = auto()    # MESI protocol
    MOESI = auto()   # MOESI protocol
    DRAGON = auto()  # Dragon protocol


class Cache:
    """Base class for processor cache implementations."""
    
    def __init__(
        self,
        cache_id: int,
        size: int = 1024,  # Total cache size in words
        line_size: int = 8,  # Words per cache line
        associativity: int = 4,  # Ways of associativity
    ):
        """
        Initialize the cache.
        
        Args:
            cache_id: Unique ID for this cache
            size: Total cache size in words
            line_size: Number of words per cache line
            associativity: Number of ways in the cache
        """
        self.cache_id = cache_id
        self.size = size
        self.line_size = line_size
        self.associativity = associativity
        
        # Calculate cache geometry
        self.num_sets = size // (line_size * associativity)
        
        # Initialize cache sets (each set contains multiple lines)
        self.sets: List[List[CacheLine]] = []
        for _ in range(self.num_sets):
            set_lines = []
            for _ in range(associativity):
                # Create a placeholder cache line with invalid address
                set_lines.append(CacheLine(address=0, size=line_size))
            self.sets.append(set_lines)
        
        # Statistics
        self.reads = 0
        self.writes = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Access timestamp for LRU
        self.access_time = 0
    
    def __str__(self) -> str:
        """String representation of the cache."""
        result = [f"Cache {self.cache_id}: {self.size} words, {self.line_size} words/line, {self.associativity}-way"]
        result.append(f"Hits: {self.hits}, Misses: {self.misses}, Hit Rate: {self.get_hit_rate():.2f}%")
        
        for set_idx, set_lines in enumerate(self.sets):
            result.append(f"Set {set_idx}: {', '.join(str(line) for line in set_lines)}")
        
        return "\n".join(result)
    
    def _get_set_index(self, address: int) -> int:
        """
        Get the set index for a memory address.
        
        Args:
            address: Memory address
            
        Returns:
            Set index
        """
        return (address // self.line_size) % self.num_sets
    
    def _get_offset(self, address: int) -> int:
        """
        Get the offset within a cache line for a memory address.
        
        Args:
            address: Memory address
            
        Returns:
            Offset within cache line
        """
        return address % self.line_size
    
    def _find_line(self, address: int) -> Tuple[Optional[CacheLine], int, int]:
        """
        Find a cache line for the given address.
        
        Args:
            address: Memory address
            
        Returns:
            Tuple of (cache_line, set_index, line_index), or (None, set_index, -1) if not found
        """
        set_idx = self._get_set_index(address)
        set_lines = self.sets[set_idx]
        
        for i, line in enumerate(set_lines):
            if line.is_hit(address):
                return line, set_idx, i
        
        return None, set_idx, -1
    
    def _select_victim(self, set_idx: int) -> int:
        """
        Select a victim cache line for replacement using LRU policy.
        
        Args:
            set_idx: Cache set index
            
        Returns:
            Index of the victim line within the set
        """
        set_lines = self.sets[set_idx]
        
        # Find the least recently used line
        min_access_time = float('inf')
        victim_idx = 0
        
        for i, line in enumerate(set_lines):
            if not line.valid:
                # Found an invalid line, use it
                return i
            
            if line.last_access < min_access_time:
                min_access_time = line.last_access
                victim_idx = i
        
        return victim_idx
    
    def read(self, address: int) -> int:
        """
        Read a value from the cache.
        
        Args:
            address: Memory address to read
            
        Returns:
            The value at the address, or None if not in cache
        """
        self.reads += 1
        self.access_time += 1
        
        # Find cache line for this address
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            # Cache hit
            self.hits += 1
            line.last_access = self.access_time
            offset = self._get_offset(address)
            return line.read(offset)
        
        # Cache miss
        self.misses += 1
        return None
    
    def write(self, address: int, value: int) -> None:
        """
        Write a value to the cache.
        
        Args:
            address: Memory address to write
            value: Value to write
        """
        self.writes += 1
        self.access_time += 1
        
        # Find cache line for this address
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            # Cache hit
            self.hits += 1
            line.last_access = self.access_time
            offset = self._get_offset(address)
            line.write(offset, value)
        else:
            # Cache miss
            self.misses += 1
    
    def allocate_line(
        self, address: int, data: List[int]
    ) -> Tuple[Optional[CacheLine], bool]:
        """
        Allocate a cache line for the given address.
        
        Args:
            address: Starting memory address
            data: Data for the cache line
            
        Returns:
            Tuple of (evicted_line, was_dirty) if a line was evicted, or (None, False) otherwise
        """
        # Align address to cache line boundary
        aligned_addr = (address // self.line_size) * self.line_size
        
        # Calculate set index for this address
        set_idx = self._get_set_index(aligned_addr)
        
        # Check if the address is already in the cache (avoid duplicate allocation)
        line, existing_set_idx, existing_line_idx = self._find_line(aligned_addr)
        if line is not None:
            # Address already cached, just update the data and access time
            line.update(data)
            line.last_access = self.access_time
            return None, False
            
        # Need to allocate a new line, select a victim
        victim_idx = self._select_victim(set_idx)
        
        # Get the victim line
        victim = self.sets[set_idx][victim_idx]
        evicted = None
        was_dirty = False
        
        # If the victim is valid, we're evicting it
        if victim.valid:
            # Create a copy of the victim line to return
            evicted = CacheLine(victim.address, victim.size)
            evicted.data = victim.data.copy()
            evicted.valid = True
            evicted.dirty = victim.dirty
            was_dirty = victim.dirty
            self.evictions += 1
        
        # Create a new cache line to replace the victim
        new_line = CacheLine(aligned_addr, self.line_size)
        new_line.update(data)
        new_line.last_access = self.access_time
        
        # Replace the victim with the new line
        self.sets[set_idx][victim_idx] = new_line
        
        return evicted, was_dirty
    
    def invalidate_line(self, address: int) -> bool:
        """
        Invalidate a cache line.
        
        Args:
            address: Memory address
            
        Returns:
            True if a line was invalidated, False otherwise
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            line.invalidate()
            return True
        
        return False
    
    def flush(self) -> List[Tuple[int, List[int]]]:
        """
        Flush all dirty cache lines.
        
        Returns:
            List of (address, data) tuples for all dirty lines
        """
        dirty_lines = []
        
        for set_idx, set_lines in enumerate(self.sets):
            for line_idx, line in enumerate(set_lines):
                if line.valid and line.dirty:
                    dirty_lines.append((line.address, line.data))
                    line.dirty = False
        
        return dirty_lines
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "cache_id": self.cache_id,
            "size": self.size,
            "line_size": self.line_size,
            "associativity": self.associativity,
            "num_sets": self.num_sets,
            "reads": self.reads,
            "writes": self.writes,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.get_hit_rate(),
        }
    
    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        
        Returns:
            Hit rate as percentage
        """
        total_accesses = self.reads + self.writes
        
        if total_accesses == 0:
            return 0.0
        
        return (self.hits / total_accesses) * 100


class MESICache(Cache):
    """Cache using the MESI coherence protocol."""
    
    def __init__(
        self,
        cache_id: int,
        size: int = 1024,
        line_size: int = 8,
        associativity: int = 4,
    ):
        """
        Initialize a MESI protocol cache.
        
        Args:
            cache_id: Unique ID for this cache
            size: Total cache size in words
            line_size: Number of words per cache line
            associativity: Number of ways in the cache
        """
        super().__init__(cache_id, size, line_size, associativity)
        
        # MESI state for each cache line
        self.line_states: Dict[Tuple[int, int], MESIState] = {}
        
        # Initialize all lines to INVALID
        for set_idx in range(self.num_sets):
            for line_idx in range(self.associativity):
                self.line_states[(set_idx, line_idx)] = MESIState.INVALID
        
        # Protocol statistics
        self.state_transitions = 0
        self.bus_transactions = 0
        self.invalidations_sent = 0
        self.invalidations_received = 0
    
    def get_state(self, address: int) -> MESIState:
        """
        Get the MESI state for a memory address.
        
        Args:
            address: Memory address
            
        Returns:
            MESI state for the address
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is None:
            return MESIState.INVALID
        
        return self.line_states[(set_idx, line_idx)]
    
    def set_state(self, address: int, state: MESIState) -> None:
        """
        Set the MESI state for a memory address.
        
        Args:
            address: Memory address
            state: New MESI state
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            old_state = self.line_states[(set_idx, line_idx)]
            self.line_states[(set_idx, line_idx)] = state
            
            if old_state != state:
                self.state_transitions += 1
    
    def read(self, address: int) -> Tuple[Optional[int], str]:
        """
        Read a value from the cache with MESI protocol.
        
        Args:
            address: Memory address to read
            
        Returns:
            Tuple of (value, bus_operation), where bus_operation is:
                "none" - No bus operation needed
                "read" - Need to read from memory
                "read_shared" - Need to read from memory or other caches
        """
        self.reads += 1
        self.access_time += 1
        
        # Find cache line for this address
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            # Cache hit
            self.hits += 1
            line.last_access = self.access_time
            offset = self._get_offset(address)
            
            # Check state
            state = self.line_states[(set_idx, line_idx)]
            
            if state in (MESIState.MODIFIED, MESIState.EXCLUSIVE, MESIState.SHARED):
                # Valid states for reading
                return line.read(offset), "none"
            else:
                # INVALID state, shouldn't happen for a cache hit
                return None, "read_shared"
        
        # Cache miss
        self.misses += 1
        self.bus_transactions += 1
        return None, "read_shared"
    
    def write(self, address: int, value: int) -> str:
        """
        Write a value to the cache with MESI protocol.
        
        Args:
            address: Memory address to write
            value: Value to write
            
        Returns:
            Bus operation:
                "none" - No bus operation needed
                "read_exclusive" - Need to read exclusively from memory
                "invalidate" - Need to invalidate other copies
                "write_back" - Need to write back modified data
        """
        self.writes += 1
        self.access_time += 1
        
        # Find cache line for this address
        line, set_idx, line_idx = self._find_line(address)
        
        if line is not None:
            # Cache hit
            self.hits += 1
            line.last_access = self.access_time
            offset = self._get_offset(address)
            
            # Check state
            state = self.line_states[(set_idx, line_idx)]
            
            if state == MESIState.MODIFIED:
                # Already modified, just update
                line.write(offset, value)
                return "none"
            
            elif state == MESIState.EXCLUSIVE:
                # Exclusive, can transition to modified without bus operation
                line.write(offset, value)
                self.line_states[(set_idx, line_idx)] = MESIState.MODIFIED
                self.state_transitions += 1
                return "none"
            
            elif state == MESIState.SHARED:
                # Shared, need to invalidate other copies
                line.write(offset, value)
                self.line_states[(set_idx, line_idx)] = MESIState.MODIFIED
                self.state_transitions += 1
                self.bus_transactions += 1
                self.invalidations_sent += 1
                return "invalidate"
            
            else:
                # INVALID state, shouldn't happen for a cache hit
                return "read_exclusive"
        
        # Cache miss
        self.misses += 1
        self.bus_transactions += 1
        return "read_exclusive"
    
    def handle_bus_read(self, address: int) -> Tuple[bool, Optional[List[int]]]:
        """
        Handle a bus read from another cache.
        
        Args:
            address: Memory address being read
            
        Returns:
            Tuple of (should_respond, data_to_share)
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is None:
            return False, None
        
        state = self.line_states[(set_idx, line_idx)]
        
        if state == MESIState.MODIFIED:
            # Modified data, transition to SHARED and provide data
            self.line_states[(set_idx, line_idx)] = MESIState.SHARED
            self.state_transitions += 1
            return True, line.data
        
        elif state == MESIState.EXCLUSIVE:
            # Exclusive data, transition to SHARED
            self.line_states[(set_idx, line_idx)] = MESIState.SHARED
            self.state_transitions += 1
            return True, line.data
        
        elif state == MESIState.SHARED:
            # Already shared, can provide data
            return True, line.data
        
        else:
            # INVALID, no response
            return False, None
    
    def handle_bus_read_exclusive(self, address: int) -> Tuple[bool, Optional[List[int]]]:
        """
        Handle a bus read exclusive from another cache.
        
        Args:
            address: Memory address being read
            
        Returns:
            Tuple of (should_respond, data_to_share)
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is None:
            return False, None
        
        state = self.line_states[(set_idx, line_idx)]
        
        if state == MESIState.MODIFIED:
            # Modified data, need to provide data and invalidate
            data = line.data.copy()
            line.invalidate()
            self.line_states[(set_idx, line_idx)] = MESIState.INVALID
            self.state_transitions += 1
            self.invalidations_received += 1
            return True, data
        
        elif state in (MESIState.EXCLUSIVE, MESIState.SHARED):
            # Need to invalidate
            line.invalidate()
            self.line_states[(set_idx, line_idx)] = MESIState.INVALID
            self.state_transitions += 1
            self.invalidations_received += 1
            return False, None
        
        else:
            # INVALID, no response
            return False, None
    
    def handle_bus_invalidate(self, address: int) -> bool:
        """
        Handle a bus invalidate from another cache.
        
        Args:
            address: Memory address being invalidated
            
        Returns:
            True if a line was invalidated, False otherwise
        """
        line, set_idx, line_idx = self._find_line(address)
        
        if line is None:
            return False
        
        state = self.line_states[(set_idx, line_idx)]
        
        if state in (MESIState.SHARED, MESIState.EXCLUSIVE):
            # Invalidate the line
            line.invalidate()
            self.line_states[(set_idx, line_idx)] = MESIState.INVALID
            self.state_transitions += 1
            self.invalidations_received += 1
            return True
        
        return False
    
    def allocate_line(
        self, address: int, data: List[int], state: MESIState
    ) -> Tuple[Optional[CacheLine], bool]:
        """
        Allocate a cache line with a specific MESI state.
        
        Args:
            address: Starting memory address
            data: Data for the cache line
            state: Initial MESI state
            
        Returns:
            Tuple of (evicted_line, was_dirty) if a line was evicted, or (None, False) otherwise
        """
        set_idx = self._get_set_index(address)
        victim_idx = self._select_victim(set_idx)
        
        # Check if victim needs writeback
        victim_state = self.line_states[(set_idx, victim_idx)]
        evicted, was_dirty = super().allocate_line(address, data)
        
        # Set the state for the new line
        self.line_states[(set_idx, victim_idx)] = state
        self.state_transitions += 1
        
        return evicted, was_dirty
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get MESI cache statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_statistics()
        
        # Add MESI-specific statistics
        state_counts = {state.name: 0 for state in MESIState}
        
        for (set_idx, line_idx), state in self.line_states.items():
            state_counts[state.name] += 1
        
        stats.update({
            "protocol": "MESI",
            "state_transitions": self.state_transitions,
            "bus_transactions": self.bus_transactions,
            "invalidations_sent": self.invalidations_sent,
            "invalidations_received": self.invalidations_received,
            "state_counts": state_counts,
        })
        
        return stats