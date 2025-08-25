"""
Tests for the playtest storage module.
"""

import tempfile
from pathlib import Path

import pytest

from gamevault.models import PlaytestSession
from gamevault.playtest_recorder.storage import PlaytestStorage


@pytest.fixture
def playtest_storage():
    """Create a PlaytestStorage with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = PlaytestStorage("test_project", temp_dir)
        yield storage


@pytest.fixture
def sample_session():
    """Create a sample playtest session for testing."""
    return PlaytestSession(
        id="session123",
        version_id="version456",
        player_id="player789",
        timestamp=1623456789.0,
        duration=600.0,
        completed=False,
        events=[
            {"type": "start", "timestamp": 1623456789.0, "data": {"level": 1}},
            {"type": "enemy_defeated", "timestamp": 1623456889.0, "data": {"enemy_id": "goblin_1"}},
            {"type": "checkpoint", "timestamp": 1623456989.0, "data": {"checkpoint_id": "level1_mid"}}
        ],
        metrics={
            "score": 100,
            "health": 75,
            "enemies_defeated": 5,
            "collectibles_found": 3
        },
        checkpoint_ids=["checkpoint1", "checkpoint2"]
    )


@pytest.fixture
def sample_checkpoint_data():
    """Create sample checkpoint data for testing."""
    return b"BINARY_CHECKPOINT_DATA_FOR_TESTING"


def test_save_and_get_session(playtest_storage, sample_session):
    """Test saving and retrieving a playtest session."""
    # Save the session
    session_id = playtest_storage.save_session(sample_session)
    
    # Verify the session ID matches
    assert session_id == sample_session.id
    
    # Retrieve the session
    retrieved = playtest_storage.get_session(session_id)
    
    # Verify the retrieved data matches
    assert retrieved is not None
    assert retrieved.id == sample_session.id
    assert retrieved.version_id == sample_session.version_id
    assert retrieved.player_id == sample_session.player_id
    assert retrieved.timestamp == sample_session.timestamp
    assert retrieved.duration == sample_session.duration
    assert retrieved.completed == sample_session.completed
    assert len(retrieved.events) == len(sample_session.events)
    assert retrieved.metrics == sample_session.metrics
    assert retrieved.checkpoint_ids == sample_session.checkpoint_ids


def test_delete_session(playtest_storage, sample_session):
    """Test deleting a playtest session."""
    # Save the session
    session_id = playtest_storage.save_session(sample_session)
    
    # Verify it exists
    assert playtest_storage.get_session(session_id) is not None
    
    # Delete the session
    result = playtest_storage.delete_session(session_id)
    assert result is True
    
    # Verify it was deleted
    assert playtest_storage.get_session(session_id) is None
    
    # Try to delete a non-existent session
    result = playtest_storage.delete_session("nonexistent")
    assert result is False


def test_list_sessions(playtest_storage):
    """Test listing playtest sessions with filtering."""
    # Create multiple sessions with different properties
    session1 = PlaytestSession(
        id="session1",
        version_id="version1",
        player_id="player1",
        timestamp=1000.0,
        duration=100.0,
        completed=False,
        events=[],
        metrics={"score": 100},
        checkpoint_ids=[]
    )
    
    session2 = PlaytestSession(
        id="session2",
        version_id="version1",
        player_id="player2",
        timestamp=2000.0,
        duration=200.0,
        completed=True,
        events=[],
        metrics={"score": 200},
        checkpoint_ids=[]
    )
    
    session3 = PlaytestSession(
        id="session3",
        version_id="version2",
        player_id="player1",
        timestamp=3000.0,
        duration=300.0,
        completed=False,
        events=[],
        metrics={"score": 300},
        checkpoint_ids=[]
    )
    
    # Save all sessions
    playtest_storage.save_session(session1)
    playtest_storage.save_session(session2)
    playtest_storage.save_session(session3)
    
    # Test listing all sessions
    all_sessions = playtest_storage.list_sessions()
    assert len(all_sessions) == 3
    
    # Test filtering by version
    version1_sessions = playtest_storage.list_sessions(version_id="version1")
    assert len(version1_sessions) == 2
    assert all(s["version_id"] == "version1" for s in version1_sessions)
    
    # Test filtering by player
    player1_sessions = playtest_storage.list_sessions(player_id="player1")
    assert len(player1_sessions) == 2
    assert all(s["player_id"] == "player1" for s in player1_sessions)
    
    # Test filtering by completion status
    completed_sessions = playtest_storage.list_sessions(completed=True)
    assert len(completed_sessions) == 1
    assert completed_sessions[0]["id"] == "session2"
    
    # Test filtering by timestamp range
    recent_sessions = playtest_storage.list_sessions(start_time=1500.0)
    assert len(recent_sessions) == 2
    older_sessions = playtest_storage.list_sessions(end_time=2500.0)
    assert len(older_sessions) == 2
    
    # Test combined filters
    filtered_sessions = playtest_storage.list_sessions(
        player_id="player1",
        start_time=2000.0
    )
    assert len(filtered_sessions) == 1
    assert filtered_sessions[0]["id"] == "session3"
    
    # Test limit and offset
    limited_sessions = playtest_storage.list_sessions(limit=2)
    assert len(limited_sessions) == 2
    offset_sessions = playtest_storage.list_sessions(offset=1, limit=2)
    assert len(offset_sessions) == 2
    assert offset_sessions[0]["id"] != limited_sessions[0]["id"]


def test_save_and_get_checkpoint(playtest_storage, sample_session, sample_checkpoint_data):
    """Test saving and retrieving checkpoint data."""
    # Save the session first
    playtest_storage.save_session(sample_session)
    
    # Save a checkpoint
    checkpoint_id = "test_checkpoint"
    checkpoint_desc = "Test checkpoint description"
    playtest_storage.save_checkpoint(
        sample_session.id,
        checkpoint_id,
        sample_checkpoint_data,
        checkpoint_desc
    )
    
    # Retrieve the checkpoint
    checkpoint_result = playtest_storage.get_checkpoint(checkpoint_id)
    
    # Verify the checkpoint data
    assert checkpoint_result is not None
    data, metadata = checkpoint_result
    
    assert data == sample_checkpoint_data
    assert metadata["id"] == checkpoint_id
    assert metadata["session_id"] == sample_session.id
    assert metadata["description"] == checkpoint_desc


def test_save_checkpoint_invalid_session(playtest_storage, sample_checkpoint_data):
    """Test saving a checkpoint for an invalid session."""
    with pytest.raises(ValueError):
        playtest_storage.save_checkpoint(
            "nonexistent_session",
            "checkpoint_id",
            sample_checkpoint_data
        )


def test_list_checkpoints(playtest_storage, sample_session, sample_checkpoint_data):
    """Test listing checkpoints for a session."""
    # Save the session
    playtest_storage.save_session(sample_session)
    
    # Save multiple checkpoints
    checkpoint_ids = ["checkpoint1", "checkpoint2", "checkpoint3"]
    for i, checkpoint_id in enumerate(checkpoint_ids):
        playtest_storage.save_checkpoint(
            sample_session.id,
            checkpoint_id,
            sample_checkpoint_data,
            f"Checkpoint {i+1}"
        )
    
    # List checkpoints
    checkpoints = playtest_storage.list_checkpoints(sample_session.id)
    
    # Verify the checkpoint list
    assert len(checkpoints) == 3
    assert set(c["id"] for c in checkpoints) == set(checkpoint_ids)


def test_add_event_to_session(playtest_storage, sample_session):
    """Test adding an event to a session."""
    # Save the session
    playtest_storage.save_session(sample_session)
    
    # Add a new event
    new_event = {
        "type": "item_collected",
        "timestamp": 1623457000.0,
        "data": {"item_id": "gold_coin"}
    }
    
    result = playtest_storage.add_event_to_session(sample_session.id, new_event)
    assert result is True
    
    # Retrieve the updated session
    updated = playtest_storage.get_session(sample_session.id)
    
    # Verify the event was added
    assert len(updated.events) == len(sample_session.events) + 1
    assert updated.events[-1] == new_event


def test_update_session_metrics(playtest_storage, sample_session):
    """Test updating metrics for a session."""
    # Save the session
    playtest_storage.save_session(sample_session)
    
    # Update metrics
    new_metrics = {
        "score": 150,  # Update existing metric
        "time_played": 600  # Add new metric
    }
    
    result = playtest_storage.update_session_metrics(sample_session.id, new_metrics)
    assert result is True
    
    # Retrieve the updated session
    updated = playtest_storage.get_session(sample_session.id)
    
    # Verify metrics were updated
    assert updated.metrics["score"] == 150
    assert updated.metrics["time_played"] == 600
    assert updated.metrics["health"] == sample_session.metrics["health"]  # Unchanged


def test_mark_session_completed(playtest_storage, sample_session):
    """Test marking a session as completed."""
    # Save the session (initially not completed)
    playtest_storage.save_session(sample_session)
    assert not sample_session.completed
    
    # Mark as completed with a specific duration
    result = playtest_storage.mark_session_completed(sample_session.id, 1200.0)
    assert result is True
    
    # Retrieve the updated session
    updated = playtest_storage.get_session(sample_session.id)
    
    # Verify completion status and duration
    assert updated.completed is True
    assert updated.duration == 1200.0
    
    # Test automatic duration calculation
    # Create a new session
    new_session = PlaytestSession(
        id="auto_duration",
        version_id="version1",
        player_id="player1",
        timestamp=playtest_storage._init_database.__globals__["generate_timestamp"]() - 500.0,  # 500 seconds ago
        duration=0.0,
        completed=False,
        events=[],
        metrics={},
        checkpoint_ids=[]
    )
    
    playtest_storage.save_session(new_session)
    
    # Mark as completed without specifying duration
    result = playtest_storage.mark_session_completed(new_session.id)
    assert result is True
    
    # Retrieve the updated session
    updated = playtest_storage.get_session(new_session.id)
    
    # Verify completion status and automatic duration
    assert updated.completed is True
    assert updated.duration >= 500.0  # Should be at least 500 seconds