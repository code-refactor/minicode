"""
Tests for the feedback analysis module.
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from gamevault.feedback_system.analysis import FeedbackAnalysis
from gamevault.feedback_system.database import FeedbackDatabase
from gamevault.models import FeedbackEntry, ProjectVersion


@pytest.fixture
def mock_feedback_db():
    """Create a mock feedback database with test data."""
    mock_db = MagicMock(spec=FeedbackDatabase)
    
    # Sample feedback entries
    feedback_entries = [
        FeedbackEntry(
            player_id="player1",
            version_id="version1",
            timestamp=1000.0,
            category="bug",
            content="The character falls through the floor in level 2",
            tags=["bug", "physics", "level-2"],
            resolved=False
        ),
        FeedbackEntry(
            player_id="player2",
            version_id="version1",
            timestamp=1100.0,
            category="suggestion",
            content="It would be great to have more weapons in the game",
            tags=["suggestion", "gameplay", "weapons"],
            resolved=False
        ),
        FeedbackEntry(
            player_id="player1",
            version_id="version2",
            timestamp=1200.0,
            category="bug",
            content="Game crashes when equipping two weapons at once",
            tags=["bug", "crash", "weapons"],
            resolved=True
        ),
        FeedbackEntry(
            player_id="player3",
            version_id="version2",
            timestamp=1300.0,
            category="suggestion",
            content="The loading times could be improved for level transitions",
            tags=["suggestion", "performance", "loading"],
            resolved=False
        ),
        FeedbackEntry(
            player_id="player2",
            version_id="version3",
            timestamp=1400.0,
            category="bug",
            content="Character animation freezes when climbing ladders",
            tags=["bug", "animation", "climbing"],
            resolved=False
        )
    ]
    
    # Mock list_feedback to return different subsets based on filters
    def list_feedback(version_id=None, player_id=None, category=None, tag=None, resolved=None, **kwargs):
        result = feedback_entries
        
        if version_id is not None:
            result = [f for f in result if f.version_id == version_id]
        
        if player_id is not None:
            result = [f for f in result if f.player_id == player_id]
        
        if category is not None:
            result = [f for f in result if f.category == category]
        
        if tag is not None:
            result = [f for f in result if tag in f.tags]
        
        if resolved is not None:
            result = [f for f in result if f.resolved == resolved]
        
        return result
    
    mock_db.list_feedback.side_effect = list_feedback
    
    # Mock get_feedback_stats
    mock_db.get_feedback_stats.return_value = {
        "total_count": len(feedback_entries),
        "by_category": {"bug": 3, "suggestion": 2},
        "by_resolved": {"resolved": 1, "unresolved": 4},
        "top_tags": {"bug": 3, "suggestion": 2, "weapons": 2, "physics": 1},
        "timeline": {"2021-06-12": 2, "2021-06-13": 3}
    }
    
    return mock_db


@pytest.fixture
def feedback_analyzer(mock_feedback_db):
    """Create a FeedbackAnalysis instance with the mock database."""
    return FeedbackAnalysis(mock_feedback_db)


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
            type="alpha",
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


def test_get_common_terms(feedback_analyzer, mock_feedback_db):
    """Test extracting common terms from feedback content."""
    # Get all feedback
    feedback = mock_feedback_db.list_feedback()
    
    # Get common terms
    terms = feedback_analyzer.get_common_terms(feedback, min_length=5, max_terms=10)
    
    # Verify format of results
    assert isinstance(terms, list)
    assert all(isinstance(term, tuple) and len(term) == 2 for term in terms)
    assert all(isinstance(term[0], str) and isinstance(term[1], int) for term in terms)
    
    # Verify some expected terms
    term_dict = dict(terms)
    
    # Check for words that should appear in the feedback
    # We only look for terms with at least 5 characters as required by min_length
    expected_terms = ["character", "weapons", "level", "floor", "loading"]
    for term in expected_terms:
        if len(term) >= 5:  # Only check terms that meet the min_length
            assert any(term in word for word, _ in terms), f"Expected term '{term}' not found"


def test_get_feedback_over_time(feedback_analyzer, sample_version_history):
    """Test tracking feedback patterns over time."""
    # Get feedback over time
    feedback_over_time = feedback_analyzer.get_feedback_over_time(sample_version_history)
    
    # Verify format of results
    assert len(feedback_over_time) == 3  # One entry per version
    
    # Check each version's data
    for version_id, data in feedback_over_time.items():
        assert "name" in data
        assert "timestamp" in data
        assert "counts" in data
        assert "total" in data
        
        # Check the correct versions are included
        assert version_id in ["version1", "version2", "version3"]


def test_identify_recurring_issues(feedback_analyzer, sample_version_history):
    """Test identifying recurring issues across versions."""
    # Identify recurring issues
    recurring = feedback_analyzer.identify_recurring_issues(sample_version_history, threshold=2)
    
    # Verify format of results
    assert isinstance(recurring, list)
    
    # We can't assert exact content since it depends on the natural language processing
    # But we can check the structure
    if recurring:
        issue = recurring[0]
        assert "term" in issue
        assert "version_count" in issue
        assert "versions" in issue
        assert "examples" in issue


def test_get_sentiment_distribution(feedback_analyzer, mock_feedback_db):
    """Test sentiment analysis of feedback entries."""
    # Get all feedback
    feedback = mock_feedback_db.list_feedback()
    
    # Get sentiment distribution
    sentiments = feedback_analyzer.get_sentiment_distribution(feedback)
    
    # Verify format of results
    assert "positive" in sentiments
    assert "negative" in sentiments
    assert "neutral" in sentiments
    assert sentiments["positive"] + sentiments["negative"] + sentiments["neutral"] == len(feedback)


def test_analyze_feature_feedback(feedback_analyzer, sample_version_history):
    """Test analyzing feedback related to a specific feature."""
    # Analyze 'weapons' feature
    weapons_analysis = feedback_analyzer.analyze_feature_feedback("weapons", sample_version_history)
    
    # Verify format of results
    assert "feature_tag" in weapons_analysis
    assert weapons_analysis["feature_tag"] == "weapons"
    assert "total_feedback" in weapons_analysis
    assert "by_version" in weapons_analysis
    assert "common_terms" in weapons_analysis
    assert "sentiment" in weapons_analysis


def test_get_player_engagement(feedback_analyzer, sample_version_history):
    """Test analyzing a player's engagement across versions."""
    # Analyze player1's engagement
    engagement = feedback_analyzer.get_player_engagement("player1", sample_version_history)
    
    # Verify format of results
    assert "player_id" in engagement
    assert engagement["player_id"] == "player1"
    assert "feedback_count" in engagement
    assert "versions_with_feedback" in engagement
    
    # player1 has feedback in version1 and version2
    assert engagement["versions_with_feedback"] == 2
    
    # Verify by_version data
    assert "by_version" in engagement
    assert "version1" in engagement["by_version"]
    assert "version2" in engagement["by_version"]


def test_get_player_engagement_no_feedback(feedback_analyzer, sample_version_history):
    """Test analyzing a player with no feedback."""
    # Analyze a non-existent player
    engagement = feedback_analyzer.get_player_engagement("nonexistent", sample_version_history)
    
    # Verify empty result
    assert "player_id" in engagement
    assert engagement["player_id"] == "nonexistent"
    assert "feedback_count" in engagement
    assert engagement["feedback_count"] == 0