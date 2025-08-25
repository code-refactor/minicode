"""Memory access pattern analysis for the VM."""

import math
from collections import Counter, defaultdict
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Any, Union


class AccessPattern(Enum):
    """Types of memory access patterns."""
    SEQUENTIAL = auto()       # Sequential access pattern
    STRIDED = auto()          # Strided access pattern
    RANDOM = auto()           # Random access pattern
    REPEATED = auto()         # Repeated access pattern
    PRODUCER_CONSUMER = auto()  # Producer-consumer pattern
    MIGRATORY = auto()        # Migratory access pattern
    FALSE_SHARING = auto()    # False sharing pattern
    TRUE_SHARING = auto()     # True sharing pattern


class AccessDirection(Enum):
    """Direction of sequential or strided accesses."""
    ASCENDING = auto()  # Addresses increasing
    DESCENDING = auto()  # Addresses decreasing
    MIXED = auto()      # Mixed directions


class SharingPattern(Enum):
    """Types of data sharing patterns between threads."""
    NO_SHARING = auto()      # No sharing detected
    READ_ONLY = auto()       # Multiple threads read, none write
    PRODUCER_CONSUMER = auto() # One thread writes, another reads
    MIGRATORY = auto()       # Ownership passes between threads
    READ_WRITE_SHARING = auto() # Multiple threads read and write
    WRITE_WRITE_SHARING = auto() # Multiple threads write


class MemoryPatternAnalyzer:
    """
    Analyzes memory access patterns.
    
    Detects patterns such as sequential access, strided access,
    false sharing, and various sharing patterns between threads.
    """
    
    def __init__(self, cache_line_size: int = 8):
        """
        Initialize the memory pattern analyzer.
        
        Args:
            cache_line_size: Size of a cache line in words
        """
        self.cache_line_size = cache_line_size
        
        # Memory accesses by thread
        self.thread_accesses: Dict[str, List[Dict[str, Any]]] = {}
        
        # Memory accesses by address
        self.address_accesses: Dict[int, List[Dict[str, Any]]] = {}
        
        # Cache line accesses
        self.line_accesses: Dict[int, List[Dict[str, Any]]] = {}
        
        # Thread access history for detecting sequential/strided patterns
        self.thread_access_history: Dict[str, List[int]] = {}
        
        # For processing status
        self.is_processed = False
        self.pattern_results: Dict[str, Dict[str, Any]] = {}
    
    def record_access(
        self,
        address: int,
        thread_id: str,
        timestamp: int,
        access_type: str,
        processor_id: Optional[int] = None,
        value: Optional[int] = None,
    ) -> None:
        """
        Record a memory access.
        
        Args:
            address: Memory address
            thread_id: ID of the thread performing the access
            timestamp: Time of the access
            access_type: Type of access ("read" or "write")
            processor_id: ID of the processor
            value: Value read or written
        """
        # Create the access record
        access = {
            "address": address,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "type": access_type,
            "processor_id": processor_id,
            "value": value,
            "cache_line": address // self.cache_line_size,
        }
        
        # Add to thread accesses
        if thread_id not in self.thread_accesses:
            self.thread_accesses[thread_id] = []
        self.thread_accesses[thread_id].append(access)
        
        # Add to address accesses
        if address not in self.address_accesses:
            self.address_accesses[address] = []
        self.address_accesses[address].append(access)
        
        # Add to cache line accesses
        cache_line = address // self.cache_line_size
        if cache_line not in self.line_accesses:
            self.line_accesses[cache_line] = []
        self.line_accesses[cache_line].append(access)
        
        # Add to thread access history
        if thread_id not in self.thread_access_history:
            self.thread_access_history[thread_id] = []
        self.thread_access_history[thread_id].append(address)
        
        # Reset processed flag
        self.is_processed = False
    
    def process(self) -> None:
        """Process all recorded accesses to detect patterns."""
        if self.is_processed:
            return
        
        # Process patterns for each thread
        for thread_id in self.thread_accesses:
            self.pattern_results[thread_id] = self._analyze_thread_patterns(thread_id)
        
        # Process patterns for each address
        for address in self.address_accesses:
            if address not in self.pattern_results:
                self.pattern_results[f"addr_{address}"] = self._analyze_address_patterns(address)
        
        # Process patterns for each cache line
        for line in self.line_accesses:
            self.pattern_results[f"line_{line}"] = self._analyze_line_patterns(line)
        
        # Process global patterns
        self.pattern_results["global"] = self._analyze_global_patterns()
        
        self.is_processed = True
    
    def _analyze_thread_patterns(self, thread_id: str) -> Dict[str, Any]:
        """
        Analyze access patterns for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Dictionary of detected patterns
        """
        accesses = self.thread_accesses[thread_id]
        history = self.thread_access_history[thread_id]
        
        # Not enough accesses for meaningful analysis
        if len(accesses) < 5:
            return {
                "thread_id": thread_id,
                "access_count": len(accesses),
                "patterns": [],
                "insufficient_data": True,
            }
        
        patterns = []
        pattern_details = {}
        
        # Check for sequential access
        seq_result = self._detect_sequential_pattern(history)
        if seq_result["is_sequential"]:
            patterns.append(AccessPattern.SEQUENTIAL)
            pattern_details["sequential"] = seq_result
        
        # Check for strided access
        stride_result = self._detect_strided_pattern(history)
        if stride_result["is_strided"]:
            patterns.append(AccessPattern.STRIDED)
            pattern_details["strided"] = stride_result
        
        # Check for repeated access
        repeat_result = self._detect_repeated_pattern(history)
        if repeat_result["is_repeated"]:
            patterns.append(AccessPattern.REPEATED)
            pattern_details["repeated"] = repeat_result
        
        # Check for random access if no other patterns detected
        if not patterns:
            patterns.append(AccessPattern.RANDOM)
            pattern_details["random"] = {"confidence": 0.8}
        
        # Analyze read/write ratio
        reads = sum(1 for a in accesses if a["type"] == "read")
        writes = sum(1 for a in accesses if a["type"] == "write")
        
        return {
            "thread_id": thread_id,
            "access_count": len(accesses),
            "read_count": reads,
            "write_count": writes,
            "read_ratio": reads / len(accesses) if accesses else 0,
            "write_ratio": writes / len(accesses) if accesses else 0,
            "patterns": [p.name for p in patterns],
            "pattern_details": pattern_details,
            "unique_addresses": len(set(a["address"] for a in accesses)),
            "unique_lines": len(set(a["cache_line"] for a in accesses)),
        }
    
    def _analyze_address_patterns(self, address: int) -> Dict[str, Any]:
        """
        Analyze access patterns for a specific address.
        
        Args:
            address: Memory address
            
        Returns:
            Dictionary of detected patterns
        """
        accesses = self.address_accesses[address]
        
        # Count accesses by thread
        thread_counts = Counter(a["thread_id"] for a in accesses)
        threads = list(thread_counts.keys())
        
        # Count read/write operations
        reads = sum(1 for a in accesses if a["type"] == "read")
        writes = sum(1 for a in accesses if a["type"] == "write")
        
        # Detect sharing patterns
        sharing_pattern = self._detect_sharing_pattern(accesses)
        
        return {
            "address": address,
            "access_count": len(accesses),
            "thread_count": len(thread_counts),
            "threads": threads,
            "read_count": reads,
            "write_count": writes,
            "sharing_pattern": sharing_pattern.name,
        }
    
    def _analyze_line_patterns(self, line: int) -> Dict[str, Any]:
        """
        Analyze access patterns for a specific cache line.
        
        Args:
            line: Cache line number
            
        Returns:
            Dictionary of detected patterns
        """
        accesses = self.line_accesses[line]
        
        # Count accesses by thread and address
        thread_counts = Counter(a["thread_id"] for a in accesses)
        address_counts = Counter(a["address"] for a in accesses)
        
        # Check for false sharing
        false_sharing = self._detect_false_sharing(accesses)
        
        # Count read/write operations
        reads = sum(1 for a in accesses if a["type"] == "read")
        writes = sum(1 for a in accesses if a["type"] == "write")
        
        # Analyze temporal locality
        temporal_locality = self._analyze_temporal_locality(accesses)
        
        return {
            "line": line,
            "access_count": len(accesses),
            "thread_count": len(thread_counts),
            "address_count": len(address_counts),
            "read_count": reads,
            "write_count": writes,
            "false_sharing": false_sharing,
            "temporal_locality": temporal_locality,
        }
    
    def _analyze_global_patterns(self) -> Dict[str, Any]:
        """
        Analyze global memory access patterns.
        
        Returns:
            Dictionary of global patterns
        """
        # Count total accesses
        total_accesses = sum(len(accesses) for accesses in self.thread_accesses.values())
        
        # Count unique addresses and cache lines
        unique_addresses = len(self.address_accesses)
        unique_lines = len(self.line_accesses)
        
        # Calculate address density (accesses per unique address)
        address_density = total_accesses / unique_addresses if unique_addresses > 0 else 0
        
        # Calculate line density (accesses per unique cache line)
        line_density = total_accesses / unique_lines if unique_lines > 0 else 0
        
        # Count read/write operations
        reads = 0
        writes = 0
        for thread_accesses in self.thread_accesses.values():
            reads += sum(1 for a in thread_accesses if a["type"] == "read")
            writes += sum(1 for a in thread_accesses if a["type"] == "write")
        
        # Detect spatial locality
        spatial_locality = self._analyze_global_spatial_locality()
        
        # Find hot spots (most frequently accessed addresses)
        hot_spots = self._find_hot_spots()
        
        return {
            "total_accesses": total_accesses,
            "unique_addresses": unique_addresses,
            "unique_lines": unique_lines,
            "thread_count": len(self.thread_accesses),
            "address_density": address_density,
            "line_density": line_density,
            "read_count": reads,
            "write_count": writes,
            "read_ratio": reads / total_accesses if total_accesses > 0 else 0,
            "write_ratio": writes / total_accesses if total_accesses > 0 else 0,
            "spatial_locality": spatial_locality,
            "hot_spots": hot_spots,
        }
    
    def _detect_sequential_pattern(self, addresses: List[int]) -> Dict[str, Any]:
        """
        Detect sequential access pattern.
        
        Args:
            addresses: List of accessed addresses
            
        Returns:
            Dictionary with sequential pattern details
        """
        if len(addresses) < 5:
            return {"is_sequential": False}
        
        # Check for sequential access (addresses increasing or decreasing by 1)
        sequential_count = 0
        direction = None
        
        for i in range(1, len(addresses)):
            diff = addresses[i] - addresses[i-1]
            
            if diff == 1:
                if direction is None:
                    direction = AccessDirection.ASCENDING
                    sequential_count = 1
                elif direction == AccessDirection.ASCENDING:
                    sequential_count += 1
                else:
                    direction = AccessDirection.MIXED
            elif diff == -1:
                if direction is None:
                    direction = AccessDirection.DESCENDING
                    sequential_count = 1
                elif direction == AccessDirection.DESCENDING:
                    sequential_count += 1
                else:
                    direction = AccessDirection.MIXED
            else:
                # Reset counter for non-sequential accesses
                sequential_count = 0
                
                if direction is not None and direction != AccessDirection.MIXED:
                    direction = AccessDirection.MIXED
        
        # Calculate what percentage of accesses are sequential
        seq_ratio = sequential_count / (len(addresses) - 1)
        
        is_sequential = seq_ratio >= 0.7  # At least 70% sequential
        
        return {
            "is_sequential": is_sequential,
            "direction": direction.name if direction else None,
            "sequential_ratio": seq_ratio,
            "confidence": seq_ratio,
        }
    
    def _detect_strided_pattern(self, addresses: List[int]) -> Dict[str, Any]:
        """
        Detect strided access pattern.
        
        Args:
            addresses: List of accessed addresses
            
        Returns:
            Dictionary with strided pattern details
        """
        if len(addresses) < 5:
            return {"is_strided": False}
        
        # Count strides (differences between consecutive addresses)
        strides = [addresses[i] - addresses[i-1] for i in range(1, len(addresses))]
        stride_counts = Counter(strides)
        
        # Remove sequential accesses (stride 1 or -1)
        if 1 in stride_counts:
            del stride_counts[1]
        if -1 in stride_counts:
            del stride_counts[-1]
        
        # If no strides left, not a strided pattern
        if not stride_counts:
            return {"is_strided": False}
        
        # Find the most common stride
        most_common_stride, most_common_count = stride_counts.most_common(1)[0]
        
        # Calculate what percentage of accesses have this stride
        stride_ratio = most_common_count / (len(addresses) - 1)
        
        is_strided = stride_ratio >= 0.5  # At least 50% strided
        
        return {
            "is_strided": is_strided,
            "stride": most_common_stride,
            "stride_ratio": stride_ratio,
            "confidence": stride_ratio,
        }
    
    def _detect_repeated_pattern(self, addresses: List[int]) -> Dict[str, Any]:
        """
        Detect repeated access pattern.
        
        Args:
            addresses: List of accessed addresses
            
        Returns:
            Dictionary with repeated pattern details
        """
        if len(addresses) < 5:
            return {"is_repeated": False}
        
        # Count occurrences of each address
        addr_counts = Counter(addresses)
        
        # Find the most frequently accessed address
        most_common_addr, most_common_count = addr_counts.most_common(1)[0]
        
        # Calculate what percentage of accesses are to this address
        repeat_ratio = most_common_count / len(addresses)
        
        # Calculate average repetition (accesses per unique address)
        avg_repetition = len(addresses) / len(addr_counts)
        
        is_repeated = avg_repetition >= 2.0  # Average at least 2 accesses per address
        
        return {
            "is_repeated": is_repeated,
            "most_common_address": most_common_addr,
            "most_common_count": most_common_count,
            "repeat_ratio": repeat_ratio,
            "avg_repetition": avg_repetition,
            "confidence": min(1.0, (avg_repetition - 1) / 4),  # Scale confidence based on repetition
        }
    
    def _detect_sharing_pattern(self, accesses: List[Dict[str, Any]]) -> SharingPattern:
        """
        Detect sharing pattern for a set of accesses.
        
        Args:
            accesses: List of memory accesses
            
        Returns:
            Detected sharing pattern
        """
        # Count threads doing reads and writes
        threads = set(a["thread_id"] for a in accesses)
        
        if len(threads) == 1:
            # Only one thread, no sharing
            return SharingPattern.NO_SHARING
        
        # Check which threads read and write
        reading_threads = set(a["thread_id"] for a in accesses if a["type"] == "read")
        writing_threads = set(a["thread_id"] for a in accesses if a["type"] == "write")
        
        if not writing_threads:
            # Multiple threads reading, none writing
            return SharingPattern.READ_ONLY
        
        if len(writing_threads) == 1 and reading_threads - writing_threads:
            # One thread writes, others read
            # Check if it's a producer-consumer pattern
            thread_accesses = defaultdict(list)
            for access in accesses:
                thread_accesses[access["thread_id"]].append(access)
            
            # Get writer thread
            writer_thread = list(writing_threads)[0]
            write_timestamps = [a["timestamp"] for a in thread_accesses[writer_thread] if a["type"] == "write"]
            
            # Check if reads happen after writes
            is_producer_consumer = True
            for thread in reading_threads - writing_threads:
                read_timestamps = [a["timestamp"] for a in thread_accesses[thread] if a["type"] == "read"]
                if not read_timestamps:
                    continue
                
                # Check if reads happen after writes
                for read_ts in read_timestamps:
                    if not any(write_ts < read_ts for write_ts in write_timestamps):
                        is_producer_consumer = False
                        break
            
            if is_producer_consumer:
                return SharingPattern.PRODUCER_CONSUMER
        
        # Check for migratory pattern (exclusive access changing between threads)
        if self._detect_migratory_pattern(accesses):
            return SharingPattern.MIGRATORY
        
        # Multiple threads writing
        if len(writing_threads) > 1:
            return SharingPattern.WRITE_WRITE_SHARING
        
        # Default case: read-write sharing
        return SharingPattern.READ_WRITE_SHARING
    
    def _detect_migratory_pattern(self, accesses: List[Dict[str, Any]]) -> bool:
        """
        Detect migratory access pattern.
        
        Args:
            accesses: List of memory accesses
            
        Returns:
            True if migratory pattern detected
        """
        # Sort accesses by timestamp
        sorted_accesses = sorted(accesses, key=lambda a: a["timestamp"])
        
        current_owner = None
        ownership_changes = 0
        
        for access in sorted_accesses:
            thread_id = access["thread_id"]
            
            if access["type"] == "write":
                if current_owner is not None and current_owner != thread_id:
                    # Ownership changed
                    ownership_changes += 1
                current_owner = thread_id
        
        # If ownership changed multiple times, it's a migratory pattern
        return ownership_changes >= 2
    
    def _detect_false_sharing(self, accesses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect false sharing in a cache line.
        
        Args:
            accesses: List of cache line accesses
            
        Returns:
            Dictionary with false sharing details
        """
        # Group accesses by address
        address_accesses = defaultdict(list)
        for access in accesses:
            address_accesses[access["address"]].append(access)
        
        # If only one address in the cache line, no false sharing
        if len(address_accesses) <= 1:
            return {
                "detected": False,
                "confidence": 0.0,
            }
        
        # Check each address for exclusive thread access
        address_threads = {}
        for addr, addr_accesses in address_accesses.items():
            threads = set(a["thread_id"] for a in addr_accesses)
            if len(threads) == 1:
                # This address is accessed by only one thread
                address_threads[addr] = list(threads)[0]
        
        # False sharing occurs when different threads access different addresses in the same cache line
        distinct_threads = set(address_threads.values())
        
        if len(distinct_threads) > 1:
            # Calculate how many addresses have exclusive access
            exclusive_ratio = len(address_threads) / len(address_accesses)
            
            # Higher confidence if more addresses have exclusive access
            confidence = exclusive_ratio * 0.8
            
            # Higher confidence if there are write accesses
            write_count = sum(1 for a in accesses if a["type"] == "write")
            if write_count > 0:
                confidence = min(1.0, confidence + 0.2)
            
            return {
                "detected": True,
                "exclusive_addresses": list(address_threads.keys()),
                "exclusive_threads": list(address_threads.values()),
                "confidence": confidence,
            }
        
        return {
            "detected": False,
            "confidence": 0.0,
        }
    
    def _analyze_temporal_locality(self, accesses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze temporal locality for a set of accesses.
        
        Args:
            accesses: List of memory accesses
            
        Returns:
            Dictionary with temporal locality metrics
        """
        if len(accesses) < 3:
            return {"score": 0.0, "confidence": 0.0}
        
        # Sort accesses by timestamp
        sorted_accesses = sorted(accesses, key=lambda a: a["timestamp"])
        
        # Track the reuse distance (in terms of accesses) for each address
        last_access = {}
        reuse_distances = []
        
        for i, access in enumerate(sorted_accesses):
            addr = access["address"]
            
            if addr in last_access:
                # Calculate reuse distance
                reuse_distance = i - last_access[addr]
                reuse_distances.append(reuse_distance)
            
            last_access[addr] = i
        
        if not reuse_distances:
            return {"score": 0.0, "confidence": 0.0}
        
        # Calculate average reuse distance
        avg_reuse_distance = sum(reuse_distances) / len(reuse_distances)
        
        # Calculate temporal locality score (lower distance = higher locality)
        max_distance = len(sorted_accesses)
        temporal_score = 1.0 - (avg_reuse_distance / max_distance)
        
        return {
            "score": temporal_score,
            "avg_reuse_distance": avg_reuse_distance,
            "confidence": 0.8 if len(reuse_distances) >= 5 else 0.5,
        }
    
    def _analyze_global_spatial_locality(self) -> Dict[str, Any]:
        """
        Analyze global spatial locality.
        
        Returns:
            Dictionary with spatial locality metrics
        """
        # Count accesses to each cache line
        line_access_counts = Counter()
        for line, accesses in self.line_accesses.items():
            line_access_counts[line] = len(accesses)
        
        if not line_access_counts:
            return {"score": 0.0, "confidence": 0.0}
        
        # Calculate average accesses per line
        avg_accesses_per_line = sum(line_access_counts.values()) / len(line_access_counts)
        
        # Calculate standard deviation of accesses per line
        variance = sum((count - avg_accesses_per_line) ** 2 for count in line_access_counts.values()) / len(line_access_counts)
        std_dev = math.sqrt(variance)
        
        # Calculate coefficient of variation (higher = more uneven distribution)
        cv = std_dev / avg_accesses_per_line if avg_accesses_per_line > 0 else 0
        
        # Calculate spatial locality score
        # Higher score indicates better spatial locality (more clustered accesses)
        spatial_score = min(1.0, 1.0 - (1.0 / (1.0 + cv)))
        
        return {
            "score": spatial_score,
            "avg_accesses_per_line": avg_accesses_per_line,
            "std_dev": std_dev,
            "confidence": 0.8 if len(line_access_counts) >= 5 else 0.5,
        }
    
    def _find_hot_spots(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Find memory access hot spots.
        
        Args:
            top_n: Number of hot spots to return
            
        Returns:
            List of hot spot dictionaries
        """
        # Count accesses to each address
        addr_counts = Counter()
        for addr, accesses in self.address_accesses.items():
            addr_counts[addr] = len(accesses)
        
        # Find the most frequently accessed addresses
        hot_spots = []
        for addr, count in addr_counts.most_common(top_n):
            hot_spots.append({
                "address": addr,
                "access_count": count,
                "cache_line": addr // self.cache_line_size,
            })
        
        return hot_spots
    
    def get_thread_patterns(self, thread_id: str) -> Dict[str, Any]:
        """
        Get memory access patterns for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Dictionary of thread access patterns
        """
        self.process()
        
        if thread_id not in self.pattern_results:
            return {"error": "Thread not found"}
        
        return self.pattern_results[thread_id]
    
    def get_all_thread_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Get memory access patterns for all threads.
        
        Returns:
            Dictionary of thread_id -> access patterns
        """
        self.process()
        
        return {tid: self.pattern_results[tid] for tid in self.thread_accesses}
    
    def get_address_patterns(self, address: int) -> Dict[str, Any]:
        """
        Get memory access patterns for a specific address.
        
        Args:
            address: Memory address
            
        Returns:
            Dictionary of address access patterns
        """
        self.process()
        
        addr_key = f"addr_{address}"
        if addr_key not in self.pattern_results:
            return {"error": "Address not found"}
        
        return self.pattern_results[addr_key]
    
    def get_line_patterns(self, line: int) -> Dict[str, Any]:
        """
        Get memory access patterns for a specific cache line.
        
        Args:
            line: Cache line number
            
        Returns:
            Dictionary of cache line access patterns
        """
        self.process()
        
        line_key = f"line_{line}"
        if line_key not in self.pattern_results:
            return {"error": "Cache line not found"}
        
        return self.pattern_results[line_key]
    
    def get_global_patterns(self) -> Dict[str, Any]:
        """
        Get global memory access patterns.
        
        Returns:
            Dictionary of global access patterns
        """
        self.process()
        
        return self.pattern_results.get("global", {"error": "No global patterns found"})
    
    def get_false_sharing_instances(self) -> List[Dict[str, Any]]:
        """
        Get instances of false sharing.
        
        Returns:
            List of false sharing instances
        """
        self.process()
        
        false_sharing_instances = []
        
        for key, results in self.pattern_results.items():
            if key.startswith("line_"):
                if "false_sharing" in results and results["false_sharing"]["detected"]:
                    line = results["line"]
                    false_sharing_instances.append({
                        "cache_line": line,
                        "details": results["false_sharing"],
                        "access_count": results["access_count"],
                        "thread_count": results["thread_count"],
                        "address_count": results["address_count"],
                    })
        
        # Sort by confidence
        false_sharing_instances.sort(
            key=lambda x: x["details"]["confidence"],
            reverse=True,
        )
        
        return false_sharing_instances
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of memory access pattern analysis.
        
        Returns:
            Dictionary of summarized results
        """
        self.process()
        
        global_patterns = self.get_global_patterns()
        
        # Count occurrences of each pattern type
        pattern_counts = Counter()
        for thread_id in self.thread_accesses:
            if thread_id in self.pattern_results:
                for pattern in self.pattern_results[thread_id].get("patterns", []):
                    pattern_counts[pattern] += 1
        
        # Count sharing patterns
        sharing_counts = Counter()
        for key, results in self.pattern_results.items():
            if key.startswith("addr_") and "sharing_pattern" in results:
                sharing_counts[results["sharing_pattern"]] += 1
        
        # Get false sharing instances
        false_sharing_instances = self.get_false_sharing_instances()
        
        return {
            "total_accesses": global_patterns.get("total_accesses", 0),
            "unique_addresses": global_patterns.get("unique_addresses", 0),
            "unique_lines": global_patterns.get("unique_lines", 0),
            "thread_count": global_patterns.get("thread_count", 0),
            "read_ratio": global_patterns.get("read_ratio", 0),
            "write_ratio": global_patterns.get("write_ratio", 0),
            "access_patterns": dict(pattern_counts),
            "sharing_patterns": dict(sharing_counts),
            "spatial_locality": global_patterns.get("spatial_locality", {"score": 0}),
            "false_sharing_count": len(false_sharing_instances),
            "hot_spots": global_patterns.get("hot_spots", []),
        }
    
    def reset(self) -> None:
        """Reset the analyzer."""
        self.thread_accesses = {}
        self.address_accesses = {}
        self.line_accesses = {}
        self.thread_access_history = {}
        self.is_processed = False
        self.pattern_results = {}