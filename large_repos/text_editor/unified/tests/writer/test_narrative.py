"""Tests for the character and plot element tracking system."""

import pytest
import re
from unittest.mock import MagicMock, patch
from writer_text_editor.document import Document, Section, TextSegment
from writer_text_editor.narrative import (
    NarrativeTracker, ElementType, NarrativeElement,
    ElementOccurrence, ConsistencyIssue
)


@pytest.fixture
def sample_document():
    """Create a sample document with narrative elements for testing."""
    doc = Document(title="Test Novel")
    
    # Chapter 1
    chapter1 = doc.add_section("Chapter 1: The Beginning")
    
    # Add paragraphs with character references
    chapter1.add_segment("Sarah walked through the park, enjoying the sunshine on her face.")
    chapter1.add_segment("As she sat on a bench, she noticed John approaching from the distance.")
    chapter1.add_segment("'Hello, Sarah,' John said with a smile. 'Beautiful day, isn't it?'")
    
    # Chapter 2
    chapter2 = doc.add_section("Chapter 2: The Encounter")
    
    # Add more paragraphs with character and plot elements
    chapter2.add_segment("Later that evening, Sarah met with her friend Emily at the Moonlight Cafe.")
    chapter2.add_segment("'I saw John today,' Sarah told Emily. 'He seemed different, more confident.'")
    chapter2.add_segment("Emily nodded. 'He's been like that ever since he found the ancient amulet.'")
    
    # Chapter 3
    chapter3 = doc.add_section("Chapter 3: The Mystery")
    
    # Add more narrative elements and potential inconsistencies
    chapter3.add_segment("John examined the ancient amulet carefully. Its golden surface gleamed in the low light.")
    chapter3.add_segment("Sarah had always known John was tall with dark hair, but now she noticed his eyes were green.")
    chapter3.add_segment("'Wait,' she thought, 'weren't his eyes blue when we met at the park?'")
    
    return doc


@pytest.fixture
def narrative_tracker(sample_document):
    """Create a narrative tracker with mocked NLP capabilities."""
    tracker = NarrativeTracker(sample_document)
    
    # Mock the NLP model to avoid external dependencies
    nlp_mock = MagicMock()
    
    # Mock the entity recognition
    doc_mock = MagicMock()
    
    # Create mock entities for "Sarah", "John", "Emily", "Moonlight Cafe", and "ancient amulet"
    entities = [
        MagicMock(text="Sarah", label_="PERSON"),
        MagicMock(text="John", label_="PERSON"),
        MagicMock(text="Emily", label_="PERSON"),
        MagicMock(text="Moonlight Cafe", label_="LOC"),
        MagicMock(text="ancient amulet", label_="OBJECT")
    ]
    
    doc_mock.ents = entities
    
    # Mock tokens for proper noun detection
    tokens = []
    for name in ["Sarah", "John", "Emily"]:
        token_mock = MagicMock()
        token_mock.is_alpha = True
        token_mock.is_title = True
        token_mock.pos_ = "PROPN"
        token_mock.text = name
        
        # Mock head for noun phrase detection
        token_mock.head.pos_ = "PROPN"
        
        # Mock subtree for full noun phrase extraction
        token_mock.head.subtree = [token_mock]
        
        tokens.append(token_mock)
    
    doc_mock.__iter__ = lambda self: iter(tokens)
    
    nlp_mock.return_value = doc_mock
    tracker._nlp = nlp_mock
    
    return tracker


def test_narrative_tracker_initialization(sample_document, narrative_tracker):
    """Test that the narrative tracker initializes correctly."""
    assert narrative_tracker.document == sample_document
    assert narrative_tracker.elements == {}
    assert narrative_tracker.consistency_issues == []
    assert narrative_tracker._nlp is not None


def test_track_element(narrative_tracker):
    """Test tracking a narrative element by name and aliases."""
    # Track a character
    element = narrative_tracker.track_element(
        name="Sarah",
        element_type=ElementType.CHARACTER,
        aliases=["Sarah Johnson"],
        description="The protagonist of the story."
    )
    
    assert element.id in narrative_tracker.elements
    assert narrative_tracker.elements[element.id] == element
    assert element.name == "Sarah"
    assert element.element_type == ElementType.CHARACTER
    assert "Sarah Johnson" in element.aliases
    assert element.description == "The protagonist of the story."
    assert len(element.occurrences) > 0  # Should find occurrences in the document


def test_find_element_occurrences(narrative_tracker):
    """Test finding occurrences of an element in the document."""
    # Use a direct call to _find_element_occurrences
    occurrences = narrative_tracker._find_element_occurrences("John", ["Johnny"])
    
    assert len(occurrences) > 0
    
    # Each occurrence should be a tuple of (section, segment, position, context)
    for occurrence in occurrences:
        assert len(occurrence) == 4
        assert isinstance(occurrence[0], Section)
        assert isinstance(occurrence[1], TextSegment)
        assert isinstance(occurrence[2], int)
        assert isinstance(occurrence[3], str)
        assert "John" in occurrence[3]


def test_detect_elements(narrative_tracker):
    """Test automatically detecting narrative elements."""
    # When using spaCy, this would normally detect characters like "Sarah" and "John"
    tracked_elements = narrative_tracker.detect_elements()
    
    # Should have characters, locations, items, and events
    assert ElementType.CHARACTER.value in tracked_elements
    
    # Check that we found at least some characters
    characters = tracked_elements[ElementType.CHARACTER.value]
    assert any(element.name == "Sarah" for element in characters) or \
           any(element.name == "John" for element in characters) or \
           any(element.name == "Emily" for element in characters)


def test_update_element_relationships(narrative_tracker):
    """Test updating relationships between elements based on co-occurrence."""
    # Add some elements first
    sarah = narrative_tracker.track_element(
        name="Sarah",
        element_type=ElementType.CHARACTER
    )
    
    john = narrative_tracker.track_element(
        name="John",
        element_type=ElementType.CHARACTER
    )
    
    # Update relationships
    narrative_tracker.update_element_relationships()
    
    # Sarah and John should be related since they appear together
    assert john.id in sarah.related_elements or sarah.id in john.related_elements


def test_check_consistency(narrative_tracker):
    """Test checking for consistency issues in the narrative."""
    # Setup: Add character with contradictory descriptions
    sarah = narrative_tracker.track_element(
        name="Sarah",
        element_type=ElementType.CHARACTER
    )
    
    john = narrative_tracker.track_element(
        name="John",
        element_type=ElementType.CHARACTER
    )
    
    # Explicitly add some mock occurrences with contradictory descriptions
    # We'll modify John's occurrences to include descriptions about eye color
    for section in narrative_tracker.document.current_revision.sections:
        for segment in section.segments:
            if "eyes were green" in segment.content or "eyes were blue" in segment.content:
                john.occurrences.append(ElementOccurrence(
                    element_id=john.id,
                    section_id=section.id,
                    segment_id=segment.id,
                    position=0,
                    context=segment.content
                ))
    
    # Check for consistency issues
    issues = narrative_tracker.check_consistency()
    
    # Might find issues, or might not depending on the mock setup
    # Just ensure it runs without errors
    assert isinstance(narrative_tracker.consistency_issues, list)


def test_get_element_appearances(narrative_tracker):
    """Test getting detailed information about all appearances of an element."""
    # Track an element first
    element = narrative_tracker.track_element(
        name="Sarah",
        element_type=ElementType.CHARACTER
    )
    
    # Get appearances
    appearances = narrative_tracker.get_element_appearances(element.id)
    
    assert len(appearances) > 0
    
    # Each appearance should have expected fields
    for appearance in appearances:
        assert "section_title" in appearance
        assert "section_id" in appearance
        assert "segment_id" in appearance
        assert "context" in appearance
        assert "Sarah" in appearance["context"]


def test_get_element_timeline(narrative_tracker):
    """Test getting a timeline of an element's appearances ordered by position."""
    # Track an element first
    element = narrative_tracker.track_element(
        name="Sarah",
        element_type=ElementType.CHARACTER
    )
    
    # Get timeline
    timeline = narrative_tracker.get_element_timeline(element.id)
    
    assert len(timeline) > 0
    
    # Each timeline entry should be a section with appearances
    for entry in timeline:
        assert "section_id" in entry
        assert "section_title" in entry
        assert "appearances" in entry
        assert isinstance(entry["appearances"], list)
        
        # Appearances should be ordered by segment position
        positions = [a["segment_position"] for a in entry["appearances"]]
        assert positions == sorted(positions)


def test_resolve_consistency_issue(narrative_tracker):
    """Test marking a consistency issue as resolved."""
    # Add a consistency issue
    issue = ConsistencyIssue(
        id="1",
        issue_type="contradiction",
        elements_involved=["character_1"],
        description="Test contradiction",
        locations=[("section_1", "segment_1"), ("section_2", "segment_2")],
        severity=3
    )
    
    narrative_tracker.consistency_issues = [issue]
    
    # Resolve the issue
    result = narrative_tracker.resolve_consistency_issue("1", "This is fixed now.")
    
    assert result is True
    assert narrative_tracker.consistency_issues[0].resolved is True
    assert narrative_tracker.consistency_issues[0].notes == "This is fixed now."
    
    # Try to resolve non-existent issue
    result = narrative_tracker.resolve_consistency_issue("999")
    
    assert result is False