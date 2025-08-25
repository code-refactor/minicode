"""Tests for the temporal manager."""

import pytest
import tempfile
import os
import json
from datetime import datetime, date, timedelta
from legal_discovery_interpreter.temporal.models import (
    TimeUnit,
    TimePeriod,
    TimeframeType,
    LegalTimeframe
)
from legal_discovery_interpreter.temporal.manager import TemporalManager


@pytest.fixture
def temporal_manager():
    """Create a sample temporal manager for testing."""
    return TemporalManager()


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return {
        "doc001": {
            "metadata": {
                "document_id": "doc001",
                "title": "Contract Agreement",
                "document_type": "contract",
                "date_created": datetime(2020, 5, 15, 10, 30)
            },
            "content": "This is a contract agreement."
        },
        "doc002": {
            "metadata": {
                "document_id": "doc002",
                "title": "Meeting Minutes",
                "document_type": "minutes",
                "date_created": datetime(2020, 7, 10, 14, 0)
            },
            "content": "These are meeting minutes."
        },
        "doc003": {
            "metadata": {
                "document_id": "doc003",
                "title": "Legal Memorandum",
                "document_type": "memorandum",
                "date_created": datetime(2020, 9, 22, 9, 15)
            },
            "content": "This is a legal memorandum."
        }
    }


@pytest.fixture
def sample_timeframe_file():
    """Create a sample timeframe file for testing."""
    timeframes_data = [
        {
            "timeframe_id": "sol_contract_ny",
            "name": "Contract SOL (NY)",
            "description": "Statute of limitations for written contracts in New York",
            "timeframe_type": "statute_of_limitations",
            "period": {
                "amount": 6,
                "unit": "years"
            },
            "jurisdiction": "NY",
            "legal_reference": "N.Y. C.P.L.R. § 213"
        },
        {
            "timeframe_id": "sol_tort_ny",
            "name": "Tort SOL (NY)",
            "description": "Statute of limitations for torts in New York",
            "timeframe_type": "statute_of_limitations",
            "period": {
                "amount": 3,
                "unit": "years"
            },
            "jurisdiction": "NY",
            "legal_reference": "N.Y. C.P.L.R. § 214"
        }
    ]
    
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(timeframes_data, f)
        yield path
    finally:
        os.remove(path)


def test_temporal_manager_initialization(temporal_manager):
    """Test initializing a temporal manager."""
    assert temporal_manager.timeframe_catalog is not None
    assert len(temporal_manager.date_formats) > 0
    
    # Check that common timeframes were initialized
    assert len(temporal_manager.timeframe_catalog.timeframes) > 0
    
    # Check that there are some statute of limitations timeframes
    sol_timeframes = temporal_manager.timeframe_catalog.get_timeframes_by_type(
        TimeframeType.STATUTE_OF_LIMITATIONS
    )
    assert len(sol_timeframes) > 0


def test_normalize_date(temporal_manager):
    """Test normalizing date strings."""
    # ISO format
    date = temporal_manager.normalize_date("2020-01-15")
    assert date is not None
    assert date.year == 2020
    assert date.month == 1
    assert date.day == 15
    
    # US format
    date = temporal_manager.normalize_date("01/15/2020")
    assert date is not None
    assert date.year == 2020
    assert date.month == 1
    assert date.day == 15
    
    # Long format
    date = temporal_manager.normalize_date("January 15, 2020")
    assert date is not None
    assert date.year == 2020
    assert date.month == 1
    assert date.day == 15
    
    # With time
    date = temporal_manager.normalize_date("2020-01-15 10:30:00")
    assert date is not None
    assert date.year == 2020
    assert date.month == 1
    assert date.day == 15
    assert date.hour == 10
    assert date.minute == 30
    
    # Invalid format
    date = temporal_manager.normalize_date("not a date")
    assert date is None


def test_normalize_dates_in_document(temporal_manager):
    """Test normalizing dates in a document."""
    document = {
        "metadata": {
            "document_id": "doc001",
            "title": "Test Document",
            "document_type": "contract",
            "date_created": "2020-01-15",
            "date_modified": "2020-02-20"
        },
        "content": "This is a test document."
    }
    
    normalized_doc = temporal_manager.normalize_dates_in_document(document)
    
    assert isinstance(normalized_doc["metadata"]["date_created"], datetime)
    assert normalized_doc["metadata"]["date_created"].year == 2020
    assert normalized_doc["metadata"]["date_created"].month == 1
    assert normalized_doc["metadata"]["date_created"].day == 15
    
    assert isinstance(normalized_doc["metadata"]["date_modified"], datetime)
    assert normalized_doc["metadata"]["date_modified"].year == 2020
    assert normalized_doc["metadata"]["date_modified"].month == 2
    assert normalized_doc["metadata"]["date_modified"].day == 20


def test_load_timeframes_from_file(temporal_manager, sample_timeframe_file):
    """Test loading timeframes from a file."""
    count = temporal_manager.load_timeframes_from_file(sample_timeframe_file)
    
    assert count == 2
    
    # Check that the timeframes were loaded
    assert "sol_contract_ny" in temporal_manager.timeframe_catalog.timeframes
    assert "sol_tort_ny" in temporal_manager.timeframe_catalog.timeframes
    
    # Check the loaded timeframes
    contract_sol = temporal_manager.timeframe_catalog.get_timeframe("sol_contract_ny")
    assert contract_sol is not None
    assert contract_sol.name == "Contract SOL (NY)"
    assert contract_sol.period.amount == 6
    assert contract_sol.period.unit == TimeUnit.YEARS
    
    tort_sol = temporal_manager.timeframe_catalog.get_timeframe("sol_tort_ny")
    assert tort_sol is not None
    assert tort_sol.name == "Tort SOL (NY)"
    assert tort_sol.period.amount == 3
    assert tort_sol.period.unit == TimeUnit.YEARS


def test_resolve_timeframe(temporal_manager):
    """Test resolving a timeframe to actual dates."""
    # Resolve a statute of limitations timeframe
    reference_date = datetime(2020, 1, 1)
    dates = temporal_manager.resolve_timeframe(
        "statute_of_limitations",
        jurisdiction="NY",
        reference_date=reference_date
    )
    
    assert 'start' in dates
    assert 'end' in dates
    assert dates['start'] == reference_date
    
    # Resolve a specific timeframe by ID
    # First, create a custom timeframe
    custom_tf = temporal_manager.create_custom_timeframe(
        name="Custom Timeframe",
        period={"amount": 30, "unit": "days"},
        description="A custom timeframe for testing"
    )
    
    dates = temporal_manager.resolve_timeframe(
        custom_tf.timeframe_id,
        reference_date=reference_date
    )
    
    assert 'start' in dates
    assert 'end' in dates
    assert dates['start'] == reference_date
    assert dates['end'] == reference_date + timedelta(days=30)


def test_create_custom_timeframe(temporal_manager):
    """Test creating a custom timeframe."""
    timeframe = temporal_manager.create_custom_timeframe(
        name="Test Timeframe",
        period={"amount": 45, "unit": "days"},
        description="A test timeframe",
        jurisdiction="Federal",
        legal_reference="Test Reference"
    )
    
    assert timeframe.name == "Test Timeframe"
    assert timeframe.period.amount == 45
    assert timeframe.period.unit == TimeUnit.DAYS
    assert timeframe.description == "A test timeframe"
    assert timeframe.jurisdiction == "Federal"
    assert timeframe.legal_reference == "Test Reference"
    assert timeframe.timeframe_type == TimeframeType.CUSTOM
    
    # Check that the timeframe was added to the catalog
    assert timeframe.timeframe_id in temporal_manager.timeframe_catalog.timeframes


def test_filter_documents_by_date(temporal_manager, sample_documents):
    """Test filtering documents by date range."""
    # Filter documents created in May 2020
    start_date = datetime(2020, 5, 1)
    end_date = datetime(2020, 5, 31)
    
    results = temporal_manager.filter_documents_by_date(
        sample_documents, "date_created", start_date, end_date
    )
    
    assert len(results) == 1
    assert "doc001" in results
    
    # Filter documents created in the first half of 2020
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2020, 6, 30)
    
    results = temporal_manager.filter_documents_by_date(
        sample_documents, "date_created", start_date, end_date
    )
    
    assert len(results) == 1
    assert "doc001" in results
    
    # Filter documents created in 2020
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2020, 12, 31)
    
    results = temporal_manager.filter_documents_by_date(
        sample_documents, "date_created", start_date, end_date
    )
    
    assert len(results) == 3
    assert "doc001" in results
    assert "doc002" in results
    assert "doc003" in results
    
    # Filter documents with string dates
    results = temporal_manager.filter_documents_by_date(
        sample_documents, "date_created", "2020-07-01", "2020-12-31"
    )
    
    assert len(results) == 2
    assert "doc002" in results
    assert "doc003" in results


def test_filter_documents_by_timeframe(temporal_manager, sample_documents):
    """Test filtering documents by a legal timeframe."""
    # Create a custom timeframe for testing
    timeframe = temporal_manager.create_custom_timeframe(
        name="Q3 2020",
        period={"amount": 3, "unit": "months"},
        description="Third quarter of 2020"
    )
    
    # Set a reference date for the timeframe
    reference_date = datetime(2020, 7, 1)
    
    # Filter documents in Q3 2020
    results = temporal_manager.filter_documents_by_timeframe(
        sample_documents, "date_created", timeframe.timeframe_id, reference_date=reference_date
    )
    
    assert len(results) == 2
    assert "doc002" in results
    assert "doc003" in results


def test_create_timeline(temporal_manager, sample_documents):
    """Test creating a timeline of documents."""
    timeline = temporal_manager.create_timeline(sample_documents, "date_created")
    
    assert len(timeline) == 3
    
    # Check that the timeline is sorted by date
    assert timeline[0]["document_id"] == "doc001"
    assert timeline[1]["document_id"] == "doc002"
    assert timeline[2]["document_id"] == "doc003"
    
    # Check that the dates are correct
    assert timeline[0]["date"] == datetime(2020, 5, 15, 10, 30)
    assert timeline[1]["date"] == datetime(2020, 7, 10, 14, 0)
    assert timeline[2]["date"] == datetime(2020, 9, 22, 9, 15)