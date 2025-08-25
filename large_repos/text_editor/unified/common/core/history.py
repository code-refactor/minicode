"""Unified history management for undo/redo functionality."""

from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime
import time
from enum import Enum
from common.core.models import BaseModel, Position


class OperationType(str, Enum):
    """Types of edit operations."""
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


class EditOperation(BaseModel):
    """Represents an editing operation that can be undone or redone."""
    
    type: OperationType
    start: Position
    end: Optional[Position] = None
    text: str = ""  # Text that was inserted/replaced
    deleted_text: str = ""  # Text that was deleted/replaced
    timestamp: float = time.time()
    metadata: Dict[str, Any] = {}
    
    def reverse(self) -> 'EditOperation':
        """Create the reverse operation for undo."""
        if self.type == OperationType.INSERT:
            # Reverse of insert is delete
            return EditOperation(
                type=OperationType.DELETE,
                start=self.start,
                end=Position(
                    line=self.start.line + self.text.count('\n'),
                    column=len(self.text.split('\n')[-1]) if '\n' in self.text 
                           else self.start.column + len(self.text)
                ),
                deleted_text=self.text,
                metadata=self.metadata
            )
        elif self.type == OperationType.DELETE:
            # Reverse of delete is insert
            return EditOperation(
                type=OperationType.INSERT,
                start=self.start,
                text=self.deleted_text,
                metadata=self.metadata
            )
        else:  # REPLACE
            # Reverse of replace is another replace
            return EditOperation(
                type=OperationType.REPLACE,
                start=self.start,
                end=self.end,
                text=self.deleted_text,
                deleted_text=self.text,
                metadata=self.metadata
            )


class History(BaseModel):
    """Manages history of editing operations for undo/redo."""
    
    undo_stack: List[EditOperation] = []
    redo_stack: List[EditOperation] = []
    max_history_size: int = 1000
    grouping_timeout: float = 0.5  # Group operations within this time
    last_operation_time: float = 0.0
    current_group: List[EditOperation] = []
    
    def record_insert(self, position: Position, text: str, metadata: Dict[str, Any] = None) -> None:
        """Record an insert operation."""
        operation = EditOperation(
            type=OperationType.INSERT,
            start=position,
            text=text,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self._add_operation(operation)
    
    def record_delete(self, start: Position, end: Position, deleted_text: str, 
                     metadata: Dict[str, Any] = None) -> None:
        """Record a delete operation."""
        operation = EditOperation(
            type=OperationType.DELETE,
            start=start,
            end=end,
            deleted_text=deleted_text,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self._add_operation(operation)
    
    def record_replace(self, start: Position, end: Position, new_text: str, 
                      deleted_text: str, metadata: Dict[str, Any] = None) -> None:
        """Record a replace operation."""
        operation = EditOperation(
            type=OperationType.REPLACE,
            start=start,
            end=end,
            text=new_text,
            deleted_text=deleted_text,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self._add_operation(operation)
    
    def _add_operation(self, operation: EditOperation) -> None:
        """Add an operation to the undo stack."""
        # For backward compatibility, immediately add to undo stack
        self.undo_stack.append(operation)
        
        # Clear redo stack when new edit is made
        self.redo_stack = []
        
        # Limit history size
        if len(self.undo_stack) > self.max_history_size:
            self.undo_stack.pop(0)
    
    def _commit_group(self) -> None:
        """Commit the current group of operations."""
        if self.current_group:
            # For now, just add each operation individually
            # Could be extended to create composite operations
            for op in self.current_group:
                self.undo_stack.append(op)
                
                # Limit history size
                if len(self.undo_stack) > self.max_history_size:
                    self.undo_stack.pop(0)
            
            self.current_group = []
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        # Commit any pending group first
        if self.current_group:
            self._commit_group()
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return len(self.redo_stack) > 0
    
    def undo(self) -> Optional[EditOperation]:
        """Get the operation to undo."""
        if not self.can_undo():
            return None
        
        operation = self.undo_stack.pop()
        self.redo_stack.append(operation)
        return operation  # Return original operation for backward compatibility
    
    def redo(self) -> Optional[EditOperation]:
        """Get the operation to redo."""
        if not self.can_redo():
            return None
        
        operation = self.redo_stack.pop()
        self.undo_stack.append(operation)
        return operation
    
    def clear(self) -> None:
        """Clear all history."""
        self.undo_stack = []
        self.redo_stack = []
        self.current_group = []
        self.last_operation_time = 0.0
    
    def get_history_size(self) -> Dict[str, int]:
        """Get the size of history stacks."""
        return {
            "undo": len(self.undo_stack),
            "redo": len(self.redo_stack),
            "pending": len(self.current_group)
        }


class RevisionHistory(History):
    """Extended history with revision/checkpoint support."""
    
    revisions: Dict[str, List[EditOperation]] = {}
    current_revision: Optional[str] = None
    
    def create_revision(self, name: str, metadata: Dict[str, Any] = None) -> None:
        """Create a named revision point."""
        # Commit any pending operations
        if self.current_group:
            self._commit_group()
        
        # Store current state as revision
        self.revisions[name] = self.undo_stack.copy()
        self.current_revision = name
        
        # Add metadata if provided
        if metadata:
            for op in self.revisions[name]:
                op.metadata.update({"revision": name, **metadata})
    
    def restore_revision(self, name: str) -> bool:
        """Restore to a named revision."""
        if name not in self.revisions:
            return False
        
        # Clear current state
        self.clear()
        
        # Restore revision state
        self.undo_stack = self.revisions[name].copy()
        self.current_revision = name
        
        return True
    
    def list_revisions(self) -> List[Dict[str, Any]]:
        """List all available revisions."""
        result = []
        for name, operations in self.revisions.items():
            if operations:
                result.append({
                    "name": name,
                    "operation_count": len(operations),
                    "timestamp": operations[-1].timestamp if operations else None,
                    "is_current": name == self.current_revision
                })
        return result
    
    def delete_revision(self, name: str) -> bool:
        """Delete a named revision."""
        if name in self.revisions:
            del self.revisions[name]
            if self.current_revision == name:
                self.current_revision = None
            return True
        return False