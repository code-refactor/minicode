"""Unified document model for the text editor."""

from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime
import copy
from common.core.models import BaseModel, Section, TextSegment, Metadata


class IDocument(Protocol):
    """Interface for document implementations."""
    
    def get_content(self) -> str: ...
    def add_section(self, title: str) -> Section: ...
    def get_section(self, index: int) -> Optional[Section]: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...


class Revision(BaseModel):
    """A revision/version of a document."""
    
    id: str
    name: str
    timestamp: datetime = datetime.now()
    sections: List[Section] = []
    metadata: Dict[str, Any] = {}
    
    def clone(self) -> 'Revision':
        """Create a deep copy of this revision."""
        return copy.deepcopy(self)
    
    def get_word_count(self) -> int:
        """Get total word count in revision."""
        return sum(section.get_word_count() for section in self.sections)


class Document(BaseModel):
    """Unified document model supporting both personas."""
    
    metadata: Metadata
    title: str = "Untitled"
    current_revision: Revision
    revisions: Dict[str, Revision] = {}
    file_path: Optional[str] = None
    
    def __init__(self, title: str = "Untitled", **data):
        """Initialize a new document."""
        metadata = Metadata()
        initial_revision = Revision(
            id=metadata.id,
            name="Initial",
            timestamp=metadata.created_at
        )
        
        super().__init__(
            metadata=metadata,
            title=title,
            current_revision=initial_revision,
            **data
        )
        
        self.revisions["Initial"] = initial_revision
    
    def get_content(self) -> str:
        """Get the full content of the document."""
        sections_content = []
        for section in self.current_revision.sections:
            if section.title:
                sections_content.append(f"# {section.title}\n")
            sections_content.append(section.get_content())
        
        return "\n\n".join(sections_content)
    
    def get_word_count(self) -> int:
        """Get total word count of current revision."""
        return self.current_revision.get_word_count()
    
    def add_section(self, title: str = "", metadata: Optional[Dict[str, Any]] = None) -> Section:
        """Add a new section to the document."""
        section = Section(title=title, metadata=metadata or {})
        self.current_revision.sections.append(section)
        self.metadata.update()
        return section
    
    def get_section(self, index: int) -> Optional[Section]:
        """Get section by index."""
        if 0 <= index < len(self.current_revision.sections):
            return self.current_revision.sections[index]
        return None
    
    def get_section_by_id(self, section_id: str) -> Optional[Section]:
        """Get section by ID."""
        for section in self.current_revision.sections:
            if section.id == section_id:
                return section
        return None
    
    def get_section_by_title(self, title: str) -> Optional[Section]:
        """Get first section with matching title."""
        for section in self.current_revision.sections:
            if section.title == title:
                return section
        return None
    
    def update_section_title(self, index: int, title: str) -> Optional[Section]:
        """Update title of a section."""
        section = self.get_section(index)
        if section:
            section.title = title
            self.metadata.update()
            return section
        return None
    
    def delete_section(self, index: int) -> bool:
        """Delete a section by index."""
        if 0 <= index < len(self.current_revision.sections):
            self.current_revision.sections.pop(index)
            self.metadata.update()
            return True
        return False
    
    def move_section(self, from_index: int, to_index: int) -> bool:
        """Move a section to a different position."""
        sections = self.current_revision.sections
        if (0 <= from_index < len(sections) and 
            0 <= to_index < len(sections)):
            section = sections.pop(from_index)
            sections.insert(to_index, section)
            self.metadata.update()
            return True
        return False
    
    def create_revision(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Revision:
        """Create a new revision from current state."""
        new_revision = self.current_revision.clone()
        new_revision.name = name
        new_revision.timestamp = datetime.now()
        new_revision.metadata = metadata or {}
        
        self.revisions[name] = new_revision
        self.current_revision = new_revision
        self.metadata.update()
        
        return new_revision
    
    def get_revision(self, name: str) -> Optional[Revision]:
        """Get a revision by name."""
        return self.revisions.get(name)
    
    def switch_to_revision(self, name: str) -> bool:
        """Switch to a different revision."""
        revision = self.get_revision(name)
        if revision:
            self.current_revision = revision
            self.metadata.update()
            return True
        return False
    
    def list_revisions(self) -> List[Dict[str, Any]]:
        """List all revisions with metadata."""
        result = []
        for name, revision in self.revisions.items():
            result.append({
                "name": name,
                "id": revision.id,
                "timestamp": revision.timestamp.isoformat(),
                "section_count": len(revision.sections),
                "word_count": revision.get_word_count(),
                "is_current": revision == self.current_revision
            })
        return result
    
    def merge_sections(self, start_index: int, end_index: int) -> Optional[Section]:
        """Merge multiple sections into one."""
        sections = self.current_revision.sections
        
        if not (0 <= start_index < len(sections) and 
                start_index <= end_index < len(sections)):
            return None
        
        # Get sections to merge
        sections_to_merge = sections[start_index:end_index + 1]
        
        # Create merged section
        merged = Section(
            title=sections_to_merge[0].title,
            metadata=sections_to_merge[0].metadata.copy()
        )
        
        # Merge all segments
        for section in sections_to_merge:
            for segment in section.segments:
                merged.segments.append(segment)
        
        # Update positions
        for i, segment in enumerate(merged.segments):
            segment.position = i
        
        # Replace original sections with merged
        self.current_revision.sections[start_index:end_index + 1] = [merged]
        self.metadata.update()
        
        return merged
    
    def split_section(self, section_index: int, segment_index: int) -> bool:
        """Split a section at a specific segment."""
        section = self.get_section(section_index)
        if not section or not (0 < segment_index < len(section.segments)):
            return False
        
        # Create new section with segments after split point
        new_section = Section(
            title=f"{section.title} (continued)" if section.title else "",
            segments=section.segments[segment_index:]
        )
        
        # Update positions in new section
        for i, segment in enumerate(new_section.segments):
            segment.position = i
        
        # Keep only segments before split point in original
        section.segments = section.segments[:segment_index]
        
        # Insert new section after current
        self.current_revision.sections.insert(section_index + 1, new_section)
        self.metadata.update()
        
        return True
    
    def find_text(self, pattern: str) -> List[Dict[str, Any]]:
        """Find text matching pattern in document."""
        import re
        results = []
        
        for section_idx, section in enumerate(self.current_revision.sections):
            for segment_idx, segment in enumerate(section.segments):
                matches = re.finditer(pattern, segment.content, re.IGNORECASE)
                for match in matches:
                    results.append({
                        "section_index": section_idx,
                        "section_id": section.id,
                        "section_title": section.title,
                        "segment_index": segment_idx,
                        "segment_id": segment.id,
                        "match": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
        
        return results
    
    def replace_text(self, pattern: str, replacement: str) -> int:
        """Replace all occurrences of pattern with replacement."""
        import re
        count = 0
        
        for section in self.current_revision.sections:
            for segment in section.segments:
                original = segment.content
                segment.content = re.sub(pattern, replacement, segment.content)
                if original != segment.content:
                    count += len(re.findall(pattern, original))
        
        if count > 0:
            self.metadata.update()
        
        return count