"""
Visual difference generator for creative files.

This module provides functionality for generating visual representations of
differences between versions of image and 3D model files.
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import trimesh

from creative_vault.interfaces import VisualDiffGenerator
from creative_vault.utils import create_unique_id, detect_file_type


class CreativeVisualDiffGenerator(VisualDiffGenerator):
    """Implementation of the visual difference generator for creative files."""
    
    def __init__(self, output_directory: Optional[Path] = None):
        """Initialize the visual difference generator.
        
        Args:
            output_directory: Optional directory to store difference visualizations
        """
        self.output_directory = output_directory or Path("diffs")
        self.output_directory.mkdir(parents=True, exist_ok=True)
    
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
            
        Raises:
            ValueError: If either file is not an image
            FileNotFoundError: If either file does not exist
        """
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found: {original_path}")
        if not modified_path.exists():
            raise FileNotFoundError(f"Modified file not found: {modified_path}")
        
        # Ensure they are image files
        if detect_file_type(original_path) != "image" or detect_file_type(modified_path) != "image":
            raise ValueError("Both files must be images")
        
        # Open images
        try:
            original_img = Image.open(original_path).convert('RGBA')
            modified_img = Image.open(modified_path).convert('RGBA')
        except Exception as e:
            raise ValueError(f"Failed to open image files: {e}")
        
        # Resize if dimensions don't match
        if original_img.size != modified_img.size:
            # Use the larger dimensions
            max_width = max(original_img.width, modified_img.width)
            max_height = max(original_img.height, modified_img.height)
            
            # Resize with transparent background
            if original_img.size != (max_width, max_height):
                new_original = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))
                new_original.paste(original_img, (0, 0))
                original_img = new_original
            
            if modified_img.size != (max_width, max_height):
                new_modified = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))
                new_modified.paste(modified_img, (0, 0))
                modified_img = new_modified
        
        # Create a difference mask
        diff_mask = self._create_image_diff_mask(original_img, modified_img)
        
        # Create a side-by-side comparison with difference highlights
        comparison = self._create_side_by_side_comparison(original_img, modified_img, diff_mask)
        
        # Save the result
        if output_path is None:
            diff_id = create_unique_id("diff-")
            output_path = self.output_directory / f"{diff_id}.png"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        comparison.save(output_path)
        
        return output_path
    
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
            
        Raises:
            ValueError: If either file is not a 3D model
            FileNotFoundError: If either file does not exist
        """
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found: {original_path}")
        if not modified_path.exists():
            raise FileNotFoundError(f"Modified file not found: {modified_path}")
        
        # Ensure they are 3D model files
        if detect_file_type(original_path) != "model" or detect_file_type(modified_path) != "model":
            raise ValueError("Both files must be 3D models")
        
        # Load models
        try:
            original_model = trimesh.load(original_path)
            modified_model = trimesh.load(modified_path)
        except Exception as e:
            raise ValueError(f"Failed to load 3D model files: {e}")
        
        # Generate a visualization of the differences
        if output_path is None:
            diff_id = create_unique_id("diff-")
            output_path = self.output_directory / f"{diff_id}.png"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a visual diff and save it
        self._create_model_diff_visualization(original_model, modified_model, output_path)
        
        return output_path
    
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
            
        Raises:
            ValueError: If the files are not supported
            FileNotFoundError: If either file does not exist
        """
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found: {original_path}")
        if not modified_path.exists():
            raise FileNotFoundError(f"Modified file not found: {modified_path}")
        
        # Detect file types
        original_type = detect_file_type(original_path)
        modified_type = detect_file_type(modified_path)
        
        # Ensure file types match
        if original_type != modified_type:
            raise ValueError("Files must be of the same type")
        
        # Get appropriate stats based on file type
        if original_type == "image":
            return self._get_image_diff_stats(original_path, modified_path)
        elif original_type == "model":
            return self._get_model_diff_stats(original_path, modified_path)
        else:
            # For other file types, just provide basic stats
            return {
                "original_size": original_path.stat().st_size,
                "modified_size": modified_path.stat().st_size,
                "size_difference": modified_path.stat().st_size - original_path.stat().st_size,
                "size_difference_percent": (
                    (modified_path.stat().st_size - original_path.stat().st_size) / 
                    original_path.stat().st_size * 100 if original_path.stat().st_size > 0 else 0
                ),
                "file_type": original_type
            }
    
    def _create_image_diff_mask(self, original_img: Image.Image, modified_img: Image.Image) -> Image.Image:
        """Create a mask highlighting the differences between two images.
        
        Args:
            original_img: The original image
            modified_img: The modified image
            
        Returns:
            An image mask highlighting the differences
        """
        # Split into channels to handle transparency correctly
        original_r, original_g, original_b, original_a = original_img.split()
        modified_r, modified_g, modified_b, modified_a = modified_img.split()
        
        # Calculate differences for each channel
        diff_r = ImageChops.difference(original_r, modified_r)
        diff_g = ImageChops.difference(original_g, modified_g)
        diff_b = ImageChops.difference(original_b, modified_b)
        diff_a = ImageChops.difference(original_a, modified_a)
        
        # Combine the difference channels
        diff_img = Image.merge('RGBA', (diff_r, diff_g, diff_b, diff_a))
        
        # Apply a threshold to the difference mask
        # This is simplified; a real implementation would be more sophisticated
        diff_array = np.array(diff_img)
        mask_array = np.zeros_like(diff_array)
        
        # Consider a pixel different if any channel difference is greater than 10
        diff_threshold = 10
        diff_pixels = np.max(diff_array[:, :, :3], axis=2) > diff_threshold
        
        # Create a red mask for changed pixels
        mask_array[diff_pixels, 0] = 255  # Red channel
        mask_array[diff_pixels, 3] = 128  # Alpha (semi-transparent)
        
        return Image.fromarray(mask_array)
    
    def _create_side_by_side_comparison(
        self, 
        original_img: Image.Image, 
        modified_img: Image.Image, 
        diff_mask: Image.Image
    ) -> Image.Image:
        """Create a side-by-side comparison image with difference highlights.
        
        Args:
            original_img: The original image
            modified_img: The modified image
            diff_mask: The difference mask
            
        Returns:
            A side-by-side comparison image
        """
        # Create a new image to hold the comparison
        width = original_img.width * 2 + 20  # Extra space between images
        height = original_img.height + 40  # Extra space for labels
        comparison = Image.new('RGBA', (width, height), (240, 240, 240, 255))
        
        # Paste the original image
        comparison.paste(original_img, (0, 30))
        
        # Create a composite of the modified image with the difference mask
        modified_with_diff = Image.alpha_composite(modified_img, diff_mask)
        
        # Paste the modified image with differences highlighted
        comparison.paste(modified_with_diff, (original_img.width + 20, 30))
        
        # Add labels
        draw = ImageDraw.Draw(comparison)
        draw.text((10, 10), "Original", fill=(0, 0, 0, 255))
        draw.text((original_img.width + 30, 10), "Modified (with differences)", fill=(0, 0, 0, 255))
        
        return comparison
    
    def _create_model_diff_visualization(
        self, 
        original_model: trimesh.Trimesh, 
        modified_model: trimesh.Trimesh, 
        output_path: Path
    ) -> None:
        """Create a visualization of the differences between two 3D models.
        
        Args:
            original_model: The original 3D model
            modified_model: The modified 3D model
            output_path: Path to save the visualization
        """
        # This is a simplified visualization
        # A real implementation would use more sophisticated methods
        
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        
        # Plot original model
        original_vertices = np.array(original_model.vertices)
        if len(original_vertices) > 0:
            ax1.scatter(original_vertices[:, 0], original_vertices[:, 1], c='blue', s=1)
            ax1.set_title("Original Model")
        else:
            ax1.set_title("Original Model (Empty)")
        
        # Plot modified model
        modified_vertices = np.array(modified_model.vertices)
        if len(modified_vertices) > 0:
            ax2.scatter(modified_vertices[:, 0], modified_vertices[:, 1], c='red', s=1)
            ax2.set_title("Modified Model")
        else:
            ax2.set_title("Modified Model (Empty)")
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close(fig)
    
    def _get_image_diff_stats(self, original_path: Path, modified_path: Path) -> Dict[str, Any]:
        """Get statistical information about the differences between two images.
        
        Args:
            original_path: Path to the original image
            modified_path: Path to the modified image
            
        Returns:
            Dictionary with statistical information
        """
        original_img = Image.open(original_path).convert('RGBA')
        modified_img = Image.open(modified_path).convert('RGBA')
        
        # Get dimensions
        original_width, original_height = original_img.size
        modified_width, modified_height = modified_img.size
        
        # If dimensions are different, resize for comparison
        if original_img.size != modified_img.size:
            # Use the smaller dimensions for comparison
            compare_width = min(original_width, modified_width)
            compare_height = min(original_height, modified_height)
            
            original_img_small = original_img.resize((compare_width, compare_height))
            modified_img_small = modified_img.resize((compare_width, compare_height))
        else:
            original_img_small = original_img
            modified_img_small = modified_img
        
        # Calculate differences
        diff_mask = self._create_image_diff_mask(original_img_small, modified_img_small)
        diff_array = np.array(diff_mask)
        
        # Count different pixels
        diff_pixels = np.sum(diff_array[:, :, 3] > 0)
        total_pixels = diff_array.shape[0] * diff_array.shape[1]
        diff_percentage = (diff_pixels / total_pixels) * 100 if total_pixels > 0 else 0
        
        # Calculate histogram differences for each channel
        original_histogram = original_img_small.histogram()
        modified_histogram = modified_img_small.histogram()
        
        # Normalize the histograms
        original_histogram_normalized = np.array(original_histogram) / sum(original_histogram)
        modified_histogram_normalized = np.array(modified_histogram) / sum(modified_histogram)
        
        # Calculate histogram difference
        histogram_diff = np.sum(np.abs(original_histogram_normalized - modified_histogram_normalized))
        
        return {
            "original_dimensions": f"{original_width}x{original_height}",
            "modified_dimensions": f"{modified_width}x{modified_height}",
            "dimension_changed": original_img.size != modified_img.size,
            "different_pixels": int(diff_pixels),
            "different_pixels_percent": float(diff_percentage),
            "histogram_difference": float(histogram_diff),
            "file_type": "image"
        }
    
    def _get_model_diff_stats(self, original_path: Path, modified_path: Path) -> Dict[str, Any]:
        """Get statistical information about the differences between two 3D models.
        
        Args:
            original_path: Path to the original 3D model
            modified_path: Path to the modified 3D model
            
        Returns:
            Dictionary with statistical information
        """
        original_model = trimesh.load(original_path)
        modified_model = trimesh.load(modified_path)
        
        # Get basic model information
        original_vertices = len(original_model.vertices) if hasattr(original_model, 'vertices') else 0
        original_faces = len(original_model.faces) if hasattr(original_model, 'faces') else 0
        
        modified_vertices = len(modified_model.vertices) if hasattr(modified_model, 'vertices') else 0
        modified_faces = len(modified_model.faces) if hasattr(modified_model, 'faces') else 0
        
        # Calculate differences
        vertex_diff = modified_vertices - original_vertices
        face_diff = modified_faces - original_faces
        
        vertex_diff_percent = (vertex_diff / original_vertices * 100) if original_vertices > 0 else 0
        face_diff_percent = (face_diff / original_faces * 100) if original_faces > 0 else 0
        
        # Calculate additional metrics if possible
        volume_diff = 0
        surface_area_diff = 0
        bounding_box_diff = 0
        
        try:
            if hasattr(original_model, 'volume') and hasattr(modified_model, 'volume'):
                original_volume = original_model.volume
                modified_volume = modified_model.volume
                volume_diff = ((modified_volume - original_volume) / original_volume * 100
                              if original_volume else 0)
            
            if hasattr(original_model, 'area') and hasattr(modified_model, 'area'):
                original_area = original_model.area
                modified_area = modified_model.area
                surface_area_diff = ((modified_area - original_area) / original_area * 100
                                   if original_area else 0)
            
            original_bbox = original_model.bounding_box.volume if hasattr(original_model, 'bounding_box') else 0
            modified_bbox = modified_model.bounding_box.volume if hasattr(modified_model, 'bounding_box') else 0
            bounding_box_diff = ((modified_bbox - original_bbox) / original_bbox * 100
                                if original_bbox else 0)
        except Exception:
            # Ignore errors in calculating these metrics
            pass
        
        return {
            "original_vertices": original_vertices,
            "modified_vertices": modified_vertices,
            "vertex_difference": vertex_diff,
            "vertex_difference_percent": float(vertex_diff_percent),
            "original_faces": original_faces,
            "modified_faces": modified_faces,
            "face_difference": face_diff,
            "face_difference_percent": float(face_diff_percent),
            "volume_difference_percent": float(volume_diff),
            "surface_area_difference_percent": float(surface_area_diff),
            "bounding_box_difference_percent": float(bounding_box_diff),
            "file_type": "model"
        }