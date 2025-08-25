"""Test fixtures for SecureTask."""

import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Any, Generator, Callable

import pytest
from cryptography.fernet import Fernet

from securetask.findings.models import Finding
from securetask.cvss.calculator import CVSSVector
from securetask.remediation.workflow import RemediationState
from securetask.compliance.frameworks import ComplianceControl, ComplianceFramework


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def encryption_key() -> bytes:
    """Generate a secure encryption key for testing."""
    return Fernet.generate_key()


@pytest.fixture
def sample_finding() -> Finding:
    """Create a sample security finding for testing."""
    return Finding(
        id=str(uuid.uuid4()),
        title="SQL Injection in Login Form",
        description="Login form is vulnerable to SQL injection via the username parameter",
        affected_systems=["web-app-01", "web-app-02"],
        discovered_date=datetime.now(),
        discovered_by="security-analyst",
        status="open",
        severity="high"
    )


@pytest.fixture
def sample_cvss_vector() -> CVSSVector:
    """Create a sample CVSS vector for testing."""
    return CVSSVector(
        attack_vector="N",  # Network
        attack_complexity="L",  # Low
        privileges_required="N",  # None
        user_interaction="N",  # None
        scope="U",  # Unchanged
        confidentiality="H",  # High
        integrity="H",  # High
        availability="H"  # High
    )


@pytest.fixture
def sample_compliance_framework() -> ComplianceFramework:
    """Create a sample compliance framework for testing."""
    return ComplianceFramework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard 4.0",
        description="Standard for organizations that handle credit cards",
        version="4.0",
        controls=[
            ComplianceControl(
                id="PCI-DSS-4.0-6.5.1",
                name="Injection Flaws",
                description="Prevent injection flaws, particularly SQL injection",
                section="6.5.1"
            ),
            ComplianceControl(
                id="PCI-DSS-4.0-6.5.2",
                name="Buffer Overflows",
                description="Prevent buffer overflows",
                section="6.5.2"
            )
        ]
    )