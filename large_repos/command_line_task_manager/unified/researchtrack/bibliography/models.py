from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field

from common.core import BaseEntity


class CitationStyle(str, Enum):
    """Supported academic citation styles."""
    
    APA = "apa"  # American Psychological Association
    MLA = "mla"  # Modern Language Association
    CHICAGO = "chicago"  # Chicago Manual of Style
    HARVARD = "harvard"  # Harvard referencing
    IEEE = "ieee"  # Institute of Electrical and Electronics Engineers
    VANCOUVER = "vancouver"  # Vancouver system
    NATURE = "nature"  # Nature journal style
    SCIENCE = "science"  # Science journal style


class AuthorType(str, Enum):
    """Types of reference authors."""
    
    PERSON = "person"
    ORGANIZATION = "organization"


class ReferenceType(str, Enum):
    """Types of academic references."""
    
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PAPER = "conference_paper"
    THESIS = "thesis"
    REPORT = "report"
    WEBSITE = "website"
    PREPRINT = "preprint"
    DATASET = "dataset"
    SOFTWARE = "software"
    OTHER = "other"


@dataclass
class Author(BaseEntity):
    """Model representing an author of an academic reference."""
    
    type: AuthorType = AuthorType.PERSON
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None
    orcid_id: Optional[str] = None
    
    def full_name(self) -> str:
        """
        Get the full name of the author.
        
        Returns:
            str: Full name in the format "Last, First" for persons, or organization name
        """
        if self.type == AuthorType.PERSON:
            if self.first_name and self.last_name:
                return f"{self.last_name}, {self.first_name}"
            elif self.last_name:
                return self.last_name
            elif self.first_name:
                return self.first_name
            else:
                return "Unknown Author"
        else:  # ORGANIZATION
            return self.organization_name or "Unknown Organization"


@dataclass
class Reference(BaseEntity):
    """Model representing an academic reference/citation."""
    
    type: ReferenceType = ReferenceType.JOURNAL_ARTICLE
    authors: List[Author] = field(default_factory=list)
    title: str = ""
    year: Optional[int] = None
    
    # Journal article specific fields
    journal_name: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    
    # Book specific fields
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    edition: Optional[str] = None
    
    # Conference paper specific fields
    conference_name: Optional[str] = None
    conference_location: Optional[str] = None
    
    # Website specific fields
    url: Optional[str] = None
    accessed_date: Optional[datetime] = None
    
    # Preprint specific fields
    preprint_server: Optional[str] = None
    preprint_id: Optional[str] = None
    
    # Dataset specific fields
    repository: Optional[str] = None
    dataset_id: Optional[str] = None
    version: Optional[str] = None
    
    # General fields
    abstract: Optional[str] = None
    keywords: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)
    custom_fields: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Reference title cannot be empty")
    
    def update(self, **kwargs) -> 'Reference':
        """Update reference fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_author(self, author: Author) -> None:
        """Add an author to the reference."""
        self.authors.append(author)
        self.updated_at = datetime.now()
    
    def remove_author(self, author_id: str) -> bool:
        """
        Remove an author from the reference.
        
        Args:
            author_id: The ID of the author to remove
            
        Returns:
            bool: True if author was removed, False if not found
        """
        original_length = len(self.authors)
        self.authors = [author for author in self.authors if author.id != author_id]
        
        if len(self.authors) < original_length:
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_keyword(self, keyword: str) -> None:
        """Add a keyword to the reference."""
        self.keywords.add(keyword)
        self.updated_at = datetime.now()
    
    def remove_keyword(self, keyword: str) -> None:
        """Remove a keyword from the reference."""
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            self.updated_at = datetime.now()
    
    def add_note(self, note: str) -> None:
        """Add a note to the reference."""
        self.notes.append(note)
        self.updated_at = datetime.now()
    
    def update_custom_field(self, key: str, value: str) -> None:
        """Update a custom field."""
        self.custom_fields[key] = value
        self.updated_at = datetime.now()
    
    def remove_custom_field(self, key: str) -> bool:
        """
        Remove a custom field.
        
        Args:
            key: The key of the custom field to remove
            
        Returns:
            bool: True if field was removed, False if not found
        """
        if key in self.custom_fields:
            del self.custom_fields[key]
            self.updated_at = datetime.now()
            return True
        return False
    
    def author_names_formatted(self) -> str:
        """
        Get formatted author names for citation.
        
        Returns:
            str: Formatted author list for citation
        """
        if not self.authors:
            return "Unknown Author"
        
        if len(self.authors) == 1:
            return self.authors[0].full_name()
        
        if len(self.authors) == 2:
            return f"{self.authors[0].full_name()} and {self.authors[1].full_name()}"
        
        if len(self.authors) > 2:
            return f"{self.authors[0].full_name()} et al."


@dataclass
class TaskReferenceLink(BaseEntity):
    """Model representing a link between a research task and a reference."""
    
    task_id: str = ""
    reference_id: str = ""
    relevance: Optional[str] = None  # Description of why this reference is relevant to the task
    
    # Link-specific notes
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        if not self.reference_id:
            raise ValueError("Reference ID cannot be empty")
    
    def update(self, **kwargs) -> 'TaskReferenceLink':
        """Update link fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_note(self, note: str) -> None:
        """Add a note to the link."""
        self.notes.append(note)
        self.updated_at = datetime.now()