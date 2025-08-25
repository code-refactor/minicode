"""Unified text buffer implementation for the text editor."""

from typing import List, Optional, Protocol
from abc import ABC, abstractmethod
from common.core.models import BaseModel, Position, Range


class IBuffer(Protocol):
    """Interface for text buffer implementations."""
    
    def get_content(self) -> str: ...
    def insert_text(self, position: Position, text: str) -> None: ...
    def delete_text(self, start: Position, end: Position) -> str: ...
    def replace_text(self, start: Position, end: Position, text: str) -> str: ...
    def get_line_count(self) -> int: ...


class BaseBuffer(ABC):
    """Abstract base class for text buffer implementations."""
    
    @abstractmethod
    def get_content(self) -> str:
        """Get the entire content of the buffer."""
        pass
    
    @abstractmethod
    def insert_text(self, position: Position, text: str) -> None:
        """Insert text at the specified position."""
        pass
    
    @abstractmethod
    def delete_text(self, start: Position, end: Position) -> str:
        """Delete text between two positions and return deleted text."""
        pass
    
    def replace_text(self, start: Position, end: Position, text: str) -> str:
        """Replace text between two positions."""
        # First delete the text
        deleted = self.delete_text(start, end)
        # Then insert new text at start position
        self.insert_text(start, text)
        return deleted
    
    @abstractmethod
    def get_line_count(self) -> int:
        """Get the number of lines in the buffer."""
        pass


class TextBuffer(BaseModel, BaseBuffer):
    """Line-based text buffer implementation."""
    
    lines: List[str] = []
    
    def __init__(self, content: str = ""):
        """Initialize with optional content."""
        super().__init__()
        self.lines = content.split("\n") if content else [""]
    
    def get_content(self) -> str:
        """Get the entire content as a string."""
        return "\n".join(self.lines)
    
    def get_line(self, line_number: int) -> str:
        """Get a specific line."""
        if 0 <= line_number < len(self.lines):
            return self.lines[line_number]
        raise IndexError(f"Line number {line_number} out of range")
    
    def get_line_count(self) -> int:
        """Get the number of lines."""
        return len(self.lines)
    
    def insert_text(self, position: Position, text: str) -> None:
        """Insert text at the specified position."""
        line, column = position.line, position.column
        
        # Validate position
        if not (0 <= line < len(self.lines)):
            raise IndexError(f"Line number {line} out of range")
        
        current_line = self.lines[line]
        if not (0 <= column <= len(current_line)):
            raise IndexError(f"Column number {column} out of range for line {line}")
        
        # Handle multi-line insertion
        if "\n" in text:
            new_lines = text.split("\n")
            first_part = current_line[:column]
            last_part = current_line[column:]
            
            # Create new set of lines
            new_content = [first_part + new_lines[0]]
            new_content.extend(new_lines[1:-1])
            new_content.append(new_lines[-1] + last_part)
            
            # Update buffer
            self.lines[line:line+1] = new_content
        else:
            # Single-line insertion
            new_line = current_line[:column] + text + current_line[column:]
            self.lines[line] = new_line
    
    def delete_text(self, start: Position, end: Position) -> str:
        """Delete text between two positions."""
        start_line, start_col = start.line, start.column
        end_line, end_col = end.line, end.column
        
        # Validate positions
        if start > end:
            raise ValueError("End position must come after start position")
        
        if not (0 <= start_line < len(self.lines)):
            raise IndexError(f"Start line {start_line} out of range")
        if not (0 <= end_line < len(self.lines)):
            raise IndexError(f"End line {end_line} out of range")
        
        start_line_text = self.lines[start_line]
        end_line_text = self.lines[end_line]
        
        if not (0 <= start_col <= len(start_line_text)):
            raise IndexError(f"Start column {start_col} out of range")
        if not (0 <= end_col <= len(end_line_text)):
            raise IndexError(f"End column {end_col} out of range")
        
        # Handle single-line deletion
        if start_line == end_line:
            deleted_text = start_line_text[start_col:end_col]
            self.lines[start_line] = start_line_text[:start_col] + start_line_text[end_col:]
            return deleted_text
        
        # Handle multi-line deletion
        deleted_lines = []
        deleted_lines.append(start_line_text[start_col:])
        
        if end_line - start_line > 1:
            deleted_lines.extend(self.lines[start_line+1:end_line])
        
        deleted_lines.append(end_line_text[:end_col])
        deleted_text = "\n".join(deleted_lines)
        
        # Update buffer
        new_line = start_line_text[:start_col] + end_line_text[end_col:]
        self.lines[start_line:end_line+1] = [new_line]
        
        return deleted_text
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.lines = [""]
    
    def get_text_in_range(self, range: Range) -> str:
        """Get text within a specific range."""
        start_line, start_col = range.start.line, range.start.column
        end_line, end_col = range.end.line, range.end.column
        
        if start_line == end_line:
            return self.lines[start_line][start_col:end_col]
        
        result = []
        result.append(self.lines[start_line][start_col:])
        
        for i in range(start_line + 1, end_line):
            result.append(self.lines[i])
        
        result.append(self.lines[end_line][:end_col])
        return "\n".join(result)
    
    def find_text(self, text: str, start: Optional[Position] = None) -> Optional[Position]:
        """Find text in the buffer starting from a position."""
        if start is None:
            start = Position(line=0, column=0)
        
        for line_idx in range(start.line, len(self.lines)):
            line = self.lines[line_idx]
            start_col = start.column if line_idx == start.line else 0
            
            col_idx = line.find(text, start_col)
            if col_idx != -1:
                return Position(line=line_idx, column=col_idx)
        
        return None