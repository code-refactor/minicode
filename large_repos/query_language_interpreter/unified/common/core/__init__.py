"""Core module for the unified query language interpreter."""

# Base models and data structures
from .base_models import (
    # Enums
    QueryOperator,
    QueryStatus, 
    DistanceUnit,
    TemporalUnit,
    SortOrder,
    HookType,
    AggregationType,
    
    # Base models
    BaseDocumentMetadata,
    BaseDocument,
    SortField,
    QueryClause,
    QueryResult,
    BaseQuery,
    ExecutionContext,
    DataSourceConfig,
    ServiceConfig,
    Hook,
    FieldFilter,
    RangeFilter,
    TextSearchOptions,
    AggregationSpec,
    AggregationResult
)

# Query parsing
from .query_parser import (
    QueryType,
    ParsedQueryComponent,
    BaseQueryParser,
    SQLQueryParser
)

# Query engine
from .query_engine import (
    DataSourceManager,
    QueryEngineConfig,
    BaseQueryEngine
)

# Execution
from .execution import (
    ExecutionPhase,
    ExecutionResult,
    ExecutionPipeline,
    QueryExecutor,
    ResultAggregator
)

# Operators
from .operators import (
    ComparisonOperator,
    TextOperator,
    ProximityOperator,
    TemporalOperator,
    NumericOperator,
    OperatorRegistry,
    default_operator_registry
)

# Exceptions
from .exceptions import (
    QueryInterpreterError,
    QueryParsingError,
    QueryValidationError,
    QueryEngineError,
    ExecutionError,
    DataSourceError,
    AccessDeniedError,
    AuthenticationError,
    PolicyViolationError,
    PrivacyError,
    ServiceError,
    ConfigurationError,
    TimeoutError,
    ResourceError,
    CacheError,
    ValidationError,
    SerializationError,
    create_error_response
)

__all__ = [
    # Enums
    'QueryOperator',
    'QueryStatus',
    'DistanceUnit', 
    'TemporalUnit',
    'SortOrder',
    'HookType',
    'AggregationType',
    
    # Base models
    'BaseDocumentMetadata',
    'BaseDocument',
    'SortField',
    'QueryClause',
    'QueryResult',
    'BaseQuery',
    'ExecutionContext',
    'DataSourceConfig',
    'ServiceConfig',
    'Hook',
    'FieldFilter',
    'RangeFilter',
    'TextSearchOptions',
    'AggregationSpec',
    'AggregationResult',
    
    # Query parsing
    'QueryType',
    'ParsedQueryComponent', 
    'BaseQueryParser',
    'SQLQueryParser',
    
    # Query engine
    'DataSourceManager',
    'QueryEngineConfig',
    'BaseQueryEngine',
    
    # Execution
    'ExecutionPhase',
    'ExecutionResult',
    'ExecutionPipeline',
    'QueryExecutor',
    'ResultAggregator',
    
    # Operators
    'ComparisonOperator',
    'TextOperator',
    'ProximityOperator',
    'TemporalOperator',
    'NumericOperator',
    'OperatorRegistry',
    'default_operator_registry',
    
    # Exceptions
    'QueryInterpreterError',
    'QueryParsingError',
    'QueryValidationError',
    'QueryEngineError',
    'ExecutionError',
    'DataSourceError',
    'AccessDeniedError',
    'AuthenticationError',
    'PolicyViolationError',
    'PrivacyError',
    'ServiceError',
    'ConfigurationError',
    'TimeoutError',
    'ResourceError',
    'CacheError',
    'ValidationError',
    'SerializationError',
    'create_error_response'
]
