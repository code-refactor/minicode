"""
Tests for the element extraction framework component.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

from creative_vault.element_extraction.extractor import CreativeElementExtractor


def test_list_elements_for_image(element_extractor, test_image):
    """Test listing extractable elements in an image file."""
    # List elements
    elements = element_extractor.list_elements(test_image)
    
    # Check the result
    assert elements is not None
    assert len(elements) > 0
    
    # Check the whole image element
    whole_image = next((e for e in elements if e["id"] == "whole_image"), None)
    assert whole_image is not None
    assert whole_image["name"] == "Whole Image"
    assert whole_image["type"] == "image"
    
    # Check that quadrants are present
    quadrants = [e for e in elements if e["id"].startswith("quadrant_")]
    assert len(quadrants) == 4


def test_extract_whole_image(element_extractor, test_image, temp_dir):
    """Test extracting the whole image as an element."""
    # List elements to get the element ID
    elements = element_extractor.list_elements(test_image)
    whole_image = next((e for e in elements if e["id"] == "whole_image"), None)
    assert whole_image is not None
    
    # Extract the whole image
    output_path = temp_dir / "extracted_whole_image.png"
    result_path = element_extractor.extract_element(
        test_image, 
        whole_image["id"], 
        output_path
    )
    
    # Check the result
    assert result_path == output_path
    assert output_path.exists()
    
    # Check that the extracted image is valid
    extracted_img = Image.open(output_path)
    original_img = Image.open(test_image)
    assert extracted_img.size == original_img.size


def test_extract_image_region(element_extractor, test_image, temp_dir):
    """Test extracting a region of an image as an element."""
    # List elements to get a quadrant element ID
    elements = element_extractor.list_elements(test_image)
    quadrant = next((e for e in elements if e["id"].startswith("quadrant_")), None)
    assert quadrant is not None
    
    # Extract the quadrant
    output_path = temp_dir / "extracted_quadrant.png"
    result_path = element_extractor.extract_element(
        test_image, 
        quadrant["id"], 
        output_path
    )
    
    # Check the result
    assert result_path == output_path
    assert output_path.exists()
    
    # Check that the extracted image is valid
    extracted_img = Image.open(output_path)
    assert extracted_img.size[0] > 0
    assert extracted_img.size[1] > 0
    
    # Check dimensions match metadata
    assert extracted_img.size[0] == quadrant["metadata"]["width"]
    assert extracted_img.size[1] == quadrant["metadata"]["height"]


def test_replace_image_region(element_extractor, test_image, temp_dir):
    """Test replacing a region of an image with another image."""
    # List elements to get a quadrant element ID
    elements = element_extractor.list_elements(test_image)
    quadrant = next((e for e in elements if e["id"].startswith("quadrant_")), None)
    assert quadrant is not None
    
    # Create a replacement image (solid red)
    replacement_path = temp_dir / "replacement.png"
    replacement_img = Image.new(
        'RGB', 
        (quadrant["metadata"]["width"], quadrant["metadata"]["height"]), 
        color=(255, 0, 0)
    )
    replacement_img.save(replacement_path)
    
    # Replace the quadrant
    output_path = temp_dir / "image_with_replaced_region.png"
    result_path = element_extractor.replace_element(
        test_image, 
        quadrant["id"], 
        replacement_path, 
        output_path
    )
    
    # Check the result
    assert result_path == output_path
    assert output_path.exists()
    
    # Check that the modified image is valid
    modified_img = Image.open(output_path)
    original_img = Image.open(test_image)
    assert modified_img.size == original_img.size


def test_list_elements_for_3d_model(element_extractor, test_model):
    """Test listing extractable elements in a 3D model file."""
    # List elements
    elements = element_extractor.list_elements(test_model)
    
    # Check the result
    assert elements is not None
    assert len(elements) > 0
    
    # Check the whole model element
    whole_model = next((e for e in elements if e["id"] == "whole_model"), None)
    assert whole_model is not None
    assert whole_model["name"] == "Complete Model"
    assert whole_model["type"] == "model"


def test_extract_whole_model(element_extractor, test_model, temp_dir):
    """Test extracting the whole 3D model as an element."""
    # List elements to get the element ID
    elements = element_extractor.list_elements(test_model)
    whole_model = next((e for e in elements if e["id"] == "whole_model"), None)
    assert whole_model is not None
    
    # Extract the whole model
    output_path = temp_dir / "extracted_model.obj"
    result_path = element_extractor.extract_element(
        test_model, 
        whole_model["id"], 
        output_path
    )
    
    # Check the result
    assert result_path == output_path
    assert output_path.exists()
    
    # Check that the output file has content
    assert output_path.stat().st_size > 0


def test_error_handling_for_invalid_element(element_extractor, test_image):
    """Test error handling when requesting an invalid element."""
    # Attempt to extract a non-existent element
    with pytest.raises(ValueError):
        element_extractor.extract_element(test_image, "non_existent_element")


def test_error_handling_for_nonexistent_file(element_extractor, temp_dir):
    """Test error handling when file doesn't exist."""
    non_existent_file = temp_dir / "does_not_exist.png"
    
    # Attempt to list elements in a non-existent file
    with pytest.raises(FileNotFoundError):
        element_extractor.list_elements(non_existent_file)
    
    # Attempt to extract an element from a non-existent file
    with pytest.raises(FileNotFoundError):
        element_extractor.extract_element(non_existent_file, "some_element")