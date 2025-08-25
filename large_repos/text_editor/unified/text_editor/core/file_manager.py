"""
File management functionality for the text editor.
This module extends the common file manager for backward compatibility.
"""
from typing import Optional
from common.core import FileManager as CommonFileManager, BaseModel
import time
import os


class FileManager(BaseModel):
    """
    Manages file operations for the text editor.
    
    This class wraps the common FileManager and provides backward-compatible
    methods for the student text editor implementation.
    """
    current_path: Optional[str] = None
    last_saved_time: Optional[float] = None
    _common_manager: CommonFileManager = CommonFileManager()
    
    def load_file(self, file_path: str) -> str:
        """
        Load content from a file.
        
        Args:
            file_path: Path to the file to load
            
        Returns:
            The file content as a string
            
        Raises:
            FileNotFoundError: If the file does not exist
            PermissionError: If the file cannot be read
        """
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.current_path = file_path
            self.last_saved_time = os.path.getmtime(file_path)
            
            # Calculate loading time for performance metrics
            load_time_ms = (time.time() - start_time) * 1000
            return content
            
        except UnicodeDecodeError:
            # Try with latin-1 encoding as a fallback
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            self.current_path = file_path
            self.last_saved_time = os.path.getmtime(file_path)
            
            return content
    
    def save_file(self, content: str, file_path: Optional[str] = None) -> None:
        """
        Save content to a file.
        
        Args:
            content: The content to save
            file_path: Path to save to (if None, uses current_path)
            
        Raises:
            ValueError: If no file path is provided and no current path is set
            PermissionError: If the file cannot be written
        """
        start_time = time.time()
        
        # Use the provided path or the current path
        path = file_path or self.current_path
        
        if not path:
            raise ValueError("No file path provided and no current path set")
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.current_path = path
        self.last_saved_time = time.time()
        
        # Calculate saving time for performance metrics
        save_time_ms = (time.time() - start_time) * 1000
    
    def is_file_modified(self, file_path: Optional[str] = None) -> bool:
        """
        Check if the file has been modified since it was last saved.
        
        Args:
            file_path: Path to check (if None, uses current_path)
            
        Returns:
            True if the file has been modified, False otherwise
            
        Raises:
            ValueError: If no file path is provided and no current path is set
        """
        path = file_path or self.current_path
        
        if not path:
            raise ValueError("No file path provided and no current path set")
        
        if not os.path.exists(path):
            return True
        
        if not self.last_saved_time:
            return True
        
        return os.path.getmtime(path) > self.last_saved_time
    
    def get_current_path(self) -> Optional[str]:
        """
        Get the current file path.
        
        Returns:
            The current file path, or None if no file is open
        """
        return self.current_path