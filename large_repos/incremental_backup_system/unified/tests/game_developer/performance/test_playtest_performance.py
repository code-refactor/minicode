"""
Performance tests for the playtest data recorder.

This module contains tests that verify the playtest data recorder meets the
performance requirements specified in the requirements.
"""

import os
import random
import tempfile
import time
from pathlib import Path

import pytest

from gamevault.models import GameVersionType
from gamevault.playtest_recorder.recorder import PlaytestRecorder


@pytest.fixture
def playtest_recorder():
    """Create a PlaytestRecorder with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        recorder = PlaytestRecorder("perf_test", temp_dir)
        yield recorder


@pytest.fixture
def active_session(playtest_recorder):
    """Create an active playtest session."""
    session_id = playtest_recorder.start_session(
        version_id="test_version",
        player_id="test_player",
        initial_metrics={"score": 0, "health": 100}
    )
    yield session_id


def test_playtest_event_recording_performance(playtest_recorder, active_session):
    """Test performance of recording playtest events."""
    # Generate test events
    event_count = 1000  # A typical 30 minute session might have 1000+ events
    events = []
    
    for i in range(event_count):
        event_type = random.choice([
            "player_move", "enemy_spawn", "item_collect", "weapon_fire",
            "damage_taken", "checkpoint_reached", "menu_open", "menu_close"
        ])
        
        event_data = {
            "timestamp": time.time(),
            "frame": i * 10,
            "position_x": random.uniform(-100, 100),
            "position_y": random.uniform(-100, 100),
            "position_z": random.uniform(-100, 100),
            "value": random.randint(0, 100)
        }
        
        events.append((event_type, event_data))
    
    # Start recording
    start_time = time.time()
    overhead_times = []
    
    for i, (event_type, event_data) in enumerate(events):
        # Simulate game frame time (33ms for 30fps)
        frame_start = time.time()
        
        # Record the event and measure overhead
        event_record_start = time.time()
        playtest_recorder.record_event(active_session, event_type, event_data)
        event_record_time = time.time() - event_record_start
        
        # Calculate overhead as percentage of frame time
        frame_time = time.time() - frame_start
        if frame_time > 0:
            overhead_percent = (event_record_time / 0.033) * 100  # 33ms frame time
            overhead_times.append(overhead_percent)
        
        # Add a small delay to simulate frame time
        time.sleep(0.001)
    
    total_time = time.time() - start_time
    
    # Calculate average overhead
    avg_overhead = sum(overhead_times) / len(overhead_times) if overhead_times else 0
    max_overhead = max(overhead_times) if overhead_times else 0
    
    # Requirement: Playtest data capture must add less than 5% overhead
    print(f"Recorded {event_count} events in {total_time:.2f} seconds")
    print(f"Average overhead: {avg_overhead:.2f}% of frame time")
    print(f"Maximum overhead: {max_overhead:.2f}% of frame time")
    
    # Verify requirement is met
    assert avg_overhead < 5.0, f"Average recording overhead exceeded requirement: {avg_overhead:.2f}% > 5.0%"
    assert max_overhead < 100.0, f"Maximum recording overhead exceeded one frame: {max_overhead:.2f}%"


def test_checkpoint_storage_performance(playtest_recorder, active_session):
    """Test performance of storing game state checkpoints."""
    # Create test checkpoint data of various sizes
    checkpoints = []
    total_size = 0
    
    # 10 checkpoints of increasing size (1KB to 10MB)
    for i in range(10):
        size = 1024 * (2 ** i)  # 1KB, 2KB, 4KB, 8KB, ..., ~10MB
        data = os.urandom(size)
        checkpoints.append((f"checkpoint_{i}", data, f"Checkpoint {i} description"))
        total_size += size
    
    # Store the checkpoints and measure time
    checkpoint_times = []
    
    for name, data, description in checkpoints:
        start_time = time.time()
        playtest_recorder.save_checkpoint(active_session, data, description)
        elapsed = time.time() - start_time
        checkpoint_times.append((len(data), elapsed))
    
    # Calculate overhead per MB
    overhead_per_mb = []
    for size, elapsed in checkpoint_times:
        mb_size = size / (1024 * 1024)
        if mb_size > 0:
            overhead_per_mb.append(elapsed / mb_size)
    
    avg_overhead_per_mb = sum(overhead_per_mb) / len(overhead_per_mb) if overhead_per_mb else 0
    
    # Calculate overhead for a 100MB checkpoint
    projected_overhead_100mb = avg_overhead_per_mb * 100
    
    # Requirement: Add less than 100ms overhead to game frame times
    print(f"Average checkpoint storage overhead: {avg_overhead_per_mb * 1000:.2f} ms/MB")
    print(f"Projected overhead for 100MB checkpoint: {projected_overhead_100mb * 1000:.2f} ms")
    
    # Verify requirement is met
    assert projected_overhead_100mb < 0.1, f"Checkpoint storage overhead too high: {projected_overhead_100mb * 1000:.2f} ms > 100ms for 100MB"


def test_playtest_analysis_performance(playtest_recorder):
    """Test performance of analyzing playtest data."""
    # Create multiple sessions with varying data
    session_count = 20
    session_ids = []
    
    # Generate sessions
    for i in range(session_count):
        session_id = playtest_recorder.start_session(
            version_id=f"version_{i % 3}",
            player_id=f"player_{i % 5}",
            initial_metrics={"score": 0, "health": 100}
        )
        
        # Add varying numbers of events
        event_count = random.randint(50, 200)
        for j in range(event_count):
            playtest_recorder.record_event(
                session_id,
                random.choice(["move", "attack", "item", "death", "respawn"]),
                {"timestamp": j * 0.1, "data": f"Event {j}"}
            )
        
        # Update metrics
        playtest_recorder.update_metrics(
            session_id,
            {
                "score": random.randint(100, 1000),
                "health": random.randint(0, 100),
                "enemies_defeated": random.randint(5, 50),
                "items_collected": random.randint(10, 100),
                "distance_traveled": random.uniform(100, 1000)
            }
        )
        
        # Add checkpoints
        checkpoint_count = random.randint(1, 5)
        for j in range(checkpoint_count):
            playtest_recorder.save_checkpoint(
                session_id,
                os.urandom(1024 * random.randint(1, 10)),
                f"Checkpoint {j}"
            )
        
        # Complete the session
        playtest_recorder.end_session(session_id)
        session_ids.append(session_id)
    
    # Get the analyzer
    analyzer = playtest_recorder.get_analyzer()
    
    # Test session summary performance
    start_time = time.time()
    summary = analyzer.get_session_summary(session_ids[0])
    summary_time = time.time() - start_time
    
    # Test version statistics performance
    start_time = time.time()
    version_stats = analyzer.get_version_statistics("version_0")
    version_stats_time = time.time() - start_time
    
    # Test player statistics performance
    start_time = time.time()
    player_stats = analyzer.get_player_statistics("player_0")
    player_stats_time = time.time() - start_time
    
    # Test session comparison performance
    start_time = time.time()
    comparison = analyzer.compare_sessions(session_ids[:3])
    comparison_time = time.time() - start_time
    
    # Print timing results
    print(f"Session summary time: {summary_time:.6f} seconds")
    print(f"Version statistics time: {version_stats_time:.6f} seconds")
    print(f"Player statistics time: {player_stats_time:.6f} seconds")
    print(f"Session comparison time: {comparison_time:.6f} seconds")
    
    # Requirement: Queries should return results in under 3 seconds
    assert summary_time < 3.0, f"Session summary time exceeded requirement: {summary_time:.2f} > 3.0 seconds"
    assert version_stats_time < 3.0, f"Version statistics time exceeded requirement: {version_stats_time:.2f} > 3.0 seconds"
    assert player_stats_time < 3.0, f"Player statistics time exceeded requirement: {player_stats_time:.2f} > 3.0 seconds"
    assert comparison_time < 3.0, f"Session comparison time exceeded requirement: {comparison_time:.2f} > 3.0 seconds"


def test_high_frequency_event_recording(playtest_recorder, active_session):
    """Test recording events at high frequency to simulate intense gameplay."""
    # Simulate recording events at 60Hz (60 events per second)
    # This would be like recording detailed physics or input data
    event_count = 600  # 10 seconds worth at 60Hz
    events_per_second = 60
    
    # Prepare all events
    events = []
    for i in range(event_count):
        event_data = {
            "timestamp": time.time() + (i / events_per_second),
            "frame": i,
            "position_x": random.uniform(-100, 100),
            "position_y": random.uniform(-100, 100),
            "position_z": random.uniform(-100, 100),
            "velocity_x": random.uniform(-10, 10),
            "velocity_y": random.uniform(-10, 10),
            "velocity_z": random.uniform(-10, 10),
            "rotation": [random.uniform(0, 360) for _ in range(3)],
            "inputs": {
                "forward": random.choice([0, 1]),
                "back": random.choice([0, 1]),
                "left": random.choice([0, 1]),
                "right": random.choice([0, 1]),
                "jump": random.choice([0, 1]),
                "action": random.choice([0, 1])
            }
        }
        events.append(event_data)
    
    # Record events as fast as possible
    start_time = time.time()
    
    for i, event_data in enumerate(events):
        event_type = "high_frequency_data"
        playtest_recorder.record_event(active_session, event_type, event_data)
    
    record_time = time.time() - start_time
    events_per_second_actual = event_count / record_time
    
    # Record metrics
    playtest_recorder.update_metrics(
        active_session,
        {"events_recorded": event_count, "record_time": record_time}
    )
    
    # Get the session data to verify everything was recorded
    session = playtest_recorder.get_session(active_session)
    recorded_count = len(session.events)
    
    # Print results
    print(f"Recorded {recorded_count} events in {record_time:.2f} seconds")
    print(f"Recording rate: {events_per_second_actual:.2f} events/second")
    
    # Verify events were recorded
    assert recorded_count >= event_count, f"Not all events were recorded: {recorded_count} < {event_count}"
    
    # Check if recording rate meets real-time requirements for 60Hz gameplay
    assert events_per_second_actual >= events_per_second, f"Recording rate too slow: {events_per_second_actual:.2f} < {events_per_second} events/second"


def test_large_batch_processing(playtest_recorder):
    """Test processing a large batch of playtest data."""
    # Simulate importing data from an external source
    # Create a large batch of events across multiple sessions
    
    version_id = "batch_test_version"
    session_count = 50
    events_per_session = 200
    
    start_time = time.time()
    
    # Create multiple sessions
    session_ids = []
    for i in range(session_count):
        session_id = playtest_recorder.start_session(
            version_id=version_id,
            player_id=f"batch_player_{i}",
            initial_metrics={"batch": i}
        )
        session_ids.append(session_id)
        
        # Add events to each session
        for j in range(events_per_session):
            playtest_recorder.record_event(
                session_id,
                f"batch_event_{j % 10}",
                {"batch_id": i, "event_id": j, "value": random.random()}
            )
        
        # Complete the session
        playtest_recorder.end_session(session_id)
    
    batch_time = time.time() - start_time
    
    # Calculate processing rate
    total_events = session_count * events_per_session
    events_per_second = total_events / batch_time
    
    # Print results
    print(f"Processed {session_count} sessions with {total_events} events in {batch_time:.2f} seconds")
    print(f"Processing rate: {events_per_second:.2f} events/second")
    
    # Check if we can handle at least 1000 events per second
    assert events_per_second >= 1000, f"Batch processing rate too slow: {events_per_second:.2f} < 1000 events/second"