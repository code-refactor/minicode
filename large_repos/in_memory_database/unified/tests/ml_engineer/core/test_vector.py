"""
Tests for the Vector data type implementation.
"""

import pytest
import math
import json
from vectordb.core.vector import Vector


class TestVector:
    """Tests for the Vector class."""

    def test_vector_initialization(self):
        """Test vector initialization with various inputs."""
        # Test with list of values
        v1 = Vector([1.0, 2.0, 3.0])
        assert v1.dimension == 3
        assert v1.values == (1.0, 2.0, 3.0)
        assert v1.id is None

        # Test with tuple of values
        v2 = Vector((4.0, 5.0, 6.0))
        assert v2.dimension == 3
        assert v2.values == (4.0, 5.0, 6.0)

        # Test with ID
        v3 = Vector([7.0, 8.0, 9.0], id="test_id")
        assert v3.id == "test_id"
        
        # Test with integer values (should be converted to float)
        v4 = Vector([1, 2, 3])
        assert v4.values == (1.0, 2.0, 3.0)
        
        # Test empty vector (should raise error)
        with pytest.raises(ValueError):
            Vector([])
        
        # Test non-numeric values (should raise error)
        with pytest.raises(ValueError):
            Vector(["a", "b", "c"])

    def test_vector_properties(self):
        """Test vector properties."""
        v = Vector([1.0, 2.0, 3.0], id="test_vector")
        
        assert v.id == "test_vector"
        assert v.dimension == 3
        assert v.values == (1.0, 2.0, 3.0)
        assert len(v) == 3

    def test_vector_indexing_and_iteration(self):
        """Test vector indexing and iteration."""
        v = Vector([1.0, 2.0, 3.0])
        
        # Test indexing
        assert v[0] == 1.0
        assert v[1] == 2.0
        assert v[2] == 3.0
        
        # Test iteration
        values = [val for val in v]
        assert values == [1.0, 2.0, 3.0]

    def test_vector_equality(self):
        """Test vector equality."""
        v1 = Vector([1.0, 2.0, 3.0])
        v2 = Vector([1.0, 2.0, 3.0])
        v3 = Vector([4.0, 5.0, 6.0])
        v4 = Vector([1.0, 2.0, 3.0], id="test_id")
        
        # Equal vectors
        assert v1 == v2
        
        # Different vectors
        assert v1 != v3
        
        # Same values but different ID (still equal by value)
        assert v1 == v4
        
        # Non-vector comparison
        assert v1 != "not a vector"

    def test_dot_product(self):
        """Test vector dot product calculation."""
        v1 = Vector([1.0, 2.0, 3.0])
        v2 = Vector([4.0, 5.0, 6.0])
        
        # Calculate dot product: 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        dot = v1.dot(v2)
        assert dot == 32.0
        
        # Test with different dimensions (should raise error)
        v3 = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            v1.dot(v3)

    def test_magnitude(self):
        """Test vector magnitude calculation."""
        v = Vector([3.0, 4.0])
        
        # Calculate magnitude: sqrt(3^2 + 4^2) = sqrt(9 + 16) = sqrt(25) = 5
        mag = v.magnitude()
        assert mag == 5.0
        
        # Test zero vector
        v_zero = Vector([0.0, 0.0, 0.0])
        assert v_zero.magnitude() == 0.0

    def test_normalize(self):
        """Test vector normalization."""
        v = Vector([3.0, 4.0])
        
        # Normalize to unit vector
        unit_v = v.normalize()
        
        # Check magnitude is 1.0 (within floating point tolerance)
        assert math.isclose(unit_v.magnitude(), 1.0)
        
        # Check values: [3/5, 4/5] = [0.6, 0.8]
        assert math.isclose(unit_v[0], 0.6)
        assert math.isclose(unit_v[1], 0.8)
        
        # Test zero vector (should raise error)
        v_zero = Vector([0.0, 0.0, 0.0])
        with pytest.raises(ValueError):
            v_zero.normalize()

    def test_vector_addition(self):
        """Test vector addition."""
        v1 = Vector([1.0, 2.0, 3.0])
        v2 = Vector([4.0, 5.0, 6.0])
        
        # Add vectors: [1+4, 2+5, 3+6] = [5, 7, 9]
        v_sum = v1.add(v2)
        assert v_sum.values == (5.0, 7.0, 9.0)
        
        # Test with different dimensions (should raise error)
        v3 = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            v1.add(v3)

    def test_vector_subtraction(self):
        """Test vector subtraction."""
        v1 = Vector([5.0, 7.0, 9.0])
        v2 = Vector([1.0, 2.0, 3.0])
        
        # Subtract vectors: [5-1, 7-2, 9-3] = [4, 5, 6]
        v_diff = v1.subtract(v2)
        assert v_diff.values == (4.0, 5.0, 6.0)
        
        # Test with different dimensions (should raise error)
        v3 = Vector([1.0, 2.0])
        with pytest.raises(ValueError):
            v1.subtract(v3)

    def test_vector_scaling(self):
        """Test vector scaling."""
        v = Vector([1.0, 2.0, 3.0])
        
        # Scale by 2: [1*2, 2*2, 3*2] = [2, 4, 6]
        v_scaled = v.scale(2.0)
        assert v_scaled.values == (2.0, 4.0, 6.0)
        
        # Scale by 0: [1*0, 2*0, 3*0] = [0, 0, 0]
        v_zero = v.scale(0.0)
        assert v_zero.values == (0.0, 0.0, 0.0)
        
        # Scale by negative: [1*(-1), 2*(-1), 3*(-1)] = [-1, -2, -3]
        v_negative = v.scale(-1.0)
        assert v_negative.values == (-1.0, -2.0, -3.0)

    def test_serialization(self):
        """Test vector serialization and deserialization."""
        v = Vector([1.0, 2.0, 3.0], id="test_id")
        
        # Convert to dictionary
        v_dict = v.to_dict()
        assert v_dict["values"] == [1.0, 2.0, 3.0]
        assert v_dict["id"] == "test_id"
        
        # Deserialize from dictionary
        v_from_dict = Vector.from_dict(v_dict)
        assert v_from_dict == v
        
        # Convert to JSON
        v_json = v.to_json()
        assert isinstance(v_json, str)
        
        # Deserialize from JSON
        v_from_json = Vector.from_json(v_json)
        assert v_from_json == v
        
        # Test missing values (should raise error)
        with pytest.raises(ValueError):
            Vector.from_dict({"id": "test_id"})
            
        # Test invalid JSON (should raise error)
        with pytest.raises(ValueError):
            Vector.from_json("not a json string")

    def test_string_representation(self):
        """Test string representation of vectors."""
        # Short vector
        v1 = Vector([1.0, 2.0, 3.0], id="test_id")
        str_rep = str(v1)
        assert "test_id" in str_rep
        assert "1.0" in str_rep
        assert "2.0" in str_rep
        assert "3.0" in str_rep
        
        # Vector without ID
        v2 = Vector([1.0, 2.0, 3.0])
        str_rep = str(v2)
        assert "id" not in str_rep
        
        # Long vector (should be truncated in string representation)
        v3 = Vector([float(i) for i in range(100)])
        str_rep = str(v3)
        assert "..." in str_rep
        assert len(str_rep) < 1000  # String should be reasonably short