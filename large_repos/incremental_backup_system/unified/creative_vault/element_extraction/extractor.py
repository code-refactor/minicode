"""
Element Extraction Framework for creative files.

This module provides functionality for extracting and replacing specific elements
or layers from creative files such as images, 3D models, and project files.
"""

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw

from creative_vault.interfaces import ElementExtractor
from creative_vault.utils import create_unique_id, detect_file_type


class ElementInfo:
    """Information about an extractable element."""
    
    def __init__(
        self, 
        id: str, 
        name: str, 
        element_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.name = name
        self.element_type = element_type
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the element info to a dictionary.
        
        Returns:
            Dictionary representation of the element info
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.element_type,
            "metadata": self.metadata
        }


class CreativeElementExtractor(ElementExtractor):
    """Implementation of the element extraction framework."""
    
    def __init__(self, output_directory: Optional[Path] = None):
        """Initialize the element extractor.
        
        Args:
            output_directory: Optional directory to store extracted elements
        """
        self.output_directory = output_directory or Path("extracted_elements")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Register handlers for different file types
        self._handlers = {
            "image": self._handle_image,
            "model": self._handle_model,
            "adobe_project": self._handle_adobe_project
        }
    
    def extract_element(
        self, 
        source_file: Path, 
        element_id: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Extract a specific element from a file.
        
        Args:
            source_file: Path to the source file
            element_id: ID of the element to extract
            output_path: Optional path to save the extracted element
            
        Returns:
            Path to the extracted element
            
        Raises:
            ValueError: If the file type is not supported or the element is not found
            FileNotFoundError: If the source file does not exist
        """
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Detect the file type
        file_type = detect_file_type(source_file)
        
        # Check if we have a handler for this file type
        if file_type not in self._handlers:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Get all elements in the file
        elements = self.list_elements(source_file)
        
        # Find the requested element
        element_info = None
        for element in elements:
            if element["id"] == element_id:
                element_info = element
                break
        
        if not element_info:
            raise ValueError(f"Element {element_id} not found in {source_file}")
        
        # Create output path if not provided
        if output_path is None:
            element_name = element_info["name"].replace(" ", "_").lower()
            output_path = self.output_directory / f"{element_name}_{create_unique_id()}"
            
            # Add an appropriate extension based on the element type
            if "extension" in element_info["metadata"]:
                output_path = output_path.with_suffix(element_info["metadata"]["extension"])
        
        # Extract the element using the appropriate handler
        handler = self._handlers[file_type]
        return handler(source_file, element_id, output_path, "extract")
    
    def list_elements(self, file_path: Path) -> List[Dict[str, Any]]:
        """List all extractable elements in a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dictionaries containing element information
            
        Raises:
            ValueError: If the file type is not supported
            FileNotFoundError: If the file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Detect the file type
        file_type = detect_file_type(file_path)
        
        # Check if we have a handler for this file type
        if file_type not in self._handlers:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Get elements using the appropriate handler
        handler = self._handlers[file_type]
        return handler(file_path, None, None, "list")
    
    def replace_element(
        self, 
        target_file: Path, 
        element_id: str, 
        replacement_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Replace a specific element in a file.
        
        Args:
            target_file: Path to the target file
            element_id: ID of the element to replace
            replacement_path: Path to the replacement element
            output_path: Optional path to save the modified file
            
        Returns:
            Path to the modified file
            
        Raises:
            ValueError: If the file type is not supported or the element is not found
            FileNotFoundError: If the target file or replacement element does not exist
        """
        if not target_file.exists():
            raise FileNotFoundError(f"Target file not found: {target_file}")
        if not replacement_path.exists():
            raise FileNotFoundError(f"Replacement element not found: {replacement_path}")
        
        # Detect the file type
        file_type = detect_file_type(target_file)
        
        # Check if we have a handler for this file type
        if file_type not in self._handlers:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Get all elements in the file
        elements = self.list_elements(target_file)
        
        # Find the requested element
        element_info = None
        for element in elements:
            if element["id"] == element_id:
                element_info = element
                break
        
        if not element_info:
            raise ValueError(f"Element {element_id} not found in {target_file}")
        
        # Create output path if not provided
        if output_path is None:
            output_path = target_file.parent / f"{target_file.stem}_modified{target_file.suffix}"
        
        # Replace the element using the appropriate handler
        handler = self._handlers[file_type]
        return handler(target_file, element_id, output_path, "replace", replacement_path)
    
    def _handle_image(
        self, 
        file_path: Path, 
        element_id: Optional[str], 
        output_path: Optional[Path],
        operation: str,
        replacement_path: Optional[Path] = None
    ) -> Union[List[Dict[str, Any]], Path]:
        """Handle operations on image files.
        
        Args:
            file_path: Path to the image file
            element_id: ID of the element to extract/replace (None for list operation)
            output_path: Path to save the extracted element or modified file
            operation: The operation to perform (list, extract, replace)
            replacement_path: Path to the replacement element (for replace operation)
            
        Returns:
            List of dictionaries containing element information (for list operation)
            Path to the extracted element or modified file (for extract/replace operations)
        """
        # Load the image
        with Image.open(file_path) as img:
            if operation == "list":
                # For simplicity, we'll treat image regions as elements
                # In a real implementation, this would be more sophisticated
                elements = []
                
                # Add the whole image as an element
                elements.append(ElementInfo(
                    id="whole_image",
                    name="Whole Image",
                    element_type="image",
                    metadata={"width": img.width, "height": img.height, "extension": file_path.suffix}
                ).to_dict())
                
                # Add quadrants as elements
                width, height = img.size
                half_width = width // 2
                half_height = height // 2
                
                quadrants = [
                    ((0, 0, half_width, half_height), "Top Left Quadrant"),
                    ((half_width, 0, width, half_height), "Top Right Quadrant"),
                    ((0, half_height, half_width, height), "Bottom Left Quadrant"),
                    ((half_width, half_height, width, height), "Bottom Right Quadrant")
                ]
                
                for i, (bbox, name) in enumerate(quadrants):
                    elements.append(ElementInfo(
                        id=f"quadrant_{i+1}",
                        name=name,
                        element_type="image_region",
                        metadata={
                            "bbox": bbox,
                            "width": bbox[2] - bbox[0],
                            "height": bbox[3] - bbox[1],
                            "extension": ".png"
                        }
                    ).to_dict())
                
                return elements
            
            elif operation == "extract":
                assert element_id is not None, "Element ID is required for extract operation"
                assert output_path is not None, "Output path is required for extract operation"
                
                # Find the element
                elements = self._handle_image(file_path, None, None, "list")
                element_info = next((e for e in elements if e["id"] == element_id), None)
                
                if not element_info:
                    raise ValueError(f"Element {element_id} not found in {file_path}")
                
                # Extract the element
                if element_id == "whole_image":
                    # Just copy the whole image
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(output_path)
                else:
                    # Extract the region
                    bbox = element_info["metadata"]["bbox"]
                    region = img.crop(bbox)
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    region.save(output_path)
                
                return output_path
            
            elif operation == "replace":
                assert element_id is not None, "Element ID is required for replace operation"
                assert output_path is not None, "Output path is required for replace operation"
                assert replacement_path is not None, "Replacement path is required for replace operation"
                
                # Find the element
                elements = self._handle_image(file_path, None, None, "list")
                element_info = next((e for e in elements if e["id"] == element_id), None)
                
                if not element_info:
                    raise ValueError(f"Element {element_id} not found in {file_path}")
                
                # Load the replacement image
                with Image.open(replacement_path) as replacement_img:
                    # Create a copy of the original image
                    result = img.copy()
                    
                    if element_id == "whole_image":
                        # Replace the whole image
                        result = replacement_img.resize(img.size)
                    else:
                        # Replace just the region
                        bbox = element_info["metadata"]["bbox"]
                        
                        # Resize the replacement to match the region
                        region_width = bbox[2] - bbox[0]
                        region_height = bbox[3] - bbox[1]
                        resized_replacement = replacement_img.resize((region_width, region_height))
                        
                        # Paste the replacement into the region
                        result.paste(resized_replacement, (bbox[0], bbox[1]))
                    
                    # Save the result
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    result.save(output_path)
                
                return output_path
            
            else:
                raise ValueError(f"Unsupported operation: {operation}")
    
    def _handle_model(
        self, 
        file_path: Path, 
        element_id: Optional[str], 
        output_path: Optional[Path],
        operation: str,
        replacement_path: Optional[Path] = None
    ) -> Union[List[Dict[str, Any]], Path]:
        """Handle operations on 3D model files.
        
        Args:
            file_path: Path to the 3D model file
            element_id: ID of the element to extract/replace (None for list operation)
            output_path: Path to save the extracted element or modified file
            operation: The operation to perform (list, extract, replace)
            replacement_path: Path to the replacement element (for replace operation)
            
        Returns:
            List of dictionaries containing element information (for list operation)
            Path to the extracted element or modified file (for extract/replace operations)
        """
        # Load the model
        import trimesh
        
        try:
            model = trimesh.load(file_path)
            
            if operation == "list":
                # For simplicity, we'll treat meshes or scenes as elements
                # In a real implementation, this would be more sophisticated
                elements = []
                
                # Add the whole model as an element
                elements.append(ElementInfo(
                    id="whole_model",
                    name="Complete Model",
                    element_type="model",
                    metadata={"extension": file_path.suffix}
                ).to_dict())
                
                # If the model is a scene with multiple meshes, add each mesh as an element
                if isinstance(model, trimesh.Scene):
                    for i, (name, geometry) in enumerate(model.geometry.items()):
                        elements.append(ElementInfo(
                            id=f"mesh_{i+1}",
                            name=f"Mesh: {name}",
                            element_type="mesh",
                            metadata={"mesh_name": name, "extension": ".obj"}
                        ).to_dict())
                
                return elements
            
            elif operation == "extract":
                assert element_id is not None, "Element ID is required for extract operation"
                assert output_path is not None, "Output path is required for extract operation"
                
                # Find the element
                elements = self._handle_model(file_path, None, None, "list")
                element_info = next((e for e in elements if e["id"] == element_id), None)
                
                if not element_info:
                    raise ValueError(f"Element {element_id} not found in {file_path}")
                
                # Extract the element
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                if element_id == "whole_model":
                    # Just export the whole model
                    model.export(output_path)
                else:
                    # Extract a specific mesh
                    mesh_name = element_info["metadata"]["mesh_name"]
                    if isinstance(model, trimesh.Scene) and mesh_name in model.geometry:
                        mesh = model.geometry[mesh_name]
                        mesh.export(output_path)
                    else:
                        raise ValueError(f"Mesh {mesh_name} not found in model")
                
                return output_path
            
            elif operation == "replace":
                assert element_id is not None, "Element ID is required for replace operation"
                assert output_path is not None, "Output path is required for replace operation"
                assert replacement_path is not None, "Replacement path is required for replace operation"
                
                # Find the element
                elements = self._handle_model(file_path, None, None, "list")
                element_info = next((e for e in elements if e["id"] == element_id), None)
                
                if not element_info:
                    raise ValueError(f"Element {element_id} not found in {file_path}")
                
                # Load the replacement model
                replacement_model = trimesh.load(replacement_path)
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                if element_id == "whole_model":
                    # Just use the replacement model
                    replacement_model.export(output_path)
                else:
                    # Replace a specific mesh in the scene
                    if isinstance(model, trimesh.Scene):
                        mesh_name = element_info["metadata"]["mesh_name"]
                        if mesh_name in model.geometry:
                            # Create a copy of the scene
                            result = model.copy()
                            
                            # Replace the mesh
                            if isinstance(replacement_model, trimesh.Trimesh):
                                result.geometry[mesh_name] = replacement_model
                            elif isinstance(replacement_model, trimesh.Scene):
                                # Just use the first mesh from the replacement
                                if len(replacement_model.geometry) > 0:
                                    first_mesh_name = list(replacement_model.geometry.keys())[0]
                                    result.geometry[mesh_name] = replacement_model.geometry[first_mesh_name]
                            
                            # Export the result
                            result.export(output_path)
                        else:
                            raise ValueError(f"Mesh {mesh_name} not found in model")
                    else:
                        # If the model is not a scene, just replace the whole model
                        replacement_model.export(output_path)
                
                return output_path
            
            else:
                raise ValueError(f"Unsupported operation: {operation}")
                
        except Exception as e:
            # If trimesh fails, provide a limited implementation
            print(f"Warning: Failed to load 3D model: {e}")
            
            if operation == "list":
                # Just return the whole model as an element
                return [ElementInfo(
                    id="whole_model",
                    name="Complete Model",
                    element_type="model",
                    metadata={"extension": file_path.suffix}
                ).to_dict()]
            
            elif operation == "extract" and element_id == "whole_model":
                # Just copy the whole file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
                return output_path
            
            elif operation == "replace" and element_id == "whole_model":
                # Just copy the replacement file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(replacement_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
                return output_path
            
            else:
                raise ValueError(f"Operation {operation} not supported for this model")
    
    def _handle_adobe_project(
        self, 
        file_path: Path, 
        element_id: Optional[str], 
        output_path: Optional[Path],
        operation: str,
        replacement_path: Optional[Path] = None
    ) -> Union[List[Dict[str, Any]], Path]:
        """Handle operations on Adobe project files.
        
        Args:
            file_path: Path to the Adobe project file
            element_id: ID of the element to extract/replace (None for list operation)
            output_path: Path to save the extracted element or modified file
            operation: The operation to perform (list, extract, replace)
            replacement_path: Path to the replacement element (for replace operation)
            
        Returns:
            List of dictionaries containing element information (for list operation)
            Path to the extracted element or modified file (for extract/replace operations)
        """
        # Note: This is a simplified implementation for Adobe files
        # A real implementation would use appropriate libraries to parse and modify
        # the specific Adobe file formats (PSD, AI, etc.)
        
        # For simplicity, we'll just return mock data
        if operation == "list":
            # Return mock elements based on the file extension
            elements = []
            
            # Add the whole file as an element
            elements.append(ElementInfo(
                id="whole_project",
                name="Complete Project",
                element_type="project",
                metadata={"extension": file_path.suffix}
            ).to_dict())
            
            # Add mock layers based on file type
            extension = file_path.suffix.lower()
            
            if extension == ".psd":
                # Photoshop file - mock layers
                for i in range(1, 6):
                    elements.append(ElementInfo(
                        id=f"layer_{i}",
                        name=f"Layer {i}",
                        element_type="layer",
                        metadata={"extension": ".png"}
                    ).to_dict())
            
            elif extension == ".ai":
                # Illustrator file - mock artboards
                for i in range(1, 4):
                    elements.append(ElementInfo(
                        id=f"artboard_{i}",
                        name=f"Artboard {i}",
                        element_type="artboard",
                        metadata={"extension": ".svg"}
                    ).to_dict())
            
            elif extension == ".aep":
                # After Effects file - mock compositions
                for i in range(1, 4):
                    elements.append(ElementInfo(
                        id=f"comp_{i}",
                        name=f"Composition {i}",
                        element_type="composition",
                        metadata={"extension": ".mov"}
                    ).to_dict())
            
            return elements
        
        elif operation == "extract":
            assert element_id is not None, "Element ID is required for extract operation"
            assert output_path is not None, "Output path is required for extract operation"
            
            # In a real implementation, this would extract the element from the file
            # For this mock implementation, we'll just create a placeholder file
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if element_id == "whole_project":
                # Just copy the whole file
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
            else:
                # Create a placeholder file
                with open(output_path, 'w') as f:
                    f.write(f"Mock extracted element: {element_id} from {file_path.name}")
            
            return output_path
        
        elif operation == "replace":
            assert element_id is not None, "Element ID is required for replace operation"
            assert output_path is not None, "Output path is required for replace operation"
            assert replacement_path is not None, "Replacement path is required for replace operation"
            
            # In a real implementation, this would replace the element in the file
            # For this mock implementation, we'll just create a placeholder file
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if element_id == "whole_project":
                # Just copy the replacement file
                with open(replacement_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
            else:
                # Copy the original file and append a note about the replacement
                with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
                
                # Append a note (this would not work with binary files in reality)
                try:
                    with open(output_path, 'a') as f:
                        f.write(f"\nMock replacement: {element_id} replaced with {replacement_path.name}")
                except Exception:
                    pass
            
            return output_path
        
        else:
            raise ValueError(f"Unsupported operation: {operation}")