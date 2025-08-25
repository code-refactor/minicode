"""
Interface modules for the File System Analyzer unified library.

This package provides standard interfaces for file system access,
API interactions, and other external system integrations.
"""

from .filesystem import FileSystemInterface, EnhancedFileSystemInterface
from .api import BaseAPI, AnalysisAPI

__all__ = [
    'FileSystemInterface',
    'EnhancedFileSystemInterface', 
    'BaseAPI',
    'AnalysisAPI'
]