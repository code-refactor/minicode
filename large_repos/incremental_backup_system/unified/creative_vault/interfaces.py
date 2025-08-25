"""
Interfaces for the CreativeVault backup system components.

This module defines abstract base classes and protocols that each component
must implement, ensuring consistent API design across the system.

Note: The BackupEngine interface is now imported from the common library.
Creative vault specific interfaces are defined here.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple, Union

# Import the common BackupEngine interface
from common.core.interfaces import BackupEngine


class VisualDiffGenerator(ABC):
    """Interface for the visual difference generator."""
    
    @abstractmethod
    def generate_image_diff(
        self, 
        original_path: Path, 
        modified_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate a visual difference image between two versions of an image file.
        
        Args:
            original_path: Path to the original image
            modified_path: Path to the modified image
            output_path: Optional path to save the difference visualization
            
        Returns:
            Path to the generated difference visualization
        """
        pass
    
    @abstractmethod
    def generate_model_diff(
        self, 
        original_path: Path, 
        modified_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate a visual difference representation between two versions of a 3D model.
        
        Args:
            original_path: Path to the original 3D model
            modified_path: Path to the modified 3D model
            output_path: Optional path to save the difference visualization
            
        Returns:
            Path to the generated difference visualization
        """
        pass
    
    @abstractmethod
    def get_diff_stats(
        self, 
        original_path: Path, 
        modified_path: Path
    ) -> Dict[str, Any]:
        """Get statistical information about the differences between two files.
        
        Args:
            original_path: Path to the original file
            modified_path: Path to the modified file
            
        Returns:
            Dictionary with statistical information about the differences
        """
        pass


class TimelineManager(ABC):
    """Interface for the creative timeline manager."""
    
    @abstractmethod
    def register_version(
        self, 
        file_path: Path, 
        snapshot_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new version of a file in the timeline.
        
        Args:
            file_path: Path to the file
            snapshot_id: ID of the snapshot containing this version
            metadata: Optional metadata about this version
            
        Returns:
            str: Unique version ID
        """
        pass
    
    @abstractmethod
    def get_file_timeline(
        self, 
        file_path: Path, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get the timeline of versions for a specific file.
        
        Args:
            file_path: Path to the file
            start_time: Optional start time to filter versions
            end_time: Optional end time to filter versions
            
        Returns:
            List of dictionaries containing version information
        """
        pass
    
    @abstractmethod
    def generate_thumbnail(self, version_id: str) -> Path:
        """Generate a thumbnail preview for a specific version.
        
        Args:
            version_id: ID of the version
            
        Returns:
            Path to the generated thumbnail
        """
        pass
    
    @abstractmethod
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two versions of a file.
        
        Args:
            version_id_1: ID of the first version
            version_id_2: ID of the second version
            
        Returns:
            Dictionary with comparison information
        """
        pass


class ElementExtractor(ABC):
    """Interface for the element extraction framework."""
    
    @abstractmethod
    def extract_element(
        self, 
        source_file: Path, 
        element_id: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Extract a specific element from a file.
        
        Args:
            source_file: Path to the source file
            element_id: ID of the element to extract
            output_path: Optional path to save the extracted element
            
        Returns:
            Path to the extracted element
        """
        pass
    
    @abstractmethod
    def list_elements(self, file_path: Path) -> List[Dict[str, Any]]:
        """List all extractable elements in a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dictionaries containing element information
        """
        pass
    
    @abstractmethod
    def replace_element(
        self, 
        target_file: Path, 
        element_id: str, 
        replacement_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Replace a specific element in a file.
        
        Args:
            target_file: Path to the target file
            element_id: ID of the element to replace
            replacement_path: Path to the replacement element
            output_path: Optional path to save the modified file
            
        Returns:
            Path to the modified file
        """
        pass


class AssetReferenceTracker(ABC):
    """Interface for the asset reference tracker."""
    
    @abstractmethod
    def scan_project(self, project_path: Path) -> Dict[str, Any]:
        """Scan a project directory to identify assets and references.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with information about identified assets and references
        """
        pass
    
    @abstractmethod
    def get_asset_references(self, asset_path: Path) -> List[Path]:
        """Get all files that reference a specific asset.
        
        Args:
            asset_path: Path to the asset
            
        Returns:
            List of paths to files that reference this asset
        """
        pass
    
    @abstractmethod
    def get_referenced_assets(self, file_path: Path) -> List[Path]:
        """Get all assets referenced by a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of paths to assets referenced by this file
        """
        pass
    
    @abstractmethod
    def update_reference(
        self, 
        file_path: Path, 
        old_asset_path: Path, 
        new_asset_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Update a reference to point to a different asset.
        
        Args:
            file_path: Path to the file containing the reference
            old_asset_path: Path to the currently referenced asset
            new_asset_path: Path to the new asset
            output_path: Optional path to save the modified file
            
        Returns:
            Path to the modified file
        """
        pass


class WorkspaceCapture(ABC):
    """Interface for the application environment capture."""
    
    @abstractmethod
    def capture_workspace(
        self, 
        application_name: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Capture the current workspace state of an application.
        
        Args:
            application_name: Name of the application
            output_path: Optional path to save the workspace state
            
        Returns:
            Path to the saved workspace state
        """
        pass
    
    @abstractmethod
    def restore_workspace(
        self, 
        workspace_path: Path, 
        application_name: Optional[str] = None
    ) -> bool:
        """Restore a workspace state to an application.
        
        Args:
            workspace_path: Path to the workspace state file
            application_name: Optional name of the application
            
        Returns:
            bool: True if restore was successful
        """
        pass
    
    @abstractmethod
    def get_supported_applications(self) -> List[str]:
        """Get a list of applications supported by the workspace capture system.
        
        Returns:
            List of supported application names
        """
        pass