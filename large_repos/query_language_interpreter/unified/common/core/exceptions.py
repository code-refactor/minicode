"""Common exception classes for the unified query language interpreter."""

from typing import Optional, Dict, Any


class QueryInterpreterError(Exception):
    """Base exception for all query interpreter errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class QueryParsingError(QueryInterpreterError):
    """Exception raised when query parsing fails."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        position: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the parsing error.
        
        Args:
            message: Error message
            query: The query string that failed to parse
            position: Position in query where error occurred
            details: Additional error details
        """
        super().__init__(message, details)
        self.query = query
        self.position = position


class QueryValidationError(QueryInterpreterError):
    """Exception raised when query validation fails."""
    
    def __init__(
        self,
        message: str,
        query_id: Optional[str] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the validation error.
        
        Args:
            message: Error message
            query_id: ID of the query that failed validation
            validation_rule: Name of the validation rule that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.query_id = query_id
        self.validation_rule = validation_rule


class QueryEngineError(QueryInterpreterError):
    """Exception raised by query engine operations."""
    
    def __init__(
        self,
        message: str,
        query_id: Optional[str] = None,
        engine_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the query engine error.
        
        Args:
            message: Error message
            query_id: ID of the query being executed
            engine_type: Type of query engine
            details: Additional error details
        """
        super().__init__(message, details)
        self.query_id = query_id
        self.engine_type = engine_type


class ExecutionError(QueryInterpreterError):
    """Exception raised during query execution."""
    
    def __init__(
        self,
        message: str,
        query_id: Optional[str] = None,
        execution_phase: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the execution error.
        
        Args:
            message: Error message
            query_id: ID of the query being executed
            execution_phase: Phase of execution where error occurred
            details: Additional error details
        """
        super().__init__(message, details)
        self.query_id = query_id
        self.execution_phase = execution_phase


class DataSourceError(QueryInterpreterError):
    """Exception raised by data source operations."""
    
    def __init__(
        self,
        message: str,
        data_source: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the data source error.
        
        Args:
            message: Error message
            data_source: Name of the data source
            operation: Operation that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.data_source = data_source
        self.operation = operation


class AccessDeniedError(QueryInterpreterError):
    """Exception raised when access to resources is denied."""
    
    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the access denied error.
        
        Args:
            message: Error message
            user_id: ID of the user being denied access
            resource: Resource that access was denied to
            required_permission: Permission required for access
            details: Additional error details
        """
        super().__init__(message, details)
        self.user_id = user_id
        self.resource = resource
        self.required_permission = required_permission


class AuthenticationError(QueryInterpreterError):
    """Exception raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        user_id: Optional[str] = None,
        auth_method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the authentication error.
        
        Args:
            message: Error message
            user_id: ID of the user attempting authentication
            auth_method: Authentication method used
            details: Additional error details
        """
        super().__init__(message, details)
        self.user_id = user_id
        self.auth_method = auth_method


class PolicyViolationError(QueryInterpreterError):
    """Exception raised when a policy is violated."""
    
    def __init__(
        self,
        message: str,
        policy_name: Optional[str] = None,
        violation_type: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the policy violation error.
        
        Args:
            message: Error message
            policy_name: Name of the violated policy
            violation_type: Type of violation
            user_id: ID of the user who violated the policy
            details: Additional error details
        """
        super().__init__(message, details)
        self.policy_name = policy_name
        self.violation_type = violation_type
        self.user_id = user_id


class PrivacyError(QueryInterpreterError):
    """Exception raised when privacy constraints are violated."""
    
    def __init__(
        self,
        message: str,
        privacy_rule: Optional[str] = None,
        sensitive_fields: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the privacy error.
        
        Args:
            message: Error message
            privacy_rule: Name of the privacy rule violated
            sensitive_fields: List of sensitive fields involved
            details: Additional error details
        """
        super().__init__(message, details)
        self.privacy_rule = privacy_rule
        self.sensitive_fields = sensitive_fields or []


class ServiceError(QueryInterpreterError):
    """Exception raised by service operations."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        service_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the service error.
        
        Args:
            message: Error message
            service_name: Name of the service
            service_type: Type of service
            operation: Operation that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.service_name = service_name
        self.service_type = service_type
        self.operation = operation


class ConfigurationError(QueryInterpreterError):
    """Exception raised when configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that is invalid
            config_value: Configuration value that is invalid
            details: Additional error details
        """
        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value


class TimeoutError(QueryInterpreterError):
    """Exception raised when operations timeout."""
    
    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            operation: Operation that timed out
            details: Additional error details
        """
        super().__init__(message, details)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class ResourceError(QueryInterpreterError):
    """Exception raised when resource operations fail."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the resource error.
        
        Args:
            message: Error message
            resource_type: Type of resource
            resource_id: ID of the resource
            operation: Operation that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.operation = operation


class CacheError(QueryInterpreterError):
    """Exception raised by cache operations."""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the cache error.
        
        Args:
            message: Error message
            cache_key: Cache key involved in the operation
            operation: Cache operation that failed
            details: Additional error details
        """
        super().__init__(message, details)
        self.cache_key = cache_key
        self.operation = operation


class ValidationError(QueryInterpreterError):
    """Exception raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the validation error.
        
        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_rule: Validation rule that was violated
            details: Additional error details
        """
        super().__init__(message, details)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule


class SerializationError(QueryInterpreterError):
    """Exception raised during serialization/deserialization."""
    
    def __init__(
        self,
        message: str,
        object_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the serialization error.
        
        Args:
            message: Error message
            object_type: Type of object being serialized/deserialized
            operation: Operation that failed (serialize/deserialize)
            details: Additional error details
        """
        super().__init__(message, details)
        self.object_type = object_type
        self.operation = operation


def create_error_response(
    error: Exception,
    query_id: Optional[str] = None,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """Create a standardized error response dictionary.
    
    Args:
        error: The exception that occurred
        query_id: Optional query ID
        include_traceback: Whether to include the traceback
        
    Returns:
        Dictionary containing error information
    """
    import traceback
    
    error_response = {
        "error": True,
        "error_type": type(error).__name__,
        "message": str(error),
        "query_id": query_id
    }
    
    # Add specific error attributes if it's a QueryInterpreterError
    if isinstance(error, QueryInterpreterError):
        if hasattr(error, 'details') and error.details:
            error_response["details"] = error.details
        
        # Add specific attributes based on error type
        if isinstance(error, QueryParsingError):
            if error.query:
                error_response["query"] = error.query
            if error.position is not None:
                error_response["position"] = error.position
                
        elif isinstance(error, AccessDeniedError):
            if error.user_id:
                error_response["user_id"] = error.user_id
            if error.resource:
                error_response["resource"] = error.resource
            if error.required_permission:
                error_response["required_permission"] = error.required_permission
                
        elif isinstance(error, PolicyViolationError):
            if error.policy_name:
                error_response["policy_name"] = error.policy_name
            if error.violation_type:
                error_response["violation_type"] = error.violation_type
                
        elif isinstance(error, TimeoutError):
            if error.timeout_seconds is not None:
                error_response["timeout_seconds"] = error.timeout_seconds
            if error.operation:
                error_response["operation"] = error.operation
    
    # Include traceback if requested
    if include_traceback:
        error_response["traceback"] = traceback.format_exc()
    
    return error_response