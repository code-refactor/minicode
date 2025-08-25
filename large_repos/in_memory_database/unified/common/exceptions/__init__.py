"""Exception classes for the unified library."""

from .base import (
    UnifiedError,
    ConfigurationError,
    ConnectionError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    DataError,
    QueryError,
    IndexError,
    SchemaError,
    TransactionError,
    TimeoutError,
    ResourceError,
    SerializationError,
    NetworkError,
    RetryableError,
    NonRetryableError,
    CriticalError,
    WarningError,
    ErrorContext,
    ErrorHandler,
    error_handler
)

__all__ = [
    # Base exception classes
    'UnifiedError',
    'ConfigurationError',
    'ConnectionError', 
    'AuthenticationError',
    'AuthorizationError',
    'ValidationError',
    'DataError',
    'QueryError',
    'IndexError',
    'SchemaError',
    'TransactionError',
    'TimeoutError',
    'ResourceError',
    'SerializationError',
    'NetworkError',
    
    # Error classification
    'RetryableError',
    'NonRetryableError',
    'CriticalError',
    'WarningError',
    
    # Error handling utilities
    'ErrorContext',
    'ErrorHandler',
    'error_handler'
]