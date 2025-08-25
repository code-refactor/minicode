"""Synchronization manager for the virtual machine."""

from typing import Dict, List, Optional, Set, Any, Union, Tuple

from vm_emulator.synchronization.primitives import (
    Lock,
    ReentrantLock,
    ReadWriteLock,
    Semaphore,
    Barrier,
    CountDownLatch,
)


class SynchronizationManager:
    """
    Manages all synchronization primitives in the VM.
    
    Provides a unified interface for creating and manipulating locks,
    semaphores, barriers, and other synchronization constructs.
    """
    
    def __init__(self):
        """Initialize the synchronization manager."""
        self.locks: Dict[int, Lock] = {}
        self.reentrant_locks: Dict[int, ReentrantLock] = {}
        self.read_write_locks: Dict[int, ReadWriteLock] = {}
        self.semaphores: Dict[int, Semaphore] = {}
        self.barriers: Dict[int, Barrier] = {}
        self.latches: Dict[int, CountDownLatch] = {}
        
        # Track waiting relationships between threads and sync objects
        self.thread_waits: Dict[str, Tuple[str, int]] = {}  # thread_id -> (primitive_type, id)
        
        # Overall synchronization events
        self.sync_events: List[Dict[str, Any]] = []
    
    # Lock operations
    def create_lock(self, lock_id: int) -> None:
        """
        Create a new lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        if lock_id in self.locks:
            raise ValueError(f"Lock already exists: {lock_id}")
        
        self.locks[lock_id] = Lock(lock_id)
    
    def acquire_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Attempt to acquire a lock.
        
        Args:
            lock_id: ID of the lock to acquire
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if lock_id not in self.locks:
            self.create_lock(lock_id)
        
        lock = self.locks[lock_id]
        acquired = lock.acquire(thread_id, timestamp)
        
        if acquired:
            # Succeeded, remove any wait record
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Failed, record the wait
            self.thread_waits[thread_id] = ("lock", lock_id)
        
        # Record event
        self.sync_events.append({
            "event": "lock_acquire",
            "primitive_type": "lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "success": acquired,
        })
        
        return acquired
    
    def release_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> Optional[str]:
        """
        Release a lock.
        
        Args:
            lock_id: ID of the lock to release
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            ID of the next thread that gets the lock, or None
        """
        if lock_id not in self.locks:
            raise ValueError(f"Lock not found: {lock_id}")
        
        lock = self.locks[lock_id]
        next_thread = lock.release(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "lock_release",
            "primitive_type": "lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "next_thread": next_thread,
        })
        
        return next_thread
    
    # Reentrant lock operations
    def create_reentrant_lock(self, lock_id: int) -> None:
        """
        Create a new reentrant lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        if lock_id in self.reentrant_locks:
            raise ValueError(f"Reentrant lock already exists: {lock_id}")
        
        self.reentrant_locks[lock_id] = ReentrantLock(lock_id)
    
    def acquire_reentrant_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Attempt to acquire a reentrant lock.
        
        Args:
            lock_id: ID of the lock to acquire
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if lock_id not in self.reentrant_locks:
            self.create_reentrant_lock(lock_id)
        
        lock = self.reentrant_locks[lock_id]
        acquired = lock.acquire(thread_id, timestamp)
        
        if acquired:
            # Succeeded, remove any wait record
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Failed, record the wait
            self.thread_waits[thread_id] = ("reentrant_lock", lock_id)
        
        # Record event
        self.sync_events.append({
            "event": "reentrant_lock_acquire",
            "primitive_type": "reentrant_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "success": acquired,
        })
        
        return acquired
    
    def release_reentrant_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> Optional[str]:
        """
        Release a reentrant lock.
        
        Args:
            lock_id: ID of the lock to release
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            ID of the next thread that gets the lock, or None
        """
        if lock_id not in self.reentrant_locks:
            raise ValueError(f"Reentrant lock not found: {lock_id}")
        
        lock = self.reentrant_locks[lock_id]
        next_thread = lock.release(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "reentrant_lock_release",
            "primitive_type": "reentrant_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "next_thread": next_thread,
        })
        
        return next_thread
    
    # Read-write lock operations
    def create_read_write_lock(self, lock_id: int) -> None:
        """
        Create a new read-write lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        if lock_id in self.read_write_locks:
            raise ValueError(f"Read-write lock already exists: {lock_id}")
        
        self.read_write_locks[lock_id] = ReadWriteLock(lock_id)
    
    def acquire_read_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Attempt to acquire a read lock.
        
        Args:
            lock_id: ID of the lock to acquire
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if lock_id not in self.read_write_locks:
            self.create_read_write_lock(lock_id)
        
        lock = self.read_write_locks[lock_id]
        acquired = lock.acquire_read(thread_id, timestamp)
        
        if acquired:
            # Succeeded, remove any wait record
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Failed, record the wait
            self.thread_waits[thread_id] = ("read_lock", lock_id)
        
        # Record event
        self.sync_events.append({
            "event": "read_lock_acquire",
            "primitive_type": "read_write_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "success": acquired,
        })
        
        return acquired
    
    def release_read_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> List[str]:
        """
        Release a read lock.
        
        Args:
            lock_id: ID of the lock to release
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get the lock
        """
        if lock_id not in self.read_write_locks:
            raise ValueError(f"Read-write lock not found: {lock_id}")
        
        lock = self.read_write_locks[lock_id]
        unblocked_threads = lock.release_read(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "read_lock_release",
            "primitive_type": "read_write_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "unblocked_threads": unblocked_threads,
        })
        
        return unblocked_threads
    
    def acquire_write_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Attempt to acquire a write lock.
        
        Args:
            lock_id: ID of the lock to acquire
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if lock_id not in self.read_write_locks:
            self.create_read_write_lock(lock_id)
        
        lock = self.read_write_locks[lock_id]
        acquired = lock.acquire_write(thread_id, timestamp)
        
        if acquired:
            # Succeeded, remove any wait record
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Failed, record the wait
            self.thread_waits[thread_id] = ("write_lock", lock_id)
        
        # Record event
        self.sync_events.append({
            "event": "write_lock_acquire",
            "primitive_type": "read_write_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "success": acquired,
        })
        
        return acquired
    
    def release_write_lock(
        self, lock_id: int, thread_id: str, timestamp: int
    ) -> List[str]:
        """
        Release a write lock.
        
        Args:
            lock_id: ID of the lock to release
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get the lock
        """
        if lock_id not in self.read_write_locks:
            raise ValueError(f"Read-write lock not found: {lock_id}")
        
        lock = self.read_write_locks[lock_id]
        unblocked_threads = lock.release_write(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "write_lock_release",
            "primitive_type": "read_write_lock",
            "id": lock_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "unblocked_threads": unblocked_threads,
        })
        
        return unblocked_threads
    
    # Semaphore operations
    def create_semaphore(self, semaphore_id: int, permits: int = 1) -> None:
        """
        Create a new semaphore.
        
        Args:
            semaphore_id: Unique identifier for the semaphore
            permits: Initial number of permits
        """
        if semaphore_id in self.semaphores:
            raise ValueError(f"Semaphore already exists: {semaphore_id}")
        
        self.semaphores[semaphore_id] = Semaphore(semaphore_id, permits)
    
    def acquire_semaphore(
        self, semaphore_id: int, thread_id: str, count: int, timestamp: int
    ) -> bool:
        """
        Attempt to acquire permits from a semaphore.
        
        Args:
            semaphore_id: ID of the semaphore
            thread_id: ID of the thread attempting to acquire
            count: Number of permits to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if semaphore_id not in self.semaphores:
            self.create_semaphore(semaphore_id, count)
        
        semaphore = self.semaphores[semaphore_id]
        acquired = semaphore.acquire(thread_id, count, timestamp)
        
        if acquired:
            # Succeeded, remove any wait record
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Failed, record the wait
            self.thread_waits[thread_id] = ("semaphore", semaphore_id)
        
        # Record event
        self.sync_events.append({
            "event": "semaphore_acquire",
            "primitive_type": "semaphore",
            "id": semaphore_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "count": count,
            "success": acquired,
        })
        
        return acquired
    
    def release_semaphore(
        self, semaphore_id: int, thread_id: str, count: int, timestamp: int
    ) -> List[str]:
        """
        Release permits back to a semaphore.
        
        Args:
            semaphore_id: ID of the semaphore
            thread_id: ID of the thread releasing permits
            count: Number of permits to release
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get permits
        """
        if semaphore_id not in self.semaphores:
            raise ValueError(f"Semaphore not found: {semaphore_id}")
        
        semaphore = self.semaphores[semaphore_id]
        unblocked_threads = semaphore.release(thread_id, count, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "semaphore_release",
            "primitive_type": "semaphore",
            "id": semaphore_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "count": count,
            "unblocked_threads": unblocked_threads,
        })
        
        return unblocked_threads
    
    # Barrier operations
    def create_barrier(self, barrier_id: int, parties: int) -> None:
        """
        Create a new barrier.
        
        Args:
            barrier_id: Unique identifier for the barrier
            parties: Number of threads that must arrive
        """
        if barrier_id in self.barriers:
            raise ValueError(f"Barrier already exists: {barrier_id}")
        
        self.barriers[barrier_id] = Barrier(barrier_id, parties)
    
    def arrive_at_barrier(
        self, barrier_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Register a thread's arrival at a barrier.
        
        Args:
            barrier_id: ID of the barrier
            thread_id: ID of the thread arriving
            timestamp: Current global clock value
            
        Returns:
            True if the barrier tripped, False otherwise
        """
        if barrier_id not in self.barriers:
            raise ValueError(f"Barrier not found: {barrier_id}")
        
        barrier = self.barriers[barrier_id]
        tripped = barrier.arrive(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "barrier_arrive",
            "primitive_type": "barrier",
            "id": barrier_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "tripped": tripped,
            "waiting_count": barrier.get_waiting_count(),
            "parties": barrier.parties,
        })
        
        if tripped:
            # Barrier tripped, unblock all waiting threads
            unblocked_threads = []
            for tid in list(barrier.waiting_threads):
                unblocked_threads.append(tid)
                if tid in self.thread_waits:
                    del self.thread_waits[tid]
            
            # Record event
            self.sync_events.append({
                "event": "barrier_trip",
                "primitive_type": "barrier",
                "id": barrier_id,
                "thread_id": thread_id,
                "timestamp": timestamp,
                "generation": barrier.generation,
                "unblocked_threads": unblocked_threads,
            })
            
            # Reset barrier for reuse
            barrier.reset()
            
            return True
        else:
            # Barrier didn't trip, record this thread as waiting
            self.thread_waits[thread_id] = ("barrier", barrier_id)
            return False
    
    # Latch operations
    def create_latch(self, latch_id: int, count: int) -> None:
        """
        Create a new count-down latch.
        
        Args:
            latch_id: Unique identifier for the latch
            count: Initial count value
        """
        if latch_id in self.latches:
            raise ValueError(f"Latch already exists: {latch_id}")
        
        self.latches[latch_id] = CountDownLatch(latch_id, count)
    
    def count_down_latch(
        self, latch_id: int, thread_id: str, timestamp: int
    ) -> Tuple[bool, List[str]]:
        """
        Decrement a latch's count.
        
        Args:
            latch_id: ID of the latch
            thread_id: ID of the thread counting down
            timestamp: Current global clock value
            
        Returns:
            Tuple of (reached_zero, unblocked_threads)
        """
        if latch_id not in self.latches:
            raise ValueError(f"Latch not found: {latch_id}")
        
        latch = self.latches[latch_id]
        reached_zero = latch.count_down(thread_id, timestamp)
        
        # Record event
        self.sync_events.append({
            "event": "latch_countdown",
            "primitive_type": "latch",
            "id": latch_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "new_count": latch.count,
            "reached_zero": reached_zero,
        })
        
        unblocked_threads = []
        if reached_zero:
            # Latch reached zero, unblock all waiting threads
            for tid in list(latch.waiting_threads):
                unblocked_threads.append(tid)
                if tid in self.thread_waits:
                    del self.thread_waits[tid]
            
            # Record event
            self.sync_events.append({
                "event": "latch_complete",
                "primitive_type": "latch",
                "id": latch_id,
                "thread_id": thread_id,
                "timestamp": timestamp,
                "unblocked_threads": unblocked_threads,
            })
        
        return reached_zero, unblocked_threads
    
    def await_latch(
        self, latch_id: int, thread_id: str, timestamp: int
    ) -> bool:
        """
        Wait for a latch to reach zero.
        
        Args:
            latch_id: ID of the latch
            thread_id: ID of the thread waiting
            timestamp: Current global clock value
            
        Returns:
            True if the latch is already at zero, False if needs to wait
        """
        if latch_id not in self.latches:
            raise ValueError(f"Latch not found: {latch_id}")
        
        latch = self.latches[latch_id]
        completed = latch.await_latch(thread_id, timestamp)
        
        if completed:
            # Latch already at zero, no need to wait
            if thread_id in self.thread_waits:
                del self.thread_waits[thread_id]
        else:
            # Latch not yet at zero, record this thread as waiting
            self.thread_waits[thread_id] = ("latch", latch_id)
        
        # Record event
        self.sync_events.append({
            "event": "latch_await",
            "primitive_type": "latch",
            "id": latch_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "current_count": latch.count,
            "completed": completed,
        })
        
        return completed
    
    # Utility methods
    def get_thread_wait_info(self, thread_id: str) -> Optional[Tuple[str, int]]:
        """
        Get information about what a thread is waiting for.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Tuple of (primitive_type, primitive_id), or None if not waiting
        """
        return self.thread_waits.get(thread_id)
    
    def get_waiting_threads(self, primitive_type: str, primitive_id: int) -> List[str]:
        """
        Get all threads waiting on a specific synchronization primitive.
        
        Args:
            primitive_type: Type of primitive ("lock", "semaphore", etc.)
            primitive_id: ID of the primitive
            
        Returns:
            List of waiting thread IDs
        """
        return [
            tid for tid, (ptype, pid) in self.thread_waits.items()
            if ptype == primitive_type and pid == primitive_id
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about all synchronization primitives.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "locks": {},
            "reentrant_locks": {},
            "read_write_locks": {},
            "semaphores": {},
            "barriers": {},
            "latches": {},
            "waiting_threads": len(self.thread_waits),
            "sync_events": len(self.sync_events),
        }
        
        # Lock statistics
        for lock_id, lock in self.locks.items():
            stats["locks"][lock_id] = lock.get_statistics()
        
        # Reentrant lock statistics
        for lock_id, lock in self.reentrant_locks.items():
            stats["reentrant_locks"][lock_id] = lock.get_statistics()
        
        # Read-write lock statistics
        for lock_id, lock in self.read_write_locks.items():
            stats["read_write_locks"][lock_id] = lock.get_statistics()
        
        # Semaphore statistics
        for semaphore_id, semaphore in self.semaphores.items():
            stats["semaphores"][semaphore_id] = semaphore.get_statistics()
        
        # Barrier statistics
        for barrier_id, barrier in self.barriers.items():
            stats["barriers"][barrier_id] = barrier.get_statistics()
        
        # Latch statistics
        for latch_id, latch in self.latches.items():
            stats["latches"][latch_id] = latch.get_statistics()
        
        return stats
    
    def get_events(
        self,
        primitive_type: Optional[str] = None,
        primitive_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get filtered synchronization events.
        
        Args:
            primitive_type: Filter by primitive type
            primitive_id: Filter by primitive ID
            thread_id: Filter by thread ID
            event_types: Filter by event types
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of filtered events
        """
        result = self.sync_events
        
        if primitive_type is not None:
            result = [e for e in result if e.get("primitive_type") == primitive_type]
        
        if primitive_id is not None:
            result = [e for e in result if e.get("id") == primitive_id]
        
        if thread_id is not None:
            result = [e for e in result if e.get("thread_id") == thread_id]
        
        if event_types:
            result = [e for e in result if e.get("event") in event_types]
        
        if start_time is not None:
            result = [e for e in result if e.get("timestamp", 0) >= start_time]
        
        if end_time is not None:
            result = [e for e in result if e.get("timestamp", 0) <= end_time]
        
        return result
    
    def create_state_snapshot(self) -> Dict[str, Any]:
        """
        Create a snapshot of the entire synchronization manager state.
        
        Returns:
            Dictionary representing the synchronization manager state
        """
        # This would involve serializing the state of all primitives
        # For brevity, this is a simplified version
        return {
            "locks": {lid: {"state": lock.state.name, "owner": lock.owner} 
                     for lid, lock in self.locks.items()},
            "reentrant_locks": {lid: {"state": lock.state.name, "owner": lock.owner, "recursion_level": lock.recursion_level} 
                               for lid, lock in self.reentrant_locks.items()},
            "semaphores": {sid: {"permits": sem.permits, "waiting": list(sem.waiting_threads)} 
                          for sid, sem in self.semaphores.items()},
            "barriers": {bid: {"waiting": list(barrier.waiting_threads), "generation": barrier.generation} 
                        for bid, barrier in self.barriers.items()},
            "latches": {lid: {"count": latch.count, "waiting": list(latch.waiting_threads)} 
                       for lid, latch in self.latches.items()},
            "thread_waits": {tid: {"primitive_type": ptype, "primitive_id": pid} 
                            for tid, (ptype, pid) in self.thread_waits.items()},
            "sync_events": self.sync_events.copy(),
        }
    
    def reset(self) -> None:
        """Reset the synchronization manager to initial state."""
        self.locks = {}
        self.reentrant_locks = {}
        self.read_write_locks = {}
        self.semaphores = {}
        self.barriers = {}
        self.latches = {}
        self.thread_waits = {}
        self.sync_events = []