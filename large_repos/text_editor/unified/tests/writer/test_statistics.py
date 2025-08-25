"""Tests for the writing statistics tracking system."""

import pytest
import time
from datetime import datetime, timedelta
from writer_text_editor.document import Document, Section, TextSegment
from writer_text_editor.statistics import WritingStatistics, ReadingLevel, WritingPace, DocumentStats


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    doc = Document(title="Test Document")
    
    # Add a chapter
    chapter = doc.add_section("Chapter 1: Introduction")
    
    # Add some paragraphs with varied content for statistics testing
    chapter.add_segment("This is a simple paragraph with basic vocabulary and straightforward sentence structure.")
    chapter.add_segment("In contrast, this paragraph utilizes more sophisticated terminology and complex clausal arrangements, thereby demonstrating a higher level of linguistic complexity that might appeal to readers with advanced reading capabilities.")
    chapter.add_segment("Short sentences. One after another. Like this one. And this. Creating rhythm.")
    
    # Add another chapter
    chapter2 = doc.add_section("Chapter 2: Development")
    
    # Add more paragraphs
    chapter2.add_segment("The narrative continued to evolve with intricate plot developments and character arcs.")
    chapter2.add_segment("Elena pondered the implications of her decisions, weighing the consequences against potential benefits.")
    chapter2.add_segment("Was this the right path? She couldn't be certain, but she had to make a choice nonetheless.")
    
    return doc


@pytest.fixture
def statistics(sample_document):
    """Create a writing statistics instance for testing."""
    return WritingStatistics(sample_document)


def test_statistics_initialization(sample_document, statistics):
    """Test that statistics tracking initializes correctly."""
    assert statistics.document == sample_document
    assert statistics.stats_history == []
    assert statistics.pace_history == []
    assert statistics.progress_trackers == {}
    assert statistics._last_word_count == 0
    assert statistics._last_check_time > 0


def test_calculate_stats(statistics):
    """Test calculating document statistics."""
    stats = statistics.calculate_stats()
    
    assert isinstance(stats, DocumentStats)
    assert stats.word_count > 0
    assert stats.character_count > 0
    assert stats.paragraph_count > 0
    assert stats.sentence_count > 0
    
    # Verify word stats
    assert stats.word_stats.total_words > 0
    assert stats.word_stats.unique_words > 0
    assert 0 < stats.word_stats.vocabulary_richness <= 1  # Should be between 0 and 1
    
    # Verify sentence stats
    assert stats.sentence_stats.total_sentences > 0
    assert stats.sentence_stats.average_sentence_length > 0
    
    # Verify reading level metrics
    assert ReadingLevel.FLESCH_KINCAID_GRADE.value in stats.reading_level
    assert ReadingLevel.FLESCH_READING_EASE.value in stats.reading_level
    assert ReadingLevel.GUNNING_FOG.value in stats.reading_level
    
    # Verify it's added to history
    assert len(statistics.stats_history) == 1
    assert statistics.stats_history[0] == stats


def test_calculate_writing_pace(statistics, sample_document):
    """Test calculating writing pace."""
    # Set initial word count
    statistics._last_word_count = 100
    statistics._last_check_time = time.time() - 60  # 60 seconds ago
    
    # Add some content to increase word count
    chapter = sample_document.add_section("New Chapter")
    chapter.add_segment("Adding some new content to test the writing pace calculation.")
    chapter.add_segment("This should register as new words written since the last check.")
    
    # Calculate pace
    pace = statistics.calculate_writing_pace()
    
    assert isinstance(pace, WritingPace)
    assert pace.words_per_minute >= 0
    assert pace.words_per_hour == pace.words_per_minute * 60
    assert pace.words_per_day == pace.words_per_minute * 60 * 24
    
    # Verify it's added to history
    assert len(statistics.pace_history) == 1
    assert statistics.pace_history[0] == pace


def test_set_progress_goal(statistics):
    """Test setting a progress goal."""
    goal_id = "word_count_goal"
    target = 10000
    deadline = datetime.now() + timedelta(days=30)
    
    tracker = statistics.set_progress_goal(
        goal_id=goal_id,
        goal_type="word_count",
        target=target,
        deadline=deadline
    )
    
    assert goal_id in statistics.progress_trackers
    assert statistics.progress_trackers[goal_id] == tracker
    assert tracker.goal_type == "word_count"
    assert tracker.goal_target == target
    assert tracker.goal_deadline == deadline


def test_update_progress(statistics):
    """Test updating progress for a goal."""
    # Set a progress goal
    goal_id = "word_count_goal"
    statistics.set_progress_goal(
        goal_id=goal_id,
        goal_type="word_count",
        target=10000
    )
    
    # Update progress
    progress = statistics.update_progress(goal_id)
    
    assert progress is not None
    assert "timestamp" in progress
    assert "word_count" in progress
    assert "goal_type" in progress
    assert "goal_target" in progress
    assert "progress_percentage" in progress
    assert "remaining" in progress
    
    # Non-existent goal should return None
    assert statistics.update_progress("non_existent_goal") is None
    
    # Verify history is updated
    assert len(statistics.progress_trackers[goal_id].progress_history) == 1
    assert statistics.progress_trackers[goal_id].progress_history[0] == progress


def test_get_progress_report(statistics):
    """Test getting a progress report for a goal."""
    # Set a progress goal and update it
    goal_id = "word_count_goal"
    statistics.set_progress_goal(
        goal_id=goal_id,
        goal_type="word_count",
        target=10000
    )
    statistics.update_progress(goal_id)
    
    # Get progress report
    report = statistics.get_progress_report(goal_id)
    
    assert report is not None
    assert report["goal_id"] == goal_id
    assert report["goal_type"] == "word_count"
    assert report["goal_target"] == 10000
    assert "current_progress" in report
    assert "history_summary" in report
    
    # Non-existent goal should return None
    assert statistics.get_progress_report("non_existent_goal") is None


def test_get_trend_analysis_insufficient_data(statistics):
    """Test trend analysis with insufficient data."""
    result = statistics.get_trend_analysis()
    
    assert "error" in result
    assert result["error"] == "Not enough data for trend analysis"


def test_get_trend_analysis(statistics):
    """Test trend analysis with sufficient data."""
    # Add multiple data points
    for i in range(3):
        stats = statistics.calculate_stats()
        # Modify timestamp to simulate different days
        stats.timestamp = datetime.now() - timedelta(days=2-i)
        statistics.stats_history[-1] = stats
        
        pace = statistics.calculate_writing_pace()
        pace.timestamp = datetime.now() - timedelta(days=2-i)
        statistics.pace_history[-1] = pace
    
    # Get trend analysis
    trends = statistics.get_trend_analysis(days=7)
    
    assert "error" not in trends
    assert "period_days" in trends
    assert "daily_progress" in trends
    assert "reading_level_trends" in trends
    
    # There should be some daily changes (at least one day)
    assert "daily_change" in trends
    
    # Test with shorter period
    shorter_trends = statistics.get_trend_analysis(days=1)
    
    # Should filter out older entries
    assert shorter_trends["period_days"] == 1


def test_count_sentences(statistics):
    """Test the sentence counting method."""
    text = "This is one sentence. This is another! And a third? And a fourth."
    count = statistics._count_sentences(text)
    
    assert count == 4


def test_identify_sentence_type(statistics):
    """Test the sentence type identification method."""
    assert statistics._identify_sentence_type("This is a declarative sentence.") == "declarative"
    assert statistics._identify_sentence_type("Is this an interrogative sentence?") == "interrogative"
    assert statistics._identify_sentence_type("What a surprise!") == "exclamatory"
    assert statistics._identify_sentence_type("This is a sentence, but it has a conjunction.") == "complex"
    assert statistics._identify_sentence_type("") == "unknown"


def test_is_complex_sentence(statistics):
    """Test the complex sentence detection method."""
    assert statistics._is_complex_sentence("This is a simple sentence.") is False
    assert statistics._is_complex_sentence("This is a sentence, but it has a conjunction.") is True
    assert statistics._is_complex_sentence("When she arrived, the party had already started.") is True


def test_calculate_vocabulary_richness(statistics):
    """Test the vocabulary richness calculation method."""
    assert statistics._calculate_vocabulary_richness(100, 50) == 0.5
    assert statistics._calculate_vocabulary_richness(100, 100) == 1.0
    assert statistics._calculate_vocabulary_richness(0, 0) == 0.0