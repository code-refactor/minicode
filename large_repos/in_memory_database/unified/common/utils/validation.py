"""Data validation utilities for the unified library."""

from typing import Any, Dict, List, Optional, Union, Callable, Type, Set, Tuple
from dataclasses import dataclass, field
import re
from datetime import datetime, date
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
            value: Value that failed validation
        """
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.field:
            return f"Validation error for field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


@dataclass
class ValidationRule:
    """Represents a validation rule."""
    name: str
    validator: Callable[[Any], bool]
    error_message: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against this rule.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if self.validator(value):
                return True, None
            else:
                return False, self.error_message.format(value=value, **self.parameters)
        except Exception as e:
            return False, f"Validation rule '{self.name}' failed: {str(e)}"


class Validator:
    """Flexible data validator with chainable rules."""
    
    def __init__(self, field_name: Optional[str] = None):
        """Initialize validator.
        
        Args:
            field_name: Name of the field being validated
        """
        self.field_name = field_name
        self.rules: List[ValidationRule] = []
        self._required = False
        self._allow_none = True
    
    def required(self, error_message: str = "Field is required") -> 'Validator':
        """Make field required (not None/empty).
        
        Args:
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        self._required = True
        self._allow_none = False
        rule = ValidationRule(
            name="required",
            validator=lambda x: x is not None and x != "",
            error_message=error_message
        )
        self.rules.append(rule)
        return self
    
    def not_none(self, error_message: str = "Value cannot be None") -> 'Validator':
        """Disallow None values.
        
        Args:
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        self._allow_none = False
        rule = ValidationRule(
            name="not_none",
            validator=lambda x: x is not None,
            error_message=error_message
        )
        self.rules.append(rule)
        return self
    
    def type_check(self, expected_type: Union[Type, Tuple[Type, ...]], 
                  error_message: str = "Invalid type") -> 'Validator':
        """Check value type.
        
        Args:
            expected_type: Expected type or tuple of types
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        rule = ValidationRule(
            name="type_check",
            validator=lambda x: isinstance(x, expected_type),
            error_message=f"{error_message}: expected {expected_type}, got {{value.__class__.__name__}}"
        )
        self.rules.append(rule)
        return self
    
    def min_length(self, min_len: int, error_message: str = None) -> 'Validator':
        """Check minimum length for strings/sequences.
        
        Args:
            min_len: Minimum length
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Length must be at least {min_len}"
        
        rule = ValidationRule(
            name="min_length",
            validator=lambda x: len(x) >= min_len if hasattr(x, '__len__') else False,
            error_message=error_message,
            parameters={'min_len': min_len}
        )
        self.rules.append(rule)
        return self
    
    def max_length(self, max_len: int, error_message: str = None) -> 'Validator':
        """Check maximum length for strings/sequences.
        
        Args:
            max_len: Maximum length
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Length must be at most {max_len}"
        
        rule = ValidationRule(
            name="max_length",
            validator=lambda x: len(x) <= max_len if hasattr(x, '__len__') else False,
            error_message=error_message,
            parameters={'max_len': max_len}
        )
        self.rules.append(rule)
        return self
    
    def min_value(self, min_val: Union[int, float], error_message: str = None) -> 'Validator':
        """Check minimum value for numeric types.
        
        Args:
            min_val: Minimum value
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Value must be at least {min_val}"
        
        rule = ValidationRule(
            name="min_value",
            validator=lambda x: x >= min_val if isinstance(x, (int, float, Decimal)) else False,
            error_message=error_message,
            parameters={'min_val': min_val}
        )
        self.rules.append(rule)
        return self
    
    def max_value(self, max_val: Union[int, float], error_message: str = None) -> 'Validator':
        """Check maximum value for numeric types.
        
        Args:
            max_val: Maximum value
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Value must be at most {max_val}"
        
        rule = ValidationRule(
            name="max_value",
            validator=lambda x: x <= max_val if isinstance(x, (int, float, Decimal)) else False,
            error_message=error_message,
            parameters={'max_val': max_val}
        )
        self.rules.append(rule)
        return self
    
    def in_range(self, min_val: Union[int, float], max_val: Union[int, float], 
                error_message: str = None) -> 'Validator':
        """Check value is within range.
        
        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Value must be between {min_val} and {max_val}"
        
        rule = ValidationRule(
            name="in_range",
            validator=lambda x: min_val <= x <= max_val if isinstance(x, (int, float, Decimal)) else False,
            error_message=error_message,
            parameters={'min_val': min_val, 'max_val': max_val}
        )
        self.rules.append(rule)
        return self
    
    def regex_match(self, pattern: str, error_message: str = "Invalid format") -> 'Validator':
        """Check value matches regex pattern.
        
        Args:
            pattern: Regular expression pattern
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        compiled_pattern = re.compile(pattern)
        
        rule = ValidationRule(
            name="regex_match",
            validator=lambda x: bool(compiled_pattern.match(str(x))),
            error_message=error_message,
            parameters={'pattern': pattern}
        )
        self.rules.append(rule)
        return self
    
    def email(self, error_message: str = "Invalid email format") -> 'Validator':
        """Validate email format.
        
        Args:
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return self.regex_match(email_pattern, error_message)
    
    def url(self, error_message: str = "Invalid URL format") -> 'Validator':
        """Validate URL format.
        
        Args:
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return self.regex_match(url_pattern, error_message)
    
    def one_of(self, valid_values: List[Any], error_message: str = None) -> 'Validator':
        """Check value is one of allowed values.
        
        Args:
            valid_values: List of valid values
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        if error_message is None:
            error_message = f"Value must be one of: {valid_values}"
        
        rule = ValidationRule(
            name="one_of",
            validator=lambda x: x in valid_values,
            error_message=error_message,
            parameters={'valid_values': valid_values}
        )
        self.rules.append(rule)
        return self
    
    def json_serializable(self, error_message: str = "Value must be JSON serializable") -> 'Validator':
        """Check value is JSON serializable.
        
        Args:
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        def is_json_serializable(value):
            try:
                json.dumps(value)
                return True
            except (TypeError, ValueError):
                return False
        
        rule = ValidationRule(
            name="json_serializable",
            validator=is_json_serializable,
            error_message=error_message
        )
        self.rules.append(rule)
        return self
    
    def custom(self, validator_func: Callable[[Any], bool], 
              error_message: str = "Custom validation failed") -> 'Validator':
        """Add custom validation rule.
        
        Args:
            validator_func: Function that takes value and returns bool
            error_message: Custom error message
            
        Returns:
            Self for chaining
        """
        rule = ValidationRule(
            name="custom",
            validator=validator_func,
            error_message=error_message
        )
        self.rules.append(rule)
        return self
    
    def validate(self, value: Any) -> None:
        """Validate value against all rules.
        
        Args:
            value: Value to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Handle None values
        if value is None:
            if not self._allow_none:
                raise ValidationError("Value cannot be None", field=self.field_name, value=value)
            return  # Skip other rules if None is allowed
        
        # Run all validation rules
        for rule in self.rules:
            is_valid, error_message = rule.validate(value)
            if not is_valid:
                raise ValidationError(error_message, field=self.field_name, value=value)
    
    def is_valid(self, value: Any) -> bool:
        """Check if value is valid without raising exception.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate(value)
            return True
        except ValidationError:
            return False
    
    def get_errors(self, value: Any) -> List[str]:
        """Get all validation errors for a value.
        
        Args:
            value: Value to validate
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Handle None values
        if value is None and not self._allow_none:
            errors.append("Value cannot be None")
            return errors
        
        if value is None:
            return errors  # Skip other rules if None is allowed
        
        # Run all validation rules
        for rule in self.rules:
            is_valid, error_message = rule.validate(value)
            if not is_valid:
                errors.append(error_message)
        
        return errors


class SchemaValidator:
    """Validator for structured data schemas."""
    
    def __init__(self):
        """Initialize schema validator."""
        self.field_validators: Dict[str, Validator] = {}
        self.required_fields: Set[str] = set()
        self.allow_extra_fields = True
    
    def add_field(self, field_name: str, validator: Validator) -> 'SchemaValidator':
        """Add field validator.
        
        Args:
            field_name: Field name
            validator: Validator for the field
            
        Returns:
            Self for chaining
        """
        self.field_validators[field_name] = validator
        if validator._required:
            self.required_fields.add(field_name)
        return self
    
    def require_field(self, field_name: str) -> 'SchemaValidator':
        """Mark field as required.
        
        Args:
            field_name: Field name to mark as required
            
        Returns:
            Self for chaining
        """
        self.required_fields.add(field_name)
        return self
    
    def strict_mode(self, strict: bool = True) -> 'SchemaValidator':
        """Set strict mode (disallow extra fields).
        
        Args:
            strict: Whether to enable strict mode
            
        Returns:
            Self for chaining
        """
        self.allow_extra_fields = not strict
        return self
    
    def validate(self, data: Dict[str, Any]) -> None:
        """Validate data against schema.
        
        Args:
            data: Data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
        
        # Check required fields
        missing_fields = self.required_fields - set(data.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Check extra fields in strict mode
        if not self.allow_extra_fields:
            extra_fields = set(data.keys()) - set(self.field_validators.keys())
            if extra_fields:
                raise ValidationError(f"Extra fields not allowed: {extra_fields}")
        
        # Validate each field
        for field_name, value in data.items():
            if field_name in self.field_validators:
                try:
                    self.field_validators[field_name].validate(value)
                except ValidationError as e:
                    # Re-raise with field context
                    raise ValidationError(e.message, field=field_name, value=value)
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Check if data is valid without raising exception.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate(data)
            return True
        except ValidationError:
            return False
    
    def get_errors(self, data: Dict[str, Any]) -> List[str]:
        """Get all validation errors for data.
        
        Args:
            data: Data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(data, dict):
            return ["Data must be a dictionary"]
        
        # Check required fields
        missing_fields = self.required_fields - set(data.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")
        
        # Check extra fields in strict mode
        if not self.allow_extra_fields:
            extra_fields = set(data.keys()) - set(self.field_validators.keys())
            if extra_fields:
                errors.append(f"Extra fields not allowed: {extra_fields}")
        
        # Validate each field
        for field_name, value in data.items():
            if field_name in self.field_validators:
                field_errors = self.field_validators[field_name].get_errors(value)
                for error in field_errors:
                    errors.append(f"{field_name}: {error}")
        
        return errors


# Convenience functions for common validation patterns

def validate_email(email: str) -> bool:
    """Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format
    """
    try:
        Validator().type_check(str).email().validate(email)
        return True
    except ValidationError:
        return False


def validate_url(url: str) -> bool:
    """Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL format
    """
    try:
        Validator().type_check(str).url().validate(url)
        return True
    except ValidationError:
        return False


def validate_type(value: Any, expected_type: Union[Type, Tuple[Type, ...]]) -> bool:
    """Validate value type.
    
    Args:
        value: Value to check
        expected_type: Expected type or tuple of types
        
    Returns:
        True if value matches expected type
    """
    return isinstance(value, expected_type)


def validate_range(value: Union[int, float], min_val: Union[int, float], 
                  max_val: Union[int, float]) -> bool:
    """Validate value is within range.
    
    Args:
        value: Value to check
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        
    Returns:
        True if value is within range
    """
    try:
        Validator().type_check((int, float)).in_range(min_val, max_val).validate(value)
        return True
    except ValidationError:
        return False


def validate_schema(data: Dict[str, Any], schema: Dict[str, Validator]) -> List[str]:
    """Validate data against a schema dictionary.
    
    Args:
        data: Data to validate
        schema: Dictionary mapping field names to validators
        
    Returns:
        List of validation error messages (empty if valid)
    """
    validator = SchemaValidator()
    
    for field_name, field_validator in schema.items():
        validator.add_field(field_name, field_validator)
    
    return validator.get_errors(data)


# Pre-built validators for common use cases

def string_validator(min_len: int = 0, max_len: int = None, 
                    pattern: str = None) -> Validator:
    """Create string validator.
    
    Args:
        min_len: Minimum length
        max_len: Maximum length
        pattern: Regex pattern to match
        
    Returns:
        Configured string validator
    """
    validator = Validator().type_check(str).min_length(min_len)
    
    if max_len is not None:
        validator.max_length(max_len)
    
    if pattern is not None:
        validator.regex_match(pattern)
    
    return validator


def number_validator(min_val: Union[int, float] = None, 
                    max_val: Union[int, float] = None,
                    number_type: Type = float) -> Validator:
    """Create number validator.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value  
        number_type: Number type (int, float, etc.)
        
    Returns:
        Configured number validator
    """
    validator = Validator().type_check(number_type)
    
    if min_val is not None:
        validator.min_value(min_val)
    
    if max_val is not None:
        validator.max_value(max_val)
    
    return validator


def list_validator(item_validator: Validator = None, min_items: int = 0, 
                  max_items: int = None) -> Validator:
    """Create list validator.
    
    Args:
        item_validator: Validator for list items
        min_items: Minimum number of items
        max_items: Maximum number of items
        
    Returns:
        Configured list validator
    """
    validator = Validator().type_check(list).min_length(min_items)
    
    if max_items is not None:
        validator.max_length(max_items)
    
    if item_validator is not None:
        def validate_items(lst):
            return all(item_validator.is_valid(item) for item in lst)
        
        validator.custom(validate_items, "One or more list items are invalid")
    
    return validator