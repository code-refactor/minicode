"""Tests for the query interpreter."""

import pytest
from datetime import datetime
import uuid

from legal_discovery_interpreter.core.document import (
    DocumentMetadata,
    Document,
    EmailDocument,
    DocumentCollection
)
from legal_discovery_interpreter.core.query import (
    QueryOperator,
    DistanceUnit,
    QueryType,
    FullTextQuery,
    MetadataQuery,
    ProximityQuery,
    TemporalQuery,
    PrivilegeQuery,
    CompositeQuery,
    LegalDiscoveryQuery
)
from legal_discovery_interpreter.core.interpreter import (
    QueryExecutionContext,
    QueryInterpreter
)


@pytest.fixture
def sample_document_collection(sample_documents):
    """Create a sample document collection for testing."""
    collection = DocumentCollection(
        collection_id="test_collection",
        name="Test Collection"
    )
    
    for doc_data in sample_documents:
        metadata = DocumentMetadata(
            document_id=doc_data["id"],
            title=doc_data["title"],
            document_type=doc_data["metadata"]["type"],
            date_created=datetime.fromisoformat(doc_data["metadata"]["date"])
        )
        
        document = Document(
            metadata=metadata,
            content=doc_data["content"]
        )
        
        collection.add_document(document)
    
    return collection


@pytest.fixture
def sample_interpreter(sample_document_collection):
    """Create a sample query interpreter for testing."""
    return QueryInterpreter(document_collection=sample_document_collection)


def test_query_execution_context():
    """Test creating a query execution context."""
    collection = DocumentCollection(
        collection_id="test_collection",
        name="Test Collection"
    )
    
    context = QueryExecutionContext(document_collection=collection)
    
    assert context.document_collection == collection
    assert context.expand_terms_func is None
    assert context.calculate_proximity_func is None
    assert context.analyze_communication_func is None
    assert context.resolve_timeframe_func is None
    assert context.detect_privilege_func is None
    assert isinstance(context.matched_documents, set)
    assert isinstance(context.relevance_scores, dict)
    assert isinstance(context.privilege_status, dict)
    assert isinstance(context.highlighting, dict)


def test_query_interpreter_initialization(sample_document_collection):
    """Test initializing a query interpreter."""
    interpreter = QueryInterpreter(document_collection=sample_document_collection)
    
    assert interpreter.document_collection == sample_document_collection
    assert interpreter.ontology_service is None
    assert interpreter.document_analyzer is None
    assert interpreter.communication_analyzer is None
    assert interpreter.temporal_manager is None
    assert interpreter.privilege_detector is None
    assert interpreter.logger is not None


def test_parse_query(sample_interpreter):
    """Test parsing a query string."""
    # Test parsing a basic CONTAINS query
    query_str = "CONTAINS(content, 'agreement', 'liability')"
    query = sample_interpreter.parse_query(query_str)
    
    assert isinstance(query, LegalDiscoveryQuery)
    assert len(query.clauses) == 1
    assert isinstance(query.clauses[0], FullTextQuery)
    assert query.clauses[0].terms == ['agreement', 'liability']
    assert query.expand_terms is True
    
    # Test parsing a NEAR query
    query_str = "NEAR('statute', 'limitations', 10, 'WORDS')"
    query = sample_interpreter.parse_query(query_str)
    
    assert isinstance(query, LegalDiscoveryQuery)
    assert len(query.clauses) == 1
    assert isinstance(query.clauses[0], ProximityQuery)
    assert query.clauses[0].terms == ['statute', 'limitations']
    assert query.clauses[0].distance == 10
    assert query.clauses[0].unit == 'WORDS'
    
    # Test parsing a simple text query
    query_str = "legal memorandum"
    query = sample_interpreter.parse_query(query_str)
    
    assert isinstance(query, LegalDiscoveryQuery)
    assert len(query.clauses) == 1
    assert isinstance(query.clauses[0], FullTextQuery)
    assert query.clauses[0].terms == ['legal memorandum']


def test_execute_query_full_text(sample_interpreter):
    """Test executing a full text query."""
    # Create a query for documents containing "agreement"
    query = LegalDiscoveryQuery(
        query_id=str(uuid.uuid4()),
        clauses=[
            FullTextQuery(
                terms=["agreement"],
                operator=QueryOperator.AND,
                expand_terms=False
            )
        ]
    )
    
    result = sample_interpreter.execute_query(query)
    
    assert result.query_id == query.query_id
    assert "doc001" in result.document_ids  # Sample doc with "agreement" in content
    assert result.total_hits == 1
    assert "doc001" in result.relevance_scores
    assert result.execution_time > 0


def test_execute_query_metadata(sample_interpreter):
    """Test executing a metadata query."""
    # Create a query for documents with type "contract"
    query = LegalDiscoveryQuery(
        query_id=str(uuid.uuid4()),
        clauses=[
            MetadataQuery(
                field="document_type",
                operator=QueryOperator.EQUALS,
                value="contract"
            )
        ]
    )
    
    result = sample_interpreter.execute_query(query)
    
    assert result.query_id == query.query_id
    assert "doc001" in result.document_ids  # Sample contract doc
    assert result.total_hits == 1


def test_execute_query_composite(sample_interpreter):
    """Test executing a composite query."""
    # Create a composite query for documents with type "memorandum" that mention "litigation"
    query = LegalDiscoveryQuery(
        query_id=str(uuid.uuid4()),
        clauses=[
            CompositeQuery(
                operator=QueryOperator.AND,
                clauses=[
                    MetadataQuery(
                        field="document_type",
                        operator=QueryOperator.EQUALS,
                        value="memorandum"
                    ),
                    FullTextQuery(
                        terms=["legal"],  # Changed to a term that exists in the sample document
                        operator=QueryOperator.AND,
                        expand_terms=False
                    )
                ]
            )
        ]
    )

    result = sample_interpreter.execute_query(query)

    assert result.query_id == query.query_id
    assert result.total_hits >= 1
    assert "doc003" in result.document_ids  # Sample memorandum with "legal"


def test_execute_query_string(sample_interpreter):
    """Test executing a query from a query string."""
    query_str = "CONTAINS(content, 'agreement')"
    
    result = sample_interpreter.execute_query(query_str)
    
    assert result.query_id is not None
    assert "doc001" in result.document_ids  # Sample doc with "agreement" in content
    assert result.total_hits == 1
    assert "doc001" in result.relevance_scores
    assert result.execution_time > 0