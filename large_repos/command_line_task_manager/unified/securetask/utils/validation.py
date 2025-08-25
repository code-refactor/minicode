"""Validation utilities for SecureTask."""

import re
import os
from typing import Any, Dict, List, Optional, Union, Callable

from pydantic import BaseModel, field_validator
from pydantic import ValidationError as PydanticValidationError
from common.core import ValidationError as CommonValidationError


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        self.message = message
        super().__init__(f"{field + ': ' if field else ''}{message}")
    
    @classmethod
    def from_common(cls, common_error: CommonValidationError) -> 'ValidationError':
        """Create a ValidationError from a common library ValidationError."""
        return cls(message=common_error.message, field=common_error.field)
    
    def to_common(self) -> CommonValidationError:
        """Convert this ValidationError to a common library ValidationError."""
        return CommonValidationError(field=self.field, message=self.message)


def validate_file_size(file_path: str, max_size_mb: int = 100) -> bool:
    """
    Validate that a file does not exceed the maximum allowed size.
    
    Args:
        file_path: Path to the file to check
        max_size_mb: Maximum allowed size in megabytes
        
    Returns:
        True if the file is within size limits
        
    Raises:
        ValidationError: If the file is too large
        FileNotFoundError: If the file does not exist
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    
    if file_size > max_size_bytes:
        raise ValidationError(
            f"File exceeds maximum size of {max_size_mb}MB (actual: {file_size / 1024 / 1024:.2f}MB)",
            "file_size"
        )
    
    return True


def validate_cvss_metric(value: str, allowed_values: List[str], metric_name: str) -> str:
    """
    Validate that a CVSS metric value is allowed.
    
    Args:
        value: The metric value to validate
        allowed_values: List of allowed values for this metric
        metric_name: Name of the metric being validated
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If the value is not in the allowed values
    """
    if value not in allowed_values:
        raise ValidationError(
            f"Invalid value '{value}' for {metric_name}. Allowed values: {', '.join(allowed_values)}",
            metric_name
        )
    
    return value