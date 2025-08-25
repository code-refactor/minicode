"""Tests for the Validation Utilities module."""

import os
import tempfile
import pytest
from pydantic import BaseModel, field_validator

from securetask.utils.validation import ValidationError, validate_file_size, validate_cvss_metric


def test_validation_error():
    """Test the custom ValidationError class."""
    # Test with field
    error = ValidationError("Invalid value", "field_name")
    assert error.message == "Invalid value"
    assert error.field == "field_name"
    assert str(error) == "field_name: Invalid value"
    
    # Test without field
    error = ValidationError("General error")
    assert error.message == "General error"
    assert error.field is None
    assert str(error) == "General error"


def test_validate_file_size():
    """Test the validate_file_size function."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        # Write 500KB of data
        temp_file.write(b'0' * (500 * 1024))
        file_path = temp_file.name
    
    try:
        # Test with file size within limit (default 100MB)
        assert validate_file_size(file_path) is True
        
        # Test with custom limit that file exceeds (0.4MB)
        with pytest.raises(ValidationError, match="File exceeds maximum size"):
            validate_file_size(file_path, max_size_mb=0.4)
        
        # Test with custom limit that file is within (0.6MB)
        assert validate_file_size(file_path, max_size_mb=0.6) is True
        
        # Test with non-existent file
        non_existent_path = file_path + ".nonexistent"
        with pytest.raises(FileNotFoundError):
            validate_file_size(non_existent_path)
    finally:
        # Clean up the temporary file
        os.unlink(file_path)


def test_validate_cvss_metric():
    """Test the validate_cvss_metric function."""
    # Valid inputs
    assert validate_cvss_metric("L", ["L", "M", "H"], "complexity") == "L"
    assert validate_cvss_metric("M", ["L", "M", "H"], "complexity") == "M"
    assert validate_cvss_metric("H", ["L", "M", "H"], "complexity") == "H"
    
    # Invalid inputs
    with pytest.raises(ValidationError, match="Invalid value 'X' for complexity"):
        validate_cvss_metric("X", ["L", "M", "H"], "complexity")
    
    with pytest.raises(ValidationError, match="Invalid value 'LOW' for complexity"):
        validate_cvss_metric("LOW", ["L", "M", "H"], "complexity")
    
    # Test with empty allowed values
    with pytest.raises(ValidationError):
        validate_cvss_metric("L", [], "complexity")
    
    # Test case sensitivity
    with pytest.raises(ValidationError):
        validate_cvss_metric("l", ["L", "M", "H"], "complexity")


def test_validation_with_pydantic():
    """Test integration with Pydantic models."""
    # Create a test class that uses ValidationError
    class TestModel(BaseModel):
        attack_vector: str
        
        @field_validator('attack_vector')
        def validate_attack_vector(cls, v):
            try:
                return validate_cvss_metric(v, ["N", "A", "L", "P"], "attack_vector")
            except ValidationError as e:
                # Convert to Pydantic's ValidationError
                raise ValueError(str(e))
    
    # Test valid input
    model = TestModel(attack_vector="N")
    assert model.attack_vector == "N"
    
    # Test invalid input
    with pytest.raises(ValueError):
        TestModel(attack_vector="X")


def test_validate_file_size_edge_cases():
    """Test edge cases for the validate_file_size function."""
    # Create temporary files for testing
    with tempfile.NamedTemporaryFile(delete=False) as empty_file:
        empty_path = empty_file.name
        
    with tempfile.NamedTemporaryFile(delete=False) as small_file:
        small_file.write(b'1')
        small_path = small_file.name
    
    try:
        # Test with empty file
        assert validate_file_size(empty_path) is True
        
        # Test with very small file
        assert validate_file_size(small_path) is True
        
        # Test with zero size limit
        with pytest.raises(ValidationError):
            validate_file_size(small_path, max_size_mb=0)
        
        # Test with negative size limit (should be treated as 0)
        with pytest.raises(ValidationError):
            validate_file_size(small_path, max_size_mb=-1)
    finally:
        # Clean up the temporary files
        os.unlink(empty_path)
        os.unlink(small_path)


def test_validate_cvss_metric_performance():
    """Test the performance of validate_cvss_metric function."""
    import time
    
    # Define test parameters
    metric_name = "complexity"
    allowed_values = ["L", "M", "H"]
    valid_value = "M"
    
    # Measure time for a valid call
    start_time = time.time()
    for _ in range(1000):  # Run 1000 validations
        validate_cvss_metric(valid_value, allowed_values, metric_name)
    
    execution_time = time.time() - start_time
    
    # This should be very fast, less than 0.1 seconds for 1000 iterations
    assert execution_time < 0.1, f"1000 validations took {execution_time:.4f}s, should be <0.1s"


def test_validation_error_inheritance():
    """Test that ValidationError properly inherits from Exception."""
    error = ValidationError("Test error")
    
    # Should be instance of Exception
    assert isinstance(error, Exception)
    
    # Should be catchable as an Exception
    try:
        raise ValidationError("Test error")
    except Exception as e:
        assert str(e) == "Test error"
        
    # Should have a proper traceback
    try:
        raise ValidationError("Test error")
    except ValidationError as e:
        import traceback
        tb = traceback.format_exc()
        assert "ValidationError: Test error" in tb