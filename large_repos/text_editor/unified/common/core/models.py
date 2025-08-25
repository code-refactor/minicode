"""Common data models for the unified text editor library."""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field
import uuid


class BaseModel(PydanticBaseModel):
    """Extended Pydantic BaseModel with common functionality."""
    
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True


class Position(BaseModel):
    """Represents a position in a text buffer."""
    
    line: int = 0
    column: int = 0
    
    def __lt__(self, other: 'Position') -> bool:
        """Check if this position comes before another."""
        if self.line < other.line:
            return True
        if self.line == other.line and self.column < other.column:
            return True
        return False
    
    def __le__(self, other: 'Position') -> bool:
        """Check if this position comes before or equals another."""
        return self < other or self == other
    
    def __gt__(self, other: 'Position') -> bool:
        """Check if this position comes after another."""
        return not self <= other
    
    def __ge__(self, other: 'Position') -> bool:
        """Check if this position comes after or equals another."""
        return not self < other
    
    def to_tuple(self) -> Tuple[int, int]:
        """Convert to tuple representation."""
        return (self.line, self.column)
    
    @classmethod
    def from_tuple(cls, pos: Tuple[int, int]) -> 'Position':
        """Create from tuple representation."""
        return cls(line=pos[0], column=pos[1])


class Range(BaseModel):
    """Represents a range of text between two positions."""
    
    start: Position
    end: Position
    
    def __init__(self, start: Position, end: Position, **data):
        """Initialize ensuring start comes before end."""
        if start > end:
            start, end = end, start
        super().__init__(start=start, end=end, **data)
    
    def contains(self, position: Position) -> bool:
        """Check if a position is within this range."""
        return self.start <= position <= self.end
    
    def overlaps(self, other: 'Range') -> bool:
        """Check if this range overlaps with another."""
        return not (self.end < other.start or other.end < self.start)


class Metadata(BaseModel):
    """Standard metadata structure for documents and elements."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: Dict[str, Any] = Field(default_factory=dict)
    
    def update(self) -> None:
        """Update the timestamp."""
        self.updated_at = datetime.now()


class TextSegment(BaseModel):
    """A segment of text with metadata."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    position: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_word_count(self) -> int:
        """Get the number of words in this segment."""
        import re
        return len(re.findall(r'\b\w+\b', self.content))
    
    def get_line_count(self) -> int:
        """Get the number of lines in this segment."""
        return len(self.content.splitlines())


class Section(BaseModel):
    """A section containing multiple text segments."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    segments: list[TextSegment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_content(self) -> str:
        """Get the full content of this section."""
        return "\n".join([segment.content for segment in self.segments])
    
    def get_word_count(self) -> int:
        """Get the total word count of this section."""
        return sum(segment.get_word_count() for segment in self.segments)
    
    def add_segment(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> TextSegment:
        """Add a new segment to this section."""
        position = len(self.segments)
        segment = TextSegment(
            content=content,
            position=position,
            metadata=metadata or {}
        )
        self.segments.append(segment)
        return segment
    
    def get_segment(self, position: int) -> Optional[TextSegment]:
        """Get the segment at the specified position."""
        if 0 <= position < len(self.segments):
            return self.segments[position]
        return None
    
    def update_segment(self, position: int, content: str) -> Optional[TextSegment]:
        """Update the content of a segment."""
        segment = self.get_segment(position)
        if segment:
            segment.content = content
            return segment
        return None
    
    def delete_segment(self, position: int) -> bool:
        """Delete a segment at the specified position."""
        if 0 <= position < len(self.segments):
            self.segments.pop(position)
            # Update positions
            for i in range(position, len(self.segments)):
                self.segments[i].position = i
            return True
        return False