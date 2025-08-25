"""
History management for undo/redo functionality.
This module extends the common history implementation for backward compatibility.
"""
from typing import List, Dict, Any, Callable, Optional, Tuple
from common.core import History as CommonHistory, EditOperation as CommonEditOperation, Position, OperationType
import time


class EditOperation(CommonEditOperation):
    """
    Represents an editing operation that can be undone or redone.
    This class provides backward compatibility with the original interface.
    """
    
    @property
    def start_line(self) -> int:
        """Get start line for backward compatibility."""
        return self.start.line
    
    @property
    def start_col(self) -> int:
        """Get start column for backward compatibility."""
        return self.start.column
    
    @property
    def end_line(self) -> Optional[int]:
        """Get end line for backward compatibility."""
        return self.end.line if self.end else None
    
    @property
    def end_col(self) -> Optional[int]:
        """Get end column for backward compatibility."""
        return self.end.column if self.end else None
    
    @classmethod
    def from_legacy(cls, type: str, start_line: int, start_col: int,
                   end_line: Optional[int] = None, end_col: Optional[int] = None,
                   text: str = "", deleted_text: str = "", timestamp: float = None) -> 'EditOperation':
        """Create from legacy parameters."""
        op_type = OperationType(type)
        start = Position(line=start_line, column=start_col)
        end = Position(line=end_line, column=end_col) if end_line is not None else None
        
        return cls(
            type=op_type,
            start=start,
            end=end,
            text=text,
            deleted_text=deleted_text,
            timestamp=timestamp or time.time()
        )


class History(CommonHistory):
    """
    Manages the history of editing operations for undo/redo functionality.
    This class extends the common History for backward compatibility.
    """
    
    def record_insert(self, line: int, col: int, text: str) -> None:
        """
        Record an insert operation.
        
        Args:
            line: Line where text was inserted
            col: Column where text was inserted
            text: Text that was inserted
        """
        operation = EditOperation(
            type=OperationType.INSERT,
            start=Position(line=line, column=col),
            text=text,
            timestamp=time.time()
        )
        self._add_operation(operation)
    
    def record_delete(self, start_line: int, start_col: int, 
                     end_line: int, end_col: int, deleted_text: str) -> None:
        """
        Record a delete operation.
        
        Args:
            start_line: Starting line of deleted text
            start_col: Starting column of deleted text
            end_line: Ending line of deleted text
            end_col: Ending column of deleted text
            deleted_text: The text that was deleted
        """
        operation = EditOperation(
            type=OperationType.DELETE,
            start=Position(line=start_line, column=start_col),
            end=Position(line=end_line, column=end_col),
            deleted_text=deleted_text,
            timestamp=time.time()
        )
        self._add_operation(operation)
    
    def record_replace(self, start_line: int, start_col: int,
                      end_line: int, end_col: int, 
                      new_text: str, deleted_text: str) -> None:
        """
        Record a replace operation.
        
        Args:
            start_line: Starting line of replaced text
            start_col: Starting column of replaced text
            end_line: Ending line of replaced text
            end_col: Ending column of replaced text
            new_text: The text that was inserted
            deleted_text: The text that was deleted
        """
        operation = EditOperation(
            type=OperationType.REPLACE,
            start=Position(line=start_line, column=start_col),
            end=Position(line=end_line, column=end_col),
            text=new_text,
            deleted_text=deleted_text,
            timestamp=time.time()
        )
        self._add_operation(operation)
    
    def undo(self) -> Optional[EditOperation]:
        """Get the operation to undo."""
        op = super().undo()
        if op and not isinstance(op, EditOperation):
            # Convert to EditOperation if needed
            return EditOperation(
                type=op.type,
                start=op.start,
                end=op.end,
                text=op.text,
                deleted_text=op.deleted_text,
                timestamp=op.timestamp,
                metadata=op.metadata
            )
        return op
    
    def redo(self) -> Optional[EditOperation]:
        """Get the operation to redo."""
        op = super().redo()
        if op and not isinstance(op, EditOperation):
            # Convert to EditOperation if needed
            return EditOperation(
                type=op.type,
                start=op.start,
                end=op.end,
                text=op.text,
                deleted_text=op.deleted_text,
                timestamp=op.timestamp,
                metadata=op.metadata
            )
        return op