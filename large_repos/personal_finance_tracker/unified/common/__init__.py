"""
Common financial system library.

This package provides shared functionality for personal finance applications
including core models, calculations, validation, processing utilities, and
design patterns that both persona implementations can leverage.

The library is organized into two main components:
- core: Foundational functionality (models, calculations, validation, etc.)
- patterns: Reusable design patterns (managers, results, configuration)
"""

# Import core functionality
from . import core

# Import design patterns
from . import patterns

# Re-export commonly used core items for convenience
from .core import (
    # Essential models
    Money,
    Currency,
    Period,
    PeriodType,
    BaseTransaction,
    TransactionType,
    ValidationMixin,
    AuditMixin,
    BasePortfolio,
    
    # Key calculations
    percentage_change,
    compound_growth_rate,
    present_value,
    future_value,
    net_present_value,
    
    # Validation essentials
    ValidationError,
    ValidationResult,
    validate_required,
    validate_positive_amount,
    validate_date,
    
    # Processing utilities
    BatchProcessor,
    cached,
    get_cache_manager,
    
    # Formatting utilities
    format_currency,
    format_date,
    serialize_to_json,
    deserialize_from_json,
)

# Re-export commonly used patterns for convenience
from .patterns import (
    # Manager patterns
    BaseManager,
    CRUDManager,
    ManagerResult,
    
    # Result patterns
    Result,
    ProcessingResult,
    ResultStatus,
    safe_operation,
    
    # Configuration patterns
    BaseConfiguration,
    FinancialConfiguration,
    ConfigurationManager,
    get_global_config_manager,
)

__version__ = "1.0.0"

__all__ = [
    # Subpackages
    "core",
    "patterns",
    
    # Essential models
    "Money",
    "Currency", 
    "Period",
    "PeriodType",
    "BaseTransaction",
    "TransactionType",
    "ValidationMixin",
    "AuditMixin",
    "BasePortfolio",
    
    # Key calculations
    "percentage_change",
    "compound_growth_rate",
    "present_value",
    "future_value",
    "net_present_value",
    
    # Validation essentials
    "ValidationError",
    "ValidationResult",
    "validate_required",
    "validate_positive_amount",
    "validate_date",
    
    # Processing utilities
    "BatchProcessor",
    "cached",
    "get_cache_manager",
    
    # Formatting utilities
    "format_currency",
    "format_date", 
    "serialize_to_json",
    "deserialize_from_json",
    
    # Manager patterns
    "BaseManager",
    "CRUDManager",
    "ManagerResult",
    
    # Result patterns
    "Result",
    "ProcessingResult",
    "ResultStatus",
    "safe_operation",
    
    # Configuration patterns
    "BaseConfiguration",
    "FinancialConfiguration",
    "ConfigurationManager",
    "get_global_config_manager",
]
