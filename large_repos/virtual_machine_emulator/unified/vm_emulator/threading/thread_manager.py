"""Thread management system for the VM."""

import random
import uuid
from typing import Dict, List, Optional, Set, Tuple, Any, Union

from vm_emulator.core.processor import ProcessorState
from vm_emulator.threading.thread import Thread, ThreadPriority


class ThreadManager:
    """
    Manages threads in the virtual machine.
    
    Responsible for thread creation, termination, state tracking,
    and providing thread information to the scheduler.
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize the thread manager.
        
        Args:
            random_seed: Optional seed for thread ID generation
        """
        self.threads: Dict[str, Thread] = {}
        self.ready_queue: List[str] = []
        self.waiting_threads: Dict[str, Dict[str, Any]] = {}
        self.random_seed = random_seed
        
        if random_seed is not None:
            random.seed(random_seed)
        
        # For tracking thread events
        self.thread_events: List[Dict[str, Any]] = []
        
        # For thread affinity
        self.processor_affinity: Dict[str, Set[int]] = {}
    
    def create_thread(
        self,
        program_id: str,
        entry_point: int,
        parent_thread_id: Optional[str] = None,
        priority: ThreadPriority = ThreadPriority.NORMAL,
        processor_affinity: Optional[Set[int]] = None,
        creation_time: int = 0,
    ) -> str:
        """
        Create a new thread.
        
        Args:
            program_id: ID of the program to execute
            entry_point: Starting program counter
            parent_thread_id: ID of parent thread, if any
            priority: Thread priority
            processor_affinity: Set of processor IDs this thread can run on
            creation_time: Global clock time at creation
            
        Returns:
            The new thread ID
        """
        # Generate thread ID
        if self.random_seed is not None:
            # Use deterministic ID generation
            thread_id = f"thread-{len(self.threads):08d}"
        else:
            thread_id = str(uuid.uuid4())
        
        # Create the thread
        thread = Thread(
            thread_id=thread_id,
            program_id=program_id,
            pc=entry_point,
            parent_thread_id=parent_thread_id,
            creation_time=creation_time,
            priority=priority,
            random_seed=self.random_seed,
        )
        
        # Store the thread
        self.threads[thread_id] = thread
        
        # Add to ready queue (sorted by priority)
        self._insert_into_ready_queue(thread_id)
        
        # Set processor affinity if provided
        if processor_affinity:
            self.processor_affinity[thread_id] = processor_affinity
        
        # Record thread creation event
        self.thread_events.append({
            "event": "thread_created",
            "thread_id": thread_id,
            "parent_thread_id": parent_thread_id,
            "program_id": program_id,
            "priority": priority.name,
            "timestamp": creation_time,
        })
        
        return thread_id
    
    def terminate_thread(self, thread_id: str, timestamp: int) -> None:
        """
        Terminate a thread.
        
        Args:
            thread_id: ID of the thread to terminate
            timestamp: Global clock time at termination
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        thread = self.threads[thread_id]
        
        # Update thread state
        thread.state = ProcessorState.TERMINATED
        
        # Remove from ready queue if present
        if thread_id in self.ready_queue:
            self.ready_queue.remove(thread_id)
        
        # Remove from waiting threads if present
        if thread_id in self.waiting_threads:
            del self.waiting_threads[thread_id]
        
        # Check for any threads waiting on this one to complete (join)
        for waiting_id, waiting_info in list(self.waiting_threads.items()):
            if waiting_info.get("reason") == "join" and waiting_info.get("target_thread_id") == thread_id:
                # Wake up the waiting thread
                self._unblock_thread(waiting_id, "join_completed", timestamp)
        
        # Record thread termination event
        self.thread_events.append({
            "event": "thread_terminated",
            "thread_id": thread_id,
            "execution_cycles": thread.execution_cycles,
            "timestamp": timestamp,
        })
    
    def block_thread(
        self, thread_id: str, reason: str, details: Dict[str, Any], timestamp: int
    ) -> None:
        """
        Block a thread from execution.
        
        Args:
            thread_id: ID of the thread to block
            reason: Reason for blocking (e.g., "lock", "io", "sleep")
            details: Additional details about the block
            timestamp: Global clock time at blocking
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        thread = self.threads[thread_id]
        
        # Update thread state
        prev_state = thread.state
        thread.state = ProcessorState.WAITING
        
        # Remove from ready queue if present
        if thread_id in self.ready_queue:
            self.ready_queue.remove(thread_id)
        
        # Add to waiting threads
        self.waiting_threads[thread_id] = {
            "reason": reason,
            **details,
            "blocked_at": timestamp,
        }
        
        # Record thread blocking event
        self.thread_events.append({
            "event": "thread_blocked",
            "thread_id": thread_id,
            "reason": reason,
            "details": details,
            "previous_state": prev_state.name,
            "timestamp": timestamp,
        })
    
    def _unblock_thread(self, thread_id: str, reason: str, timestamp: int) -> None:
        """
        Unblock a waiting thread.
        
        Args:
            thread_id: ID of the thread to unblock
            reason: Reason for unblocking
            timestamp: Global clock time at unblocking
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        if thread_id not in self.waiting_threads:
            return  # Thread is not waiting
        
        thread = self.threads[thread_id]
        
        # Calculate wait time
        blocked_at = self.waiting_threads[thread_id].get("blocked_at", timestamp)
        wait_time = timestamp - blocked_at
        thread.wait_times.append(wait_time)
        
        # Remove from waiting threads
        block_info = self.waiting_threads.pop(thread_id)
        
        # Update thread state
        thread.state = ProcessorState.WAITING
        
        # Add to ready queue
        self._insert_into_ready_queue(thread_id)
        
        # Record thread unblocking event
        self.thread_events.append({
            "event": "thread_unblocked",
            "thread_id": thread_id,
            "reason": reason,
            "wait_time": wait_time,
            "block_reason": block_info.get("reason"),
            "timestamp": timestamp,
        })
    
    def unblock_threads_by_condition(
        self, condition_func: callable, reason: str, timestamp: int
    ) -> List[str]:
        """
        Unblock all threads that meet a condition.
        
        Args:
            condition_func: Function that takes (thread_id, block_info) and returns bool
            reason: Reason for unblocking
            timestamp: Global clock time at unblocking
            
        Returns:
            List of unblocked thread IDs
        """
        unblocked_threads = []
        
        for thread_id, block_info in list(self.waiting_threads.items()):
            if condition_func(thread_id, block_info):
                self._unblock_thread(thread_id, reason, timestamp)
                unblocked_threads.append(thread_id)
        
        return unblocked_threads
    
    def _insert_into_ready_queue(self, thread_id: str) -> None:
        """
        Insert a thread into the ready queue based on priority.
        
        Args:
            thread_id: ID of the thread to insert
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        thread = self.threads[thread_id]
        
        # Find insert position based on priority
        insert_pos = len(self.ready_queue)
        for i, existing_id in enumerate(self.ready_queue):
            existing_thread = self.threads[existing_id]
            if thread.priority.value > existing_thread.priority.value:
                insert_pos = i
                break
        
        # Insert the thread ID
        self.ready_queue.insert(insert_pos, thread_id)
    
    def get_next_ready_thread(self) -> Optional[str]:
        """
        Get the next thread from the ready queue.
        
        Returns:
            Thread ID, or None if the queue is empty
        """
        if not self.ready_queue:
            return None
        
        return self.ready_queue.pop(0)
    
    def get_ready_threads(self) -> List[str]:
        """
        Get all ready threads in priority order.
        
        Returns:
            List of thread IDs
        """
        return self.ready_queue.copy()
    
    def get_waiting_threads(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all waiting threads and their reasons.
        
        Returns:
            Dictionary of thread_id -> waiting info
        """
        return self.waiting_threads.copy()
    
    def get_thread_count(self) -> int:
        """
        Get the total number of threads.
        
        Returns:
            Thread count
        """
        return len(self.threads)
    
    def get_ready_thread_count(self) -> int:
        """
        Get the number of ready threads.
        
        Returns:
            Ready thread count
        """
        return len(self.ready_queue)
    
    def get_waiting_thread_count(self) -> int:
        """
        Get the number of waiting threads.
        
        Returns:
            Waiting thread count
        """
        return len(self.waiting_threads)
    
    def get_running_thread_count(self) -> int:
        """
        Get the number of running threads.
        
        Returns:
            Running thread count
        """
        return sum(1 for t in self.threads.values() if t.state == ProcessorState.RUNNING)
    
    def get_thread_stats(self, thread_id: str) -> Dict[str, Union[int, float, List[int]]]:
        """
        Get statistics for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Dictionary of thread statistics
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        return self.threads[thread_id].get_statistics()
    
    def get_all_thread_stats(self) -> Dict[str, Dict[str, Union[int, float, List[int]]]]:
        """
        Get statistics for all threads.
        
        Returns:
            Dictionary of thread_id -> statistics
        """
        return {tid: thread.get_statistics() for tid, thread in self.threads.items()}
    
    def get_thread_processor_affinity(self, thread_id: str) -> Optional[Set[int]]:
        """
        Get the processor affinity for a thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Set of processor IDs or None if no affinity set
        """
        return self.processor_affinity.get(thread_id)
    
    def set_thread_processor_affinity(self, thread_id: str, processor_ids: Set[int]) -> None:
        """
        Set the processor affinity for a thread.
        
        Args:
            thread_id: ID of the thread
            processor_ids: Set of processor IDs this thread can run on
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        self.processor_affinity[thread_id] = processor_ids
    
    def set_thread_priority(
        self, thread_id: str, priority: ThreadPriority, timestamp: int
    ) -> None:
        """
        Set the priority for a thread.
        
        Args:
            thread_id: ID of the thread
            priority: New priority level
            timestamp: Global clock time of priority change
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        thread = self.threads[thread_id]
        old_priority = thread.priority
        
        # Update thread priority
        thread.priority = priority
        
        # If in ready queue, reposition based on new priority
        if thread_id in self.ready_queue:
            self.ready_queue.remove(thread_id)
            self._insert_into_ready_queue(thread_id)
        
        # Record priority change event
        self.thread_events.append({
            "event": "thread_priority_changed",
            "thread_id": thread_id,
            "old_priority": old_priority.name,
            "new_priority": priority.name,
            "timestamp": timestamp,
        })
    
    def get_thread_events(
        self,
        thread_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get filtered thread events.
        
        Args:
            thread_id: Filter by thread ID
            event_types: Filter by event types
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of filtered thread events
        """
        result = self.thread_events
        
        if thread_id is not None:
            result = [e for e in result if e.get("thread_id") == thread_id]
        
        if event_types:
            result = [e for e in result if e.get("event") in event_types]
        
        if start_time is not None:
            result = [e for e in result if e.get("timestamp", 0) >= start_time]
        
        if end_time is not None:
            result = [e for e in result if e.get("timestamp", 0) <= end_time]
        
        return result
    
    def get_thread_ancestry(self, thread_id: str) -> List[str]:
        """
        Get the ancestry chain for a thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            List of thread IDs representing ancestry (oldest first)
        """
        if thread_id not in self.threads:
            raise ValueError(f"Thread not found: {thread_id}")
        
        ancestry = [thread_id]
        current = self.threads[thread_id]
        
        while current.parent_thread_id and current.parent_thread_id in self.threads:
            ancestry.append(current.parent_thread_id)
            current = self.threads[current.parent_thread_id]
        
        return list(reversed(ancestry))
    
    def create_state_snapshot(self) -> Dict[str, Any]:
        """
        Create a snapshot of the entire thread manager state.
        
        Returns:
            Dictionary representing the thread manager state
        """
        return {
            "threads": {tid: thread.create_state_snapshot() for tid, thread in self.threads.items()},
            "ready_queue": self.ready_queue.copy(),
            "waiting_threads": self.waiting_threads.copy(),
            "processor_affinity": {tid: list(affinity) for tid, affinity in self.processor_affinity.items()},
            "thread_events": self.thread_events.copy(),
        }
    
    def apply_state_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        Apply a state snapshot to restore thread manager state.
        
        Args:
            snapshot: Thread manager state snapshot
        """
        # Clear current state
        self.threads.clear()
        self.ready_queue.clear()
        self.waiting_threads.clear()
        self.processor_affinity.clear()
        self.thread_events.clear()
        
        # Restore threads
        for tid, thread_snapshot in snapshot["threads"].items():
            program_id = thread_snapshot["program_id"]
            pc = thread_snapshot["pc"]
            parent_thread_id = thread_snapshot["parent_thread_id"]
            creation_time = thread_snapshot["creation_time"]
            priority = ThreadPriority[thread_snapshot["priority"]]
            
            # Create thread
            self.create_thread(
                program_id=program_id,
                entry_point=pc,
                parent_thread_id=parent_thread_id,
                priority=priority,
                creation_time=creation_time,
            )
            
            # Further state customization
            self.threads[tid].apply_state_snapshot(thread_snapshot)
        
        # Restore ready queue
        self.ready_queue = snapshot["ready_queue"].copy()
        
        # Restore waiting threads
        self.waiting_threads = snapshot["waiting_threads"].copy()
        
        # Restore processor affinity
        for tid, affinity_list in snapshot["processor_affinity"].items():
            self.processor_affinity[tid] = set(affinity_list)
        
        # Restore thread events
        self.thread_events = snapshot["thread_events"].copy()