"""Logging utilities and configuration for the unified query language interpreter."""

import logging
import logging.handlers
import sys
import os
import json
from typing import Dict, Any, Optional, Union, TextIO
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path


class LogLevel(str, Enum):
    """Log levels for the application."""
    
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class LogFormat(str, Enum):
    """Log output formats."""
    
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


class QueryLogType(str, Enum):
    """Types of query-related log events."""
    
    QUERY_START = "query_start"
    QUERY_COMPLETE = "query_complete"
    QUERY_ERROR = "query_error"
    QUERY_CANCELLED = "query_cancelled"
    PARSE_START = "parse_start"
    PARSE_COMPLETE = "parse_complete"
    PARSE_ERROR = "parse_error"
    VALIDATION_START = "validation_start"
    VALIDATION_COMPLETE = "validation_complete"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_START = "execution_start"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_ERROR = "execution_error"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PRIVACY_APPLIED = "privacy_applied"


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON log output."""
    
    def __init__(self, include_timestamp: bool = True, include_level: bool = True):
        """Initialize the JSON formatter.
        
        Args:
            include_timestamp: Whether to include timestamp in output
            include_level: Whether to include log level in output
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string
        """
        log_entry = {
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if self.include_timestamp:
            log_entry['timestamp'] = datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat()
        
        if self.include_level:
            log_entry['level'] = record.levelname
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'):
                log_entry[key] = value
        
        # Handle exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=self._json_default)
    
    def _json_default(self, obj: Any) -> str:
        """Default JSON serializer for non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)


class StructuredFormatter(logging.Formatter):
    """Structured formatter with key-value pairs."""
    
    def __init__(self, format_string: Optional[str] = None):
        """Initialize the structured formatter.
        
        Args:
            format_string: Custom format string
        """
        if format_string is None:
            format_string = (
                '%(asctime)s | %(levelname)-8s | %(name)s | '
                '%(funcName)s:%(lineno)d | %(message)s'
            )
        super().__init__(format_string)


class QueryLogger:
    """Specialized logger for query-related events."""
    
    def __init__(self, name: str = "query_logger", level: LogLevel = LogLevel.INFO):
        """Initialize the query logger.
        
        Args:
            name: Logger name
            level: Log level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        
        # Prevent duplicate logs
        self.logger.propagate = False
        
        # Add default handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
    
    def log_query_event(
        self,
        event_type: QueryLogType,
        query_id: str,
        message: Optional[str] = None,
        user_id: Optional[str] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ) -> None:
        """Log a query-related event.
        
        Args:
            event_type: Type of query event
            query_id: Query identifier
            message: Optional message
            user_id: User identifier
            execution_time: Execution time in seconds
            **kwargs: Additional context data
        """
        log_data = {
            'event_type': event_type.value,
            'query_id': query_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        if user_id:
            log_data['user_id'] = user_id
        
        if execution_time is not None:
            log_data['execution_time_seconds'] = execution_time
        
        # Add any additional context
        log_data.update(kwargs)
        
        # Choose log level based on event type
        if event_type in [QueryLogType.QUERY_ERROR, QueryLogType.PARSE_ERROR,
                         QueryLogType.VALIDATION_ERROR, QueryLogType.EXECUTION_ERROR]:
            level = logging.ERROR
        elif event_type == QueryLogType.ACCESS_DENIED:
            level = logging.WARNING
        else:
            level = logging.INFO
        
        # Create message if not provided
        if not message:
            message = f"Query event: {event_type.value}"
        
        self.logger.log(level, message, extra=log_data)
    
    def log_query_start(self, query_id: str, query: str, user_id: Optional[str] = None) -> None:
        """Log query start event."""
        self.log_query_event(
            QueryLogType.QUERY_START,
            query_id,
            message=f"Starting query execution: {query_id}",
            user_id=user_id,
            query_text=query
        )
    
    def log_query_complete(
        self,
        query_id: str,
        execution_time: float,
        result_count: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log query completion event."""
        self.log_query_event(
            QueryLogType.QUERY_COMPLETE,
            query_id,
            message=f"Query completed: {query_id}",
            user_id=user_id,
            execution_time=execution_time,
            result_count=result_count
        )
    
    def log_query_error(
        self,
        query_id: str,
        error: str,
        execution_time: Optional[float] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log query error event."""
        self.log_query_event(
            QueryLogType.QUERY_ERROR,
            query_id,
            message=f"Query error: {query_id} - {error}",
            user_id=user_id,
            execution_time=execution_time,
            error_message=error
        )
    
    def log_access_denied(
        self,
        query_id: str,
        user_id: str,
        reason: str,
        resource: Optional[str] = None
    ) -> None:
        """Log access denied event."""
        self.log_query_event(
            QueryLogType.ACCESS_DENIED,
            query_id,
            message=f"Access denied for user {user_id}: {reason}",
            user_id=user_id,
            denial_reason=reason,
            resource=resource
        )
    
    def log_privacy_applied(
        self,
        query_id: str,
        privacy_action: str,
        affected_fields: Optional[list] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log privacy protection applied event."""
        self.log_query_event(
            QueryLogType.PRIVACY_APPLIED,
            query_id,
            message=f"Privacy protection applied: {privacy_action}",
            user_id=user_id,
            privacy_action=privacy_action,
            affected_fields=affected_fields
        )


class LoggingConfig:
    """Configuration for logging setup."""
    
    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        format_type: LogFormat = LogFormat.STRUCTURED,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        log_to_console: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        include_query_logger: bool = True
    ):
        """Initialize logging configuration.
        
        Args:
            level: Log level
            format_type: Log format type
            log_to_file: Whether to log to file
            log_file_path: Path to log file
            log_to_console: Whether to log to console
            max_file_size: Maximum log file size in bytes
            backup_count: Number of backup files to keep
            include_query_logger: Whether to include specialized query logger
        """
        self.level = level
        self.format_type = format_type
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        self.log_to_console = log_to_console
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.include_query_logger = include_query_logger


def create_formatter(format_type: LogFormat) -> logging.Formatter:
    """Create a formatter based on format type.
    
    Args:
        format_type: Format type to create
        
    Returns:
        Logging formatter instance
    """
    if format_type == LogFormat.SIMPLE:
        return logging.Formatter('%(levelname)s: %(message)s')
    
    elif format_type == LogFormat.DETAILED:
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    
    elif format_type == LogFormat.JSON:
        return JSONFormatter()
    
    elif format_type == LogFormat.STRUCTURED:
        return StructuredFormatter()
    
    else:
        return StructuredFormatter()


def configure_logging(config: Optional[LoggingConfig] = None) -> Dict[str, logging.Logger]:
    """Configure logging for the application.
    
    Args:
        config: Logging configuration (default created if not provided)
        
    Returns:
        Dictionary of configured loggers
    """
    if config is None:
        config = LoggingConfig()
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    loggers = {}
    
    # Configure root logger
    root_logger.setLevel(getattr(logging, config.level.value))
    formatter = create_formatter(config.format_type)
    
    # Add console handler if requested
    if config.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if config.log_to_file:
        log_file_path = config.log_file_path
        if not log_file_path:
            # Create default log file path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file_path = log_dir / "query_interpreter.log"
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    loggers['root'] = root_logger
    
    # Create specialized loggers
    if config.include_query_logger:
        query_logger = QueryLogger("query_logger", config.level)
        loggers['query'] = query_logger.logger
    
    # Create component-specific loggers
    component_loggers = [
        'parser', 'engine', 'executor', 'validator', 'formatter',
        'service_registry', 'detector', 'enforcer', 'analyzer'
    ]
    
    for component in component_loggers:
        logger = logging.getLogger(f"query_interpreter.{component}")
        logger.setLevel(getattr(logging, config.level.value))
        loggers[component] = logger
    
    return loggers


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def setup_query_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.STRUCTURED,
    log_file: Optional[str] = None
) -> QueryLogger:
    """Set up specialized query logging.
    
    Args:
        log_level: Log level for query events
        log_format: Format for log output
        log_file: Optional log file path
        
    Returns:
        Configured QueryLogger instance
    """
    # Configure basic logging first
    config = LoggingConfig(
        level=log_level,
        format_type=log_format,
        log_to_file=log_file is not None,
        log_file_path=log_file,
        include_query_logger=True
    )
    
    loggers = configure_logging(config)
    
    # Return the query logger
    return QueryLogger("query_logger", log_level)


def log_performance_metric(
    logger: logging.Logger,
    metric_name: str,
    value: float,
    unit: str = "seconds",
    **context
) -> None:
    """Log a performance metric.
    
    Args:
        logger: Logger instance
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        **context: Additional context information
    """
    log_data = {
        'metric_name': metric_name,
        'metric_value': value,
        'metric_unit': unit,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **context
    }
    
    logger.info(f"Performance metric: {metric_name} = {value} {unit}", extra=log_data)


def create_audit_logger(name: str = "audit") -> logging.Logger:
    """Create an audit logger with specific formatting.
    
    Args:
        name: Logger name
        
    Returns:
        Configured audit logger
    """
    audit_logger = logging.getLogger(name)
    audit_logger.setLevel(logging.INFO)
    
    # Create audit-specific formatter
    audit_formatter = logging.Formatter(
        '%(asctime)s | AUDIT | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add file handler for audit logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    audit_file = log_dir / "audit.log"
    
    file_handler = logging.handlers.RotatingFileHandler(
        audit_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10
    )
    file_handler.setFormatter(audit_formatter)
    
    audit_logger.addHandler(file_handler)
    audit_logger.propagate = False  # Don't propagate to root logger
    
    return audit_logger


# Default loggers
_default_config = LoggingConfig()
_default_loggers = configure_logging(_default_config)

# Export commonly used loggers
default_logger = _default_loggers['root']
query_logger = QueryLogger() if _default_config.include_query_logger else None
audit_logger = create_audit_logger()