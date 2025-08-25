"""Serialization utilities for the backup system."""

import json
from pathlib import Path
from typing import Any, Type, Dict
from pydantic import BaseModel


def save_json(data: Any, path: Path, indent: int = 2) -> None:
    """
    Save data as JSON to file.
    
    Args:
        data: Data to save
        path: File path
        indent: JSON indentation
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Custom encoder for Path and datetime objects
    class PathEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Path):
                return str(obj)
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            return super().default(obj)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent, cls=PathEncoder)


def load_json(path: Path) -> Any:
    """
    Load JSON data from file.
    
    Args:
        path: File path
    
    Returns:
        Loaded data
    """
    with open(path, 'r') as f:
        return json.load(f)


def serialize_model(model: BaseModel) -> Dict[str, Any]:
    """
    Serialize a Pydantic model to dictionary.
    
    Args:
        model: Pydantic model instance
    
    Returns:
        Dictionary representation
    """
    return model.dict()


def deserialize_model(data: Dict[str, Any], model_class: Type[BaseModel]) -> BaseModel:
    """
    Deserialize dictionary to Pydantic model.
    
    Args:
        data: Dictionary data
        model_class: Pydantic model class
    
    Returns:
        Model instance
    """
    return model_class(**data)