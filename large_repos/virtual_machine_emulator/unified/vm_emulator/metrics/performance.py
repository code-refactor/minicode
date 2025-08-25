"""Performance metrics for the VM."""

import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union


class MetricsCollector:
    """
    Collects and analyzes performance metrics for VM execution.
    
    Tracks various metrics such as execution time, throughput,
    processor utilization, and synchronization overhead.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        # Overall execution metrics
        self.start_time = 0.0
        self.end_time = 0.0
        self.total_cycles = 0
        self.instruction_count = 0
        
        # Thread-specific metrics
        self.thread_cycles: Dict[str, int] = {}  # Cycles spent executing each thread
        self.thread_instructions: Dict[str, int] = {}  # Instructions executed by each thread
        self.thread_wait_cycles: Dict[str, int] = {}  # Cycles spent waiting
        self.thread_contexts: Dict[str, int] = {}  # Context switches for each thread
        
        # Processor utilization
        self.processor_active_cycles: Dict[int, int] = {}  # Active cycles per processor
        self.processor_idle_cycles: Dict[int, int] = {}  # Idle cycles per processor
        
        # Memory system metrics
        self.memory_reads = 0
        self.memory_writes = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Synchronization metrics
        self.sync_operations = 0
        self.sync_wait_cycles = 0
        self.lock_acquisitions = 0
        self.lock_contentions = 0
        
        # Performance counters
        self.counters: Dict[str, int] = {}
        
        # Execution time samples for bottleneck analysis
        self.time_samples: List[Dict[str, Any]] = []
        self.sample_interval = 0.1  # seconds
        self.last_sample_time = 0.0
        
        # For recording checkpoints
        self.checkpoints: List[Dict[str, Any]] = []
    
    def start_measurement(self) -> None:
        """Start performance measurement."""
        self.start_time = time.time()
        self.last_sample_time = self.start_time
    
    def end_measurement(self) -> None:
        """End performance measurement."""
        self.end_time = time.time()
    
    def record_cycle(self, active_processors: Dict[int, Optional[str]]) -> None:
        """
        Record a VM cycle.
        
        Args:
            active_processors: Dictionary of processor_id -> thread_id or None
        """
        self.total_cycles += 1
        
        # Update processor and thread metrics
        for processor_id, thread_id in active_processors.items():
            # Initialize processor metrics if needed
            if processor_id not in self.processor_active_cycles:
                self.processor_active_cycles[processor_id] = 0
                self.processor_idle_cycles[processor_id] = 0
            
            if thread_id is not None:
                # Processor is active
                self.processor_active_cycles[processor_id] += 1
                
                # Initialize thread metrics if needed
                if thread_id not in self.thread_cycles:
                    self.thread_cycles[thread_id] = 0
                    self.thread_instructions[thread_id] = 0
                    self.thread_wait_cycles[thread_id] = 0
                    self.thread_contexts[thread_id] = 0
                
                # Update thread execution cycles
                self.thread_cycles[thread_id] += 1
            else:
                # Processor is idle
                self.processor_idle_cycles[processor_id] += 1
        
        # Take time sample if interval has elapsed
        current_time = time.time()
        if current_time - self.last_sample_time >= self.sample_interval:
            self._take_time_sample(active_processors)
            self.last_sample_time = current_time
    
    def record_instruction(self, thread_id: str, instruction_type: str) -> None:
        """
        Record an instruction execution.
        
        Args:
            thread_id: ID of the thread executing the instruction
            instruction_type: Type of instruction
        """
        self.instruction_count += 1
        
        # Initialize thread metrics if needed
        if thread_id not in self.thread_instructions:
            self.thread_instructions[thread_id] = 0
        
        # Update thread instruction count
        self.thread_instructions[thread_id] += 1
        
        # Update instruction type counter
        counter_key = f"instruction_{instruction_type}"
        self.counters[counter_key] = self.counters.get(counter_key, 0) + 1
    
    def record_memory_access(self, access_type: str, hit: bool) -> None:
        """
        Record a memory access.
        
        Args:
            access_type: Type of access ("read" or "write")
            hit: Whether the access was a cache hit
        """
        if access_type == "read":
            self.memory_reads += 1
        elif access_type == "write":
            self.memory_writes += 1
        
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_sync_operation(
        self, operation: str, thread_id: str, contended: bool = False
    ) -> None:
        """
        Record a synchronization operation.
        
        Args:
            operation: Type of operation
            thread_id: ID of the thread performing the operation
            contended: Whether the operation was contended
        """
        self.sync_operations += 1
        
        # Update specific counters based on operation type
        if operation in ("lock_acquire", "lock_try_acquire"):
            self.lock_acquisitions += 1
            
            if contended:
                self.lock_contentions += 1
        
        # Update operation counter
        counter_key = f"sync_{operation}"
        self.counters[counter_key] = self.counters.get(counter_key, 0) + 1
        
        if contended:
            counter_key = f"sync_{operation}_contended"
            self.counters[counter_key] = self.counters.get(counter_key, 0) + 1
    
    def record_sync_wait(self, thread_id: str, cycles: int) -> None:
        """
        Record synchronization wait time.
        
        Args:
            thread_id: ID of the waiting thread
            cycles: Number of cycles spent waiting
        """
        self.sync_wait_cycles += cycles
        
        # Initialize thread metrics if needed
        if thread_id not in self.thread_wait_cycles:
            self.thread_wait_cycles[thread_id] = 0
        
        # Update thread wait cycles
        self.thread_wait_cycles[thread_id] += cycles
    
    def record_context_switch(self, thread_id: str) -> None:
        """
        Record a context switch.
        
        Args:
            thread_id: ID of the thread being switched out
        """
        # Initialize thread metrics if needed
        if thread_id not in self.thread_contexts:
            self.thread_contexts[thread_id] = 0
        
        # Update thread context switch count
        self.thread_contexts[thread_id] += 1
    
    def record_counter(self, name: str, value: int = 1) -> None:
        """
        Record a custom counter value.
        
        Args:
            name: Counter name
            value: Value to add to the counter
        """
        self.counters[name] = self.counters.get(name, 0) + value
    
    def create_checkpoint(self, label: str) -> None:
        """
        Create a metrics checkpoint.
        
        Args:
            label: Checkpoint label
        """
        # Capture current metrics
        checkpoint = {
            "label": label,
            "time": time.time(),
            "elapsed_time": time.time() - self.start_time,
            "cycles": self.total_cycles,
            "instructions": self.instruction_count,
            "counters": self.counters.copy(),
        }
        
        self.checkpoints.append(checkpoint)
    
    def _take_time_sample(self, active_processors: Dict[int, Optional[str]]) -> None:
        """
        Take a time sample for bottleneck analysis.
        
        Args:
            active_processors: Dictionary of processor_id -> thread_id or None
        """
        # Record the current state
        sample = {
            "time": time.time(),
            "elapsed_time": time.time() - self.start_time,
            "cycles": self.total_cycles,
            "instructions": self.instruction_count,
            "active_processors": active_processors.copy(),
            "active_count": sum(1 for tid in active_processors.values() if tid is not None),
            "idle_count": sum(1 for tid in active_processors.values() if tid is None),
        }
        
        self.time_samples.append(sample)
    
    def get_execution_time(self) -> float:
        """
        Get the total execution time in seconds.
        
        Returns:
            Execution time in seconds
        """
        if self.end_time == 0:
            # Measurement still running
            return time.time() - self.start_time
        
        return self.end_time - self.start_time
    
    def get_cycles_per_second(self) -> float:
        """
        Get the average number of cycles per second.
        
        Returns:
            Cycles per second
        """
        exec_time = self.get_execution_time()
        
        if exec_time == 0:
            return 0.0
        
        return self.total_cycles / exec_time
    
    def get_instructions_per_cycle(self) -> float:
        """
        Get the average number of instructions per cycle.
        
        Returns:
            Instructions per cycle
        """
        if self.total_cycles == 0:
            return 0.0
        
        return self.instruction_count / self.total_cycles
    
    def get_instructions_per_second(self) -> float:
        """
        Get the average number of instructions per second.
        
        Returns:
            Instructions per second
        """
        exec_time = self.get_execution_time()
        
        if exec_time == 0:
            return 0.0
        
        return self.instruction_count / exec_time
    
    def get_processor_utilization(self) -> Dict[int, float]:
        """
        Get the utilization percentage for each processor.
        
        Returns:
            Dictionary of processor_id -> utilization percentage
        """
        utilization = {}
        
        for processor_id in self.processor_active_cycles:
            active = self.processor_active_cycles[processor_id]
            idle = self.processor_idle_cycles[processor_id]
            total = active + idle
            
            if total == 0:
                utilization[processor_id] = 0.0
            else:
                utilization[processor_id] = (active / total) * 100.0
        
        return utilization
    
    def get_overall_processor_utilization(self) -> float:
        """
        Get the overall processor utilization.
        
        Returns:
            Overall processor utilization percentage
        """
        total_active = sum(self.processor_active_cycles.values())
        total_idle = sum(self.processor_idle_cycles.values())
        total = total_active + total_idle
        
        if total == 0:
            return 0.0
        
        return (total_active / total) * 100.0
    
    def get_cache_hit_rate(self) -> float:
        """
        Get the cache hit rate.
        
        Returns:
            Cache hit rate percentage
        """
        total_accesses = self.cache_hits + self.cache_misses
        
        if total_accesses == 0:
            return 0.0
        
        return (self.cache_hits / total_accesses) * 100.0
    
    def get_thread_metrics(self, thread_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Dictionary of thread metrics
        """
        if thread_id not in self.thread_cycles:
            return {"thread_id": thread_id, "error": "Thread not found"}
        
        cycles = self.thread_cycles.get(thread_id, 0)
        instructions = self.thread_instructions.get(thread_id, 0)
        wait_cycles = self.thread_wait_cycles.get(thread_id, 0)
        contexts = self.thread_contexts.get(thread_id, 0)
        
        # Calculate derived metrics
        ipc = instructions / cycles if cycles > 0 else 0.0
        wait_percentage = (wait_cycles / (cycles + wait_cycles)) * 100.0 if (cycles + wait_cycles) > 0 else 0.0
        
        return {
            "thread_id": thread_id,
            "cycles": cycles,
            "instructions": instructions,
            "instructions_per_cycle": ipc,
            "wait_cycles": wait_cycles,
            "wait_percentage": wait_percentage,
            "context_switches": contexts,
        }
    
    def get_all_thread_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all threads.
        
        Returns:
            Dictionary of thread_id -> thread metrics
        """
        return {tid: self.get_thread_metrics(tid) for tid in self.thread_cycles}
    
    def get_sync_metrics(self) -> Dict[str, Any]:
        """
        Get synchronization metrics.
        
        Returns:
            Dictionary of synchronization metrics
        """
        # Calculate contention rate
        contention_rate = (
            (self.lock_contentions / self.lock_acquisitions) * 100.0
            if self.lock_acquisitions > 0 else 0.0
        )
        
        # Calculate sync overhead
        sync_overhead = (
            (self.sync_wait_cycles / self.total_cycles) * 100.0
            if self.total_cycles > 0 else 0.0
        )
        
        return {
            "sync_operations": self.sync_operations,
            "lock_acquisitions": self.lock_acquisitions,
            "lock_contentions": self.lock_contentions,
            "contention_rate": contention_rate,
            "sync_wait_cycles": self.sync_wait_cycles,
            "sync_overhead": sync_overhead,
        }
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Get memory system metrics.
        
        Returns:
            Dictionary of memory metrics
        """
        # Calculate hit rate
        hit_rate = self.get_cache_hit_rate()
        
        # Calculate memory intensity
        memory_intensity = (
            ((self.memory_reads + self.memory_writes) / self.instruction_count) * 100.0
            if self.instruction_count > 0 else 0.0
        )
        
        return {
            "memory_reads": self.memory_reads,
            "memory_writes": self.memory_writes,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "memory_intensity": memory_intensity,
        }
    
    def get_counters(self) -> Dict[str, int]:
        """
        Get all performance counters.
        
        Returns:
            Dictionary of counter name -> value
        """
        return self.counters.copy()
    
    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """
        Get all metrics checkpoints.
        
        Returns:
            List of checkpoint dictionaries
        """
        return self.checkpoints
    
    def get_checkpoint_diff(self, label1: str, label2: str) -> Dict[str, Any]:
        """
        Get the difference between two checkpoints.
        
        Args:
            label1: First checkpoint label
            label2: Second checkpoint label
            
        Returns:
            Dictionary of differences
        """
        # Find the checkpoints
        checkpoint1 = None
        checkpoint2 = None
        
        for cp in self.checkpoints:
            if cp["label"] == label1:
                checkpoint1 = cp
            elif cp["label"] == label2:
                checkpoint2 = cp
        
        if not checkpoint1 or not checkpoint2:
            return {"error": "Checkpoint not found"}
        
        # Calculate differences
        time_diff = checkpoint2["elapsed_time"] - checkpoint1["elapsed_time"]
        cycle_diff = checkpoint2["cycles"] - checkpoint1["cycles"]
        instruction_diff = checkpoint2["instructions"] - checkpoint1["instructions"]
        
        # Calculate counter diffs
        counter_diffs = {}
        for key in set(checkpoint2["counters"].keys()) | set(checkpoint1["counters"].keys()):
            val1 = checkpoint1["counters"].get(key, 0)
            val2 = checkpoint2["counters"].get(key, 0)
            counter_diffs[key] = val2 - val1
        
        return {
            "label1": label1,
            "label2": label2,
            "time_diff": time_diff,
            "cycle_diff": cycle_diff,
            "instruction_diff": instruction_diff,
            "counter_diffs": counter_diffs,
            "cycles_per_second": cycle_diff / time_diff if time_diff > 0 else 0.0,
            "instructions_per_second": instruction_diff / time_diff if time_diff > 0 else 0.0,
            "instructions_per_cycle": instruction_diff / cycle_diff if cycle_diff > 0 else 0.0,
        }
    
    def find_bottlenecks(self) -> Dict[str, Any]:
        """
        Analyze metrics to identify potential bottlenecks.
        
        Returns:
            Dictionary of bottleneck analysis results
        """
        bottlenecks = []
        bottleneck_scores = {}
        
        # Check processor utilization for imbalance
        proc_util = self.get_processor_utilization()
        avg_util = sum(proc_util.values()) / len(proc_util) if proc_util else 0
        
        for pid, util in proc_util.items():
            if util > avg_util * 1.5:
                bottlenecks.append(f"Processor {pid} utilization is significantly higher than average")
                bottleneck_scores["processor_imbalance"] = abs(util - avg_util) / 100.0
        
        # Check cache hit rate
        hit_rate = self.get_cache_hit_rate()
        if hit_rate < 80.0:
            bottlenecks.append(f"Low cache hit rate: {hit_rate:.2f}%")
            bottleneck_scores["cache_misses"] = (80.0 - hit_rate) / 80.0
        
        # Check lock contention
        sync_metrics = self.get_sync_metrics()
        contention_rate = sync_metrics["contention_rate"]
        
        if contention_rate > 10.0:
            bottlenecks.append(f"High lock contention rate: {contention_rate:.2f}%")
            bottleneck_scores["lock_contention"] = contention_rate / 100.0
        
        # Check thread wait time
        thread_metrics = self.get_all_thread_metrics()
        high_wait_threads = []
        
        for tid, metrics in thread_metrics.items():
            if metrics["wait_percentage"] > 40.0:
                high_wait_threads.append(tid)
                bottleneck_scores["thread_wait"] = max(
                    bottleneck_scores.get("thread_wait", 0.0),
                    metrics["wait_percentage"] / 100.0
                )
        
        if high_wait_threads:
            bottlenecks.append(f"High thread wait time for threads: {', '.join(high_wait_threads)}")
        
        # Check for serial execution
        for sample in self.time_samples:
            if len(self.processor_active_cycles) > 1 and sample["active_count"] <= 1:
                bottlenecks.append("Poor parallelization: frequently only one processor active")
                bottleneck_scores["parallelization"] = 0.8
                break
        
        # Check instruction mix
        if "instruction_SYNC" in self.counters:
            sync_instr_pct = (self.counters["instruction_SYNC"] / self.instruction_count) * 100.0 if self.instruction_count > 0 else 0
            
            if sync_instr_pct > 15.0:
                bottlenecks.append(f"High ratio of synchronization instructions: {sync_instr_pct:.2f}%")
                bottleneck_scores["sync_instructions"] = sync_instr_pct / 100.0
        
        # Find the top bottlenecks
        top_bottlenecks = sorted(
            bottleneck_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Prepare recommendations
        recommendations = []
        
        for bottleneck, score in top_bottlenecks:
            if bottleneck == "processor_imbalance":
                recommendations.append("Review thread assignment strategy to better balance load across processors")
            elif bottleneck == "cache_misses":
                recommendations.append("Optimize memory access patterns for better cache locality")
            elif bottleneck == "lock_contention":
                recommendations.append("Reduce lock contention by finer-grained locking or lock-free algorithms")
            elif bottleneck == "thread_wait":
                recommendations.append("Reduce thread wait time by optimizing synchronization or better scheduling")
            elif bottleneck == "parallelization":
                recommendations.append("Improve parallelization to utilize more processors simultaneously")
            elif bottleneck == "sync_instructions":
                recommendations.append("Reduce synchronization overhead by batching work or using more efficient algorithms")
        
        return {
            "bottlenecks": bottlenecks,
            "bottleneck_scores": bottleneck_scores,
            "top_bottlenecks": top_bottlenecks,
            "recommendations": recommendations,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            Dictionary of summarized metrics
        """
        return {
            "execution_time": self.get_execution_time(),
            "total_cycles": self.total_cycles,
            "total_instructions": self.instruction_count,
            "cycles_per_second": self.get_cycles_per_second(),
            "instructions_per_cycle": self.get_instructions_per_cycle(),
            "instructions_per_second": self.get_instructions_per_second(),
            "processor_utilization": self.get_overall_processor_utilization(),
            "processor_util_breakdown": self.get_processor_utilization(),
            "thread_count": len(self.thread_cycles),
            "sync_metrics": self.get_sync_metrics(),
            "memory_metrics": self.get_memory_metrics(),
            "bottlenecks": self.find_bottlenecks(),
        }
    
    def reset(self) -> None:
        """Reset the metrics collector."""
        self.start_time = 0.0
        self.end_time = 0.0
        self.total_cycles = 0
        self.instruction_count = 0
        self.thread_cycles = {}
        self.thread_instructions = {}
        self.thread_wait_cycles = {}
        self.thread_contexts = {}
        self.processor_active_cycles = {}
        self.processor_idle_cycles = {}
        self.memory_reads = 0
        self.memory_writes = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.sync_operations = 0
        self.sync_wait_cycles = 0
        self.lock_acquisitions = 0
        self.lock_contentions = 0
        self.counters = {}
        self.time_samples = []
        self.last_sample_time = 0.0
        self.checkpoints = []