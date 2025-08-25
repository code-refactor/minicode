"""
Integration tests for the CreativeVault backup system.
"""

import os
import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from creative_vault.__main__ import CreativeVault


def test_full_backup_restore_workflow(temp_dir, test_project_dir):
    """Test the complete backup and restore workflow."""
    # Initialize CreativeVault
    vault = CreativeVault(repository_path=temp_dir / "repo")
    
    # Create a backup of the test project
    backup_result = vault.backup_project(test_project_dir)
    
    # Check the backup result
    assert "snapshot_id" in backup_result
    snapshot_id = backup_result["snapshot_id"]
    
    # Create a target directory for restoration
    restore_dir = temp_dir / "restored_project"
    
    # Restore the backup
    restore_result = vault.restore_project(snapshot_id, restore_dir)
    
    # Check the restore result
    assert restore_result["success"] is True
    
    # Check that all project files were restored
    assert (restore_dir / "images").exists()
    assert (restore_dir / "models").exists()
    assert (restore_dir / "textures").exists()
    assert (restore_dir / "images" / "image1.png").exists()
    assert (restore_dir / "images" / "image2.png").exists()
    assert (restore_dir / "textures" / "texture1.png").exists()
    assert (restore_dir / "models" / "model1.obj").exists()
    assert (restore_dir / "project.txt").exists()


def test_version_comparison_workflow(temp_dir, test_project_dir, test_image, test_image_modified):
    """Test the version comparison workflow."""
    # Initialize CreativeVault
    vault = CreativeVault(repository_path=temp_dir / "repo")
    
    # Create an image to track in the project directory
    image_path = test_project_dir / "images" / "test_comparison.png"
    shutil.copy(test_image, image_path)
    
    # Create an initial backup
    backup_result = vault.backup_project(test_project_dir)
    snapshot_id_1 = backup_result["snapshot_id"]
    
    # Initialize the timeline for an image file
    version_id_1 = vault.timeline_manager.register_version(image_path, snapshot_id_1)
    
    # Replace with the modified image instead of modifying at runtime
    shutil.copy(test_image_modified, image_path)
    
    # Create a second backup
    backup_result = vault.backup_project(test_project_dir)
    snapshot_id_2 = backup_result["snapshot_id"]
    
    # Register the second version
    version_id_2 = vault.timeline_manager.register_version(image_path, snapshot_id_2)
    
    # Compare the versions
    comparison = vault.compare_versions(version_id_1, version_id_2)
    
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


def test_element_extraction_workflow(temp_dir, test_project_dir):
    """Test the element extraction workflow."""
    # Initialize CreativeVault
    vault = CreativeVault(repository_path=temp_dir / "repo")
    
    # Get an image file to work with
    image_path = test_project_dir / "images" / "image1.png"
    
    # List extractable elements
    elements = vault.element_extractor.list_elements(image_path)
    assert len(elements) > 0
    
    # Find the whole image element
    whole_image = next((e for e in elements if e["id"] == "whole_image"), None)
    assert whole_image is not None
    
    # Extract the whole image
    output_path = temp_dir / "extracted_whole_image.png"
    extract_result = vault.extract_element(image_path, whole_image["id"], output_path)
    
    # Check the result
    assert extract_result == output_path
    assert output_path.exists()
    
    # Check that the extracted image is valid
    extracted_img = Image.open(output_path)
    original_img = Image.open(image_path)
    assert extracted_img.size == original_img.size


def test_asset_deduplication_workflow(temp_dir):
    """Test the asset deduplication workflow."""
    # Create a test project with duplicate assets
    project_dir = temp_dir / "dedup_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (project_dir / "images").mkdir()
    (project_dir / "duplicates").mkdir()
    
    # Create an original image
    original_img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    original_path = project_dir / "images" / "original.png"
    original_img.save(original_path)
    
    # Create duplicate images
    for i in range(1, 4):
        dup_path = project_dir / "duplicates" / f"duplicate_{i}.png"
        original_img.save(dup_path)
    
    # Create a project file that references the images
    with open(project_dir / "project.txt", "w") as f:
        f.write("This project references:\n")
        f.write("images/original.png\n")
        for i in range(1, 4):
            f.write(f"duplicates/duplicate_{i}.png\n")
    
    # Initialize CreativeVault
    vault = CreativeVault(repository_path=temp_dir / "repo")
    
    # Backup the project
    vault.backup_project(project_dir)
    
    # Deduplicate assets
    dedup_result = vault.deduplicate_assets(project_dir)
    
    # Check the deduplication result
    assert dedup_result is not None
    assert "duplicate_groups" in dedup_result
    assert "space_saved" in dedup_result
    assert "files_deduplicated" in dedup_result
    
    # There should be at least one group of duplicates
    assert len(dedup_result["duplicate_groups"]) > 0
    assert dedup_result["files_deduplicated"] > 0


def test_multi_snapshot_timeline(temp_dir, test_project_dir):
    """Test creating multiple snapshots and tracking a file's timeline."""
    # Initialize CreativeVault
    vault = CreativeVault(repository_path=temp_dir / "repo")
    
    # Create a test image to track
    target_image = test_project_dir / "test_tracked_image.png"
    
    # Create the initial image
    img = Image.new('RGB', (200, 200), color=(0, 0, 255))
    img.save(target_image)
    
    # Create the first backup
    backup_result_1 = vault.backup_project(test_project_dir)
    snapshot_id_1 = backup_result_1["snapshot_id"]
    
    # Register the first version of a file
    version_id_1 = vault.timeline_manager.register_version(target_image, snapshot_id_1)
    
    # Create the first modified version
    img = Image.new('RGB', (200, 200), color=(0, 0, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (50, 50)], fill=(255, 0, 0))
    img.save(target_image)
    
    # Create a second backup
    backup_result_2 = vault.backup_project(test_project_dir)
    snapshot_id_2 = backup_result_2["snapshot_id"]
    
    # Register the second version
    version_id_2 = vault.timeline_manager.register_version(target_image, snapshot_id_2)
    
    # Create the second modified version
    img = Image.new('RGB', (200, 200), color=(0, 0, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (50, 50)], fill=(255, 0, 0))
    draw.rectangle([(60, 60), (100, 100)], fill=(0, 255, 0))
    img.save(target_image)
    
    # Create a third backup
    backup_result_3 = vault.backup_project(test_project_dir)
    snapshot_id_3 = backup_result_3["snapshot_id"]
    
    # Register the third version
    version_id_3 = vault.timeline_manager.register_version(target_image, snapshot_id_3)
    
    # Get the file's timeline
    timeline = vault.timeline_manager.get_file_timeline(target_image)
    
    # Check the timeline
    assert timeline is not None
    assert len(timeline) >= 3
    
    # Find versions in the timeline
    versions = {v["id"]: i for i, v in enumerate(timeline)}
    
    # Check that all versions exist
    assert version_id_1 in versions
    assert version_id_2 in versions
    assert version_id_3 in versions
    
    # The timeline should be ordered with newer versions first (or at least contain all versions)
    assert versions[version_id_3] < versions[version_id_1]
    assert versions[version_id_2] < versions[version_id_1]