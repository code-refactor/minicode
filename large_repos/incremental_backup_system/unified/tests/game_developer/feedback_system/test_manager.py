"""
Tests for the feedback manager module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.feedback_system.manager import FeedbackManager
from gamevault.models import FeedbackEntry, ProjectVersion


@pytest.fixture
def mock_version_tracker():
    """Create a mock version tracker."""
    mock = MagicMock(spec=VersionTracker)
    
    # Mock version existence check
    def get_version(version_id):
        if version_id == "valid_version":
            return ProjectVersion(
                name="Test Version",
                timestamp=1000.0,
                files={}
            )
        else:
            raise FileNotFoundError(f"Version {version_id} not found")
    
    mock.get_version.side_effect = get_version
    
    return mock


@pytest.fixture
def feedback_manager(mock_version_tracker):
    """Create a FeedbackManager with a temporary directory and mock version tracker."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = FeedbackManager("test_project", mock_version_tracker, temp_dir)
        yield manager


def test_add_feedback(feedback_manager):
    """Test adding a feedback entry."""
    # Add feedback
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Test feedback",
        metadata={"severity": "high"},
        tags=["gameplay"],
        priority=1
    )
    
    # Verify the feedback was created
    assert feedback.player_id == "player123"
    assert feedback.version_id == "valid_version"
    assert feedback.category == "bug"
    assert feedback.content == "Test feedback"
    assert feedback.metadata == {"severity": "high"}
    assert feedback.tags == ["gameplay"]
    assert feedback.priority == 1
    assert not feedback.resolved
    
    # Verify the feedback is retrievable
    retrieved = feedback_manager.get_feedback(feedback.id)
    assert retrieved is not None
    assert retrieved.id == feedback.id


def test_add_feedback_invalid_version(feedback_manager):
    """Test adding feedback for an invalid version."""
    # Try to add feedback for a non-existent version
    with pytest.raises(ValueError, match="Version invalid_version not found"):
        feedback_manager.add_feedback(
            player_id="player123",
            version_id="invalid_version",
            category="bug",
            content="Test feedback"
        )


def test_update_feedback(feedback_manager):
    """Test updating a feedback entry."""
    # Add feedback
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Original content",
        tags=["original"]
    )
    
    # Update the feedback
    feedback.content = "Updated content"
    feedback.tags = ["updated"]
    result = feedback_manager.update_feedback(feedback)
    
    # Verify the update succeeded
    assert result is True
    
    # Verify the changes were applied
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.content == "Updated content"
    assert updated.tags == ["updated"]


def test_delete_feedback(feedback_manager):
    """Test deleting a feedback entry."""
    # Add feedback
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Content to delete"
    )
    
    # Verify it exists
    assert feedback_manager.get_feedback(feedback.id) is not None
    
    # Delete the feedback
    result = feedback_manager.delete_feedback(feedback.id)
    
    # Verify deletion succeeded
    assert result is True
    assert feedback_manager.get_feedback(feedback.id) is None


def test_mark_feedback_resolved(feedback_manager):
    """Test marking a feedback entry as resolved."""
    # Add feedback
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Bug to resolve"
    )
    
    # Mark as resolved
    result = feedback_manager.mark_feedback_resolved(feedback.id)
    
    # Verify the operation succeeded
    assert result is True
    
    # Verify the feedback is marked as resolved
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.resolved is True
    
    # Mark as unresolved
    result = feedback_manager.mark_feedback_resolved(feedback.id, False)
    
    # Verify the feedback is marked as unresolved
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.resolved is False


def test_add_tags_to_feedback(feedback_manager):
    """Test adding tags to a feedback entry."""
    # Add feedback with initial tags
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Tagged feedback",
        tags=["initial"]
    )
    
    # Add more tags
    result = feedback_manager.add_tags_to_feedback(feedback.id, ["new", "tags"])
    
    # Verify the operation succeeded
    assert result is True
    
    # Verify the tags were added
    updated = feedback_manager.get_feedback(feedback.id)
    assert set(updated.tags) == {"initial", "new", "tags"}
    
    # Add duplicate tag (should be ignored)
    feedback_manager.add_tags_to_feedback(feedback.id, ["initial", "another"])
    updated = feedback_manager.get_feedback(feedback.id)
    assert set(updated.tags) == {"initial", "new", "tags", "another"}


def test_remove_tags_from_feedback(feedback_manager):
    """Test removing tags from a feedback entry."""
    # Add feedback with tags
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Tagged feedback",
        tags=["tag1", "tag2", "tag3"]
    )
    
    # Remove some tags
    result = feedback_manager.remove_tags_from_feedback(feedback.id, ["tag1", "tag3"])
    
    # Verify the operation succeeded
    assert result is True
    
    # Verify the tags were removed
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.tags == ["tag2"]


def test_add_metadata_to_feedback(feedback_manager):
    """Test adding metadata to a feedback entry."""
    # Add feedback with initial metadata
    feedback = feedback_manager.add_feedback(
        player_id="player123",
        version_id="valid_version",
        category="bug",
        content="Metadata feedback",
        metadata={"initial": "value"}
    )
    
    # Add more metadata
    result = feedback_manager.add_metadata_to_feedback(feedback.id, {"new": "data", "another": "field"})
    
    # Verify the operation succeeded
    assert result is True
    
    # Verify the metadata was added
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.metadata == {"initial": "value", "new": "data", "another": "field"}
    
    # Update existing metadata
    feedback_manager.add_metadata_to_feedback(feedback.id, {"initial": "updated"})
    updated = feedback_manager.get_feedback(feedback.id)
    assert updated.metadata["initial"] == "updated"


def test_get_feedback_for_version(feedback_manager):
    """Test getting feedback for a specific version."""
    # Add some feedback entries
    for i in range(5):
        feedback_manager.add_feedback(
            player_id=f"player{i}",
            version_id="valid_version",
            category="bug" if i % 2 == 0 else "suggestion",
            content=f"Feedback {i}",
            tags=["tag1"] if i % 2 == 0 else ["tag2"],
            resolved=i % 3 == 0
        )
    
    # Get all feedback for the version
    all_feedback = feedback_manager.get_feedback_for_version("valid_version")
    assert len(all_feedback) == 5
    
    # Filter by category
    bug_feedback = feedback_manager.get_feedback_for_version("valid_version", category="bug")
    assert len(bug_feedback) == 3
    
    # Filter by tag
    tag1_feedback = feedback_manager.get_feedback_for_version("valid_version", tag="tag1")
    assert len(tag1_feedback) == 3
    
    # Filter by resolved status
    resolved_feedback = feedback_manager.get_feedback_for_version("valid_version", resolved=True)
    assert len(resolved_feedback) == 2


def test_get_feedback_for_invalid_version(feedback_manager):
    """Test getting feedback for an invalid version."""
    with pytest.raises(ValueError, match="Version invalid_version not found"):
        feedback_manager.get_feedback_for_version("invalid_version")


def test_get_feedback_for_player(feedback_manager):
    """Test getting feedback for a specific player."""
    # Add some feedback entries from different players
    for i in range(5):
        player_id = "player1" if i % 2 == 0 else "player2"
        feedback_manager.add_feedback(
            player_id=player_id,
            version_id="valid_version",
            category="bug",
            content=f"Feedback {i}"
        )
    
    # Get feedback for player1
    player1_feedback = feedback_manager.get_feedback_for_player("player1")
    assert len(player1_feedback) == 3
    
    # Get feedback for player2
    player2_feedback = feedback_manager.get_feedback_for_player("player2")
    assert len(player2_feedback) == 2


def test_search_feedback(feedback_manager):
    """Test searching for feedback."""
    # Add some feedback entries with searchable content
    feedback_manager.add_feedback(
        player_id="player1",
        version_id="valid_version",
        category="bug",
        content="Found a crash when loading the level",
        tags=["crash", "loading"]
    )
    
    feedback_manager.add_feedback(
        player_id="player2",
        version_id="valid_version",
        category="suggestion",
        content="The loading screen should show progress",
        tags=["ui", "loading"]
    )
    
    feedback_manager.add_feedback(
        player_id="player3",
        version_id="valid_version",
        category="bug",
        content="Game freezes during combat",
        tags=["freeze", "combat"]
    )
    
    # Search by content keyword
    loading_results = feedback_manager.search_feedback("loading")
    assert len(loading_results) == 2
    
    # Search by tag
    loading_tag_results = feedback_manager.search_feedback("loading", tag="loading")
    assert len(loading_tag_results) == 2
    
    # Search with category filter
    bug_loading_results = feedback_manager.search_feedback("loading", category="bug")
    assert len(bug_loading_results) == 1
    
    # Search that should return no results
    no_results = feedback_manager.search_feedback("nonexistent")
    assert len(no_results) == 0