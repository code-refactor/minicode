"""Document model for the writer text editor."""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any
import re
import copy
from common.core import (
    Document as CommonDocument, 
    Section as CommonSection, 
    TextSegment as CommonTextSegment,
    Revision as CommonRevision
)


# Re-export common classes for backward compatibility
TextSegment = CommonTextSegment
Section = CommonSection
Revision = CommonRevision


class Document(CommonDocument):
    """A document in the writer text editor, extending the common Document."""
    
    # Additional writer-specific attributes
    id: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    def __init__(self, title: str, **data: Any):
        """Initialize a new document with the given title."""
        import uuid
        # Initialize parent first
        super().__init__(title=title, **data)
        
        # Then set writer-specific attributes
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_section(self, title: str, metadata: Optional[Dict[str, Any]] = None) -> Section:
        """Add a new section to the document, updating writer-specific timestamp."""
        section = super().add_section(title, metadata)
        self.updated_at = datetime.now()
        return section
    
    def update_section_title(self, index: int, title: str) -> Optional[Section]:
        """Update the title of the section, updating writer-specific timestamp."""
        section = super().update_section_title(index, title)
        if section:
            self.updated_at = datetime.now()
        return section
    
    def delete_section(self, index: int) -> bool:
        """Delete the section, updating writer-specific timestamp."""
        result = super().delete_section(index)
        if result:
            self.updated_at = datetime.now()
        return result
    
    def create_revision(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Revision:
        """Create a new revision, updating writer-specific timestamp."""
        revision = super().create_revision(name, metadata)
        self.updated_at = datetime.now()
        return revision
    
    def switch_to_revision(self, name: str) -> bool:
        """Switch to a different revision, updating writer-specific timestamp."""
        result = super().switch_to_revision(name)
        if result:
            self.updated_at = datetime.now()
        return result
    
    def find_segments_by_content(self, pattern: str) -> List[Tuple[Section, TextSegment]]:
        """Find segments that match the given pattern."""
        results = []
        for section in self.current_revision.sections:
            for segment in section.segments:
                if re.search(pattern, segment.content, re.IGNORECASE):
                    results.append((section, segment))
        return results