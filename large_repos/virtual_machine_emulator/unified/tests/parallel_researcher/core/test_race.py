"""Tests for race condition detection functionality."""

import pytest

from vm_emulator.core.race import RaceDetector, RaceType


class TestRaceDetector:
    """Test the race condition detector."""
    
    def test_initialization(self):
        """Test race detector initialization."""
        detector = RaceDetector()
        
        assert len(detector.memory_accesses) == 0
        assert len(detector.sync_operations) == 0
        assert len(detector.race_conditions) == 0
        assert len(detector.happens_before) == 0
        assert len(detector.thread_locks) == 0
        assert len(detector.atomic_regions) == 0
    
    def test_memory_access_recording(self):
        """Test recording memory accesses."""
        detector = RaceDetector()
        
        # Record some memory accesses
        detector.record_memory_access(
            address=100,
            access_type="read",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=42,
        )
        
        # Check that accesses were recorded
        assert len(detector.memory_accesses) == 1
        assert 100 in detector.memory_accesses
        assert len(detector.memory_accesses[100]) == 2
        
        # Check access details
        access1 = detector.memory_accesses[100][0]
        access2 = detector.memory_accesses[100][1]
        
        assert access1["address"] == 100
        assert access1["type"] == "read"
        assert access1["thread_id"] == "thread1"
        assert access1["timestamp"] == 0
        assert access1["processor_id"] == 0
        
        assert access2["address"] == 100
        assert access2["type"] == "write"
        assert access2["thread_id"] == "thread2"
        assert access2["timestamp"] == 1
        assert access2["processor_id"] == 1
        assert access2["value"] == 42
    
    def test_sync_operation_recording(self):
        """Test recording synchronization operations."""
        detector = RaceDetector()
        
        # Record some synchronization operations
        detector.record_sync_operation(
            operation="acquire",
            thread_id="thread1",
            timestamp=0,
            sync_object_id=1,
            sync_type="lock",
            processor_id=0,
        )
        
        detector.record_sync_operation(
            operation="release",
            thread_id="thread1",
            timestamp=1,
            sync_object_id=1,
            sync_type="lock",
            processor_id=0,
        )
        
        # Check that operations were recorded
        assert "thread1" in detector.sync_operations
        assert len(detector.sync_operations["thread1"]) == 2
        
        # Check operation details
        op1 = detector.sync_operations["thread1"][0]
        op2 = detector.sync_operations["thread1"][1]
        
        assert op1["operation"] == "acquire"
        assert op1["thread_id"] == "thread1"
        assert op1["timestamp"] == 0
        assert op1["sync_object_id"] == 1
        assert op1["sync_type"] == "lock"
        assert op1["processor_id"] == 0
        
        assert op2["operation"] == "release"
        assert op2["timestamp"] == 1
    
    def test_read_write_race_detection(self):
        """Test detecting read-write race conditions."""
        detector = RaceDetector()
        
        # Simulate two threads accessing the same address without synchronization
        detector.record_memory_access(
            address=100,
            access_type="read",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=42,
        )
        
        # Check that a race condition was detected
        assert len(detector.race_conditions) == 1
        race = detector.race_conditions[0]
        
        assert race["type"] == RaceType.READ_WRITE.name
        assert race["address"] == 100
        assert race["thread1"] == "thread1"
        assert race["thread2"] == "thread2"
        assert race["has_common_lock"] is False
    
    def test_write_write_race_detection(self):
        """Test detecting write-write race conditions."""
        detector = RaceDetector()
        
        # Simulate two threads writing to the same address without synchronization
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
            value=42,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=43,
        )
        
        # Check that a race condition was detected
        assert len(detector.race_conditions) == 1
        race = detector.race_conditions[0]
        
        assert race["type"] == RaceType.WRITE_WRITE.name
        assert race["address"] == 100
        assert race["thread1"] == "thread1"
        assert race["thread2"] == "thread2"
    
    def test_lock_protection(self):
        """Test that locks protect against race conditions."""
        detector = RaceDetector()
        
        # Thread1 accesses with lock
        detector.record_sync_operation(
            operation="acquire",
            thread_id="thread1",
            timestamp=0,
            sync_object_id=1,
            sync_type="lock",
            processor_id=0,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread1",
            timestamp=1,
            processor_id=0,
            value=42,
            lock_set={1},  # Thread holds lock 1
        )
        
        detector.record_sync_operation(
            operation="release",
            thread_id="thread1",
            timestamp=2,
            sync_object_id=1,
            sync_type="lock",
            processor_id=0,
        )
        
        # Thread2 accesses with the same lock
        detector.record_sync_operation(
            operation="acquire",
            thread_id="thread2",
            timestamp=3,
            sync_object_id=1,
            sync_type="lock",
            processor_id=1,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=4,
            processor_id=1,
            value=43,
            lock_set={1},  # Thread holds lock 1
        )
        
        # No race condition should be detected because both accesses are protected by the same lock
        assert len(detector.race_conditions) == 0
    
    def test_happens_before_relation(self):
        """Test happens-before relationship between threads."""
        detector = RaceDetector()
        
        # Thread1 releases a lock
        detector.record_sync_operation(
            operation="release",
            thread_id="thread1",
            timestamp=0,
            sync_object_id=1,
            sync_type="lock",
            processor_id=0,
        )
        
        # Thread2 acquires the same lock later
        detector.record_sync_operation(
            operation="acquire",
            thread_id="thread2",
            timestamp=1,
            sync_object_id=1,
            sync_type="lock",
            processor_id=1,
        )
        
        # Thread1 accesses memory
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread1",
            timestamp=0,  # Before release
            processor_id=0,
            value=42,
        )
        
        # Thread2 accesses same memory
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=2,  # After acquire
            processor_id=1,
            value=43,
        )
        
        # Check happens-before relationship is established
        assert "thread1" in detector.happens_before
        assert "thread2" in detector.happens_before["thread1"]
        
        # No race condition should be detected because of happens-before relationship
        assert len(detector.race_conditions) == 0
    
    def test_atomicity_violation(self):
        """Test detecting atomicity violations."""
        detector = RaceDetector()
        
        # Define atomic region for thread1
        detector.define_atomic_region(
            thread_id="thread1",
            start_address=100,
            end_address=105,
        )
        
        # Thread1 accesses memory in atomic region
        detector.record_memory_access(
            address=102,  # Within atomic region
            access_type="read",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
        )
        
        # Thread2 accesses memory in thread1's atomic region
        detector.record_memory_access(
            address=102,  # Within atomic region
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=42,
        )
        
        # Check that an atomicity violation was detected
        assert len(detector.race_conditions) == 1
        race = detector.race_conditions[0]
        
        assert race["type"] == RaceType.ATOMICITY_VIOLATION.name
        assert race["address"] == 102
        assert race["thread1"] == "thread1"
        assert race["thread2"] == "thread2"
    
    def test_deadlock_detection(self):
        """Test detecting deadlocks."""
        detector = RaceDetector()
        
        # Create a deadlock scenario
        # Thread1 holds lock1, waiting for lock2
        # Thread2 holds lock2, waiting for lock1
        waiting_graph = {
            "thread1": [("thread2", 2)],  # thread1 waiting for lock2 held by thread2
            "thread2": [("thread1", 1)],  # thread2 waiting for lock1 held by thread1
        }
        
        # Check for deadlocks
        detector.check_deadlocks(waiting_graph)
        
        # Verify deadlock detection
        assert len(detector.race_conditions) == 1
        race = detector.race_conditions[0]
        
        assert race["type"] == RaceType.DEADLOCK.name
        assert set(race["threads"]) == {"thread1", "thread2"}
    
    def test_order_violation(self):
        """Test detecting order violations."""
        detector = RaceDetector()
        
        # Simulate an order violation:
        # Thread2 reads before thread1 initializes
        detector.record_memory_access(
            address=100,
            access_type="read",
            thread_id="thread2",
            timestamp=0,
            processor_id=1,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",  # Initialization
            thread_id="thread1",
            timestamp=1,
            processor_id=0,
            value=42,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",  # Usage after seeing initialization
            thread_id="thread2",
            timestamp=2,
            processor_id=1,
            value=43,
        )
        
        # Check for order violations
        detector.check_order_violations()
        
        # Verify order violation detection
        assert len(detector.race_conditions) > 0
        
        # Find order violation
        order_violations = [r for r in detector.race_conditions if r["type"] == RaceType.ORDER_VIOLATION.name]
        assert len(order_violations) > 0
    
    def test_filtering_results(self):
        """Test filtering race condition results."""
        detector = RaceDetector()
        
        # Create some race conditions
        detector.record_memory_access(
            address=100,
            access_type="read",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=42,
        )
        
        detector.record_memory_access(
            address=200,
            access_type="write",
            thread_id="thread1",
            timestamp=2,
            processor_id=0,
            value=43,
        )
        
        detector.record_memory_access(
            address=200,
            access_type="write",
            thread_id="thread3",
            timestamp=3,
            processor_id=2,
            value=44,
        )
        
        # Check filtering by race type
        read_write_races = detector.get_race_conditions(race_type=RaceType.READ_WRITE)
        assert len(read_write_races) == 1
        assert read_write_races[0]["address"] == 100
        
        write_write_races = detector.get_race_conditions(race_type=RaceType.WRITE_WRITE)
        assert len(write_write_races) == 1
        assert write_write_races[0]["address"] == 200
        
        # Check filtering by address
        addr100_races = detector.get_race_conditions(address=100)
        assert len(addr100_races) == 1
        assert addr100_races[0]["thread1"] == "thread1"
        assert addr100_races[0]["thread2"] == "thread2"
        
        # Check filtering by thread
        thread1_races = detector.get_race_conditions(thread_id="thread1")
        assert len(thread1_races) == 2
        
        thread3_races = detector.get_race_conditions(thread_id="thread3")
        assert len(thread3_races) == 1
        assert thread3_races[0]["address"] == 200
    
    def test_statistics(self):
        """Test race detection statistics."""
        detector = RaceDetector()
        
        # Create some race conditions
        detector.record_memory_access(
            address=100,
            access_type="read",
            thread_id="thread1",
            timestamp=0,
            processor_id=0,
        )
        
        detector.record_memory_access(
            address=100,
            access_type="write",
            thread_id="thread2",
            timestamp=1,
            processor_id=1,
            value=42,
        )
        
        detector.record_memory_access(
            address=200,
            access_type="write",
            thread_id="thread1",
            timestamp=2,
            processor_id=0,
            value=43,
        )
        
        detector.record_memory_access(
            address=200,
            access_type="write",
            thread_id="thread3",
            timestamp=3,
            processor_id=2,
            value=44,
        )
        
        # Get statistics
        stats = detector.get_statistics()
        
        assert stats["total_races"] == 2
        assert stats["memory_addresses_monitored"] == 2
        assert stats["total_memory_accesses"] == 4
        assert stats["read_accesses"] == 1
        assert stats["write_accesses"] == 3
        assert stats["threads_monitored"] == 0  # Since we didn't record sync ops
        
        # Check race counts
        assert stats["race_counts"].get(RaceType.READ_WRITE.name) == 1
        assert stats["race_counts"].get(RaceType.WRITE_WRITE.name) == 1


if __name__ == "__main__":
    pytest.main(["-v", "test_race.py"])