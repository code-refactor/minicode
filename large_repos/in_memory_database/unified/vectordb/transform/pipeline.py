"""
Feature transformation pipeline implementation.

This module provides a pipeline for applying multiple feature transformations
in sequence, with support for configuration, serialization, and tracking.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
import threading

from vectordb.transform.operations import BaseOperation


class TransformationPipeline:
    """
    Pipeline for applying multiple feature transformations.
    
    This class manages a sequence of transformation operations that can be
    applied to feature data, with support for configuration, serialization,
    and tracking transformations applied to features.
    """
    
    def __init__(self, name: Optional[str] = None, operations: Optional[List[BaseOperation]] = None):
        """
        Initialize a transformation pipeline.
        
        Args:
            name: Optional name for this pipeline
            operations: Optional list of transformation operations
        """
        self._name = name or "TransformationPipeline"
        self._operations = operations or []
        self._transformations_applied = 0
        self._last_modified = time.time()
        
        # For tracking performance
        self._total_transform_time = 0.0
        self._transform_count = 0
        
        # For thread safety
        self._lock = threading.RLock()
    
    @property
    def name(self) -> str:
        """Get the name of this pipeline."""
        return self._name
    
    @property
    def operations(self) -> List[BaseOperation]:
        """Get the list of operations in this pipeline."""
        return self._operations.copy()
    
    @property
    def transformations_applied(self) -> int:
        """Get the number of transformations applied by this pipeline."""
        with self._lock:
            return self._transformations_applied
    
    @property
    def last_modified(self) -> float:
        """Get the timestamp of the last modification to this pipeline."""
        return self._last_modified
    
    @property
    def avg_transform_time(self) -> float:
        """Get the average time per transformation in seconds."""
        with self._lock:
            if self._transform_count == 0:
                return 0.0
            return self._total_transform_time / self._transform_count
    
    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add an operation to the pipeline.
        
        Args:
            operation: The operation to add
        """
        with self._lock:
            self._operations.append(operation)
            self._last_modified = time.time()
    
    def remove_operation(self, index: int) -> Optional[BaseOperation]:
        """
        Remove an operation from the pipeline.
        
        Args:
            index: The index of the operation to remove
            
        Returns:
            The removed operation, or None if index is out of range
        """
        with self._lock:
            if 0 <= index < len(self._operations):
                operation = self._operations.pop(index)
                self._last_modified = time.time()
                return operation
            return None
    
    def clear_operations(self) -> None:
        """Remove all operations from the pipeline."""
        with self._lock:
            self._operations.clear()
            self._last_modified = time.time()
    
    def fit(
        self, 
        data: Dict[str, Dict[str, Any]], 
        feature_names: Optional[List[str]] = None
    ) -> None:
        """
        Fit all operations in the pipeline.
        
        Args:
            data: Data to fit the operations on
            feature_names: Optional specific features to fit on
        """
        with self._lock:
            # Fit each operation in sequence
            current_data = data
            for operation in self._operations:
                operation.fit(current_data, feature_names)
                # Apply this operation to get transformed data for the next operation
                current_data = operation.transform(current_data, feature_names)
    
    def transform(
        self, 
        data: Dict[str, Dict[str, Any]], 
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Apply all operations in the pipeline to transform the data.
        
        Args:
            data: Data to transform
            feature_names: Optional specific features to transform
            
        Returns:
            Transformed data
        """
        start_time = time.time()
        
        with self._lock:
            # Apply each operation in sequence
            current_data = data
            for operation in self._operations:
                current_data = operation.transform(current_data, feature_names)
            
            # Update metrics
            self._transformations_applied += 1
            transform_time = time.time() - start_time
            self._total_transform_time += transform_time
            self._transform_count += 1
        
        return current_data
    
    def fit_transform(
        self, 
        data: Dict[str, Dict[str, Any]], 
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fit all operations and then transform the data.
        
        Args:
            data: Data to fit and transform
            feature_names: Optional specific features to use
            
        Returns:
            Transformed data
        """
        self.fit(data, feature_names)
        return self.transform(data, feature_names)
    
    def get_operation_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all operations in the pipeline.
        
        Returns:
            List of operation information dictionaries
        """
        with self._lock:
            return [op.to_dict() for op in self._operations]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this pipeline to a dictionary.
        
        Returns:
            Dictionary representation
        """
        with self._lock:
            return {
                "name": self._name,
                "operations": [op.to_dict() for op in self._operations],
                "transformations_applied": self._transformations_applied,
                "last_modified": self._last_modified,
                "total_transform_time": self._total_transform_time,
                "transform_count": self._transform_count
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransformationPipeline':
        """
        Create a pipeline from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            A new TransformationPipeline instance
        """
        pipeline = cls(name=data.get("name", "TransformationPipeline"))
        
        # Restore operations
        operations_data = data.get("operations", [])
        for op_data in operations_data:
            operation = BaseOperation.from_dict(op_data)
            pipeline.add_operation(operation)
        
        # Restore metrics
        pipeline._transformations_applied = data.get("transformations_applied", 0)
        pipeline._last_modified = data.get("last_modified", time.time())
        pipeline._total_transform_time = data.get("total_transform_time", 0.0)
        pipeline._transform_count = data.get("transform_count", 0)
        
        return pipeline
    
    def to_json(self) -> str:
        """
        Convert this pipeline to a JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TransformationPipeline':
        """
        Create a pipeline from a JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            A new TransformationPipeline instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def clone(self) -> 'TransformationPipeline':
        """
        Create a copy of this pipeline.
        
        Returns:
            A new TransformationPipeline with the same operations
        """
        with self._lock:
            return TransformationPipeline.from_dict(self.to_dict())
    
    def create_feature_transformer(
        self, 
        feature_mapping: Optional[Dict[str, str]] = None
    ) -> 'FeatureTransformer':
        """
        Create a FeatureTransformer from this pipeline.
        
        Args:
            feature_mapping: Optional mapping of source to target feature names
            
        Returns:
            A new FeatureTransformer
        """
        return FeatureTransformer(pipeline=self.clone(), feature_mapping=feature_mapping)


class FeatureTransformer:
    """
    Applies transformations to specific features.
    
    This class wraps a transformation pipeline and applies it to specific
    features, with support for mapping input features to different output names.
    """
    
    def __init__(
        self, 
        pipeline: TransformationPipeline,
        feature_mapping: Optional[Dict[str, str]] = None
    ):
        """
        Initialize a feature transformer.
        
        Args:
            pipeline: The transformation pipeline to use
            feature_mapping: Optional mapping of source to target feature names
        """
        self._pipeline = pipeline
        self._feature_mapping = feature_mapping or {}
    
    @property
    def pipeline(self) -> TransformationPipeline:
        """Get the transformation pipeline."""
        return self._pipeline
    
    @property
    def feature_mapping(self) -> Dict[str, str]:
        """Get the feature mapping."""
        return self._feature_mapping.copy()
    
    def transform(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Transform the data using the pipeline.
        
        Args:
            data: Data to transform
            
        Returns:
            Transformed data with mapped feature names
        """
        # Extract source feature names from the mapping
        source_features = list(self._feature_mapping.keys()) if self._feature_mapping else None
        
        # Transform using the pipeline
        transformed_data = self._pipeline.transform(data, source_features)
        
        # Apply feature mapping if needed
        if self._feature_mapping:
            result = {}
            for entity_id, entity_features in transformed_data.items():
                result[entity_id] = {}
                
                # Copy non-mapped features directly
                for feature_name, value in entity_features.items():
                    if feature_name not in self._feature_mapping:
                        result[entity_id][feature_name] = value
                
                # Apply mapping for mapped features
                for source, target in self._feature_mapping.items():
                    if source in entity_features:
                        result[entity_id][target] = entity_features[source]
                        
            return result
        
        # No mapping needed
        return transformed_data
    
    def fit(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Fit the transformation pipeline.
        
        Args:
            data: Data to fit the pipeline on
        """
        # Extract source feature names from the mapping
        source_features = list(self._feature_mapping.keys()) if self._feature_mapping else None
        
        # Fit the pipeline
        self._pipeline.fit(data, source_features)
    
    def fit_transform(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Fit the pipeline and then transform the data.
        
        Args:
            data: Data to fit and transform
            
        Returns:
            Transformed data with mapped feature names
        """
        self.fit(data)
        return self.transform(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this transformer to a dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "pipeline": self._pipeline.to_dict(),
            "feature_mapping": self._feature_mapping
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeatureTransformer':
        """
        Create a transformer from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            A new FeatureTransformer instance
        """
        pipeline = TransformationPipeline.from_dict(data["pipeline"])
        feature_mapping = data.get("feature_mapping", {})
        
        return cls(pipeline=pipeline, feature_mapping=feature_mapping)
    
    def to_json(self) -> str:
        """
        Convert this transformer to a JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'FeatureTransformer':
        """
        Create a transformer from a JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            A new FeatureTransformer instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)