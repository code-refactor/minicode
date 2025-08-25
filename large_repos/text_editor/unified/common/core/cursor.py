"""Unified cursor implementation for the text editor."""

from typing import Optional, Tuple
from common.core.models import BaseModel, Position
from common.core.buffer import TextBuffer


class Cursor(BaseModel):
    """Represents a cursor position within a text buffer."""
    
    position: Position = Position(line=0, column=0)
    buffer: TextBuffer
    
    def __init__(self, buffer: TextBuffer, **data):
        """Initialize cursor with a buffer."""
        super().__init__(buffer=buffer, **data)
    
    def move_to(self, position: Position) -> None:
        """Move cursor to specified position."""
        line, column = position.line, position.column
        
        # Validate line
        if not (0 <= line < self.buffer.get_line_count()):
            raise IndexError(f"Line number {line} out of range")
        
        # Validate column
        line_length = len(self.buffer.get_line(line))
        if not (0 <= column <= line_length):
            raise IndexError(f"Column number {column} out of range for line {line}")
        
        self.position = position
    
    def get_position(self) -> Position:
        """Get current cursor position."""
        return self.position
    
    def move_up(self, count: int = 1) -> None:
        """Move cursor up by specified number of lines."""
        target_line = max(0, self.position.line - count)
        # Preserve column or adjust to line length
        target_column = min(self.position.column, len(self.buffer.get_line(target_line)))
        self.position = Position(line=target_line, column=target_column)
    
    def move_down(self, count: int = 1) -> None:
        """Move cursor down by specified number of lines."""
        target_line = min(self.buffer.get_line_count() - 1, self.position.line + count)
        # Preserve column or adjust to line length
        target_column = min(self.position.column, len(self.buffer.get_line(target_line)))
        self.position = Position(line=target_line, column=target_column)
    
    def move_left(self, count: int = 1) -> None:
        """Move cursor left by specified number of characters."""
        remaining = count
        line = self.position.line
        column = self.position.column
        
        while remaining > 0:
            if column > 0:
                # Move within current line
                move_amount = min(remaining, column)
                column -= move_amount
                remaining -= move_amount
            elif line > 0:
                # Move to end of previous line
                line -= 1
                column = len(self.buffer.get_line(line))
                remaining -= 1
            else:
                # At start of buffer
                break
        
        self.position = Position(line=line, column=column)
    
    def move_right(self, count: int = 1) -> None:
        """Move cursor right by specified number of characters."""
        remaining = count
        line = self.position.line
        column = self.position.column
        
        while remaining > 0:
            current_line_length = len(self.buffer.get_line(line))
            
            if column < current_line_length:
                # Move within current line
                move_amount = min(remaining, current_line_length - column)
                column += move_amount
                remaining -= move_amount
            elif line < self.buffer.get_line_count() - 1:
                # Move to beginning of next line
                line += 1
                column = 0
                remaining -= 1
            else:
                # At end of buffer
                break
        
        self.position = Position(line=line, column=column)
    
    def move_to_line_start(self) -> None:
        """Move cursor to start of current line."""
        self.position.column = 0
    
    def move_to_line_end(self) -> None:
        """Move cursor to end of current line."""
        self.position.column = len(self.buffer.get_line(self.position.line))
    
    def move_to_buffer_start(self) -> None:
        """Move cursor to start of buffer."""
        self.position = Position(line=0, column=0)
    
    def move_to_buffer_end(self) -> None:
        """Move cursor to end of buffer."""
        last_line = self.buffer.get_line_count() - 1
        self.position = Position(
            line=last_line,
            column=len(self.buffer.get_line(last_line))
        )
    
    def move_to_word_start(self) -> None:
        """Move cursor to start of current word."""
        line_text = self.buffer.get_line(self.position.line)
        col = self.position.column
        
        # Move backward to find word start
        while col > 0 and not line_text[col - 1].isalnum():
            col -= 1
        while col > 0 and line_text[col - 1].isalnum():
            col -= 1
        
        self.position.column = col
    
    def move_to_word_end(self) -> None:
        """Move cursor to end of current word."""
        line_text = self.buffer.get_line(self.position.line)
        col = self.position.column
        line_length = len(line_text)
        
        # Move forward to find word end
        while col < line_length and not line_text[col].isalnum():
            col += 1
        while col < line_length and line_text[col].isalnum():
            col += 1
        
        self.position.column = col
    
    def move_to_next_word(self) -> None:
        """Move cursor to start of next word."""
        line = self.position.line
        col = self.position.column
        
        while line < self.buffer.get_line_count():
            line_text = self.buffer.get_line(line)
            line_length = len(line_text)
            
            # Skip current word
            while col < line_length and line_text[col].isalnum():
                col += 1
            
            # Skip whitespace/punctuation
            while col < line_length and not line_text[col].isalnum():
                col += 1
            
            if col < line_length:
                # Found next word on same line
                self.position = Position(line=line, column=col)
                return
            
            # Move to next line
            line += 1
            col = 0
            
            if line < self.buffer.get_line_count():
                line_text = self.buffer.get_line(line)
                # Find first word on new line
                while col < len(line_text) and not line_text[col].isalnum():
                    col += 1
                if col < len(line_text):
                    self.position = Position(line=line, column=col)
                    return
    
    def move_to_previous_word(self) -> None:
        """Move cursor to start of previous word."""
        line = self.position.line
        col = self.position.column
        
        # If at start of word, move back one position
        if col > 0:
            col -= 1
        elif line > 0:
            line -= 1
            col = len(self.buffer.get_line(line))
        else:
            return  # Already at start
        
        while line >= 0:
            line_text = self.buffer.get_line(line)
            
            # Skip whitespace/punctuation backward
            while col > 0 and not line_text[col - 1].isalnum():
                col -= 1
            
            # Skip word backward
            while col > 0 and line_text[col - 1].isalnum():
                col -= 1
            
            if col >= 0 and (col == 0 or not line_text[col - 1].isalnum()):
                # Found start of word
                self.position = Position(line=line, column=col)
                return
            
            # Move to previous line
            if line > 0:
                line -= 1
                col = len(self.buffer.get_line(line))
            else:
                break