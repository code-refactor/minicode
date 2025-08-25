"""
Tests for the feedback database module.
"""

import tempfile
from pathlib import Path

import pytest

from gamevault.feedback_system.database import FeedbackDatabase
from gamevault.models import FeedbackEntry


@pytest.fixture
def feedback_db():
    """Create a FeedbackDatabase with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db = FeedbackDatabase("test_project", temp_dir)
        yield db


@pytest.fixture
def sample_feedback():
    """Create a sample feedback entry for testing."""
    return FeedbackEntry(
        player_id="player123",
        version_id="version456",
        timestamp=1623456789.0,
        category="bug",
        content="Found a bug when jumping on platforms",
        metadata={"severity": "high", "area": "platforming", "build": "123"},
        tags=["bug", "gameplay", "physics"],
        priority=1,
        resolved=False
    )


def test_add_feedback(feedback_db, sample_feedback):
    """Test adding a feedback entry to the database."""
    # Add the feedback
    feedback_id = feedback_db.add_feedback(sample_feedback)
    
    # Verify the feedback was added
    assert feedback_id == sample_feedback.id
    
    # Retrieve the feedback
    retrieved = feedback_db.get_feedback(feedback_id)
    
    # Verify the retrieved data matches
    assert retrieved is not None
    assert retrieved.player_id == sample_feedback.player_id
    assert retrieved.version_id == sample_feedback.version_id
    assert retrieved.category == sample_feedback.category
    assert retrieved.content == sample_feedback.content
    assert retrieved.metadata == sample_feedback.metadata
    assert set(retrieved.tags) == set(sample_feedback.tags)
    assert retrieved.priority == sample_feedback.priority
    assert retrieved.resolved == sample_feedback.resolved


def test_update_feedback(feedback_db, sample_feedback):
    """Test updating a feedback entry."""
    # Add the feedback
    feedback_id = feedback_db.add_feedback(sample_feedback)
    
    # Modify the feedback
    sample_feedback.content = "Updated bug description"
    sample_feedback.metadata["severity"] = "medium"
    sample_feedback.tags.append("updated")
    sample_feedback.priority = 2
    sample_feedback.resolved = True
    
    # Update the feedback
    result = feedback_db.update_feedback(sample_feedback)
    assert result is True
    
    # Retrieve the updated feedback
    retrieved = feedback_db.get_feedback(feedback_id)
    
    # Verify the updates were applied
    assert retrieved.content == "Updated bug description"
    assert retrieved.metadata["severity"] == "medium"
    assert "updated" in retrieved.tags
    assert retrieved.priority == 2
    assert retrieved.resolved is True


def test_delete_feedback(feedback_db, sample_feedback):
    """Test deleting a feedback entry."""
    # Add the feedback
    feedback_id = feedback_db.add_feedback(sample_feedback)
    
    # Verify it exists
    assert feedback_db.get_feedback(feedback_id) is not None
    
    # Delete the feedback
    result = feedback_db.delete_feedback(feedback_id)
    assert result is True
    
    # Verify it was deleted
    assert feedback_db.get_feedback(feedback_id) is None
    
    # Try to delete a non-existent feedback
    result = feedback_db.delete_feedback("nonexistent")
    assert result is False


def test_list_feedback(feedback_db):
    """Test listing feedback entries with filtering."""
    # Add some feedback entries
    feedback1 = FeedbackEntry(
        player_id="player1",
        version_id="version1",
        timestamp=1000.0,
        category="bug",
        content="Bug report 1",
        tags=["bug"],
        resolved=False
    )
    
    feedback2 = FeedbackEntry(
        player_id="player1",
        version_id="version2",
        timestamp=2000.0,
        category="suggestion",
        content="Suggestion 1",
        tags=["suggestion", "ui"],
        resolved=True
    )
    
    feedback3 = FeedbackEntry(
        player_id="player2",
        version_id="version1",
        timestamp=3000.0,
        category="bug",
        content="Bug report 2",
        tags=["bug", "audio"],
        resolved=False
    )
    
    feedback_db.add_feedback(feedback1)
    feedback_db.add_feedback(feedback2)
    feedback_db.add_feedback(feedback3)
    
    # Test filtering by version
    version1_feedback = feedback_db.list_feedback(version_id="version1")
    assert len(version1_feedback) == 2
    assert {f.id for f in version1_feedback} == {feedback1.id, feedback3.id}
    
    # Test filtering by player
    player1_feedback = feedback_db.list_feedback(player_id="player1")
    assert len(player1_feedback) == 2
    assert {f.id for f in player1_feedback} == {feedback1.id, feedback2.id}
    
    # Test filtering by category
    bug_feedback = feedback_db.list_feedback(category="bug")
    assert len(bug_feedback) == 2
    assert {f.id for f in bug_feedback} == {feedback1.id, feedback3.id}
    
    # Test filtering by tag
    ui_feedback = feedback_db.list_feedback(tag="ui")
    assert len(ui_feedback) == 1
    assert ui_feedback[0].id == feedback2.id
    
    # Test filtering by resolved status
    resolved_feedback = feedback_db.list_feedback(resolved=True)
    assert len(resolved_feedback) == 1
    assert resolved_feedback[0].id == feedback2.id
    
    # Test combining filters
    combined_filters = feedback_db.list_feedback(version_id="version1", category="bug")
    assert len(combined_filters) == 2
    assert {f.id for f in combined_filters} == {feedback1.id, feedback3.id}
    
    # Test limit and offset
    limited = feedback_db.list_feedback(limit=1)
    assert len(limited) == 1
    
    offset = feedback_db.list_feedback(limit=1, offset=1)
    assert len(offset) == 1
    assert offset[0].id != limited[0].id


def test_count_feedback(feedback_db):
    """Test counting feedback entries."""
    # Add some feedback entries
    feedback1 = FeedbackEntry(
        player_id="player1",
        version_id="version1",
        timestamp=1000.0,
        category="bug",
        content="Bug report 1",
        tags=["bug"],
        resolved=False
    )
    
    feedback2 = FeedbackEntry(
        player_id="player2",
        version_id="version1",
        timestamp=2000.0,
        category="suggestion",
        content="Suggestion 1",
        tags=["suggestion"],
        resolved=True
    )
    
    feedback_db.add_feedback(feedback1)
    feedback_db.add_feedback(feedback2)
    
    # Test counting all feedback
    total_count = feedback_db.count_feedback()
    assert total_count == 2
    
    # Test counting with filters
    bug_count = feedback_db.count_feedback(category="bug")
    assert bug_count == 1
    
    resolved_count = feedback_db.count_feedback(resolved=True)
    assert resolved_count == 1
    
    player1_count = feedback_db.count_feedback(player_id="player1")
    assert player1_count == 1


def test_get_feedback_by_versions(feedback_db):
    """Test getting feedback grouped by version."""
    # Add feedback for different versions
    feedback1 = FeedbackEntry(
        player_id="player1",
        version_id="version1",
        timestamp=1000.0,
        category="bug",
        content="Bug for version 1"
    )
    
    feedback2 = FeedbackEntry(
        player_id="player1",
        version_id="version2",
        timestamp=2000.0,
        category="bug",
        content="Bug for version 2"
    )
    
    feedback3 = FeedbackEntry(
        player_id="player2",
        version_id="version1",
        timestamp=3000.0,
        category="suggestion",
        content="Suggestion for version 1"
    )
    
    feedback_db.add_feedback(feedback1)
    feedback_db.add_feedback(feedback2)
    feedback_db.add_feedback(feedback3)
    
    # Get feedback by versions
    by_versions = feedback_db.get_feedback_by_versions(["version1", "version2"])
    
    # Verify results
    assert "version1" in by_versions
    assert "version2" in by_versions
    assert len(by_versions["version1"]) == 2
    assert len(by_versions["version2"]) == 1
    
    # Verify the right feedback is associated with each version
    version1_ids = {f.id for f in by_versions["version1"]}
    assert feedback1.id in version1_ids
    assert feedback3.id in version1_ids
    
    version2_ids = {f.id for f in by_versions["version2"]}
    assert feedback2.id in version2_ids


def test_get_feedback_stats(feedback_db):
    """Test getting statistics about feedback data."""
    # Add a variety of feedback entries
    for i in range(5):
        feedback = FeedbackEntry(
            player_id=f"player{i % 2 + 1}",
            version_id=f"version{i % 3 + 1}",
            timestamp=1000.0 + i * 100,
            category="bug" if i % 2 == 0 else "suggestion",
            content=f"Feedback {i + 1}",
            tags=["tag1"] if i % 2 == 0 else ["tag2"],
            resolved=i % 3 == 0
        )
        feedback_db.add_feedback(feedback)
    
    # Get statistics
    stats = feedback_db.get_feedback_stats()
    
    # Verify the statistics
    assert stats["total_count"] == 5
    
    # Check category counts
    assert "by_category" in stats
    assert stats["by_category"]["bug"] == 3
    assert stats["by_category"]["suggestion"] == 2
    
    # Check resolved counts
    assert "by_resolved" in stats
    assert stats["by_resolved"]["resolved"] == 2
    assert stats["by_resolved"]["unresolved"] == 3
    
    # Check tag counts
    assert "top_tags" in stats
    assert "tag1" in stats["top_tags"]
    assert "tag2" in stats["top_tags"]
    
    # Check timeline stats
    assert "timeline" in stats


def test_update_nonexistent_feedback(feedback_db, sample_feedback):
    """Test attempting to update a non-existent feedback entry."""
    # Modify the ID to a non-existent one
    sample_feedback.id = "nonexistent"
    
    # Try to update
    result = feedback_db.update_feedback(sample_feedback)
    
    # Should return False
    assert result is False