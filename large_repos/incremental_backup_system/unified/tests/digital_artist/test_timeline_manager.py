"""
Tests for the creative timeline manager component.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from PIL import Image, ImageDraw

from creative_vault.timeline.timeline_manager import CreativeTimelineManager
from creative_vault.backup_engine.incremental_backup import DeltaBackupEngine
from creative_vault.utils import BackupConfig


def _create_modified_image(orig_image_path, output_path):
    """Create a modified version of an image for testing."""
    # Read the original image
    img = Image.open(orig_image_path)
    
    # Draw something on it to modify it
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (150, 150)], fill=(255, 0, 0))
    
    # Save the modified image
    img.save(output_path)
    
    return output_path


class TestTimelineManager:
    """Test cases for the timeline manager."""
    
    def test_register_version(self, backup_engine, timeline_manager, test_project_dir, test_image):
        """Test registering a version of a file in the timeline."""
        # First ensure the test image is in the test project directory
        target_path = test_project_dir / "test_image.png"
        shutil.copy(test_image, target_path)
        
        # Create a snapshot that includes the image
        snapshot_id = backup_engine.create_snapshot(test_project_dir)
        
        # Register a version
        version_id = timeline_manager.register_version(target_path, snapshot_id)
        
        # Check that the version was registered
        assert version_id is not None
        assert version_id.startswith("ver-")
        
        # Check that the version metadata was created
        timeline_path = timeline_manager._get_file_timeline_path(target_path)
        assert timeline_path.exists()
        assert (timeline_path / f"{version_id}.json").exists()
        assert (timeline_path / "index.json").exists()
    
    def test_get_file_timeline(self, backup_engine, timeline_manager, test_project_dir, test_image):
        """Test getting the timeline of versions for a file."""
        # Copy the test image to the test project directory
        target_path = test_project_dir / "test_image.png"
        shutil.copy(test_image, target_path)
        
        # Create a snapshot
        snapshot_id = backup_engine.create_snapshot(test_project_dir)
        
        # Register a version
        version_id = timeline_manager.register_version(target_path, snapshot_id)
        
        # Get the file timeline
        timeline = timeline_manager.get_file_timeline(target_path)
        
        # Check the timeline
        assert timeline is not None
        assert len(timeline) >= 1
        
        # Check the version in the timeline
        version = next((v for v in timeline if v["id"] == version_id), None)
        assert version is not None
        assert version["snapshot_id"] == snapshot_id
        assert "timestamp" in version
        assert "file_path" in version
        assert "file_hash" in version
        assert "file_size" in version
        assert "content_type" in version
    
    def test_generate_thumbnail(self, backup_engine, timeline_manager, test_project_dir, test_image):
        """Test generating a thumbnail preview for a version."""
        # Copy the test image to the test project directory
        target_path = test_project_dir / "test_image.png"
        shutil.copy(test_image, target_path)
        
        # Create a snapshot
        snapshot_id = backup_engine.create_snapshot(test_project_dir)
        
        # Register a version
        version_id = timeline_manager.register_version(target_path, snapshot_id)
        
        # Generate a thumbnail
        thumbnail_path = timeline_manager.generate_thumbnail(version_id)
        
        # Check that the thumbnail was created
        assert thumbnail_path.exists()
        
        # Check that the thumbnail is a valid image
        try:
            thumbnail_img = Image.open(thumbnail_path)
            assert thumbnail_img.width <= timeline_manager.thumbnail_size[0]
            assert thumbnail_img.height <= timeline_manager.thumbnail_size[1]
        except Exception as e:
            pytest.fail(f"Failed to open thumbnail: {e}")
    
    def test_compare_versions(self, backup_engine, timeline_manager, test_project_dir, 
                             test_image, test_image_modified):
        """Test comparing two versions of a file."""
        # Copy the test image to the test project directory
        target_path = test_project_dir / "test_image.png"
        shutil.copy(test_image, target_path)
        
        # Create an initial snapshot
        snapshot_id_1 = backup_engine.create_snapshot(test_project_dir)
        
        # Register the first version
        version_id_1 = timeline_manager.register_version(target_path, snapshot_id_1)
        
        # Use the pre-modified test image instead of modifying at runtime
        shutil.copy(test_image_modified, target_path)
        
        # Create a second snapshot
        snapshot_id_2 = backup_engine.create_snapshot(test_project_dir)
        
        # Register the second version
        version_id_2 = timeline_manager.register_version(target_path, snapshot_id_2)
        
        # Compare the versions
        comparison = timeline_manager.compare_versions(version_id_1, version_id_2)
        
        # Check the comparison result
        assert comparison is not None
        assert "version_1" in comparison
        assert "version_2" in comparison
        assert "diff_path" in comparison
        assert "diff_stats" in comparison
        
        # Check version information
        assert comparison["version_1"]["id"] == version_id_1
        assert comparison["version_2"]["id"] == version_id_2
        
        # Check that the diff image was created
        diff_path = Path(comparison["diff_path"])
        assert diff_path.exists()
    
    def test_timeline_filtering_by_time_range(self, backup_engine, timeline_manager, 
                                             test_project_dir, test_image):
        """Test filtering the timeline by time range."""
        # Copy the test image to the test project directory
        target_path = test_project_dir / "test_image.png"
        shutil.copy(test_image, target_path)
        
        # Create an initial snapshot
        snapshot_id_1 = backup_engine.create_snapshot(test_project_dir)
        
        # Register the first version
        version_id_1 = timeline_manager.register_version(target_path, snapshot_id_1)
        
        # Get the first version timestamp
        timeline = timeline_manager.get_file_timeline(target_path)
        version = next((v for v in timeline if v["id"] == version_id_1), None)
        assert version is not None
        first_timestamp = datetime.fromisoformat(version["timestamp"])
        
        # Create a time range that includes the first version
        start_time = first_timestamp - timedelta(minutes=5)
        end_time = first_timestamp + timedelta(minutes=5)
        
        # Get the timeline filtered by time range
        filtered_timeline = timeline_manager.get_file_timeline(target_path, start_time, end_time)
        
        # Check that the filtered timeline includes the first version
        assert len(filtered_timeline) >= 1
        assert any(v["id"] == version_id_1 for v in filtered_timeline)
        
        # Create a time range that excludes the first version
        start_time = first_timestamp + timedelta(minutes=10)
        end_time = first_timestamp + timedelta(minutes=20)
        
        # Get the timeline filtered by the exclusionary time range
        filtered_timeline = timeline_manager.get_file_timeline(target_path, start_time, end_time)
        
        # Check that the filtered timeline is empty
        assert len(filtered_timeline) == 0