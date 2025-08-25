"""
Tests for the visual difference generator component.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

from creative_vault.visual_diff.diff_generator import CreativeVisualDiffGenerator


def test_generate_image_diff(diff_generator, test_image, test_image_modified):
    """Test generating a visual difference image between two versions of an image file."""
    # Generate a diff image
    diff_path = diff_generator.generate_image_diff(test_image, test_image_modified)
    
    # Check that the diff image was created
    assert diff_path.exists()
    
    # Check that the diff image is a valid image
    diff_img = Image.open(diff_path)
    assert diff_img.size[0] > 0
    assert diff_img.size[1] > 0


def test_generate_model_diff(diff_generator, test_model, test_model_modified):
    """Test generating a visual difference representation between two versions of a 3D model."""
    # Generate a diff visualization
    diff_path = diff_generator.generate_model_diff(test_model, test_model_modified)
    
    # Check that the diff visualization was created
    assert diff_path.exists()
    
    # Check that the visualization is a valid image (should be a PNG)
    diff_img = Image.open(diff_path)
    assert diff_img.size[0] > 0
    assert diff_img.size[1] > 0


def test_get_diff_stats_for_images(diff_generator, test_image, test_image_modified):
    """Test getting statistical information about the differences between two images."""
    # Get diff statistics
    diff_stats = diff_generator.get_diff_stats(test_image, test_image_modified)
    
    # Check the diff statistics
    assert diff_stats is not None
    assert "file_type" in diff_stats
    assert diff_stats["file_type"] == "image"
    assert "original_dimensions" in diff_stats
    assert "modified_dimensions" in diff_stats
    assert "different_pixels" in diff_stats
    assert "different_pixels_percent" in diff_stats
    assert "histogram_difference" in diff_stats
    
    # Check that there are differences detected
    assert diff_stats["different_pixels"] > 0
    assert diff_stats["different_pixels_percent"] > 0
    assert diff_stats["histogram_difference"] > 0


def test_get_diff_stats_for_models(diff_generator, test_model, test_model_modified):
    """Test getting statistical information about the differences between two 3D models."""
    # Get diff statistics
    diff_stats = diff_generator.get_diff_stats(test_model, test_model_modified)
    
    # Check the diff statistics
    assert diff_stats is not None
    assert "file_type" in diff_stats
    assert diff_stats["file_type"] == "model"
    assert "original_vertices" in diff_stats
    assert "modified_vertices" in diff_stats
    assert "vertex_difference" in diff_stats
    assert "vertex_difference_percent" in diff_stats
    assert "original_faces" in diff_stats
    assert "modified_faces" in diff_stats
    assert "face_difference" in diff_stats
    assert "face_difference_percent" in diff_stats


def test_diff_generation_with_custom_output_path(diff_generator, test_image, test_image_modified, temp_dir):
    """Test generating a diff image with a custom output path."""
    # Create a custom output path
    output_path = temp_dir / "custom_diff.png"
    
    # Generate a diff image with the custom output path
    result_path = diff_generator.generate_image_diff(
        test_image, 
        test_image_modified, 
        output_path
    )
    
    # Check that the diff image was created at the specified path
    assert result_path == output_path
    assert output_path.exists()


def test_error_handling_for_nonexistent_files(diff_generator, temp_dir):
    """Test error handling when files don't exist."""
    non_existent_file = temp_dir / "does_not_exist.png"
    
    # Attempt to generate a diff with a non-existent file
    with pytest.raises(FileNotFoundError):
        diff_generator.generate_image_diff(non_existent_file, non_existent_file)
    
    # Attempt to get diff stats with a non-existent file
    with pytest.raises(FileNotFoundError):
        diff_generator.get_diff_stats(non_existent_file, non_existent_file)


def test_diff_for_different_image_sizes(diff_generator, temp_dir):
    """Test generating a diff between images of different sizes."""
    # Create two images with different dimensions
    img1_path = temp_dir / "small.png"
    img2_path = temp_dir / "large.png"
    
    # Create a small image
    small_img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    small_img.save(img1_path)
    
    # Create a larger image
    large_img = Image.new('RGB', (200, 200), color=(0, 0, 255))
    large_img.save(img2_path)
    
    # Generate a diff image
    diff_path = diff_generator.generate_image_diff(img1_path, img2_path)
    
    # Check that the diff image was created
    assert diff_path.exists()
    
    # Get diff statistics
    diff_stats = diff_generator.get_diff_stats(img1_path, img2_path)
    
    # Check that the difference in dimensions is detected
    assert diff_stats["dimension_changed"] is True
    assert diff_stats["original_dimensions"] != diff_stats["modified_dimensions"]