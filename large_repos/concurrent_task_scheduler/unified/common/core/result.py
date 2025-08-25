"""Result type for error handling in the unified task scheduling library."""

from dataclasses import dataclass, field
from typing import Generic, Optional, TypeVar, Any, Dict

T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """
    A generic result wrapper for operations that may fail.
    
    This provides a consistent way to handle errors without exceptions,
    allowing for more explicit error handling in the codebase.
    """
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def ok(cls, value: T, **metadata) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, value=value, metadata=metadata)
    
    @classmethod
    def fail(cls, error: str, error_code: Optional[str] = None, **metadata) -> 'Result[T]':
        """Create a failed result."""
        return cls(success=False, error=error, error_code=error_code, metadata=metadata)
    
    def is_ok(self) -> bool:
        """Check if the result is successful."""
        return self.success
    
    def is_error(self) -> bool:
        """Check if the result is an error."""
        return not self.success
    
    def unwrap(self) -> T:
        """
        Get the value, raising an exception if result is an error.
        
        Raises:
            ValueError: If the result is an error
        """
        if not self.success:
            raise ValueError(f"Cannot unwrap error result: {self.error}")
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        """Get the value or return a default if error."""
        return self.value if self.success else default
    
    def map(self, func) -> 'Result':
        """
        Transform the value if successful.
        
        Args:
            func: Function to apply to the value
            
        Returns:
            New Result with transformed value or same error
        """
        if self.success:
            try:
                return Result.ok(func(self.value))
            except Exception as e:
                return Result.fail(str(e))
        return self
    
    def flat_map(self, func) -> 'Result':
        """
        Chain operations that return Results.
        
        Args:
            func: Function that returns a Result
            
        Returns:
            Result from func or current error
        """
        if self.success:
            return func(self.value)
        return self
    
    def __repr__(self) -> str:
        if self.success:
            return f"Result.ok({self.value!r})"
        return f"Result.fail({self.error!r})"


@dataclass
class OperationResult(Result[T]):
    """Extended result type with operation-specific metadata."""
    operation_name: Optional[str] = None
    duration_ms: Optional[float] = None
    retry_count: int = 0
    
    @classmethod
    def from_result(cls, result: Result[T], operation_name: str = None, **kwargs) -> 'OperationResult[T]':
        """Create an OperationResult from a regular Result."""
        return cls(
            success=result.success,
            value=result.value,
            error=result.error,
            error_code=result.error_code,
            metadata=result.metadata,
            operation_name=operation_name,
            **kwargs
        )


class ErrorCode:
    """Standard error codes for the scheduling system."""
    
    # Resource errors
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Job errors
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_ALREADY_EXISTS = "JOB_ALREADY_EXISTS"
    JOB_INVALID_STATE = "JOB_INVALID_STATE"
    JOB_DEPENDENCY_ERROR = "JOB_DEPENDENCY_ERROR"
    
    # Node errors
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    NODE_OFFLINE = "NODE_OFFLINE"
    NODE_CAPACITY_EXCEEDED = "NODE_CAPACITY_EXCEEDED"
    
    # Scheduling errors
    SCHEDULING_FAILED = "SCHEDULING_FAILED"
    NO_SUITABLE_NODE = "NO_SUITABLE_NODE"
    DEADLINE_IMPOSSIBLE = "DEADLINE_IMPOSSIBLE"
    
    # Dependency errors
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    
    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TIMEOUT = "TIMEOUT"


class SchedulingException(Exception):
    """Base exception for scheduling-related errors."""
    def __init__(self, message: str, error_code: str = None, **details):
        super().__init__(message)
        self.error_code = error_code
        self.details = details


class ResourceException(SchedulingException):
    """Exception for resource-related errors."""
    pass


class DependencyException(SchedulingException):
    """Exception for dependency-related errors."""
    pass


class NodeException(SchedulingException):
    """Exception for node-related errors."""
    pass