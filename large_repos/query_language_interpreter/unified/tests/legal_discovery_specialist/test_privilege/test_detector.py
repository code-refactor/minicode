"""Tests for the privilege detector."""

import pytest
import tempfile
import os
import json
from datetime import datetime
from legal_discovery_interpreter.core.document import (
    DocumentMetadata,
    Document,
    EmailDocument,
    DocumentCollection
)
from legal_discovery_interpreter.privilege.models import (
    PrivilegeType,
    PrivilegeIndicatorCategory,
    PrivilegeStatus,
    PrivilegeIndicator,
    Attorney
)
from legal_discovery_interpreter.privilege.detector import PrivilegeDetector


@pytest.fixture
def privilege_detector():
    """Create a sample privilege detector for testing."""
    return PrivilegeDetector()


@pytest.fixture
def sample_document_collection():
    """Create a sample document collection for testing."""
    collection = DocumentCollection(
        collection_id="test_collection",
        name="Test Collection"
    )
    
    # Document 1 - Privileged
    metadata1 = DocumentMetadata(
        document_id="doc001",
        title="Legal Memorandum",
        document_type="memorandum",
        date_created=datetime(2020, 9, 22, 9, 15)
    )
    
    document1 = Document(
        metadata=metadata1,
        content="""
        ATTORNEY-CLIENT PRIVILEGED COMMUNICATION
        
        This memorandum analyzes the legal risks associated with the proposed merger.
        Based on our research, we recommend proceeding with caution.
        
        John Smith, Esq.
        Smith & Associates
        """
    )
    
    # Document 2 - Potentially Privileged
    metadata2 = DocumentMetadata(
        document_id="doc002",
        title="Email Regarding Legal Advice",
        document_type="email",
        date_created=datetime(2020, 9, 23, 10, 30)
    )
    
    document2 = EmailDocument(
        metadata=metadata2,
        content="""
        Alice,
        
        As we discussed, here is my advice on how to proceed with the contract negotiations.
        Please let me know if you have any questions.
        
        Best regards,
        John
        """,
        sender="john.smith@lawfirm.com",
        recipients=["alice@companyA.com"],
        subject="Legal Advice on Contract",
        sent_date=datetime(2020, 9, 23, 10, 30)
    )
    
    # Document 3 - Not Privileged
    metadata3 = DocumentMetadata(
        document_id="doc003",
        title="Meeting Minutes",
        document_type="minutes",
        date_created=datetime(2020, 9, 24, 14, 0)
    )
    
    document3 = Document(
        metadata=metadata3,
        content="""
        Meeting Minutes - September 24, 2020
        
        Attendees: Alice, Bob, Carol, Dave
        
        1. Project status update
        2. Budget review
        3. Timeline discussion
        
        Action items:
        - Alice to follow up with vendors
        - Bob to prepare budget report
        - Carol to update project timeline
        """
    )
    
    collection.add_document(document1)
    collection.add_document(document2)
    collection.add_document(document3)
    
    return collection


@pytest.fixture
def sample_attorney_file():
    """Create a sample attorneys file for testing."""
    attorneys_data = [
        {
            "attorney_id": "atty001",
            "name": "John Smith",
            "email": "john.smith@lawfirm.com",
            "organization": "Smith & Associates",
            "bar_number": "12345",
            "role": "External Counsel",
            "is_internal": False
        },
        {
            "attorney_id": "atty002",
            "name": "Jane Doe",
            "email": "jane.doe@lawfirm.com",
            "organization": "Smith & Associates",
            "bar_number": "67890",
            "role": "External Counsel",
            "is_internal": False
        },
        {
            "attorney_id": "atty003",
            "name": "Sarah Johnson",
            "email": "sarah.johnson@companyA.com",
            "organization": "Company A",
            "role": "General Counsel",
            "is_internal": True
        }
    ]
    
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(attorneys_data, f)
        yield path
    finally:
        os.remove(path)


def test_detector_initialization(privilege_detector):
    """Test initializing a privilege detector."""
    assert privilege_detector.logger is not None
    assert len(privilege_detector.privilege_indicators) > 0
    assert len(privilege_detector.attorneys) == 0
    assert privilege_detector.privilege_log is not None


def test_add_privilege_indicator(privilege_detector):
    """Test adding a privilege indicator."""
    # Count initial indicators
    initial_count = len(privilege_detector.privilege_indicators)
    
    # Add a new indicator
    indicator = PrivilegeIndicator(
        indicator_id="test_indicator",
        name="Test Indicator",
        description="A test privilege indicator",
        indicator_type=PrivilegeType.ATTORNEY_CLIENT,
        category=PrivilegeIndicatorCategory.CONTENT,
        weight=0.7,
        pattern=r"test pattern",
        case_sensitive=False,
        exact_match=False
    )
    
    privilege_detector.add_privilege_indicator(indicator)
    
    # Check that the indicator was added
    assert len(privilege_detector.privilege_indicators) == initial_count + 1
    assert "test_indicator" in privilege_detector.privilege_indicators
    assert privilege_detector.privilege_indicators["test_indicator"] == indicator


def test_add_attorney(privilege_detector):
    """Test adding an attorney."""
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        role="External Counsel",
        is_internal=False
    )
    
    privilege_detector.add_attorney(attorney)
    
    # Check that the attorney was added
    assert "atty001" in privilege_detector.attorneys
    assert privilege_detector.attorneys["atty001"] == attorney
    
    # Check that the attorney was also indexed by email
    assert "john.smith@lawfirm.com" in privilege_detector.attorneys
    assert privilege_detector.attorneys["john.smith@lawfirm.com"] == attorney


def test_load_attorneys_from_file(privilege_detector, sample_attorney_file):
    """Test loading attorneys from a file."""
    count = privilege_detector.load_attorneys_from_file(sample_attorney_file)
    
    assert count == 3
    
    # Check that the attorneys were loaded
    assert "atty001" in privilege_detector.attorneys
    assert "atty002" in privilege_detector.attorneys
    assert "atty003" in privilege_detector.attorneys
    
    # Check that attorneys were also indexed by email (case-insensitive check)
    emails = [key.lower() if isinstance(key, str) else key for key in privilege_detector.attorneys.keys()]
    assert "john.smith@lawfirm.com".lower() in emails
    assert "jane.doe@lawfirm.com".lower() in emails
    assert "sarah.johnson@companya.com".lower() in emails


def test_is_attorney(privilege_detector):
    """Test checking if an email belongs to an attorney."""
    # Add an attorney
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        role="External Counsel",
        is_internal=False
    )
    
    privilege_detector.add_attorney(attorney)
    
    # Check if the email belongs to an attorney
    assert privilege_detector.is_attorney("john.smith@lawfirm.com") is True
    assert privilege_detector.is_attorney("JOHN.SMITH@LAWFIRM.COM") is True  # Case insensitive
    assert privilege_detector.is_attorney("jane.doe@lawfirm.com") is False


def test_detect_privilege_indicators(privilege_detector, sample_document_collection):
    """Test detecting privilege indicators in a document."""
    # Get a privileged document
    document = sample_document_collection.get_document("doc001")
    
    # Detect privilege indicators
    indicators = privilege_detector.detect_privilege_indicators(document)
    
    assert len(indicators) > 0
    
    # Check that the header indicator was detected
    header_indicator_id = next(
        (id for id in indicators.keys() if "header" in id and "attorney_client" in id),
        None
    )
    assert header_indicator_id is not None
    
    # Get a non-privileged document
    document = sample_document_collection.get_document("doc003")
    
    # Detect privilege indicators
    indicators = privilege_detector.detect_privilege_indicators(document)
    
    assert len(indicators) == 0


def test_detect_attorneys(privilege_detector, sample_document_collection):
    """Test detecting attorneys involved in a document."""
    # Add an attorney
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        role="External Counsel",
        is_internal=False
    )
    
    privilege_detector.add_attorney(attorney)
    
    # Get a document with attorney involvement
    document = sample_document_collection.get_document("doc002")
    
    # Detect attorneys
    attorneys = privilege_detector.detect_attorneys(document)
    
    assert len(attorneys) == 1
    assert "john.smith@lawfirm.com" in attorneys or "atty001" in attorneys
    
    # Get a document without attorney involvement
    document = sample_document_collection.get_document("doc003")
    
    # Detect attorneys
    attorneys = privilege_detector.detect_attorneys(document)
    
    assert len(attorneys) == 0


def test_calculate_privilege_score(privilege_detector):
    """Test calculating a privilege score for a document."""
    # Case 1: No indicators or attorneys
    score, types = privilege_detector.calculate_privilege_score({}, [])
    assert score == 0.0
    assert len(types) == 0

    # Clear any default indicators that might be present
    privilege_detector.privilege_indicators = {}

    # Case 2: Indicators only, with no registry entries
    indicators = {
        "header_attorney_client_privilege": 0.9,
        "content_legal_advice": 0.6
    }
    score, types = privilege_detector.calculate_privilege_score(indicators, [])

    # With no registry, score should be 0 and types should be empty
    assert score == 0.0
    assert len(types) == 0
    
    # Add the indicators to the registry
    privilege_detector.add_privilege_indicator(PrivilegeIndicator(
        indicator_id="header_attorney_client_privilege",
        name="Attorney-Client Privilege Header",
        indicator_type=PrivilegeType.ATTORNEY_CLIENT,
        category=PrivilegeIndicatorCategory.HEADER,
        weight=0.9
    ))
    privilege_detector.add_privilege_indicator(PrivilegeIndicator(
        indicator_id="content_legal_advice",
        name="Legal Advice Content",
        indicator_type=PrivilegeType.ATTORNEY_CLIENT,
        category=PrivilegeIndicatorCategory.CONTENT,
        weight=0.6
    ))
    
    # Case 3: Indicators and attorneys
    score, types = privilege_detector.calculate_privilege_score(
        indicators, ["john.smith@lawfirm.com"]
    )
    assert score > 0.0
    assert PrivilegeType.ATTORNEY_CLIENT in types


def test_determine_privilege_status(privilege_detector):
    """Test determining privilege status based on confidence score."""
    assert privilege_detector.determine_privilege_status(0.0) == PrivilegeStatus.UNKNOWN
    assert privilege_detector.determine_privilege_status(0.2) == PrivilegeStatus.NOT_PRIVILEGED
    assert privilege_detector.determine_privilege_status(0.6) == PrivilegeStatus.POTENTIALLY_PRIVILEGED
    assert privilege_detector.determine_privilege_status(0.9) == PrivilegeStatus.PRIVILEGED


def test_detect_privilege(privilege_detector, sample_document_collection):
    """Test detecting privilege in a document."""
    # Add an attorney
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        role="External Counsel",
        is_internal=False
    )
    
    privilege_detector.add_attorney(attorney)
    
    # Test a privileged document
    document = sample_document_collection.get_document("doc001")
    result = privilege_detector.detect_privilege(document)
    
    assert result["document_id"] == "doc001"
    assert result["status"] in (PrivilegeStatus.PRIVILEGED, PrivilegeStatus.POTENTIALLY_PRIVILEGED)
    assert result["confidence"] > 0.0
    assert len(result["detected_indicators"]) > 0
    
    # Check that the result was added to the privilege log
    assert "doc001" in privilege_detector.privilege_log.entries
    
    # Test a non-privileged document
    document = sample_document_collection.get_document("doc003")
    result = privilege_detector.detect_privilege(document)
    
    assert result["document_id"] == "doc003"
    assert result["status"] in (PrivilegeStatus.NOT_PRIVILEGED, PrivilegeStatus.UNKNOWN)
    assert result["confidence"] >= 0.0
    assert len(result["detected_indicators"]) == 0


def test_detect_privilege_in_collection(privilege_detector, sample_document_collection):
    """Test detecting privilege in a collection of documents."""
    # Add an attorney
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        role="External Counsel",
        is_internal=False
    )
    
    privilege_detector.add_attorney(attorney)
    
    # Detect privilege in the collection
    results = privilege_detector.detect_privilege_in_collection(sample_document_collection)
    
    assert len(results) == 3
    assert "doc001" in results
    assert "doc002" in results
    assert "doc003" in results
    
    # Check the results
    assert results["doc001"]["status"] in (PrivilegeStatus.PRIVILEGED, PrivilegeStatus.POTENTIALLY_PRIVILEGED)
    assert results["doc002"]["status"] in (PrivilegeStatus.PRIVILEGED, PrivilegeStatus.POTENTIALLY_PRIVILEGED)
    assert results["doc003"]["status"] in (PrivilegeStatus.NOT_PRIVILEGED, PrivilegeStatus.UNKNOWN)
    
    # Check the privilege log
    assert len(privilege_detector.privilege_log.entries) == 3


def test_generate_privilege_log(privilege_detector, sample_document_collection):
    """Test generating a privilege log."""
    # Detect privilege in the collection
    privilege_detector.detect_privilege_in_collection(sample_document_collection)
    
    # Generate a simple log
    simple_log = privilege_detector.generate_privilege_log("simple")
    
    assert isinstance(simple_log, dict)
    assert "entries" in simple_log
    assert "summary" in simple_log
    assert len(simple_log["entries"]) == 3
    
    # Generate a detailed log
    detailed_log = privilege_detector.generate_privilege_log("detailed")
    
    assert isinstance(detailed_log, dict)
    assert "entries" in detailed_log
    assert "summary" in detailed_log
    assert len(detailed_log["entries"]) == 3
    
    # Generate a CSV log
    csv_log = privilege_detector.generate_privilege_log("csv")
    
    assert isinstance(csv_log, str)
    assert "Document ID,Status,Confidence" in csv_log
    assert "doc001" in csv_log
    assert "doc002" in csv_log
    assert "doc003" in csv_log