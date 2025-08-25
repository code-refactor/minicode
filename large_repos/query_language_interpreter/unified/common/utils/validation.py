"""Input validation utilities for the unified query language interpreter."""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from enum import Enum
from datetime import datetime, date
from decimal import Decimal

from ..core.base_models import BaseQuery, QueryClause, QueryOperator
from ..core.exceptions import ValidationError, QueryValidationError


class ValidationType(str, Enum):
    """Types of validation that can be performed."""
    
    REQUIRED = "required"
    TYPE = "type"
    LENGTH = "length"
    RANGE = "range"
    PATTERN = "pattern"
    CUSTOM = "custom"
    EMAIL = "email"
    URL = "url"
    DATE = "date"
    NUMERIC = "numeric"


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(
        self,
        is_valid: bool,
        field_name: Optional[str] = None,
        message: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize validation result.
        
        Args:
            is_valid: Whether validation passed
            field_name: Name of the field that was validated
            message: Validation message
            severity: Severity of the validation issue
            details: Additional validation details
        """
        self.is_valid = is_valid
        self.field_name = field_name
        self.message = message
        self.severity = severity
        self.details = details or {}


class ValidationRule:
    """Represents a validation rule that can be applied to data."""
    
    def __init__(
        self,
        validation_type: ValidationType,
        field_name: str,
        message: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        **kwargs
    ):
        """Initialize validation rule.
        
        Args:
            validation_type: Type of validation
            field_name: Name of the field to validate
            message: Custom validation message
            severity: Severity of validation failures
            **kwargs: Additional validation parameters
        """
        self.validation_type = validation_type
        self.field_name = field_name
        self.message = message
        self.severity = severity
        self.params = kwargs
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate a value against this rule.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            Validation result
        """
        try:
            if self.validation_type == ValidationType.REQUIRED:
                return self._validate_required(value)
            elif self.validation_type == ValidationType.TYPE:
                return self._validate_type(value)
            elif self.validation_type == ValidationType.LENGTH:
                return self._validate_length(value)
            elif self.validation_type == ValidationType.RANGE:
                return self._validate_range(value)
            elif self.validation_type == ValidationType.PATTERN:
                return self._validate_pattern(value)
            elif self.validation_type == ValidationType.EMAIL:
                return self._validate_email(value)
            elif self.validation_type == ValidationType.URL:
                return self._validate_url(value)
            elif self.validation_type == ValidationType.DATE:
                return self._validate_date(value)
            elif self.validation_type == ValidationType.NUMERIC:
                return self._validate_numeric(value)
            elif self.validation_type == ValidationType.CUSTOM:
                return self._validate_custom(value, context)
            else:
                return ValidationResult(
                    is_valid=False,
                    field_name=self.field_name,
                    message=f"Unknown validation type: {self.validation_type}",
                    severity=self.severity
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=f"Validation error: {str(e)}",
                severity=ValidationSeverity.ERROR,
                details={"exception": str(e)}
            )
    
    def _validate_required(self, value: Any) -> ValidationResult:
        """Validate that a value is not None or empty."""
        is_valid = value is not None and (not hasattr(value, '__len__') or len(value) > 0)
        message = self.message or f"Field '{self.field_name}' is required"
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=self.field_name,
            message=None if is_valid else message,
            severity=self.severity
        )
    
    def _validate_type(self, value: Any) -> ValidationResult:
        """Validate that a value is of the expected type."""
        expected_type = self.params.get('expected_type')
        if not expected_type:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message="No expected type specified for type validation",
                severity=ValidationSeverity.ERROR
            )
        
        is_valid = isinstance(value, expected_type)
        message = self.message or f"Field '{self.field_name}' must be of type {expected_type.__name__}"
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=self.field_name,
            message=None if is_valid else message,
            severity=self.severity
        )
    
    def _validate_length(self, value: Any) -> ValidationResult:
        """Validate the length of a value."""
        if not hasattr(value, '__len__'):
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=f"Field '{self.field_name}' does not support length validation",
                severity=self.severity
            )
        
        length = len(value)
        min_length = self.params.get('min_length')
        max_length = self.params.get('max_length')
        
        if min_length is not None and length < min_length:
            message = self.message or f"Field '{self.field_name}' must be at least {min_length} characters"
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=message,
                severity=self.severity
            )
        
        if max_length is not None and length > max_length:
            message = self.message or f"Field '{self.field_name}' must be at most {max_length} characters"
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=message,
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=self.field_name,
            severity=self.severity
        )
    
    def _validate_range(self, value: Any) -> ValidationResult:
        """Validate that a numeric value is within range."""
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=f"Field '{self.field_name}' must be numeric for range validation",
                severity=self.severity
            )
        
        min_value = self.params.get('min_value')
        max_value = self.params.get('max_value')
        
        if min_value is not None and numeric_value < min_value:
            message = self.message or f"Field '{self.field_name}' must be at least {min_value}"
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=message,
                severity=self.severity
            )
        
        if max_value is not None and numeric_value > max_value:
            message = self.message or f"Field '{self.field_name}' must be at most {max_value}"
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=message,
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=self.field_name,
            severity=self.severity
        )
    
    def _validate_pattern(self, value: Any) -> ValidationResult:
        """Validate that a value matches a regex pattern."""
        pattern = self.params.get('pattern')
        if not pattern:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message="No pattern specified for pattern validation",
                severity=ValidationSeverity.ERROR
            )
        
        try:
            is_valid = bool(re.match(pattern, str(value)))
            message = self.message or f"Field '{self.field_name}' does not match the required pattern"
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=self.field_name,
                message=None if is_valid else message,
                severity=self.severity
            )
        except re.error as e:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=f"Invalid regex pattern: {str(e)}",
                severity=ValidationSeverity.ERROR
            )
    
    def _validate_email(self, value: Any) -> ValidationResult:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(email_pattern, str(value)))
        message = self.message or f"Field '{self.field_name}' must be a valid email address"
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=self.field_name,
            message=None if is_valid else message,
            severity=self.severity
        )
    
    def _validate_url(self, value: Any) -> ValidationResult:
        """Validate URL format."""
        url_pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        is_valid = bool(re.match(url_pattern, str(value)))
        message = self.message or f"Field '{self.field_name}' must be a valid URL"
        
        return ValidationResult(
            is_valid=is_valid,
            field_name=self.field_name,
            message=None if is_valid else message,
            severity=self.severity
        )
    
    def _validate_date(self, value: Any) -> ValidationResult:
        """Validate date format."""
        if isinstance(value, (datetime, date)):
            return ValidationResult(
                is_valid=True,
                field_name=self.field_name,
                severity=self.severity
            )
        
        # Try to parse string date
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S"
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(str(value), fmt)
                return ValidationResult(
                    is_valid=True,
                    field_name=self.field_name,
                    severity=self.severity
                )
            except ValueError:
                continue
        
        message = self.message or f"Field '{self.field_name}' must be a valid date"
        return ValidationResult(
            is_valid=False,
            field_name=self.field_name,
            message=message,
            severity=self.severity
        )
    
    def _validate_numeric(self, value: Any) -> ValidationResult:
        """Validate numeric format."""
        if isinstance(value, (int, float, Decimal)):
            return ValidationResult(
                is_valid=True,
                field_name=self.field_name,
                severity=self.severity
            )
        
        try:
            float(value)
            return ValidationResult(
                is_valid=True,
                field_name=self.field_name,
                severity=self.severity
            )
        except (TypeError, ValueError):
            message = self.message or f"Field '{self.field_name}' must be numeric"
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=message,
                severity=self.severity
            )
    
    def _validate_custom(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate using a custom function."""
        custom_func = self.params.get('custom_func')
        if not custom_func:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message="No custom function specified for custom validation",
                severity=ValidationSeverity.ERROR
            )
        
        try:
            is_valid = custom_func(value, context)
            message = self.message or f"Field '{self.field_name}' failed custom validation"
            
            return ValidationResult(
                is_valid=is_valid,
                field_name=self.field_name,
                message=None if is_valid else message,
                severity=self.severity
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                field_name=self.field_name,
                message=f"Custom validation error: {str(e)}",
                severity=ValidationSeverity.ERROR,
                details={"exception": str(e)}
            )


class InputValidator:
    """Validator for general input data."""
    
    def __init__(self):
        """Initialize the input validator."""
        self.rules: List[ValidationRule] = []
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule.
        
        Args:
            rule: Validation rule to add
        """
        self.rules.append(rule)
    
    def add_required_rule(self, field_name: str, message: Optional[str] = None) -> None:
        """Add a required field validation rule.
        
        Args:
            field_name: Name of the required field
            message: Custom validation message
        """
        rule = ValidationRule(
            ValidationType.REQUIRED,
            field_name,
            message
        )
        self.add_rule(rule)
    
    def add_type_rule(
        self,
        field_name: str,
        expected_type: type,
        message: Optional[str] = None
    ) -> None:
        """Add a type validation rule.
        
        Args:
            field_name: Name of the field
            expected_type: Expected type
            message: Custom validation message
        """
        rule = ValidationRule(
            ValidationType.TYPE,
            field_name,
            message,
            expected_type=expected_type
        )
        self.add_rule(rule)
    
    def add_length_rule(
        self,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """Add a length validation rule.
        
        Args:
            field_name: Name of the field
            min_length: Minimum length
            max_length: Maximum length
            message: Custom validation message
        """
        rule = ValidationRule(
            ValidationType.LENGTH,
            field_name,
            message,
            min_length=min_length,
            max_length=max_length
        )
        self.add_rule(rule)
    
    def add_range_rule(
        self,
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        message: Optional[str] = None
    ) -> None:
        """Add a numeric range validation rule.
        
        Args:
            field_name: Name of the field
            min_value: Minimum value
            max_value: Maximum value
            message: Custom validation message
        """
        rule = ValidationRule(
            ValidationType.RANGE,
            field_name,
            message,
            min_value=min_value,
            max_value=max_value
        )
        self.add_rule(rule)
    
    def add_pattern_rule(
        self,
        field_name: str,
        pattern: str,
        message: Optional[str] = None
    ) -> None:
        """Add a regex pattern validation rule.
        
        Args:
            field_name: Name of the field
            pattern: Regex pattern
            message: Custom validation message
        """
        rule = ValidationRule(
            ValidationType.PATTERN,
            field_name,
            message,
            pattern=pattern
        )
        self.add_rule(rule)
    
    def validate(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Validate data against all registered rules.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            List of validation results
        """
        results = []
        
        for rule in self.rules:
            value = data.get(rule.field_name)
            result = rule.validate(value, context)
            results.append(result)
        
        return results
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Validate a specific field.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            context: Optional validation context
            
        Returns:
            List of validation results for the field
        """
        results = []
        
        for rule in self.rules:
            if rule.field_name == field_name:
                result = rule.validate(value, context)
                results.append(result)
        
        return results
    
    def is_valid(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if data is valid according to all rules.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            True if all validations pass
        """
        results = self.validate(data, context)
        return all(result.is_valid or result.severity != ValidationSeverity.ERROR for result in results)
    
    def get_errors(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Get only the validation errors.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            List of validation errors
        """
        results = self.validate(data, context)
        return [result for result in results if not result.is_valid and result.severity == ValidationSeverity.ERROR]


class QueryValidator:
    """Validator for query-specific validation."""
    
    def __init__(self):
        """Initialize the query validator."""
        self.max_query_length = 10000
        self.max_clauses = 50
        self.forbidden_patterns = [
            r';\s*(drop|delete|truncate|alter)\s+',  # Dangerous SQL operations
            r'union\s+select',  # SQL injection attempts
            r'\/\*.*\*\/',  # SQL comments
            r'--.*$'  # SQL line comments
        ]
        self.required_escape_chars = ['\'', '"', ';', '--']
    
    def validate_query_string(self, query: str) -> List[ValidationResult]:
        """Validate a query string.
        
        Args:
            query: Query string to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        # Check query length
        if len(query) > self.max_query_length:
            results.append(ValidationResult(
                is_valid=False,
                field_name="query",
                message=f"Query length exceeds maximum of {self.max_query_length} characters",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="query",
                    message=f"Query contains forbidden pattern: {pattern}",
                    severity=ValidationSeverity.ERROR
                ))
        
        # Check for empty query
        if not query.strip():
            results.append(ValidationResult(
                is_valid=False,
                field_name="query",
                message="Query cannot be empty",
                severity=ValidationSeverity.ERROR
            ))
        
        # If no errors found, add success result
        if not any(not r.is_valid for r in results):
            results.append(ValidationResult(
                is_valid=True,
                field_name="query",
                message="Query string validation passed",
                severity=ValidationSeverity.INFO
            ))
        
        return results
    
    def validate_query_structure(self, query: BaseQuery) -> List[ValidationResult]:
        """Validate a structured query object.
        
        Args:
            query: Query object to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        # Check query ID
        if not query.query_id:
            results.append(ValidationResult(
                is_valid=False,
                field_name="query_id",
                message="Query ID is required",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check clauses
        if not query.clauses:
            results.append(ValidationResult(
                is_valid=False,
                field_name="clauses",
                message="Query must have at least one clause",
                severity=ValidationSeverity.ERROR
            ))
        elif len(query.clauses) > self.max_clauses:
            results.append(ValidationResult(
                is_valid=False,
                field_name="clauses",
                message=f"Query has too many clauses (max: {self.max_clauses})",
                severity=ValidationSeverity.ERROR
            ))
        
        # Validate individual clauses
        for i, clause in enumerate(query.clauses):
            clause_results = self.validate_query_clause(clause, f"clause_{i}")
            results.extend(clause_results)
        
        # Validate limit and offset
        if query.limit is not None and query.limit < 0:
            results.append(ValidationResult(
                is_valid=False,
                field_name="limit",
                message="Limit cannot be negative",
                severity=ValidationSeverity.ERROR
            ))
        
        if query.offset is not None and query.offset < 0:
            results.append(ValidationResult(
                is_valid=False,
                field_name="offset",
                message="Offset cannot be negative",
                severity=ValidationSeverity.ERROR
            ))
        
        return results
    
    def validate_query_clause(self, clause: QueryClause, field_prefix: str = "") -> List[ValidationResult]:
        """Validate a query clause.
        
        Args:
            clause: Query clause to validate
            field_prefix: Prefix for field names in results
            
        Returns:
            List of validation results
        """
        results = []
        field_name = f"{field_prefix}.clause" if field_prefix else "clause"
        
        # Basic clause validation
        if not hasattr(clause, 'query_type') and not hasattr(clause, '__class__'):
            results.append(ValidationResult(
                is_valid=False,
                field_name=field_name,
                message="Invalid clause structure",
                severity=ValidationSeverity.ERROR
            ))
        
        # Additional validation can be added here based on clause type
        # This would be extended by specific implementations
        
        return results
    
    def validate_user_permissions(
        self,
        user_context: Dict[str, Any],
        query: Union[str, BaseQuery]
    ) -> List[ValidationResult]:
        """Validate user permissions for a query.
        
        Args:
            user_context: User context information
            query: Query to validate permissions for
            
        Returns:
            List of validation results
        """
        results = []
        
        # Check if user ID is provided
        if not user_context.get('user_id'):
            results.append(ValidationResult(
                is_valid=False,
                field_name="user_id",
                message="User ID is required for query execution",
                severity=ValidationSeverity.ERROR
            ))
        
        # Check user roles (basic example)
        user_roles = user_context.get('roles', [])
        if not user_roles:
            results.append(ValidationResult(
                is_valid=False,
                field_name="roles",
                message="User must have at least one role",
                severity=ValidationSeverity.WARNING
            ))
        
        return results
    
    def validate_data_access(
        self,
        user_context: Dict[str, Any],
        requested_fields: List[str],
        data_sources: List[str]
    ) -> List[ValidationResult]:
        """Validate user access to specific data fields and sources.
        
        Args:
            user_context: User context information
            requested_fields: Fields requested in the query
            data_sources: Data sources accessed by the query
            
        Returns:
            List of validation results
        """
        results = []
        
        # This is a placeholder implementation
        # Real implementations would check against actual permission systems
        
        user_roles = set(user_context.get('roles', []))
        
        # Example: Check for sensitive fields
        sensitive_fields = {'ssn', 'credit_card', 'password', 'private_key'}
        restricted_fields = [field for field in requested_fields if field.lower() in sensitive_fields]
        
        if restricted_fields and 'admin' not in user_roles:
            results.append(ValidationResult(
                is_valid=False,
                field_name="fields",
                message=f"Access denied to sensitive fields: {restricted_fields}",
                severity=ValidationSeverity.ERROR,
                details={"restricted_fields": restricted_fields}
            ))
        
        # Example: Check for restricted data sources
        restricted_sources = {'audit_logs', 'security_events'}
        accessed_restricted = [source for source in data_sources if source in restricted_sources]
        
        if accessed_restricted and 'security_admin' not in user_roles:
            results.append(ValidationResult(
                is_valid=False,
                field_name="data_sources",
                message=f"Access denied to restricted data sources: {accessed_restricted}",
                severity=ValidationSeverity.ERROR,
                details={"restricted_sources": accessed_restricted}
            ))
        
        return results


async def validate_config(config: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> None:
    """Validate a configuration dictionary against a schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: Schema dictionary specifying field types and defaults
        
    Raises:
        ValidationError: If validation fails
    """
    for field_name, field_spec in schema.items():
        field_type = field_spec.get('type')
        default_value = field_spec.get('default')
        required = field_spec.get('required', False)
        
        if field_name not in config:
            if required:
                raise ValidationError(
                    f"Required configuration field '{field_name}' is missing",
                    field_name=field_name
                )
            elif default_value is not None:
                config[field_name] = default_value
        else:
            value = config[field_name]
            if field_type and not isinstance(value, field_type):
                raise ValidationError(
                    f"Configuration field '{field_name}' must be of type {field_type.__name__}, got {type(value).__name__}",
                    field_name=field_name
                )