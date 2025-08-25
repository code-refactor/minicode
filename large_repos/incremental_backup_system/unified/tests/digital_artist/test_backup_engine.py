"""
Tests for the incremental backup engine component.
"""

import os
import shutil
from pathlib import Path

import pytest

from creative_vault.backup_engine.incremental_backup import DeltaBackupEngine
from creative_vault.utils import BackupConfig


def test_initialize_repository(temp_dir):
    """Test initializing a new backup repository."""
    # Create a backup engine
    repo_path = temp_dir / "test_repo"
    config = BackupConfig(repository_path=repo_path)
    engine = DeltaBackupEngine(config)
    
    # Initialize the repository
    result = engine.initialize_repository(repo_path)
    
    # Check the result
    assert result is True
    
    # Check that the repository directories were created
    assert repo_path.exists()
    assert (repo_path / "snapshots").exists()
    assert (repo_path / "objects").exists()
    assert (repo_path / "metadata").exists()
    assert (repo_path / "repository.json").exists()


def test_create_snapshot(backup_engine, test_project_dir):
    """Test creating a snapshot of a project directory."""
    # Create a snapshot
    snapshot_id = backup_engine.create_snapshot(test_project_dir)
    
    # Check that the snapshot was created
    assert snapshot_id is not None
    assert snapshot_id.startswith("snapshot-")
    
    # Check that the snapshot directory was created
    snapshots_path = backup_engine._snapshots_path
    assert (snapshots_path / snapshot_id).exists()
    assert (snapshots_path / snapshot_id / "info.json").exists()
    assert (snapshots_path / snapshot_id / "files.json").exists()
    assert (snapshots_path / snapshot_id / "manifest.json").exists()


def test_restore_snapshot(backup_engine, test_project_dir, temp_dir):
    """Test restoring a snapshot to a directory."""
    # Create a snapshot
    snapshot_id = backup_engine.create_snapshot(test_project_dir)
    
    # Create a target directory for restoration
    target_dir = temp_dir / "restored_project"
    
    # Restore the snapshot
    result = backup_engine.restore_snapshot(snapshot_id, target_dir)
    
    # Check the result
    assert result is True
    
    # Check that the files were restored
    assert target_dir.exists()
    assert (target_dir / "images").exists()
    assert (target_dir / "models").exists()
    assert (target_dir / "textures").exists()
    assert (target_dir / "images" / "image1.png").exists()
    assert (target_dir / "images" / "image2.png").exists()
    assert (target_dir / "textures" / "texture1.png").exists()
    assert (target_dir / "models" / "model1.obj").exists()
    assert (target_dir / "project.txt").exists()


def test_get_snapshot_info(backup_engine, test_project_dir):
    """Test getting information about a snapshot."""
    # Create a snapshot
    snapshot_id = backup_engine.create_snapshot(test_project_dir)
    
    # Get the snapshot info
    snapshot_info = backup_engine.get_snapshot_info(snapshot_id)
    
    # Check the snapshot info
    assert snapshot_info is not None
    assert snapshot_info["id"] == snapshot_id
    assert "timestamp" in snapshot_info
    assert "source_path" in snapshot_info
    assert "files_count" in snapshot_info
    assert "total_size" in snapshot_info
    assert "new_files" in snapshot_info
    assert "modified_files" in snapshot_info
    assert "deleted_files" in snapshot_info


def test_list_snapshots(backup_engine, test_project_dir):
    """Test listing all snapshots."""
    # Create a snapshot
    snapshot_id = backup_engine.create_snapshot(test_project_dir)
    
    # List the snapshots
    snapshots = backup_engine.list_snapshots()
    
    # Check the result
    assert snapshots is not None
    assert len(snapshots) >= 1
    
    # Check the first snapshot
    first_snapshot = snapshots[0]
    assert first_snapshot["id"] == snapshot_id


def test_incremental_backup(backup_engine, test_project_dir):
    """Test incremental backup with modified files."""
    # Create an initial snapshot
    snapshot_id_1 = backup_engine.create_snapshot(test_project_dir)
    
    # Modify a file in the project
    with open(test_project_dir / "project.txt", "a") as f:
        f.write("This is a new line added to test incremental backup.\n")
    
    # Create a new file
    with open(test_project_dir / "new_file.txt", "w") as f:
        f.write("This is a new file added to test incremental backup.\n")
    
    # Create a second snapshot
    snapshot_id_2 = backup_engine.create_snapshot(test_project_dir)
    
    # Get info about the second snapshot
    snapshot_info = backup_engine.get_snapshot_info(snapshot_id_2)
    
    # Check that only the modified and new files are included
    assert len(snapshot_info["new_files"]) == 1  # The new file
    assert len(snapshot_info["modified_files"]) == 1  # The modified file
    
    # Restore the second snapshot to a new directory
    target_dir = backup_engine._repository_path.parent / "restored_incremental"
    result = backup_engine.restore_snapshot(snapshot_id_2, target_dir)
    
    # Check that the files were restored correctly
    assert result is True
    assert (target_dir / "project.txt").exists()
    assert (target_dir / "new_file.txt").exists()
    
    # Check the content of the modified file
    with open(target_dir / "project.txt", "r") as f:
        content = f.read()
        assert "This is a new line added to test incremental backup." in content