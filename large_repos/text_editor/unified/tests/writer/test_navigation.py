"""Tests for the non-linear document navigation system."""

import pytest
from unittest.mock import MagicMock
from writer_text_editor.document import Document, Section, TextSegment
from writer_text_editor.navigation import (
    DocumentNavigator, NavigationViewType, NavigationTag,
    NavigationLink, NavigationElement, NavigationView
)
from writer_text_editor.narrative import NarrativeTracker, ElementType


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    doc = Document(title="Test Document")
    
    # Add chapters
    chapter1 = doc.add_section("Chapter 1: Introduction")
    chapter1.add_segment("This is the first paragraph of chapter 1.")
    chapter1.add_segment("This is the second paragraph of chapter 1.")
    
    chapter2 = doc.add_section("Chapter 2: Development")
    chapter2.add_segment("This is the first paragraph of chapter 2.")
    chapter2.add_segment("This is the second paragraph of chapter 2.")
    
    chapter3 = doc.add_section("Chapter 3: Conclusion")
    chapter3.add_segment("This is the first paragraph of chapter 3.")
    chapter3.add_segment("This is the second paragraph of chapter 3.")
    
    return doc


@pytest.fixture
def mock_narrative_tracker(sample_document):
    """Create a mock narrative tracker for testing."""
    tracker = MagicMock(spec=NarrativeTracker)
    tracker.document = sample_document

    # Create real Element objects instead of MagicMocks
    from writer_text_editor.narrative import NarrativeElement, ElementOccurrence

    # Mock some elements
    element1 = NarrativeElement(
        id="character_1",
        name="Sarah",
        element_type=ElementType.CHARACTER,
        occurrences=[]
    )

    element2 = NarrativeElement(
        id="character_2",
        name="John",
        element_type=ElementType.CHARACTER,
        occurrences=[]
    )

    element3 = NarrativeElement(
        id="location_1",
        name="The Castle",
        element_type=ElementType.LOCATION,
        occurrences=[]
    )

    elements = {
        "character_1": element1,
        "character_2": element2,
        "location_1": element3
    }

    tracker.elements = elements

    # Mock get_element_appearances
    def mock_get_appearances(element_id):
        return [
            {
                "section_title": "Chapter 1: Introduction",
                "section_id": sample_document.get_section(0).id,
                "segment_id": sample_document.get_section(0).get_segment(0).id,
                "segment_position": 0,
                "context": "Context with " + elements[element_id].name,
                "mentioned_with": []
            },
            {
                "section_title": "Chapter 3: Conclusion",
                "section_id": sample_document.get_section(2).id,
                "segment_id": sample_document.get_section(2).get_segment(1).id,
                "segment_position": 1,
                "context": "More context with " + elements[element_id].name,
                "mentioned_with": []
            }
        ]

    tracker.get_element_appearances.side_effect = mock_get_appearances

    # Mock get_element_timeline
    def mock_get_timeline(element_id):
        appearances = mock_get_appearances(element_id)
        sections = {}

        for appearance in appearances:
            section_id = appearance["section_id"]
            if section_id not in sections:
                sections[section_id] = {
                    "section_title": appearance["section_title"],
                    "appearances": []
                }
            sections[section_id]["appearances"].append(appearance)

        return [
            {
                "section_id": section_id,
                "section_title": info["section_title"],
                "appearances": sorted(info["appearances"], key=lambda a: a["segment_position"])
            }
            for section_id, info in sections.items()
        ]

    tracker.get_element_timeline.side_effect = mock_get_timeline

    return tracker


@pytest.fixture
def navigator(sample_document, mock_narrative_tracker):
    """Create a document navigator for testing."""
    return DocumentNavigator(sample_document, mock_narrative_tracker)


def test_navigator_initialization(navigator, sample_document):
    """Test that the navigator initializes correctly with a linear view."""
    assert navigator.document == sample_document
    assert "view_linear" in navigator.views
    assert navigator.views["view_linear"].view_type == NavigationViewType.LINEAR
    
    # Should have elements for each section and segment
    assert len(navigator.elements) > 0
    
    # Linear view should have root elements for each section
    linear_view = navigator.views["view_linear"]
    assert len(linear_view.root_elements) == 3  # 3 chapters
    
    # Current position should be set to the first section if available
    assert navigator.current_position is not None
    assert navigator.current_position.view_id == "view_linear"
    assert navigator.current_position.element_id == linear_view.root_elements[0]


def test_create_character_view(navigator, mock_narrative_tracker):
    """Test creating a view organized by characters."""
    character_view_id = navigator.create_view("Character View", NavigationViewType.CHARACTER)
    
    assert character_view_id == "view_character"
    assert character_view_id in navigator.views
    assert navigator.views[character_view_id].view_type == NavigationViewType.CHARACTER
    
    # Should have elements for each character
    character_view = navigator.views[character_view_id]
    assert len(character_view.root_elements) > 0
    
    # Each root element should be a character
    for element_id in character_view.root_elements:
        element = navigator.elements[element_id]
        assert element.element_type == "character"
        
        # Each character should have children for sections they appear in
        assert len(element.children) > 0


def test_create_plot_view(navigator, mock_narrative_tracker):
    """Test creating a view organized by plot elements."""
    plot_view_id = navigator.create_view("Plot View", NavigationViewType.PLOT)
    
    assert plot_view_id == "view_plot"
    assert plot_view_id in navigator.views
    assert navigator.views[plot_view_id].view_type == NavigationViewType.PLOT


def test_create_timeline_view(navigator, sample_document):
    """Test creating a view organized by timeline/chronology."""
    # Add timeline metadata to sections
    for i, section in enumerate(sample_document.current_revision.sections):
        section.metadata["timeline"] = f"Day {i+1}"
    
    timeline_view_id = navigator.create_view("Timeline View", NavigationViewType.TIMELINE)
    
    assert timeline_view_id == "view_timeline"
    assert timeline_view_id in navigator.views
    assert navigator.views[timeline_view_id].view_type == NavigationViewType.TIMELINE
    
    # Timeline view should organize sections by timeline value
    timeline_view = navigator.views[timeline_view_id]
    
    # Check that section elements have timeline info in their names
    for element_id in timeline_view.root_elements:
        element = navigator.elements[element_id]
        assert "Day" in element.name
        
        # Each element should have children (segments)
        assert len(element.children) > 0


def test_create_custom_view(navigator):
    """Test creating a custom view."""
    custom_view_id = navigator.create_view("Custom View", NavigationViewType.CUSTOM)
    
    assert custom_view_id.startswith("view_custom")
    assert custom_view_id in navigator.views
    assert navigator.views[custom_view_id].view_type == NavigationViewType.CUSTOM
    assert navigator.views[custom_view_id].name == "Custom View"


def test_create_tag(navigator):
    """Test creating a new tag for navigation elements."""
    tag_id = navigator.create_tag("Important Scene", "#FF0000")
    
    assert tag_id in navigator.tags
    assert navigator.tags[tag_id].name == "Important Scene"
    assert navigator.tags[tag_id].color == "#FF0000"


def test_add_tag_to_element(navigator):
    """Test adding a tag to a navigation element."""
    # Create a tag
    tag_id = navigator.create_tag("Important")
    
    # Get an element ID from the linear view
    linear_view = navigator.views["view_linear"]
    element_id = linear_view.root_elements[0]
    
    # Add the tag to the element
    result = navigator.add_tag_to_element(element_id, tag_id)
    
    assert result is True
    assert tag_id in navigator.elements[element_id].tags
    
    # Try with invalid IDs
    assert navigator.add_tag_to_element("non_existent_element", tag_id) is False
    assert navigator.add_tag_to_element(element_id, "non_existent_tag") is False


def test_create_link(navigator):
    """Test creating a link between two navigation elements."""
    # Get two element IDs from the linear view
    linear_view = navigator.views["view_linear"]
    source_id = linear_view.root_elements[0]
    target_id = linear_view.root_elements[1]
    
    # Create a link
    link_id = navigator.create_link(
        source_type="section",
        source_id=source_id,
        target_type="section",
        target_id=target_id,
        link_type="follows"
    )
    
    assert link_id in navigator.links
    assert navigator.links[link_id].source_id == source_id
    assert navigator.links[link_id].target_id == target_id
    assert navigator.links[link_id].link_type == "follows"


def test_add_element_to_view(navigator):
    """Test adding an element to a view."""
    # Create a custom view
    view_id = navigator.create_view("Custom View", NavigationViewType.CUSTOM)
    
    # Get an element ID from the linear view
    linear_view = navigator.views["view_linear"]
    element_id = linear_view.root_elements[0]
    
    # Add the element to the custom view
    result = navigator.add_element_to_view(view_id, element_id)
    
    assert result is True
    assert element_id in navigator.views[view_id].root_elements
    
    # Get another element
    child_element_id = navigator.elements[element_id].children[0]
    
    # Add it as a child of the first element in the custom view
    result = navigator.add_element_to_view(view_id, child_element_id, parent_id=element_id)
    
    assert result is True
    assert child_element_id in navigator.elements[element_id].children
    
    # Try with invalid IDs
    assert navigator.add_element_to_view("non_existent_view", element_id) is False
    assert navigator.add_element_to_view(view_id, "non_existent_element") is False
    assert navigator.add_element_to_view(view_id, element_id, "non_existent_parent") is False


def test_get_current_element(navigator):
    """Test getting the current navigation element."""
    current_element = navigator.get_current_element()
    
    assert current_element is not None
    assert current_element.id == navigator.current_position.element_id
    
    # Test with no current position
    navigator.current_position = None
    assert navigator.get_current_element() is None


def test_get_element_content(navigator, sample_document):
    """Test getting the content of a navigation element."""
    # Get a section element
    linear_view = navigator.views["view_linear"]
    section_element_id = linear_view.root_elements[0]
    section_element = navigator.elements[section_element_id]
    
    # Get content
    content = navigator.get_element_content(section_element_id)
    
    assert content is not None
    assert "first paragraph of chapter 1" in content
    assert "second paragraph of chapter 1" in content
    
    # Get a segment element
    segment_element_id = section_element.children[0]
    
    # Get content
    content = navigator.get_element_content(segment_element_id)
    
    assert content is not None
    assert "first paragraph of chapter 1" in content
    
    # Try with invalid ID
    assert navigator.get_element_content("non_existent_element") is None
    
    # Try with element with no original ID
    custom_element = NavigationElement(
        id="custom_element",
        element_type="custom",
        name="Custom Element"
    )
    navigator.elements["custom_element"] = custom_element
    assert navigator.get_element_content("custom_element") is None


def test_navigate_to(navigator):
    """Test navigating to a specific element in a view."""
    # Get an element ID from the linear view
    linear_view = navigator.views["view_linear"]
    element_id = linear_view.root_elements[1]  # Second chapter
    
    # Navigate to it
    result = navigator.navigate_to("view_linear", element_id)
    
    assert result is True
    assert navigator.current_position.view_id == "view_linear"
    assert navigator.current_position.element_id == element_id
    
    # Try with invalid IDs
    assert navigator.navigate_to("non_existent_view", element_id) is False
    assert navigator.navigate_to("view_linear", "non_existent_element") is False


def test_navigate_to_related(navigator):
    """Test navigating to elements related to the current element."""
    # Set up: create some links
    linear_view = navigator.views["view_linear"]
    source_id = linear_view.root_elements[0]
    target_id = linear_view.root_elements[1]
    
    navigator.create_link(
        source_type="section",
        source_id=source_id,
        target_type="section",
        target_id=target_id,
        link_type="follows"
    )
    
    # Navigate to the source element
    navigator.navigate_to("view_linear", source_id)
    
    # Get related elements
    related_elements = navigator.navigate_to_related()
    
    assert len(related_elements) == 1
    assert related_elements[0].id == target_id
    
    # Get related elements with specific link type
    related_elements = navigator.navigate_to_related(link_type="follows")
    
    assert len(related_elements) == 1
    assert related_elements[0].id == target_id
    
    # Get related elements with non-existent link type
    related_elements = navigator.navigate_to_related(link_type="non_existent")
    
    assert len(related_elements) == 0


def test_navigate_parent(navigator):
    """Test navigating to the parent of the current element."""
    # Navigate to a child element first
    linear_view = navigator.views["view_linear"]
    section_element_id = linear_view.root_elements[0]
    section_element = navigator.elements[section_element_id]
    segment_element_id = section_element.children[0]
    
    navigator.navigate_to("view_linear", segment_element_id)
    
    # Navigate to parent
    result = navigator.navigate_parent()
    
    assert result is True
    assert navigator.current_position.element_id == section_element_id
    
    # Try to navigate to parent of root element (should return False)
    navigator.navigate_to("view_linear", section_element_id)
    result = navigator.navigate_parent()
    
    assert result is False
    
    # Try with no current position
    navigator.current_position = None
    assert navigator.navigate_parent() is False


def test_navigate_next(navigator):
    """Test navigating to the next element at the same level."""
    # Navigate to the first root element
    linear_view = navigator.views["view_linear"]
    first_element_id = linear_view.root_elements[0]
    
    navigator.navigate_to("view_linear", first_element_id)
    
    # Navigate to next
    result = navigator.navigate_next()
    
    assert result is True
    assert navigator.current_position.element_id == linear_view.root_elements[1]
    
    # Navigate to last element
    last_element_id = linear_view.root_elements[-1]
    navigator.navigate_to("view_linear", last_element_id)
    
    # Try to navigate next (should return False)
    result = navigator.navigate_next()
    
    assert result is False
    
    # Try with no current position
    navigator.current_position = None
    assert navigator.navigate_next() is False


def test_navigate_previous(navigator):
    """Test navigating to the previous element at the same level."""
    # Navigate to the second root element
    linear_view = navigator.views["view_linear"]
    second_element_id = linear_view.root_elements[1]
    
    navigator.navigate_to("view_linear", second_element_id)
    
    # Navigate to previous
    result = navigator.navigate_previous()
    
    assert result is True
    assert navigator.current_position.element_id == linear_view.root_elements[0]
    
    # Navigate to first element
    first_element_id = linear_view.root_elements[0]
    navigator.navigate_to("view_linear", first_element_id)
    
    # Try to navigate previous (should return False)
    result = navigator.navigate_previous()
    
    assert result is False
    
    # Try with no current position
    navigator.current_position = None
    assert navigator.navigate_previous() is False


def test_navigate_children(navigator):
    """Test getting the children of the current element."""
    # Navigate to a section element
    linear_view = navigator.views["view_linear"]
    section_element_id = linear_view.root_elements[0]
    section_element = navigator.elements[section_element_id]
    
    navigator.navigate_to("view_linear", section_element_id)
    
    # Get children
    children = navigator.navigate_children()
    
    assert len(children) == len(section_element.children)
    for i, child_id in enumerate(section_element.children):
        assert children[i].id == child_id
    
    # Try with element that has no children
    segment_element_id = section_element.children[0]
    navigator.navigate_to("view_linear", segment_element_id)
    children = navigator.navigate_children()
    
    assert len(children) == 0
    
    # Try with no current position
    navigator.current_position = None
    assert navigator.navigate_children() == []


def test_find_elements_by_tag(navigator):
    """Test finding all elements with a specific tag."""
    # Create a tag
    tag_id = navigator.create_tag("Important")
    
    # Add the tag to some elements
    linear_view = navigator.views["view_linear"]
    element_ids = linear_view.root_elements[:2]  # First two chapters
    
    for element_id in element_ids:
        navigator.add_tag_to_element(element_id, tag_id)
    
    # Find elements with the tag
    tagged_elements = navigator.find_elements_by_tag(tag_id)
    
    assert len(tagged_elements) == 2
    assert tagged_elements[0].id in element_ids
    assert tagged_elements[1].id in element_ids
    
    # Try with non-existent tag
    assert navigator.find_elements_by_tag("non_existent_tag") == []


def test_find_elements_by_name(navigator):
    """Test finding elements by name."""
    # Find elements with "Chapter" in their name
    matching_elements = navigator.find_elements_by_name("Chapter")
    
    assert len(matching_elements) >= 3  # At least 3 chapters
    
    # Find elements with "Introduction" in their name
    matching_elements = navigator.find_elements_by_name("Introduction")
    
    assert len(matching_elements) >= 1
    assert "Introduction" in matching_elements[0].name
    
    # Try with non-existent name
    assert len(navigator.find_elements_by_name("non_existent_name")) == 0


def test_get_path_to_element(navigator):
    """Test getting the path from root to a specified element."""
    # Get a section element and one of its children
    linear_view = navigator.views["view_linear"]
    section_element_id = linear_view.root_elements[0]
    section_element = navigator.elements[section_element_id]
    segment_element_id = section_element.children[0]
    
    # Get path to section (should be just the section)
    path = navigator.get_path_to_element(section_element_id)
    
    assert len(path) == 1
    assert path[0] == section_element_id
    
    # Get path to segment (should be section -> segment)
    path = navigator.get_path_to_element(segment_element_id)
    
    assert len(path) == 2
    assert path[0] == section_element_id
    assert path[1] == segment_element_id
    
    # Try with non-existent element
    assert navigator.get_path_to_element("non_existent_element") == []