"""
Validation utilities for financial data integrity and business rules.

This package provides validation functions and constraint checking utilities
that both persona implementations can use to ensure data quality and
enforce business rules.
"""

# Validation functions and classes
from .validators import (
    ValidationError,
    ValidationResult,
    validate_required,
    validate_type,
    validate_numeric,
    validate_positive_amount,
    validate_percentage,
    validate_date,
    validate_date_range,
    validate_email,
    validate_string_length,
    validate_regex_pattern,
    validate_choice,
    validate_list,
    validate_dict,
    validate_business_rules,
)

# Constraint classes and utilities
from .constraints import (
    ConstraintSeverity,
    ConstraintViolation,
    Constraint,
    RangeConstraint,
    DateRangeConstraint,
    UniquenessConstraint,
    RegexConstraint,
    CustomConstraint,
    FinancialConstraints,
    ConstraintValidator,
    create_financial_validator,
)

__all__ = [
    # Validation functions and classes
    "ValidationError",
    "ValidationResult",
    "validate_required",
    "validate_type",
    "validate_numeric",
    "validate_positive_amount",
    "validate_percentage",
    "validate_date",
    "validate_date_range",
    "validate_email",
    "validate_string_length",
    "validate_regex_pattern",
    "validate_choice",
    "validate_list",
    "validate_dict",
    "validate_business_rules",
    
    # Constraint classes and utilities
    "ConstraintSeverity",
    "ConstraintViolation",
    "Constraint",
    "RangeConstraint",
    "DateRangeConstraint",
    "UniquenessConstraint",
    "RegexConstraint",
    "CustomConstraint",
    "FinancialConstraints",
    "ConstraintValidator",
    "create_financial_validator",
]