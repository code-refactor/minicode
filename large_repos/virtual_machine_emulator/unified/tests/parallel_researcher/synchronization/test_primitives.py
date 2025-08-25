"""Tests for synchronization primitives."""

import pytest

from vm_emulator.synchronization.primitives import (
    Lock, ReentrantLock, ReadWriteLock, Semaphore, Barrier, CountDownLatch,
    LockState, SemaphoreState, BarrierState
)


class TestLock:
    """Test the Lock implementation."""
    
    def test_initialization(self):
        """Test lock initialization."""
        lock = Lock(lock_id=1)
        
        assert lock.lock_id == 1
        assert lock.state == LockState.UNLOCKED
        assert lock.owner is None
        assert len(lock.waiting_threads) == 0
        assert lock.acquisition_count == 0
        assert lock.contention_count == 0
    
    def test_acquire(self):
        """Test acquiring a lock."""
        lock = Lock(lock_id=1)
        
        # First acquisition should succeed
        assert lock.acquire(thread_id="thread1", timestamp=0)
        assert lock.state == LockState.LOCKED
        assert lock.owner == "thread1"
        assert lock.acquisition_count == 1
        assert lock.contention_count == 0
        
        # Second acquisition by different thread should fail
        assert not lock.acquire(thread_id="thread2", timestamp=1)
        assert lock.state == LockState.LOCKED
        assert lock.owner == "thread1"
        assert lock.acquisition_count == 1
        assert lock.contention_count == 1
        assert "thread2" in lock.waiting_threads
    
    def test_release(self):
        """Test releasing a lock."""
        lock = Lock(lock_id=1)
        
        # Acquire the lock
        lock.acquire(thread_id="thread1", timestamp=0)
        
        # Attempt to release by wrong thread should raise ValueError
        with pytest.raises(ValueError):
            lock.release(thread_id="thread2", timestamp=1)
        
        # Release by owner should succeed
        next_thread = lock.release(thread_id="thread1", timestamp=1)
        assert lock.state == LockState.UNLOCKED
        assert lock.owner is None
        assert next_thread is None
    
    def test_contention_and_queuing(self):
        """Test lock contention and waiting thread queuing."""
        lock = Lock(lock_id=1)
        
        # Acquire lock with thread1
        lock.acquire(thread_id="thread1", timestamp=0)
        
        # Try to acquire with thread2 and thread3
        lock.acquire(thread_id="thread2", timestamp=1)
        lock.acquire(thread_id="thread3", timestamp=2)
        
        assert lock.waiting_threads == ["thread2", "thread3"]
        assert lock.contention_count == 2
        
        # Release the lock
        next_thread = lock.release(thread_id="thread1", timestamp=3)
        
        # Check that thread2 got the lock
        assert next_thread == "thread2"
        assert lock.owner == "thread2"
        assert lock.waiting_threads == ["thread3"]
        
        # Release again
        next_thread = lock.release(thread_id="thread2", timestamp=4)
        
        # Check that thread3 got the lock
        assert next_thread == "thread3"
        assert lock.owner == "thread3"
        assert len(lock.waiting_threads) == 0
    
    def test_statistics(self):
        """Test lock statistics."""
        lock = Lock(lock_id=1)
        
        # Simulate some lock activity
        lock.acquire(thread_id="thread1", timestamp=0)
        lock.acquire(thread_id="thread2", timestamp=1)  # Contention
        lock.release(thread_id="thread1", timestamp=2)  # thread2 gets the lock
        lock.release(thread_id="thread2", timestamp=3)
        lock.acquire(thread_id="thread3", timestamp=4)
        lock.release(thread_id="thread3", timestamp=5)
        
        # Get statistics
        stats = lock.get_statistics()
        
        assert stats["lock_id"] == 1
        assert stats["state"] == "UNLOCKED"
        assert stats["owner"] is None
        assert stats["waiting_count"] == 0
        assert stats["acquisition_count"] == 3
        assert stats["contention_count"] == 1
        assert stats["contention_ratio"] == 1 / 3


class TestReentrantLock:
    """Test the ReentrantLock implementation."""
    
    def test_initialization(self):
        """Test reentrant lock initialization."""
        lock = ReentrantLock(lock_id=1)
        
        assert lock.lock_id == 1
        assert lock.state == LockState.UNLOCKED
        assert lock.owner is None
        assert lock.recursion_level == 0
    
    def test_reentrant_acquisition(self):
        """Test reentrant lock acquisition by the same thread."""
        lock = ReentrantLock(lock_id=1)
        
        # First acquisition
        assert lock.acquire(thread_id="thread1", timestamp=0)
        assert lock.state == LockState.LOCKED
        assert lock.owner == "thread1"
        assert lock.recursion_level == 1
        
        # Reentrant acquisition
        assert lock.acquire(thread_id="thread1", timestamp=1)
        assert lock.recursion_level == 2
        
        # Further reentrant acquisition
        assert lock.acquire(thread_id="thread1", timestamp=2)
        assert lock.recursion_level == 3
        
        # Other thread can't acquire
        assert not lock.acquire(thread_id="thread2", timestamp=3)
        assert lock.recursion_level == 3
    
    def test_reentrant_release(self):
        """Test reentrant lock release."""
        lock = ReentrantLock(lock_id=1)
        
        # Multiple acquisitions
        lock.acquire(thread_id="thread1", timestamp=0)
        lock.acquire(thread_id="thread1", timestamp=1)
        lock.acquire(thread_id="thread1", timestamp=2)
        
        assert lock.recursion_level == 3
        
        # First release
        next_thread = lock.release(thread_id="thread1", timestamp=3)
        assert next_thread is None
        assert lock.state == LockState.LOCKED
        assert lock.owner == "thread1"
        assert lock.recursion_level == 2
        
        # Second release
        next_thread = lock.release(thread_id="thread1", timestamp=4)
        assert next_thread is None
        assert lock.recursion_level == 1
        
        # Another thread is waiting
        lock.acquire(thread_id="thread2", timestamp=5)
        
        # Final release
        next_thread = lock.release(thread_id="thread1", timestamp=6)
        assert next_thread == "thread2"
        assert lock.owner == "thread2"
        assert lock.recursion_level == 1
    
    def test_statistics(self):
        """Test reentrant lock statistics."""
        lock = ReentrantLock(lock_id=1)
        
        # Simulate some lock activity
        lock.acquire(thread_id="thread1", timestamp=0)
        lock.acquire(thread_id="thread1", timestamp=1)  # Reentrant
        lock.release(thread_id="thread1", timestamp=2)
        lock.release(thread_id="thread1", timestamp=3)
        
        # Get statistics
        stats = lock.get_statistics()
        
        assert stats["lock_id"] == 1
        assert stats["recursion_level"] == 0


class TestReadWriteLock:
    """Test the ReadWriteLock implementation."""
    
    def test_initialization(self):
        """Test read-write lock initialization."""
        lock = ReadWriteLock(lock_id=1)
        
        assert lock.lock_id == 1
        assert lock.reader_count == 0
        assert len(lock.readers) == 0
        assert lock.writer is None
    
    def test_read_acquisition(self):
        """Test acquiring read locks."""
        lock = ReadWriteLock(lock_id=1)
        
        # First reader
        assert lock.acquire_read(thread_id="reader1", timestamp=0)
        assert lock.reader_count == 1
        assert "reader1" in lock.readers
        
        # Second reader
        assert lock.acquire_read(thread_id="reader2", timestamp=1)
        assert lock.reader_count == 2
        assert "reader2" in lock.readers
        
        # Third reader
        assert lock.acquire_read(thread_id="reader3", timestamp=2)
        assert lock.reader_count == 3
        assert "reader3" in lock.readers
    
    def test_write_acquisition(self):
        """Test acquiring write lock."""
        lock = ReadWriteLock(lock_id=1)
        
        # Writer acquisition
        assert lock.acquire_write(thread_id="writer1", timestamp=0)
        assert lock.writer == "writer1"
        
        # Reader can't acquire while writer holds lock
        assert not lock.acquire_read(thread_id="reader1", timestamp=1)
        assert "reader1" in lock.waiting_readers
        
        # Another writer can't acquire
        assert not lock.acquire_write(thread_id="writer2", timestamp=2)
        assert "writer2" in lock.waiting_writers
    
    def test_read_release(self):
        """Test releasing read locks."""
        lock = ReadWriteLock(lock_id=1)
        
        # Acquire read locks
        lock.acquire_read(thread_id="reader1", timestamp=0)
        lock.acquire_read(thread_id="reader2", timestamp=1)
        
        # Try to acquire write lock
        lock.acquire_write(thread_id="writer1", timestamp=2)
        
        # Release first read lock
        unblocked = lock.release_read(thread_id="reader1", timestamp=3)
        assert len(unblocked) == 0  # Writer not unblocked yet
        assert lock.reader_count == 1
        
        # Release second read lock
        unblocked = lock.release_read(thread_id="reader2", timestamp=4)
        assert unblocked == ["writer1"]  # Writer should be unblocked
        assert lock.writer == "writer1"
    
    def test_write_release(self):
        """Test releasing write lock."""
        lock = ReadWriteLock(lock_id=1)
        
        # Acquire write lock
        lock.acquire_write(thread_id="writer1", timestamp=0)
        
        # Try to acquire read locks
        lock.acquire_read(thread_id="reader1", timestamp=1)
        lock.acquire_read(thread_id="reader2", timestamp=2)
        
        # Release write lock
        unblocked = lock.release_write(thread_id="writer1", timestamp=3)
        
        # Check that readers were unblocked
        assert set(unblocked) == {"reader1", "reader2"}
        assert lock.reader_count == 2
        assert "reader1" in lock.readers
        assert "reader2" in lock.readers
    
    def test_writer_priority(self):
        """Test that writers have priority over readers."""
        lock = ReadWriteLock(lock_id=1)
        
        # Acquire write lock
        lock.acquire_write(thread_id="writer1", timestamp=0)
        
        # Queue up readers and writers
        lock.acquire_read(thread_id="reader1", timestamp=1)
        lock.acquire_write(thread_id="writer2", timestamp=2)
        lock.acquire_read(thread_id="reader2", timestamp=3)
        
        # Release write lock
        unblocked = lock.release_write(thread_id="writer1", timestamp=4)
        
        # Writer2 should get the lock, not the readers
        assert unblocked == ["writer2"]
        assert lock.writer == "writer2"
        assert lock.reader_count == 0
    
    def test_statistics(self):
        """Test read-write lock statistics."""
        lock = ReadWriteLock(lock_id=1)
        
        # Simulate some lock activity
        lock.acquire_read(thread_id="reader1", timestamp=0)
        lock.acquire_read(thread_id="reader2", timestamp=1)
        lock.acquire_write(thread_id="writer1", timestamp=2)  # Waits
        lock.release_read(thread_id="reader1", timestamp=3)
        lock.release_read(thread_id="reader2", timestamp=4)  # Writer1 gets lock
        lock.release_write(thread_id="writer1", timestamp=5)
        
        # Get statistics
        stats = lock.get_statistics()
        
        assert stats["lock_id"] == 1
        assert stats["reader_count"] == 0
        assert stats["writer"] is None
        assert stats["reader_acquisitions"] == 2
        assert stats["writer_acquisitions"] == 1


class TestSemaphore:
    """Test the Semaphore implementation."""
    
    def test_initialization(self):
        """Test semaphore initialization."""
        sem = Semaphore(semaphore_id=1, permits=3)
        
        assert sem.semaphore_id == 1
        assert sem.permits == 3
        assert sem.max_permits == 3
        assert sem.state == SemaphoreState.AVAILABLE
    
    def test_acquisition(self):
        """Test semaphore acquisition."""
        sem = Semaphore(semaphore_id=1, permits=3)
        
        # Acquire 1 permit
        assert sem.acquire(thread_id="thread1", timestamp=0, count=1)
        assert sem.permits == 2
        
        # Acquire 2 permits
        assert sem.acquire(thread_id="thread2", timestamp=1, count=2)
        assert sem.permits == 0
        assert sem.state == SemaphoreState.UNAVAILABLE
        
        # Try to acquire when no permits available
        assert not sem.acquire(thread_id="thread3", timestamp=2, count=1)
        assert any(tid == "thread3" for tid, _ in sem.waiting_threads)
    
    def test_release(self):
        """Test semaphore release."""
        sem = Semaphore(semaphore_id=1, permits=3)
        
        # Acquire all permits
        sem.acquire(thread_id="thread1", timestamp=0, count=3)
        
        # Try to acquire when no permits available
        sem.acquire(thread_id="thread2", timestamp=1, count=1)
        sem.acquire(thread_id="thread3", timestamp=2, count=2)
        
        # Release 1 permit
        unblocked = sem.release(thread_id="thread1", timestamp=3, count=1)
        
        # Check that thread2 got a permit
        assert unblocked == ["thread2"]
        assert sem.permits == 0  # All permits used
        assert any(tid == "thread3" for tid, _ in sem.waiting_threads)  # thread3 still waiting
        
        # Release 2 more permits
        unblocked = sem.release(thread_id="thread1", timestamp=4, count=2)
        
        # Check that thread3 got permits
        assert unblocked == ["thread3"]
        assert sem.permits == 0  # All permits used
    
    def test_statistics(self):
        """Test semaphore statistics."""
        sem = Semaphore(semaphore_id=1, permits=3)
        
        # Simulate some semaphore activity
        sem.acquire(thread_id="thread1", timestamp=0, count=2)
        sem.acquire(thread_id="thread2", timestamp=1, count=1)
        sem.acquire(thread_id="thread3", timestamp=2, count=1)  # Contention
        sem.release(thread_id="thread1", timestamp=3, count=1)  # thread3 gets permit
        
        # Get statistics
        stats = sem.get_statistics()
        
        assert stats["semaphore_id"] == 1
        assert stats["permits"] == 0
        assert stats["max_permits"] == 3
        assert stats["state"] == "UNAVAILABLE"
        assert stats["acquisitions"] == 3
        assert stats["contentions"] == 1


class TestBarrier:
    """Test the Barrier implementation."""
    
    def test_initialization(self):
        """Test barrier initialization."""
        barrier = Barrier(barrier_id=1, parties=3)
        
        assert barrier.barrier_id == 1
        assert barrier.parties == 3
        assert len(barrier.waiting_threads) == 0
        assert barrier.generation == 0
        assert barrier.state == BarrierState.WAITING
    
    def test_arrival(self):
        """Test thread arrivals at barrier."""
        barrier = Barrier(barrier_id=1, parties=3)
        
        # First arrival
        assert not barrier.arrive(thread_id="thread1", timestamp=0)
        assert len(barrier.waiting_threads) == 1
        assert "thread1" in barrier.waiting_threads
        assert barrier.state == BarrierState.WAITING
        
        # Second arrival
        assert not barrier.arrive(thread_id="thread2", timestamp=1)
        assert len(barrier.waiting_threads) == 2
        assert barrier.state == BarrierState.WAITING
        
        # Third arrival should trip the barrier
        assert barrier.arrive(thread_id="thread3", timestamp=2)
        assert barrier.state == BarrierState.OPEN
        assert barrier.generation == 1
    
    def test_reset(self):
        """Test barrier reset."""
        barrier = Barrier(barrier_id=1, parties=3)
        
        # All threads arrive
        barrier.arrive(thread_id="thread1", timestamp=0)
        barrier.arrive(thread_id="thread2", timestamp=1)
        barrier.arrive(thread_id="thread3", timestamp=2)
        
        assert barrier.state == BarrierState.OPEN
        assert barrier.generation == 1
        
        # Reset the barrier
        barrier.reset()
        
        assert len(barrier.waiting_threads) == 0
        assert barrier.state == BarrierState.WAITING
        assert barrier.generation == 1  # Generation not reset
    
    def test_statistics(self):
        """Test barrier statistics."""
        barrier = Barrier(barrier_id=1, parties=3)
        
        # Simulate some barrier activity
        barrier.arrive(thread_id="thread1", timestamp=0)
        barrier.arrive(thread_id="thread2", timestamp=1)
        
        # Get statistics
        stats = barrier.get_statistics()
        
        assert stats["barrier_id"] == 1
        assert stats["parties"] == 3
        assert stats["waiting_count"] == 2
        assert stats["state"] == "WAITING"
        assert stats["generation"] == 0


class TestCountDownLatch:
    """Test the CountDownLatch implementation."""
    
    def test_initialization(self):
        """Test latch initialization."""
        latch = CountDownLatch(latch_id=1, count=3)
        
        assert latch.latch_id == 1
        assert latch.count == 3
        assert latch.initial_count == 3
        assert len(latch.waiting_threads) == 0
    
    def test_count_down(self):
        """Test counting down the latch."""
        latch = CountDownLatch(latch_id=1, count=3)
        
        # First count down
        assert not latch.count_down(thread_id="thread1", timestamp=0)
        assert latch.count == 2
        
        # Second count down
        assert not latch.count_down(thread_id="thread2", timestamp=1)
        assert latch.count == 1
        
        # Third count down should complete
        assert latch.count_down(thread_id="thread3", timestamp=2)
        assert latch.count == 0
    
    def test_await(self):
        """Test waiting for the latch."""
        latch = CountDownLatch(latch_id=1, count=3)
        
        # Thread1 waits
        assert not latch.await_latch(thread_id="thread1", timestamp=0)
        assert "thread1" in latch.waiting_threads
        
        # Thread2 waits
        assert not latch.await_latch(thread_id="thread2", timestamp=1)
        assert "thread2" in latch.waiting_threads
        
        # Thread3 counts down
        latch.count_down(thread_id="thread3", timestamp=2)
        latch.count_down(thread_id="thread3", timestamp=3)
        
        # Thread4 waits
        assert not latch.await_latch(thread_id="thread4", timestamp=4)
        assert "thread4" in latch.waiting_threads
        
        # Final count down
        latch.count_down(thread_id="thread3", timestamp=5)
        
        # New thread should not wait
        assert latch.await_latch(thread_id="thread5", timestamp=6)
    
    def test_statistics(self):
        """Test latch statistics."""
        latch = CountDownLatch(latch_id=1, count=3)
        
        # Simulate some latch activity
        latch.await_latch(thread_id="thread1", timestamp=0)
        latch.count_down(thread_id="thread2", timestamp=1)
        latch.count_down(thread_id="thread2", timestamp=2)
        
        # Get statistics
        stats = latch.get_statistics()
        
        assert stats["latch_id"] == 1
        assert stats["current_count"] == 1
        assert stats["initial_count"] == 3
        assert stats["is_completed"] is False
        assert stats["waiting_threads"] == 1


if __name__ == "__main__":
    pytest.main(["-v", "test_primitives.py"])