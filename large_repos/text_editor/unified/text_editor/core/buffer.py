"""
Text buffer implementation for the text editor.
This module extends the common buffer implementation for backward compatibility.
"""
from typing import List, Tuple, Optional
from common.core import TextBuffer as CommonTextBuffer, Position


class TextBuffer(CommonTextBuffer):
    """
    A text buffer that stores the content of a file as a list of lines.
    
    This class extends the common TextBuffer and provides backward-compatible
    methods for the student text editor implementation.
    """
    
    def insert_text(self, line: int, column: int, text: str) -> None:
        """
        Insert text at the specified position in the buffer.
        
        Args:
            line: Line number where text should be inserted (0-indexed)
            column: Column number where text should be inserted (0-indexed)
            text: The text to insert
            
        Raises:
            IndexError: If the line or column is out of range
        """
        position = Position(line=line, column=column)
        super().insert_text(position, text)
    
    def delete_text(self, start_line: int, start_col: int, 
                   end_line: int, end_col: int) -> str:
        """
        Delete text between the specified positions and return the deleted text.
        
        Args:
            start_line: Starting line number (0-indexed)
            start_col: Starting column number (0-indexed)
            end_line: Ending line number (0-indexed)
            end_col: Ending column number (0-indexed)
            
        Returns:
            The deleted text
            
        Raises:
            IndexError: If any position is out of range
            ValueError: If the end position comes before the start position
        """
        start = Position(line=start_line, column=start_col)
        end = Position(line=end_line, column=end_col)
        return super().delete_text(start, end)
        
    def replace_text(self, start_line: int, start_col: int,
                    end_line: int, end_col: int, new_text: str) -> str:
        """
        Replace text between the specified positions with new text.
        
        Args:
            start_line: Starting line number (0-indexed)
            start_col: Starting column number (0-indexed)
            end_line: Ending line number (0-indexed)
            end_col: Ending column number (0-indexed)
            new_text: The text to insert
            
        Returns:
            The replaced text
            
        Raises:
            IndexError: If any position is out of range
            ValueError: If the end position comes before the start position
        """
        # Delete the text first and get what was deleted
        deleted_text = self.delete_text(start_line, start_col, end_line, end_col)
        
        # Insert the new text
        self.insert_text(start_line, start_col, new_text)
        
        return deleted_text