"""
Result and response pattern implementations.

This module provides standardized result patterns for handling
operation outcomes, error reporting, and data packaging across
both persona implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Callable
from dataclasses import dataclass, field
import datetime
from enum import Enum
import traceback

# Type variable for generic results
T = TypeVar('T')

# Factory function for default datetime
def _now():
    return datetime.datetime.now()


class ResultStatus(Enum):
    """Standard result status codes."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"
    PENDING = "pending"
    CANCELLED = "cancelled"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Detailed error information."""
    code: str
    message: str
    timestamp: datetime.datetime = field(default_factory=_now)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    traceback: Optional[str] = None
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        field: Optional[str] = None
    ) -> 'ErrorInfo':
        """Create ErrorInfo from an exception."""
        return cls(
            code=code or exception.__class__.__name__,
            message=str(exception),
            severity=severity,
            field=field,
            traceback=traceback.format_exc()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class WarningInfo:
    """Warning information."""
    message: str
    timestamp: datetime.datetime = field(default_factory=_now)
    code: Optional[str] = None
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "message": self.message,
            "code": self.code,
            "field": self.field,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class Result(Generic[T]):
    """
    Generic result container with comprehensive error handling.
    
    Provides a standardized way to return operation results with
    success/failure status, data, errors, warnings, and metadata.
    """
    
    def __init__(
        self,
        status: ResultStatus = ResultStatus.SUCCESS,
        data: Optional[T] = None,
        message: Optional[str] = None,
        errors: Optional[List[ErrorInfo]] = None,
        warnings: Optional[List[WarningInfo]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize result.
        
        Args:
            status: Result status
            data: Result data
            message: Optional result message
            errors: List of errors
            warnings: List of warnings
            metadata: Additional metadata
        """
        self.status = status
        self.data = data
        self.message = message
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.timestamp = datetime.datetime.now()
    
    @property
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == ResultStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """Check if result has errors."""
        return self.status == ResultStatus.ERROR
    
    @property
    def has_errors(self) -> bool:
        """Check if result has any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """Get number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Get number of warnings."""
        return len(self.warnings)
    
    @classmethod
    def success(
        cls,
        data: Optional[T] = None,
        message: Optional[str] = None,
        warnings: Optional[List[WarningInfo]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Create a successful result."""
        return cls(
            status=ResultStatus.SUCCESS,
            data=data,
            message=message,
            warnings=warnings,
            metadata=metadata
        )
    
    @classmethod
    def error(
        cls,
        message: str,
        code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Create an error result."""
        error = ErrorInfo(
            code=code or "ERROR",
            message=message,
            severity=severity,
            field=field,
            details=details
        )
        
        return cls(
            status=ResultStatus.ERROR,
            errors=[error],
            metadata=metadata
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        message: Optional[str] = None,
        code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        field: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Create error result from exception."""
        error = ErrorInfo.from_exception(exception, code, severity, field)
        
        return cls(
            status=ResultStatus.ERROR,
            message=message or str(exception),
            errors=[error],
            metadata=metadata
        )
    
    @classmethod
    def warning(
        cls,
        data: Optional[T] = None,
        message: str = None,
        warning_message: str = None,
        code: Optional[str] = None,
        field: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Create a warning result."""
        warning = WarningInfo(
            message=warning_message or message or "Warning occurred",
            code=code,
            field=field
        )
        
        return cls(
            status=ResultStatus.WARNING,
            data=data,
            message=message,
            warnings=[warning],
            metadata=metadata
        )
    
    def add_error(
        self,
        message: str,
        code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Add an error to the result."""
        error = ErrorInfo(
            code=code or "ERROR",
            message=message,
            severity=severity,
            field=field,
            details=details
        )
        
        self.errors.append(error)
        
        if self.status == ResultStatus.SUCCESS:
            self.status = ResultStatus.ERROR
        
        return self
    
    def add_warning(
        self,
        message: str,
        code: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'Result[T]':
        """Add a warning to the result."""
        warning = WarningInfo(
            message=message,
            code=code,
            field=field,
            details=details
        )
        
        self.warnings.append(warning)
        return self
    
    def merge(self, other: 'Result') -> 'Result[T]':
        """
        Merge with another result.
        
        Args:
            other: Other result to merge
            
        Returns:
            New result with merged data
        """
        # Determine combined status
        if self.is_error or other.is_error:
            combined_status = ResultStatus.ERROR
        elif self.has_warnings or other.has_warnings:
            combined_status = ResultStatus.WARNING
        else:
            combined_status = ResultStatus.SUCCESS
        
        # Combine data (prefer non-None values)
        combined_data = self.data if self.data is not None else other.data
        
        # Combine messages
        messages = [msg for msg in [self.message, other.message] if msg]
        combined_message = "; ".join(messages) if messages else None
        
        # Merge metadata
        combined_metadata = {**self.metadata, **other.metadata}
        
        return Result(
            status=combined_status,
            data=combined_data,
            message=combined_message,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            metadata=combined_metadata
        )
    
    def map(self, func: Callable[[T], Any]) -> 'Result':
        """
        Apply function to data if result is successful.
        
        Args:
            func: Function to apply to data
            
        Returns:
            New result with transformed data
        """
        if self.is_success and self.data is not None:
            try:
                new_data = func(self.data)
                return Result.success(
                    data=new_data,
                    message=self.message,
                    warnings=self.warnings,
                    metadata=self.metadata
                )
            except Exception as e:
                return Result.from_exception(e, metadata=self.metadata)
        else:
            # Return copy of current result without transformation
            return Result(
                status=self.status,
                data=self.data,
                message=self.message,
                errors=self.errors,
                warnings=self.warnings,
                metadata=self.metadata
            )
    
    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """
        Convert result to dictionary representation.
        
        Args:
            include_traceback: Whether to include error tracebacks
            
        Returns:
            Dictionary representation of result
        """
        result_dict = {
            "status": self.status.value,
            "success": self.is_success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "error_count": self.error_count,
            "warning_count": self.warning_count
        }
        
        # Add errors
        if self.errors:
            error_dicts = []
            for error in self.errors:
                error_dict = error.to_dict()
                if not include_traceback:
                    error_dict.pop("traceback", None)
                error_dicts.append(error_dict)
            result_dict["errors"] = error_dicts
        
        # Add warnings
        if self.warnings:
            result_dict["warnings"] = [warning.to_dict() for warning in self.warnings]
        
        return result_dict
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the result."""
        parts = [f"Status: {self.status.value}"]
        
        if self.message:
            parts.append(f"Message: {self.message}")
        
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        
        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
        
        if self.data is not None:
            parts.append(f"Data: {type(self.data).__name__}")
        
        return " | ".join(parts)
    
    def __str__(self) -> str:
        """String representation of result."""
        return self.get_summary()
    
    def __bool__(self) -> bool:
        """Boolean conversion (True if successful)."""
        return self.is_success


class ProcessingResult(Result[T]):
    """
    Specialized result for data processing operations.
    
    Extends Result with processing-specific information
    like item counts, processing time, and performance metrics.
    """
    
    def __init__(
        self,
        status: ResultStatus = ResultStatus.SUCCESS,
        data: Optional[T] = None,
        message: Optional[str] = None,
        errors: Optional[List[ErrorInfo]] = None,
        warnings: Optional[List[WarningInfo]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        items_processed: int = 0,
        items_successful: int = 0,
        items_failed: int = 0,
        processing_time: Optional[float] = None
    ):
        """
        Initialize processing result.
        
        Args:
            status: Result status
            data: Result data
            message: Optional result message
            errors: List of errors
            warnings: List of warnings
            metadata: Additional metadata
            items_processed: Total number of items processed
            items_successful: Number of items processed successfully
            items_failed: Number of items that failed processing
            processing_time: Processing time in seconds
        """
        super().__init__(status, data, message, errors, warnings, metadata)
        
        self.items_processed = items_processed
        self.items_successful = items_successful
        self.items_failed = items_failed
        self.processing_time = processing_time
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.items_processed == 0:
            return 0.0
        return (self.items_successful / self.items_processed) * 100
    
    @property
    def items_per_second(self) -> Optional[float]:
        """Calculate processing rate in items per second."""
        if self.processing_time is None or self.processing_time == 0:
            return None
        return self.items_processed / self.processing_time
    
    @classmethod
    def processing_success(
        cls,
        data: Optional[T] = None,
        items_processed: int = 0,
        processing_time: Optional[float] = None,
        message: Optional[str] = None,
        warnings: Optional[List[WarningInfo]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ProcessingResult[T]':
        """Create successful processing result."""
        return cls(
            status=ResultStatus.SUCCESS,
            data=data,
            message=message,
            warnings=warnings,
            metadata=metadata,
            items_processed=items_processed,
            items_successful=items_processed,
            items_failed=0,
            processing_time=processing_time
        )
    
    @classmethod
    def partial_success(
        cls,
        data: Optional[T] = None,
        items_processed: int = 0,
        items_successful: int = 0,
        items_failed: int = 0,
        processing_time: Optional[float] = None,
        message: Optional[str] = None,
        errors: Optional[List[ErrorInfo]] = None,
        warnings: Optional[List[WarningInfo]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ProcessingResult[T]':
        """Create partial success processing result."""
        return cls(
            status=ResultStatus.PARTIAL,
            data=data,
            message=message,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
            items_processed=items_processed,
            items_successful=items_successful,
            items_failed=items_failed,
            processing_time=processing_time
        )
    
    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with processing metrics."""
        result_dict = super().to_dict(include_traceback)
        
        result_dict.update({
            "items_processed": self.items_processed,
            "items_successful": self.items_successful,
            "items_failed": self.items_failed,
            "success_rate": self.success_rate,
            "processing_time": self.processing_time,
            "items_per_second": self.items_per_second
        })
        
        return result_dict
    
    def get_summary(self) -> str:
        """Get processing-specific summary."""
        parts = [super().get_summary()]
        
        parts.append(f"Processed: {self.items_processed}")
        parts.append(f"Success Rate: {self.success_rate:.1f}%")
        
        if self.processing_time:
            parts.append(f"Time: {self.processing_time:.2f}s")
        
        if self.items_per_second:
            parts.append(f"Rate: {self.items_per_second:.1f} items/s")
        
        return " | ".join(parts)


class ResultCollector:
    """
    Utility for collecting and aggregating multiple results.
    
    Useful for batch operations or when combining results
    from multiple sources or operations.
    """
    
    def __init__(self):
        self.results: List[Result] = []
    
    def add(self, result: Result) -> None:
        """Add a result to the collection."""
        self.results.append(result)
    
    def add_success(self, data: Any = None, message: str = None) -> None:
        """Add a successful result."""
        self.add(Result.success(data=data, message=message))
    
    def add_error(self, message: str, code: str = None) -> None:
        """Add an error result."""
        self.add(Result.error(message=message, code=code))
    
    def add_warning(self, data: Any = None, message: str = None, warning_message: str = None) -> None:
        """Add a warning result."""
        self.add(Result.warning(data=data, message=message, warning_message=warning_message))
    
    def aggregate(self) -> Result:
        """
        Aggregate all collected results into a single result.
        
        Returns:
            Aggregated result containing all data, errors, and warnings
        """
        if not self.results:
            return Result.success()
        
        # Start with first result
        aggregated = self.results[0]
        
        # Merge with remaining results
        for result in self.results[1:]:
            aggregated = aggregated.merge(result)
        
        return aggregated
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about collected results."""
        total = len(self.results)
        success_count = sum(1 for r in self.results if r.is_success)
        error_count = sum(1 for r in self.results if r.is_error)
        warning_count = sum(1 for r in self.results if r.has_warnings)
        
        return {
            "total_results": total,
            "success_count": success_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "total_errors": sum(len(r.errors) for r in self.results),
            "total_warnings": sum(len(r.warnings) for r in self.results)
        }
    
    def get_all_errors(self) -> List[ErrorInfo]:
        """Get all errors from collected results."""
        all_errors = []
        for result in self.results:
            all_errors.extend(result.errors)
        return all_errors
    
    def get_all_warnings(self) -> List[WarningInfo]:
        """Get all warnings from collected results."""
        all_warnings = []
        for result in self.results:
            all_warnings.extend(result.warnings)
        return all_warnings
    
    def clear(self) -> None:
        """Clear all collected results."""
        self.results.clear()


def safe_operation(func: Callable, *args, **kwargs) -> Result:
    """
    Execute a function safely and return a Result.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function
        
    Returns:
        Result with function output or error information
    """
    try:
        result = func(*args, **kwargs)
        return Result.success(data=result)
    except Exception as e:
        return Result.from_exception(e)


def chain_operations(*operations: Callable[[], Result]) -> Result:
    """
    Chain multiple operations, stopping on first error.
    
    Args:
        *operations: Functions that return Result objects
        
    Returns:
        Result of the chain (success if all succeed, first error otherwise)
    """
    results = []
    
    for operation in operations:
        result = operation()
        results.append(result)
        
        if not result.is_success:
            # Return failed result immediately
            return result
    
    # All operations succeeded, merge results
    if results:
        final_result = results[0]
        for result in results[1:]:
            final_result = final_result.merge(result)
        return final_result
    else:
        return Result.success()


def parallel_operation_results(results: List[Result]) -> Result:
    """
    Combine results from parallel operations.
    
    Args:
        results: List of results from parallel operations
        
    Returns:
        Combined result with aggregated status
    """
    collector = ResultCollector()
    for result in results:
        collector.add(result)
    
    return collector.aggregate()