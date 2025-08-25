"""
Feature transformation operations for preprocessing ML features.

This module provides common preprocessing operations for ML features,
such as scaling, normalization, encoding, and missing value imputation.
"""

import math
import statistics
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
import json


class BaseOperation:
    """
    Base class for feature transformation operations.
    
    This abstract class defines the interface for all transformation operations
    and provides common functionality for serialization and parameter management.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize a transformation operation.
        
        Args:
            name: Optional name for this operation
        """
        self._name = name or self.__class__.__name__
        self._fitted = False
    
    @property
    def name(self) -> str:
        """Get the name of this operation."""
        return self._name
    
    @property
    def fitted(self) -> bool:
        """Check if this operation has been fitted."""
        return self._fitted
    
    def fit(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> None:
        """
        Fit the operation parameters based on the data.
        
        Args:
            data: Data to fit the operation on, as entity_id -> feature_name -> value
            feature_names: Optional specific features to fit on
            
        Raises:
            NotImplementedError: If not implemented in a subclass
        """
        raise NotImplementedError("Subclasses must implement fit()")
    
    def transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Apply the transformation to the data.
        
        Args:
            data: Data to transform, as entity_id -> feature_name -> value
            feature_names: Optional specific features to transform
            
        Returns:
            Transformed data
            
        Raises:
            NotImplementedError: If not implemented in a subclass
        """
        raise NotImplementedError("Subclasses must implement transform()")
    
    def fit_transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fit the operation and then transform the data.
        
        Args:
            data: Data to fit and transform
            feature_names: Optional specific features to use
            
        Returns:
            Transformed data
        """
        self.fit(data, feature_names)
        return self.transform(data, feature_names)
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters of this operation.
        
        Returns:
            Dictionary of parameters
            
        Raises:
            NotImplementedError: If not implemented in a subclass
        """
        raise NotImplementedError("Subclasses must implement get_params()")
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Set the parameters of this operation.
        
        Args:
            params: Dictionary of parameters
            
        Raises:
            NotImplementedError: If not implemented in a subclass
        """
        raise NotImplementedError("Subclasses must implement set_params()")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this operation to a dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "name": self._name,
            "type": self.__class__.__name__,
            "fitted": self._fitted,
            "params": self.get_params()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseOperation':
        """
        Create an operation from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            A new operation instance
            
        Raises:
            ValueError: If the operation type is not recognized
        """
        op_type = data["type"]
        
        # Find the appropriate class
        if op_type == "Scaler":
            op = Scaler(name=data.get("name"))
        elif op_type == "Normalizer":
            op = Normalizer(name=data.get("name"))
        elif op_type == "OneHotEncoder":
            op = OneHotEncoder(name=data.get("name"))
        elif op_type == "MissingValueImputer":
            op = MissingValueImputer(name=data.get("name"))
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
        
        # Set parameters and fitted state
        op.set_params(data["params"])
        op._fitted = data["fitted"]
        
        return op
    
    def to_json(self) -> str:
        """
        Convert this operation to a JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseOperation':
        """
        Create an operation from a JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            A new operation instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


class Scaler(BaseOperation):
    """
    Scales numeric features to a specific range.
    
    This operation scales numeric features to be within a specified range,
    typically [0, 1] or [-1, 1], based on observed min and max values.
    """
    
    def __init__(
        self,
        feature_range: Tuple[float, float] = (0, 1),
        name: Optional[str] = None
    ):
        """
        Initialize a scaler.
        
        Args:
            feature_range: (min, max) range to scale to
            name: Optional name for this operation
        """
        super().__init__(name)
        self._feature_range = feature_range
        self._min_values: Dict[str, float] = {}
        self._max_values: Dict[str, float] = {}
    
    def fit(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> None:
        """
        Fit the scaler by computing min and max values.
        
        Args:
            data: Data to fit the scaler on
            feature_names: Optional specific features to fit on
        """
        if feature_names is None:
            # Extract all numeric feature names from the data
            all_features = set()
            for entity_features in data.values():
                all_features.update(entity_features.keys())
            
            # Filter out non-numeric features
            feature_names = []
            for feature in all_features:
                # Sample a non-None value for this feature
                sample_value = None
                for entity_id, entity_features in data.items():
                    if feature in entity_features and entity_features[feature] is not None:
                        sample_value = entity_features[feature]
                        break
                
                # Check if it's numeric
                if sample_value is not None and isinstance(sample_value, (int, float)):
                    feature_names.append(feature)
        
        # Compute min and max for each feature
        for feature in feature_names:
            values = []
            for entity_id, entity_features in data.items():
                if feature in entity_features and entity_features[feature] is not None:
                    value = entity_features[feature]
                    if isinstance(value, (int, float)):
                        values.append(value)
            
            if values:
                self._min_values[feature] = min(values)
                self._max_values[feature] = max(values)
        
        self._fitted = True
    
    def transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Scale the data.
        
        Args:
            data: Data to scale
            feature_names: Optional specific features to scale
            
        Returns:
            Scaled data
            
        Raises:
            ValueError: If the scaler has not been fitted
        """
        if not self._fitted:
            raise ValueError("Scaler must be fitted before transforming data")
        
        # If no feature names provided, use all fitted features
        if feature_names is None:
            feature_names = list(self._min_values.keys())
        
        # Scale each entity's features
        result = {}
        for entity_id, entity_features in data.items():
            result[entity_id] = entity_features.copy()
            
            for feature in feature_names:
                if feature in entity_features and feature in self._min_values:
                    value = entity_features[feature]
                    
                    if value is not None and isinstance(value, (int, float)):
                        min_val = self._min_values[feature]
                        max_val = self._max_values[feature]
                        
                        if max_val > min_val:  # Avoid division by zero
                            # Scale to [0, 1]
                            scaled = (value - min_val) / (max_val - min_val)
                            
                            # Scale to feature_range
                            a, b = self._feature_range
                            scaled = a + (b - a) * scaled
                            
                            result[entity_id][feature] = scaled
        
        return result
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters of this scaler.
        
        Returns:
            Dictionary of parameters
        """
        return {
            "feature_range": self._feature_range,
            "min_values": self._min_values,
            "max_values": self._max_values
        }
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Set the parameters of this scaler.
        
        Args:
            params: Dictionary of parameters
        """
        if "feature_range" in params:
            self._feature_range = params["feature_range"]
        if "min_values" in params:
            self._min_values = params["min_values"]
        if "max_values" in params:
            self._max_values = params["max_values"]
            
        # If we have min and max values, consider it fitted
        if self._min_values and self._max_values:
            self._fitted = True


class Normalizer(BaseOperation):
    """
    Normalizes features to have zero mean and unit variance.
    
    This operation transforms features to have zero mean and unit variance
    (standard normalization or z-score normalization).
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize a normalizer.
        
        Args:
            name: Optional name for this operation
        """
        super().__init__(name)
        self._means: Dict[str, float] = {}
        self._stds: Dict[str, float] = {}
    
    def fit(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> None:
        """
        Fit the normalizer by computing means and standard deviations.
        
        Args:
            data: Data to fit the normalizer on
            feature_names: Optional specific features to fit on
        """
        if feature_names is None:
            # Extract all numeric feature names from the data
            all_features = set()
            for entity_features in data.values():
                all_features.update(entity_features.keys())
            
            # Filter out non-numeric features
            feature_names = []
            for feature in all_features:
                # Sample a non-None value for this feature
                sample_value = None
                for entity_id, entity_features in data.items():
                    if feature in entity_features and entity_features[feature] is not None:
                        sample_value = entity_features[feature]
                        break
                
                # Check if it's numeric
                if sample_value is not None and isinstance(sample_value, (int, float)):
                    feature_names.append(feature)
        
        # Compute mean and std for each feature
        for feature in feature_names:
            values = []
            for entity_id, entity_features in data.items():
                if feature in entity_features and entity_features[feature] is not None:
                    value = entity_features[feature]
                    if isinstance(value, (int, float)):
                        values.append(value)
            
            if values:
                self._means[feature] = statistics.mean(values)
                
                # Use population std (not sample std) for consistency
                self._stds[feature] = statistics.pstdev(values)
        
        self._fitted = True
    
    def transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Normalize the data.
        
        Args:
            data: Data to normalize
            feature_names: Optional specific features to normalize
            
        Returns:
            Normalized data
            
        Raises:
            ValueError: If the normalizer has not been fitted
        """
        if not self._fitted:
            raise ValueError("Normalizer must be fitted before transforming data")
        
        # If no feature names provided, use all fitted features
        if feature_names is None:
            feature_names = list(self._means.keys())
        
        # Normalize each entity's features
        result = {}
        for entity_id, entity_features in data.items():
            result[entity_id] = entity_features.copy()
            
            for feature in feature_names:
                if feature in entity_features and feature in self._means:
                    value = entity_features[feature]
                    
                    if value is not None and isinstance(value, (int, float)):
                        mean = self._means[feature]
                        std = self._stds[feature]
                        
                        if not math.isclose(std, 0):  # Avoid division by zero
                            normalized = (value - mean) / std
                            result[entity_id][feature] = normalized
        
        return result
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters of this normalizer.
        
        Returns:
            Dictionary of parameters
        """
        return {
            "means": self._means,
            "stds": self._stds
        }
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Set the parameters of this normalizer.
        
        Args:
            params: Dictionary of parameters
        """
        if "means" in params:
            self._means = params["means"]
        if "stds" in params:
            self._stds = params["stds"]
            
        # If we have means and stds, consider it fitted
        if self._means and self._stds:
            self._fitted = True


class OneHotEncoder(BaseOperation):
    """
    Encodes categorical features as one-hot vectors.
    
    This operation transforms categorical features into a one-hot encoded
    representation, where each category becomes a binary feature.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize a one-hot encoder.
        
        Args:
            name: Optional name for this operation
        """
        super().__init__(name)
        self._categories: Dict[str, List[Any]] = {}
    
    def fit(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> None:
        """
        Fit the encoder by learning the categories for each feature.
        
        Args:
            data: Data to fit the encoder on
            feature_names: Optional specific features to fit on
        """
        if feature_names is None:
            # Extract all feature names from the data
            all_features = set()
            for entity_features in data.values():
                all_features.update(entity_features.keys())
            
            # Filter out numeric features (we'll assume anything else is categorical)
            feature_names = []
            for feature in all_features:
                # Sample a non-None value for this feature
                sample_value = None
                for entity_id, entity_features in data.items():
                    if feature in entity_features and entity_features[feature] is not None:
                        sample_value = entity_features[feature]
                        break
                
                # Check if it's non-numeric or a string (categorical)
                if sample_value is not None and (
                    isinstance(sample_value, str) or 
                    (not isinstance(sample_value, (int, float)))
                ):
                    feature_names.append(feature)
        
        # Find unique categories for each feature
        for feature in feature_names:
            categories = set()
            for entity_id, entity_features in data.items():
                if feature in entity_features and entity_features[feature] is not None:
                    # For consistent serialization, convert non-primitive types to strings
                    value = entity_features[feature]
                    if not isinstance(value, (str, int, float, bool)):
                        value = str(value)
                    categories.add(value)
            
            if categories:
                # Sort categories for consistent ordering
                self._categories[feature] = sorted(categories)
        
        self._fitted = True
    
    def transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Encode the data.
        
        Args:
            data: Data to encode
            feature_names: Optional specific features to encode
            
        Returns:
            Encoded data
            
        Raises:
            ValueError: If the encoder has not been fitted
        """
        if not self._fitted:
            raise ValueError("OneHotEncoder must be fitted before transforming data")
        
        # If no feature names provided, use all fitted features
        if feature_names is None:
            feature_names = list(self._categories.keys())
        
        # Encode each entity's features
        result = {}
        for entity_id, entity_features in data.items():
            result[entity_id] = entity_features.copy()
            
            for feature in feature_names:
                if feature in entity_features and feature in self._categories:
                    value = entity_features[feature]
                    
                    # Skip None values
                    if value is None:
                        continue
                    
                    # For consistent lookup, convert non-primitive types to strings
                    if not isinstance(value, (str, int, float, bool)):
                        value = str(value)
                    
                    # Remove the original feature
                    del result[entity_id][feature]
                    
                    # Add one-hot encoded features
                    for category in self._categories[feature]:
                        encoded_feature = f"{feature}_{category}"
                        result[entity_id][encoded_feature] = 1.0 if value == category else 0.0
        
        return result
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters of this encoder.
        
        Returns:
            Dictionary of parameters
        """
        return {
            "categories": self._categories
        }
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Set the parameters of this encoder.
        
        Args:
            params: Dictionary of parameters
        """
        if "categories" in params:
            self._categories = params["categories"]
            
        # If we have categories, consider it fitted
        if self._categories:
            self._fitted = True


class MissingValueImputer(BaseOperation):
    """
    Imputes missing values in features.
    
    This operation replaces missing (None) values with imputed values
    based on a strategy like mean, median, or constant.
    """
    
    def __init__(
        self,
        strategy: str = "mean",
        fill_value: Optional[Any] = None,
        name: Optional[str] = None
    ):
        """
        Initialize a missing value imputer.
        
        Args:
            strategy: Imputation strategy ('mean', 'median', 'constant')
            fill_value: Value to use with 'constant' strategy
            name: Optional name for this operation
        """
        super().__init__(name)
        self._strategy = strategy
        self._fill_value = fill_value
        self._imputation_values: Dict[str, Any] = {}
    
    def fit(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> None:
        """
        Fit the imputer by computing imputation values.
        
        Args:
            data: Data to fit the imputer on
            feature_names: Optional specific features to fit on
            
        Raises:
            ValueError: If the strategy is invalid
        """
        if self._strategy not in ("mean", "median", "constant"):
            raise ValueError(f"Unknown imputation strategy: {self._strategy}")
        
        if feature_names is None:
            # Extract all feature names from the data
            all_features = set()
            for entity_features in data.values():
                all_features.update(entity_features.keys())
            feature_names = list(all_features)
        
        # Compute imputation values for each feature
        for feature in feature_names:
            if self._strategy == "constant":
                self._imputation_values[feature] = self._fill_value
            else:
                # Collect non-missing values
                values = []
                for entity_id, entity_features in data.items():
                    if feature in entity_features and entity_features[feature] is not None:
                        value = entity_features[feature]
                        if isinstance(value, (int, float)):
                            values.append(value)
                
                if values:
                    if self._strategy == "mean":
                        self._imputation_values[feature] = statistics.mean(values)
                    elif self._strategy == "median":
                        self._imputation_values[feature] = statistics.median(values)
        
        self._fitted = True
    
    def transform(self, data: Dict[str, Dict[str, Any]], feature_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Impute missing values in the data.
        
        Args:
            data: Data to impute
            feature_names: Optional specific features to impute
            
        Returns:
            Imputed data
            
        Raises:
            ValueError: If the imputer has not been fitted
        """
        if not self._fitted:
            raise ValueError("MissingValueImputer must be fitted before transforming data")
        
        # If no feature names provided, use all fitted features
        if feature_names is None:
            feature_names = list(self._imputation_values.keys())
        
        # Impute each entity's features
        result = {}
        for entity_id, entity_features in data.items():
            result[entity_id] = entity_features.copy()
            
            for feature in feature_names:
                if feature in entity_features and feature in self._imputation_values:
                    value = entity_features[feature]
                    
                    if value is None:
                        result[entity_id][feature] = self._imputation_values[feature]
        
        return result
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters of this imputer.
        
        Returns:
            Dictionary of parameters
        """
        return {
            "strategy": self._strategy,
            "fill_value": self._fill_value,
            "imputation_values": self._imputation_values
        }
    
    def set_params(self, params: Dict[str, Any]) -> None:
        """
        Set the parameters of this imputer.
        
        Args:
            params: Dictionary of parameters
        """
        if "strategy" in params:
            self._strategy = params["strategy"]
        if "fill_value" in params:
            self._fill_value = params["fill_value"]
        if "imputation_values" in params:
            self._imputation_values = params["imputation_values"]
            
        # If we have imputation values, consider it fitted
        if self._imputation_values:
            self._fitted = True