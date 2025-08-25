"""
Tests for the feature transformation pipeline.
"""

import pytest
import json
import time
import math
from vectordb.transform.operations import Scaler, Normalizer, OneHotEncoder, MissingValueImputer
from vectordb.transform.pipeline import TransformationPipeline, FeatureTransformer


class TestTransformationPipeline:
    """Tests for the TransformationPipeline class."""
    
    def setup_method(self):
        """Set up test data and operations for each test."""
        # Create test data
        self.data = {
            "entity1": {"num": 10, "cat": "A", "missing": None},
            "entity2": {"num": 20, "cat": "B", "missing": 20},
            "entity3": {"num": 30, "cat": "C", "missing": None},
            "entity4": {"num": 40, "cat": "A", "missing": 40},
            "entity5": {"num": 50, "cat": "B", "missing": 50}
        }
        
        # Create operations
        self.scaler = Scaler()
        self.encoder = OneHotEncoder()
        self.imputer = MissingValueImputer(strategy="mean")
    
    def test_initialization(self):
        """Test TransformationPipeline initialization."""
        # Default initialization
        pipeline = TransformationPipeline()
        assert pipeline.name == "TransformationPipeline"
        assert pipeline.operations == []
        assert pipeline.transformations_applied == 0
        
        # Initialize with operations
        pipeline = TransformationPipeline(
            name="TestPipeline",
            operations=[self.scaler, self.encoder]
        )
        assert pipeline.name == "TestPipeline"
        assert len(pipeline.operations) == 2
        assert pipeline.operations[0] == self.scaler
        assert pipeline.operations[1] == self.encoder
    
    def test_add_remove_operations(self):
        """Test adding and removing operations."""
        pipeline = TransformationPipeline()
        
        # Add operations
        pipeline.add_operation(self.scaler)
        pipeline.add_operation(self.encoder)
        pipeline.add_operation(self.imputer)
        
        assert len(pipeline.operations) == 3
        assert pipeline.operations[0] == self.scaler
        assert pipeline.operations[1] == self.encoder
        assert pipeline.operations[2] == self.imputer
        
        # Remove operation
        removed = pipeline.remove_operation(1)
        assert removed == self.encoder
        assert len(pipeline.operations) == 2
        assert pipeline.operations[0] == self.scaler
        assert pipeline.operations[1] == self.imputer
        
        # Try to remove with invalid index
        assert pipeline.remove_operation(999) is None
        
        # Clear operations
        pipeline.clear_operations()
        assert len(pipeline.operations) == 0
    
    def test_fit(self):
        """Test fitting the pipeline."""
        pipeline = TransformationPipeline(
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # None of the operations should be fitted initially
        assert not self.scaler.fitted
        assert not self.encoder.fitted
        assert not self.imputer.fitted
        
        # Fit the pipeline
        pipeline.fit(self.data)
        
        # All operations should now be fitted
        assert self.scaler.fitted
        assert self.encoder.fitted
        assert self.imputer.fitted
        
        # Test fitting on specific features
        pipeline = TransformationPipeline(
            operations=[self.scaler, self.encoder, self.imputer]
        )
        pipeline.fit(self.data, feature_names=["num"])
        
        # Operations should be fitted on the specified features
        assert "num" in self.scaler._min_values
        assert "cat" not in self.scaler._min_values
    
    def test_transform(self):
        """Test transforming data with the pipeline."""
        pipeline = TransformationPipeline(
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # Fit the pipeline
        pipeline.fit(self.data)
        
        # Transform the data
        transformed = pipeline.transform(self.data)
        
        # Check result of transformation chain
        # Scaler: Scales 'num' to [0, 1]
        # OneHotEncoder: Encodes 'cat' to one-hot
        # Imputer: Imputes missing values
        
        # Check 'num' (should be scaled to [0, 1])
        assert math.isclose(transformed["entity1"]["num"], 0.0)
        assert math.isclose(transformed["entity5"]["num"], 1.0)
        
        # Check 'cat' (should be one-hot encoded)
        assert "cat" not in transformed["entity1"]
        assert transformed["entity1"]["cat_A"] == 1.0
        assert transformed["entity1"]["cat_B"] == 0.0
        assert transformed["entity1"]["cat_C"] == 0.0
        
        # Check 'missing' (should be imputed)
        # Value might be normalized/scaled after imputation
        assert transformed["entity1"]["missing"] is not None
        
        # Check metrics
        assert pipeline.transformations_applied == 1
        assert pipeline.avg_transform_time > 0
    
    def test_fit_transform(self):
        """Test combined fit and transform."""
        pipeline = TransformationPipeline(
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # Fit and transform
        transformed = pipeline.fit_transform(self.data)
        
        # Check the result (similar to transform test)
        assert transformed["entity1"]["num"] == 0.0
        assert "cat_A" in transformed["entity1"]
        assert transformed["entity1"]["missing"] is not None
        
        # Pipeline should be fitted
        assert self.scaler.fitted
        assert self.encoder.fitted
        assert self.imputer.fitted
    
    def test_operation_info(self):
        """Test getting operation information."""
        pipeline = TransformationPipeline(
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # Fit to set parameters
        pipeline.fit(self.data)
        
        # Get operation info
        info = pipeline.get_operation_info()
        
        assert len(info) == 3
        assert info[0]["type"] == "Scaler"
        assert info[1]["type"] == "OneHotEncoder"
        assert info[2]["type"] == "MissingValueImputer"
        
        # Should include fitted parameters
        assert "params" in info[0]
        assert "min_values" in info[0]["params"]
    
    def test_serialization(self):
        """Test serialization to dictionary and JSON."""
        pipeline = TransformationPipeline(
            name="TestPipeline",
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # Fit to set parameters
        pipeline.fit(self.data)
        
        # Convert to dictionary
        pipeline_dict = pipeline.to_dict()
        
        assert pipeline_dict["name"] == "TestPipeline"
        assert len(pipeline_dict["operations"]) == 3
        assert pipeline_dict["transformations_applied"] == 0
        
        # Create from dictionary
        new_pipeline = TransformationPipeline.from_dict(pipeline_dict)
        
        assert new_pipeline.name == "TestPipeline"
        assert len(new_pipeline.operations) == 3
        
        # Check operation types
        assert type(new_pipeline.operations[0]).__name__ == "Scaler"
        assert type(new_pipeline.operations[1]).__name__ == "OneHotEncoder"
        assert type(new_pipeline.operations[2]).__name__ == "MissingValueImputer"
        
        # Convert to JSON
        pipeline_json = pipeline.to_json()
        
        # Create from JSON
        new_pipeline = TransformationPipeline.from_json(pipeline_json)
        
        assert new_pipeline.name == "TestPipeline"
        assert len(new_pipeline.operations) == 3
    
    def test_clone(self):
        """Test cloning the pipeline."""
        pipeline = TransformationPipeline(
            name="TestPipeline",
            operations=[self.scaler, self.encoder, self.imputer]
        )
        
        # Fit to set parameters
        pipeline.fit(self.data)
        
        # Clone the pipeline
        clone = pipeline.clone()
        
        assert clone.name == pipeline.name
        assert len(clone.operations) == len(pipeline.operations)
        
        # Should be a deep copy
        assert clone is not pipeline
        assert clone.operations[0] is not pipeline.operations[0]
        
        # But operations should be functionally equivalent
        assert clone.operations[0]._min_values == pipeline.operations[0]._min_values
        
        # Transformations should produce the same result
        original_result = pipeline.transform(self.data)
        clone_result = clone.transform(self.data)
        
        assert original_result == clone_result


class TestFeatureTransformer:
    """Tests for the FeatureTransformer class."""
    
    def setup_method(self):
        """Set up test data and pipeline for each test."""
        # Create test data
        self.data = {
            "entity1": {"num1": 10, "num2": 100, "cat": "A"},
            "entity2": {"num1": 20, "num2": 200, "cat": "B"},
            "entity3": {"num1": 30, "num2": 300, "cat": "C"},
            "entity4": {"num1": 40, "num2": 400, "cat": "A"},
            "entity5": {"num1": 50, "num2": 500, "cat": "B"}
        }
        
        # Create a pipeline
        self.pipeline = TransformationPipeline(
            operations=[
                Scaler(),
                OneHotEncoder()
            ]
        )
        self.pipeline.fit(self.data)
    
    def test_initialization(self):
        """Test FeatureTransformer initialization."""
        # Default initialization
        transformer = FeatureTransformer(pipeline=self.pipeline)
        assert transformer.pipeline is self.pipeline
        assert transformer.feature_mapping == {}
        
        # With feature mapping
        mapping = {"num1": "scaled_num1", "cat": "encoded_cat"}
        transformer = FeatureTransformer(
            pipeline=self.pipeline,
            feature_mapping=mapping
        )
        assert transformer.feature_mapping == mapping
    
    def test_transform(self):
        """Test transforming data with the feature transformer."""
        # Transformer without mapping
        transformer = FeatureTransformer(pipeline=self.pipeline)
        
        transformed = transformer.transform(self.data)
        
        # Check transformation results (similar to pipeline transform)
        assert transformed["entity1"]["num1"] == 0.0  # Scaled
        assert transformed["entity5"]["num1"] == 1.0  # Scaled
        assert "cat" not in transformed["entity1"]  # Original feature removed
        assert transformed["entity1"]["cat_A"] == 1.0  # One-hot encoded
        
        # Transformer with feature mapping
        mapping = {"num1": "scaled_num1", "cat": "original_cat"}
        transformer = FeatureTransformer(
            pipeline=self.pipeline,
            feature_mapping=mapping
        )
        
        transformed = transformer.transform(self.data)
        
        # Check transformed feature names
        assert "scaled_num1" in transformed["entity1"]
        assert "num1" not in transformed["entity1"]
        assert transformed["entity1"]["scaled_num1"] == 0.0
        
        # cat is mapped but removed by encoder, cat_X features should remain
        assert "original_cat" not in transformed["entity1"]
        assert "cat_A" in transformed["entity1"]
        
        # Unmapped features should remain unchanged
        assert transformed["entity1"]["num2"] == 100
    
    def test_fit_transform(self):
        """Test combined fit and transform."""
        # Create a new pipeline (not fitted)
        pipeline = TransformationPipeline(
            operations=[
                Scaler(),
                OneHotEncoder()
            ]
        )
        
        mapping = {"num1": "scaled_num1"}
        transformer = FeatureTransformer(
            pipeline=pipeline,
            feature_mapping=mapping
        )
        
        # Create a pipeline with operations
        scaler = Scaler()
        scaler.fit(self.data)  # Pre-fit the scaler

        # Create a new pipeline with the fitted scaler
        pipeline = TransformationPipeline(
            operations=[scaler]
        )

        # Create the transformer with the fitted pipeline
        transformer = FeatureTransformer(
            pipeline=pipeline,
            feature_mapping=mapping
        )

        # Transform the data (no need to fit again)
        transformed = transformer.transform(self.data)

        # Check the result
        assert "scaled_num1" in transformed["entity1"]
        assert transformed["entity1"]["scaled_num1"] == 0.0
        
        # Pipeline should now be fitted
        assert pipeline.operations[0].fitted
    
    def test_serialization(self):
        """Test serialization to dictionary and JSON."""
        mapping = {"num1": "scaled_num1", "cat": "encoded_cat"}
        transformer = FeatureTransformer(
            pipeline=self.pipeline,
            feature_mapping=mapping
        )
        
        # Convert to dictionary
        transformer_dict = transformer.to_dict()
        
        assert "pipeline" in transformer_dict
        assert transformer_dict["feature_mapping"] == mapping
        
        # Create from dictionary
        new_transformer = FeatureTransformer.from_dict(transformer_dict)
        
        assert new_transformer.feature_mapping == mapping
        assert len(new_transformer.pipeline.operations) == 2
        
        # Convert to JSON
        transformer_json = transformer.to_json()
        
        # Create from JSON
        new_transformer = FeatureTransformer.from_json(transformer_json)
        
        assert new_transformer.feature_mapping == mapping