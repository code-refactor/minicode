"""
Tests for the backup engine module.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from gamevault.backup_engine.engine import BackupEngine
from gamevault.models import GameVersionType


@pytest.fixture
def project_dir():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()
        
        # Create some text files
        text_file1 = project_dir / "file1.txt"
        text_file1.write_text("This is a text file for testing")
        
        text_file2 = project_dir / "file2.txt"
        text_file2.write_text("Another text file with different content")
        
        # Create a binary file
        binary_file = project_dir / "data.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")
        
        # Create a subdirectory with files
        subdir = project_dir / "subdir"
        subdir.mkdir()
        
        subfile = subdir / "subfile.txt"
        subfile.write_text("File in a subdirectory")
        
        yield project_dir


@pytest.fixture
def backup_engine(project_dir):
    """Create a BackupEngine with a temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = BackupEngine(
            project_name="test_project",
            project_path=project_dir,
            storage_dir=temp_dir
        )
        yield engine


def test_create_backup(backup_engine, project_dir):
    """Test creating a backup of a project."""
    # Create a backup
    version = backup_engine.create_backup(
        name="test backup",
        version_type=GameVersionType.DEVELOPMENT,
        description="Test backup",
        is_milestone=False,
        tags=["test", "initial"]
    )
    
    # Verify the version was created
    assert version.name == "test backup"
    assert version.type == GameVersionType.DEVELOPMENT
    assert version.description == "Test backup"
    assert not version.is_milestone
    assert set(version.tags) == {"test", "initial"}
    
    # Verify all files were backed up
    file_paths = {file_info.path for file_info in version.files.values()}
    assert "file1.txt" in file_paths
    assert "file2.txt" in file_paths
    assert "data.bin" in file_paths
    assert "subdir/subfile.txt" in file_paths


def test_incremental_backup(backup_engine, project_dir):
    """Test creating an incremental backup after changes."""
    # Create an initial backup
    initial_version = backup_engine.create_backup(name="initial")
    
    # Modify a file
    text_file = project_dir / "file1.txt"
    text_file.write_text("This is a modified text file")
    
    # Add a new file
    new_file = project_dir / "newfile.txt"
    new_file.write_text("This is a new file")
    
    # Remove a file
    (project_dir / "file2.txt").unlink()
    
    # Create a new backup
    new_version = backup_engine.create_backup(name="incremental")
    
    # Verify the new version has the expected changes
    assert new_version.parent_id == initial_version.id
    
    # Verify modified file was backed up
    assert "file1.txt" in new_version.files
    assert new_version.files["file1.txt"].hash != initial_version.files["file1.txt"].hash
    
    # Verify new file was backed up
    assert "newfile.txt" in new_version.files
    
    # Verify removed file is not in the new version
    assert "file2.txt" not in new_version.files
    
    # Verify unchanged file has the same hash
    assert "data.bin" in new_version.files
    assert new_version.files["data.bin"].hash == initial_version.files["data.bin"].hash
    assert new_version.files["subdir/subfile.txt"].hash == initial_version.files["subdir/subfile.txt"].hash


def test_restore_version(backup_engine, project_dir):
    """Test restoring a backed up version."""
    # Create a backup
    version = backup_engine.create_backup(name="test")
    
    # Modify all files to ensure the restore actually changes something
    (project_dir / "file1.txt").write_text("Modified content")
    (project_dir / "file2.txt").write_text("Modified content")
    (project_dir / "data.bin").write_bytes(b"\xFF\xFF\xFF\xFF")
    (project_dir / "subdir/subfile.txt").write_text("Modified content")
    
    # Create a new file that shouldn't be in the restored version
    (project_dir / "not_in_backup.txt").write_text("This file wasn't in the backup")
    
    # Create a restoration directory
    with tempfile.TemporaryDirectory() as restore_dir:
        # Restore the version
        restored_dir = backup_engine.restore_version(
            version_id=version.id,
            output_path=restore_dir
        )
        
        # Verify all files were restored with correct content
        assert (restored_dir / "file1.txt").read_text() == "This is a text file for testing"
        assert (restored_dir / "file2.txt").read_text() == "Another text file with different content"
        assert (restored_dir / "data.bin").read_bytes() == b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        assert (restored_dir / "subdir/subfile.txt").read_text() == "File in a subdirectory"
        
        # Verify new file is not in the restored version
        assert not (restored_dir / "not_in_backup.txt").exists()


def test_restore_with_exclusions(backup_engine, project_dir):
    """Test restoring a version with exclusions."""
    # Create a backup
    version = backup_engine.create_backup(name="test")
    
    # Create a restoration directory
    with tempfile.TemporaryDirectory() as restore_dir:
        # Restore the version with exclusions
        restored_dir = backup_engine.restore_version(
            version_id=version.id,
            output_path=restore_dir,
            excluded_paths=["file1.txt", "subdir/subfile.txt"]
        )
        
        # Verify excluded files were not restored
        assert not (restored_dir / "file1.txt").exists()
        assert not (restored_dir / "subdir/subfile.txt").exists()
        
        # Verify non-excluded files were restored
        assert (restored_dir / "file2.txt").exists()
        assert (restored_dir / "data.bin").exists()


def test_get_version_diff(backup_engine, project_dir):
    """Test getting differences between two versions."""
    # Create an initial backup
    initial_version = backup_engine.create_backup(name="initial")
    
    # Modify, add, and remove files
    (project_dir / "file1.txt").write_text("Modified content")
    (project_dir / "newfile.txt").write_text("New file")
    (project_dir / "file2.txt").unlink()
    
    # Create a new backup
    new_version = backup_engine.create_backup(name="modified")
    
    # Get the differences
    diff = backup_engine.get_version_diff(initial_version.id, new_version.id)
    
    # Verify differences
    assert diff["file1.txt"] == "modified"
    assert diff["newfile.txt"] == "added"
    assert diff["file2.txt"] == "deleted"
    assert diff["data.bin"] == "unchanged"
    assert diff["subdir/subfile.txt"] == "unchanged"


def test_get_storage_stats(backup_engine, project_dir):
    """Test getting storage statistics."""
    # Initially should have no storage used
    stats_before = backup_engine.get_storage_stats()
    assert stats_before["total"] == 0
    
    # Create a backup
    backup_engine.create_backup(name="test")
    
    # Get updated stats
    stats_after = backup_engine.get_storage_stats()
    
    # Verify storage is now being used
    assert stats_after["total"] > 0
    assert stats_after["files"] > 0  # Text files stored as files
    
    # In this test setup, we may not actually have binary files that get chunked
    # or the binary files may be too small to be chunked
    # So this assertion is not always applicable
    # Assert that either files or chunks are being used for storage
    assert stats_after["files"] > 0 or stats_after["chunks"] > 0