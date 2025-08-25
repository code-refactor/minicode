"""
Test configuration and fixtures for the CreativeVault backup system.
"""

import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont
import trimesh

from creative_vault.backup_engine.incremental_backup import DeltaBackupEngine
from creative_vault.visual_diff.diff_generator import CreativeVisualDiffGenerator
from creative_vault.timeline.timeline_manager import CreativeTimelineManager
from creative_vault.element_extraction.extractor import CreativeElementExtractor
from creative_vault.asset_tracker.reference_tracker import CreativeAssetReferenceTracker
from creative_vault.workspace_capture.environment_capture import CreativeEnvironmentCapture
from creative_vault.utils import BackupConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Return the directory path
    yield Path(temp_dir)
    
    # Clean up after the test
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_data_dir():
    """Path to the test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def test_image(test_data_dir):
    """Create a test image for testing."""
    # Create the test data directory if it doesn't exist
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test image
    image_path = test_data_dir / "test_image.png"
    if not image_path.exists():
        # Create a simple test image
        img = Image.new('RGB', (500, 300), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.rectangle([(50, 50), (450, 250)], fill=(128, 0, 0))
        d.text((100, 100), "Test Image", fill=(255, 255, 0))
        
        # Save the image
        img.save(image_path)
    
    return image_path


@pytest.fixture
def test_image_modified(test_data_dir):
    """Create a modified test image for testing."""
    # Create the test data directory if it doesn't exist
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a modified test image
    image_path = test_data_dir / "test_image_modified.png"
    if not image_path.exists():
        # Create a simple test image with modifications
        img = Image.new('RGB', (500, 300), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.rectangle([(50, 50), (450, 250)], fill=(0, 128, 0))  # Changed color
        d.text((100, 100), "Modified Image", fill=(255, 255, 0))  # Changed text
        
        # Save the image
        img.save(image_path)
    
    return image_path


@pytest.fixture
def test_model(test_data_dir):
    """Create a test 3D model for testing."""
    # Create the test data directory if it doesn't exist
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test model (a simple box)
    model_path = test_data_dir / "test_model.obj"
    if not model_path.exists():
        # Create a simple cube mesh
        mesh = trimesh.creation.box()
        
        # Save the mesh as an OBJ file
        mesh.export(model_path)
    
    return model_path


@pytest.fixture
def test_model_modified(test_data_dir):
    """Create a modified test 3D model for testing."""
    # Create the test data directory if it doesn't exist
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a modified test model (a box with one vertex moved)
    model_path = test_data_dir / "test_model_modified.obj"
    if not model_path.exists():
        # Create a cube mesh
        mesh = trimesh.creation.box()
        
        # Modify one vertex to create a difference
        if len(mesh.vertices) > 0:
            mesh.vertices[0] = mesh.vertices[0] + [0.5, 0.5, 0.5]
        
        # Save the modified mesh
        mesh.export(model_path)
    
    return model_path


@pytest.fixture
def test_project_dir(temp_dir, test_image, test_model):
    """Create a test project directory with files for testing."""
    # Create project directory
    project_dir = temp_dir / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (project_dir / "images").mkdir()
    (project_dir / "models").mkdir()
    (project_dir / "textures").mkdir()
    
    # Copy the test image
    shutil.copy(test_image, project_dir / "images" / "image1.png")
    
    # Create additional test images
    img1 = Image.new('RGB', (200, 200), color=(255, 0, 0))
    img1.save(project_dir / "images" / "image2.png")
    
    img2 = Image.new('RGB', (200, 200), color=(0, 255, 0))
    img2.save(project_dir / "textures" / "texture1.png")
    
    # Copy the test model
    shutil.copy(test_model, project_dir / "models" / "model1.obj")
    
    # Create a mock project file
    with open(project_dir / "project.txt", "w") as f:
        f.write("This is a mock project file.\n")
        f.write("It references the following files:\n")
        f.write("images/image1.png\n")
        f.write("textures/texture1.png\n")
        f.write("models/model1.obj\n")
    
    return project_dir


@pytest.fixture
def backup_engine(temp_dir):
    """Create a backup engine instance for testing."""
    repo_path = temp_dir / "repo"
    config = BackupConfig(repository_path=repo_path)
    engine = DeltaBackupEngine(config)
    engine.initialize_repository(repo_path)
    return engine


@pytest.fixture
def diff_generator(temp_dir):
    """Create a visual diff generator instance for testing."""
    output_dir = temp_dir / "diffs"
    return CreativeVisualDiffGenerator(output_directory=output_dir)


@pytest.fixture
def timeline_manager(temp_dir, diff_generator):
    """Create a timeline manager instance for testing."""
    return CreativeTimelineManager(
        repository_path=temp_dir / "repo",
        diff_generator=diff_generator
    )


@pytest.fixture
def element_extractor(temp_dir):
    """Create an element extractor instance for testing."""
    output_dir = temp_dir / "elements"
    return CreativeElementExtractor(output_directory=output_dir)


@pytest.fixture
def asset_tracker(temp_dir):
    """Create an asset reference tracker instance for testing."""
    return CreativeAssetReferenceTracker(repository_path=temp_dir / "repo")


@pytest.fixture
def workspace_capture(temp_dir):
    """Create a workspace capture instance for testing."""
    return CreativeEnvironmentCapture(workspace_path=temp_dir / "workspaces")