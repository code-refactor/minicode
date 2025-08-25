"""Non-linear document navigation system for the writer text editor."""

from __future__ import annotations
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from pydantic import BaseModel, Field

from writer_text_editor.document import Document, Section, TextSegment
from writer_text_editor.narrative import NarrativeTracker, ElementType, NarrativeElement


class NavigationViewType(str, Enum):
    """Types of navigation views."""
    
    LINEAR = "linear"  # Traditional linear document view
    CHAPTER = "chapter"  # Organized by chapters/sections
    CHARACTER = "character"  # Organized by character appearances
    PLOT = "plot"  # Organized by plot elements/arcs
    TIMELINE = "timeline"  # Organized by timeline/chronology
    CUSTOM = "custom"  # Custom organization


class NavigationTag(BaseModel):
    """A tag for organizing document content."""
    
    id: str
    name: str
    color: str = "#CCCCCC"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NavigationLink(BaseModel):
    """A link between two document elements."""
    
    id: str
    source_type: str  # "section", "segment", "tag"
    source_id: str
    target_type: str  # "section", "segment", "tag" 
    target_id: str
    link_type: str  # "related", "follows", "references", etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NavigationElement(BaseModel):
    """An element in the navigation structure."""
    
    id: str
    element_type: str  # "section", "segment", "tag", "character", "plot", etc.
    name: str
    original_id: Optional[str] = None  # Original section/segment ID if applicable
    children: List[str] = Field(default_factory=list)  # Child element IDs
    tags: List[str] = Field(default_factory=list)  # Tag IDs
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NavigationView(BaseModel):
    """A view of the document organized in a specific way."""
    
    id: str
    name: str
    view_type: NavigationViewType
    root_elements: List[str] = Field(default_factory=list)  # Root element IDs
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NavigationPosition(BaseModel):
    """A position within the navigation structure."""
    
    view_id: str
    element_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentNavigator:
    """Non-linear document navigation system."""
    
    def __init__(self, document: Document, narrative_tracker: Optional[NarrativeTracker] = None):
        """Initialize the navigation system with the given document."""
        self.document = document
        self.narrative_tracker = narrative_tracker
        self.elements: Dict[str, NavigationElement] = {}
        self.views: Dict[str, NavigationView] = {}
        self.tags: Dict[str, NavigationTag] = {}
        self.links: Dict[str, NavigationLink] = {}
        self.current_position: Optional[NavigationPosition] = None
        
        # Initialize with default linear view
        self._initialize_linear_view()
    
    def _initialize_linear_view(self) -> None:
        """Initialize the default linear view of the document."""
        # Create view
        view_id = "view_linear"
        view = NavigationView(
            id=view_id,
            name="Linear View",
            view_type=NavigationViewType.LINEAR
        )
        
        # Create elements for sections and segments
        root_elements = []
        
        for section_idx, section in enumerate(self.document.current_revision.sections):
            # Create element for the section
            section_element_id = f"element_section_{section.id}"
            section_element = NavigationElement(
                id=section_element_id,
                element_type="section",
                name=section.title,
                original_id=section.id
            )
            
            # Add to elements
            self.elements[section_element_id] = section_element
            root_elements.append(section_element_id)
            
            # Create elements for segments
            for segment_idx, segment in enumerate(section.segments):
                segment_element_id = f"element_segment_{segment.id}"
                segment_element = NavigationElement(
                    id=segment_element_id,
                    element_type="segment",
                    name=f"Paragraph {segment_idx + 1}",
                    original_id=segment.id
                )
                
                # Add to elements
                self.elements[segment_element_id] = segment_element
                
                # Add to section's children
                section_element.children.append(segment_element_id)
        
        # Update view
        view.root_elements = root_elements
        self.views[view_id] = view
        
        # Set current position to the first section if available
        if root_elements:
            self.current_position = NavigationPosition(
                view_id=view_id,
                element_id=root_elements[0]
            )
    
    def _create_character_view(self) -> str:
        """Create a view organized by characters."""
        if not self.narrative_tracker:
            return ""
        
        # Create view
        view_id = "view_character"
        view = NavigationView(
            id=view_id,
            name="Character View",
            view_type=NavigationViewType.CHARACTER
        )
        
        # Get character elements from the narrative tracker
        character_elements = [
            element for element in self.narrative_tracker.elements.values()
            if element.element_type == ElementType.CHARACTER
        ]
        
        # Create elements for each character
        root_elements = []
        
        for character in character_elements:
            # Create element for the character
            character_element_id = f"element_character_{character.id}"
            character_element = NavigationElement(
                id=character_element_id,
                element_type="character",
                name=character.name,
                original_id=character.id,
                metadata={"description": character.description}
            )
            
            # Add to elements
            self.elements[character_element_id] = character_element
            root_elements.append(character_element_id)
            
            # Get appearances of this character
            appearances = self.narrative_tracker.get_element_appearances(character.id)
            
            # Group by section
            section_appearances: Dict[str, List[Dict[str, Any]]] = {}
            for appearance in appearances:
                section_id = appearance["section_id"]
                if section_id not in section_appearances:
                    section_appearances[section_id] = []
                section_appearances[section_id].append(appearance)
            
            # Create elements for each section with appearances
            for section_id, section_apps in section_appearances.items():
                # Get the section
                section = None
                for s in self.document.current_revision.sections:
                    if s.id == section_id:
                        section = s
                        break
                
                if not section:
                    continue
                
                # Create element for the section
                section_element_id = f"element_character_section_{character.id}_{section.id}"
                section_element = NavigationElement(
                    id=section_element_id,
                    element_type="section",
                    name=section.title,
                    original_id=section.id
                )
                
                # Add to elements
                self.elements[section_element_id] = section_element
                
                # Add to character's children
                character_element.children.append(section_element_id)
                
                # Create elements for each appearance
                for appearance in section_apps:
                    segment_id = appearance["segment_id"]
                    
                    # Get the segment
                    segment = None
                    for seg in section.segments:
                        if seg.id == segment_id:
                            segment = seg
                            break
                    
                    if not segment:
                        continue
                    
                    # Create element for the segment
                    segment_element_id = f"element_character_segment_{character.id}_{segment.id}"
                    
                    # Skip if already added
                    if segment_element_id in self.elements:
                        continue
                    
                    segment_element = NavigationElement(
                        id=segment_element_id,
                        element_type="segment",
                        name=f"Appearance {len(section_element.children) + 1}",
                        original_id=segment.id,
                        metadata={"context": appearance["context"]}
                    )
                    
                    # Add to elements
                    self.elements[segment_element_id] = segment_element
                    
                    # Add to section's children
                    section_element.children.append(segment_element_id)
        
        # Update view
        view.root_elements = root_elements
        self.views[view_id] = view
        
        return view_id
    
    def _create_plot_view(self) -> str:
        """Create a view organized by plot elements."""
        # Create view
        view_id = "view_plot"
        view = NavigationView(
            id=view_id,
            name="Plot View",
            view_type=NavigationViewType.PLOT
        )
        
        # First, look for plot-related metadata in the document
        plot_elements = []
        
        # Check for plot tags
        plot_tags = [tag for tag in self.tags.values() if "plot" in tag.name.lower()]
        
        if plot_tags:
            # Organize by plot tags
            for tag in plot_tags:
                # Create element for the tag
                tag_element_id = f"element_plot_tag_{tag.id}"
                tag_element = NavigationElement(
                    id=tag_element_id,
                    element_type="tag",
                    name=tag.name,
                    original_id=tag.id
                )
                
                # Add to elements
                self.elements[tag_element_id] = tag_element
                plot_elements.append(tag_element_id)
                
                # Find elements with this tag
                for element_id, element in self.elements.items():
                    if tag.id in element.tags:
                        # Create a reference element
                        ref_element_id = f"element_plot_ref_{tag.id}_{element.id}"
                        ref_element = NavigationElement(
                            id=ref_element_id,
                            element_type=element.element_type,
                            name=element.name,
                            original_id=element.original_id
                        )
                        
                        # Add to elements
                        self.elements[ref_element_id] = ref_element
                        
                        # Add to tag's children
                        tag_element.children.append(ref_element_id)
        
        # If we have a narrative tracker, use plot elements from there
        elif self.narrative_tracker:
            # Get plot elements from the narrative tracker
            plot_narrative_elements = [
                element for element in self.narrative_tracker.elements.values()
                if element.element_type in (ElementType.EVENT, ElementType.ITEM, ElementType.TERM)
            ]
            
            for plot_element in plot_narrative_elements:
                # Create element for the plot element
                plot_element_id = f"element_plot_{plot_element.id}"
                plot_nav_element = NavigationElement(
                    id=plot_element_id,
                    element_type="plot",
                    name=plot_element.name,
                    original_id=plot_element.id,
                    metadata={"description": plot_element.description}
                )
                
                # Add to elements
                self.elements[plot_element_id] = plot_nav_element
                plot_elements.append(plot_element_id)
                
                # Get appearances of this plot element
                appearances = self.narrative_tracker.get_element_appearances(plot_element.id)
                
                # Group by section
                section_appearances: Dict[str, List[Dict[str, Any]]] = {}
                for appearance in appearances:
                    section_id = appearance["section_id"]
                    if section_id not in section_appearances:
                        section_appearances[section_id] = []
                    section_appearances[section_id].append(appearance)
                
                # Create elements for each section with appearances
                for section_id, section_apps in section_appearances.items():
                    # Get the section
                    section = None
                    for s in self.document.current_revision.sections:
                        if s.id == section_id:
                            section = s
                            break
                    
                    if not section:
                        continue
                    
                    # Create element for the section
                    section_element_id = f"element_plot_section_{plot_element.id}_{section.id}"
                    section_element = NavigationElement(
                        id=section_element_id,
                        element_type="section",
                        name=section.title,
                        original_id=section.id
                    )
                    
                    # Add to elements
                    self.elements[section_element_id] = section_element
                    
                    # Add to plot element's children
                    plot_nav_element.children.append(section_element_id)
                    
                    # Create elements for each appearance
                    for appearance in section_apps:
                        segment_id = appearance["segment_id"]
                        
                        # Get the segment
                        segment = None
                        for seg in section.segments:
                            if seg.id == segment_id:
                                segment = seg
                                break
                        
                        if not segment:
                            continue
                        
                        # Create element for the segment
                        segment_element_id = f"element_plot_segment_{plot_element.id}_{segment.id}"
                        
                        # Skip if already added
                        if segment_element_id in self.elements:
                            continue
                        
                        segment_element = NavigationElement(
                            id=segment_element_id,
                            element_type="segment",
                            name=f"Reference {len(section_element.children) + 1}",
                            original_id=segment.id,
                            metadata={"context": appearance["context"]}
                        )
                        
                        # Add to elements
                        self.elements[segment_element_id] = segment_element
                        
                        # Add to section's children
                        section_element.children.append(segment_element_id)
        
        # If we don't have plot tags or narrative tracker, create a dummy structure
        if not plot_elements:
            # Create a default "plot" element
            plot_element_id = "element_plot_default"
            plot_element = NavigationElement(
                id=plot_element_id,
                element_type="plot",
                name="Main Plot"
            )
            
            # Add to elements
            self.elements[plot_element_id] = plot_element
            plot_elements.append(plot_element_id)
            
            # Add all sections as children
            for section in self.document.current_revision.sections:
                # Create element for the section
                section_element_id = f"element_plot_section_{section.id}"
                section_element = NavigationElement(
                    id=section_element_id,
                    element_type="section",
                    name=section.title,
                    original_id=section.id
                )
                
                # Add to elements
                self.elements[section_element_id] = section_element
                
                # Add to plot's children
                plot_element.children.append(section_element_id)
        
        # Update view
        view.root_elements = plot_elements
        self.views[view_id] = view
        
        return view_id
    
    def _create_timeline_view(self) -> str:
        """Create a view organized by timeline/chronology."""
        # Create view
        view_id = "view_timeline"
        view = NavigationView(
            id=view_id,
            name="Timeline View",
            view_type=NavigationViewType.TIMELINE
        )
        
        # Check for timeline metadata in sections
        timeline_sections = []
        
        for section in self.document.current_revision.sections:
            if "timeline" in section.metadata:
                timeline_sections.append((section, section.metadata["timeline"]))
        
        # If we have timeline metadata, use it to organize the view
        if timeline_sections:
            # Sort sections by timeline value
            timeline_sections.sort(key=lambda x: x[1])
            
            # Create elements for each section in chronological order
            root_elements = []
            
            for section, timeline in timeline_sections:
                # Create element for the section
                section_element_id = f"element_timeline_section_{section.id}"
                section_element = NavigationElement(
                    id=section_element_id,
                    element_type="section",
                    name=f"{timeline}: {section.title}",
                    original_id=section.id,
                    metadata={"timeline": timeline}
                )
                
                # Add to elements
                self.elements[section_element_id] = section_element
                root_elements.append(section_element_id)
                
                # Create elements for segments
                for segment_idx, segment in enumerate(section.segments):
                    segment_element_id = f"element_timeline_segment_{segment.id}"
                    segment_element = NavigationElement(
                        id=segment_element_id,
                        element_type="segment",
                        name=f"Paragraph {segment_idx + 1}",
                        original_id=segment.id
                    )
                    
                    # Add to elements
                    self.elements[segment_element_id] = segment_element
                    
                    # Add to section's children
                    section_element.children.append(segment_element_id)
        else:
            # Create a simple chronological view (same as linear)
            root_elements = []
            
            for section_idx, section in enumerate(self.document.current_revision.sections):
                # Create element for the section
                section_element_id = f"element_timeline_section_{section.id}"
                section_element = NavigationElement(
                    id=section_element_id,
                    element_type="section",
                    name=section.title,
                    original_id=section.id,
                    metadata={"position": section_idx}
                )
                
                # Add to elements
                self.elements[section_element_id] = section_element
                root_elements.append(section_element_id)
                
                # Create elements for segments
                for segment_idx, segment in enumerate(section.segments):
                    segment_element_id = f"element_timeline_segment_{segment.id}"
                    segment_element = NavigationElement(
                        id=segment_element_id,
                        element_type="segment",
                        name=f"Paragraph {segment_idx + 1}",
                        original_id=segment.id
                    )
                    
                    # Add to elements
                    self.elements[segment_element_id] = segment_element
                    
                    # Add to section's children
                    section_element.children.append(segment_element_id)
        
        # Update view
        view.root_elements = root_elements
        self.views[view_id] = view
        
        return view_id
    
    def create_view(self, name: str, view_type: NavigationViewType) -> str:
        """Create a new navigation view."""
        if view_type == NavigationViewType.CHARACTER:
            return self._create_character_view()
        elif view_type == NavigationViewType.PLOT:
            return self._create_plot_view()
        elif view_type == NavigationViewType.TIMELINE:
            return self._create_timeline_view()
        elif view_type == NavigationViewType.CUSTOM:
            # Create a custom view
            view_id = f"view_custom_{len(self.views) + 1}"
            view = NavigationView(
                id=view_id,
                name=name,
                view_type=view_type
            )
            
            self.views[view_id] = view
            return view_id
        else:
            # Linear view already exists
            return "view_linear"
    
    def create_tag(self, name: str, color: str = "#CCCCCC") -> str:
        """Create a new tag for navigation elements."""
        tag_id = f"tag_{len(self.tags) + 1}"
        tag = NavigationTag(
            id=tag_id,
            name=name,
            color=color
        )
        
        self.tags[tag_id] = tag
        return tag_id
    
    def add_tag_to_element(self, element_id: str, tag_id: str) -> bool:
        """Add a tag to a navigation element."""
        if element_id not in self.elements or tag_id not in self.tags:
            return False
        
        element = self.elements[element_id]
        if tag_id not in element.tags:
            element.tags.append(tag_id)
        
        return True
    
    def create_link(
        self, 
        source_type: str, 
        source_id: str, 
        target_type: str, 
        target_id: str, 
        link_type: str
    ) -> str:
        """Create a link between two navigation elements."""
        link_id = f"link_{len(self.links) + 1}"
        link = NavigationLink(
            id=link_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            link_type=link_type
        )
        
        self.links[link_id] = link
        return link_id
    
    def add_element_to_view(self, view_id: str, element_id: str, parent_id: Optional[str] = None) -> bool:
        """Add an element to a view, optionally as a child of another element."""
        if view_id not in self.views or element_id not in self.elements:
            return False
        
        view = self.views[view_id]
        
        if parent_id:
            if parent_id not in self.elements:
                return False
            
            parent = self.elements[parent_id]
            if element_id not in parent.children:
                parent.children.append(element_id)
        else:
            if element_id not in view.root_elements:
                view.root_elements.append(element_id)
        
        return True
    
    def get_current_element(self) -> Optional[NavigationElement]:
        """Get the current navigation element."""
        if not self.current_position:
            return None
        
        element_id = self.current_position.element_id
        return self.elements.get(element_id)
    
    def get_element_content(self, element_id: str) -> Optional[str]:
        """Get the content of a navigation element."""
        if element_id not in self.elements:
            return None
        
        element = self.elements[element_id]
        original_id = element.original_id
        
        if not original_id:
            return None
        
        if element.element_type == "section":
            # Find the section
            for section in self.document.current_revision.sections:
                if section.id == original_id:
                    return section.get_content()
        
        elif element.element_type == "segment":
            # Find the segment
            for section in self.document.current_revision.sections:
                for segment in section.segments:
                    if segment.id == original_id:
                        return segment.content
        
        return None
    
    def navigate_to(self, view_id: str, element_id: str) -> bool:
        """Navigate to a specific element in a view."""
        if view_id not in self.views or element_id not in self.elements:
            return False
        
        self.current_position = NavigationPosition(
            view_id=view_id,
            element_id=element_id
        )
        
        return True
    
    def navigate_to_related(self, link_type: Optional[str] = None) -> List[NavigationElement]:
        """Navigate to elements related to the current element."""
        if not self.current_position:
            return []
        
        current_element_id = self.current_position.element_id
        
        # Find links with this element as source
        related_links = []
        for link in self.links.values():
            if link.source_id == current_element_id:
                if not link_type or link.link_type == link_type:
                    related_links.append(link)
        
        # Get related elements
        related_elements = []
        for link in related_links:
            target_id = link.target_id
            if target_id in self.elements:
                related_elements.append(self.elements[target_id])
        
        return related_elements
    
    def navigate_parent(self) -> bool:
        """Navigate to the parent of the current element."""
        if not self.current_position:
            return False
        
        current_element_id = self.current_position.element_id
        view_id = self.current_position.view_id
        
        # Find parent element
        parent_id = None
        
        for element_id, element in self.elements.items():
            if current_element_id in element.children:
                parent_id = element_id
                break
        
        if parent_id:
            # Navigate to parent
            self.current_position = NavigationPosition(
                view_id=view_id,
                element_id=parent_id
            )
            return True
        
        # Check if this is a root element in the view
        view = self.views.get(view_id)
        if view and current_element_id in view.root_elements:
            # Already at top level
            return False
        
        return False
    
    def navigate_next(self) -> bool:
        """Navigate to the next element at the same level."""
        if not self.current_position:
            return False
        
        current_element_id = self.current_position.element_id
        view_id = self.current_position.view_id
        
        # Check if this element is a child of another element
        parent_id = None
        
        for element_id, element in self.elements.items():
            if current_element_id in element.children:
                parent_id = element_id
                break
        
        if parent_id:
            # Get siblings
            parent = self.elements[parent_id]
            siblings = parent.children
            
            # Find current index
            try:
                current_index = siblings.index(current_element_id)
                
                # If there's a next sibling, navigate to it
                if current_index + 1 < len(siblings):
                    next_id = siblings[current_index + 1]
                    self.current_position = NavigationPosition(
                        view_id=view_id,
                        element_id=next_id
                    )
                    return True
            except ValueError:
                pass
        
        # Check if this is a root element in the view
        view = self.views.get(view_id)
        if view and current_element_id in view.root_elements:
            # Find current index
            try:
                current_index = view.root_elements.index(current_element_id)
                
                # If there's a next sibling, navigate to it
                if current_index + 1 < len(view.root_elements):
                    next_id = view.root_elements[current_index + 1]
                    self.current_position = NavigationPosition(
                        view_id=view_id,
                        element_id=next_id
                    )
                    return True
            except ValueError:
                pass
        
        return False
    
    def navigate_previous(self) -> bool:
        """Navigate to the previous element at the same level."""
        if not self.current_position:
            return False
        
        current_element_id = self.current_position.element_id
        view_id = self.current_position.view_id
        
        # Check if this element is a child of another element
        parent_id = None
        
        for element_id, element in self.elements.items():
            if current_element_id in element.children:
                parent_id = element_id
                break
        
        if parent_id:
            # Get siblings
            parent = self.elements[parent_id]
            siblings = parent.children
            
            # Find current index
            try:
                current_index = siblings.index(current_element_id)
                
                # If there's a previous sibling, navigate to it
                if current_index > 0:
                    prev_id = siblings[current_index - 1]
                    self.current_position = NavigationPosition(
                        view_id=view_id,
                        element_id=prev_id
                    )
                    return True
            except ValueError:
                pass
        
        # Check if this is a root element in the view
        view = self.views.get(view_id)
        if view and current_element_id in view.root_elements:
            # Find current index
            try:
                current_index = view.root_elements.index(current_element_id)
                
                # If there's a previous sibling, navigate to it
                if current_index > 0:
                    prev_id = view.root_elements[current_index - 1]
                    self.current_position = NavigationPosition(
                        view_id=view_id,
                        element_id=prev_id
                    )
                    return True
            except ValueError:
                pass
        
        return False
    
    def navigate_children(self) -> List[NavigationElement]:
        """Get the children of the current element."""
        if not self.current_position:
            return []
        
        current_element_id = self.current_position.element_id
        
        # Get element
        element = self.elements.get(current_element_id)
        if not element:
            return []
        
        # Get children
        children = []
        for child_id in element.children:
            if child_id in self.elements:
                children.append(self.elements[child_id])
        
        return children
    
    def find_elements_by_tag(self, tag_id: str) -> List[NavigationElement]:
        """Find all elements with a specific tag."""
        if tag_id not in self.tags:
            return []
        
        # Find elements with this tag
        tagged_elements = []
        for element_id, element in self.elements.items():
            if tag_id in element.tags:
                tagged_elements.append(element)
        
        return tagged_elements
    
    def find_elements_by_name(self, name: str) -> List[NavigationElement]:
        """Find elements by name (case-insensitive partial match)."""
        name = name.lower()
        
        matching_elements = []
        for element_id, element in self.elements.items():
            if name in element.name.lower():
                matching_elements.append(element)
        
        return matching_elements
    
    def get_path_to_element(self, element_id: str) -> List[str]:
        """Get the path from root to the specified element."""
        if element_id not in self.elements:
            return []
        
        # Find view that contains this element
        view_id = None
        for view_id, view in self.views.items():
            if element_id in view.root_elements:
                break
            
            # Check if it's a descendant of any root element
            for root_id in view.root_elements:
                if self._is_descendant(root_id, element_id):
                    view_id = view_id
                    break
            
            if view_id:
                break
        
        if not view_id:
            return []
        
        # Find path
        path = []
        current_id = element_id
        
        while current_id:
            path.insert(0, current_id)
            
            # Find parent
            parent_id = None
            for element_id, element in self.elements.items():
                if current_id in element.children:
                    parent_id = element_id
                    break
            
            # If no parent, check if it's a root element
            if not parent_id:
                # If it's a root element, we've reached the top
                if current_id in self.views[view_id].root_elements:
                    break
            
            current_id = parent_id
        
        return path
    
    def _is_descendant(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if descendant_id is a descendant of ancestor_id."""
        if ancestor_id not in self.elements:
            return False
        
        # Check direct children
        ancestor = self.elements[ancestor_id]
        if descendant_id in ancestor.children:
            return True
        
        # Check descendants recursively
        for child_id in ancestor.children:
            if self._is_descendant(child_id, descendant_id):
                return True
        
        return False