"""
Common design patterns for financial applications.

This package provides reusable design patterns including managers,
results handling, and configuration management that both persona
implementations can use for consistent architecture.
"""

# Manager patterns
from .managers import (
    ManagerResult,
    BaseManager,
    CRUDManager,
    TransactionManager,
    CacheableManager,
    ConfigurableManager,
)

# Result patterns
from .results import (
    ResultStatus,
    ErrorSeverity,
    ErrorInfo,
    WarningInfo,
    Result,
    ProcessingResult,
    ResultCollector,
    safe_operation,
    chain_operations,
    parallel_operation_results,
)

# Configuration patterns
from .config import (
    ConfigurationError,
    Environment,
    ConfigField,
    BaseConfiguration,
    FinancialConfiguration,
    ConfigurationManager,
    DynamicConfiguration,
    get_global_config_manager,
    setup_default_configurations,
)

__all__ = [
    # Manager patterns
    "ManagerResult",
    "BaseManager",
    "CRUDManager",
    "TransactionManager",
    "CacheableManager",
    "ConfigurableManager",
    
    # Result patterns
    "ResultStatus",
    "ErrorSeverity",
    "ErrorInfo",
    "WarningInfo",
    "Result",
    "ProcessingResult",
    "ResultCollector",
    "safe_operation",
    "chain_operations",
    "parallel_operation_results",
    
    # Configuration patterns
    "ConfigurationError",
    "Environment",
    "ConfigField",
    "BaseConfiguration",
    "FinancialConfiguration",
    "ConfigurationManager",
    "DynamicConfiguration",
    "get_global_config_manager",
    "setup_default_configurations",
]