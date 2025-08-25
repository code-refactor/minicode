"""
Tests for the version tracker module of the backup engine.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict

import pytest

from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.models import FileInfo, GameVersionType


@pytest.fixture
def version_tracker():
    """Create a VersionTracker with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield VersionTracker("test_project", temp_dir)


@pytest.fixture
def sample_files():
    """Create sample file info for testing."""
    return {
        "file1.txt": FileInfo(
            path="file1.txt",
            size=100,
            hash="hash1",
            modified_time=1000.0,
            is_binary=False,
            storage_path="/path/to/file1.txt"
        ),
        "file2.bin": FileInfo(
            path="file2.bin",
            size=200,
            hash="hash2",
            modified_time=1001.0,
            is_binary=True,
            chunks=["chunk1", "chunk2"]
        ),
        "file3.png": FileInfo(
            path="file3.png",
            size=300,
            hash="hash3",
            modified_time=1002.0,
            is_binary=True,
            chunks=["chunk3", "chunk4"]
        )
    }


def test_create_version(version_tracker, sample_files):
    """Test creating a new version."""
    # Create a version
    version = version_tracker.create_version(
        name="test version",
        files=sample_files,
        version_type=GameVersionType.DEVELOPMENT,
        description="Test version",
        is_milestone=False,
        tags=["test", "initial"]
    )
    
    # Verify the version was created
    assert version.name == "test version"
    assert version.type == GameVersionType.DEVELOPMENT
    assert version.description == "Test version"
    assert version.is_milestone is False
    assert set(version.tags) == {"test", "initial"}
    assert version.parent_id is None
    assert len(version.files) == 3
    
    # Verify the version is stored in metadata
    versions = version_tracker.list_versions()
    assert len(versions) == 1
    assert versions[0]["id"] == version.id
    assert versions[0]["name"] == "test version"
    
    # Verify this is now the latest version
    latest = version_tracker.get_latest_version()
    assert latest is not None
    assert latest.id == version.id


def test_create_version_with_parent(version_tracker, sample_files):
    """Test creating a version with a parent."""
    # Create a first version
    version1 = version_tracker.create_version(
        name="version 1",
        files=sample_files,
        version_type=GameVersionType.DEVELOPMENT
    )
    
    # Create a second version with the first as parent
    version2 = version_tracker.create_version(
        name="version 2",
        files=sample_files,
        version_type=GameVersionType.DEVELOPMENT,
        parent_id=version1.id
    )
    
    # Verify parent relationship
    assert version2.parent_id == version1.id
    
    # Verify version history
    history = version_tracker.get_version_history(version2.id)
    assert len(history) == 2
    assert history[0].id == version1.id
    assert history[1].id == version2.id


def test_get_version(version_tracker, sample_files):
    """Test getting a specific version."""
    # Create a version
    version = version_tracker.create_version(
        name="test version",
        files=sample_files
    )
    
    # Get the version by ID
    retrieved = version_tracker.get_version(version.id)
    
    # Verify it's the same version
    assert retrieved.id == version.id
    assert retrieved.name == version.name
    assert retrieved.files == version.files


def test_list_versions(version_tracker, sample_files):
    """Test listing all versions."""
    # Create multiple versions
    v1 = version_tracker.create_version(name="v1", files=sample_files)
    v2 = version_tracker.create_version(name="v2", files=sample_files)
    v3 = version_tracker.create_version(name="v3", files=sample_files)
    
    # List all versions
    versions = version_tracker.list_versions()
    
    # Verify all versions are listed
    assert len(versions) == 3
    assert {v["id"] for v in versions} == {v1.id, v2.id, v3.id}


def test_get_version_history(version_tracker, sample_files):
    """Test getting the history of a version."""
    # Create a chain of versions
    v1 = version_tracker.create_version(name="v1", files=sample_files)
    v2 = version_tracker.create_version(name="v2", files=sample_files, parent_id=v1.id)
    v3 = version_tracker.create_version(name="v3", files=sample_files, parent_id=v2.id)
    
    # Get the history of v3
    history = version_tracker.get_version_history(v3.id)
    
    # Verify the history is correct
    assert len(history) == 3
    assert history[0].id == v1.id
    assert history[1].id == v2.id
    assert history[2].id == v3.id


def test_get_milestones(version_tracker, sample_files):
    """Test getting milestone versions."""
    # Create some regular versions
    version_tracker.create_version(name="v1", files=sample_files)
    version_tracker.create_version(name="v2", files=sample_files)
    
    # Create milestone versions
    m1 = version_tracker.create_version(name="milestone 1", files=sample_files, is_milestone=True)
    m2 = version_tracker.create_version(name="milestone 2", files=sample_files, is_milestone=True)
    
    # Get milestones
    milestones = version_tracker.get_milestones()
    
    # Verify only milestone versions are returned
    assert len(milestones) == 2
    assert {m.id for m in milestones} == {m1.id, m2.id}


def test_get_versions_by_tag(version_tracker, sample_files):
    """Test getting versions with a specific tag."""
    # Create versions with different tags
    v1 = version_tracker.create_version(name="v1", files=sample_files, tags=["alpha", "test"])
    v2 = version_tracker.create_version(name="v2", files=sample_files, tags=["beta", "test"])
    v3 = version_tracker.create_version(name="v3", files=sample_files, tags=["alpha", "release"])
    
    # Get versions with the "alpha" tag
    alpha_versions = version_tracker.get_versions_by_tag("alpha")
    assert len(alpha_versions) == 2
    assert {v.id for v in alpha_versions} == {v1.id, v3.id}
    
    # Get versions with the "test" tag
    test_versions = version_tracker.get_versions_by_tag("test")
    assert len(test_versions) == 2
    assert {v.id for v in test_versions} == {v1.id, v2.id}
    
    # Get versions with the "release" tag
    release_versions = version_tracker.get_versions_by_tag("release")
    assert len(release_versions) == 1
    assert release_versions[0].id == v3.id


def test_get_versions_by_type(version_tracker, sample_files):
    """Test getting versions of a specific type."""
    # Create versions of different types
    v1 = version_tracker.create_version(
        name="v1", 
        files=sample_files, 
        version_type=GameVersionType.DEVELOPMENT
    )
    v2 = version_tracker.create_version(
        name="v2", 
        files=sample_files, 
        version_type=GameVersionType.ALPHA
    )
    v3 = version_tracker.create_version(
        name="v3", 
        files=sample_files, 
        version_type=GameVersionType.BETA
    )
    v4 = version_tracker.create_version(
        name="v4", 
        files=sample_files, 
        version_type=GameVersionType.ALPHA
    )
    
    # Get alpha versions
    alpha_versions = version_tracker.get_versions_by_type(GameVersionType.ALPHA)
    assert len(alpha_versions) == 2
    assert {v.id for v in alpha_versions} == {v2.id, v4.id}
    
    # Get beta versions
    beta_versions = version_tracker.get_versions_by_type(GameVersionType.BETA)
    assert len(beta_versions) == 1
    assert beta_versions[0].id == v3.id


def test_delete_version(version_tracker, sample_files):
    """Test deleting a version."""
    # Create versions
    v1 = version_tracker.create_version(name="v1", files=sample_files)
    v2 = version_tracker.create_version(name="v2", files=sample_files)
    
    # Verify both versions exist
    versions = version_tracker.list_versions()
    assert len(versions) == 2
    
    # Delete a version
    result = version_tracker.delete_version(v1.id)
    assert result is True
    
    # Verify the version was deleted
    versions = version_tracker.list_versions()
    assert len(versions) == 1
    assert versions[0]["id"] == v2.id
    
    # Try to get the deleted version
    with pytest.raises(FileNotFoundError):
        version_tracker.get_version(v1.id)
    
    # Try to delete a non-existent version
    result = version_tracker.delete_version("nonexistent")
    assert result is False


def test_version_not_found(version_tracker):
    """Test behavior when attempting to get a non-existent version."""
    with pytest.raises(FileNotFoundError):
        version_tracker.get_version("nonexistent")