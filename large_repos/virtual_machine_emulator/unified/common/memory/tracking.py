"""Memory access tracking and analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from ..core.memory_base import MemoryAccess


@dataclass
class AccessPattern:
    """Memory access pattern information."""
    
    address: int
    read_count: int = 0
    write_count: int = 0
    execute_count: int = 0
    last_read_cycle: Optional[int] = None
    last_write_cycle: Optional[int] = None
    readers: Set[int] = field(default_factory=set)  # Set of thread/processor IDs
    writers: Set[int] = field(default_factory=set)
    
    def is_shared(self) -> bool:
        """Check if memory is accessed by multiple entities."""
        return len(self.readers.union(self.writers)) > 1
    
    def is_read_only(self) -> bool:
        """Check if memory is only read."""
        return self.read_count > 0 and self.write_count == 0
    
    def is_write_only(self) -> bool:
        """Check if memory is only written."""
        return self.write_count > 0 and self.read_count == 0


class MemoryAccessTracker:
    """Track and analyze memory accesses."""
    
    def __init__(self):
        """Initialize tracker."""
        self.accesses: List[MemoryAccess] = []
        self.patterns: Dict[int, AccessPattern] = {}
        self.race_conditions: List[Dict] = []
        self.enabled = True
        
    def track_access(self, access: MemoryAccess) -> None:
        """Track a memory access."""
        if not self.enabled:
            return
        
        self.accesses.append(access)
        
        # Update access pattern
        if access.address not in self.patterns:
            self.patterns[access.address] = AccessPattern(address=access.address)
        
        pattern = self.patterns[access.address]
        
        if access.access_type == 'read':
            pattern.read_count += 1
            pattern.last_read_cycle = access.cycle
            if access.processor_id is not None:
                pattern.readers.add(access.processor_id)
        elif access.access_type == 'write':
            pattern.write_count += 1
            pattern.last_write_cycle = access.cycle
            if access.processor_id is not None:
                pattern.writers.add(access.processor_id)
        elif access.access_type == 'execute':
            pattern.execute_count += 1
    
    def detect_race_conditions(self, window_size: int = 10) -> List[Dict]:
        """Detect potential race conditions in access patterns."""
        races = []
        
        # Group accesses by address
        by_address = defaultdict(list)
        for access in self.accesses:
            by_address[access.address].append(access)
        
        # Check each address for races
        for address, addr_accesses in by_address.items():
            # Sort by cycle
            addr_accesses.sort(key=lambda a: a.cycle)
            
            # Look for write-write or read-write races within window
            for i, access1 in enumerate(addr_accesses):
                for access2 in addr_accesses[i+1:]:
                    # Check if within window
                    if access2.cycle - access1.cycle > window_size:
                        break
                    
                    # Check for race conditions
                    is_race = False
                    race_type = None
                    
                    # Different processors/threads
                    if access1.processor_id != access2.processor_id:
                        if access1.access_type == 'write' and access2.access_type == 'write':
                            is_race = True
                            race_type = 'write-write'
                        elif (access1.access_type == 'write' and access2.access_type == 'read') or \
                             (access1.access_type == 'read' and access2.access_type == 'write'):
                            is_race = True
                            race_type = 'read-write'
                    
                    if is_race:
                        race = {
                            'address': address,
                            'type': race_type,
                            'access1': {
                                'cycle': access1.cycle,
                                'type': access1.access_type,
                                'processor': access1.processor_id
                            },
                            'access2': {
                                'cycle': access2.cycle,
                                'type': access2.access_type,
                                'processor': access2.processor_id
                            }
                        }
                        races.append(race)
                        self.race_conditions.append(race)
        
        return races
    
    def get_hot_addresses(self, top_n: int = 10) -> List[Tuple[int, int]]:
        """Get most frequently accessed addresses."""
        access_counts = {}
        for pattern in self.patterns.values():
            total = pattern.read_count + pattern.write_count + pattern.execute_count
            access_counts[pattern.address] = total
        
        sorted_addrs = sorted(access_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_addrs[:top_n]
    
    def get_shared_addresses(self) -> List[int]:
        """Get addresses accessed by multiple processors/threads."""
        return [addr for addr, pattern in self.patterns.items() if pattern.is_shared()]
    
    def get_statistics(self) -> Dict:
        """Get access statistics."""
        total_reads = sum(p.read_count for p in self.patterns.values())
        total_writes = sum(p.write_count for p in self.patterns.values())
        total_execs = sum(p.execute_count for p in self.patterns.values())
        
        return {
            'total_accesses': len(self.accesses),
            'unique_addresses': len(self.patterns),
            'reads': total_reads,
            'writes': total_writes,
            'executes': total_execs,
            'shared_addresses': len(self.get_shared_addresses()),
            'race_conditions': len(self.race_conditions)
        }
    
    def clear(self) -> None:
        """Clear tracking data."""
        self.accesses.clear()
        self.patterns.clear()
        self.race_conditions.clear()
    
    def enable(self) -> None:
        """Enable tracking."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable tracking."""
        self.enabled = False