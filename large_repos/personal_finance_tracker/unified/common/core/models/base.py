"""
Base model classes for the personal finance system.

This module provides abstract base classes and common interfaces that
both persona implementations can inherit from and extend.
"""

from abc import ABC, abstractmethod
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Factory function for default datetime
def _now():
    return datetime.datetime.now()


class TransactionType(Enum):
    """Standard transaction types."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    INVESTMENT = "investment"
    WITHDRAWAL = "withdrawal"


class BaseTransaction(ABC):
    """
    Abstract base class for all transaction types.
    
    Provides common interface and validation for financial transactions
    that can be extended by both persona implementations.
    """
    
    def __init__(
        self,
        amount: Union[Decimal, float, int],
        date: datetime.datetime,
        description: str,
        transaction_type: TransactionType,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a base transaction.
        
        Args:
            amount: Transaction amount (converted to Decimal for precision)
            date: Transaction date
            description: Human-readable description
            transaction_type: Type of transaction
            category: Optional category classification
            tags: Optional list of tags for organization
            metadata: Optional additional data
            
        Raises:
            ValueError: If amount is invalid or required fields are missing
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount == 0:
            raise ValueError("Transaction amount cannot be zero")
        
        if not description.strip():
            raise ValueError("Transaction description cannot be empty")
        
        self.amount = amount
        self.date = date
        self.description = description.strip()
        self.transaction_type = transaction_type
        self.category = category
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate transaction data according to business rules.
        
        Returns:
            True if valid, raises exception if invalid
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary representation."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseTransaction':
        """Create transaction from dictionary representation."""
        pass
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if it doesn't already exist."""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag if it exists."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.datetime.now()
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self.metadata[key] = value
        self.updated_at = datetime.datetime.now()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value with optional default."""
        return self.metadata.get(key, default)


@dataclass
class BasePortfolio(ABC):
    """
    Abstract base class for portfolio management.
    
    Provides common structure for managing collections of financial
    instruments and calculating portfolio-level metrics.
    """
    
    name: str
    created_at: datetime.datetime = field(default_factory=_now)
    updated_at: datetime.datetime = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate portfolio after initialization."""
        if not self.name.strip():
            raise ValueError("Portfolio name cannot be empty")
    
    @abstractmethod
    def get_total_value(self) -> Decimal:
        """Calculate total portfolio value."""
        pass
    
    @abstractmethod
    def get_holdings(self) -> List[Any]:
        """Get list of portfolio holdings."""
        pass
    
    @abstractmethod
    def add_holding(self, holding: Any) -> None:
        """Add a holding to the portfolio."""
        pass
    
    @abstractmethod
    def remove_holding(self, holding_id: str) -> bool:
        """Remove a holding from the portfolio."""
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        pass
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update portfolio metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.datetime.now()


@dataclass
class BaseConfiguration(ABC):
    """
    Abstract base class for application configuration.
    
    Provides common configuration management patterns that both
    personas can extend with their specific settings.
    """
    
    name: str
    version: str = "1.0.0"
    created_at: datetime.datetime = field(default_factory=_now)
    updated_at: datetime.datetime = field(default_factory=_now)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.name.strip():
            raise ValueError("Configuration name cannot be empty")
    
    @abstractmethod
    def validate_settings(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if valid, raises exception if invalid
        """
        pass
    
    @abstractmethod
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default configuration settings."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseConfiguration':
        """Create configuration from dictionary."""
        pass
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting with optional default."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting."""
        self.settings[key] = value
        self.updated_at = datetime.datetime.now()
    
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """Update multiple configuration settings."""
        self.settings.update(new_settings)
        self.updated_at = datetime.datetime.now()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default settings."""
        self.settings = self.get_default_settings()
        self.updated_at = datetime.datetime.now()


class ValidationMixin:
    """
    Mixin class providing common validation utilities.
    
    Can be used by any class that needs standardized validation methods.
    """
    
    @staticmethod
    def validate_positive_amount(amount: Union[Decimal, float, int], field_name: str = "amount") -> Decimal:
        """
        Validate that an amount is positive and convert to Decimal.
        
        Args:
            amount: The amount to validate
            field_name: Name of the field for error messages
            
        Returns:
            Decimal representation of the amount
            
        Raises:
            ValueError: If amount is not positive
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValueError(f"{field_name} must be positive, got {amount}")
        
        return amount
    
    @staticmethod
    def validate_date_range(start_date: datetime.datetime, end_date: datetime.datetime) -> None:
        """
        Validate that start_date is before end_date.
        
        Args:
            start_date: The start date
            end_date: The end date
            
        Raises:
            ValueError: If start_date is not before end_date
        """
        if start_date >= end_date:
            raise ValueError(f"Start date {start_date} must be before end date {end_date}")
    
    @staticmethod
    def validate_non_empty_string(value: str, field_name: str = "field") -> str:
        """
        Validate that a string is not empty after stripping whitespace.
        
        Args:
            value: The string to validate
            field_name: Name of the field for error messages
            
        Returns:
            Stripped string value
            
        Raises:
            ValueError: If string is empty after stripping
        """
        stripped = value.strip() if value else ""
        if not stripped:
            raise ValueError(f"{field_name} cannot be empty")
        return stripped


class AuditMixin:
    """
    Mixin class providing audit trail functionality.
    
    Automatically tracks creation and modification timestamps.
    """
    
    def __init_audit__(self):
        """Initialize audit fields."""
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
        self.version = 1
    
    def touch(self):
        """Update the modification timestamp and increment version."""
        self.updated_at = datetime.datetime.now()
        if hasattr(self, 'version'):
            self.version += 1
    
    def get_age(self) -> float:
        """Get the age of this object in seconds."""
        return (datetime.datetime.now() - self.created_at).total_seconds()
    
    def get_last_modified_age(self) -> float:
        """Get seconds since last modification."""
        return (datetime.datetime.now() - self.updated_at).total_seconds()