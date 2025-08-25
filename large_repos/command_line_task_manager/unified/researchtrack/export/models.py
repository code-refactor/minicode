from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field

from common.core import BaseEntity


class JournalFormat(str, Enum):
    """Supported academic journal formats."""

    NATURE = "nature"
    SCIENCE = "science"
    PLOS = "plos"
    FRONTIERS = "frontiers"
    CELL = "cell"
    IEEE = "ieee"
    ACM = "acm"
    JMLR = "jmlr"  # Journal of Machine Learning Research
    PNAS = "pnas"  # Proceedings of the National Academy of Sciences
    ROYAL_SOCIETY = "royal_society"
    DEFAULT = "default"


@dataclass
class TextBlock(BaseEntity):
    """A block of text content."""

    content: str = ""
    type: str = "text"
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.content:
            raise ValueError("Content cannot be empty")


@dataclass
class ImageBlock(BaseEntity):
    """A block containing an image."""

    path: str = ""  # Path to the image file
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    type: str = "image"
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.path:
            raise ValueError("Path cannot be empty")


@dataclass
class TableBlock(BaseEntity):
    """A block containing a table."""

    headers: List[str] = field(default_factory=list)
    data: List[List[str]] = field(default_factory=list)
    caption: Optional[str] = None
    type: str = "table"


@dataclass
class CodeBlock(BaseEntity):
    """A block containing code."""

    code: str = ""
    language: str = "python"
    type: str = "code"
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.code:
            raise ValueError("Code cannot be empty")


@dataclass
class EquationBlock(BaseEntity):
    """A block containing a mathematical equation."""

    equation: str = ""  # LaTeX format equation
    type: str = "equation"
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.equation:
            raise ValueError("Equation cannot be empty")


@dataclass
class CitationBlock(BaseEntity):
    """A block for a citation reference."""

    reference_ids: List[str] = field(default_factory=list)  # IDs of references to cite
    context: Optional[str] = None
    type: str = "citation"


@dataclass
class Section(BaseEntity):
    """A section in a document."""

    title: str = ""
    content_blocks: List[Any] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Title cannot be empty")


@dataclass
class Document(BaseEntity):
    """A complete academic document."""

    title: str = ""
    authors: List[str] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)
    corresponding_email: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    format: JournalFormat = JournalFormat.DEFAULT
    sections: List[Section] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Title cannot be empty")

    def add_run(self, parameters: List[Any]) -> Any:
        """Add a new run to this experiment."""
        # This is a stub for the test, it will be implemented in the formatter
        pass