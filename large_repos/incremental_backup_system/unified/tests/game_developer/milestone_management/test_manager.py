"""
Tests for the milestone management module.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gamevault.backup_engine.engine import BackupEngine
from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.milestone_management.manager import MilestoneManager
from gamevault.models import GameVersionType, ProjectVersion


@pytest.fixture
def mock_version_tracker():
    """Create a mock version tracker."""
    mock = MagicMock(spec=VersionTracker)
    
    # Mock versions
    versions = {
        "milestone1": ProjectVersion(
            id="milestone1",
            name="Alpha Release",
            timestamp=1000.0,
            type=GameVersionType.ALPHA,
            description="First alpha release",
            is_milestone=True,
            tags=["release", "alpha"],
            files={}
        ),
        "milestone2": ProjectVersion(
            id="milestone2",
            name="Beta Release",
            timestamp=2000.0,
            type=GameVersionType.BETA,
            description="First beta release",
            is_milestone=True,
            tags=["release", "beta"],
            parent_id="milestone1",
            files={}
        ),
        "regular": ProjectVersion(
            id="regular",
            name="Regular Version",
            timestamp=1500.0,
            type=GameVersionType.DEVELOPMENT,
            is_milestone=False,
            tags=["development"],
            files={}
        )
    }
    
    # Mock get_version method
    def get_version(version_id):
        if version_id in versions:
            return versions[version_id]
        raise FileNotFoundError(f"Version {version_id} not found")
    
    mock.get_version.side_effect = get_version
    
    # Mock get_milestones method
    mock.get_milestones.return_value = [
        versions["milestone1"],
        versions["milestone2"]
    ]
    
    # Mock get_versions_by_type method
    def get_versions_by_type(version_type):
        return [v for v in versions.values() if v.type == version_type]
    
    mock.get_versions_by_type.side_effect = get_versions_by_type
    
    # Mock get_versions_by_tag method
    def get_versions_by_tag(tag):
        return [v for v in versions.values() if tag in v.tags]
    
    mock.get_versions_by_tag.side_effect = get_versions_by_tag
    
    return mock


@pytest.fixture
def mock_backup_engine():
    """Create a mock backup engine."""
    mock = MagicMock(spec=BackupEngine)
    
    # Mock create_backup method
    def create_backup(name, version_type, description, is_milestone, tags):
        version = ProjectVersion(
            id=f"milestone_{name.lower().replace(' ', '_')}",
            name=name,
            timestamp=3000.0,  # New milestone
            type=version_type,
            description=description,
            is_milestone=is_milestone,
            tags=tags or [],
            files={}
        )
        return version
    
    mock.create_backup.side_effect = create_backup
    
    # Mock restore_version method
    def restore_version(version_id, output_path, excluded_paths=None):
        return Path(output_path)
    
    mock.restore_version.side_effect = restore_version
    
    # Mock get_version_diff method
    mock.get_version_diff.return_value = {
        "file1.txt": "added",
        "file2.txt": "modified",
        "file3.txt": "deleted",
        "file4.txt": "unchanged"
    }
    
    return mock


@pytest.fixture
def milestone_manager(mock_version_tracker, mock_backup_engine):
    """Create a MilestoneManager with mocked dependencies and a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = MilestoneManager(
            "test_project",
            mock_version_tracker,
            mock_backup_engine,
            temp_dir
        )
        yield manager


def test_create_milestone(milestone_manager, mock_backup_engine):
    """Test creating a new milestone."""
    # Create a milestone
    version = milestone_manager.create_milestone(
        name="Release Candidate",
        version_type=GameVersionType.RELEASE_CANDIDATE,
        description="First release candidate",
        annotations={"completion": "90%", "critical_bugs": 0},
        tags=["release", "candidate"],
        parent_id="milestone2"
    )
    
    # Verify backup engine was called correctly
    mock_backup_engine.create_backup.assert_called_once_with(
        name="Release Candidate",
        version_type=GameVersionType.RELEASE_CANDIDATE,
        description="First release candidate",
        is_milestone=True,
        tags=["release", "candidate"]
    )
    
    # Verify annotation file was created
    annotation_path = milestone_manager._get_milestone_path(version.id)
    assert os.path.exists(annotation_path)
    
    # Verify annotation content
    with open(annotation_path, "r") as f:
        annotation_data = json.load(f)
    
    assert annotation_data["milestone_id"] == version.id
    assert annotation_data["name"] == "Release Candidate"
    assert annotation_data["version_type"] == GameVersionType.RELEASE_CANDIDATE
    assert annotation_data["description"] == "First release candidate"
    assert annotation_data["annotations"] == {"completion": "90%", "critical_bugs": 0}
    assert annotation_data["tags"] == ["release", "candidate"]
    assert annotation_data["parent_id"] == "milestone2"


def test_create_milestone_no_backup_engine(mock_version_tracker):
    """Test creating a milestone without a backup engine."""
    # Create a milestone manager without a backup engine
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = MilestoneManager("test_project", mock_version_tracker, None, temp_dir)
        
        # Try to create a milestone without a project path
        with pytest.raises(ValueError):
            manager.create_milestone(
                name="Test Milestone",
                version_type=GameVersionType.ALPHA,
                description="Test",
                annotations={},
                tags=[]
            )
        
        # With project path, it should create a temporary backup engine
        with patch("gamevault.milestone_management.manager.BackupEngine") as mock_engine_class:
            # Mock the backup engine instance
            mock_engine_instance = MagicMock()
            mock_engine_class.return_value = mock_engine_instance
            
            # Setup the create_backup method
            mock_engine_instance.create_backup.return_value = ProjectVersion(
                id="temp_milestone",
                name="Test Milestone",
                timestamp=1000.0,
                type=GameVersionType.ALPHA,
                description="Test",
                is_milestone=True,
                tags=[],
                files={}
            )
            
            # Create a milestone with a project path
            manager.create_milestone(
                name="Test Milestone",
                version_type=GameVersionType.ALPHA,
                description="Test",
                annotations={},
                tags=[],
                project_path="/path/to/project"
            )
            
            # Verify a temporary backup engine was created
            mock_engine_class.assert_called_once_with(
                project_name="test_project",
                project_path="/path/to/project",
                storage_dir=manager.storage_dir
            )


def test_get_milestone(milestone_manager, mock_version_tracker):
    """Test getting a milestone with its annotations."""
    # Create a mock annotation file for milestone1
    annotation_path = milestone_manager._get_milestone_path("milestone1")
    annotation_data = {
        "milestone_id": "milestone1",
        "name": "Alpha Release",
        "version_type": GameVersionType.ALPHA,
        "description": "First alpha release",
        "annotations": {"completion": "70%", "critical_bugs": 2},
        "tags": ["release", "alpha"],
        "created_at": 1000.0,
        "parent_id": None
    }
    
    os.makedirs(os.path.dirname(annotation_path), exist_ok=True)
    with open(annotation_path, "w") as f:
        json.dump(annotation_data, f)
    
    # Get the milestone
    milestone = milestone_manager.get_milestone("milestone1")
    
    # Verify data from both version and annotation
    assert milestone["id"] == "milestone1"
    assert milestone["name"] == "Alpha Release"
    assert milestone["type"] == GameVersionType.ALPHA
    assert milestone["description"] == "First alpha release"
    assert milestone["annotations"] == {"completion": "70%", "critical_bugs": 2}
    assert "tags" in milestone
    assert set(milestone["tags"]) == {"release", "alpha"}


def test_get_nonexistent_milestone(milestone_manager):
    """Test getting a non-existent milestone."""
    with pytest.raises(FileNotFoundError):
        milestone_manager.get_milestone("nonexistent")


def test_update_milestone_annotations(milestone_manager):
    """Test updating annotations for a milestone."""
    # First create an annotation file
    milestone_id = "milestone1"
    annotation_path = milestone_manager._get_milestone_path(milestone_id)
    annotation_data = {
        "milestone_id": milestone_id,
        "name": "Alpha Release",
        "version_type": GameVersionType.ALPHA,
        "description": "First alpha release",
        "annotations": {"completion": "70%", "critical_bugs": 2},
        "tags": ["release", "alpha"],
        "created_at": 1000.0,
        "parent_id": None
    }
    
    os.makedirs(os.path.dirname(annotation_path), exist_ok=True)
    with open(annotation_path, "w") as f:
        json.dump(annotation_data, f)
    
    # Update annotations
    new_annotations = {
        "completion": "80%",  # Update existing
        "performance_issues": 3  # Add new
    }
    
    result = milestone_manager.update_milestone_annotations(milestone_id, new_annotations)
    assert result is True
    
    # Verify annotations were updated
    with open(annotation_path, "r") as f:
        updated_data = json.load(f)
    
    assert updated_data["annotations"]["completion"] == "80%"
    assert updated_data["annotations"]["critical_bugs"] == 2  # Unchanged
    assert updated_data["annotations"]["performance_issues"] == 3  # New


def test_update_nonexistent_milestone(milestone_manager):
    """Test updating annotations for a non-existent milestone."""
    result = milestone_manager.update_milestone_annotations("nonexistent", {})
    assert result is False


def test_list_milestones(milestone_manager, mock_version_tracker):
    """Test listing milestones with optional filtering."""
    # Create annotation files for the mock milestones
    for milestone_id in ["milestone1", "milestone2"]:
        annotation_path = milestone_manager._get_milestone_path(milestone_id)
        annotation_data = {
            "milestone_id": milestone_id,
            "name": f"Milestone {milestone_id[-1]}",
            "version_type": GameVersionType.ALPHA if milestone_id == "milestone1" else GameVersionType.BETA,
            "annotations": {"key": "value"},
            "tags": ["release", "alpha" if milestone_id == "milestone1" else "beta"],
            "created_at": 1000.0 if milestone_id == "milestone1" else 2000.0,
            "parent_id": None if milestone_id == "milestone1" else "milestone1"
        }
        
        os.makedirs(os.path.dirname(annotation_path), exist_ok=True)
        with open(annotation_path, "w") as f:
            json.dump(annotation_data, f)
    
    # List all milestones
    milestones = milestone_manager.list_milestones()
    assert len(milestones) == 2
    
    # List milestones by version type
    alpha_milestones = milestone_manager.list_milestones(version_type=GameVersionType.ALPHA)
    assert len(alpha_milestones) == 1
    assert alpha_milestones[0]["id"] == "milestone1"
    
    beta_milestones = milestone_manager.list_milestones(version_type=GameVersionType.BETA)
    assert len(beta_milestones) == 1
    assert beta_milestones[0]["id"] == "milestone2"
    
    # List milestones by tag
    release_milestones = milestone_manager.list_milestones(tag="release")
    assert len(release_milestones) == 2
    
    alpha_tag_milestones = milestone_manager.list_milestones(tag="alpha")
    assert len(alpha_tag_milestones) == 1
    assert alpha_tag_milestones[0]["id"] == "milestone1"


def test_restore_milestone(milestone_manager, mock_backup_engine):
    """Test restoring a milestone to a directory."""
    # Test restoring with string path
    result = milestone_manager.restore_milestone("milestone1", "/output/path")
    
    # Verify backup engine was called correctly
    mock_backup_engine.restore_version.assert_called_once_with(
        version_id="milestone1",
        output_path="/output/path",
        excluded_paths=None
    )
    
    # Test restoring with Path and excluded paths
    mock_backup_engine.restore_version.reset_mock()
    excluded = ["file1.txt", "dir/file2.txt"]
    result = milestone_manager.restore_milestone("milestone2", Path("/another/path"), excluded)
    
    mock_backup_engine.restore_version.assert_called_once_with(
        version_id="milestone2",
        output_path=Path("/another/path"),
        excluded_paths=excluded
    )


def test_restore_without_backup_engine(mock_version_tracker):
    """Test restoring a milestone without a backup engine."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = MilestoneManager("test_project", mock_version_tracker, None, temp_dir)
        
        with pytest.raises(ValueError):
            manager.restore_milestone("milestone1", "/output/path")


def test_compare_milestones(milestone_manager, mock_backup_engine):
    """Test comparing two milestones."""
    # Compare two milestones
    comparison = milestone_manager.compare_milestones("milestone1", "milestone2")
    
    # Verify backup engine was called correctly
    mock_backup_engine.get_version_diff.assert_called_once_with("milestone1", "milestone2")
    
    # Verify comparison structure
    assert "milestone1" in comparison
    assert "milestone2" in comparison
    assert "file_changes" in comparison
    assert "added" in comparison["file_changes"]
    assert "modified" in comparison["file_changes"]
    assert "deleted" in comparison["file_changes"]
    assert "unchanged" in comparison["file_changes"]
    assert "annotation_changes" in comparison
    assert "tag_changes" in comparison
    assert "time_between" in comparison


def test_compare_with_annotation_changes(milestone_manager, mock_backup_engine):
    """Test comparing milestones with annotation changes."""
    # Create annotation files with differences
    milestone1_path = milestone_manager._get_milestone_path("milestone1")
    milestone1_data = {
        "milestone_id": "milestone1",
        "name": "Alpha Release",
        "annotations": {"key1": "value1", "key2": "value2", "key3": "value3"},
        "tags": ["tag1", "tag2"]
    }
    
    milestone2_path = milestone_manager._get_milestone_path("milestone2")
    milestone2_data = {
        "milestone_id": "milestone2",
        "name": "Beta Release",
        "annotations": {"key1": "value1_changed", "key2": "value2", "key4": "value4"},
        "tags": ["tag1", "tag3"]
    }
    
    os.makedirs(os.path.dirname(milestone1_path), exist_ok=True)
    os.makedirs(os.path.dirname(milestone2_path), exist_ok=True)
    
    with open(milestone1_path, "w") as f:
        json.dump(milestone1_data, f)
    
    with open(milestone2_path, "w") as f:
        json.dump(milestone2_data, f)
    
    # Monkey patch the get_milestone method to use these files
    milestone_manager.get_milestone = MagicMock(side_effect=[milestone1_data, milestone2_data])
    
    # Compare the milestones
    comparison = milestone_manager.compare_milestones("milestone1", "milestone2")
    
    # Verify annotation changes
    assert "added" in comparison["annotation_changes"]
    assert "modified" in comparison["annotation_changes"]
    assert "removed" in comparison["annotation_changes"]
    
    assert "key4" in comparison["annotation_changes"]["added"]
    assert "key1" in comparison["annotation_changes"]["modified"]
    assert "key3" in comparison["annotation_changes"]["removed"]
    
    # Verify tag changes
    assert "tag3" in comparison["tag_changes"]["added"]
    assert "tag2" in comparison["tag_changes"]["removed"]
    assert "tag1" in comparison["tag_changes"]["common"]


def test_delete_milestone(milestone_manager):
    """Test deleting a milestone."""
    # Create an annotation file
    milestone_id = "milestone1"
    annotation_path = milestone_manager._get_milestone_path(milestone_id)
    annotation_data = {
        "milestone_id": milestone_id,
        "name": "Alpha Release",
        "annotations": {"key": "value"},
        "tags": ["tag"]
    }
    
    os.makedirs(os.path.dirname(annotation_path), exist_ok=True)
    with open(annotation_path, "w") as f:
        json.dump(annotation_data, f)
    
    # Delete the milestone
    result = milestone_manager.delete_milestone(milestone_id)
    assert result is True
    
    # Verify the annotation file was deleted
    assert not os.path.exists(annotation_path)
    
    # Try to delete a non-existent milestone
    result = milestone_manager.delete_milestone("nonexistent")
    assert result is False


def test_get_milestone_timeline(milestone_manager, mock_version_tracker):
    """Test getting a timeline of milestones."""
    # Create annotation files for the mock milestones
    for milestone_id in ["milestone1", "milestone2"]:
        annotation_path = milestone_manager._get_milestone_path(milestone_id)
        annotation_data = {
            "milestone_id": milestone_id,
            "name": f"Milestone {milestone_id[-1]}",
            "version_type": GameVersionType.ALPHA if milestone_id == "milestone1" else GameVersionType.BETA,
            "annotations": {},
            "tags": [],
            "created_at": 1000.0 if milestone_id == "milestone1" else 2000.0
        }
        
        os.makedirs(os.path.dirname(annotation_path), exist_ok=True)
        with open(annotation_path, "w") as f:
            json.dump(annotation_data, f)
    
    # Get the timeline
    timeline = milestone_manager.get_milestone_timeline()
    
    # Verify the timeline structure
    assert len(timeline) > 0
    
    # Check that we have entries for each version type
    alpha_entry = next((entry for entry in timeline if entry["version_type"] == GameVersionType.ALPHA), None)
    beta_entry = next((entry for entry in timeline if entry["version_type"] == GameVersionType.BETA), None)
    
    assert alpha_entry is not None
    assert beta_entry is not None
    
    # Verify the milestone counts
    assert alpha_entry["count"] == 1
    assert beta_entry["count"] == 1
    
    # Verify chronological ordering
    assert alpha_entry["first"] < beta_entry["first"]