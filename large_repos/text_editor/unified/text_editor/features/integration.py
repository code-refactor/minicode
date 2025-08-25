"""
Integration of the progressive feature system with the text editor.
"""
from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field
import time

from text_editor.core.editor import Editor
from text_editor.features.manager import FeatureManager
from text_editor.features.models import FeatureCategory, SkillLevel, Feature


class ProgressiveEditor(BaseModel):
    """
    Editor with progressive feature unlocking.
    
    This class wraps the core editor functionality and adds the progressive
    feature system, controlling which features are available based on the
    user's skill level.
    """
    editor: Editor = Field(default_factory=Editor)
    feature_manager: FeatureManager = Field(default_factory=FeatureManager)
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        """Initialize the progressive editor."""
        super().__init__(**kwargs)
        
        # Register feature hooks for special handling
        self._register_feature_hooks()
    
    def _register_feature_hooks(self) -> None:
        """Register feature hooks for special handling of newly unlocked features."""
        # We could add hooks here for features that need special handling when unlocked
        self.feature_manager.register_feature_hook(
            "find_replace",
            lambda f: print(f"Newly unlocked: {f.name} - {f.description}")
        )
    
    def _check_feature_access(self, feature_id: str) -> bool:
        """
        Check if the user has access to a specific feature.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the user has access to the feature, False otherwise
        """
        has_access = self.feature_manager.is_feature_enabled(feature_id)
        
        if not has_access:
            # Log this attempt to use a disabled feature
            print(f"Attempted to use disabled feature: {feature_id}")
            
            # Provide guidance on how to unlock the feature
            pending_features = self.feature_manager.get_pending_features()
            for feature in pending_features:
                if feature.id == feature_id:
                    print(f"Feature '{feature.name}' requires skill level: {feature.required_skill_level.name}")
                    if feature.prerequisites:
                        print(f"Prerequisites: {', '.join(feature.prerequisites)}")
        
        return has_access
    
    def _record_feature_usage(self, feature_id: str) -> None:
        """
        Record that a feature was used.
        
        Args:
            feature_id: ID of the feature that was used
        """
        self.feature_manager.record_feature_usage(feature_id)
    
    # Core editing operations with feature checks
    
    def get_content(self) -> str:
        """Get the entire content of the editor."""
        # This is a basic feature available to all skill levels
        self._record_feature_usage("basic_text_insertion")
        return self.editor.get_content()
    
    def insert_text(self, text: str) -> None:
        """
        Insert text at the current cursor position.
        
        Args:
            text: The text to insert
        """
        # This is a basic feature available to all skill levels
        self._record_feature_usage("basic_text_insertion")
        self.editor.insert_text(text)
    
    def delete_char_before_cursor(self) -> None:
        """Delete the character before the cursor (backspace operation)."""
        # This is a basic feature available to all skill levels
        self._record_feature_usage("basic_text_deletion")
        self.editor.delete_char_before_cursor()
    
    def delete_char_after_cursor(self) -> None:
        """Delete the character after the cursor (delete key operation)."""
        # This is a basic feature available to all skill levels
        self._record_feature_usage("basic_text_deletion")
        self.editor.delete_char_after_cursor()
    
    def move_cursor(self, direction: str, count: int = 1) -> None:
        """
        Move the cursor in the specified direction.
        
        Args:
            direction: One of "up", "down", "left", "right", 
                      "line_start", "line_end", "buffer_start", "buffer_end"
            count: Number of units to move (for up, down, left, right)
        """
        # Different cursor movements might require different feature access
        if direction in ["up", "down", "left", "right"]:
            self._record_feature_usage("basic_cursor_movement")
        elif direction in ["line_start", "line_end"]:
            if not self._check_feature_access("line_operations"):
                return
            self._record_feature_usage("line_operations")
        elif direction in ["buffer_start", "buffer_end"]:
            if not self._check_feature_access("line_operations"):
                return
            self._record_feature_usage("line_operations")
        
        self.editor.move_cursor(direction, count)
    
    # Word navigation requires intermediate skill level
    
    def move_by_word(self, direction: str, count: int = 1) -> None:
        """
        Move the cursor by words.
        
        Args:
            direction: Either "left" or "right"
            count: Number of words to move
        """
        if not self._check_feature_access("word_navigation"):
            return
            
        self._record_feature_usage("word_navigation")
        
        # Implementation depends on direction
        if direction == "left":
            # Move left word by word
            for _ in range(count):
                line, col = self.editor.get_cursor_position()
                line_text = self.editor.get_line(line)
                
                # Find the previous word boundary
                if col > 0:
                    i = col - 1
                    # Skip spaces
                    while i > 0 and line_text[i].isspace():
                        i -= 1
                    # Find start of word
                    while i > 0 and not line_text[i-1].isspace():
                        i -= 1
                    self.editor.set_cursor_position(line, i)
                elif line > 0:
                    # Move to the end of the previous line
                    self.editor.set_cursor_position(line-1, len(self.editor.get_line(line-1)))
        elif direction == "right":
            # Move right word by word
            for _ in range(count):
                line, col = self.editor.get_cursor_position()
                line_text = self.editor.get_line(line)
                line_length = len(line_text)
                
                # Find the next word boundary
                if col < line_length:
                    i = col
                    # Find end of current word
                    while i < line_length and not line_text[i].isspace():
                        i += 1
                    # Skip spaces
                    while i < line_length and line_text[i].isspace():
                        i += 1
                    self.editor.set_cursor_position(line, i)
                elif line < self.editor.get_line_count() - 1:
                    # Move to the beginning of the next line
                    self.editor.set_cursor_position(line+1, 0)
    
    # Undo/redo operations require intermediate skill level
    
    def undo(self) -> bool:
        """
        Undo the last operation.
        
        Returns:
            True if an operation was undone, False otherwise
        """
        if not self._check_feature_access("undo_redo"):
            return False
            
        self._record_feature_usage("undo_redo")
        return self.editor.undo()
    
    def redo(self) -> bool:
        """
        Redo the last undone operation.
        
        Returns:
            True if an operation was redone, False otherwise
        """
        if not self._check_feature_access("undo_redo"):
            return False
            
        self._record_feature_usage("undo_redo")
        return self.editor.redo()
    
    # File operations
    
    def load_file(self, file_path: str) -> None:
        """
        Load content from a file.
        
        Args:
            file_path: Path to the file to load
        """
        self._record_feature_usage("load_save_file")
        self.editor.load_file(file_path)
    
    def save_file(self, file_path: Optional[str] = None) -> None:
        """
        Save content to a file.
        
        Args:
            file_path: Path to save to (if None, uses current path)
        """
        self._record_feature_usage("load_save_file")
        self.editor.save_file(file_path)
    
    # Advanced search features
    
    def find_text(self, text: str, start_line: int = 0, start_col: int = 0) -> Optional[Dict[str, int]]:
        """
        Find text in the document.
        
        Args:
            text: Text to search for
            start_line: Line to start searching from (0-indexed)
            start_col: Column to start searching from (0-indexed)
            
        Returns:
            Dict with 'line' and 'column' keys if found, None otherwise
        """
        if not self._check_feature_access("find_text"):
            return None
            
        self._record_feature_usage("find_text")
        
        # Simple sequential search implementation
        for line_num in range(start_line, self.editor.get_line_count()):
            line_text = self.editor.get_line(line_num)
            
            # For the first line, start from the specified column
            col = start_col if line_num == start_line else 0
            
            # Search in this line
            found_pos = line_text.find(text, col)
            if found_pos >= 0:
                return {
                    "line": line_num,
                    "column": found_pos
                }
        
        return None
    
    def replace_text(self, search_text: str, replace_text: str, start_line: int = 0, 
                     start_col: int = 0, all_occurrences: bool = False) -> int:
        """
        Find and replace text in the document.
        
        Args:
            search_text: Text to search for
            replace_text: Text to replace with
            start_line: Line to start searching from (0-indexed)
            start_col: Column to start searching from (0-indexed)
            all_occurrences: If True, replace all occurrences
            
        Returns:
            Number of replacements made
        """
        if not self._check_feature_access("find_replace"):
            return 0
            
        self._record_feature_usage("find_replace")
        
        replacements = 0
        position = self.find_text(search_text, start_line, start_col)
        
        while position:
            line, col = position["line"], position["column"]
            
            # Replace this occurrence
            self.editor.replace_text(
                line, col,
                line, col + len(search_text),
                replace_text
            )
            replacements += 1
            
            if not all_occurrences:
                break
                
            # Find the next occurrence, considering the replacement
            next_col = col + len(replace_text)
            position = self.find_text(search_text, line, next_col)
            if not position and line < self.editor.get_line_count() - 1:
                # If not found in this line, try the next line
                position = self.find_text(search_text, line + 1, 0)
        
        return replacements
    
    # Feature management methods
    
    def get_available_features(self) -> List[Feature]:
        """
        Get a list of currently available features.
        
        Returns:
            List of available Feature objects
        """
        return self.feature_manager.get_available_features()
    
    def get_pending_features(self) -> List[Feature]:
        """
        Get a list of features that could be unlocked next.
        
        Returns:
            List of pending Feature objects
        """
        return self.feature_manager.get_pending_features()
    
    def get_progress_report(self) -> Dict[str, Any]:
        """
        Get a report of the user's progress.
        
        Returns:
            Dictionary with progress information
        """
        return self.feature_manager.get_user_progress_report()
    
    def set_skill_level(self, level: SkillLevel) -> List[Feature]:
        """
        Set the user's skill level directly (for testing).
        
        Args:
            level: The skill level to set
            
        Returns:
            List of newly unlocked features
        """
        return self.feature_manager.set_skill_level(level)
    
    def get_feature_guidance(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """
        Get guidance for a specific feature.
        
        Args:
            feature_id: ID of the feature to get guidance for
            
        Returns:
            Dictionary with guidance information, or None if the feature doesn't exist
        """
        return self.feature_manager.get_feature_guidance(feature_id)