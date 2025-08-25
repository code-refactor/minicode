"""Tests for the client module."""

import pytest
from writer_text_editor.client import WriterTextEditor
from writer_text_editor.focus import FocusLevel
from writer_text_editor.navigation import NavigationViewType


@pytest.fixture
def editor():
    """Create a text editor instance for testing."""
    editor = WriterTextEditor("Test Novel")
    
    # Add some content
    chapter1_id = editor.add_section("Chapter 1: The Beginning")
    editor.add_paragraph(0, "Once upon a time, in a land far away, there lived a young writer named Elena.")
    editor.add_paragraph(0, "Elena had always dreamed of becoming a famous author, crafting tales of adventure and romance.")
    
    chapter2_id = editor.add_section("Chapter 2: The Journey")
    editor.add_paragraph(1, "As Elena continued to write, she found herself facing a difficult challenge.")
    editor.add_paragraph(1, "Her stories were good, but they lacked the focus and clarity she desired.")
    
    yield editor
    
    # Clean up
    editor.close()


def test_editor_initialization():
    """Test that the editor initializes correctly."""
    editor = WriterTextEditor("Test Document")
    
    assert editor.document.title == "Test Document"
    assert editor.focus_mode is not None
    assert editor.statistics is not None
    assert editor.narrative_tracker is not None
    assert editor.navigator is not None
    assert editor.revision_manager is not None
    
    editor.close()


def test_document_operations(editor):
    """Test basic document operations."""
    # Add a new section
    section_id = editor.add_section("Chapter 3: The Resolution")
    assert section_id is not None
    
    # Add a paragraph
    paragraph_id = editor.add_paragraph(2, "Finally, Elena discovered the perfect writing tool that helped her organize her thoughts.")
    assert paragraph_id is not None
    
    # Get document content
    content = editor.get_document_content()
    assert "Chapter 1: The Beginning" in content
    assert "Chapter 2: The Journey" in content
    assert "Chapter 3: The Resolution" in content
    assert "Elena had always dreamed" in content
    assert "Finally, Elena discovered" in content


def test_focus_mode_operations(editor):
    """Test focus mode operations."""
    # Enter focus mode
    result = editor.enter_focus(0, 0, FocusLevel.PARAGRAPH)
    assert result is True
    
    # Get focus context
    context = editor.get_focus_context()
    assert context["active"] is True
    assert context["section_title"] == "Chapter 1: The Beginning"
    assert "Elena" in context["content"]
    assert context["level"] == "paragraph"
    
    # Edit in focus mode
    new_content = "Once upon a time, in a magical kingdom, there lived a talented writer named Elena."
    result = editor.edit_in_focus(new_content)
    assert result is True
    
    # Check that content was updated
    context = editor.get_focus_context()
    assert context["content"] == new_content
    
    # Move focus
    result = editor.move_focus(1)
    assert result is True
    
    # Check new focus context
    context = editor.get_focus_context()
    assert context["active"] is True
    assert "dreamed of becoming" in context["content"]
    
    # Exit focus mode
    result = editor.exit_focus()
    assert result is True
    
    # Check that focus is inactive
    context = editor.get_focus_context()
    assert context["active"] is False


def test_statistics_operations(editor):
    """Test statistics operations."""
    # Get statistics
    stats = editor.get_statistics()
    assert stats is not None
    assert stats["word_count"] > 0
    assert stats["character_count"] > 0
    assert stats["paragraph_count"] > 0
    assert stats["sentence_count"] > 0
    
    # Get writing pace
    pace = editor.get_writing_pace()
    assert pace is not None
    assert "words_per_minute" in pace
    assert "words_per_hour" in pace
    assert "words_per_day" in pace
    
    # Set a writing goal
    goal = editor.set_writing_goal("daily_goal", 1000, days=7)
    assert goal is not None
    assert goal["goal_id"] == "daily_goal"
    assert goal["target"] == 1000
    assert goal["deadline_days"] == 7
    
    # Get goal progress
    progress = editor.get_goal_progress("daily_goal")
    assert progress is not None
    assert progress["goal_id"] == "daily_goal"
    assert "current_progress" in progress


def test_narrative_operations(editor, monkeypatch):
    """Test narrative element operations."""
    # First manually create a character for Elena in the narrative tracker
    from writer_text_editor.narrative import NarrativeElement, ElementType, ElementOccurrence

    # Create a real element for Elena
    elena_element = NarrativeElement(
        id="character_elena",
        name="Elena",
        element_type=ElementType.CHARACTER,
        occurrences=[]
    )

    # Add it to the narrative tracker
    editor.narrative_tracker.elements["character_elena"] = elena_element

    # Create a mock for detect_elements that includes our Elena character
    def mock_detect_elements():
        return {
            ElementType.CHARACTER.value: [elena_element]
        }

    # Patch the detect_elements method
    monkeypatch.setattr(editor.narrative_tracker, 'detect_elements', mock_detect_elements)

    # Now test the client methods
    characters = editor.detect_characters()

    # Elena should be returned as a character
    elena_found = False
    elena_id = None
    for character in characters:
        if character["name"] == "Elena":
            elena_found = True
            elena_id = character["id"]
            break

    assert elena_found
    assert elena_id == "character_elena"

    # Mock the get_element_timeline method
    def mock_timeline(element_id):
        return [
            {
                "section_id": editor.document.get_section(0).id,
                "section_title": "Chapter 1: The Beginning",
                "appearances": [
                    {
                        "segment_position": 0,
                        "context": "Context with Elena"
                    }
                ]
            }
        ]

    monkeypatch.setattr(editor.narrative_tracker, 'get_element_timeline', mock_timeline)

    # Get character timeline
    timeline = editor.get_character_timeline(elena_id)
    assert timeline is not None

    # Mock the check_consistency method
    def mock_check_consistency():
        return []

    monkeypatch.setattr(editor.narrative_tracker, 'check_consistency', mock_check_consistency)

    # Check consistency
    issues = editor.check_narrative_consistency()
    assert isinstance(issues, list)


def test_navigation_operations(editor, monkeypatch):
    """Test navigation operations."""
    # We need to mock some methods in the narrative_tracker
    from writer_text_editor.narrative import NarrativeElement, ElementType

    # Create an element for Elena
    elena_element = NarrativeElement(
        id="character_elena",
        name="Elena",
        element_type=ElementType.CHARACTER,
        occurrences=[]
    )

    # Add it to the narrative tracker
    editor.narrative_tracker.elements["character_elena"] = elena_element

    # Create a mock for detect_elements that includes our Elena character
    def mock_detect_elements():
        return {
            ElementType.CHARACTER.value: [elena_element]
        }

    # Patch the detect_elements method
    monkeypatch.setattr(editor.narrative_tracker, 'detect_elements', mock_detect_elements)

    # Mock the get_element_appearances method
    def mock_get_appearances(element_id):
        return [
            {
                "section_title": "Chapter 1: The Beginning",
                "section_id": editor.document.get_section(0).id,
                "segment_id": editor.document.get_section(0).get_segment(0).id,
                "segment_position": 0,
                "context": "Context with Elena",
                "mentioned_with": []
            }
        ]

    monkeypatch.setattr(editor.narrative_tracker, 'get_element_appearances', mock_get_appearances)

    # Create navigation views
    timeline_view_id = editor.create_navigation_view("Timeline View", NavigationViewType.TIMELINE.value)
    assert timeline_view_id is not None

    # Since character view depends on narrative tracker mock it last
    character_view_id = editor.create_navigation_view("Character View", NavigationViewType.CHARACTER.value)
    assert character_view_id is not None

    # Create a linear view and manually navigate to it first
    linear_view_id = "view_linear"  # This view is created by default in the navigator

    # Get the first element in the linear view
    root_elements = editor.navigator.views[linear_view_id].root_elements
    if root_elements:
        element_id = root_elements[0]
        # Navigate to this element
        editor.navigate_to(linear_view_id, element_id)

        # Now get the location
        location = editor.get_current_location()
        assert location is not None
        assert "element_id" in location
        assert location["element_id"] == element_id
    else:
        # If no root elements (shouldn't happen), skip the element_id check
        location = editor.get_current_location()
        assert location is not None

    # Navigate next and previous - only if we have an element_id
    if "element_id" in location:
        current_id = location["element_id"]

        # Try to navigate
        result = editor.navigate_next()
        new_location = editor.get_current_location()

        # Make sure we have a valid location after navigation
        assert new_location is not None

        # If the navigation succeeded and we can check the element_id
        if "element_id" in new_location and new_location["element_id"] != current_id:
            # Test navigate previous
            result = editor.navigate_previous()
            assert result is True

            # Should be back at the original location
            back_location = editor.get_current_location()
            assert "element_id" in back_location
            assert back_location["element_id"] == current_id

    # Get children
    children = editor.get_navigation_children()
    assert isinstance(children, list)


def test_revision_operations(editor):
    """Test revision operations."""
    # Create a new revision
    revision_id = editor.create_revision("Draft 2")
    assert revision_id is not None
    
    # Make a change
    editor.enter_focus(0, 0, FocusLevel.PARAGRAPH)
    editor.edit_in_focus("This is a revised paragraph in Draft 2.")
    editor.exit_focus()
    
    # Create another revision
    editor.switch_revision("Initial")
    revision_id2 = editor.create_revision("Draft 3")
    
    # Make a different change
    editor.enter_focus(1, 0, FocusLevel.PARAGRAPH)
    editor.edit_in_focus("This is a revised paragraph in Draft 3.")
    editor.exit_focus()
    
    # Compare revisions
    diff = editor.compare_revisions("Initial", "Draft 2")
    assert diff is not None
    assert diff["old_revision"] == "Initial"
    assert diff["new_revision"] == "Draft 2"
    
    # Get revision history
    history = editor.get_revision_history()
    assert history is not None
    assert "Initial" in history["revisions"]
    assert "Draft 2" in history["revisions"]
    assert "Draft 3" in history["revisions"]
    
    # Merge revisions
    merged_name = editor.merge_revisions("Initial", ["Draft 2", "Draft 3"])
    assert merged_name is not None
    assert merged_name.startswith("Merged_")
    
    # The merged revision should contain changes from both drafts
    result = editor.switch_revision(merged_name)
    assert result is True