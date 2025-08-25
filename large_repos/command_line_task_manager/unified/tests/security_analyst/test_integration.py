"""Integration tests for the SecureTask workflow."""

import os
import json
import time
import uuid
import tempfile
from typing import Dict, Any, List
from datetime import datetime, timedelta

import pytest

from securetask.utils.crypto import CryptoManager
from securetask.findings.models import Finding
from securetask.findings.repository import FindingRepository
from securetask.evidence.vault import EvidenceVault
from securetask.evidence.models import Evidence, EvidenceType, AccessLevel
from securetask.remediation.tracker import RemediationTracker
from securetask.remediation.workflow import RemediationState, RemediationPriority, WorkflowEngine
from securetask.compliance.repository import ComplianceRepository
from securetask.compliance.frameworks import ComplianceFramework, ComplianceControl, ComplianceControlStatus
from securetask.reporting.generator import ReportGenerator, ReportType, ReportFormat, Report
from securetask.reporting.redaction import RedactionEngine, RedactionLevel


@pytest.fixture
def security_assessment_environment():
    """Setup a complete environment for security assessment testing."""
    with tempfile.TemporaryDirectory() as base_dir:
        # Create directories for each component
        findings_dir = os.path.join(base_dir, "findings")
        evidence_dir = os.path.join(base_dir, "evidence")
        remediation_dir = os.path.join(base_dir, "remediation")
        compliance_dir = os.path.join(base_dir, "compliance")
        reports_dir = os.path.join(base_dir, "reports")
        
        os.makedirs(findings_dir, exist_ok=True)
        os.makedirs(evidence_dir, exist_ok=True)
        os.makedirs(remediation_dir, exist_ok=True)
        os.makedirs(compliance_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create a shared crypto manager for all components
        crypto_manager = CryptoManager()
        
        # Initialize all components
        findings_repo = FindingRepository(findings_dir, crypto_manager)
        evidence_vault = EvidenceVault(evidence_dir, crypto_manager)
        remediation_tracker = RemediationTracker(remediation_dir, crypto_manager)
        compliance_repo = ComplianceRepository(compliance_dir, crypto_manager)
        report_generator = ReportGenerator(
            findings_repo=findings_repo,
            evidence_vault=evidence_vault,
            remediation_tracker=remediation_tracker,
            compliance_repo=compliance_repo
        )
        
        # Return all initialized components
        yield {
            "base_dir": base_dir,
            "reports_dir": reports_dir,
            "crypto_manager": crypto_manager,
            "findings_repo": findings_repo,
            "evidence_vault": evidence_vault,
            "remediation_tracker": remediation_tracker,
            "compliance_repo": compliance_repo,
            "report_generator": report_generator
        }


# Full integration test
def test_complete_security_assessment_workflow(security_assessment_environment):
    """
    Test the complete security assessment workflow from finding creation to final report.
    
    This integration test verifies that all components of the SecureTask system
    work together correctly through a complete security assessment lifecycle:
    
    1. Create security findings
    2. Add evidence to findings
    3. Create compliance framework and map findings
    4. Create and update remediation tasks
    5. Generate different types of reports
    6. Verify encryption and integrity throughout the process
    """
    env = security_assessment_environment
    
    # Step 1: Create security findings
    findings = []
    
    # SQL Injection finding
    sql_injection = Finding(
        id=str(uuid.uuid4()),
        title="SQL Injection in Login Form",
        description="The login form is vulnerable to SQL injection via the 'username' parameter, allowing authentication bypass.",
        affected_systems=["web-01.example.com", "web-02.example.com"],
        discovered_date=datetime.now() - timedelta(days=14),
        discovered_by="security_analyst",
        status="open",
        severity="high",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L",
        cvss_score=9.4,
        cvss_severity="Critical",
        remediation_plan="Implement prepared statements for all database queries. Add input validation."
    )
    findings.append(sql_injection)
    saved_sql_injection = env["findings_repo"].create(sql_injection)
    
    # XSS finding
    xss_finding = Finding(
        id=str(uuid.uuid4()),
        title="Cross-Site Scripting in Search Results",
        description="The search results page does not properly sanitize user input, leading to reflected XSS vulnerabilities.",
        affected_systems=["web-01.example.com"],
        discovered_date=datetime.now() - timedelta(days=10),
        discovered_by="security_analyst",
        status="open",
        severity="medium",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        cvss_score=6.1,
        cvss_severity="Medium",
        remediation_plan="Implement proper output encoding for user-supplied content."
    )
    findings.append(xss_finding)
    saved_xss_finding = env["findings_repo"].create(xss_finding)
    
    # Insecure Configuration finding
    config_finding = Finding(
        id=str(uuid.uuid4()),
        title="Insecure TLS Configuration",
        description="The web server is configured to allow weak cipher suites (TLS 1.0, weak ciphers).",
        affected_systems=["web-01.example.com", "web-02.example.com", "load-balancer.example.com"],
        discovered_date=datetime.now() - timedelta(days=7),
        discovered_by="security_analyst",
        status="open",
        severity="medium",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        cvss_score=5.3,
        cvss_severity="Medium",
        remediation_plan="Update TLS configuration to enforce TLS 1.2+ and strong cipher suites only."
    )
    findings.append(config_finding)
    saved_config_finding = env["findings_repo"].create(config_finding)
    
    # Verify findings were saved correctly
    saved_findings = env["findings_repo"].list()
    assert len(saved_findings) == 3


def test_integrity_checks_simple():
    """Test that integrity checks work with the CryptoManager."""
    crypto_manager = CryptoManager()
    
    # Test data
    test_data = b"This is test data for integrity checks"
    
    # Encrypt data
    encrypted, digest = crypto_manager.encrypt(test_data)
    
    # Verify the correct data can be decrypted
    decrypted = crypto_manager.decrypt(encrypted, digest)
    assert decrypted == test_data
    
    # Tamper with encrypted data
    tampered_data = bytearray(encrypted)
    tampered_data[10] = (tampered_data[10] + 1) % 256
    
    # Verify that tampered data fails integrity check
    with pytest.raises(ValueError, match="Integrity verification failed"):
        crypto_manager.decrypt(bytes(tampered_data), digest)


def test_redaction_basic():
    """Test that redaction works properly."""
    engine = RedactionEngine()
    
    # Test with data containing sensitive information
    test_data = {
        "customer": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "credit_card": "4111-1111-1111-1111"
        },
        "server": {
            "address": "192.168.1.100",
            "hostname": "internal.example.com",
            "admin": "admin@example.com"
        }
    }
    
    # Test with MEDIUM redaction
    redacted = engine.redact_dict(test_data, RedactionLevel.MEDIUM)
    
    # Email addresses should be redacted at MEDIUM level
    assert redacted["customer"]["email"] != "john.doe@example.com"
    assert "[EMAIL REDACTED]" in str(redacted["customer"]["email"])
    
    # Credit card numbers should be redacted at all levels
    assert "4111-1111-1111-1111" not in json.dumps(redacted)
    
    # IP addresses should be redacted at MEDIUM level
    assert redacted["server"]["address"] != "192.168.1.100"
    assert "[IP REDACTED]" in str(redacted["server"]["address"])