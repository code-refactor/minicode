"""
Tests for the playtest recorder module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gamevault.playtest_recorder.recorder import PlaytestRecorder


@pytest.fixture
def playtest_recorder():
    """Create a PlaytestRecorder with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        recorder = PlaytestRecorder("test_project", temp_dir)
        yield recorder


def test_start_session(playtest_recorder):
    """Test starting a new playtest session."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456",
        initial_metrics={"score": 0, "health": 100}
    )
    
    # Verify the session was created
    assert session_id is not None
    
    # Verify the session exists in storage
    session = playtest_recorder.get_session(session_id)
    assert session is not None
    assert session.version_id == "version123"
    assert session.player_id == "player456"
    assert session.metrics == {"score": 0, "health": 100}
    assert not session.completed
    assert len(session.events) == 0


def test_end_session(playtest_recorder):
    """Test ending a playtest session."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456"
    )
    
    # End the session
    result = playtest_recorder.end_session(session_id)
    assert result is True
    
    # Verify the session is marked as completed
    session = playtest_recorder.get_session(session_id)
    assert session.completed
    
    # Try to end a non-existent session
    result = playtest_recorder.end_session("nonexistent")
    assert result is False


def test_record_event(playtest_recorder):
    """Test recording a gameplay event."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456"
    )
    
    # Record an event
    event_type = "enemy_defeated"
    event_data = {"enemy_id": "goblin_1", "position": {"x": 100, "y": 200}}
    
    result = playtest_recorder.record_event(session_id, event_type, event_data)
    assert result is True
    
    # Verify the event was recorded
    session = playtest_recorder.get_session(session_id)
    assert len(session.events) == 1
    assert session.events[0]["type"] == event_type
    assert session.events[0]["data"] == event_data
    
    # Record another event
    playtest_recorder.record_event(
        session_id,
        "item_collected",
        {"item_id": "health_potion"}
    )
    
    # Verify both events are recorded
    session = playtest_recorder.get_session(session_id)
    assert len(session.events) == 2
    
    # Try to record an event for a non-existent session
    result = playtest_recorder.record_event("nonexistent", "test", {})
    assert result is False


def test_update_metrics(playtest_recorder):
    """Test updating session metrics."""
    # Start a session with initial metrics
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456",
        initial_metrics={"score": 0, "health": 100}
    )
    
    # Update metrics
    new_metrics = {"score": 50, "enemies_defeated": 5}
    result = playtest_recorder.update_metrics(session_id, new_metrics)
    assert result is True
    
    # Verify metrics were updated
    session = playtest_recorder.get_session(session_id)
    assert session.metrics["score"] == 50
    assert session.metrics["health"] == 100
    assert session.metrics["enemies_defeated"] == 5
    
    # Try to update metrics for a non-existent session
    result = playtest_recorder.update_metrics("nonexistent", {})
    assert result is False


def test_save_and_get_checkpoint(playtest_recorder):
    """Test saving and retrieving checkpoint data."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456"
    )
    
    # Create checkpoint data
    checkpoint_data = b"BINARY_CHECKPOINT_DATA"
    
    # Save the checkpoint
    checkpoint_id = playtest_recorder.save_checkpoint(
        session_id,
        checkpoint_data,
        "Level 1 completion"
    )
    
    # Verify checkpoint was created
    assert checkpoint_id is not None
    
    # Get the checkpoint
    checkpoint_result = playtest_recorder.get_checkpoint(checkpoint_id)
    
    # Verify checkpoint data
    assert checkpoint_result is not None
    data, metadata = checkpoint_result
    
    assert data == checkpoint_data
    assert metadata["session_id"] == session_id
    assert metadata["description"] == "Level 1 completion"
    
    # Verify checkpoint was added to the session
    session = playtest_recorder.get_session(session_id)
    assert checkpoint_id in session.checkpoint_ids
    
    # Try to save a checkpoint for a non-existent session
    result = playtest_recorder.save_checkpoint("nonexistent", b"data", "desc")
    assert result is None


def test_list_sessions(playtest_recorder):
    """Test listing playtest sessions."""
    # Create multiple sessions
    session1_id = playtest_recorder.start_session("version1", "player1")
    session2_id = playtest_recorder.start_session("version1", "player2")
    session3_id = playtest_recorder.start_session("version2", "player1")
    
    # Mark one session as completed
    playtest_recorder.end_session(session2_id)
    
    # List all sessions
    all_sessions = playtest_recorder.list_sessions()
    assert len(all_sessions) == 3
    
    # List with filtering
    version1_sessions = playtest_recorder.list_sessions(version_id="version1")
    assert len(version1_sessions) == 2
    
    player1_sessions = playtest_recorder.list_sessions(player_id="player1")
    assert len(player1_sessions) == 2
    
    completed_sessions = playtest_recorder.list_sessions(completed=True)
    assert len(completed_sessions) == 1
    assert completed_sessions[0]["id"] == session2_id


def test_delete_session(playtest_recorder):
    """Test deleting a playtest session."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456"
    )
    
    # Verify it exists
    assert playtest_recorder.get_session(session_id) is not None
    
    # Delete the session
    result = playtest_recorder.delete_session(session_id)
    assert result is True
    
    # Verify it was deleted
    assert playtest_recorder.get_session(session_id) is None
    
    # Try to delete a non-existent session
    result = playtest_recorder.delete_session("nonexistent")
    assert result is False


def test_get_analyzer(playtest_recorder):
    """Test getting the playtest analyzer."""
    analyzer = playtest_recorder.get_analyzer()
    assert analyzer is not None
    assert analyzer.storage == playtest_recorder.storage


def test_active_session_buffering(playtest_recorder):
    """Test the buffering of events and metrics for active sessions."""
    # Start a session
    session_id = playtest_recorder.start_session(
        version_id="version123",
        player_id="player456"
    )
    
    # Verify session is in active sessions
    assert session_id in playtest_recorder.active_sessions
    
    # Record events and metrics without flushing
    for i in range(5):
        playtest_recorder.record_event(
            session_id,
            f"event_{i}",
            {"data": i}
        )
    
    playtest_recorder.update_metrics(
        session_id,
        {"score": 100}
    )
    
    # Verify buffer contains the events and metrics
    assert len(playtest_recorder.active_sessions[session_id]["events_buffer"]) == 5
    assert playtest_recorder.active_sessions[session_id]["metrics_buffer"] == {"score": 100}
    
    # Force flush by getting the session
    session = playtest_recorder.get_session(session_id)
    
    # Verify events and metrics were applied
    assert len(session.events) == 5
    assert session.metrics["score"] == 100
    
    # Verify buffers were cleared
    assert len(playtest_recorder.active_sessions[session_id]["events_buffer"]) == 0
    assert playtest_recorder.active_sessions[session_id]["metrics_buffer"] == {}