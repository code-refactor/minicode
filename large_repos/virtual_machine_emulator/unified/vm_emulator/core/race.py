"""Race condition detection for the VM."""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Any


class RaceType(Enum):
    """Types of race conditions."""
    READ_WRITE = auto()      # Read-write race condition
    WRITE_WRITE = auto()     # Write-write race condition
    ATOMICITY_VIOLATION = auto()  # Atomicity violation
    ORDER_VIOLATION = auto()  # Order violation
    DEADLOCK = auto()        # Deadlock
    LIVELOCK = auto()        # Livelock
    STARVATION = auto()      # Starvation


class RaceDetector:
    """Race condition detector for the VM."""
    
    def __init__(self):
        """Initialize the race detector."""
        # Track memory accesses by address
        self.memory_accesses: Dict[int, List[Dict[str, Any]]] = {}
        
        # Track synchronization operations
        self.sync_operations: Dict[str, List[Dict[str, Any]]] = {}
        
        # Detected race conditions
        self.race_conditions: List[Dict[str, Any]] = []
        
        # Thread happens-before relationships
        self.happens_before: Dict[str, Set[str]] = {}
        
        # For tracking thread locks
        self.thread_locks: Dict[str, Set[int]] = {}
        
        # Atomicity violations (expected atomic regions)
        self.atomic_regions: Dict[str, List[Tuple[int, int]]] = {}
    
    def record_memory_access(
        self,
        address: int,
        access_type: str,
        thread_id: str,
        timestamp: int,
        processor_id: int,
        value: Optional[int] = None,
        lock_set: Optional[Set[int]] = None,
    ) -> None:
        """
        Record a memory access.
        
        Args:
            address: Memory address
            access_type: Type of access ("read" or "write")
            thread_id: ID of the thread
            timestamp: Global clock time
            processor_id: ID of the processor
            value: Value read or written (for writes)
            lock_set: Set of lock IDs held during access
        """
        # Initialize address entry if needed
        if address not in self.memory_accesses:
            self.memory_accesses[address] = []
        
        # Record the access
        access = {
            "address": address,
            "type": access_type,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "processor_id": processor_id,
            "value": value,
            "lock_set": lock_set or set(),
        }
        
        self.memory_accesses[address].append(access)
        
        # Check for race conditions
        self._check_races(access)
    
    def record_sync_operation(
        self,
        operation: str,
        thread_id: str,
        timestamp: int,
        sync_object_id: int,
        sync_type: str,
        processor_id: int,
    ) -> None:
        """
        Record a synchronization operation.
        
        Args:
            operation: Type of operation ("acquire", "release", etc.)
            thread_id: ID of the thread
            timestamp: Global clock time
            sync_object_id: ID of the synchronization object
            sync_type: Type of synchronization object ("lock", "semaphore", etc.)
            processor_id: ID of the processor
        """
        # Initialize thread entry if needed
        if thread_id not in self.sync_operations:
            self.sync_operations[thread_id] = []
        
        # Record the operation
        op = {
            "operation": operation,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "sync_object_id": sync_object_id,
            "sync_type": sync_type,
            "processor_id": processor_id,
        }
        
        self.sync_operations[thread_id].append(op)
        
        # Update thread lock set
        if sync_type == "lock":
            if thread_id not in self.thread_locks:
                self.thread_locks[thread_id] = set()
            
            if operation == "acquire":
                self.thread_locks[thread_id].add(sync_object_id)
            elif operation == "release":
                if sync_object_id in self.thread_locks[thread_id]:
                    self.thread_locks[thread_id].remove(sync_object_id)
        
        # Update happens-before relationships
        if operation == "release":
            # Create thread entry in happens-before if it doesn't exist
            if thread_id not in self.happens_before:
                self.happens_before[thread_id] = set()
                
            # Track this release operation for future reference
            release_op = {
                "thread_id": thread_id,
                "sync_object_id": sync_object_id,
                "sync_type": sync_type,
                "timestamp": timestamp
            }
            
            # Store in a structure for later matching with acquire operations
            if "releases" not in self.__dict__:
                self.__dict__["releases"] = []
            self.__dict__["releases"].append(release_op)
                
        elif operation == "acquire":
            # Check for any prior releases of this sync object
            if "releases" in self.__dict__:
                for release in self.__dict__["releases"]:
                    if (release["sync_object_id"] == sync_object_id and
                            release["sync_type"] == sync_type and
                            release["timestamp"] < timestamp and
                            release["thread_id"] != thread_id):
                        
                        # Establish happens-before relationship from releaser to acquirer
                        release_thread = release["thread_id"]
                        if release_thread not in self.happens_before:
                            self.happens_before[release_thread] = set()
                        self.happens_before[release_thread].add(thread_id)
                        
                        # Also establish the inverse relationship for easy lookup
                        if "happens_after" not in self.__dict__:
                            self.__dict__["happens_after"] = {}
                        if thread_id not in self.__dict__["happens_after"]:
                            self.__dict__["happens_after"][thread_id] = set()
                        self.__dict__["happens_after"][thread_id].add(release_thread)
    
    def define_atomic_region(
        self,
        thread_id: str,
        start_address: int,
        end_address: int,
    ) -> None:
        """
        Define an expected atomic region between memory accesses.
        
        Args:
            thread_id: ID of the thread
            start_address: Starting memory address
            end_address: Ending memory address
        """
        if thread_id not in self.atomic_regions:
            self.atomic_regions[thread_id] = []
        
        self.atomic_regions[thread_id].append((start_address, end_address))
    
    def _check_races(self, access: Dict[str, Any]) -> None:
        """
        Check for race conditions based on the new access.
        
        Args:
            access: The new memory access
        """
        address = access["address"]
        thread_id = access["thread_id"]
        access_type = access["type"]
        timestamp = access["timestamp"]
        lock_set = access.get("lock_set", set())
        
        # Get previous accesses to this address
        prev_accesses = self.memory_accesses[address][:-1]  # All except the last (current) access
        
        for prev in prev_accesses:
            prev_thread_id = prev["thread_id"]
            prev_type = prev["type"]
            prev_timestamp = prev["timestamp"]
            prev_lock_set = prev.get("lock_set", set())
            
            # Skip if same thread
            if thread_id == prev_thread_id:
                continue
            
            # Check happens-before relationship
            has_happens_before = False
            # Direct happens-before relation
            if prev_thread_id in self.happens_before and thread_id in self.happens_before[prev_thread_id]:
                has_happens_before = True
            # Reverse happens-before relation (happens-after)
            elif hasattr(self, "happens_after") and thread_id in self.__dict__["happens_after"] and prev_thread_id in self.__dict__["happens_after"][thread_id]:
                has_happens_before = True
            
            # Check if the accesses are protected by a common lock
            has_common_lock = bool(lock_set & prev_lock_set)
            
            # Detect race conditions
            race_found = False
            race_type = None
            race_description = None
            
            # Read-write race
            if (access_type == "read" and prev_type == "write") or (access_type == "write" and prev_type == "read"):
                if not has_happens_before and not has_common_lock:
                    race_type = RaceType.READ_WRITE
                    race_description = f"Read-write race condition at address {address:#x}"
                    race_found = True
            
            # Write-write race
            elif access_type == "write" and prev_type == "write":
                if not has_happens_before and not has_common_lock:
                    race_type = RaceType.WRITE_WRITE
                    race_description = f"Write-write race condition at address {address:#x}"
                    race_found = True
            
            # Check for atomicity violations in defined atomic regions
            if prev_thread_id in self.atomic_regions:
                for start_addr, end_addr in self.atomic_regions[prev_thread_id]:
                    if start_addr <= address <= end_addr:
                        # Another thread accessed an address within an atomic region
                        race_type = RaceType.ATOMICITY_VIOLATION
                        race_description = (
                            f"Atomicity violation: Thread {thread_id} accessed address "
                            f"{address:#x} which is within an atomic region of thread {prev_thread_id}"
                        )
                        race_found = True
                        break
            
            if race_found:
                # Record the race condition
                race = {
                    "type": race_type.name,
                    "description": race_description,
                    "address": address,
                    "thread1": prev_thread_id,
                    "thread2": thread_id,
                    "access1": prev,
                    "access2": access,
                    "has_happens_before": has_happens_before,
                    "has_common_lock": has_common_lock,
                    "detected_at": timestamp,
                }
                
                self.race_conditions.append(race)
    
    def check_deadlocks(self, waiting_graph: Dict[str, List[Tuple[str, int]]]) -> None:
        """
        Check for deadlocks in the waiting graph.
        
        Args:
            waiting_graph: Graph of thread_id -> list of (thread_id, lock_id)
        """
        # Find cycles in the waiting graph
        visited = set()
        path = []
        
        def dfs(thread_id):
            if thread_id in path:
                # Found a cycle - deadlock
                cycle_start = path.index(thread_id)
                deadlock_cycle = path[cycle_start:] + [thread_id]
                
                # Get lock information
                locks_involved = []
                for i in range(len(deadlock_cycle) - 1):
                    thread1 = deadlock_cycle[i]
                    thread2 = deadlock_cycle[i + 1]
                    
                    # Find the lock that thread1 is waiting for from thread2
                    for waiting_thread, lock_id in waiting_graph.get(thread1, []):
                        if waiting_thread == thread2:
                            locks_involved.append(lock_id)
                            break
                
                # Record the deadlock
                self.race_conditions.append({
                    "type": RaceType.DEADLOCK.name,
                    "description": f"Deadlock detected involving threads {deadlock_cycle}",
                    "threads": deadlock_cycle,
                    "locks": locks_involved,
                    "detected_at": 0,  # We don't have a timestamp here
                })
                
                return True
            
            if thread_id in visited:
                return False
            
            visited.add(thread_id)
            path.append(thread_id)
            
            for waiting_thread, _ in waiting_graph.get(thread_id, []):
                if dfs(waiting_thread):
                    return True
            
            path.pop()
            return False
        
        # Start DFS from each thread
        for thread_id in waiting_graph:
            if thread_id not in visited:
                if dfs(thread_id):
                    break
    
    def check_order_violations(self) -> None:
        """Check for order violations between threads."""
        # Get all memory addresses that have been accessed
        for address, accesses in self.memory_accesses.items():
            # Get all threads that have accessed this address
            thread_accesses: Dict[str, List[Dict[str, Any]]] = {}
            
            for access in accesses:
                thread_id = access["thread_id"]
                if thread_id not in thread_accesses:
                    thread_accesses[thread_id] = []
                thread_accesses[thread_id].append(access)
            
            # Check for patterns indicating order violations
            for thread1 in thread_accesses:
                for thread2 in thread_accesses:
                    if thread1 == thread2:
                        continue
                    
                    # Sort accesses by timestamp
                    t1_accesses = sorted(thread_accesses[thread1], key=lambda a: a["timestamp"])
                    t2_accesses = sorted(thread_accesses[thread2], key=lambda a: a["timestamp"])
                    
                    # Look for patterns like init-read-write instead of init-write-read
                    # This is a simplified example - in practice you'd look for specific patterns
                    if (len(t1_accesses) >= 1 and len(t2_accesses) >= 2 and
                            t1_accesses[0]["type"] == "write" and  # Init
                            t2_accesses[0]["type"] == "read" and   # Read
                            t2_accesses[1]["type"] == "write" and  # Write
                            t2_accesses[0]["timestamp"] < t1_accesses[0]["timestamp"] < t2_accesses[1]["timestamp"]):
                        
                        # This is a potential order violation
                        self.race_conditions.append({
                            "type": RaceType.ORDER_VIOLATION.name,
                            "description": (
                                f"Order violation at address {address:#x}: "
                                f"Thread {thread2} read uninitialized data before thread {thread1} wrote it"
                            ),
                            "address": address,
                            "thread1": thread1,
                            "thread2": thread2,
                            "accesses": t2_accesses[0:2] + [t1_accesses[0]],
                            "detected_at": t2_accesses[1]["timestamp"],
                        })
    
    def check_livelock(self, thread_stats: Dict[str, Dict[str, Any]]) -> None:
        """
        Check for livelocks.
        
        Args:
            thread_stats: Dictionary of thread statistics
        """
        # Look for threads that are active but not making progress
        # This is a simplified implementation
        suspicious_threads = []
        
        for thread_id, stats in thread_stats.items():
            # Check if the thread is active but seemingly not progressing
            if stats.get("state") != "TERMINATED" and stats.get("progress_rate", 0) < 0.1:
                suspicious_threads.append(thread_id)
        
        if len(suspicious_threads) >= 2:
            # Potential livelock
            self.race_conditions.append({
                "type": RaceType.LIVELOCK.name,
                "description": f"Potential livelock involving threads {suspicious_threads}",
                "threads": suspicious_threads,
                "detected_at": 0,  # We don't have a timestamp here
            })
    
    def check_starvation(self, thread_stats: Dict[str, Dict[str, Any]], threshold: int = 100) -> None:
        """
        Check for thread starvation.
        
        Args:
            thread_stats: Dictionary of thread statistics
            threshold: Wait time threshold for detecting starvation
        """
        # Look for threads that are waiting for a long time
        starved_threads = []
        
        for thread_id, stats in thread_stats.items():
            # Check if the thread is waiting for a long time
            if stats.get("state") == "WAITING" and stats.get("wait_time", 0) > threshold:
                starved_threads.append((thread_id, stats.get("wait_time", 0)))
        
        for thread_id, wait_time in starved_threads:
            self.race_conditions.append({
                "type": RaceType.STARVATION.name,
                "description": f"Thread {thread_id} might be starving (waiting for {wait_time} cycles)",
                "thread_id": thread_id,
                "wait_time": wait_time,
                "detected_at": 0,  # We don't have a timestamp here
            })
    
    def get_race_conditions(
        self,
        race_type: Optional[RaceType] = None,
        address: Optional[int] = None,
        thread_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get detected race conditions, optionally filtered.
        
        Args:
            race_type: Filter by race type
            address: Filter by memory address
            thread_id: Filter by thread ID
            
        Returns:
            List of race conditions
        """
        result = self.race_conditions
        
        if race_type:
            result = [r for r in result if r["type"] == race_type.name]
        
        if address is not None:
            result = [r for r in result if r.get("address") == address]
        
        if thread_id:
            result = [
                r for r in result
                if r.get("thread1") == thread_id or r.get("thread2") == thread_id
                or r.get("thread_id") == thread_id
                or (r.get("threads") and thread_id in r.get("threads"))
            ]
        
        return result
    
    def get_memory_access_history(
        self,
        address: Optional[int] = None,
        thread_id: Optional[str] = None,
        access_type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get memory access history, optionally filtered.
        
        Args:
            address: Filter by memory address
            thread_id: Filter by thread ID
            access_type: Filter by access type ("read" or "write")
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of memory accesses
        """
        # Collect all accesses
        all_accesses = []
        for addr, accesses in self.memory_accesses.items():
            if address is None or addr == address:
                all_accesses.extend(accesses)
        
        # Apply filters
        result = all_accesses
        
        if thread_id:
            result = [a for a in result if a["thread_id"] == thread_id]
        
        if access_type:
            result = [a for a in result if a["type"] == access_type]
        
        if start_time is not None:
            result = [a for a in result if a["timestamp"] >= start_time]
        
        if end_time is not None:
            result = [a for a in result if a["timestamp"] <= end_time]
        
        # Sort by timestamp
        result.sort(key=lambda a: a["timestamp"])
        
        return result
    
    def get_thread_happens_before_graph(self) -> Dict[str, Set[str]]:
        """
        Get the happens-before relationship graph.
        
        Returns:
            Dictionary of thread_id -> set of thread_ids that must run after
        """
        return self.happens_before
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get race detection statistics.
        
        Returns:
            Dictionary of statistics
        """
        # Count race conditions by type
        race_counts = {}
        for race in self.race_conditions:
            race_type = race["type"]
            race_counts[race_type] = race_counts.get(race_type, 0) + 1
        
        # Count memory accesses
        read_count = 0
        write_count = 0
        for _, accesses in self.memory_accesses.items():
            for access in accesses:
                if access["type"] == "read":
                    read_count += 1
                elif access["type"] == "write":
                    write_count += 1
        
        return {
            "total_races": len(self.race_conditions),
            "race_counts": race_counts,
            "memory_addresses_monitored": len(self.memory_accesses),
            "total_memory_accesses": read_count + write_count,
            "read_accesses": read_count,
            "write_accesses": write_count,
            "threads_monitored": len(self.sync_operations),
        }
    
    def reset(self) -> None:
        """Reset the race detector."""
        self.memory_accesses = {}
        self.sync_operations = {}
        self.race_conditions = []
        self.happens_before = {}
        self.thread_locks = {}
        self.atomic_regions = {}