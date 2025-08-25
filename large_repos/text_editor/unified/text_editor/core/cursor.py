"""
Cursor implementation for the text editor.
This module extends the common cursor implementation for backward compatibility.
"""
from typing import Tuple
from common.core import Cursor as CommonCursor, Position
from text_editor.core.buffer import TextBuffer


class Cursor(CommonCursor):
    """
    Represents a cursor position within a text buffer.
    
    This class extends the common Cursor and provides backward-compatible
    methods for the student text editor implementation.
    """
    # Add line and column as properties for backward compatibility
    @property
    def line(self) -> int:
        """Get current line number."""
        return self.position.line
    
    @line.setter
    def line(self, value: int):
        """Set line number."""
        self.position.line = value
    
    @property
    def column(self) -> int:
        """Get current column number."""
        return self.position.column
    
    @column.setter
    def column(self, value: int):
        """Set column number."""
        self.position.column = value
    
    def __init__(self, buffer: TextBuffer = None, **data):
        """Initialize cursor with optional buffer."""
        if buffer is None:
            buffer = TextBuffer()
        super().__init__(buffer=buffer, **data)
    
    def move_to(self, line: int, column: int) -> None:
        """
        Move the cursor to the specified position.
        
        Args:
            line: Target line number (0-indexed)
            column: Target column number (0-indexed)
            
        Raises:
            IndexError: If the position is invalid
        """
        position = Position(line=line, column=column)
        super().move_to(position)
    
    def get_position(self) -> Tuple[int, int]:
        """
        Get the current cursor position.
        
        Returns:
            A tuple of (line, column)
        """
        return (self.position.line, self.position.column)
    
    def move_up(self, count: int = 1) -> None:
        """
        Move the cursor up by the specified number of lines.
        
        Args:
            count: Number of lines to move up (default: 1)
        """
        super().move_up(count)
    
    def move_down(self, count: int = 1) -> None:
        """
        Move the cursor down by the specified number of lines.
        
        Args:
            count: Number of lines to move down (default: 1)
        """
        super().move_down(count)
    
    def move_left(self, count: int = 1) -> None:
        """
        Move the cursor left by the specified number of characters.
        
        If the cursor is at the beginning of a line, it will move to the
        end of the previous line.
        
        Args:
            count: Number of characters to move left (default: 1)
        """
        super().move_left(count)
    
    def move_right(self, count: int = 1) -> None:
        """
        Move the cursor right by the specified number of characters.
        
        If the cursor is at the end of a line, it will move to the
        beginning of the next line.
        
        Args:
            count: Number of characters to move right (default: 1)
        """
        super().move_right(count)
    
    def move_to_line_start(self) -> None:
        """Move the cursor to the start of the current line."""
        super().move_to_line_start()
    
    def move_to_line_end(self) -> None:
        """Move the cursor to the end of the current line."""
        super().move_to_line_end()
    
    def move_to_buffer_start(self) -> None:
        """Move the cursor to the start of the buffer."""
        super().move_to_buffer_start()
    
    def move_to_buffer_end(self) -> None:
        """Move the cursor to the end of the buffer."""
        super().move_to_buffer_end()