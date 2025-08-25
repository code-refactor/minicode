"""Tests for the document model."""

import pytest
from datetime import datetime
from writer_text_editor.document import Document, Section, TextSegment, Revision


def test_text_segment():
    """Test the TextSegment class."""
    segment = TextSegment(content="This is a test paragraph.", position=0)
    
    assert segment.content == "This is a test paragraph."
    assert segment.position == 0
    assert segment.id is not None
    
    # Test word count
    assert segment.get_word_count() == 5


def test_section():
    """Test the Section class."""
    section = Section(title="Test Section")
    
    assert section.title == "Test Section"
    assert section.segments == []
    assert section.id is not None
    
    # Add segments
    segment1 = section.add_segment("First paragraph.")
    segment2 = section.add_segment("Second paragraph with more words.")
    
    assert len(section.segments) == 2
    assert segment1.position == 0
    assert segment2.position == 1
    
    # Test get_content
    assert section.get_content() == "First paragraph.\nSecond paragraph with more words."
    
    # Test get_word_count
    assert section.get_word_count() == 7  # 2 + 5
    
    # Test get_segment
    assert section.get_segment(0) == segment1
    assert section.get_segment(1) == segment2
    assert section.get_segment(2) is None
    
    # Test update_segment
    updated_segment = section.update_segment(0, "Updated first paragraph.")
    assert updated_segment == segment1
    assert segment1.content == "Updated first paragraph."
    
    # Test delete_segment
    assert section.delete_segment(0) is True
    assert len(section.segments) == 1
    assert section.segments[0] == segment2
    assert section.segments[0].position == 0  # Position should be updated
    
    # Test delete non-existent segment
    assert section.delete_segment(5) is False


def test_document():
    """Test the Document class."""
    doc = Document(title="Test Document")
    
    assert doc.title == "Test Document"
    assert doc.id is not None
    assert doc.created_at <= datetime.now()
    assert doc.updated_at <= datetime.now()
    
    # Current revision
    assert doc.current_revision is not None
    assert doc.current_revision.name == "Initial"
    assert "Initial" in doc.revisions
    
    # Add sections
    section1 = doc.add_section("Chapter 1")
    section2 = doc.add_section("Chapter 2")
    
    assert len(doc.current_revision.sections) == 2
    assert doc.current_revision.sections[0] == section1
    assert doc.current_revision.sections[1] == section2
    
    # Add content to sections
    section1.add_segment("Chapter 1, Paragraph 1.")
    section1.add_segment("Chapter 1, Paragraph 2.")
    section2.add_segment("Chapter 2, Paragraph 1.")
    
    # Test get_word_count
    assert doc.get_word_count() == 12  # 3 + 3 + 3 + 3
    
    # Test get_section
    assert doc.get_section(0) == section1
    assert doc.get_section(1) == section2
    assert doc.get_section(2) is None
    
    # Test get_section_by_title
    assert doc.get_section_by_title("Chapter 1") == section1
    assert doc.get_section_by_title("Chapter 2") == section2
    assert doc.get_section_by_title("Non-existent") is None
    
    # Test update_section_title
    updated_section = doc.update_section_title(0, "Updated Chapter 1")
    assert updated_section == section1
    assert section1.title == "Updated Chapter 1"
    
    # Test delete_section
    assert doc.delete_section(1) is True
    assert len(doc.current_revision.sections) == 1
    assert doc.current_revision.sections[0] == section1
    
    # Test create_revision
    new_revision = doc.create_revision("Draft 2")
    assert new_revision.name == "Draft 2"
    assert doc.current_revision == new_revision
    assert "Draft 2" in doc.revisions
    
    # Test get_revision
    assert doc.get_revision("Initial") is not None
    assert doc.get_revision("Draft 2") == new_revision
    assert doc.get_revision("Non-existent") is None
    
    # Test switch_to_revision
    assert doc.switch_to_revision("Initial") is True
    assert doc.current_revision == doc.revisions["Initial"]
    assert doc.switch_to_revision("Non-existent") is False
    
    # Test get_content
    assert "# Updated Chapter 1" in doc.get_content()
    assert "Chapter 1, Paragraph 1." in doc.get_content()
    assert "Chapter 1, Paragraph 2." in doc.get_content()
    
    # Test find_segments_by_content
    results = doc.find_segments_by_content("Paragraph 1")
    assert len(results) == 1
    assert results[0][0] == section1
    assert results[0][1].content == "Chapter 1, Paragraph 1."