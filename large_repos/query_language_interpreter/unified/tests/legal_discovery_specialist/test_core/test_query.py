"""Tests for the query models."""

import pytest
from datetime import datetime
import uuid
from legal_discovery_interpreter.core.query import (
    QueryOperator,
    DistanceUnit,
    QueryType,
    SortOrder,
    SortField,
    QueryClause,
    FullTextQuery,
    MetadataQuery,
    ProximityQuery,
    CommunicationQuery,
    TemporalQuery,
    PrivilegeQuery,
    CompositeQuery,
    QueryResult,
    LegalDiscoveryQuery
)


def test_query_operators():
    """Test query operators."""
    assert QueryOperator.AND == "AND"
    assert QueryOperator.OR == "OR"
    assert QueryOperator.NOT == "NOT"
    assert QueryOperator.NEAR == "NEAR"
    assert QueryOperator.CONTAINS == "CONTAINS"


def test_distance_units():
    """Test distance units."""
    assert DistanceUnit.WORDS == "WORDS"
    assert DistanceUnit.SENTENCES == "SENTENCES"
    assert DistanceUnit.PARAGRAPHS == "PARAGRAPHS"


def test_query_types():
    """Test query types."""
    assert QueryType.FULL_TEXT == "FULL_TEXT"
    assert QueryType.METADATA == "METADATA"
    assert QueryType.PROXIMITY == "PROXIMITY"
    assert QueryType.COMMUNICATION == "COMMUNICATION"
    assert QueryType.TEMPORAL == "TEMPORAL"
    assert QueryType.PRIVILEGE == "PRIVILEGE"
    assert QueryType.COMPOSITE == "COMPOSITE"


def test_full_text_query():
    """Test creating a full text query."""
    query = FullTextQuery(
        terms=["contract", "agreement"],
        operator=QueryOperator.AND,
        expand_terms=True
    )
    
    assert query.query_type == QueryType.FULL_TEXT
    assert query.terms == ["contract", "agreement"]
    assert query.operator == QueryOperator.AND
    assert query.expand_terms is True
    assert query.field is None  # Optional field
    assert query.boost == 1.0  # Default value


def test_metadata_query():
    """Test creating a metadata query."""
    query = MetadataQuery(
        field="document_type",
        operator=QueryOperator.EQUALS,
        value="contract"
    )
    
    assert query.query_type == QueryType.METADATA
    assert query.field == "document_type"
    assert query.operator == QueryOperator.EQUALS
    assert query.value == "contract"


def test_proximity_query():
    """Test creating a proximity query."""
    query = ProximityQuery(
        terms=["breach", "contract"],
        distance=5,
        unit=DistanceUnit.WORDS,
        ordered=True
    )
    
    assert query.query_type == QueryType.PROXIMITY
    assert query.terms == ["breach", "contract"]
    assert query.distance == 5
    assert query.unit == DistanceUnit.WORDS
    assert query.ordered is True
    assert query.expand_terms is True  # Default value


def test_communication_query():
    """Test creating a communication query."""
    query = CommunicationQuery(
        participants=["john@example.com", "jane@example.com"],
        direction="between",
        date_range={"start": datetime(2020, 1, 1), "end": datetime(2020, 12, 31)}
    )
    
    assert query.query_type == QueryType.COMMUNICATION
    assert query.participants == ["john@example.com", "jane@example.com"]
    assert query.direction == "between"
    assert query.date_range["start"] == datetime(2020, 1, 1)
    assert query.date_range["end"] == datetime(2020, 12, 31)
    assert query.thread_analysis is False  # Default value
    assert query.include_cc is True  # Default value
    assert query.include_bcc is False  # Default value


def test_temporal_query():
    """Test creating a temporal query."""
    query = TemporalQuery(
        date_field="date_created",
        operator=QueryOperator.GREATER_THAN,
        value=datetime(2020, 1, 1)
    )
    
    assert query.query_type == QueryType.TEMPORAL
    assert query.date_field == "date_created"
    assert query.operator == QueryOperator.GREATER_THAN
    assert query.value == datetime(2020, 1, 1)
    assert query.timeframe_type is None  # Optional field
    assert query.jurisdiction is None  # Optional field


def test_privilege_query():
    """Test creating a privilege query."""
    query = PrivilegeQuery(
        privilege_type="attorney_client",
        threshold=0.7,
        attorneys=["john.lawyer@example.com"]
    )
    
    assert query.query_type == QueryType.PRIVILEGE
    assert query.privilege_type == "attorney_client"
    assert query.threshold == 0.7
    assert query.attorneys == ["john.lawyer@example.com"]
    assert query.include_potentially_privileged is True  # Default value


def test_composite_query():
    """Test creating a composite query."""
    query1 = FullTextQuery(
        terms=["contract"],
        operator=QueryOperator.AND
    )
    
    query2 = MetadataQuery(
        field="document_type",
        operator=QueryOperator.EQUALS,
        value="agreement"
    )
    
    composite = CompositeQuery(
        operator=QueryOperator.AND,
        clauses=[query1, query2]
    )
    
    assert composite.query_type == QueryType.COMPOSITE
    assert composite.operator == QueryOperator.AND
    assert len(composite.clauses) == 2
    assert isinstance(composite.clauses[0], FullTextQuery)
    assert isinstance(composite.clauses[1], MetadataQuery)


def test_query_result():
    """Test creating a query result."""
    query_id = str(uuid.uuid4())
    result = QueryResult(
        query_id=query_id,
        document_ids=["doc001", "doc002"],
        total_hits=2,
        relevance_scores={"doc001": 0.8, "doc002": 0.6},
        execution_time=0.05
    )
    
    assert result.query_id == query_id
    assert result.document_ids == ["doc001", "doc002"]
    assert result.total_hits == 2
    assert result.relevance_scores["doc001"] == 0.8
    assert result.relevance_scores["doc002"] == 0.6
    assert result.execution_time == 0.05
    assert result.privilege_status is None  # Optional field
    assert result.pagination is None  # Optional field


def test_legal_discovery_query():
    """Test creating a legal discovery query."""
    query_id = str(uuid.uuid4())
    query1 = FullTextQuery(
        terms=["contract", "breach"],
        operator=QueryOperator.AND
    )
    
    query2 = TemporalQuery(
        date_field="date_created",
        operator=QueryOperator.GREATER_THAN,
        value=datetime(2020, 1, 1)
    )
    
    sort_field = SortField(
        field="relevance",
        order=SortOrder.DESC
    )
    
    query = LegalDiscoveryQuery(
        query_id=query_id,
        clauses=[query1, query2],
        sort=[sort_field],
        limit=10,
        offset=0,
        highlight=True
    )
    
    assert query.query_id == query_id
    assert len(query.clauses) == 2
    assert isinstance(query.clauses[0], FullTextQuery)
    assert isinstance(query.clauses[1], TemporalQuery)
    assert len(query.sort) == 1
    assert query.sort[0].field == "relevance"
    assert query.sort[0].order == SortOrder.DESC
    assert query.limit == 10
    assert query.offset == 0
    assert query.highlight is True
    assert query.expand_terms is True  # Default value
    assert query.include_privileged is False  # Default value


def test_legal_discovery_query_to_sql_like():
    """Test converting a legal discovery query to a SQL-like string."""
    query_id = str(uuid.uuid4())
    query1 = FullTextQuery(
        terms=["contract", "breach"],
        operator=QueryOperator.AND
    )
    
    query2 = MetadataQuery(
        field="document_type",
        operator=QueryOperator.EQUALS,
        value="agreement"
    )
    
    sort_field = SortField(
        field="date_created",
        order=SortOrder.DESC
    )
    
    query = LegalDiscoveryQuery(
        query_id=query_id,
        clauses=[query1, query2],
        sort=[sort_field],
        limit=10,
        offset=0
    )
    
    sql_like = query.to_sql_like()
    
    # Check that the SQL-like string contains the expected components
    assert "CONTAINS" in sql_like
    assert "'contract'" in sql_like
    assert "'breach'" in sql_like
    assert "document_type EQUALS 'agreement'" in sql_like
    assert "ORDER BY date_created DESC" in sql_like
    assert "LIMIT 10" in sql_like
    assert "OFFSET 0" in sql_like