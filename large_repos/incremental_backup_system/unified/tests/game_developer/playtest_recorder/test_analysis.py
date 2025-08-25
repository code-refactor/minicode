"""
Tests for the playtest analysis module.
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from gamevault.models import PlaytestSession, ProjectVersion
from gamevault.playtest_recorder.analysis import PlaytestAnalyzer
from gamevault.playtest_recorder.storage import PlaytestStorage


@pytest.fixture
def mock_playtest_storage():
    """Create a mock playtest storage with test data."""
    mock_storage = MagicMock(spec=PlaytestStorage)
    
    # Sample sessions
    sessions = [
        {
            "id": "session1",
            "version_id": "version1",
            "player_id": "player1",
            "timestamp": 1000.0,
            "duration": 600.0,
            "completed": True,
            "metrics": {"score": 100, "enemies_defeated": 10, "health": 80},
            "checkpoint_count": 2
        },
        {
            "id": "session2",
            "version_id": "version1",
            "player_id": "player2",
            "timestamp": 1100.0,
            "duration": 900.0,
            "completed": False,
            "metrics": {"score": 150, "enemies_defeated": 15, "health": 60},
            "checkpoint_count": 3
        },
        {
            "id": "session3",
            "version_id": "version2",
            "player_id": "player1",
            "timestamp": 1200.0,
            "duration": 1200.0,
            "completed": True,
            "metrics": {"score": 200, "enemies_defeated": 20, "health": 90},
            "checkpoint_count": 4
        },
        {
            "id": "session4",
            "version_id": "version2",
            "player_id": "player3",
            "timestamp": 1300.0,
            "duration": 1500.0,
            "completed": True,
            "metrics": {"score": 250, "enemies_defeated": 25, "health": 75},
            "checkpoint_count": 5
        },
        {
            "id": "session5",
            "version_id": "version3",
            "player_id": "player2",
            "timestamp": 1400.0,
            "duration": 1800.0,
            "completed": False,
            "metrics": {"score": 300, "enemies_defeated": 30, "health": 50},
            "checkpoint_count": 6
        }
    ]
    
    # Mock list_sessions to return different subsets based on filters
    def list_sessions(version_id=None, player_id=None, **kwargs):
        result = sessions
        
        if version_id is not None:
            result = [s for s in result if s["version_id"] == version_id]
        
        if player_id is not None:
            result = [s for s in result if s["player_id"] == player_id]
        
        return result
    
    mock_storage.list_sessions.side_effect = list_sessions
    
    # Mock get_session
    def get_session(session_id):
        for session in sessions:
            if session["id"] == session_id:
                events = [
                    {"type": "start", "timestamp": session["timestamp"], "data": {}},
                    {"type": "enemy_defeated", "timestamp": session["timestamp"] + 100, "data": {}}
                ]
                
                return PlaytestSession(
                    id=session["id"],
                    version_id=session["version_id"],
                    player_id=session["player_id"],
                    timestamp=session["timestamp"],
                    duration=session["duration"],
                    completed=session["completed"],
                    events=events,
                    metrics=session["metrics"],
                    checkpoint_ids=["checkpoint"] * session["checkpoint_count"]
                )
        return None
    
    mock_storage.get_session.side_effect = get_session
    
    # Mock list_checkpoints
    mock_storage.list_checkpoints.return_value = [
        {"id": "checkpoint1", "timestamp": 1000.0, "description": "Checkpoint 1"},
        {"id": "checkpoint2", "timestamp": 1100.0, "description": "Checkpoint 2"}
    ]
    
    return mock_storage


@pytest.fixture
def playtest_analyzer(mock_playtest_storage):
    """Create a PlaytestAnalyzer with the mock storage."""
    return PlaytestAnalyzer(mock_playtest_storage)


@pytest.fixture
def sample_version_history():
    """Create a sample version history for testing."""
    return [
        ProjectVersion(
            id="version1",
            name="v0.1",
            timestamp=1000.0,
            type="alpha",
            files={}
        ),
        ProjectVersion(
            id="version2",
            name="v0.2",
            timestamp=1200.0,
            type="beta",
            files={}
        ),
        ProjectVersion(
            id="version3",
            name="v0.3",
            timestamp=1400.0,
            type="beta",
            files={}
        )
    ]


def test_get_session_summary(playtest_analyzer):
    """Test getting a summary of a playtest session."""
    # Get session summary
    summary = playtest_analyzer.get_session_summary("session1")
    
    # Verify summary content
    assert summary["id"] == "session1"
    assert summary["version_id"] == "version1"
    assert summary["player_id"] == "player1"
    assert summary["duration"] == 600.0
    assert summary["completed"] is True
    assert "metrics" in summary
    assert "event_count" in summary
    assert "events_by_type" in summary
    assert "event_frequency" in summary
    assert "checkpoint_count" in summary
    assert "checkpoints" in summary


def test_get_session_summary_not_found(playtest_analyzer):
    """Test getting a summary of a non-existent session."""
    with pytest.raises(ValueError):
        playtest_analyzer.get_session_summary("nonexistent")


def test_compare_sessions(playtest_analyzer):
    """Test comparing multiple playtest sessions."""
    # Compare multiple sessions
    comparison = playtest_analyzer.compare_sessions(["session1", "session3", "session5"])
    
    # Verify comparison content
    assert comparison["count"] == 3
    assert set(comparison["version_ids"]) == {"version1", "version2", "version3"}
    assert set(comparison["player_ids"]) == {"player1", "player2"}
    
    # Check metric statistics
    assert "metric_stats" in comparison
    assert "score" in comparison["metric_stats"]
    assert "enemies_defeated" in comparison["metric_stats"]
    assert "health" in comparison["metric_stats"]
    
    # Check duration statistics
    assert "duration_stats" in comparison
    assert comparison["duration_stats"]["min"] == 600.0
    assert comparison["duration_stats"]["max"] == 1800.0
    assert comparison["duration_stats"]["mean"] == pytest.approx((600.0 + 1200.0 + 1800.0) / 3)


def test_get_version_statistics(playtest_analyzer):
    """Test getting statistics for a game version."""
    # Get version statistics
    stats = playtest_analyzer.get_version_statistics("version1")
    
    # Verify statistics content
    assert stats["version_id"] == "version1"
    assert stats["session_count"] == 2
    assert stats["player_count"] == 2
    assert stats["completed_count"] == 1
    assert stats["completion_rate"] == 0.5
    
    # Check duration statistics
    assert "duration_stats" in stats
    assert stats["duration_stats"]["min"] == 600.0
    assert stats["duration_stats"]["max"] == 900.0
    assert stats["duration_stats"]["mean"] == 750.0
    
    # Check metric statistics
    assert "metric_stats" in stats
    assert "score" in stats["metric_stats"]
    assert stats["metric_stats"]["score"]["min"] == 100
    assert stats["metric_stats"]["score"]["max"] == 150
    assert stats["metric_stats"]["score"]["mean"] == 125.0


def test_get_version_statistics_no_sessions(playtest_analyzer):
    """Test getting statistics for a version with no sessions."""
    # Get statistics for a non-existent version
    stats = playtest_analyzer.get_version_statistics("nonexistent")
    
    # Verify default/empty statistics
    assert stats["version_id"] == "nonexistent"
    assert stats["session_count"] == 0


def test_compare_versions(playtest_analyzer, sample_version_history):
    """Test comparing playtest data across different game versions."""
    # Compare versions
    comparison = playtest_analyzer.compare_versions(
        ["version1", "version2", "version3"]
    )
    
    # Verify comparison content
    assert comparison["versions"] == ["version1", "version2", "version3"]
    assert "version_stats" in comparison
    assert "version1" in comparison["version_stats"]
    assert "version2" in comparison["version_stats"]
    assert "version3" in comparison["version_stats"]
    
    # Check version-specific data
    assert comparison["version_stats"]["version1"]["session_count"] == 2
    assert comparison["version_stats"]["version2"]["session_count"] == 2
    assert comparison["version_stats"]["version3"]["session_count"] == 1
    
    # Check metric comparisons (if available)
    if "metric_comparisons" in comparison:
        assert "score" in comparison["metric_comparisons"]
        
        # Score should increase across versions
        scores = comparison["metric_comparisons"]["score"]["values"]
        assert scores[0] < scores[1] < scores[2]
    
    # Check completion rates
    assert "completion_rates" in comparison
    assert len(comparison["completion_rates"]) == 3
    
    # Check duration progression
    assert "mean_durations" in comparison
    assert len(comparison["mean_durations"]) == 3
    
    # Check change metrics
    assert "completion_change" in comparison
    assert "duration_change" in comparison


def test_get_player_statistics(playtest_analyzer):
    """Test getting statistics for a player."""
    # Get player statistics
    stats = playtest_analyzer.get_player_statistics("player1")
    
    # Verify statistics content
    assert stats["player_id"] == "player1"
    assert stats["session_count"] == 2
    assert stats["version_count"] == 2
    assert stats["completed_count"] == 2
    assert stats["completion_rate"] == 1.0
    
    # Check duration statistics
    assert "duration_stats" in stats
    assert stats["duration_stats"]["min"] == 600.0
    assert stats["duration_stats"]["max"] == 1200.0
    assert stats["duration_stats"]["mean"] == 900.0
    assert stats["duration_stats"]["total"] == 1800.0
    
    # Check metric statistics
    assert "metric_stats" in stats
    assert "score" in stats["metric_stats"]
    assert stats["metric_stats"]["score"]["min"] == 100
    assert stats["metric_stats"]["score"]["max"] == 200
    
    # Check version progression
    assert "version_progression" in stats
    assert len(stats["version_progression"]) == 2
    
    # Version progression should be ordered by first played time
    assert stats["version_progression"][0]["version_id"] == "version1"
    assert stats["version_progression"][1]["version_id"] == "version2"


def test_get_player_statistics_no_sessions(playtest_analyzer):
    """Test getting statistics for a player with no sessions."""
    # Get statistics for a non-existent player
    stats = playtest_analyzer.get_player_statistics("nonexistent")
    
    # Verify default/empty statistics
    assert stats["player_id"] == "nonexistent"
    assert stats["session_count"] == 0