"""
Tests for feature transformation operations.
"""

import pytest
import math
import json
from vectordb.transform.operations import (
    BaseOperation,
    Scaler,
    Normalizer,
    OneHotEncoder,
    MissingValueImputer
)


class TestBaseOperation:
    """Tests for the BaseOperation abstract base class."""
    
    def test_concrete_subclass(self):
        """Test that concrete subclasses of BaseOperation can be instantiated."""
        # Create a minimal concrete subclass
        class MinimalOp(BaseOperation):
            def fit(self, data, feature_names=None):
                pass

            def transform(self, data, feature_names=None):
                return data

            def get_params(self):
                return {}

            def set_params(self, params):
                pass

        # Should be able to instantiate the minimal subclass
        op = MinimalOp()
        assert op.name == "MinimalOp"
        assert not op.fitted

        # Should be able to use fit_transform
        data = {"entity1": {"feature1": 1}}
        result = op.fit_transform(data)
        assert result == data


class TestScaler:
    """Tests for the Scaler operation."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create test data
        self.data = {
            "entity1": {"feature1": 1, "feature2": 10, "text": "not_numeric"},
            "entity2": {"feature1": 2, "feature2": 20, "text": "not_numeric"},
            "entity3": {"feature1": 3, "feature2": 30, "text": "not_numeric"},
            "entity4": {"feature1": 4, "feature2": 40, "text": "not_numeric"},
            "entity5": {"feature1": 5, "feature2": 50, "text": "not_numeric"}
        }
    
    def test_initialization(self):
        """Test Scaler initialization."""
        # Default initialization
        scaler = Scaler()
        assert scaler.name == "Scaler"
        assert scaler._feature_range == (0, 1)
        assert not scaler.fitted
        
        # Custom initialization
        scaler = Scaler(feature_range=(-1, 1), name="CustomScaler")
        assert scaler.name == "CustomScaler"
        assert scaler._feature_range == (-1, 1)
    
    def test_fit(self):
        """Test fitting the scaler."""
        scaler = Scaler()
        
        # Fit on all numeric features
        scaler.fit(self.data)
        
        # Should compute min and max for feature1 and feature2
        assert "feature1" in scaler._min_values
        assert "feature2" in scaler._min_values
        assert "text" not in scaler._min_values
        
        assert scaler._min_values["feature1"] == 1
        assert scaler._max_values["feature1"] == 5
        assert scaler._min_values["feature2"] == 10
        assert scaler._max_values["feature2"] == 50
        
        assert scaler.fitted
        
        # Fit on specific features
        scaler = Scaler()
        scaler.fit(self.data, feature_names=["feature1"])
        
        assert "feature1" in scaler._min_values
        assert "feature2" not in scaler._min_values
    
    def test_transform(self):
        """Test transforming data with the scaler."""
        # Fit and transform
        scaler = Scaler()
        scaler.fit(self.data)
        
        transformed = scaler.transform(self.data)
        
        # Check transformed values for feature1 (range 1-5 -> 0-1)
        assert transformed["entity1"]["feature1"] == 0.0  # (1-1)/(5-1) = 0
        assert transformed["entity3"]["feature1"] == 0.5  # (3-1)/(5-1) = 0.5
        assert transformed["entity5"]["feature1"] == 1.0  # (5-1)/(5-1) = 1
        
        # Check transformed values for feature2 (range 10-50 -> 0-1)
        assert transformed["entity1"]["feature2"] == 0.0  # (10-10)/(50-10) = 0
        assert transformed["entity3"]["feature2"] == 0.5  # (30-10)/(50-10) = 0.5
        assert transformed["entity5"]["feature2"] == 1.0  # (50-10)/(50-10) = 1
        
        # Non-numeric features should remain unchanged
        assert transformed["entity1"]["text"] == "not_numeric"
        
        # Test with different feature range
        scaler = Scaler(feature_range=(-1, 1))
        scaler.fit(self.data)
        
        transformed = scaler.transform(self.data)
        
        # Values should be scaled to [-1, 1]
        assert transformed["entity1"]["feature1"] == -1.0  # min -> -1
        assert transformed["entity3"]["feature1"] == 0.0   # mid -> 0
        assert transformed["entity5"]["feature1"] == 1.0   # max -> 1
        
        # Test transform on specific features
        transformed = scaler.transform(self.data, feature_names=["feature1"])
        
        # feature1 should be scaled, feature2 should be unchanged
        assert transformed["entity1"]["feature1"] == -1.0
        assert transformed["entity1"]["feature2"] == 10
    
    def test_transform_without_fit(self):
        """Test that transform raises error when not fitted."""
        scaler = Scaler()
        
        with pytest.raises(ValueError):
            scaler.transform(self.data)
    
    def test_fit_transform(self):
        """Test combined fit and transform."""
        scaler = Scaler()
        
        transformed = scaler.fit_transform(self.data)
        
        # Check transformed values
        assert transformed["entity1"]["feature1"] == 0.0
        assert transformed["entity5"]["feature1"] == 1.0
        
        # Scaler should now be fitted
        assert scaler.fitted
    
    def test_get_set_params(self):
        """Test getting and setting parameters."""
        scaler = Scaler()
        scaler.fit(self.data)
        
        # Get parameters
        params = scaler.get_params()
        
        assert params["feature_range"] == (0, 1)
        assert "min_values" in params
        assert "max_values" in params
        
        # Set parameters
        new_params = {
            "feature_range": (-1, 1),
            "min_values": {"feature1": 0, "feature2": 0},
            "max_values": {"feature1": 10, "feature2": 100}
        }
        
        scaler.set_params(new_params)
        
        assert scaler._feature_range == (-1, 1)
        assert scaler._min_values == {"feature1": 0, "feature2": 0}
        assert scaler._max_values == {"feature1": 10, "feature2": 100}
        assert scaler.fitted  # Should be considered fitted now
    
    def test_serialization(self):
        """Test serialization to dictionary and JSON."""
        scaler = Scaler(feature_range=(-1, 1), name="CustomScaler")
        scaler.fit(self.data)
        
        # Convert to dictionary
        scaler_dict = scaler.to_dict()
        
        assert scaler_dict["name"] == "CustomScaler"
        assert scaler_dict["type"] == "Scaler"
        assert scaler_dict["fitted"] is True
        assert "params" in scaler_dict
        
        # Create from dictionary
        new_scaler = BaseOperation.from_dict(scaler_dict)
        
        assert isinstance(new_scaler, Scaler)
        assert new_scaler.name == "CustomScaler"
        assert new_scaler._feature_range == (-1, 1)
        assert new_scaler.fitted
        
        # Convert to JSON
        scaler_json = scaler.to_json()
        
        # Create from JSON
        new_scaler = BaseOperation.from_json(scaler_json)
        
        assert isinstance(new_scaler, Scaler)
        assert new_scaler.name == "CustomScaler"
        assert new_scaler.fitted


class TestNormalizer:
    """Tests for the Normalizer operation."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create test data
        self.data = {
            "entity1": {"feature1": 10, "feature2": 100, "text": "not_numeric"},
            "entity2": {"feature1": 20, "feature2": 200, "text": "not_numeric"},
            "entity3": {"feature1": 30, "feature2": 300, "text": "not_numeric"},
            "entity4": {"feature1": 40, "feature2": 400, "text": "not_numeric"},
            "entity5": {"feature1": 50, "feature2": 500, "text": "not_numeric"}
        }
    
    def test_fit(self):
        """Test fitting the normalizer."""
        normalizer = Normalizer()
        
        # Fit on all numeric features
        normalizer.fit(self.data)
        
        # Should compute mean and std for feature1 and feature2
        assert "feature1" in normalizer._means
        assert "feature2" in normalizer._means
        assert "text" not in normalizer._means
        
        # Mean of [10, 20, 30, 40, 50] is 30
        assert math.isclose(normalizer._means["feature1"], 30.0)
        # Mean of [100, 200, 300, 400, 500] is 300
        assert math.isclose(normalizer._means["feature2"], 300.0)

        # Std of [10, 20, 30, 40, 50] will vary based on std calculation method
        # Range is wider to accommodate population vs sample std differences
        assert 14.0 <= normalizer._stds["feature1"] <= 17.0
        # Std of [100, 200, 300, 400, 500] will also vary
        assert 140.0 <= normalizer._stds["feature2"] <= 170.0
        
        assert normalizer.fitted
    
    def test_transform(self):
        """Test transforming data with the normalizer."""
        # Fit and transform
        normalizer = Normalizer()
        normalizer.fit(self.data)
        
        transformed = normalizer.transform(self.data)
        
        # Check transformed values for feature1 (z-score normalization)
        # For (10 - 30) / std, expecting approximately -1.3 to -1.2
        assert -1.5 <= transformed["entity1"]["feature1"] <= -1.0
        # For (30 - 30) / std, expecting approximately 0
        assert -0.1 <= transformed["entity3"]["feature1"] <= 0.1
        # For (50 - 30) / std, expecting approximately 1.2 to 1.3
        assert 1.0 <= transformed["entity5"]["feature1"] <= 1.5
        
        # Non-numeric features should remain unchanged
        assert transformed["entity1"]["text"] == "not_numeric"
        
        # Test with zero standard deviation (edge case)
        data = {
            "entity1": {"constant": 5},
            "entity2": {"constant": 5}
        }
        
        normalizer = Normalizer()
        normalizer.fit(data)
        
        transformed = normalizer.transform(data)
        
        # Should not change values with zero std
        assert transformed["entity1"]["constant"] == 5
    
    def test_transform_without_fit(self):
        """Test that transform raises error when not fitted."""
        normalizer = Normalizer()
        
        with pytest.raises(ValueError):
            normalizer.transform(self.data)


class TestOneHotEncoder:
    """Tests for the OneHotEncoder operation."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create test data with categorical features
        self.data = {
            "entity1": {"category": "A", "color": "red", "value": 10},
            "entity2": {"category": "B", "color": "green", "value": 20},
            "entity3": {"category": "C", "color": "blue", "value": 30},
            "entity4": {"category": "A", "color": "green", "value": 40},
            "entity5": {"category": "B", "color": "red", "value": 50}
        }
    
    def test_fit(self):
        """Test fitting the encoder."""
        encoder = OneHotEncoder()
        
        # Fit on all features
        encoder.fit(self.data)
        
        # Should identify categorical features (category and color)
        assert "category" in encoder._categories
        assert "color" in encoder._categories
        assert "value" not in encoder._categories
        
        # Check categories
        assert set(encoder._categories["category"]) == {"A", "B", "C"}
        assert set(encoder._categories["color"]) == {"red", "green", "blue"}
        
        assert encoder.fitted
        
        # Fit on specific features
        encoder = OneHotEncoder()
        encoder.fit(self.data, feature_names=["category"])
        
        assert "category" in encoder._categories
        assert "color" not in encoder._categories
    
    def test_transform(self):
        """Test transforming data with the encoder."""
        # Fit and transform
        encoder = OneHotEncoder()
        encoder.fit(self.data)
        
        transformed = encoder.transform(self.data)
        
        # Check entity1 transformed values
        assert "category" not in transformed["entity1"]  # Original feature removed
        assert transformed["entity1"]["category_A"] == 1.0
        assert transformed["entity1"]["category_B"] == 0.0
        assert transformed["entity1"]["category_C"] == 0.0
        assert transformed["entity1"]["color_red"] == 1.0
        assert transformed["entity1"]["color_green"] == 0.0
        assert transformed["entity1"]["color_blue"] == 0.0
        
        # Numeric features should remain unchanged
        assert transformed["entity1"]["value"] == 10
        
        # Check entity3 transformed values
        assert transformed["entity3"]["category_A"] == 0.0
        assert transformed["entity3"]["category_B"] == 0.0
        assert transformed["entity3"]["category_C"] == 1.0
        assert transformed["entity3"]["color_red"] == 0.0
        assert transformed["entity3"]["color_green"] == 0.0
        assert transformed["entity3"]["color_blue"] == 1.0
        
        # Test transform on specific features
        transformed = encoder.transform(self.data, feature_names=["category"])
        
        # category should be encoded, color should remain unchanged
        assert "category_A" in transformed["entity1"]
        assert "color" in transformed["entity1"]  # Original feature still present
        assert "color_red" not in transformed["entity1"]
    
    def test_transform_without_fit(self):
        """Test that transform raises error when not fitted."""
        encoder = OneHotEncoder()
        
        with pytest.raises(ValueError):
            encoder.transform(self.data)
    
    def test_unknown_categories(self):
        """Test handling of unknown categories during transform."""
        encoder = OneHotEncoder()
        encoder.fit(self.data)
        
        # Create new data with an unknown category
        new_data = {
            "entity6": {"category": "D", "color": "yellow", "value": 60}
        }
        
        transformed = encoder.transform(new_data)
        
        # Unknown categories should result in all zeros
        assert transformed["entity6"]["category_A"] == 0.0
        assert transformed["entity6"]["category_B"] == 0.0
        assert transformed["entity6"]["category_C"] == 0.0
        assert transformed["entity6"]["color_red"] == 0.0
        assert transformed["entity6"]["color_green"] == 0.0
        assert transformed["entity6"]["color_blue"] == 0.0


class TestMissingValueImputer:
    """Tests for the MissingValueImputer operation."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create test data with missing values
        self.data = {
            "entity1": {"feature1": 10, "feature2": 100, "feature3": None},
            "entity2": {"feature1": 20, "feature2": None, "feature3": "A"},
            "entity3": {"feature1": 30, "feature2": 300, "feature3": "B"},
            "entity4": {"feature1": None, "feature2": 400, "feature3": None},
            "entity5": {"feature1": 50, "feature2": 500, "feature3": "C"}
        }
    
    def test_initialization(self):
        """Test MissingValueImputer initialization."""
        # Default initialization
        imputer = MissingValueImputer()
        assert imputer.name == "MissingValueImputer"
        assert imputer._strategy == "mean"
        assert imputer._fill_value is None
        
        # Custom initialization
        imputer = MissingValueImputer(strategy="constant", fill_value="MISSING")
        assert imputer._strategy == "constant"
        assert imputer._fill_value == "MISSING"
        
        # Invalid strategy
        with pytest.raises(ValueError):
            imputer = MissingValueImputer(strategy="invalid")
            imputer.fit(self.data)
    
    def test_fit_mean_strategy(self):
        """Test fitting with mean strategy."""
        imputer = MissingValueImputer(strategy="mean")
        
        # Fit on all features
        imputer.fit(self.data)
        
        # Should compute mean for numeric features
        assert "feature1" in imputer._imputation_values
        assert "feature2" in imputer._imputation_values
        assert "feature3" not in imputer._imputation_values  # Not numeric
        
        # Mean of [10, 20, 30, 50] is 27.5
        assert imputer._imputation_values["feature1"] == 27.5
        # Mean of [100, 300, 400, 500] is 325
        assert imputer._imputation_values["feature2"] == 325
        
        assert imputer.fitted
    
    def test_fit_median_strategy(self):
        """Test fitting with median strategy."""
        imputer = MissingValueImputer(strategy="median")
        
        # Fit on all features
        imputer.fit(self.data)
        
        # Median of [10, 20, 30, 50] is 25
        assert imputer._imputation_values["feature1"] == 25
        # Median of [100, 300, 400, 500] is 350
        assert imputer._imputation_values["feature2"] == 350
    
    def test_fit_constant_strategy(self):
        """Test fitting with constant strategy."""
        fill_value = 999
        imputer = MissingValueImputer(strategy="constant", fill_value=fill_value)
        
        # Fit on all features
        imputer.fit(self.data)
        
        # Should use the constant value for all features
        assert imputer._imputation_values["feature1"] == fill_value
        assert imputer._imputation_values["feature2"] == fill_value
        assert imputer._imputation_values["feature3"] == fill_value
    
    def test_transform(self):
        """Test transforming data with the imputer."""
        # Fit and transform with mean strategy
        imputer = MissingValueImputer(strategy="mean")
        imputer.fit(self.data)
        
        transformed = imputer.transform(self.data)
        
        # Check imputed values
        assert transformed["entity4"]["feature1"] == 27.5  # Imputed with mean
        assert transformed["entity2"]["feature2"] == 325   # Imputed with mean
        
        # Non-missing values should remain unchanged
        assert transformed["entity1"]["feature1"] == 10
        assert transformed["entity3"]["feature2"] == 300
        
        # Non-numeric features should not be imputed
        assert transformed["entity1"]["feature3"] is None
        assert transformed["entity4"]["feature3"] is None
        
        # Test with constant strategy
        imputer = MissingValueImputer(strategy="constant", fill_value="MISSING")
        imputer.fit(self.data)
        
        transformed = imputer.transform(self.data)
        
        # Check imputed values (all missing values should be replaced with constant)
        assert transformed["entity4"]["feature1"] == "MISSING"
        assert transformed["entity2"]["feature2"] == "MISSING"
        assert transformed["entity1"]["feature3"] == "MISSING"
        assert transformed["entity4"]["feature3"] == "MISSING"
    
    def test_transform_without_fit(self):
        """Test that transform raises error when not fitted."""
        imputer = MissingValueImputer()
        
        with pytest.raises(ValueError):
            imputer.transform(self.data)