"""
Creative Timeline Manager for version history.

This module provides functionality for managing the timeline of creative
file versions, including thumbnail generation and version comparison.
"""

import json
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from creative_vault.interfaces import TimelineManager, VisualDiffGenerator
from creative_vault.utils import create_unique_id, detect_file_type, load_json, save_json
from creative_vault.visual_diff.diff_generator import CreativeVisualDiffGenerator


class CreativeTimelineManager(TimelineManager):
    """Implementation of the creative timeline manager."""
    
    def __init__(
        self, 
        repository_path: Path,
        diff_generator: Optional[VisualDiffGenerator] = None,
        thumbnail_size: Tuple[int, int] = (256, 256)
    ):
        """Initialize the timeline manager.
        
        Args:
            repository_path: Path to the backup repository
            diff_generator: Optional visual difference generator
            thumbnail_size: Size of the generated thumbnails (width, height)
        """
        self.repository_path = repository_path
        self.timeline_path = repository_path / "timeline"
        self.timeline_path.mkdir(parents=True, exist_ok=True)
        
        self.thumbnails_path = repository_path / "thumbnails"
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)
        
        self.snapshots_path = repository_path / "snapshots"
        self.objects_path = repository_path / "objects"
        self._metadata_path = repository_path / "metadata"
        
        self.diff_generator = diff_generator or CreativeVisualDiffGenerator(
            output_directory=repository_path / "diffs"
        )
        
        self.thumbnail_size = thumbnail_size
    
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
            
        Raises:
            ValueError: If the snapshot does not exist
        """
        snapshot_path = self.snapshots_path / snapshot_id
        if not snapshot_path.exists():
            raise ValueError(f"Snapshot {snapshot_id} does not exist")
        
        # Create a unique version ID
        version_id = create_unique_id("ver-")
        
        # Get the snapshot manifest to find the file
        manifest_path = snapshot_path / "manifest.json"
        try:
            manifest = load_json(manifest_path)
        except Exception as e:
            raise ValueError(f"Failed to load snapshot manifest: {e}")
        
        # Try to find the file in the manifest using different path formats
        # First try the original path as-is
        relative_path = str(file_path)
        if relative_path not in manifest["files"]:
            # Try using just the filename
            file_name = file_path.name
            matching_paths = [path for path in manifest["files"].keys() if path.endswith(file_name)]
            if matching_paths:
                relative_path = matching_paths[0]
            else:
                # If still not found, fail with a clear error
                raise ValueError(f"File {relative_path} not found in snapshot {snapshot_id}")
        
        file_info = manifest["files"][relative_path]
        file_hash = file_info["hash"]
        
        # Create the file's timeline directory if it doesn't exist
        file_timeline_path = self._get_file_timeline_path(file_path)
        file_timeline_path.mkdir(parents=True, exist_ok=True)
        
        # Create version metadata
        version_info = {
            "id": version_id,
            "timestamp": datetime.now().isoformat(),
            "snapshot_id": snapshot_id,
            "file_path": relative_path,
            "file_hash": file_hash,
            "file_size": file_info["size"],
            "content_type": file_info["content_type"],
            "metadata": metadata or {}
        }
        
        # Save version metadata
        version_path = file_timeline_path / f"{version_id}.json"
        save_json(version_info, version_path)
        
        # Generate a thumbnail for the version
        try:
            thumbnail_path = self.generate_thumbnail(version_id)
            version_info["thumbnail_path"] = str(thumbnail_path)
            
            # Update the version metadata with the thumbnail path
            save_json(version_info, version_path)
        except Exception as e:
            print(f"Warning: Failed to generate thumbnail for {version_id}: {e}")
        
        # Update the file's timeline index
        self._update_timeline_index(file_path, version_id, version_info)
        
        return version_id
    
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
        file_timeline_path = self._get_file_timeline_path(file_path)
        
        if not file_timeline_path.exists():
            return []
        
        # Load the timeline index
        index_path = file_timeline_path / "index.json"
        if not index_path.exists():
            return []
        
        try:
            index = load_json(index_path)
        except Exception as e:
            print(f"Error loading timeline index: {e}")
            return []
        
        # Get all versions from the index
        versions = index.get("versions", [])
        
        # Filter by time range if specified
        if start_time or end_time:
            filtered_versions = []
            for version in versions:
                version_time = datetime.fromisoformat(version["timestamp"])
                
                if start_time and version_time < start_time:
                    continue
                if end_time and version_time > end_time:
                    continue
                
                filtered_versions.append(version)
            
            return filtered_versions
        
        return versions
    
    def generate_thumbnail(self, version_id: str) -> Path:
        """Generate a thumbnail preview for a specific version.
        
        Args:
            version_id: ID of the version
            
        Returns:
            Path to the generated thumbnail
            
        Raises:
            ValueError: If the version does not exist or is not supported
        """
        # Find the version metadata
        version_info = self._get_version_info(version_id)
        
        # Get the file hash and determine content type from the hash metadata
        file_hash = version_info["file_hash"]
        
        # Get the object path
        object_path = self._get_object_path(file_hash)
        if not object_path.exists():
            raise ValueError(f"Object file not found for version {version_id}")
        
        # Create the thumbnail path
        thumbnail_path = self.thumbnails_path / f"{version_id}.png"
        
        # Determine the content type from the file info
        content_type = version_info.get("content_type")
        if not content_type:
            # Try to determine from metadata
            metadata_path = self._metadata_path / file_hash[:2] / file_hash[2:4] / f"{file_hash}.json"
            if metadata_path.exists():
                try:
                    metadata = load_json(metadata_path)
                    content_type = metadata.get("content_type")
                except Exception:
                    pass
        
        # If we still don't have a content type, try to guess from the filename
        if not content_type:
            file_path_str = version_info.get("file_path", "")
            if file_path_str.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                content_type = "image"
            elif file_path_str.lower().endswith(('.obj', '.fbx', '.3ds', '.stl')):
                content_type = "model"
        
        # Generate the thumbnail based on the file type
        if content_type == "image":
            self._generate_image_thumbnail(object_path, thumbnail_path)
        elif content_type == "model":
            self._generate_model_thumbnail(object_path, thumbnail_path)
        else:
            # For unsupported file types, generate a generic thumbnail using the version info
            self._generate_generic_thumbnail_from_info(version_info, thumbnail_path)
        
        return thumbnail_path
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two versions of a file.
        
        Args:
            version_id_1: ID of the first version
            version_id_2: ID of the second version
            
        Returns:
            Dictionary with comparison information
            
        Raises:
            ValueError: If either version does not exist
        """
        # Get version information
        version_info_1 = self._get_version_info(version_id_1)
        version_info_2 = self._get_version_info(version_id_2)
        
        # Check if versions are of the same file
        if version_info_1["file_path"] != version_info_2["file_path"]:
            raise ValueError("Versions must be of the same file")
        
        # Get object paths
        file_hash_1 = version_info_1["file_hash"]
        file_hash_2 = version_info_2["file_hash"]
        
        object_path_1 = self._get_object_path(file_hash_1)
        object_path_2 = self._get_object_path(file_hash_2)
        
        # Create a diff path
        diff_id = create_unique_id("compare-")
        diff_output_path = self.repository_path / "diffs" / f"{diff_id}.png"
        
        # Ensure diffs directory exists
        diff_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine the content type from version info
        content_type = version_info_1.get("content_type")
        
        # If not available, try to determine from file extension
        if not content_type:
            file_path_str = version_info_1.get("file_path", "")
            if file_path_str.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                content_type = "image"
            elif file_path_str.lower().endswith(('.obj', '.fbx', '.3ds', '.stl')):
                content_type = "model"
            else:
                content_type = "unknown"
        
        # Generate a visual diff
        if content_type == "image":
            diff_path = self.diff_generator.generate_image_diff(
                object_path_1, object_path_2, diff_output_path)
        elif content_type == "model":
            diff_path = self.diff_generator.generate_model_diff(
                object_path_1, object_path_2, diff_output_path)
        else:
            # For unknown types, create a placeholder diff
            diff_path = diff_output_path
            # Create a simple placeholder image
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), "Diff not available for this file type", fill='black')
            img.save(diff_path)
        
        # Get diff statistics
        diff_stats = self.diff_generator.get_diff_stats(object_path_1, object_path_2)
        
        # Create comparison result
        result = {
            "version_1": {
                "id": version_id_1,
                "timestamp": version_info_1["timestamp"],
                "file_size": version_info_1["file_size"]
            },
            "version_2": {
                "id": version_id_2,
                "timestamp": version_info_2["timestamp"],
                "file_size": version_info_2["file_size"]
            },
            "diff_path": str(diff_path),
            "diff_stats": diff_stats,
            "content_type": content_type
        }
        
        return result
        
    def _generate_generic_thumbnail_from_info(self, version_info: Dict[str, Any], thumbnail_path: Path) -> None:
        """Generate a generic thumbnail for unsupported file types using version info.
        
        Args:
            version_info: Dictionary containing version metadata
            thumbnail_path: Path to save the thumbnail
        """
        # Create a blank image with file information
        img = Image.new('RGB', self.thumbnail_size, color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Add file name from version_info
        file_path_str = version_info.get("file_path", "Unknown file")
        file_name = Path(file_path_str).name
        draw.text((10, 10), file_name, fill=(0, 0, 0))
        
        # Add file type
        file_type = Path(file_path_str).suffix.upper() if "." in file_path_str else "UNKNOWN"
        draw.text((10, 40), f"Type: {file_type}", fill=(0, 0, 0))
        
        # Add version ID
        version_id = version_info.get("id", "unknown")
        draw.text((10, 70), f"Version: {version_id[:10]}...", fill=(0, 0, 0))
        
        # Add timestamp
        timestamp = version_info.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if isinstance(timestamp, str):
            display_time = timestamp.split("T")[0] if "T" in timestamp else timestamp
        else:
            display_time = "Unknown time"
        draw.text((10, 100), f"Time: {display_time}", fill=(0, 0, 0))
        
        # Save the thumbnail
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumbnail_path, "PNG")
    
    def _get_file_timeline_path(self, file_path: Path) -> Path:
        """Get the path to the timeline directory for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Path to the file's timeline directory
        """
        # Normalize the file path - use just the name to avoid path issues
        # This ensures consistency regardless of absolute vs relative paths
        path_str = file_path.name
        
        # Create a hash of the path to avoid issues with special characters
        path_hash = hash(path_str) % 10000
        
        return self.timeline_path / f"{path_hash:04d}" / path_str
    
    def _get_version_info(self, version_id: str) -> Dict[str, Any]:
        """Get metadata about a specific version.
        
        Args:
            version_id: ID of the version
            
        Returns:
            Dictionary containing version metadata
            
        Raises:
            ValueError: If the version does not exist
        """
        # Search for the version in the timeline directories
        for path_hash_dir in self.timeline_path.iterdir():
            if not path_hash_dir.is_dir():
                continue
            
            for file_dir in path_hash_dir.iterdir():
                if not file_dir.is_dir():
                    continue
                
                version_file = file_dir / f"{version_id}.json"
                if version_file.exists():
                    try:
                        return load_json(version_file)
                    except Exception as e:
                        raise ValueError(f"Failed to load version information: {e}")
        
        raise ValueError(f"Version {version_id} not found")
    
    def _get_object_path(self, file_hash: str) -> Path:
        """Get the path to an object file.
        
        Args:
            file_hash: The hash of the file
            
        Returns:
            Path to the object file
        """
        return self.objects_path / file_hash[:2] / file_hash[2:4] / file_hash
    
    def _update_timeline_index(self, file_path: Path, version_id: str, version_info: Dict[str, Any]) -> None:
        """Update the timeline index for a file.
        
        Args:
            file_path: Path to the file
            version_id: ID of the new version
            version_info: Metadata about the new version
        """
        file_timeline_path = self._get_file_timeline_path(file_path)
        index_path = file_timeline_path / "index.json"
        
        # Load the existing index or create a new one
        if index_path.exists():
            try:
                index = load_json(index_path)
            except Exception:
                index = {"file_path": str(file_path), "versions": []}
        else:
            index = {"file_path": str(file_path), "versions": []}
        
        # Add the new version to the index
        index["versions"].append(version_info)
        
        # Sort versions by timestamp
        index["versions"].sort(key=lambda v: v["timestamp"], reverse=True)
        
        # Save the updated index
        save_json(index, index_path)
    
    def _generate_image_thumbnail(self, image_path: Path, thumbnail_path: Path) -> None:
        """Generate a thumbnail for an image file.
        
        Args:
            image_path: Path to the image file
            thumbnail_path: Path to save the thumbnail
        """
        with Image.open(image_path) as img:
            # Convert to RGB to ensure compatibility
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Resize the image to fit the thumbnail size
            img.thumbnail(self.thumbnail_size)
            
            # Save the thumbnail
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumbnail_path, "PNG")
    
    def _generate_model_thumbnail(self, model_path: Path, thumbnail_path: Path) -> None:
        """Generate a thumbnail for a 3D model file.
        
        Args:
            model_path: Path to the 3D model file
            thumbnail_path: Path to save the thumbnail
        """
        # In a real implementation, this would render a preview of the 3D model
        # Here we'll create a simplified representation
        import trimesh
        import matplotlib.pyplot as plt
        
        try:
            model = trimesh.load(model_path)
            
            # Create a figure
            fig = plt.figure(figsize=(self.thumbnail_size[0]/100, self.thumbnail_size[1]/100), dpi=100)
            ax = fig.add_subplot(111, projection='3d')
            
            # Plot the model
            vertices = np.array(model.vertices)
            if len(vertices) > 0:
                ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2], c='blue', s=1)
            
            # Remove axes and set background to white
            ax.set_axis_off()
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            
            # Save the figure
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(thumbnail_path, bbox_inches='tight', pad_inches=0)
            plt.close(fig)
        except Exception as e:
            print(f"Error generating model thumbnail: {e}")
            # Fall back to generic thumbnail
            self._generate_generic_thumbnail(model_path, "3D Model", thumbnail_path)
    
    def _generate_generic_thumbnail(self, file_path: Path, version_id: str, thumbnail_path: Path) -> None:
        """Generate a generic thumbnail for unsupported file types.
        
        Args:
            file_path: Path to the file
            version_id: ID of the version
            thumbnail_path: Path to save the thumbnail
        """
        # Create a blank image with the file name and type
        img = Image.new('RGB', self.thumbnail_size, color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Add file name
        file_name = file_path.name
        draw.text((10, 10), file_name, fill=(0, 0, 0))
        
        # Add file type
        file_type = file_path.suffix.upper()
        draw.text((10, 40), f"Type: {file_type}", fill=(0, 0, 0))
        
        # Add version ID
        draw.text((10, 70), f"Version: {version_id[:10]}...", fill=(0, 0, 0))
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 100), f"Time: {timestamp}", fill=(0, 0, 0))
        
        # Save the thumbnail
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(thumbnail_path, "PNG")