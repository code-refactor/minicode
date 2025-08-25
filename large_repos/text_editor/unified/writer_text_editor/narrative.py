"""Character and plot element tracking system for the writer text editor."""

from __future__ import annotations
import re
import time
import threading
import spacy
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from pydantic import BaseModel, Field

from writer_text_editor.document import Document, Section, TextSegment


class ElementType(str, Enum):
    """Types of narrative elements."""
    
    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    EVENT = "event"
    TERM = "term"
    CUSTOM = "custom"


class ElementOccurrence(BaseModel):
    """An occurrence of a narrative element in the document."""
    
    element_id: str
    section_id: str
    segment_id: str
    position: int  # Character position within the segment
    context: str  # Surrounding text for context
    mentioned_with: List[str] = Field(default_factory=list)  # Other elements mentioned in the same context


class NarrativeElement(BaseModel):
    """A tracked narrative element such as a character or plot element."""
    
    id: str
    name: str
    element_type: ElementType
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurrences: List[ElementOccurrence] = Field(default_factory=list)
    related_elements: Dict[str, float] = Field(default_factory=dict)  # Element ID to relationship strength
    first_appearance: Optional[datetime] = None
    last_appearance: Optional[datetime] = None


class ConsistencyIssue(BaseModel):
    """A potential consistency issue in the narrative."""
    
    id: str
    issue_type: str  # "contradiction", "timeline", "character", etc.
    elements_involved: List[str]  # Element IDs
    description: str
    locations: List[Tuple[str, str]]  # List of (section_id, segment_id) tuples
    severity: int  # 1-5, with 5 being most severe
    resolved: bool = False
    notes: str = ""


class NarrativeTracker:
    """Character and plot element tracking system."""
    
    def __init__(self, document: Document):
        """Initialize the narrative tracking system with the given document."""
        self.document = document
        self.elements: Dict[str, NarrativeElement] = {}
        self.consistency_issues: List[ConsistencyIssue] = []
        self._nlp = None  # Lazy-loaded spaCy model
        self._background_thread: Optional[threading.Thread] = None
        self._stop_background_thread: bool = False
    
    def _ensure_nlp_loaded(self):
        """Ensure the NLP model is loaded."""
        if self._nlp is None:
            # Load a smaller spaCy model for performance
            self._nlp = spacy.load("en_core_web_sm")
    
    def _find_element_occurrences(
        self, 
        element_name: str, 
        aliases: List[str] = None
    ) -> List[Tuple[Section, TextSegment, int, str]]:
        """Find occurrences of an element in the document by name and aliases."""
        results = []
        names_to_search = [element_name]
        if aliases:
            names_to_search.extend(aliases)
        
        # Compile regex pattern for faster matching
        # Ensure we match whole words only
        pattern = r'\b(' + '|'.join(re.escape(name) for name in names_to_search) + r')\b'
        regex = re.compile(pattern, re.IGNORECASE)
        
        for section in self.document.current_revision.sections:
            for segment in section.segments:
                for match in regex.finditer(segment.content):
                    # Extract some context around the match (up to 100 characters)
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(segment.content), match.end() + 50)
                    context = segment.content[start_pos:end_pos]
                    
                    results.append((section, segment, match.start(), context))
        
        return results
    
    def _identify_potential_elements(self) -> Dict[str, Dict[str, Any]]:
        """Identify potential narrative elements using NLP."""
        self._ensure_nlp_loaded()
        
        potential_elements = {
            ElementType.CHARACTER.value: set(),
            ElementType.LOCATION.value: set(),
            ElementType.ITEM.value: set(),
            ElementType.EVENT.value: set()
        }
        
        # Process the document content
        text = self.document.get_content()
        doc = self._nlp(text)
        
        # Find named entities
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "PER"):
                potential_elements[ElementType.CHARACTER.value].add(ent.text)
            elif ent.label_ in ("GPE", "LOC", "FAC"):
                potential_elements[ElementType.LOCATION.value].add(ent.text)
            elif ent.label_ in ("EVENT", "WORK_OF_ART"):
                potential_elements[ElementType.EVENT.value].add(ent.text)
            elif ent.label_ in ("PRODUCT", "OBJECT"):
                potential_elements[ElementType.ITEM.value].add(ent.text)
        
        # Look for capitalized noun phrases that might be character names
        for token in doc:
            if token.is_alpha and token.is_title and token.pos_ == "PROPN":
                # Get the full noun phrase if this is part of one
                if token.head.pos_ == "PROPN":
                    noun_phrase = " ".join([t.text for t in token.head.subtree])
                    potential_elements[ElementType.CHARACTER.value].add(noun_phrase)
                else:
                    potential_elements[ElementType.CHARACTER.value].add(token.text)
        
        # Convert sets to lists and count occurrences
        results = {}
        for element_type, elements in potential_elements.items():
            results[element_type] = {}
            for element in elements:
                # Count occurrences
                occurrences = len(re.findall(r'\b' + re.escape(element) + r'\b', text, re.IGNORECASE))
                if occurrences > 0:
                    results[element_type][element] = {
                        "occurrences": occurrences,
                        "already_tracked": element in [e.name for e in self.elements.values()]
                    }
        
        return results
    
    def _detect_connections(self) -> Dict[str, Dict[str, float]]:
        """Detect connections between elements based on co-occurrence."""
        connections = {}
        
        # Iterate through all elements
        for element_id, element in self.elements.items():
            connections[element_id] = {}
            
            # Get all contexts where this element appears
            contexts = [occurrence.context for occurrence in element.occurrences]
            
            # Check which other elements appear in the same contexts
            for other_id, other_element in self.elements.items():
                if other_id == element_id:
                    continue
                
                co_occurrences = 0
                for context in contexts:
                    pattern = r'\b(' + '|'.join(
                        [re.escape(other_element.name)] + 
                        [re.escape(alias) for alias in other_element.aliases]
                    ) + r')\b'
                    
                    if re.search(pattern, context, re.IGNORECASE):
                        co_occurrences += 1
                
                if co_occurrences > 0:
                    # Calculate connection strength (0-1)
                    strength = co_occurrences / len(contexts) if contexts else 0
                    connections[element_id][other_id] = strength
        
        return connections
    
    def _detect_consistency_issues(self) -> List[ConsistencyIssue]:
        """Detect potential consistency issues in the narrative."""
        issues = []
        
        # Check for characters appearing in impossible timeframes/locations
        character_locations = {}
        
        for element_id, element in self.elements.items():
            if element.element_type != ElementType.CHARACTER:
                continue
            
            # Track which sections each character appears in
            character_locations[element_id] = set()
            for occurrence in element.occurrences:
                character_locations[element_id].add(occurrence.section_id)
        
        # Perform timeline analysis if we have section metadata with timeline info
        timeline_sections = {}
        for section in self.document.current_revision.sections:
            if "timeline" in section.metadata:
                timeline_sections[section.id] = section.metadata["timeline"]
        
        if timeline_sections:
            # Check for characters appearing in non-sequential timeline points
            for char_id, sections in character_locations.items():
                char_timeline_sections = [s for s in sections if s in timeline_sections]
                if len(char_timeline_sections) > 1:
                    # Sort by timeline value
                    sorted_sections = sorted(char_timeline_sections, key=lambda s: timeline_sections[s])
                    
                    # Check if any section is repeated out of order
                    for i in range(len(sorted_sections) - 1):
                        for j in range(i + 1, len(sorted_sections)):
                            if sorted_sections[i] == sorted_sections[j]:
                                # This character appears in the same timeline point multiple times
                                # Not necessarily an issue, skip
                                continue
                            
                            for k in range(j + 1, len(sorted_sections)):
                                if sorted_sections[k] == sorted_sections[i]:
                                    # Character appears at timeline point i, then j, then i again
                                    # This could be a flashback, but flag it as a potential issue
                                    issues.append(ConsistencyIssue(
                                        id=str(len(issues) + 1),
                                        issue_type="timeline",
                                        elements_involved=[char_id],
                                        description=(
                                            f"Character appears in non-sequential timeline points: "
                                            f"{timeline_sections[sorted_sections[i]]} -> "
                                            f"{timeline_sections[sorted_sections[j]]} -> "
                                            f"{timeline_sections[sorted_sections[k]]}"
                                        ),
                                        locations=[
                                            (sorted_sections[i], ""),
                                            (sorted_sections[j], ""),
                                            (sorted_sections[k], "")
                                        ],
                                        severity=3
                                    ))
        
        # Look for description inconsistencies by comparing contexts
        for element_id, element in self.elements.items():
            if len(element.occurrences) < 2:
                continue
            
            # Extract descriptive contexts
            descriptive_contexts = []
            for occurrence in element.occurrences:
                # Look for descriptions (X was Y, X had Y, etc.)
                context = occurrence.context
                element_pos = context.lower().find(element.name.lower())
                
                if element_pos >= 0:
                    # Check text after the element name
                    after_text = context[element_pos + len(element.name):]
                    
                    # Simple pattern matching for descriptions
                    description_patterns = [
                        r'\s+was\s+(\w+)',
                        r'\s+had\s+(\w+)',
                        r'\s+with\s+(\w+)',
                        r',\s+a\s+(\w+)',
                        r',\s+the\s+(\w+)'
                    ]
                    
                    for pattern in description_patterns:
                        matches = re.finditer(pattern, after_text, re.IGNORECASE)
                        for match in matches:
                            descriptive_contexts.append((
                                occurrence.section_id,
                                occurrence.segment_id,
                                match.group(1),
                                context
                            ))
            
            # Compare descriptions for contradictions
            if len(descriptive_contexts) > 1:
                # Very simple contradiction detection - could be improved
                descriptions = {}
                for section_id, segment_id, desc, context in descriptive_contexts:
                    key = desc.lower()
                    if key not in descriptions:
                        descriptions[key] = []
                    descriptions[key].append((section_id, segment_id, context))
                
                # Check for antonyms or contradictory descriptions
                # This is a simplified approach and could be enhanced with a proper lexical database
                common_antonym_pairs = [
                    ("tall", "short"),
                    ("large", "small"),
                    ("big", "little"),
                    ("old", "young"),
                    ("dark", "light"),
                    ("black", "white"),
                    ("angry", "calm"),
                    ("happy", "sad"),
                    ("rich", "poor")
                ]
                
                for word1, word2 in common_antonym_pairs:
                    if word1 in descriptions and word2 in descriptions:
                        # Possible contradiction found
                        issues.append(ConsistencyIssue(
                            id=str(len(issues) + 1),
                            issue_type="contradiction",
                            elements_involved=[element_id],
                            description=(
                                f"Possible contradictory descriptions: '{word1}' vs '{word2}'"
                            ),
                            locations=[
                                (descriptions[word1][0][0], descriptions[word1][0][1]),
                                (descriptions[word2][0][0], descriptions[word2][0][1])
                            ],
                            severity=4
                        ))
        
        return issues
    
    def track_element(
        self,
        name: str,
        element_type: ElementType,
        aliases: List[str] = None,
        description: str = "",
        metadata: Dict[str, Any] = None
    ) -> NarrativeElement:
        """Track a narrative element by name and aliases."""
        element_id = f"{element_type.value}_{len(self.elements) + 1}"
        
        # Find occurrences
        occurrences = []
        for section, segment, position, context in self._find_element_occurrences(name, aliases):
            occurrences.append(ElementOccurrence(
                element_id=element_id,
                section_id=section.id,
                segment_id=segment.id,
                position=position,
                context=context
            ))
        
        # Create the element
        element = NarrativeElement(
            id=element_id,
            name=name,
            element_type=element_type,
            aliases=aliases or [],
            description=description,
            metadata=metadata or {},
            occurrences=occurrences,
            first_appearance=datetime.now() if occurrences else None,
            last_appearance=datetime.now() if occurrences else None
        )
        
        self.elements[element_id] = element
        return element
    
    def detect_elements(self) -> Dict[str, List[NarrativeElement]]:
        """Automatically detect and track potential narrative elements."""
        potential_elements = self._identify_potential_elements()
        
        # Track elements by type
        tracked_elements = {
            ElementType.CHARACTER.value: [],
            ElementType.LOCATION.value: [],
            ElementType.ITEM.value: [],
            ElementType.EVENT.value: []
        }
        
        # Add elements that aren't already tracked
        for element_type, elements in potential_elements.items():
            for name, info in elements.items():
                if not info["already_tracked"] and info["occurrences"] >= 2:
                    # Only track elements that appear at least twice
                    element = self.track_element(
                        name=name,
                        element_type=ElementType(element_type)
                    )
                    tracked_elements[element_type].append(element)
        
        # Update element relationships
        self.update_element_relationships()
        
        # Detect consistency issues
        self.check_consistency()
        
        return tracked_elements
    
    def update_element_relationships(self) -> None:
        """Update relationships between elements based on co-occurrence."""
        connections = self._detect_connections()
        
        # Update related_elements for each element
        for element_id, related in connections.items():
            if element_id in self.elements:
                self.elements[element_id].related_elements = related
    
    def check_consistency(self) -> List[ConsistencyIssue]:
        """Check for consistency issues in the narrative."""
        self.consistency_issues = self._detect_consistency_issues()
        return self.consistency_issues
    
    def get_element_appearances(self, element_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about all appearances of an element."""
        if element_id not in self.elements:
            return []
        
        element = self.elements[element_id]
        appearances = []
        
        for occurrence in element.occurrences:
            # Find the section and segment
            section = None
            segment = None
            
            for s in self.document.current_revision.sections:
                if s.id == occurrence.section_id:
                    section = s
                    for seg in s.segments:
                        if seg.id == occurrence.segment_id:
                            segment = seg
                            break
                    break
            
            if section and segment:
                appearances.append({
                    "section_title": section.title,
                    "section_id": section.id,
                    "segment_id": segment.id,
                    "segment_position": segment.position,
                    "context": occurrence.context,
                    "mentioned_with": [
                        self.elements[e_id].name 
                        for e_id in occurrence.mentioned_with 
                        if e_id in self.elements
                    ]
                })
        
        return appearances
    
    def get_element_timeline(self, element_id: str) -> List[Dict[str, Any]]:
        """Get a timeline of an element's appearances ordered by position in the document."""
        appearances = self.get_element_appearances(element_id)
        
        # Group by section
        sections = {}
        for appearance in appearances:
            section_id = appearance["section_id"]
            if section_id not in sections:
                sections[section_id] = {
                    "section_title": appearance["section_title"],
                    "appearances": []
                }
            sections[section_id]["appearances"].append(appearance)
        
        # Order sections by their position in the document
        ordered_sections = []
        for section in self.document.current_revision.sections:
            if section.id in sections:
                ordered_sections.append({
                    "section_id": section.id,
                    "section_title": sections[section.id]["section_title"],
                    "appearances": sorted(
                        sections[section.id]["appearances"],
                        key=lambda a: a["segment_position"]
                    )
                })
        
        return ordered_sections
    
    def resolve_consistency_issue(self, issue_id: str, notes: str = "") -> bool:
        """Mark a consistency issue as resolved with optional notes."""
        for issue in self.consistency_issues:
            if issue.id == issue_id:
                issue.resolved = True
                issue.notes = notes
                return True
        return False
    
    def start_background_tracking(self, interval_seconds: int = 300) -> None:
        """Start tracking narrative elements in a background thread."""
        if self._background_thread and self._background_thread.is_alive():
            return  # Already running
        
        self._stop_background_thread = False
        
        def tracking_task():
            while not self._stop_background_thread:
                try:
                    self.detect_elements()
                    self.update_element_relationships()
                    self.check_consistency()
                except Exception as e:
                    print(f"Error in background narrative tracking: {e}")
                
                # Sleep for the specified interval
                for _ in range(interval_seconds):
                    if self._stop_background_thread:
                        break
                    time.sleep(1)
        
        self._background_thread = threading.Thread(target=tracking_task, daemon=True)
        self._background_thread.start()
    
    def stop_background_tracking(self) -> None:
        """Stop the background tracking thread."""
        self._stop_background_thread = True
        if self._background_thread:
            self._background_thread.join(timeout=5)