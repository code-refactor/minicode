"""Core module containing base classes and interfaces for the legal discovery interpreter.

This module extends the common query engine framework with legal-specific functionality.
"""

from .interpreter import LegalQueryEngine, QueryInterpreter  # QueryInterpreter for backward compatibility
from .query import (
    LegalDiscoveryQuery,
    QueryResult,
    QueryClause,
    FullTextQuery,
    MetadataQuery,
    ProximityQuery,
    CommunicationQuery,
    TemporalQuery,
    PrivilegeQuery,
    CompositeQuery,
    QueryType,
    QueryOperator,
    DistanceUnit,
    SortOrder,
    SortField
)
from .document import Document, DocumentCollection, EmailDocument, DocumentMetadata

__all__ = [
    # Engine classes
    "LegalQueryEngine",
    "QueryInterpreter",  # Backward compatibility
    
    # Query classes
    "LegalDiscoveryQuery",
    "QueryResult", 
    "QueryClause",
    "FullTextQuery",
    "MetadataQuery",
    "ProximityQuery", 
    "CommunicationQuery",
    "TemporalQuery",
    "PrivilegeQuery",
    "CompositeQuery",
    
    # Enums and utilities
    "QueryType",
    "QueryOperator",
    "DistanceUnit", 
    "SortOrder",
    "SortField",
    
    # Document classes
    "Document",
    "DocumentCollection",
    "EmailDocument",
    "DocumentMetadata",
]