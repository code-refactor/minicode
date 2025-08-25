"""Base models and data structures for the unified query language interpreter."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
from datetime import datetime, date
from pydantic import BaseModel, Field


# Common Enums
class QueryOperator(str, Enum):
    """Common query operators for both persona implementations."""
    
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NEAR = "NEAR"
    WITHIN = "WITHIN"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    EQUALS = "EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN_EQUALS = "GREATER_THAN_EQUALS"
    LESS_THAN_EQUALS = "LESS_THAN_EQUALS"
    BETWEEN = "BETWEEN"
    IN = "IN"


class QueryStatus(str, Enum):
    """Status of query execution."""
    
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"
    MODIFIED = "modified"


class DistanceUnit(str, Enum):
    """Units for proximity distance measurement."""
    
    WORDS = "WORDS"
    SENTENCES = "SENTENCES"
    PARAGRAPHS = "PARAGRAPHS"
    SECTIONS = "SECTIONS"
    PAGES = "PAGES"


class TemporalUnit(str, Enum):
    """Units for temporal measurements."""
    
    SECONDS = "SECONDS"
    MINUTES = "MINUTES"
    HOURS = "HOURS"
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


class SortOrder(str, Enum):
    """Sort orders for query results."""
    
    ASC = "ASC"
    DESC = "DESC"


# Base Document Models
class BaseDocumentMetadata(BaseModel):
    """Base metadata for documents across different implementations."""
    
    document_id: str = Field(..., description="Unique identifier for the document")
    title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Type of document")
    date_created: datetime = Field(..., description="Date and time the document was created")
    date_modified: Optional[datetime] = Field(None, description="Date and time the document was last modified")
    author: Optional[str] = Field(None, description="Author of the document")
    source: Optional[str] = Field(None, description="Source of the document")
    file_path: Optional[str] = Field(None, description="File path where the document is stored")
    file_type: Optional[str] = Field(None, description="File type of the document")
    file_size: Optional[int] = Field(None, description="Size of the document in bytes")
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"  # Allow extra fields for flexibility


class BaseDocument(BaseModel):
    """Base document model that can be extended by both implementations."""
    
    metadata: BaseDocumentMetadata = Field(..., description="Document metadata")
    content: str = Field(..., description="Full text content of the document")
    
    # Analysis related fields
    relevance_score: Optional[float] = Field(None, description="Relevance score for the document")
    extracted_entities: Optional[Dict[str, List[str]]] = Field(None, 
                                                            description="Extracted entities from the document")
    tags: Optional[List[str]] = Field(None, description="Tags assigned to the document")
    
    def get_content_preview(self, max_length: int = 200) -> str:
        """Get a preview of the document content.
        
        Args:
            max_length: Maximum length of the preview
            
        Returns:
            A preview of the document content
        """
        if len(self.content) <= max_length:
            return self.content
        
        return f"{self.content[:max_length]}..."


# Query Models
class SortField(BaseModel):
    """Field to sort query results by."""
    
    field: str = Field(..., description="Field name to sort by")
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")


class QueryClause(BaseModel):
    """Base class for a query clause."""
    
    # This will be overridden in subclasses
    pass


class QueryResult(BaseModel):
    """Result of a query execution."""
    
    query_id: str = Field(..., description="Unique identifier for the query")
    document_ids: List[str] = Field(default_factory=list, description="Matching document IDs")
    total_hits: int = Field(default=0, description="Total number of matching documents")
    status: QueryStatus = Field(default=QueryStatus.COMPLETED, description="Query execution status")
    execution_time: float = Field(..., description="Query execution time in seconds")
    executed_at: datetime = Field(default_factory=datetime.now, description="When the query was executed")
    
    # Optional result metadata
    relevance_scores: Optional[Dict[str, float]] = Field(None, description="Relevance scores for documents")
    privilege_status: Optional[Dict[str, str]] = Field(None, description="Privilege status for documents")
    pagination: Optional[Dict[str, Any]] = Field(None, description="Pagination information")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results")
    facets: Optional[Dict[str, Any]] = Field(None, description="Facet results")
    
    # Privacy-related fields
    minimized: Optional[bool] = Field(None, description="Whether data was minimized")
    anonymized: Optional[bool] = Field(None, description="Whether data was anonymized")
    privacy_reason: Optional[str] = Field(None, description="Reason for privacy modifications")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if query failed")
    reason: Optional[str] = Field(None, description="Reason for denial if query was denied")


class BaseQuery(BaseModel):
    """Base query model that can be extended by both implementations."""
    
    query_id: str = Field(..., description="Unique identifier for the query")
    clauses: List[QueryClause] = Field(..., description="Query clauses")
    sort: Optional[List[SortField]] = Field(None, description="Sort specifications")
    limit: Optional[int] = Field(None, description="Maximum number of results to return")
    offset: Optional[int] = Field(None, description="Offset for pagination")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation specifications")
    facets: Optional[List[str]] = Field(None, description="Facet specifications")
    
    highlight: bool = Field(default=False, description="Whether to highlight matching terms")


# Execution Context
class ExecutionContext(BaseModel):
    """Context for query execution containing runtime state and configuration."""
    
    query_id: str = Field(..., description="ID of the query being executed")
    user_id: Optional[str] = Field(None, description="ID of the user executing the query")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User context information")
    execution_start_time: datetime = Field(default_factory=datetime.now, description="When execution started")
    
    # Runtime state
    matched_documents: Set[str] = Field(default_factory=set, description="Set of matched document IDs")
    relevance_scores: Dict[str, float] = Field(default_factory=dict, description="Document relevance scores")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about execution")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True  # Allow Set type


# Data Source Models
class DataSourceConfig(BaseModel):
    """Configuration for a data source."""
    
    name: str = Field(..., description="Name of the data source")
    source_type: str = Field(..., description="Type of data source (e.g., 'dataframe', 'elasticsearch', 'database')")
    connection_params: Dict[str, Any] = Field(default_factory=dict, description="Connection parameters")
    schema_info: Optional[Dict[str, Any]] = Field(None, description="Schema information")
    access_permissions: Optional[Dict[str, Any]] = Field(None, description="Access permissions")
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"


# Service Configuration Models
class ServiceConfig(BaseModel):
    """Base configuration for services."""
    
    service_name: str = Field(..., description="Name of the service")
    service_type: str = Field(..., description="Type of service")
    enabled: bool = Field(default=True, description="Whether the service is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Service-specific configuration")
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"


# Hook System Models
class HookType(str, Enum):
    """Types of execution hooks."""
    
    PRE_PARSE = "pre_parse"
    POST_PARSE = "post_parse"
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    PRE_TRANSFORM = "pre_transform"
    POST_TRANSFORM = "post_transform"
    ON_ERROR = "on_error"
    ON_DENY = "on_deny"


class Hook(BaseModel):
    """A hook that can be registered in the execution pipeline."""
    
    hook_type: HookType = Field(..., description="Type of hook")
    name: str = Field(..., description="Name of the hook")
    priority: int = Field(default=0, description="Priority for hook execution (higher = earlier)")
    enabled: bool = Field(default=True, description="Whether the hook is enabled")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True


# Common Field Types for Queries
class FieldFilter(BaseModel):
    """Filter specification for a field."""
    
    field_name: str = Field(..., description="Name of the field to filter")
    operator: QueryOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    case_sensitive: bool = Field(default=False, description="Whether comparison is case sensitive")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True


class RangeFilter(BaseModel):
    """Range filter for numeric or date fields."""
    
    field_name: str = Field(..., description="Name of the field to filter")
    min_value: Optional[Any] = Field(None, description="Minimum value (inclusive)")
    max_value: Optional[Any] = Field(None, description="Maximum value (inclusive)")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True


class TextSearchOptions(BaseModel):
    """Options for text search operations."""
    
    case_sensitive: bool = Field(default=False, description="Whether search is case sensitive")
    whole_words_only: bool = Field(default=False, description="Whether to match whole words only")
    use_regex: bool = Field(default=False, description="Whether to use regex matching")
    expand_terms: bool = Field(default=True, description="Whether to expand terms using ontology")
    boost_factor: float = Field(default=1.0, description="Relevance boost factor")


# Result Aggregation Models
class AggregationType(str, Enum):
    """Types of aggregations that can be performed."""
    
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    TERMS = "terms"
    DATE_HISTOGRAM = "date_histogram"
    RANGE = "range"


class AggregationSpec(BaseModel):
    """Specification for an aggregation."""
    
    name: str = Field(..., description="Name of the aggregation")
    type: AggregationType = Field(..., description="Type of aggregation")
    field: str = Field(..., description="Field to aggregate on")
    params: Dict[str, Any] = Field(default_factory=dict, description="Aggregation parameters")


class AggregationResult(BaseModel):
    """Result of an aggregation."""
    
    name: str = Field(..., description="Name of the aggregation")
    buckets: Optional[List[Dict[str, Any]]] = Field(None, description="Buckets for bucket aggregations")
    value: Optional[Any] = Field(None, description="Value for metric aggregations")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True