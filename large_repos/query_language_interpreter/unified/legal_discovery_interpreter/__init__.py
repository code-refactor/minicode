"""Legal Discovery Query Language Interpreter Package.

A specialized query language interpreter for legal discovery specialists to efficiently
search through large corporate document collections for litigation-relevant materials.

This package extends the common query language framework with legal-specific functionality
including privilege detection, communication analysis, and legal ontology integration.
"""

__version__ = "0.1.0"

# Import key classes for easy access
from .core.interpreter import LegalQueryEngine, QueryInterpreter  # QueryInterpreter for backward compatibility
from .core.query import (
    LegalDiscoveryQuery,
    QueryResult,
    QueryClause,
    FullTextQuery,
    MetadataQuery,
    ProximityQuery,
    CommunicationQuery,
    TemporalQuery,
    PrivilegeQuery,
    CompositeQuery
)
from .core.document import Document, DocumentCollection, EmailDocument
from .service_registry import LegalServiceRegistry, get_legal_registry

# Import services
from .privilege.detector import PrivilegeDetector
from .communication_analysis.analyzer import CommunicationAnalyzer
from .document_analysis.analyzer import DocumentAnalyzer
from .ontology.service import OntologyService

__all__ = [
    # Core classes
    "LegalQueryEngine",
    "QueryInterpreter",  # Backward compatibility
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
    
    # Document classes
    "Document",
    "DocumentCollection",
    "EmailDocument",
    
    # Service classes
    "PrivilegeDetector",
    "CommunicationAnalyzer", 
    "DocumentAnalyzer",
    "OntologyService",
    
    # Registry
    "LegalServiceRegistry",
    "get_legal_registry",
]