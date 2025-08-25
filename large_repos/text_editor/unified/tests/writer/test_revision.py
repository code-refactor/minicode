"""Tests for the revision management system."""

import pytest
from datetime import datetime, timedelta
from writer_text_editor.document import Document, Section, TextSegment, Revision
from writer_text_editor.revision import RevisionManager, DiffType, RevisionDiff, SectionDiff, SegmentDiff


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    doc = Document(title="Test Document")
    
    # Add a chapter
    chapter = doc.add_section("Chapter 1: Introduction")
    
    # Add some paragraphs
    chapter.add_segment("This is the first paragraph of the introduction.")
    chapter.add_segment("This is the second paragraph with more details.")
    
    # Add another chapter
    chapter2 = doc.add_section("Chapter 2: Development")
    
    # Add paragraphs
    chapter2.add_segment("The story continues with interesting developments.")
    chapter2.add_segment("Characters face challenges and grow through experiences.")
    
    return doc


@pytest.fixture
def revision_manager(sample_document):
    """Create a revision manager for testing."""
    return RevisionManager(sample_document)


def test_initialization(revision_manager, sample_document):
    """Test that the revision manager initializes correctly."""
    assert revision_manager.document == sample_document
    assert revision_manager.diffs == {}


def test_create_revision(revision_manager, sample_document):
    """Test creating a new revision."""
    original_revision_name = sample_document.current_revision.name
    
    # Create a new revision
    new_revision = revision_manager.create_revision("Draft 2", {"notes": "Added more details"})
    
    assert "Draft 2" in sample_document.revisions
    assert sample_document.revisions["Draft 2"] == new_revision
    assert sample_document.current_revision == new_revision
    assert sample_document.current_revision.name == "Draft 2"
    assert sample_document.current_revision.metadata == {"notes": "Added more details"}
    
    # The new revision should be a copy of the original
    original_revision = sample_document.revisions[original_revision_name]
    assert len(new_revision.sections) == len(original_revision.sections)


def test_compare_revisions_identical(revision_manager, sample_document):
    """Test comparing two identical revisions."""
    # Create a new revision without changes
    revision_manager.create_revision("Draft 2")
    
    # Compare revisions
    diff = revision_manager.compare_revisions("Initial", "Draft 2")
    
    assert diff is not None
    assert diff.old_revision_name == "Initial"
    assert diff.new_revision_name == "Draft 2"
    
    # Since the revisions are identical, there should be no differences
    assert len(diff.section_diffs) == 0
    
    # The diff should be cached
    assert "Initial_Draft 2" in revision_manager.diffs
    assert revision_manager.diffs["Initial_Draft 2"] == diff


def test_compare_revisions_with_changes(revision_manager, sample_document):
    """Test comparing revisions with changes."""
    # Create a new revision
    new_revision = revision_manager.create_revision("Draft 2")
    
    # Make some changes
    # Change a section title
    section = new_revision.sections[0]
    section.title = "Chapter 1: Revised Introduction"
    
    # Change a paragraph
    segment = section.segments[0]
    segment.content = "This is the revised first paragraph of the introduction."
    
    # Add a new paragraph
    section.add_segment("This is a brand new paragraph added in the revision.")
    
    # Compare revisions
    diff = revision_manager.compare_revisions("Initial", "Draft 2")
    
    assert diff is not None
    assert diff.old_revision_name == "Initial"
    assert diff.new_revision_name == "Draft 2"
    
    # Check section diffs
    assert len(diff.section_diffs) > 0
    
    # Find the diff for the changed section
    section_diff = None
    for sd in diff.section_diffs:
        if sd.section_id == section.id:
            section_diff = sd
            break
    
    assert section_diff is not None
    assert section_diff.diff_type == DiffType.REPLACE
    assert section_diff.old_title == "Chapter 1: Introduction"
    assert section_diff.new_title == "Chapter 1: Revised Introduction"
    
    # Check for segment changes
    assert len(section_diff.segment_diffs) > 0
    
    # Should have both a replaced segment and an inserted segment
    has_replace = False
    has_insert = False
    
    for segment_diff in section_diff.segment_diffs:
        if segment_diff.diff_type == DiffType.REPLACE and segment_diff.segment_id == segment.id:
            has_replace = True
            assert segment_diff.old_content == "This is the first paragraph of the introduction."
            assert segment_diff.new_content == "This is the revised first paragraph of the introduction."
        
        elif segment_diff.diff_type == DiffType.INSERT:
            has_insert = True
            assert segment_diff.new_content == "This is a brand new paragraph added in the revision."
    
    assert has_replace
    assert has_insert


def test_compare_revisions_with_added_section(revision_manager, sample_document):
    """Test comparing revisions with an added section."""
    # Create a new revision
    new_revision = revision_manager.create_revision("Draft 2")
    
    # Add a new section
    new_section = Section(title="Chapter 3: New Content")
    new_section.add_segment("This is the first paragraph of the new chapter.")
    new_revision.sections.append(new_section)
    
    # Compare revisions
    diff = revision_manager.compare_revisions("Initial", "Draft 2")
    
    assert diff is not None
    
    # Check for the added section
    added_section_diff = None
    for section_diff in diff.section_diffs:
        if section_diff.diff_type == DiffType.INSERT and section_diff.section_id == new_section.id:
            added_section_diff = section_diff
            break
    
    assert added_section_diff is not None
    assert added_section_diff.new_title == "Chapter 3: New Content"
    
    # Check that the diff includes the section's segments
    assert len(added_section_diff.segment_diffs) == 1
    assert added_section_diff.segment_diffs[0].diff_type == DiffType.INSERT
    assert added_section_diff.segment_diffs[0].new_content == "This is the first paragraph of the new chapter."


def test_compare_revisions_with_removed_section(revision_manager, sample_document):
    """Test comparing revisions with a removed section."""
    # Create a new revision
    new_revision = revision_manager.create_revision("Draft 2")
    
    # Remove a section
    removed_section = new_revision.sections.pop(0)
    
    # Compare revisions
    diff = revision_manager.compare_revisions("Initial", "Draft 2")
    
    assert diff is not None
    
    # Check for the removed section
    removed_section_diff = None
    for section_diff in diff.section_diffs:
        if section_diff.diff_type == DiffType.DELETE and section_diff.section_id == removed_section.id:
            removed_section_diff = section_diff
            break
    
    assert removed_section_diff is not None
    assert removed_section_diff.old_title == "Chapter 1: Introduction"
    
    # Check that the diff includes the section's segments
    assert len(removed_section_diff.segment_diffs) == 2  # The section had 2 segments
    assert all(sd.diff_type == DiffType.DELETE for sd in removed_section_diff.segment_diffs)


def test_compare_nonexistent_revisions(revision_manager):
    """Test comparing revisions that don't exist."""
    # Try to compare revisions that don't exist
    diff = revision_manager.compare_revisions("Non-existent", "Also-non-existent")
    
    assert diff is None


def test_html_diff_generation(revision_manager):
    """Test generating an HTML diff of two texts."""
    old_text = "This is the original text."
    new_text = "This is the modified text."
    
    html_diff = revision_manager.get_html_diff(old_text, new_text)

    assert html_diff is not None
    assert isinstance(html_diff, str)
    assert "Old Version" in html_diff
    assert "New Version" in html_diff
    assert "<html>" in html_diff  # It should be HTML


def test_unified_diff_generation(revision_manager):
    """Test generating a unified diff of two texts."""
    old_text = "Line 1\nLine 2\nLine 3\n"
    new_text = "Line 1\nModified Line 2\nLine 3\n"
    
    unified_diff = revision_manager.get_unified_diff(old_text, new_text)
    
    assert unified_diff is not None
    assert isinstance(unified_diff, str)
    assert "-Line 2" in unified_diff
    assert "+Modified Line 2" in unified_diff


def test_detailed_segment_diff(revision_manager):
    """Test generating a detailed word-level diff of two segment contents."""
    old_content = "The quick brown fox jumps over the lazy dog."
    new_content = "The quick red fox leaps over the lazy dog."
    
    detailed_diff = revision_manager.get_detailed_segment_diff(old_content, new_content)
    
    assert detailed_diff is not None
    assert isinstance(detailed_diff, list)
    
    # Check for expected operations in the diff
    assert any(d["type"] == "equal" and d["content"] == "The quick" for d in detailed_diff)
    assert any(d["type"] == "delete" and "brown" in d["content"] for d in detailed_diff)
    assert any(d["type"] == "insert" and "red" in d["content"] for d in detailed_diff)
    assert any(d["type"] == "delete" and "jumps" in d["content"] for d in detailed_diff)
    assert any(d["type"] == "insert" and "leaps" in d["content"] for d in detailed_diff)
    assert any(d["type"] == "equal" and "over the lazy dog" in d["content"] for d in detailed_diff)


def test_apply_diff(revision_manager, sample_document):
    """Test applying a diff to create a new revision."""
    # Create a new revision with changes
    original_revision = sample_document.current_revision
    
    new_revision = revision_manager.create_revision("Draft 2")
    
    # Make some changes
    # Change a section title
    section = new_revision.sections[0]
    section.title = "Chapter 1: Revised Introduction"
    
    # Change a paragraph
    segment = section.segments[0]
    segment.content = "This is the revised first paragraph of the introduction."
    
    # Add a new paragraph
    section.add_segment("This is a brand new paragraph added in the revision.")
    
    # Compare revisions to get the diff
    diff = revision_manager.compare_revisions("Initial", "Draft 2")
    
    # Switch back to the original revision
    sample_document.current_revision = original_revision
    
    # Apply the diff to create a new revision
    result_revision = revision_manager.apply_diff(diff, "Applied Changes")
    
    assert result_revision is not None
    assert "Applied Changes" in sample_document.revisions
    assert sample_document.current_revision == result_revision
    
    # Verify the changes were applied
    assert result_revision.sections[0].title == "Chapter 1: Revised Introduction"
    assert result_revision.sections[0].segments[0].content == "This is the revised first paragraph of the introduction."
    assert len(result_revision.sections[0].segments) == 3  # Original 2 + 1 new
    assert result_revision.sections[0].segments[2].content == "This is a brand new paragraph added in the revision."


def test_merge_revisions(revision_manager, sample_document):
    """Test merging multiple revisions into a new revision."""
    # Create first revision with some changes
    first_revision = revision_manager.create_revision("Draft A")
    first_revision.sections[0].title = "Chapter 1: Version A"
    first_revision.sections[0].segments[0].content = "This is version A of the first paragraph."
    
    # Create second revision with different changes
    sample_document.current_revision = sample_document.revisions["Initial"]  # Go back to initial
    second_revision = revision_manager.create_revision("Draft B")
    second_revision.sections[1].title = "Chapter 2: Version B"
    second_revision.sections[1].segments[0].content = "This is version B of the development chapter."
    
    # Merge the revisions
    merged_revision = revision_manager.merge_revisions(
        base_revision_name="Initial",
        revision_names=["Draft A", "Draft B"],
        merge_strategy={}  # Use default strategy
    )
    
    assert merged_revision is not None
    assert merged_revision.name.startswith("Merged_")
    
    # The merged revision should contain changes from both drafts
    assert merged_revision.sections[0].title == "Chapter 1: Version A"
    assert merged_revision.sections[0].segments[0].content == "This is version A of the first paragraph."
    assert merged_revision.sections[1].title == "Chapter 2: Version B"
    assert merged_revision.sections[1].segments[0].content == "This is version B of the development chapter."


def test_export_revision_history(revision_manager, sample_document):
    """Test exporting the revision history."""
    # Create a few revisions
    revision_manager.create_revision("Draft 2")
    revision_manager.create_revision("Draft 3")
    
    # Export history
    history = revision_manager.export_revision_history()
    
    assert history is not None
    assert "current_revision" in history
    assert history["current_revision"] == "Draft 3"
    
    assert "revisions" in history
    assert "Initial" in history["revisions"]
    assert "Draft 2" in history["revisions"]
    assert "Draft 3" in history["revisions"]
    
    # Check revision details
    for name, revision_info in history["revisions"].items():
        assert "id" in revision_info
        assert "timestamp" in revision_info
        assert "section_count" in revision_info
        assert "word_count" in revision_info


def test_get_revision_by_timestamp(revision_manager, sample_document):
    """Test getting a revision closest to a specified timestamp."""
    # Create revisions with different timestamps
    first_revision = revision_manager.create_revision("Draft 2")
    first_time = first_revision.timestamp
    
    # Create a revision with a timestamp in the future
    future_time = datetime.now() + timedelta(days=1)
    second_revision = revision_manager.create_revision("Draft 3")
    second_revision.timestamp = future_time
    
    # Test getting revision by timestamp
    # Should get "Draft 2" when using a time close to first_time
    target_time = first_time + timedelta(minutes=5)
    result = revision_manager.get_revision_by_timestamp(target_time)
    
    assert result is not None
    assert result.name == "Draft 2"
    
    # Should get "Draft 3" when using a time close to future_time
    target_time = future_time - timedelta(minutes=5)
    result = revision_manager.get_revision_by_timestamp(target_time)
    
    assert result is not None
    assert result.name == "Draft 3"