"""Synchronization primitives for the virtual machine."""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Any


class LockState(Enum):
    """States that a lock can be in."""
    UNLOCKED = auto()
    LOCKED = auto()


class SemaphoreState(Enum):
    """States that a semaphore can be in."""
    AVAILABLE = auto()  # Has available permits
    UNAVAILABLE = auto()  # No available permits


class BarrierState(Enum):
    """States that a barrier can be in."""
    OPEN = auto()     # All threads have arrived
    WAITING = auto()  # Still waiting for threads


class Lock:
    """Mutex lock implementation."""
    
    def __init__(self, lock_id: int):
        """
        Initialize a lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        self.lock_id = lock_id
        self.state = LockState.UNLOCKED
        self.owner: Optional[str] = None
        self.waiting_threads: List[str] = []
        self.acquisition_count = 0
        self.contention_count = 0
        self.events: List[Dict[str, Any]] = []
    
    def acquire(self, thread_id: str, timestamp: int) -> bool:
        """
        Attempt to acquire the lock.
        
        Args:
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if self.state == LockState.UNLOCKED:
            # Lock is free, acquire it
            self.state = LockState.LOCKED
            self.owner = thread_id
            self.acquisition_count += 1
            
            # Record event
            self.events.append({
                "event": "lock_acquired",
                "thread_id": thread_id,
                "timestamp": timestamp,
                "contended": False,
            })
            
            return True
        
        # Lock is taken, add to waiting list
        if thread_id not in self.waiting_threads:
            self.waiting_threads.append(thread_id)
            self.contention_count += 1
            
            # Record event
            self.events.append({
                "event": "lock_contention",
                "thread_id": thread_id,
                "owner": self.owner,
                "timestamp": timestamp,
            })
        
        return False
    
    def release(self, thread_id: str, timestamp: int) -> Optional[str]:
        """
        Release the lock if owned by the thread.
        
        Args:
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            ID of the next thread that gets the lock, or None
        """
        if self.state != LockState.LOCKED:
            raise ValueError(f"Cannot release unlocked lock: {self.lock_id}")
        
        if self.owner != thread_id:
            raise ValueError(
                f"Thread {thread_id} cannot release lock {self.lock_id} "
                f"owned by {self.owner}"
            )
        
        # Record event
        self.events.append({
            "event": "lock_released",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "wait_queue_size": len(self.waiting_threads),
        })
        
        # If no threads are waiting, just unlock
        if not self.waiting_threads:
            self.state = LockState.UNLOCKED
            self.owner = None
            return None
        
        # Otherwise, give the lock to the next waiting thread
        next_thread = self.waiting_threads.pop(0)
        self.owner = next_thread
        self.acquisition_count += 1
        
        # Record event
        self.events.append({
            "event": "lock_acquired",
            "thread_id": next_thread,
            "timestamp": timestamp,
            "contended": True,
        })
        
        return next_thread
    
    def is_held_by(self, thread_id: str) -> bool:
        """
        Check if the lock is held by a specific thread.
        
        Args:
            thread_id: ID of the thread to check
            
        Returns:
            True if the lock is held by the thread
        """
        return self.state == LockState.LOCKED and self.owner == thread_id
    
    def is_locked(self) -> bool:
        """
        Check if the lock is currently locked.
        
        Returns:
            True if locked
        """
        return self.state == LockState.LOCKED
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lock statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "lock_id": self.lock_id,
            "state": self.state.name,
            "owner": self.owner,
            "waiting_count": len(self.waiting_threads),
            "acquisition_count": self.acquisition_count,
            "contention_count": self.contention_count,
            "contention_ratio": (
                self.contention_count / self.acquisition_count 
                if self.acquisition_count > 0 else 0.0
            ),
        }


class ReentrantLock(Lock):
    """Reentrant lock implementation (can be acquired multiple times by the same thread)."""
    
    def __init__(self, lock_id: int):
        """
        Initialize a reentrant lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        super().__init__(lock_id)
        self.recursion_level = 0
    
    def acquire(self, thread_id: str, timestamp: int) -> bool:
        """
        Attempt to acquire the lock.
        
        Args:
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if self.state == LockState.LOCKED and self.owner == thread_id:
            # Already owned by this thread, increment recursion level
            self.recursion_level += 1
            
            # Record event
            self.events.append({
                "event": "lock_reacquired",
                "thread_id": thread_id,
                "timestamp": timestamp,
                "recursion_level": self.recursion_level,
            })
            
            return True
        
        # Otherwise, behave like a normal lock
        acquired = super().acquire(thread_id, timestamp)
        
        if acquired:
            self.recursion_level = 1
        
        return acquired
    
    def release(self, thread_id: str, timestamp: int) -> Optional[str]:
        """
        Release the lock if owned by the thread.
        
        Args:
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            ID of the next thread that gets the lock, or None
        """
        if self.state != LockState.LOCKED:
            raise ValueError(f"Cannot release unlocked lock: {self.lock_id}")
        
        if self.owner != thread_id:
            raise ValueError(
                f"Thread {thread_id} cannot release lock {self.lock_id} "
                f"owned by {self.owner}"
            )
        
        # Decrement recursion level
        self.recursion_level -= 1
        
        # Record event
        self.events.append({
            "event": "lock_recursion_reduced",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "recursion_level": self.recursion_level,
        })
        
        # If recursion level is still positive, lock is still held
        if self.recursion_level > 0:
            return None
        
        # Reset recursion level to avoid negative values
        self.recursion_level = 0
        
        # Otherwise, release the lock normally
        next_thread = super().release(thread_id, timestamp)
        
        # Update recursion level for the new owner
        if next_thread is not None:
            self.recursion_level = 1
        
        return next_thread
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get reentrant lock statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = super().get_statistics()
        stats["recursion_level"] = self.recursion_level
        return stats


class ReadWriteLock:
    """
    Read-write lock implementation.
    
    Allows multiple readers but only one writer.
    """
    
    def __init__(self, lock_id: int):
        """
        Initialize a read-write lock.
        
        Args:
            lock_id: Unique identifier for the lock
        """
        self.lock_id = lock_id
        self.reader_count = 0
        self.readers: Set[str] = set()
        self.writer: Optional[str] = None
        self.waiting_readers: List[str] = []
        self.waiting_writers: List[str] = []
        self.reader_acquisitions = 0
        self.writer_acquisitions = 0
        self.read_contentions = 0
        self.write_contentions = 0
        self.events: List[Dict[str, Any]] = []
    
    def acquire_read(self, thread_id: str, timestamp: int) -> bool:
        """
        Attempt to acquire the lock for reading.
        
        Args:
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        # If there's an active writer or waiting writers, readers must wait
        if self.writer is not None or self.waiting_writers:
            if thread_id not in self.waiting_readers:
                self.waiting_readers.append(thread_id)
                self.read_contentions += 1
                
                # Record event
                self.events.append({
                    "event": "read_lock_contention",
                    "thread_id": thread_id,
                    "writer": self.writer,
                    "waiting_writers": len(self.waiting_writers),
                    "timestamp": timestamp,
                })
            
            return False
        
        # Otherwise, grant read access
        self.readers.add(thread_id)
        self.reader_count += 1
        self.reader_acquisitions += 1
        
        # Record event
        self.events.append({
            "event": "read_lock_acquired",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "reader_count": self.reader_count,
        })
        
        return True
    
    def release_read(self, thread_id: str, timestamp: int) -> List[str]:
        """
        Release the read lock.
        
        Args:
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get the lock
        """
        if thread_id not in self.readers:
            raise ValueError(f"Thread {thread_id} is not a reader of lock {self.lock_id}")
        
        # Remove this reader
        self.readers.remove(thread_id)
        self.reader_count -= 1
        
        # Record event
        self.events.append({
            "event": "read_lock_released",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "reader_count": self.reader_count,
        })
        
        # If there are still active readers, we're done
        if self.reader_count > 0:
            return []
        
        # If there are no more readers and there are waiting writers,
        # grant write access to the first waiting writer
        unblocked_threads = []
        if self.waiting_writers:
            writer_thread = self.waiting_writers.pop(0)
            self.writer = writer_thread
            self.writer_acquisitions += 1
            unblocked_threads.append(writer_thread)
            
            # Record event
            self.events.append({
                "event": "write_lock_acquired",
                "thread_id": writer_thread,
                "timestamp": timestamp,
                "waited": True,
            })
        
        return unblocked_threads
    
    def acquire_write(self, thread_id: str, timestamp: int) -> bool:
        """
        Attempt to acquire the lock for writing.
        
        Args:
            thread_id: ID of the thread attempting to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        # Writers need exclusive access, so both readers and writers must be clear
        if self.reader_count > 0 or self.writer is not None:
            if thread_id not in self.waiting_writers:
                self.waiting_writers.append(thread_id)
                self.write_contentions += 1
                
                # Record event
                self.events.append({
                    "event": "write_lock_contention",
                    "thread_id": thread_id,
                    "readers": len(self.readers),
                    "writer": self.writer,
                    "timestamp": timestamp,
                })
            
            return False
        
        # Grant write access
        self.writer = thread_id
        self.writer_acquisitions += 1
        
        # Record event
        self.events.append({
            "event": "write_lock_acquired",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "waited": False,
        })
        
        return True
    
    def release_write(self, thread_id: str, timestamp: int) -> List[str]:
        """
        Release the write lock.
        
        Args:
            thread_id: ID of the thread releasing the lock
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get the lock
        """
        if self.writer != thread_id:
            raise ValueError(
                f"Thread {thread_id} is not the writer of lock {self.lock_id}"
            )
        
        # Release write access
        self.writer = None
        
        # Record event
        self.events.append({
            "event": "write_lock_released",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "waiting_readers": len(self.waiting_readers),
            "waiting_writers": len(self.waiting_writers),
        })
        
        unblocked_threads = []
        
        # If there are waiting writers, prioritize them
        if self.waiting_writers:
            writer_thread = self.waiting_writers.pop(0)
            self.writer = writer_thread
            self.writer_acquisitions += 1
            unblocked_threads.append(writer_thread)
            
            # Record event
            self.events.append({
                "event": "write_lock_acquired",
                "thread_id": writer_thread,
                "timestamp": timestamp,
                "waited": True,
            })
        
        # Otherwise, grant access to all waiting readers
        elif self.waiting_readers:
            for reader_thread in self.waiting_readers:
                self.readers.add(reader_thread)
                self.reader_count += 1
                self.reader_acquisitions += 1
                unblocked_threads.append(reader_thread)
                
                # Record event
                self.events.append({
                    "event": "read_lock_acquired",
                    "thread_id": reader_thread,
                    "timestamp": timestamp,
                    "reader_count": self.reader_count,
                })
            
            self.waiting_readers = []
        
        return unblocked_threads
    
    def is_reading(self, thread_id: str) -> bool:
        """
        Check if a thread has read access.
        
        Args:
            thread_id: ID of the thread to check
            
        Returns:
            True if the thread has read access
        """
        return thread_id in self.readers
    
    def is_writing(self, thread_id: str) -> bool:
        """
        Check if a thread has write access.
        
        Args:
            thread_id: ID of the thread to check
            
        Returns:
            True if the thread has write access
        """
        return self.writer == thread_id
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get read-write lock statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "lock_id": self.lock_id,
            "reader_count": self.reader_count,
            "writer": self.writer,
            "waiting_readers": len(self.waiting_readers),
            "waiting_writers": len(self.waiting_writers),
            "reader_acquisitions": self.reader_acquisitions,
            "writer_acquisitions": self.writer_acquisitions,
            "read_contentions": self.read_contentions,
            "write_contentions": self.write_contentions,
            "read_contention_ratio": (
                self.read_contentions / self.reader_acquisitions
                if self.reader_acquisitions > 0 else 0.0
            ),
            "write_contention_ratio": (
                self.write_contentions / self.writer_acquisitions
                if self.writer_acquisitions > 0 else 0.0
            ),
        }


class Semaphore:
    """Counting semaphore implementation."""
    
    def __init__(self, semaphore_id: int, permits: int = 1):
        """
        Initialize a semaphore.
        
        Args:
            semaphore_id: Unique identifier for the semaphore
            permits: Initial number of permits available
        """
        self.semaphore_id = semaphore_id
        self.permits = permits
        self.max_permits = permits
        # List of tuples (thread_id, permits_requested)
        self.waiting_threads: List[Tuple[str, int]] = []
        self.acquisitions = 0
        self.contentions = 0
        self.events: List[Dict[str, Any]] = []
        self.state = (
            SemaphoreState.AVAILABLE if permits > 0 else SemaphoreState.UNAVAILABLE
        )
    
    def acquire(self, thread_id: str, count: int, timestamp: int) -> bool:
        """
        Attempt to acquire permits from the semaphore.
        
        Args:
            thread_id: ID of the thread attempting to acquire
            count: Number of permits to acquire
            timestamp: Current global clock value
            
        Returns:
            True if acquired, False if needs to wait
        """
        if count <= 0:
            raise ValueError(f"Cannot acquire {count} permits")
        
        if count > self.max_permits:
            raise ValueError(
                f"Cannot acquire {count} permits when max is {self.max_permits}"
            )
        
        if self.permits >= count:
            # Enough permits available
            self.permits -= count
            self.acquisitions += 1
            
            if self.permits == 0:
                self.state = SemaphoreState.UNAVAILABLE
            
            # Record event
            self.events.append({
                "event": "semaphore_acquired",
                "thread_id": thread_id,
                "timestamp": timestamp,
                "permits_acquired": count,
                "permits_remaining": self.permits,
                "contended": False,
            })
            
            return True
        
        # Not enough permits, add to waiting list if not already there
        if not any(tid == thread_id for tid, _ in self.waiting_threads):
            self.waiting_threads.append((thread_id, count))
            self.contentions += 1
            
            # Record event
            self.events.append({
                "event": "semaphore_contention",
                "thread_id": thread_id,
                "timestamp": timestamp,
                "permits_requested": count,
                "permits_available": self.permits,
            })
        
        return False
    
    def release(self, thread_id: str, count: int, timestamp: int) -> List[str]:
        """
        Release permits back to the semaphore.
        
        Args:
            thread_id: ID of the thread releasing permits
            count: Number of permits to release
            timestamp: Current global clock value
            
        Returns:
            List of thread IDs that now get permits
        """
        if count <= 0:
            raise ValueError(f"Cannot release {count} permits")
        
        # Update permits
        old_permits = self.permits
        self.permits += count
        
        # Ensure we don't exceed max permits
        if self.permits > self.max_permits:
            self.permits = self.max_permits
        
        # Update state
        if old_permits == 0 and self.permits > 0:
            self.state = SemaphoreState.AVAILABLE
        
        # Record event
        self.events.append({
            "event": "semaphore_released",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "permits_released": count,
            "permits_available": self.permits,
            "waiting_threads": len(self.waiting_threads),
        })
        
        # If there are waiting threads, try to satisfy them
        unblocked_threads = []
        if self.waiting_threads and self.permits > 0:
            permits_to_distribute = self.permits
            
            # Try to satisfy waiting threads one by one
            idx = 0
            while idx < len(self.waiting_threads) and permits_to_distribute > 0:
                waiting_thread_id, permits_needed = self.waiting_threads[idx]
                
                # If we have enough permits for this thread
                if permits_to_distribute >= permits_needed:
                    # Remove this thread from waiting list
                    self.waiting_threads.pop(idx)
                    
                    # Unblock the thread
                    unblocked_threads.append(waiting_thread_id)
                    
                    # Distribute permits
                    permits_to_distribute -= permits_needed
                    self.acquisitions += 1
                    
                    # Record event
                    self.events.append({
                        "event": "semaphore_acquired",
                        "thread_id": waiting_thread_id,
                        "timestamp": timestamp,
                        "permits_acquired": permits_needed,
                        "permits_remaining": permits_to_distribute,
                        "contended": True,
                    })
                else:
                    # Not enough permits for this thread, try the next one
                    idx += 1
            
            # Update permits
            self.permits = permits_to_distribute
            
            if self.permits == 0:
                self.state = SemaphoreState.UNAVAILABLE
        
        return unblocked_threads
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get semaphore statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "semaphore_id": self.semaphore_id,
            "permits": self.permits,
            "max_permits": self.max_permits,
            "state": self.state.name,
            "waiting_threads": len(self.waiting_threads),
            "acquisitions": self.acquisitions,
            "contentions": self.contentions,
            "contention_ratio": (
                self.contentions / self.acquisitions if self.acquisitions > 0 else 0.0
            ),
        }


class Barrier:
    """Thread barrier implementation."""
    
    def __init__(self, barrier_id: int, parties: int):
        """
        Initialize a barrier.
        
        Args:
            barrier_id: Unique identifier for the barrier
            parties: Number of threads that must arrive before the barrier opens
        """
        self.barrier_id = barrier_id
        self.parties = parties
        self.waiting_threads: Set[str] = set()
        self.generation = 0  # Incremented each time the barrier trips
        self.state = BarrierState.WAITING
        self.events: List[Dict[str, Any]] = []
    
    def arrive(self, thread_id: str, timestamp: int) -> bool:
        """
        Register a thread's arrival at the barrier.
        
        Args:
            thread_id: ID of the thread arriving
            timestamp: Current global clock value
            
        Returns:
            True if this thread made the barrier trip, False otherwise
        """
        if thread_id in self.waiting_threads:
            raise ValueError(f"Thread {thread_id} already at barrier {self.barrier_id}")
        
        # Add thread to waiting set
        self.waiting_threads.add(thread_id)
        
        # Record event
        self.events.append({
            "event": "barrier_arrival",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "waiting_count": len(self.waiting_threads),
            "parties": self.parties,
        })
        
        # Check if barrier should trip
        if len(self.waiting_threads) >= self.parties:
            self.state = BarrierState.OPEN
            self.generation += 1
            
            # Record event
            self.events.append({
                "event": "barrier_tripped",
                "thread_id": thread_id,  # Last thread to arrive
                "timestamp": timestamp,
                "generation": self.generation,
            })
            
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset the barrier for reuse."""
        self.waiting_threads.clear()
        self.state = BarrierState.WAITING
    
    def is_waiting(self, thread_id: str) -> bool:
        """
        Check if a thread is waiting at the barrier.
        
        Args:
            thread_id: ID of the thread to check
            
        Returns:
            True if the thread is waiting
        """
        return thread_id in self.waiting_threads
    
    def get_waiting_count(self) -> int:
        """
        Get the number of threads waiting at the barrier.
        
        Returns:
            Number of waiting threads
        """
        return len(self.waiting_threads)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get barrier statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "barrier_id": self.barrier_id,
            "parties": self.parties,
            "waiting_count": len(self.waiting_threads),
            "state": self.state.name,
            "generation": self.generation,
        }


class CountDownLatch:
    """Count-down latch implementation."""
    
    def __init__(self, latch_id: int, count: int):
        """
        Initialize a count-down latch.
        
        Args:
            latch_id: Unique identifier for the latch
            count: Initial count value
        """
        self.latch_id = latch_id
        self.count = count
        self.initial_count = count
        self.waiting_threads: Set[str] = set()
        self.events: List[Dict[str, Any]] = []
    
    def count_down(self, thread_id: str, timestamp: int) -> bool:
        """
        Decrement the count and return whether it reached zero.
        
        Args:
            thread_id: ID of the thread counting down
            timestamp: Current global clock value
            
        Returns:
            True if the count reached zero, False otherwise
        """
        if self.count <= 0:
            return True
        
        self.count -= 1
        
        # Record event
        self.events.append({
            "event": "latch_countdown",
            "thread_id": thread_id,
            "timestamp": timestamp,
            "new_count": self.count,
            "waiting_threads": len(self.waiting_threads),
        })
        
        return self.count == 0
    
    def await_latch(self, thread_id: str, timestamp: int) -> bool:
        """
        Wait for the latch to reach zero.
        
        Args:
            thread_id: ID of the thread waiting
            timestamp: Current global clock value
            
        Returns:
            True if the latch is already at zero, False if it needs to wait
        """
        if self.count <= 0:
            return True
        
        # Add thread to waiting set if not already there
        if thread_id not in self.waiting_threads:
            self.waiting_threads.add(thread_id)
            
            # Record event
            self.events.append({
                "event": "latch_await",
                "thread_id": thread_id,
                "timestamp": timestamp,
                "current_count": self.count,
            })
        
        return False
    
    def is_completed(self) -> bool:
        """
        Check if the latch has reached zero.
        
        Returns:
            True if the count is zero
        """
        return self.count <= 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get latch statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "latch_id": self.latch_id,
            "current_count": self.count,
            "initial_count": self.initial_count,
            "is_completed": self.is_completed(),
            "waiting_threads": len(self.waiting_threads),
        }