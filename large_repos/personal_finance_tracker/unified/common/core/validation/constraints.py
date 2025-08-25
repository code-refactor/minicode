"""
Constraint checking utilities for financial business rules.

This module provides constraint classes and utilities for enforcing
business rules and data integrity constraints across both persona implementations.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import date, datetime
from typing import Any, List, Dict, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum

from .validators import ValidationError, ValidationResult


class ConstraintSeverity(Enum):
    """Severity levels for constraint violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""
    constraint_name: str
    severity: ConstraintSeverity
    message: str
    field_name: Optional[str] = None
    value: Any = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class Constraint(ABC):
    """Abstract base class for all constraints."""
    
    def __init__(
        self,
        name: str,
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None
    ):
        self.name = name
        self.severity = severity
        self.message = message
    
    @abstractmethod
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """
        Check if the constraint is satisfied.
        
        Args:
            value: Value to check
            context: Additional context for the check
            
        Returns:
            List of constraint violations (empty if satisfied)
        """
        pass
    
    def create_violation(
        self,
        message: Optional[str] = None,
        field_name: Optional[str] = None,
        value: Any = None,
        context: Dict[str, Any] = None
    ) -> ConstraintViolation:
        """Create a constraint violation."""
        return ConstraintViolation(
            constraint_name=self.name,
            severity=self.severity,
            message=message or self.message or f"Constraint '{self.name}' violated",
            field_name=field_name,
            value=value,
            context=context or {}
        )


class RangeConstraint(Constraint):
    """Constraint that checks if a numeric value is within a specified range."""
    
    def __init__(
        self,
        name: str,
        min_value: Optional[Union[int, float, Decimal]] = None,
        max_value: Optional[Union[int, float, Decimal]] = None,
        inclusive: bool = True,
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None
    ):
        super().__init__(name, severity, message)
        self.min_value = Decimal(str(min_value)) if min_value is not None else None
        self.max_value = Decimal(str(max_value)) if max_value is not None else None
        self.inclusive = inclusive
        
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value cannot be greater than max_value")
    
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """Check if value is within the specified range."""
        try:
            decimal_value = Decimal(str(value))
        except (ValueError, TypeError):
            return [self.create_violation(
                f"Value '{value}' is not numeric",
                value=value,
                context=context
            )]
        
        violations = []
        
        if self.min_value is not None:
            if self.inclusive and decimal_value < self.min_value:
                violations.append(self.create_violation(
                    f"Value {decimal_value} is below minimum {self.min_value}",
                    value=value,
                    context=context
                ))
            elif not self.inclusive and decimal_value <= self.min_value:
                violations.append(self.create_violation(
                    f"Value {decimal_value} must be greater than {self.min_value}",
                    value=value,
                    context=context
                ))
        
        if self.max_value is not None:
            if self.inclusive and decimal_value > self.max_value:
                violations.append(self.create_violation(
                    f"Value {decimal_value} exceeds maximum {self.max_value}",
                    value=value,
                    context=context
                ))
            elif not self.inclusive and decimal_value >= self.max_value:
                violations.append(self.create_violation(
                    f"Value {decimal_value} must be less than {self.max_value}",
                    value=value,
                    context=context
                ))
        
        return violations


class DateRangeConstraint(Constraint):
    """Constraint that checks if a date is within a specified range."""
    
    def __init__(
        self,
        name: str,
        min_date: Optional[Union[date, datetime]] = None,
        max_date: Optional[Union[date, datetime]] = None,
        allow_future: bool = True,
        allow_past: bool = True,
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None
    ):
        super().__init__(name, severity, message)
        self.min_date = min_date.date() if isinstance(min_date, datetime) else min_date
        self.max_date = max_date.date() if isinstance(max_date, datetime) else max_date
        self.allow_future = allow_future
        self.allow_past = allow_past
        
        if self.min_date and self.max_date and self.min_date > self.max_date:
            raise ValueError("min_date cannot be after max_date")
    
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """Check if date is within the specified range."""
        # Convert value to date
        if isinstance(value, datetime):
            date_value = value.date()
        elif isinstance(value, date):
            date_value = value
        elif isinstance(value, str):
            try:
                date_value = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
            except ValueError:
                return [self.create_violation(
                    f"Value '{value}' is not a valid date",
                    value=value,
                    context=context
                )]
        else:
            return [self.create_violation(
                f"Value '{value}' is not a date",
                value=value,
                context=context
            )]
        
        violations = []
        today = date.today()
        
        # Check future/past constraints
        if not self.allow_future and date_value > today:
            violations.append(self.create_violation(
                f"Future dates are not allowed: {date_value}",
                value=value,
                context=context
            ))
        
        if not self.allow_past and date_value < today:
            violations.append(self.create_violation(
                f"Past dates are not allowed: {date_value}",
                value=value,
                context=context
            ))
        
        # Check explicit date range
        if self.min_date and date_value < self.min_date:
            violations.append(self.create_violation(
                f"Date {date_value} is before minimum date {self.min_date}",
                value=value,
                context=context
            ))
        
        if self.max_date and date_value > self.max_date:
            violations.append(self.create_violation(
                f"Date {date_value} is after maximum date {self.max_date}",
                value=value,
                context=context
            ))
        
        return violations


class UniquenessConstraint(Constraint):
    """Constraint that checks if a value is unique within a collection."""
    
    def __init__(
        self,
        name: str,
        collection: List[Any],
        case_sensitive: bool = True,
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None
    ):
        super().__init__(name, severity, message)
        self.collection = collection
        self.case_sensitive = case_sensitive
    
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """Check if value is unique in the collection."""
        violations = []
        
        # Prepare values for comparison
        if isinstance(value, str) and not self.case_sensitive:
            check_value = value.lower()
            collection_values = [str(v).lower() if isinstance(v, str) else v for v in self.collection]
        else:
            check_value = value
            collection_values = self.collection
        
        if check_value in collection_values:
            violations.append(self.create_violation(
                f"Value '{value}' is not unique",
                value=value,
                context=context
            ))
        
        return violations


class RegexConstraint(Constraint):
    """Constraint that checks if a string matches a regex pattern."""
    
    def __init__(
        self,
        name: str,
        pattern: str,
        must_match: bool = True,
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None
    ):
        super().__init__(name, severity, message)
        self.pattern = pattern
        self.must_match = must_match
        
        import re
        try:
            self.compiled_pattern = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """Check if string matches the regex pattern."""
        if not isinstance(value, str):
            return [self.create_violation(
                f"Value '{value}' is not a string",
                value=value,
                context=context
            )]
        
        violations = []
        matches = bool(self.compiled_pattern.match(value))
        
        if self.must_match and not matches:
            violations.append(self.create_violation(
                f"Value '{value}' does not match required pattern",
                value=value,
                context=context
            ))
        elif not self.must_match and matches:
            violations.append(self.create_violation(
                f"Value '{value}' matches forbidden pattern",
                value=value,
                context=context
            ))
        
        return violations


class CustomConstraint(Constraint):
    """Constraint that uses a custom validation function."""
    
    def __init__(
        self,
        name: str,
        validator_func: Callable[[Any, Dict[str, Any]], bool],
        severity: ConstraintSeverity = ConstraintSeverity.ERROR,
        message: Optional[str] = None,
        error_message_func: Optional[Callable[[Any, Dict[str, Any]], str]] = None
    ):
        super().__init__(name, severity, message)
        self.validator_func = validator_func
        self.error_message_func = error_message_func
    
    def check(self, value: Any, context: Dict[str, Any] = None) -> List[ConstraintViolation]:
        """Check using the custom validation function."""
        violations = []
        
        try:
            is_valid = self.validator_func(value, context or {})
            if not is_valid:
                if self.error_message_func:
                    message = self.error_message_func(value, context or {})
                else:
                    message = self.message or f"Custom constraint '{self.name}' violated"
                
                violations.append(self.create_violation(
                    message,
                    value=value,
                    context=context
                ))
        except Exception as e:
            violations.append(self.create_violation(
                f"Error in custom constraint '{self.name}': {e}",
                value=value,
                context=context
            ))
        
        return violations


class FinancialConstraints:
    """Collection of common financial constraints."""
    
    @staticmethod
    def positive_amount() -> RangeConstraint:
        """Constraint for positive amounts."""
        return RangeConstraint(
            "positive_amount",
            min_value=Decimal('0'),
            inclusive=False,
            message="Amount must be positive"
        )
    
    @staticmethod
    def percentage_range() -> RangeConstraint:
        """Constraint for percentage values (0-100)."""
        return RangeConstraint(
            "percentage_range",
            min_value=Decimal('0'),
            max_value=Decimal('100'),
            message="Percentage must be between 0 and 100"
        )
    
    @staticmethod
    def decimal_percentage_range() -> RangeConstraint:
        """Constraint for decimal percentage values (0.0-1.0)."""
        return RangeConstraint(
            "decimal_percentage_range",
            min_value=Decimal('0'),
            max_value=Decimal('1'),
            message="Decimal percentage must be between 0.0 and 1.0"
        )
    
    @staticmethod
    def reasonable_date_range() -> DateRangeConstraint:
        """Constraint for reasonable date ranges (not too far in past/future)."""
        from datetime import timedelta
        today = date.today()
        
        return DateRangeConstraint(
            "reasonable_date_range",
            min_date=today - timedelta(days=365 * 100),  # 100 years ago
            max_date=today + timedelta(days=365 * 50),   # 50 years from now
            message="Date must be within reasonable range"
        )
    
    @staticmethod
    def business_date() -> DateRangeConstraint:
        """Constraint for business dates (no future dates)."""
        return DateRangeConstraint(
            "business_date",
            allow_future=False,
            message="Business dates cannot be in the future"
        )
    
    @staticmethod
    def debt_to_income_ratio() -> CustomConstraint:
        """Constraint for debt-to-income ratio (warning if > 40%)."""
        def validate_dti(value, context):
            try:
                ratio = Decimal(str(value))
                return ratio <= Decimal('0.4')  # 40%
            except:
                return False
        
        return CustomConstraint(
            "debt_to_income_ratio",
            validate_dti,
            severity=ConstraintSeverity.WARNING,
            message="Debt-to-income ratio above 40% may indicate financial stress"
        )
    
    @staticmethod
    def emergency_fund_months() -> CustomConstraint:
        """Constraint for emergency fund (warning if < 3 months)."""
        def validate_emergency_fund(value, context):
            try:
                months = Decimal(str(value))
                return months >= Decimal('3')
            except:
                return False
        
        return CustomConstraint(
            "emergency_fund_months",
            validate_emergency_fund,
            severity=ConstraintSeverity.WARNING,
            message="Emergency fund should cover at least 3 months of expenses"
        )


class ConstraintValidator:
    """Validates data against a set of constraints."""
    
    def __init__(self):
        self.constraints: Dict[str, List[Constraint]] = {}
    
    def add_constraint(self, field_name: str, constraint: Constraint) -> None:
        """Add a constraint for a specific field."""
        if field_name not in self.constraints:
            self.constraints[field_name] = []
        self.constraints[field_name].append(constraint)
    
    def add_constraints(self, field_name: str, constraints: List[Constraint]) -> None:
        """Add multiple constraints for a specific field."""
        for constraint in constraints:
            self.add_constraint(field_name, constraint)
    
    def validate(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate data against all configured constraints.
        
        Args:
            data: Dictionary of field values to validate
            context: Additional context for validation
            
        Returns:
            ValidationResult with any violations
        """
        result = ValidationResult(True)
        
        for field_name, constraints in self.constraints.items():
            if field_name in data:
                field_value = data[field_name]
                
                for constraint in constraints:
                    violations = constraint.check(field_value, context)
                    
                    for violation in violations:
                        violation.field_name = field_name
                        
                        if violation.severity == ConstraintSeverity.ERROR:
                            result.add_error(violation.message)
                        elif violation.severity == ConstraintSeverity.WARNING:
                            result.add_warning(violation.message)
        
        return result
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
        context: Dict[str, Any] = None
    ) -> List[ConstraintViolation]:
        """
        Validate a single field value.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            context: Additional context for validation
            
        Returns:
            List of constraint violations
        """
        violations = []
        
        if field_name in self.constraints:
            for constraint in self.constraints[field_name]:
                field_violations = constraint.check(value, context)
                for violation in field_violations:
                    violation.field_name = field_name
                violations.extend(field_violations)
        
        return violations


def create_financial_validator() -> ConstraintValidator:
    """
    Create a constraint validator with common financial constraints.
    
    Returns:
        ConstraintValidator configured with financial constraints
    """
    validator = ConstraintValidator()
    
    # Amount fields
    validator.add_constraint("amount", FinancialConstraints.positive_amount())
    validator.add_constraint("income", FinancialConstraints.positive_amount())
    validator.add_constraint("expense", FinancialConstraints.positive_amount())
    validator.add_constraint("balance", RangeConstraint("balance", min_value=0))
    
    # Percentage fields
    validator.add_constraint("interest_rate", FinancialConstraints.decimal_percentage_range())
    validator.add_constraint("tax_rate", FinancialConstraints.decimal_percentage_range())
    validator.add_constraint("growth_rate", RangeConstraint("growth_rate", min_value=-1, max_value=5))
    
    # Date fields
    validator.add_constraint("transaction_date", FinancialConstraints.business_date())
    validator.add_constraint("due_date", FinancialConstraints.reasonable_date_range())
    validator.add_constraint("start_date", FinancialConstraints.reasonable_date_range())
    validator.add_constraint("end_date", FinancialConstraints.reasonable_date_range())
    
    # Financial ratios
    validator.add_constraint("debt_to_income_ratio", FinancialConstraints.debt_to_income_ratio())
    validator.add_constraint("emergency_fund_months", FinancialConstraints.emergency_fund_months())
    
    return validator