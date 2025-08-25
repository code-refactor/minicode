"""
Common validation functions for financial data.

This module provides validation utilities that can be used across
both persona implementations for data integrity and business rules.
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, List, Dict, Optional, Union, Callable, Pattern
import re
from enum import Enum

# Type aliases
Numeric = Union[int, float, Decimal]
DateLike = Union[date, datetime]


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, field_name: str = None, value: Any = None):
        self.message = message
        self.field_name = field_name
        self.value = value
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format the validation error message."""
        if self.field_name:
            return f"Validation error in field '{self.field_name}': {self.message}"
        return f"Validation error: {self.message}"


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge with another validation result."""
        merged_errors = self.errors + other.errors
        merged_warnings = self.warnings + other.warnings
        is_valid = self.is_valid and other.is_valid
        return ValidationResult(is_valid, merged_errors, merged_warnings)


def validate_required(value: Any, field_name: str = "field") -> Any:
    """
    Validate that a value is present and not empty.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is None or empty
    """
    if value is None:
        raise ValidationError(f"{field_name} is required", field_name, value)
    
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} cannot be empty", field_name, value)
    
    if isinstance(value, (list, dict)) and len(value) == 0:
        raise ValidationError(f"{field_name} cannot be empty", field_name, value)
    
    return value


def validate_type(value: Any, expected_type: type, field_name: str = "field") -> Any:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}",
            field_name,
            value
        )
    
    return value


def validate_numeric(
    value: Any,
    field_name: str = "field",
    allow_negative: bool = True,
    allow_zero: bool = True,
    min_value: Optional[Numeric] = None,
    max_value: Optional[Numeric] = None
) -> Decimal:
    """
    Validate and convert a numeric value to Decimal.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        allow_negative: Whether negative values are allowed
        allow_zero: Whether zero values are allowed
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Validated Decimal value
        
    Raises:
        ValidationError: If value is invalid
    """
    # Convert to Decimal
    try:
        if isinstance(value, Decimal):
            decimal_value = value
        elif isinstance(value, (int, float)):
            decimal_value = Decimal(str(value))
        elif isinstance(value, str):
            decimal_value = Decimal(value.strip())
        else:
            raise ValidationError(f"{field_name} must be numeric", field_name, value)
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field_name} is not a valid number", field_name, value)
    
    # Check sign constraints
    if not allow_negative and decimal_value < 0:
        raise ValidationError(f"{field_name} cannot be negative", field_name, value)
    
    if not allow_zero and decimal_value == 0:
        raise ValidationError(f"{field_name} cannot be zero", field_name, value)
    
    # Check bounds
    if min_value is not None and decimal_value < Decimal(str(min_value)):
        raise ValidationError(f"{field_name} must be at least {min_value}", field_name, value)
    
    if max_value is not None and decimal_value > Decimal(str(max_value)):
        raise ValidationError(f"{field_name} must be at most {max_value}", field_name, value)
    
    return decimal_value


def validate_positive_amount(value: Any, field_name: str = "amount") -> Decimal:
    """
    Validate that a value is a positive amount.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated positive Decimal amount
        
    Raises:
        ValidationError: If value is not positive
    """
    return validate_numeric(value, field_name, allow_negative=False, allow_zero=False)


def validate_percentage(
    value: Any,
    field_name: str = "percentage",
    as_decimal: bool = True
) -> Decimal:
    """
    Validate a percentage value.
    
    Args:
        value: Percentage value to validate
        field_name: Name of the field for error messages
        as_decimal: If True, expect decimal form (0.15 = 15%); if False, expect percentage form (15 = 15%)
        
    Returns:
        Validated percentage as Decimal
        
    Raises:
        ValidationError: If value is not a valid percentage
    """
    decimal_value = validate_numeric(value, field_name, allow_negative=False)
    
    if as_decimal:
        if decimal_value > 1:
            raise ValidationError(f"{field_name} as decimal must be <= 1.0 (100%)", field_name, value)
    else:
        if decimal_value > 100:
            raise ValidationError(f"{field_name} as percentage must be <= 100", field_name, value)
        # Convert to decimal form
        decimal_value = decimal_value / 100
    
    return decimal_value


def validate_date(
    value: Any,
    field_name: str = "date",
    min_date: Optional[DateLike] = None,
    max_date: Optional[DateLike] = None,
    future_allowed: bool = True,
    past_allowed: bool = True
) -> date:
    """
    Validate a date value.
    
    Args:
        value: Date value to validate
        field_name: Name of the field for error messages
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        future_allowed: Whether future dates are allowed
        past_allowed: Whether past dates are allowed
        
    Returns:
        Validated date
        
    Raises:
        ValidationError: If date is invalid
    """
    # Convert to date
    if isinstance(value, datetime):
        date_value = value.date()
    elif isinstance(value, date):
        date_value = value
    elif isinstance(value, str):
        try:
            # Try parsing ISO format
            parsed_datetime = datetime.fromisoformat(value.replace('Z', '+00:00'))
            date_value = parsed_datetime.date()
        except ValueError:
            try:
                # Try parsing as date only
                date_value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(f"{field_name} is not a valid date format", field_name, value)
    else:
        raise ValidationError(f"{field_name} must be a date", field_name, value)
    
    # Check future/past constraints
    today = date.today()
    
    if not future_allowed and date_value > today:
        raise ValidationError(f"{field_name} cannot be in the future", field_name, value)
    
    if not past_allowed and date_value < today:
        raise ValidationError(f"{field_name} cannot be in the past", field_name, value)
    
    # Check bounds
    if min_date:
        min_date_val = min_date.date() if isinstance(min_date, datetime) else min_date
        if date_value < min_date_val:
            raise ValidationError(f"{field_name} must be on or after {min_date_val}", field_name, value)
    
    if max_date:
        max_date_val = max_date.date() if isinstance(max_date, datetime) else max_date
        if date_value > max_date_val:
            raise ValidationError(f"{field_name} must be on or before {max_date_val}", field_name, value)
    
    return date_value


def validate_date_range(
    start_date: Any,
    end_date: Any,
    start_field_name: str = "start_date",
    end_field_name: str = "end_date",
    allow_same_date: bool = True
) -> tuple[date, date]:
    """
    Validate a date range.
    
    Args:
        start_date: Start date to validate
        end_date: End date to validate
        start_field_name: Name of start date field
        end_field_name: Name of end date field
        allow_same_date: Whether start and end can be the same date
        
    Returns:
        Tuple of (validated_start_date, validated_end_date)
        
    Raises:
        ValidationError: If date range is invalid
    """
    start_val = validate_date(start_date, start_field_name)
    end_val = validate_date(end_date, end_field_name)
    
    if not allow_same_date and start_val == end_val:
        raise ValidationError("Start date and end date cannot be the same")
    
    if start_val > end_val:
        raise ValidationError("Start date must be before or equal to end date")
    
    return start_val, end_val


def validate_email(value: Any, field_name: str = "email") -> str:
    """
    Validate an email address.
    
    Args:
        value: Email address to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated email address
        
    Raises:
        ValidationError: If email is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name, value)
    
    email = value.strip().lower()
    
    if not email:
        raise ValidationError(f"{field_name} cannot be empty", field_name, value)
    
    # Basic email regex pattern
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    if not email_pattern.match(email):
        raise ValidationError(f"{field_name} is not a valid email address", field_name, value)
    
    return email


def validate_string_length(
    value: Any,
    field_name: str = "field",
    min_length: int = 0,
    max_length: Optional[int] = None,
    strip_whitespace: bool = True
) -> str:
    """
    Validate string length constraints.
    
    Args:
        value: String value to validate
        field_name: Name of the field for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        strip_whitespace: Whether to strip whitespace before validation
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name, value)
    
    string_val = value.strip() if strip_whitespace else value
    length = len(string_val)
    
    if length < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters", field_name, value)
    
    if max_length is not None and length > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters", field_name, value)
    
    return string_val


def validate_regex_pattern(
    value: Any,
    pattern: Union[str, Pattern],
    field_name: str = "field",
    error_message: Optional[str] = None
) -> str:
    """
    Validate that a string matches a regex pattern.
    
    Args:
        value: String value to validate
        pattern: Regex pattern (string or compiled pattern)
        field_name: Name of the field for error messages
        error_message: Custom error message
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If string doesn't match pattern
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name, value)
    
    if isinstance(pattern, str):
        compiled_pattern = re.compile(pattern)
    else:
        compiled_pattern = pattern
    
    if not compiled_pattern.match(value):
        if error_message:
            raise ValidationError(error_message, field_name, value)
        else:
            raise ValidationError(f"{field_name} does not match required format", field_name, value)
    
    return value


def validate_choice(
    value: Any,
    choices: List[Any],
    field_name: str = "field"
) -> Any:
    """
    Validate that a value is one of allowed choices.
    
    Args:
        value: Value to validate
        choices: List of allowed choices
        field_name: Name of the field for error messages
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is not in choices
    """
    if value not in choices:
        raise ValidationError(
            f"{field_name} must be one of {choices}, got '{value}'",
            field_name,
            value
        )
    
    return value


def validate_list(
    value: Any,
    field_name: str = "field",
    min_length: int = 0,
    max_length: Optional[int] = None,
    item_validator: Optional[Callable[[Any, str], Any]] = None
) -> List[Any]:
    """
    Validate a list and optionally its items.
    
    Args:
        value: List value to validate
        field_name: Name of the field for error messages
        min_length: Minimum list length
        max_length: Maximum list length
        item_validator: Optional function to validate each item
        
    Returns:
        Validated list
        
    Raises:
        ValidationError: If list or its items are invalid
    """
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list", field_name, value)
    
    length = len(value)
    
    if length < min_length:
        raise ValidationError(f"{field_name} must have at least {min_length} items", field_name, value)
    
    if max_length is not None and length > max_length:
        raise ValidationError(f"{field_name} must have at most {max_length} items", field_name, value)
    
    # Validate individual items if validator provided
    if item_validator:
        validated_items = []
        for i, item in enumerate(value):
            try:
                validated_item = item_validator(item, f"{field_name}[{i}]")
                validated_items.append(validated_item)
            except ValidationError as e:
                raise ValidationError(f"{field_name}[{i}]: {e.message}", field_name, value)
        return validated_items
    
    return value


def validate_dict(
    value: Any,
    field_name: str = "field",
    required_keys: Optional[List[str]] = None,
    optional_keys: Optional[List[str]] = None,
    key_validators: Optional[Dict[str, Callable[[Any, str], Any]]] = None
) -> Dict[str, Any]:
    """
    Validate a dictionary structure.
    
    Args:
        value: Dictionary value to validate
        field_name: Name of the field for error messages
        required_keys: List of required keys
        optional_keys: List of optional keys
        key_validators: Dictionary of key->validator function mappings
        
    Returns:
        Validated dictionary
        
    Raises:
        ValidationError: If dictionary structure is invalid
    """
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be a dictionary", field_name, value)
    
    validated_dict = {}
    
    # Check required keys
    if required_keys:
        for key in required_keys:
            if key not in value:
                raise ValidationError(f"{field_name} missing required key '{key}'", field_name, value)
    
    # Check for unexpected keys
    if required_keys is not None or optional_keys is not None:
        allowed_keys = set(required_keys or []) | set(optional_keys or [])
        for key in value:
            if key not in allowed_keys:
                raise ValidationError(f"{field_name} contains unexpected key '{key}'", field_name, value)
    
    # Validate individual values
    for key, val in value.items():
        if key_validators and key in key_validators:
            try:
                validated_dict[key] = key_validators[key](val, f"{field_name}.{key}")
            except ValidationError as e:
                raise ValidationError(f"{field_name}.{key}: {e.message}", field_name, value)
        else:
            validated_dict[key] = val
    
    return validated_dict


def validate_business_rules(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate common business rules for financial data.
    
    Args:
        data: Dictionary containing financial data to validate
        
    Returns:
        ValidationResult with any errors or warnings
    """
    result = ValidationResult(True)
    
    # Check for basic financial consistency rules
    if 'income' in data and 'expenses' in data:
        try:
            income = validate_numeric(data['income'], 'income', allow_negative=False)
            expenses = validate_numeric(data['expenses'], 'expenses', allow_negative=False)
            
            # Warn if expenses exceed income significantly
            if expenses > income * Decimal('1.2'):
                result.add_warning("Expenses significantly exceed income")
            
            # Error if expenses are more than 10x income (likely data error)
            if expenses > income * 10:
                result.add_error("Expenses are unrealistically high compared to income")
                
        except ValidationError as e:
            result.add_error(e.message)
    
    # Check date consistency
    if 'start_date' in data and 'end_date' in data:
        try:
            start_date = validate_date(data['start_date'], 'start_date')
            end_date = validate_date(data['end_date'], 'end_date')
            
            if start_date > end_date:
                result.add_error("Start date cannot be after end date")
                
        except ValidationError as e:
            result.add_error(e.message)
    
    # Check percentage fields
    percentage_fields = ['tax_rate', 'interest_rate', 'growth_rate']
    for field in percentage_fields:
        if field in data:
            try:
                validate_percentage(data[field], field)
            except ValidationError as e:
                result.add_error(e.message)
    
    return result