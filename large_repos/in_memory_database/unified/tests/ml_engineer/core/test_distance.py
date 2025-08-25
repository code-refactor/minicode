"""
Tests for the distance metrics used for vector comparisons.
"""

import pytest
import math
from vectordb.core.vector import Vector
from vectordb.core.distance import (
    euclidean_distance, 
    squared_euclidean_distance,
    manhattan_distance, 
    cosine_distance, 
    cosine_similarity,
    angular_distance,
    chebyshev_distance,
    get_distance_function,
    DISTANCE_METRICS
)


class TestDistanceMetrics:
    """Tests for the distance metrics module."""
    
    def setup_method(self):
        """Set up test vectors for each test."""
        # Define test vectors
        self.v1 = Vector([1.0, 0.0, 0.0])  # Unit vector along x-axis
        self.v2 = Vector([0.0, 1.0, 0.0])  # Unit vector along y-axis
        self.v3 = Vector([0.0, 0.0, 1.0])  # Unit vector along z-axis
        self.v4 = Vector([1.0, 1.0, 1.0])  # Vector pointing to (1,1,1)
        self.v5 = Vector([-1.0, -1.0, -1.0])  # Vector pointing to (-1,-1,-1)
        self.v6 = Vector([3.0, 4.0, 0.0])  # Vector with magnitude 5
        self.v7 = Vector([0.0, 0.0, 0.0])  # Zero vector
        
        # These vectors have the same direction but different magnitudes
        self.v8 = Vector([2.0, 0.0, 0.0])
        self.v9 = Vector([4.0, 0.0, 0.0])
    
    def test_euclidean_distance(self):
        """Test Euclidean (L2) distance."""
        # Distance between orthogonal unit vectors should be sqrt(2)
        assert math.isclose(euclidean_distance(self.v1, self.v2), math.sqrt(2))
        
        # Distance from origin to (3,4,0) should be 5
        assert math.isclose(euclidean_distance(self.v7, self.v6), 5.0)
        
        # Distance from (1,1,1) to (-1,-1,-1) should be 2*sqrt(3)
        assert math.isclose(euclidean_distance(self.v4, self.v5), 2*math.sqrt(3))
        
        # Distance from (1,0,0) to (2,0,0) should be 1
        assert math.isclose(euclidean_distance(self.v1, self.v8), 1.0)
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            euclidean_distance(self.v1, v_different)
    
    def test_squared_euclidean_distance(self):
        """Test squared Euclidean distance."""
        # Squared distance between orthogonal unit vectors should be 2
        assert math.isclose(squared_euclidean_distance(self.v1, self.v2), 2.0)
        
        # Squared distance from origin to (3,4,0) should be 25
        assert math.isclose(squared_euclidean_distance(self.v7, self.v6), 25.0)
        
        # Compare with euclidean_distance squared
        for va, vb in [(self.v1, self.v2), (self.v4, self.v5), (self.v7, self.v6)]:
            euc = euclidean_distance(va, vb)
            sqr_euc = squared_euclidean_distance(va, vb)
            assert math.isclose(sqr_euc, euc * euc)
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            squared_euclidean_distance(self.v1, v_different)
    
    def test_manhattan_distance(self):
        """Test Manhattan (L1) distance."""
        # Manhattan distance between (1,0,0) and (0,1,0) should be 2
        assert manhattan_distance(self.v1, self.v2) == 2.0
        
        # Manhattan distance from origin to (3,4,0) should be 7
        assert manhattan_distance(self.v7, self.v6) == 7.0
        
        # Manhattan distance from (1,1,1) to (-1,-1,-1) should be 6
        assert manhattan_distance(self.v4, self.v5) == 6.0
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            manhattan_distance(self.v1, v_different)
    
    def test_cosine_distance_and_similarity(self):
        """Test cosine distance and similarity."""
        # Orthogonal vectors should have similarity 0 and distance 1
        assert math.isclose(cosine_similarity(self.v1, self.v2), 0.0)
        assert math.isclose(cosine_distance(self.v1, self.v2), 1.0)
        
        # Same direction vectors should have similarity 1 and distance 0
        assert math.isclose(cosine_similarity(self.v1, self.v8), 1.0)
        assert math.isclose(cosine_distance(self.v1, self.v8), 0.0)
        
        # Same direction but different magnitude
        assert math.isclose(cosine_similarity(self.v8, self.v9), 1.0)
        assert math.isclose(cosine_distance(self.v8, self.v9), 0.0)
        
        # Opposite direction vectors should have similarity -1 and distance 2
        assert math.isclose(cosine_similarity(self.v4, self.v5), -1.0)
        assert math.isclose(cosine_distance(self.v4, self.v5), 2.0)
        
        # Test with zero vector (should raise error)
        with pytest.raises(ValueError):
            cosine_similarity(self.v1, self.v7)
        
        with pytest.raises(ValueError):
            cosine_distance(self.v1, self.v7)
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            cosine_similarity(self.v1, v_different)
    
    def test_angular_distance(self):
        """Test angular distance."""
        # Orthogonal vectors should have angle π/2 (90 degrees)
        assert math.isclose(angular_distance(self.v1, self.v2), math.pi/2)
        
        # Same direction vectors should have angle 0
        assert math.isclose(angular_distance(self.v1, self.v8), 0.0)
        
        # Opposite direction vectors should have angle π (180 degrees)
        assert math.isclose(angular_distance(self.v4, self.v5), math.pi)
        
        # Test with zero vector (should raise error)
        with pytest.raises(ValueError):
            angular_distance(self.v1, self.v7)
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            angular_distance(self.v1, v_different)
    
    def test_chebyshev_distance(self):
        """Test Chebyshev (L∞) distance."""
        # Chebyshev distance between (1,0,0) and (0,1,0) should be 1
        assert chebyshev_distance(self.v1, self.v2) == 1.0
        
        # Chebyshev distance from origin to (3,4,0) should be 4
        assert chebyshev_distance(self.v7, self.v6) == 4.0
        
        # Chebyshev distance from (1,1,1) to (-1,-1,-1) should be 2
        assert chebyshev_distance(self.v4, self.v5) == 2.0
        
        # Test with different dimensions (should raise error)
        v_different = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            chebyshev_distance(self.v1, v_different)
    
    def test_get_distance_function(self):
        """Test getting distance functions by name."""
        # Test getting each distance function by name
        assert get_distance_function("euclidean") == euclidean_distance
        assert get_distance_function("squared_euclidean") == squared_euclidean_distance
        assert get_distance_function("manhattan") == manhattan_distance
        assert get_distance_function("cosine") == cosine_distance
        assert get_distance_function("angular") == angular_distance
        assert get_distance_function("chebyshev") == chebyshev_distance
        
        # Test case insensitivity
        assert get_distance_function("EUCLIDEAN") == euclidean_distance
        assert get_distance_function("Manhattan") == manhattan_distance
        
        # Test invalid metric name
        with pytest.raises(ValueError):
            get_distance_function("invalid_metric")
    
    def test_distance_metrics_dictionary(self):
        """Test the DISTANCE_METRICS dictionary."""
        # Check all expected metrics are in the dictionary
        expected_metrics = [
            "euclidean",
            "squared_euclidean",
            "manhattan",
            "cosine",
            "angular",
            "chebyshev"
        ]
        
        for metric in expected_metrics:
            assert metric in DISTANCE_METRICS
            assert callable(DISTANCE_METRICS[metric])
        
        # Test that all functions in the dictionary work
        for metric_name, distance_fn in DISTANCE_METRICS.items():
            # Use non-zero vectors to avoid errors with cosine and angular
            distance = distance_fn(self.v1, self.v2)
            assert isinstance(distance, float)
            assert distance >= 0  # All distances should be non-negative