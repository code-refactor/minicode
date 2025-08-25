"""Base query engine for the unified query language interpreter."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Set, Callable
import time
import uuid
from datetime import datetime

from .base_models import (
    BaseQuery, 
    QueryResult, 
    ExecutionContext, 
    DataSourceConfig,
    QueryStatus
)
from .query_parser import BaseQueryParser
from .exceptions import QueryEngineError, DataSourceError, ExecutionError


class DataSourceManager:
    """Manager for data sources used by query engines."""
    
    def __init__(self):
        """Initialize the data source manager."""
        self._data_sources: Dict[str, Any] = {}
        self._data_source_configs: Dict[str, DataSourceConfig] = {}
        self._connection_pool: Dict[str, Any] = {}
    
    def register_data_source(self, config: DataSourceConfig, data_source: Any) -> None:
        """Register a data source with the manager.
        
        Args:
            config: Data source configuration
            data_source: The actual data source object
            
        Raises:
            DataSourceError: If registration fails
        """
        try:
            self._data_source_configs[config.name] = config
            self._data_sources[config.name] = data_source
        except Exception as e:
            raise DataSourceError(f"Failed to register data source '{config.name}': {str(e)}")
    
    def unregister_data_source(self, name: str) -> bool:
        """Unregister a data source.
        
        Args:
            name: Name of the data source to unregister
            
        Returns:
            True if the data source was unregistered successfully
        """
        removed = False
        
        if name in self._data_sources:
            del self._data_sources[name]
            removed = True
        
        if name in self._data_source_configs:
            del self._data_source_configs[name]
            removed = True
        
        if name in self._connection_pool:
            # Clean up any connections
            try:
                connection = self._connection_pool[name]
                if hasattr(connection, 'close'):
                    connection.close()
            except Exception:
                pass  # Ignore cleanup errors
            del self._connection_pool[name]
        
        return removed
    
    def get_data_source(self, name: str) -> Optional[Any]:
        """Get a data source by name.
        
        Args:
            name: Name of the data source
            
        Returns:
            Data source object or None if not found
        """
        return self._data_sources.get(name)
    
    def get_data_source_config(self, name: str) -> Optional[DataSourceConfig]:
        """Get a data source configuration by name.
        
        Args:
            name: Name of the data source
            
        Returns:
            Data source configuration or None if not found
        """
        return self._data_source_configs.get(name)
    
    def list_data_sources(self) -> List[str]:
        """List all registered data source names.
        
        Returns:
            List of data source names
        """
        return list(self._data_sources.keys())
    
    def validate_data_source_access(self, name: str, user_context: Dict[str, Any]) -> bool:
        """Validate if a user has access to a data source.
        
        Args:
            name: Name of the data source
            user_context: User context for access validation
            
        Returns:
            True if access is allowed
        """
        config = self._data_source_configs.get(name)
        if not config:
            return False
        
        # Check access permissions if defined
        permissions = config.access_permissions
        if permissions:
            # Basic role-based access control
            user_roles = set(user_context.get('roles', []))
            allowed_roles = set(permissions.get('allowed_roles', []))
            
            if allowed_roles and not user_roles.intersection(allowed_roles):
                return False
            
            # Check denied roles
            denied_roles = set(permissions.get('denied_roles', []))
            if denied_roles and user_roles.intersection(denied_roles):
                return False
        
        return True


class QueryEngineConfig:
    """Configuration for a query engine."""
    
    def __init__(
        self,
        max_results: int = 10000,
        default_timeout: float = 30.0,
        enable_caching: bool = False,
        cache_ttl: int = 300,
        enable_query_logging: bool = True,
        enable_performance_monitoring: bool = False,
        custom_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize query engine configuration.
        
        Args:
            max_results: Maximum number of results to return
            default_timeout: Default query timeout in seconds
            enable_caching: Whether to enable query result caching
            cache_ttl: Cache time-to-live in seconds
            enable_query_logging: Whether to log queries
            enable_performance_monitoring: Whether to monitor performance
            custom_config: Additional custom configuration
        """
        self.max_results = max_results
        self.default_timeout = default_timeout
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.enable_query_logging = enable_query_logging
        self.enable_performance_monitoring = enable_performance_monitoring
        self.custom_config = custom_config or {}


class BaseQueryEngine(ABC):
    """Base class for query engines that can be extended by different implementations."""
    
    def __init__(
        self,
        parser: BaseQueryParser,
        data_source_manager: Optional[DataSourceManager] = None,
        config: Optional[QueryEngineConfig] = None
    ):
        """Initialize the base query engine.
        
        Args:
            parser: Query parser instance
            data_source_manager: Data source manager (created if not provided)
            config: Engine configuration (default created if not provided)
        """
        self.parser = parser
        self.data_source_manager = data_source_manager or DataSourceManager()
        self.config = config or QueryEngineConfig()
        
        # Query execution tracking
        self.query_history: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        
        # Hook system
        self._pre_execute_hooks: List[Callable] = []
        self._post_execute_hooks: List[Callable] = []
        self._error_hooks: List[Callable] = []
    
    @abstractmethod
    def execute_query(
        self,
        query: Union[str, BaseQuery],
        user_context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute a query and return the results.
        
        Args:
            query: Query string or structured query object
            user_context: User context for the query execution
            
        Returns:
            Query result object
            
        Raises:
            QueryEngineError: If query execution fails
        """
        pass
    
    @abstractmethod
    def validate_query_access(
        self,
        parsed_query: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate if a user has access to execute a query.
        
        Args:
            parsed_query: Parsed query structure
            user_context: User context for access validation
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        pass
    
    def parse_query(self, query_string: str) -> Dict[str, Any]:
        """Parse a query string using the configured parser.
        
        Args:
            query_string: Query string to parse
            
        Returns:
            Parsed query structure
            
        Raises:
            QueryEngineError: If parsing fails
        """
        try:
            return self.parser.parse_query(query_string)
        except Exception as e:
            raise QueryEngineError(f"Query parsing failed: {str(e)}")
    
    def validate_parsed_query(self, parsed_query: Dict[str, Any]) -> None:
        """Validate a parsed query structure.
        
        Args:
            parsed_query: Parsed query structure
            
        Raises:
            QueryEngineError: If validation fails
        """
        is_valid, error_message = self.parser.validate_query(parsed_query)
        if not is_valid:
            raise QueryEngineError(f"Query validation failed: {error_message}")
    
    def create_execution_context(
        self,
        query_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        """Create an execution context for a query.
        
        Args:
            query_id: Unique identifier for the query
            user_context: User context information
            
        Returns:
            Execution context object
        """
        return ExecutionContext(
            query_id=query_id,
            user_id=user_context.get('user_id') if user_context else None,
            user_context=user_context or {}
        )
    
    def generate_query_id(self) -> str:
        """Generate a unique query ID.
        
        Returns:
            Unique query ID string
        """
        return str(uuid.uuid4())
    
    def register_pre_execute_hook(self, hook: Callable) -> None:
        """Register a pre-execution hook.
        
        Args:
            hook: Hook function to register
        """
        self._pre_execute_hooks.append(hook)
    
    def register_post_execute_hook(self, hook: Callable) -> None:
        """Register a post-execution hook.
        
        Args:
            hook: Hook function to register
        """
        self._post_execute_hooks.append(hook)
    
    def register_error_hook(self, hook: Callable) -> None:
        """Register an error hook.
        
        Args:
            hook: Hook function to register
        """
        self._error_hooks.append(hook)
    
    def execute_pre_hooks(self, context: ExecutionContext, parsed_query: Dict[str, Any]) -> None:
        """Execute pre-execution hooks.
        
        Args:
            context: Execution context
            parsed_query: Parsed query structure
        """
        for hook in self._pre_execute_hooks:
            try:
                hook(context, parsed_query)
            except Exception as e:
                # Log hook errors but don't stop execution
                if self.config.enable_query_logging:
                    print(f"Pre-execute hook error: {str(e)}")
    
    def execute_post_hooks(self, context: ExecutionContext, result: QueryResult) -> None:
        """Execute post-execution hooks.
        
        Args:
            context: Execution context
            result: Query result
        """
        for hook in self._post_execute_hooks:
            try:
                hook(context, result)
            except Exception as e:
                # Log hook errors but don't stop execution
                if self.config.enable_query_logging:
                    print(f"Post-execute hook error: {str(e)}")
    
    def execute_error_hooks(self, context: ExecutionContext, error: Exception) -> None:
        """Execute error hooks.
        
        Args:
            context: Execution context
            error: Exception that occurred
        """
        for hook in self._error_hooks:
            try:
                hook(context, error)
            except Exception as e:
                # Log hook errors but don't stop execution
                if self.config.enable_query_logging:
                    print(f"Error hook error: {str(e)}")
    
    def log_query_execution(
        self,
        query_id: str,
        query: str,
        execution_time: float,
        status: QueryStatus,
        user_context: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Log query execution information.
        
        Args:
            query_id: Query ID
            query: Query string
            execution_time: Execution time in seconds
            status: Query execution status
            user_context: User context
            error: Error message if any
        """
        if not self.config.enable_query_logging:
            return
        
        log_entry = {
            "query_id": query_id,
            "query": query,
            "execution_time": execution_time,
            "status": status.value,
            "timestamp": datetime.now(),
            "user_id": user_context.get('user_id') if user_context else None,
            "error": error
        }
        
        self.query_history[query_id] = log_entry
    
    def record_performance_metric(self, metric_name: str, value: float) -> None:
        """Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if not self.config.enable_performance_monitoring:
            return
        
        if metric_name not in self.performance_metrics:
            self.performance_metrics[metric_name] = []
        
        self.performance_metrics[metric_name].append(value)
        
        # Keep only the last 1000 measurements per metric
        if len(self.performance_metrics[metric_name]) > 1000:
            self.performance_metrics[metric_name] = self.performance_metrics[metric_name][-1000:]
    
    def get_query_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get query execution history.
        
        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of entries to return
            
        Returns:
            List of query history entries
        """
        history = list(self.query_history.values())
        
        # Filter by user ID if specified
        if user_id:
            history = [entry for entry in history if entry.get('user_id') == user_id]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return history[:limit]
    
    def get_performance_metrics(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics.
        
        Args:
            metric_name: Specific metric name (optional)
            
        Returns:
            Dictionary of performance metrics
        """
        if metric_name:
            values = self.performance_metrics.get(metric_name, [])
            if values:
                return {
                    metric_name: {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "recent": values[-10:]  # Last 10 values
                    }
                }
            else:
                return {metric_name: {"count": 0}}
        
        # Return all metrics
        result = {}
        for name, values in self.performance_metrics.items():
            if values:
                result[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values)
                }
            else:
                result[name] = {"count": 0}
        
        return result
    
    def clear_query_history(self) -> None:
        """Clear the query execution history."""
        self.query_history.clear()
    
    def clear_performance_metrics(self) -> None:
        """Clear the performance metrics."""
        self.performance_metrics.clear()
    
    def add_data_source(self, config: DataSourceConfig, data_source: Any) -> None:
        """Add a data source to the engine.
        
        Args:
            config: Data source configuration
            data_source: The data source object
        """
        self.data_source_manager.register_data_source(config, data_source)
    
    def remove_data_source(self, name: str) -> bool:
        """Remove a data source from the engine.
        
        Args:
            name: Name of the data source to remove
            
        Returns:
            True if the data source was removed
        """
        return self.data_source_manager.unregister_data_source(name)
    
    def list_data_sources(self) -> List[str]:
        """List all available data sources.
        
        Returns:
            List of data source names
        """
        return self.data_source_manager.list_data_sources()
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get the current status of the query engine.
        
        Returns:
            Dictionary containing engine status information
        """
        return {
            "data_sources": len(self.data_source_manager.list_data_sources()),
            "query_history_entries": len(self.query_history),
            "performance_metrics": len(self.performance_metrics),
            "config": {
                "max_results": self.config.max_results,
                "default_timeout": self.config.default_timeout,
                "caching_enabled": self.config.enable_caching,
                "logging_enabled": self.config.enable_query_logging,
                "monitoring_enabled": self.config.enable_performance_monitoring
            }
        }