"""Tests for the focus mode system."""

import pytest
from writer_text_editor.document import Document, Section, TextSegment
from writer_text_editor.focus import FocusMode, FocusLevel


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    doc = Document(title="Test Document")
    
    # Add a chapter
    chapter = doc.add_section("Chapter 1: The Beginning")
    
    # Add some paragraphs
    chapter.add_segment("Once upon a time, in a land far away, there lived a young writer named Elena.")
    chapter.add_segment("Elena had always dreamed of becoming a famous author, crafting tales of adventure and romance.")
    chapter.add_segment("She spent her days typing away on her laptop, lost in the worlds of her own creation.")
    
    # Add another chapter
    chapter2 = doc.add_section("Chapter 2: The Journey")
    
    # Add some paragraphs
    chapter2.add_segment("As Elena continued to write, she found herself facing a difficult challenge.")
    chapter2.add_segment("Her stories were good, but they lacked the focus and clarity she desired.")
    chapter2.add_segment("She needed a tool that would help her concentrate on one paragraph at a time.")
    
    return doc


def test_focus_mode_initialization(sample_document):
    """Test that focus mode initializes correctly."""
    focus_mode = FocusMode(sample_document)
    
    assert focus_mode.document == sample_document
    assert focus_mode.active_focus is None
    assert focus_mode.focus_history == []
    assert focus_mode.is_active() is False


def test_enter_focus(sample_document):
    """Test entering focus mode on a specific section and segment."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the first paragraph of the first chapter
    focus_context = focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    assert focus_mode.is_active() is True
    assert focus_context is not None
    assert focus_context.document == sample_document
    assert focus_context.section == sample_document.get_section(0)
    assert focus_context.segment == sample_document.get_section(0).get_segment(0)
    assert focus_context.level == FocusLevel.PARAGRAPH
    assert focus_mode.focus_history == [focus_context]


def test_enter_focus_invalid_indices(sample_document):
    """Test entering focus mode with invalid indices."""
    focus_mode = FocusMode(sample_document)
    
    # Try to enter focus on a non-existent section
    focus_context = focus_mode.enter_focus(
        section_index=5,  # Non-existent
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    assert focus_mode.is_active() is False
    assert focus_context is None
    
    # Try to enter focus on a non-existent segment
    focus_context = focus_mode.enter_focus(
        section_index=0,
        segment_index=5,  # Non-existent
        level=FocusLevel.PARAGRAPH
    )
    
    assert focus_mode.is_active() is False
    assert focus_context is None


def test_exit_focus(sample_document):
    """Test exiting focus mode."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    assert focus_mode.is_active() is True
    
    # Exit focus
    result = focus_mode.exit_focus()
    
    assert result is True
    assert focus_mode.is_active() is False
    assert focus_mode.active_focus is None
    
    # Try to exit focus again (should return False)
    result = focus_mode.exit_focus()
    
    assert result is False


def test_move_focus_within_section(sample_document):
    """Test moving focus to the next or previous segment within the same section."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the first paragraph
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    # Move to the next paragraph
    focus_context = focus_mode.move_focus(direction=1)
    
    assert focus_context is not None
    assert focus_context.section == sample_document.get_section(0)
    assert focus_context.segment == sample_document.get_section(0).get_segment(1)
    
    # Move to the next paragraph again
    focus_context = focus_mode.move_focus(direction=1)
    
    assert focus_context is not None
    assert focus_context.section == sample_document.get_section(0)
    assert focus_context.segment == sample_document.get_section(0).get_segment(2)
    
    # Move back to the previous paragraph
    focus_context = focus_mode.move_focus(direction=-1)
    
    assert focus_context is not None
    assert focus_context.section == sample_document.get_section(0)
    assert focus_context.segment == sample_document.get_section(0).get_segment(1)


def test_move_focus_between_sections(sample_document):
    """Test moving focus from the last segment of one section to the first segment of the next section."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the last paragraph of the first chapter
    focus_mode.enter_focus(
        section_index=0,
        segment_index=2,  # Last paragraph in chapter 1
        level=FocusLevel.PARAGRAPH
    )
    
    # Move to the next paragraph (should go to the first paragraph of chapter 2)
    focus_context = focus_mode.move_focus(direction=1)
    
    assert focus_context is not None
    assert focus_context.section == sample_document.get_section(1)  # Chapter 2
    assert focus_context.segment == sample_document.get_section(1).get_segment(0)  # First paragraph
    
    # Move back to the previous paragraph (should go back to the last paragraph of chapter 1)
    focus_context = focus_mode.move_focus(direction=-1)
    
    assert focus_context is not None
    assert focus_context.section == sample_document.get_section(0)  # Chapter 1
    assert focus_context.segment == sample_document.get_section(0).get_segment(2)  # Last paragraph


def test_move_focus_edge_cases(sample_document):
    """Test moving focus in edge cases (beyond document boundaries)."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the first paragraph of the first chapter
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    # Try to move to the previous paragraph (should return None)
    focus_context = focus_mode.move_focus(direction=-1)
    
    assert focus_context is None
    
    # Enter focus on the last paragraph of the last chapter
    focus_mode.enter_focus(
        section_index=1,  # Last chapter
        segment_index=2,  # Last paragraph
        level=FocusLevel.PARAGRAPH
    )
    
    # Try to move to the next paragraph (should return None)
    focus_context = focus_mode.move_focus(direction=1)
    
    assert focus_context is None


def test_change_focus_level(sample_document):
    """Test changing the focus level."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the first paragraph
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    assert focus_mode.active_focus.level == FocusLevel.PARAGRAPH
    
    # Change to sentence level
    focus_context = focus_mode.change_focus_level(FocusLevel.SENTENCE)
    
    assert focus_context is not None
    assert focus_context.level == FocusLevel.SENTENCE
    
    # Change to section level
    focus_context = focus_mode.change_focus_level(FocusLevel.SECTION)
    
    assert focus_context is not None
    assert focus_context.level == FocusLevel.SECTION


def test_edit_focused_content(sample_document):
    """Test editing the content of the focused segment."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the first paragraph
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    # Edit the content
    new_content = "Once upon a time, in a magical kingdom, there lived a talented writer named Elena."
    result = focus_mode.edit_focused_content(new_content)
    
    assert result is not None
    assert result.content == new_content
    assert sample_document.get_section(0).get_segment(0).content == new_content


def test_edit_focused_content_not_active(sample_document):
    """Test editing content when focus mode is not active."""
    focus_mode = FocusMode(sample_document)
    
    # Try to edit without entering focus
    result = focus_mode.edit_focused_content("New content")
    
    assert result is None


def test_get_focus_time(sample_document):
    """Test getting the time spent in the current focus session."""
    focus_mode = FocusMode(sample_document)
    
    # When focus is not active
    assert focus_mode.get_focus_time() == 0.0
    
    # Enter focus
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    # Time should be greater than 0
    assert focus_mode.get_focus_time() >= 0.0


def test_get_surrounding_context(sample_document):
    """Test getting the surrounding segments around the focused segment."""
    focus_mode = FocusMode(sample_document)
    
    # Enter focus on the middle paragraph of chapter 1
    focus_mode.enter_focus(
        section_index=0,
        segment_index=1,  # Middle paragraph
        level=FocusLevel.PARAGRAPH
    )
    
    # Get surrounding context with default (2)
    context = focus_mode.get_surrounding_context()
    
    assert len(context) == 3  # All 3 paragraphs in chapter 1
    assert context[0] == sample_document.get_section(0).get_segment(0)
    assert context[1] == sample_document.get_section(0).get_segment(1)  # The focused segment
    assert context[2] == sample_document.get_section(0).get_segment(2)
    
    # Get surrounding context with custom size
    context = focus_mode.get_surrounding_context(context_size=1)
    
    assert len(context) == 3  # Still 3 paragraphs (1 before, focused, 1 after)
    assert context[0] == sample_document.get_section(0).get_segment(0)
    assert context[1] == sample_document.get_section(0).get_segment(1)  # The focused segment
    assert context[2] == sample_document.get_section(0).get_segment(2)


def test_get_surrounding_context_edge_cases(sample_document):
    """Test getting the surrounding context in edge cases."""
    focus_mode = FocusMode(sample_document)
    
    # No active focus
    assert focus_mode.get_surrounding_context() == []
    
    # First paragraph of chapter 1
    focus_mode.enter_focus(
        section_index=0,
        segment_index=0,
        level=FocusLevel.PARAGRAPH
    )
    
    context = focus_mode.get_surrounding_context(context_size=1)
    assert len(context) == 2  # Only the focused and the next segment
    
    # Last paragraph of chapter 1
    focus_mode.enter_focus(
        section_index=0,
        segment_index=2,
        level=FocusLevel.PARAGRAPH
    )
    
    context = focus_mode.get_surrounding_context(context_size=1)
    assert len(context) == 2  # Only the previous and the focused segment