"""Tests for the privilege detection models."""

import pytest
from legal_discovery_interpreter.privilege.models import (
    PrivilegeType,
    PrivilegeIndicatorCategory,
    PrivilegeStatus,
    PrivilegeIndicator,
    Attorney,
    PrivilegeDetectionResult,
    PrivilegeLog
)


def test_privilege_indicator():
    """Test creating a privilege indicator."""
    indicator = PrivilegeIndicator(
        indicator_id="header_attorney_client_privilege",
        name="Attorney-Client Privilege Header",
        description="Header indicating attorney-client privilege",
        indicator_type=PrivilegeType.ATTORNEY_CLIENT,
        category=PrivilegeIndicatorCategory.HEADER,
        weight=0.9,
        pattern=r"(?i)attorney.client\s+privilege",
        case_sensitive=False,
        exact_match=False
    )
    
    assert indicator.indicator_id == "header_attorney_client_privilege"
    assert indicator.name == "Attorney-Client Privilege Header"
    assert indicator.description == "Header indicating attorney-client privilege"
    assert indicator.indicator_type == PrivilegeType.ATTORNEY_CLIENT
    assert indicator.category == PrivilegeIndicatorCategory.HEADER
    assert indicator.weight == 0.9
    assert indicator.pattern == r"(?i)attorney.client\s+privilege"
    assert indicator.case_sensitive is False
    assert indicator.exact_match is False


def test_attorney():
    """Test creating an attorney."""
    attorney = Attorney(
        attorney_id="atty001",
        name="John Smith",
        email="john.smith@lawfirm.com",
        organization="Smith & Associates",
        bar_number="12345",
        role="External Counsel",
        practice_areas=["Corporate", "Litigation"],
        is_internal=False
    )
    
    assert attorney.attorney_id == "atty001"
    assert attorney.name == "John Smith"
    assert attorney.email == "john.smith@lawfirm.com"
    assert attorney.organization == "Smith & Associates"
    assert attorney.bar_number == "12345"
    assert attorney.role == "External Counsel"
    assert attorney.practice_areas == ["Corporate", "Litigation"]
    assert attorney.is_internal is False


def test_privilege_detection_result():
    """Test creating a privilege detection result."""
    result = PrivilegeDetectionResult(
        document_id="doc001",
        status=PrivilegeStatus.PRIVILEGED,
        confidence=0.85,
        privilege_types=[PrivilegeType.ATTORNEY_CLIENT, PrivilegeType.WORK_PRODUCT],
        detected_indicators={
            "header_attorney_client_privilege": 0.9,
            "content_legal_advice": 0.6
        },
        attorneys_involved=["john.smith@lawfirm.com"],
        notes="High confidence attorney-client privilege"
    )
    
    assert result.document_id == "doc001"
    assert result.status == PrivilegeStatus.PRIVILEGED
    assert result.confidence == 0.85
    assert PrivilegeType.ATTORNEY_CLIENT in result.privilege_types
    assert PrivilegeType.WORK_PRODUCT in result.privilege_types
    assert "header_attorney_client_privilege" in result.detected_indicators
    assert result.detected_indicators["header_attorney_client_privilege"] == 0.9
    assert "content_legal_advice" in result.detected_indicators
    assert result.detected_indicators["content_legal_advice"] == 0.6
    assert "john.smith@lawfirm.com" in result.attorneys_involved
    assert result.notes == "High confidence attorney-client privilege"


def test_privilege_log():
    """Test creating and using a privilege log."""
    log = PrivilegeLog()
    
    assert len(log.entries) == 0
    
    # Create some results
    result1 = PrivilegeDetectionResult(
        document_id="doc001",
        status=PrivilegeStatus.PRIVILEGED,
        confidence=0.85,
        privilege_types=[PrivilegeType.ATTORNEY_CLIENT]
    )
    
    result2 = PrivilegeDetectionResult(
        document_id="doc002",
        status=PrivilegeStatus.POTENTIALLY_PRIVILEGED,
        confidence=0.65,
        privilege_types=[PrivilegeType.WORK_PRODUCT]
    )
    
    result3 = PrivilegeDetectionResult(
        document_id="doc003",
        status=PrivilegeStatus.NOT_PRIVILEGED,
        confidence=0.2,
        privilege_types=[]
    )
    
    # Add results to the log
    log.add_entry(result1)
    log.add_entry(result2)
    log.add_entry(result3)
    
    assert len(log.entries) == 3
    assert "doc001" in log.entries
    assert "doc002" in log.entries
    assert "doc003" in log.entries
    
    # Get an entry
    entry = log.get_entry("doc001")
    assert entry is not None
    assert entry.document_id == "doc001"
    assert entry.status == PrivilegeStatus.PRIVILEGED
    assert entry.confidence == 0.85
    
    # Get privileged documents
    privileged = log.get_privileged_documents()
    assert len(privileged) == 1
    assert "doc001" in privileged
    
    # Get potentially privileged documents
    potentially_privileged = log.get_potentially_privileged_documents()
    assert len(potentially_privileged) == 1
    assert "doc002" in potentially_privileged
    
    # Count entries
    counts = log.count_entries()
    assert counts["privileged"] == 1
    assert counts["potentially_privileged"] == 1
    assert counts["not_privileged"] == 1
    assert counts["unknown"] == 0
    assert counts["total"] == 3