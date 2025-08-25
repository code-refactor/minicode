"""Validation utilities for the unified library."""

import re
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Type, Union
from pathlib import Path
import uuid

from .models import ValidationError


def validate_uuid(value: str, field_name: str = "id") -> Optional[ValidationError]:
    """Validate that a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return None
    except (ValueError, AttributeError):
        return ValidationError(
            field=field_name,
            message=f"Invalid UUID format: {value}",
            code="invalid_uuid"
        )


def validate_email(value: str, field_name: str = "email") -> Optional[ValidationError]:
    """Validate that a string is a valid email address."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, value):
        return ValidationError(
            field=field_name,
            message=f"Invalid email format: {value}",
            code="invalid_email"
        )
    
    return None


def validate_date_range(start: datetime,
                       end: datetime,
                       field_name: str = "date_range") -> Optional[ValidationError]:
    """Validate that a date range is valid (start <= end)."""
    if start > end:
        return ValidationError(
            field=field_name,
            message=f"Start date ({start}) must be before or equal to end date ({end})",
            code="invalid_date_range"
        )
    
    return None


def validate_enum_value(value: Any,
                       enum_class: Type[Enum],
                       field_name: str = "enum_field") -> Optional[ValidationError]:
    """Validate that a value is a valid enum member."""
    if isinstance(value, enum_class):
        return None
    
    # Try to convert string to enum
    if isinstance(value, str):
        try:
            enum_class[value]
            return None
        except KeyError:
            pass
        
        # Try by value
        for member in enum_class:
            if member.value == value:
                return None
    
    valid_values = [f"{m.name} ({m.value})" for m in enum_class]
    return ValidationError(
        field=field_name,
        message=f"Invalid value '{value}'. Must be one of: {', '.join(valid_values)}",
        code="invalid_enum_value"
    )


def validate_required(value: Any, field_name: str) -> Optional[ValidationError]:
    """Validate that a field is not None or empty."""
    if value is None:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' is required",
            code="required_field"
        )
    
    if isinstance(value, str) and not value.strip():
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' cannot be empty",
            code="empty_field"
        )
    
    if isinstance(value, (list, dict, set)) and len(value) == 0:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' cannot be empty",
            code="empty_collection"
        )
    
    return None


def validate_string_length(value: str,
                          min_length: Optional[int] = None,
                          max_length: Optional[int] = None,
                          field_name: str = "string_field") -> Optional[ValidationError]:
    """Validate string length constraints."""
    if not isinstance(value, str):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be a string",
            code="invalid_type"
        )
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be at least {min_length} characters",
            code="string_too_short"
        )
    
    if max_length is not None and length > max_length:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be at most {max_length} characters",
            code="string_too_long"
        )
    
    return None


def validate_number_range(value: Union[int, float],
                         min_value: Optional[Union[int, float]] = None,
                         max_value: Optional[Union[int, float]] = None,
                         field_name: str = "number_field") -> Optional[ValidationError]:
    """Validate that a number is within a specified range."""
    if not isinstance(value, (int, float)):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be a number",
            code="invalid_type"
        )
    
    if min_value is not None and value < min_value:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be at least {min_value}",
            code="number_too_small"
        )
    
    if max_value is not None and value > max_value:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be at most {max_value}",
            code="number_too_large"
        )
    
    return None


def validate_url(value: str, field_name: str = "url") -> Optional[ValidationError]:
    """Validate that a string is a valid URL."""
    url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    
    if not re.match(url_pattern, value):
        return ValidationError(
            field=field_name,
            message=f"Invalid URL format: {value}",
            code="invalid_url"
        )
    
    return None


def validate_file_path(value: Union[str, Path],
                      must_exist: bool = False,
                      field_name: str = "file_path") -> Optional[ValidationError]:
    """Validate that a path is valid and optionally exists."""
    try:
        path = Path(value)
        
        if must_exist and not path.exists():
            return ValidationError(
                field=field_name,
                message=f"Path does not exist: {value}",
                code="path_not_found"
            )
        
        return None
    except (ValueError, TypeError):
        return ValidationError(
            field=field_name,
            message=f"Invalid path format: {value}",
            code="invalid_path"
        )


def validate_list_length(value: list,
                        min_length: Optional[int] = None,
                        max_length: Optional[int] = None,
                        field_name: str = "list_field") -> Optional[ValidationError]:
    """Validate list length constraints."""
    if not isinstance(value, list):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be a list",
            code="invalid_type"
        )
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must have at least {min_length} items",
            code="list_too_short"
        )
    
    if max_length is not None and length > max_length:
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must have at most {max_length} items",
            code="list_too_long"
        )
    
    return None


def validate_dict_keys(value: dict,
                      required_keys: Optional[List[str]] = None,
                      allowed_keys: Optional[List[str]] = None,
                      field_name: str = "dict_field") -> Optional[ValidationError]:
    """Validate dictionary keys."""
    if not isinstance(value, dict):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be a dictionary",
            code="invalid_type"
        )
    
    if required_keys:
        missing_keys = set(required_keys) - set(value.keys())
        if missing_keys:
            return ValidationError(
                field=field_name,
                message=f"Missing required keys: {', '.join(missing_keys)}",
                code="missing_keys"
            )
    
    if allowed_keys:
        extra_keys = set(value.keys()) - set(allowed_keys)
        if extra_keys:
            return ValidationError(
                field=field_name,
                message=f"Invalid keys: {', '.join(extra_keys)}",
                code="invalid_keys"
            )
    
    return None


def validate_regex(value: str,
                  pattern: str,
                  field_name: str = "regex_field") -> Optional[ValidationError]:
    """Validate that a string matches a regex pattern."""
    if not isinstance(value, str):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' must be a string",
            code="invalid_type"
        )
    
    if not re.match(pattern, value):
        return ValidationError(
            field=field_name,
            message=f"Field '{field_name}' does not match required pattern",
            code="pattern_mismatch"
        )
    
    return None


class CompositeValidator:
    """Compose multiple validators into a single validator."""
    
    def __init__(self):
        """Initialize composite validator."""
        self.validators = []
    
    def add(self, validator: callable) -> 'CompositeValidator':
        """Add a validator to the composite."""
        self.validators.append(validator)
        return self
    
    def validate(self, value: Any) -> List[ValidationError]:
        """Run all validators and collect errors."""
        errors = []
        
        for validator in self.validators:
            result = validator(value)
            
            if isinstance(result, ValidationError):
                errors.append(result)
            elif isinstance(result, list):
                errors.extend(result)
        
        return errors
    
    def __call__(self, value: Any) -> List[ValidationError]:
        """Make the composite validator callable."""
        return self.validate(value)


class FieldValidator:
    """Validator for specific fields of an object."""
    
    def __init__(self):
        """Initialize field validator."""
        self.field_validators = {}
    
    def add_field(self,
                 field_name: str,
                 validator: callable) -> 'FieldValidator':
        """Add a validator for a specific field."""
        if field_name not in self.field_validators:
            self.field_validators[field_name] = []
        self.field_validators[field_name].append(validator)
        return self
    
    def validate(self, obj: Any) -> List[ValidationError]:
        """Validate all fields of an object."""
        errors = []
        
        for field_name, validators in self.field_validators.items():
            # Get field value
            if hasattr(obj, field_name):
                value = getattr(obj, field_name)
            elif isinstance(obj, dict):
                value = obj.get(field_name)
            else:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Field '{field_name}' not found",
                    code="field_not_found"
                ))
                continue
            
            # Run validators for this field
            for validator in validators:
                result = validator(value)
                
                if isinstance(result, ValidationError):
                    errors.append(result)
                elif isinstance(result, list):
                    errors.extend(result)
        
        return errors
    
    def __call__(self, obj: Any) -> List[ValidationError]:
        """Make the field validator callable."""
        return self.validate(obj)