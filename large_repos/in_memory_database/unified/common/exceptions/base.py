"""Base exception classes for the unified library."""

from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
import logging
import traceback
import functools
import time
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    CONFIGURATION = "configuration"
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATA = "data"
    QUERY = "query"
    INDEX = "index"
    SCHEMA = "schema"
    TRANSACTION = "transaction"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    SERIALIZATION = "serialization"
    NETWORK = "network"
    SYSTEM = "system"
    USER = "user"


@dataclass
class ErrorContext:
    """Context information for errors."""
    timestamp: datetime = field(default_factory=datetime.now)
    operation: Optional[str] = None
    component: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'operation': self.operation,
            'component': self.component,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'trace_id': self.trace_id,
            'metadata': self.metadata
        }


class UnifiedError(Exception):
    """Base exception class for the unified library."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: Optional[ErrorCategory] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize unified error.
        
        Args:
            message: Error message
            error_code: Unique error code
            category: Error category
            severity: Error severity level
            context: Error context information
            cause: Root cause exception
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category or ErrorCategory.SYSTEM
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.details = details or {}
        self.traceback_info = traceback.format_exc()
        
        # Log error based on severity
        self._log_error()
    
    def _log_error(self) -> None:
        """Log error based on severity."""
        log_data = {
            'error_code': self.error_code,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context.to_dict(),
            'details': self.details
        }
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"{self.message}", extra=log_data, exc_info=True)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"{self.message}", extra=log_data, exc_info=True)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"{self.message}", extra=log_data)
        else:
            logger.info(f"{self.message}", extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context.to_dict(),
            'details': self.details,
            'cause': str(self.cause) if self.cause else None
        }
    
    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        return isinstance(self, RetryableError)
    
    def is_critical(self) -> bool:
        """Check if error is critical."""
        return self.severity == ErrorSeverity.CRITICAL
    
    def __str__(self) -> str:
        """String representation of error."""
        parts = [f"[{self.error_code}] {self.message}"]
        
        if self.context.operation:
            parts.append(f"Operation: {self.context.operation}")
        
        if self.context.component:
            parts.append(f"Component: {self.context.component}")
        
        if self.details:
            parts.append(f"Details: {self.details}")
        
        return " | ".join(parts)


# Configuration and setup errors
class ConfigurationError(UnifiedError):
    """Error in configuration or setup."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONFIGURATION)
        kwargs.setdefault('details', {}).update({'config_key': config_key})
        super().__init__(message, **kwargs)


# Connection and network errors
class ConnectionError(UnifiedError):
    """Connection-related error."""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONNECTION)
        kwargs.setdefault('details', {}).update({'host': host, 'port': port})
        super().__init__(message, **kwargs)


class NetworkError(UnifiedError):
    """Network-related error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.NETWORK)
        kwargs.setdefault('details', {}).update({'status_code': status_code})
        super().__init__(message, **kwargs)


# Authentication and authorization errors
class AuthenticationError(UnifiedError):
    """Authentication failure."""
    
    def __init__(self, message: str, user_id: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHENTICATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        if user_id and kwargs.get('context'):
            kwargs['context'].user_id = user_id
        super().__init__(message, **kwargs)


class AuthorizationError(UnifiedError):
    """Authorization failure."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUTHORIZATION)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('details', {}).update({'required_permission': required_permission})
        super().__init__(message, **kwargs)


# Data validation and integrity errors
class ValidationError(UnifiedError):
    """Data validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('details', {}).update({'field': field, 'value': str(value) if value is not None else None})
        super().__init__(message, **kwargs)


class DataError(UnifiedError):
    """Data-related error."""
    
    def __init__(self, message: str, data_type: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.DATA)
        kwargs.setdefault('details', {}).update({'data_type': data_type})
        super().__init__(message, **kwargs)


class SchemaError(UnifiedError):
    """Schema-related error."""
    
    def __init__(self, message: str, schema_name: Optional[str] = None, version: Optional[int] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SCHEMA)
        kwargs.setdefault('details', {}).update({'schema_name': schema_name, 'version': version})
        super().__init__(message, **kwargs)


# Query and database operation errors
class QueryError(UnifiedError):
    """Query execution error."""
    
    def __init__(self, message: str, query: Optional[str] = None, table: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.QUERY)
        kwargs.setdefault('details', {}).update({'query': query, 'table': table})
        super().__init__(message, **kwargs)


class IndexError(UnifiedError):
    """Index-related error."""
    
    def __init__(self, message: str, index_name: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.INDEX)
        kwargs.setdefault('details', {}).update({'index_name': index_name})
        super().__init__(message, **kwargs)


class TransactionError(UnifiedError):
    """Transaction-related error."""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TRANSACTION)
        kwargs.setdefault('details', {}).update({'transaction_id': transaction_id})
        super().__init__(message, **kwargs)


# Resource and performance errors
class TimeoutError(UnifiedError):
    """Timeout error."""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TIMEOUT)
        kwargs.setdefault('details', {}).update({'timeout_duration': timeout_duration})
        super().__init__(message, **kwargs)


class ResourceError(UnifiedError):
    """Resource-related error."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.RESOURCE)
        kwargs.setdefault('details', {}).update({'resource_type': resource_type})
        super().__init__(message, **kwargs)


# Serialization errors
class SerializationError(UnifiedError):
    """Serialization/deserialization error."""
    
    def __init__(self, message: str, format_type: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.SERIALIZATION)
        kwargs.setdefault('details', {}).update({'format_type': format_type})
        super().__init__(message, **kwargs)


# Error classification mixins
class RetryableError(UnifiedError):
    """Mixin for retryable errors."""
    
    def __init__(self, message: str, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        kwargs.setdefault('details', {}).update({
            'max_retries': max_retries,
            'retry_delay': retry_delay
        })
        super().__init__(message, **kwargs)
    
    def can_retry(self) -> bool:
        """Check if error can still be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1


class NonRetryableError(UnifiedError):
    """Mixin for non-retryable errors."""
    pass


class CriticalError(UnifiedError):
    """Critical error that requires immediate attention."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class WarningError(UnifiedError):
    """Warning-level error."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        super().__init__(message, **kwargs)


# Error handling utilities
class ErrorHandler:
    """Centralized error handling and reporting."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_callbacks: List[Callable[[UnifiedError], None]] = []
        self.error_stats: Dict[str, int] = {}
    
    def register_callback(self, callback: Callable[[UnifiedError], None]) -> None:
        """Register error callback.
        
        Args:
            callback: Function to call when error occurs
        """
        self.error_callbacks.append(callback)
    
    def handle_error(self, error: UnifiedError) -> None:
        """Handle error by calling registered callbacks.
        
        Args:
            error: Error to handle
        """
        # Update stats
        error_type = error.__class__.__name__
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        
        # Call callbacks
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics.
        
        Returns:
            Dictionary of error type counts
        """
        return self.error_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset error statistics."""
        self.error_stats.clear()


# Global error handler
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler."""
    return _global_error_handler


def error_handler(
    *,
    reraise: bool = True,
    default_return: Any = None,
    error_types: Optional[Union[Type[Exception], tuple]] = None,
    callback: Optional[Callable[[Exception], None]] = None,
    max_retries: int = 0,
    retry_delay: float = 1.0
):
    """Decorator for error handling with retry logic.
    
    Args:
        reraise: Whether to reraise the exception
        default_return: Default return value on error
        error_types: Exception types to handle (None for all)
        callback: Callback function for errors
        max_retries: Maximum number of retries
        retry_delay: Delay between retries
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should handle this error type
                    if error_types and not isinstance(e, error_types):
                        raise
                    
                    # Convert to unified error if needed
                    if not isinstance(e, UnifiedError):
                        unified_error = UnifiedError(
                            message=str(e),
                            cause=e,
                            context=ErrorContext(operation=func.__name__)
                        )
                    else:
                        unified_error = e
                    
                    # Handle error
                    _global_error_handler.handle_error(unified_error)
                    
                    # Call custom callback if provided
                    if callback:
                        try:
                            callback(unified_error)
                        except Exception as callback_error:
                            logger.error(f"Error in callback: {callback_error}")
                    
                    # Check if we can retry
                    if attempt < max_retries:
                        if isinstance(unified_error, RetryableError) and unified_error.can_retry():
                            unified_error.increment_retry()
                            logger.info(f"Retrying operation (attempt {attempt + 2}/{max_retries + 1}) after error: {e}")
                            time.sleep(retry_delay)
                            continue
                        elif not isinstance(unified_error, (RetryableError, NonRetryableError)):
                            # Default retry behavior for non-classified errors
                            logger.info(f"Retrying operation (attempt {attempt + 2}/{max_retries + 1}) after error: {e}")
                            time.sleep(retry_delay)
                            continue
                    
                    # No more retries or non-retryable error
                    break
            
            # Handle final error
            if reraise:
                raise last_exception
            else:
                return default_return
        
        return wrapper
    return decorator


# Specific retryable error subclasses
class RetryableConnectionError(ConnectionError, RetryableError):
    """Retryable connection error."""
    pass


class RetryableTimeoutError(TimeoutError, RetryableError):
    """Retryable timeout error."""
    pass


class RetryableNetworkError(NetworkError, RetryableError):
    """Retryable network error."""
    pass


# Specific non-retryable error subclasses
class NonRetryableAuthenticationError(AuthenticationError, NonRetryableError):
    """Non-retryable authentication error."""
    pass


class NonRetryableAuthorizationError(AuthorizationError, NonRetryableError):
    """Non-retryable authorization error."""
    pass


class NonRetryableValidationError(ValidationError, NonRetryableError):
    """Non-retryable validation error."""
    pass