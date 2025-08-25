"""Tests for scheduler implementations."""

import pytest

from vm_emulator.scheduling.scheduler import (
    Scheduler, RoundRobinScheduler, PriorityScheduler, 
    ShortestJobFirstScheduler, MultiLevelFeedbackQueueScheduler,
    AffinityScheduler, DeterministicScheduler, SchedulingPolicy
)
from vm_emulator.core.processor import ProcessorState
from vm_emulator.threading.thread import Thread, ThreadPriority


# Helper functions to create test threads
def create_test_thread(thread_id, priority=ThreadPriority.NORMAL, state=ProcessorState.WAITING):
    """Create a test thread with given ID and priority."""
    thread = Thread(
        thread_id=thread_id,
        program_id="test_program",
        pc=0,
        priority=priority,
        state=state,
    )
    return thread


class MockProcessor:
    """Mock processor for testing schedulers."""
    
    def __init__(self, processor_id):
        """Initialize the mock processor."""
        self.processor_id = processor_id
        self.state = ProcessorState.IDLE
        self.current_thread_id = None
    
    def is_busy(self):
        """Check if the processor is busy."""
        return self.state != ProcessorState.IDLE


class TestRoundRobinScheduler:
    """Test the round-robin scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = RoundRobinScheduler(num_processors=2, time_slice=10, random_seed=42)
        
        assert scheduler.num_processors == 2
        assert scheduler.time_slice == 10
        assert scheduler.random_seed == 42
    
    def test_select_thread(self):
        """Test thread selection."""
        scheduler = RoundRobinScheduler(num_processors=2, time_slice=10)
        
        # Create some test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        thread3 = create_test_thread("thread3")
        
        available_threads = [thread1, thread2, thread3]
        
        # Round robin should select the first thread
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected == thread1
        
        # If thread1 is removed, should select thread2
        available_threads = [thread2, thread3]
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=1)
        assert selected == thread2
    
    def test_should_preempt(self):
        """Test preemption decision."""
        scheduler = RoundRobinScheduler(num_processors=2, time_slice=3)
        
        # Create a test thread
        thread = create_test_thread("thread1", state=ProcessorState.RUNNING)
        
        # First two cycles, should not preempt
        assert not scheduler.should_preempt(thread, [], 0)
        assert not scheduler.should_preempt(thread, [], 1)
        
        # On third cycle, should preempt
        assert scheduler.should_preempt(thread, [], 2)
        
        # Time slice should reset
        assert not scheduler.should_preempt(thread, [], 3)
    
    def test_schedule(self):
        """Test full scheduling cycle."""
        scheduler = RoundRobinScheduler(num_processors=2, time_slice=10)
        
        # Create threads and processors
        threads = {
            "thread1": create_test_thread("thread1"),
            "thread2": create_test_thread("thread2"),
            "thread3": create_test_thread("thread3"),
        }
        
        processors = [MockProcessor(0), MockProcessor(1)]
        ready_queue = ["thread1", "thread2", "thread3"]
        
        # Schedule threads
        assignments, new_queue = scheduler.schedule(
            threads, ready_queue, processors, timestamp=0
        )
        
        # Check assignments
        assert assignments[0] == "thread1"
        assert assignments[1] == "thread2"
        
        # Check processors
        assert processors[0].current_thread_id == "thread1"
        assert processors[0].state == ProcessorState.RUNNING
        assert processors[1].current_thread_id == "thread2"
        assert processors[1].state == ProcessorState.RUNNING
        
        # Check remaining queue
        assert new_queue == ["thread3"]
    
    def test_statistics(self):
        """Test scheduler statistics."""
        scheduler = RoundRobinScheduler(num_processors=2, time_slice=10)
        
        # Simulate some scheduling
        threads = {
            "thread1": create_test_thread("thread1"),
            "thread2": create_test_thread("thread2"),
        }
        
        processors = [MockProcessor(0), MockProcessor(1)]
        ready_queue = ["thread1", "thread2"]
        
        # Do scheduling
        scheduler.schedule(threads, ready_queue, processors, timestamp=0)
        
        # Check statistics
        stats = scheduler.get_statistics()
        
        assert stats["policy"] == "RoundRobinScheduler"
        assert stats["time_slice"] == 10
        assert stats["schedule_calls"] == 1
        assert stats["context_switches"] == 2
        assert stats["num_processors"] == 2


class TestPriorityScheduler:
    """Test the priority-based scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = PriorityScheduler(
            num_processors=2, time_slice=10, random_seed=42, preemptive=True
        )
        
        assert scheduler.num_processors == 2
        assert scheduler.time_slice == 10
        assert scheduler.random_seed == 42
        assert scheduler.preemptive is True
    
    def test_select_thread_by_priority(self):
        """Test thread selection based on priority."""
        scheduler = PriorityScheduler(num_processors=2, time_slice=10)
        
        # Create threads with different priorities
        thread1 = create_test_thread("thread1", priority=ThreadPriority.NORMAL)
        thread2 = create_test_thread("thread2", priority=ThreadPriority.HIGH)
        thread3 = create_test_thread("thread3", priority=ThreadPriority.LOW)
        
        available_threads = [thread1, thread2, thread3]
        
        # Should select thread2 (HIGH priority)
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected == thread2
        
        # If thread2 is removed, should select thread1 (NORMAL priority)
        available_threads = [thread1, thread3]
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=1)
        assert selected == thread1
        
        # If thread1 is removed, should select thread3 (LOW priority)
        available_threads = [thread3]
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=2)
        assert selected == thread3
    
    def test_preemptive_scheduling(self):
        """Test preemptive scheduling based on priority."""
        scheduler = PriorityScheduler(num_processors=2, time_slice=10, preemptive=True)
        
        # Create a running thread with NORMAL priority
        running_thread = create_test_thread(
            "running", priority=ThreadPriority.NORMAL, state=ProcessorState.RUNNING
        )
        
        # Create a higher priority waiting thread
        high_thread = create_test_thread("high", priority=ThreadPriority.HIGH)
        
        # Should preempt the running thread
        assert scheduler.should_preempt(running_thread, [high_thread], 0)
        
        # Create a lower priority waiting thread
        low_thread = create_test_thread("low", priority=ThreadPriority.LOW)
        
        # Should not preempt for lower priority
        assert not scheduler.should_preempt(running_thread, [low_thread], 1)
        
        # Same priority should not preempt until time slice expires
        normal_thread = create_test_thread("normal", priority=ThreadPriority.NORMAL)
        assert not scheduler.should_preempt(running_thread, [normal_thread], 2)
    
    def test_non_preemptive_scheduling(self):
        """Test non-preemptive scheduling."""
        scheduler = PriorityScheduler(num_processors=2, time_slice=3, preemptive=False)
        
        # Create a running thread with LOW priority
        running_thread = create_test_thread(
            "running", priority=ThreadPriority.LOW, state=ProcessorState.RUNNING
        )
        
        # Create a higher priority waiting thread
        high_thread = create_test_thread("high", priority=ThreadPriority.HIGH)
        
        # Should not preempt based on priority if preemptive=False
        assert not scheduler.should_preempt(running_thread, [high_thread], 0)
        assert not scheduler.should_preempt(running_thread, [high_thread], 1)
        
        # Should still preempt after time slice expires
        assert scheduler.should_preempt(running_thread, [high_thread], 2)


class TestShortestJobFirstScheduler:
    """Test the shortest job first scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = ShortestJobFirstScheduler(
            num_processors=2, time_slice=10, estimated_run_times={"thread1": 5, "thread2": 10}
        )
        
        assert scheduler.num_processors == 2
        assert scheduler.time_slice == 10
        assert scheduler.estimated_run_times == {"thread1": 5, "thread2": 10}
    
    def test_select_thread_by_runtime(self):
        """Test thread selection based on estimated runtime."""
        # Create scheduler with estimated runtimes
        estimated_times = {
            "thread1": 30,
            "thread2": 10,
            "thread3": 20,
        }
        
        scheduler = ShortestJobFirstScheduler(
            num_processors=2, time_slice=10, estimated_run_times=estimated_times
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        thread3 = create_test_thread("thread3")
        
        available_threads = [thread1, thread2, thread3]
        
        # Should select thread2 (shortest estimated time)
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected == thread2
        
        # If thread2 is removed, should select thread3
        available_threads = [thread1, thread3]
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=1)
        assert selected == thread3
    
    def test_update_estimated_runtime(self):
        """Test updating estimated runtime."""
        scheduler = ShortestJobFirstScheduler(num_processors=2, time_slice=10)
        
        # Initial estimate
        scheduler.update_estimated_run_time("thread1", 30)
        assert scheduler.estimated_run_times["thread1"] == 30
        
        # Update estimate
        scheduler.update_estimated_run_time("thread1", 15)
        assert scheduler.estimated_run_times["thread1"] == 15


class TestMultiLevelFeedbackQueueScheduler:
    """Test the multi-level feedback queue scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = MultiLevelFeedbackQueueScheduler(
            num_processors=2, time_slice=10, num_queues=3, queue_time_slices=[5, 10, 20]
        )
        
        assert scheduler.num_processors == 2
        assert scheduler.time_slice == 10
        assert scheduler.num_queues == 3
        assert scheduler.queue_time_slices == [5, 10, 20]
    
    def test_queue_assignment(self):
        """Test thread assignment to queues."""
        scheduler = MultiLevelFeedbackQueueScheduler(
            num_processors=2, time_slice=10, num_queues=3
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        available_threads = [thread1, thread2]
        
        # First selection should assign to highest priority queue
        scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert scheduler.thread_queue["thread1"] == 0
        
        scheduler.select_thread(available_threads, processor_id=0, timestamp=1)
        assert scheduler.thread_queue["thread2"] == 0
    
    def test_queue_demotion(self):
        """Test thread demotion to lower priority queues."""
        scheduler = MultiLevelFeedbackQueueScheduler(
            num_processors=2, num_queues=3, queue_time_slices=[2, 4, 8]
        )
        
        # Create a test thread
        thread = create_test_thread("thread1", state=ProcessorState.RUNNING)
        
        # Assign thread to highest priority queue
        scheduler.thread_queue["thread1"] = 0
        
        # First time slice shouldn't preempt
        assert not scheduler.should_preempt(thread, [], 0)
        assert not scheduler.should_preempt(thread, [], 1)
        
        # After time slice expires, should preempt and demote
        assert scheduler.should_preempt(thread, [], 2)
        
        # Thread should be in the next queue
        assert scheduler.thread_queue["thread1"] == 1
        
        # New time slice should be longer
        assert scheduler.time_slice_remaining["thread1"] == 4
    
    def test_queue_priority(self):
        """Test queue priority for selection."""
        scheduler = MultiLevelFeedbackQueueScheduler(
            num_processors=2, time_slice=10, num_queues=3
        )
        
        # Create test threads in different queues
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        thread3 = create_test_thread("thread3")
        
        # Assign threads to different queues
        scheduler.thread_queue["thread1"] = 0  # Highest priority
        scheduler.thread_queue["thread2"] = 1  # Medium priority
        scheduler.thread_queue["thread3"] = 2  # Lowest priority
        
        available_threads = [thread1, thread2, thread3]
        
        # Should select thread1 from highest priority queue
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected == thread1
        
        # If thread1 is removed, should select thread2
        available_threads = [thread2, thread3]
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=1)
        assert selected == thread2
    
    def test_priority_boost(self):
        """Test priority boosting for threads."""
        scheduler = MultiLevelFeedbackQueueScheduler(
            num_processors=2, time_slice=10, num_queues=3
        )
        
        # Assign thread to low priority queue
        scheduler.thread_queue["thread1"] = 2
        
        # Boost priority
        scheduler.boost_priority("thread1")
        
        # Check that thread was moved to a higher priority queue
        assert scheduler.thread_queue["thread1"] == 1
        
        # Boost again to highest priority
        scheduler.boost_priority("thread1")
        assert scheduler.thread_queue["thread1"] == 0
        
        # Boosting highest priority thread should keep it at highest
        scheduler.boost_priority("thread1")
        assert scheduler.thread_queue["thread1"] == 0


class TestAffinityScheduler:
    """Test the processor affinity scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = AffinityScheduler(
            num_processors=4, time_slice=10, default_affinity={0, 1}
        )
        
        assert scheduler.num_processors == 4
        assert scheduler.time_slice == 10
        assert scheduler.default_affinity == {0, 1}
    
    def test_thread_affinity(self):
        """Test thread affinity assignment."""
        scheduler = AffinityScheduler(
            num_processors=4, time_slice=10, default_affinity={0, 1, 2, 3}
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        # Set specific affinity for thread1
        scheduler.set_affinity("thread1", {0, 1})
        
        # Check affinity
        assert scheduler.get_affinity("thread1") == {0, 1}
        
        # Thread2 should get default affinity
        assert scheduler.get_affinity("thread2") == {0, 1, 2, 3}
    
    def test_select_thread_with_affinity(self):
        """Test thread selection based on affinity."""
        scheduler = AffinityScheduler(
            num_processors=4, time_slice=10, default_affinity={0, 1, 2, 3}
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        thread3 = create_test_thread("thread3")
        
        # Set specific affinities
        scheduler.set_affinity("thread1", {0, 2})
        scheduler.set_affinity("thread2", {1, 3})
        scheduler.set_affinity("thread3", {0, 1})
        
        available_threads = [thread1, thread2, thread3]
        
        # For processor 0, should select thread1 or thread3
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected in (thread1, thread3)
        
        # For processor 1, should select thread2 or thread3
        selected = scheduler.select_thread(available_threads, processor_id=1, timestamp=0)
        assert selected in (thread2, thread3)
        
        # For processor 2, should select thread1
        selected = scheduler.select_thread(available_threads, processor_id=2, timestamp=0)
        assert selected == thread1
        
        # For processor 3, should select thread2
        selected = scheduler.select_thread(available_threads, processor_id=3, timestamp=0)
        assert selected == thread2
    
    def test_no_affinity_selection(self):
        """Test selection when no thread has affinity for a processor."""
        scheduler = AffinityScheduler(
            num_processors=4, time_slice=10, default_affinity={0, 1}
        )
        
        # Create test threads with limited affinity
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        scheduler.set_affinity("thread1", {0})
        scheduler.set_affinity("thread2", {1})
        
        available_threads = [thread1, thread2]
        
        # For processor 2, should select None (no thread has affinity)
        selected = scheduler.select_thread(available_threads, processor_id=2, timestamp=0)
        assert selected is None


class TestDeterministicScheduler:
    """Test the deterministic scheduler implementation."""
    
    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = DeterministicScheduler(
            num_processors=2, time_slice=10, random_seed=42, base_policy=SchedulingPolicy.ROUND_ROBIN
        )
        
        assert scheduler.num_processors == 2
        assert scheduler.time_slice == 10
        assert scheduler.random_seed == 42
        assert scheduler.base_policy == SchedulingPolicy.ROUND_ROBIN
        assert scheduler.base_scheduler is not None
    
    def test_deterministic_selection(self):
        """Test deterministic thread selection."""
        scheduler = DeterministicScheduler(
            num_processors=2, time_slice=10, random_seed=42, base_policy=SchedulingPolicy.ROUND_ROBIN
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        available_threads = [thread1, thread2]
        
        # First selection
        selected = scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected == thread1
        
        # This decision should be recorded
        assert (0, 0) in scheduler.decisions
        assert scheduler.decisions[(0, 0)] == "thread1"
        
        # Recreate the scheduler
        scheduler2 = DeterministicScheduler(
            num_processors=2, time_slice=10, random_seed=42, base_policy=SchedulingPolicy.ROUND_ROBIN
        )
        
        # Load decisions
        scheduler2.load_decisions(scheduler.decisions)
        
        # Should make the same selection based on loaded decisions
        selected2 = scheduler2.select_thread(available_threads, processor_id=0, timestamp=0)
        assert selected2 == thread1
    
    def test_record_decisions(self):
        """Test recording scheduling decisions."""
        scheduler = DeterministicScheduler(
            num_processors=2, time_slice=10, random_seed=42
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        available_threads = [thread1, thread2]
        
        # Make some scheduling decisions
        scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        scheduler.select_thread(available_threads, processor_id=1, timestamp=0)
        scheduler.select_thread(available_threads, processor_id=0, timestamp=10)
        
        # Export decisions
        decisions = scheduler.export_decisions()
        
        assert len(decisions) == 3
        assert (0, 0) in decisions
        assert (0, 1) in decisions
        assert (10, 0) in decisions
    
    def test_execution_trace(self):
        """Test execution trace generation."""
        scheduler = DeterministicScheduler(
            num_processors=2, time_slice=10, random_seed=42
        )
        
        # Create test threads
        thread1 = create_test_thread("thread1")
        thread2 = create_test_thread("thread2")
        
        available_threads = [thread1, thread2]
        
        # Make some scheduling decisions
        scheduler.select_thread(available_threads, processor_id=0, timestamp=0)
        scheduler.select_thread(available_threads, processor_id=1, timestamp=0)
        
        # Check execution trace
        trace = scheduler.get_trace()
        
        assert len(trace) == 2
        assert trace[0]["event"] == "select_thread"
        assert trace[0]["processor_id"] == 0
        assert trace[0]["thread_id"] == "thread1"
        
        assert trace[1]["event"] == "select_thread"
        assert trace[1]["processor_id"] == 1
        assert trace[1]["thread_id"] == "thread2"


if __name__ == "__main__":
    pytest.main(["-v", "test_scheduler.py"])