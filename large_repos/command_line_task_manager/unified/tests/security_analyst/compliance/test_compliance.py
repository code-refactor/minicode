"""Tests for the Compliance Framework module."""

import os
import uuid
import time
import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from securetask.compliance.frameworks import (
    ComplianceControl, ComplianceFramework, ComplianceControlStatus, ComplianceMapping
)
from securetask.compliance.repository import ComplianceRepository
from securetask.utils.crypto import CryptoManager
from securetask.utils.validation import ValidationError as CustomValidationError


def test_compliance_models():
    """Test the compliance model classes."""
    # Create a control
    control = ComplianceControl(
        id="PCI-DSS-6.5.1",
        name="Injection Flaws",
        description="Prevent injection flaws, particularly SQL injection",
        section="6.5.1"
    )
    
    assert control.id == "PCI-DSS-6.5.1"
    assert control.name == "Injection Flaws"
    assert control.status == ComplianceControlStatus.UNKNOWN
    assert len(control.finding_ids) == 0
    
    # Add a finding to the control
    finding_id = str(uuid.uuid4())
    control.add_finding(finding_id)
    
    assert finding_id in control.finding_ids
    assert len(control.finding_ids) == 1
    
    # Remove the finding
    assert control.remove_finding(finding_id) == True
    assert len(control.finding_ids) == 0
    
    # Update status
    control.update_status(ComplianceControlStatus.COMPLIANT, "Control is implemented properly")
    
    assert control.status == ComplianceControlStatus.COMPLIANT
    assert control.status_justification == "Control is implemented properly"
    
    # Create a framework
    framework = ComplianceFramework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    assert framework.id == "PCI-DSS-4.0"
    assert framework.name == "Payment Card Industry Data Security Standard"
    assert len(framework.controls) == 0
    
    # Add a control to the framework
    framework.add_control(control)
    
    assert len(framework.controls) == 1
    assert framework.controls[0].id == "PCI-DSS-6.5.1"
    
    # Get a control
    retrieved_control = framework.get_control("PCI-DSS-6.5.1")
    
    assert retrieved_control is not None
    assert retrieved_control.name == "Injection Flaws"
    
    # Get non-existent control
    assert framework.get_control("NON-EXISTENT") is None
    
    # Remove a control
    assert framework.remove_control("PCI-DSS-6.5.1") == True
    assert len(framework.controls) == 0
    
    # Remove non-existent control
    assert framework.remove_control("NON-EXISTENT") == False


def test_compliance_mapping():
    """Test the compliance mapping functionality."""
    # Create a mapping
    mapping = ComplianceMapping()
    
    # Create frameworks and controls
    pci_framework = ComplianceFramework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    pci_control1 = ComplianceControl(
        id="PCI-DSS-6.5.1",
        name="Injection Flaws",
        description="Prevent injection flaws, particularly SQL injection",
        section="6.5.1"
    )
    
    pci_control2 = ComplianceControl(
        id="PCI-DSS-6.5.2",
        name="Buffer Overflows",
        description="Prevent buffer overflows",
        section="6.5.2"
    )
    
    nist_framework = ComplianceFramework(
        id="NIST-800-53",
        name="NIST Security Controls",
        description="Security controls from NIST SP 800-53",
        version="5"
    )
    
    nist_control = ComplianceControl(
        id="NIST-AC-2",
        name="Account Management",
        description="Manage information system accounts",
        section="AC-2"
    )
    
    # Add controls to frameworks
    pci_framework.add_control(pci_control1)
    pci_framework.add_control(pci_control2)
    nist_framework.add_control(nist_control)
    
    # Add frameworks to mapping
    mapping.add_framework(pci_framework)
    mapping.add_framework(nist_framework)
    
    # Verify frameworks were added
    assert len(mapping.frameworks) == 2
    assert "PCI-DSS-4.0" in mapping.frameworks
    assert "NIST-800-53" in mapping.frameworks
    
    # Get a framework
    retrieved_pci = mapping.get_framework("PCI-DSS-4.0")
    
    assert retrieved_pci is not None
    assert retrieved_pci.name == "Payment Card Industry Data Security Standard"
    
    # List frameworks
    frameworks = mapping.list_frameworks()
    
    assert len(frameworks) == 2
    assert any(fw.id == "PCI-DSS-4.0" for fw in frameworks)
    assert any(fw.id == "NIST-800-53" for fw in frameworks)
    
    # Create findings
    finding1_id = str(uuid.uuid4())
    finding2_id = str(uuid.uuid4())
    
    # Map findings to controls
    assert mapping.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.1") == True
    assert mapping.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.2") == True
    assert mapping.map_finding_to_control(finding2_id, "NIST-800-53", "NIST-AC-2") == True
    
    # Invalid mapping should fail
    assert mapping.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "NON-EXISTENT") == False
    
    # Get controls for a finding
    controls_for_finding1 = mapping.get_controls_for_finding(finding1_id)
    
    assert "PCI-DSS-4.0" in controls_for_finding1
    assert len(controls_for_finding1["PCI-DSS-4.0"]) == 2
    assert controls_for_finding1["PCI-DSS-4.0"][0].id == "PCI-DSS-6.5.1"
    assert controls_for_finding1["PCI-DSS-4.0"][1].id == "PCI-DSS-6.5.2"
    
    # Get findings for a control
    findings_for_pci1 = mapping.get_findings_for_control("PCI-DSS-4.0", "PCI-DSS-6.5.1")
    
    assert len(findings_for_pci1) == 1
    assert finding1_id in findings_for_pci1
    
    # Update control status
    assert mapping.update_control_status(
        "PCI-DSS-4.0", 
        "PCI-DSS-6.5.1", 
        ComplianceControlStatus.NON_COMPLIANT, 
        "Vulnerability found"
    ) == True
    
    # Invalid control should fail
    assert mapping.update_control_status(
        "PCI-DSS-4.0", 
        "NON-EXISTENT", 
        ComplianceControlStatus.COMPLIANT
    ) == False
    
    # Get framework compliance status
    pci_status = mapping.get_framework_compliance_status("PCI-DSS-4.0")
    
    assert pci_status is not None
    assert pci_status[ComplianceControlStatus.NON_COMPLIANT.value] == 1
    assert pci_status[ComplianceControlStatus.UNKNOWN.value] == 1
    
    # Get overall compliance status
    overall_status = mapping.get_overall_compliance_status()
    
    assert "PCI-DSS-4.0" in overall_status
    assert "NIST-800-53" in overall_status
    assert overall_status["PCI-DSS-4.0"][ComplianceControlStatus.NON_COMPLIANT.value] == 1
    assert overall_status["NIST-800-53"][ComplianceControlStatus.UNKNOWN.value] == 1
    
    # Unmap a finding
    assert mapping.unmap_finding_from_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.1") == True
    
    # Verify mapping was removed
    findings_for_pci1 = mapping.get_findings_for_control("PCI-DSS-4.0", "PCI-DSS-6.5.1")
    assert len(findings_for_pci1) == 0
    
    # Remove a framework
    assert mapping.remove_framework("PCI-DSS-4.0") == True
    
    # Verify framework was removed
    assert "PCI-DSS-4.0" not in mapping.frameworks
    assert len(mapping.frameworks) == 1


def test_compliance_repository_create_framework(temp_dir):
    """Test creating and retrieving compliance frameworks."""
    repo = ComplianceRepository(temp_dir)
    
    # Create a framework
    framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0",
        references=[{"title": "PCI SSC Website", "url": "https://www.pcisecuritystandards.org/"}],
        tags=["payment", "card", "security"]
    )
    
    assert framework.id == "PCI-DSS-4.0"
    assert framework.name == "Payment Card Industry Data Security Standard"
    assert len(framework.references) == 1
    assert framework.references[0]["title"] == "PCI SSC Website"
    assert len(framework.tags) == 3
    
    # Verify file was created
    file_path = os.path.join(temp_dir, "frameworks", f"{framework.id}.json.enc")
    assert os.path.exists(file_path)
    
    # Verify HMAC digest was created
    digest_path = os.path.join(temp_dir, "frameworks", f"{framework.id}.hmac")
    assert os.path.exists(digest_path)
    
    # Get the framework
    retrieved = repo.get_framework("PCI-DSS-4.0")
    
    assert retrieved.id == framework.id
    assert retrieved.name == framework.name
    assert retrieved.description == framework.description
    assert retrieved.version == framework.version
    assert len(retrieved.references) == 1
    assert len(retrieved.tags) == 3


def test_compliance_repository_add_controls(temp_dir):
    """Test adding controls to a framework."""
    repo = ComplianceRepository(temp_dir)
    
    # Create a framework
    framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    # Add controls
    control1 = repo.add_control(
        framework_id="PCI-DSS-4.0",
        id="PCI-DSS-6.5.1",
        name="Injection Flaws",
        description="Prevent injection flaws, particularly SQL injection",
        section="6.5.1",
        guidance="Use parameterized queries and input validation"
    )
    
    control2 = repo.add_control(
        framework_id="PCI-DSS-4.0",
        id="PCI-DSS-6.5.2",
        name="Buffer Overflows",
        description="Prevent buffer overflows",
        section="6.5.2",
        guidance="Use safe string functions and boundary checking"
    )
    
    assert control1.id == "PCI-DSS-6.5.1"
    assert control1.name == "Injection Flaws"
    assert control1.guidance == "Use parameterized queries and input validation"
    
    # Get the updated framework
    framework = repo.get_framework("PCI-DSS-4.0")
    
    assert len(framework.controls) == 2
    assert framework.controls[0].id == "PCI-DSS-6.5.1"
    assert framework.controls[1].id == "PCI-DSS-6.5.2"
    
    # Get a specific control
    retrieved_control = repo.get_control("PCI-DSS-4.0", "PCI-DSS-6.5.1")
    
    assert retrieved_control is not None
    assert retrieved_control.id == "PCI-DSS-6.5.1"
    assert retrieved_control.name == "Injection Flaws"
    
    # Non-existent control should return None
    assert repo.get_control("PCI-DSS-4.0", "NON-EXISTENT") is None
    
    # Update a control
    control1.description = "Updated description for injection flaws"
    control1.status = ComplianceControlStatus.NON_COMPLIANT
    control1.status_justification = "Vulnerability found in login form"
    
    updated_control = repo.update_control("PCI-DSS-4.0", control1)
    
    assert updated_control.description == "Updated description for injection flaws"
    assert updated_control.status == ComplianceControlStatus.NON_COMPLIANT
    assert updated_control.status_justification == "Vulnerability found in login form"
    
    # Retrieve the framework to confirm updates were saved
    framework = repo.get_framework("PCI-DSS-4.0")
    control = framework.get_control("PCI-DSS-6.5.1")
    
    assert control.description == "Updated description for injection flaws"
    assert control.status == ComplianceControlStatus.NON_COMPLIANT
    
    # Remove a control
    assert repo.remove_control("PCI-DSS-4.0", "PCI-DSS-6.5.2") == True
    
    # Verify control was removed
    framework = repo.get_framework("PCI-DSS-4.0")
    assert len(framework.controls) == 1
    assert framework.get_control("PCI-DSS-6.5.2") is None
    
    # Removing non-existent control should return False
    assert repo.remove_control("PCI-DSS-4.0", "NON-EXISTENT") == False


def test_compliance_repository_mappings(temp_dir):
    """Test mapping findings to controls."""
    repo = ComplianceRepository(temp_dir)
    
    # Create frameworks and controls
    pci_framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    pci_control1 = repo.add_control(
        framework_id="PCI-DSS-4.0",
        id="PCI-DSS-6.5.1",
        name="Injection Flaws",
        description="Prevent injection flaws, particularly SQL injection",
        section="6.5.1"
    )
    
    pci_control2 = repo.add_control(
        framework_id="PCI-DSS-4.0",
        id="PCI-DSS-6.5.2",
        name="Buffer Overflows",
        description="Prevent buffer overflows",
        section="6.5.2"
    )
    
    nist_framework = repo.create_framework(
        id="NIST-800-53",
        name="NIST Security Controls",
        description="Security controls from NIST SP 800-53",
        version="5"
    )
    
    nist_control = repo.add_control(
        framework_id="NIST-800-53",
        id="NIST-AC-2",
        name="Account Management",
        description="Manage information system accounts",
        section="AC-2"
    )
    
    # Create findings
    finding1_id = str(uuid.uuid4())
    finding2_id = str(uuid.uuid4())
    
    # Map findings to controls
    assert repo.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.1") == True
    assert repo.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.2") == True
    assert repo.map_finding_to_control(finding2_id, "NIST-800-53", "NIST-AC-2") == True
    
    # Invalid mapping should fail
    assert repo.map_finding_to_control(finding1_id, "PCI-DSS-4.0", "NON-EXISTENT") == False
    
    # Get controls for a finding
    controls_for_finding1 = repo.get_controls_for_finding(finding1_id)
    
    assert "PCI-DSS-4.0" in controls_for_finding1
    assert len(controls_for_finding1["PCI-DSS-4.0"]) == 2
    assert controls_for_finding1["PCI-DSS-4.0"][0].id == "PCI-DSS-6.5.1"
    assert controls_for_finding1["PCI-DSS-4.0"][1].id == "PCI-DSS-6.5.2"
    
    # Get findings for a control
    findings_for_pci1 = repo.get_findings_for_control("PCI-DSS-4.0", "PCI-DSS-6.5.1")
    
    assert len(findings_for_pci1) == 1
    assert finding1_id in findings_for_pci1
    
    # Update control status
    assert repo.update_control_status(
        "PCI-DSS-4.0", 
        "PCI-DSS-6.5.1", 
        ComplianceControlStatus.NON_COMPLIANT, 
        "Vulnerability found"
    ) == True
    
    # Invalid control should fail
    assert repo.update_control_status(
        "PCI-DSS-4.0", 
        "NON-EXISTENT", 
        ComplianceControlStatus.COMPLIANT
    ) == False
    
    # Get framework compliance status
    pci_status = repo.get_framework_compliance_status("PCI-DSS-4.0")
    
    assert pci_status is not None
    assert pci_status[ComplianceControlStatus.NON_COMPLIANT.value] == 1
    assert pci_status[ComplianceControlStatus.UNKNOWN.value] == 1
    
    # Get overall compliance status
    overall_status = repo.get_overall_compliance_status()
    
    assert "PCI-DSS-4.0" in overall_status
    assert "NIST-800-53" in overall_status
    assert overall_status["PCI-DSS-4.0"][ComplianceControlStatus.NON_COMPLIANT.value] == 1
    assert overall_status["NIST-800-53"][ComplianceControlStatus.UNKNOWN.value] == 1
    
    # Unmap a finding
    assert repo.unmap_finding_from_control(finding1_id, "PCI-DSS-4.0", "PCI-DSS-6.5.1") == True
    
    # Verify mapping was removed
    findings_for_pci1 = repo.get_findings_for_control("PCI-DSS-4.0", "PCI-DSS-6.5.1")
    assert len(findings_for_pci1) == 0
    
    # Get the updated framework to confirm unmapping was saved
    pci_framework = repo.get_framework("PCI-DSS-4.0")
    control = pci_framework.get_control("PCI-DSS-6.5.1")
    assert len(control.finding_ids) == 0


def test_compliance_repository_update_framework(temp_dir):
    """Test updating a compliance framework."""
    repo = ComplianceRepository(temp_dir)
    
    # Create a framework
    framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    # Update the framework
    framework.description = "Updated description for PCI DSS"
    framework.tags = ["payment", "security"]
    
    updated = repo.update_framework(framework)
    
    assert updated.description == "Updated description for PCI DSS"
    assert len(updated.tags) == 2
    
    # Retrieve the framework to confirm updates were saved
    retrieved = repo.get_framework("PCI-DSS-4.0")
    
    assert retrieved.description == "Updated description for PCI DSS"
    assert len(retrieved.tags) == 2
    
    # Updating non-existent framework should fail
    non_existent = ComplianceFramework(
        id="NON-EXISTENT",
        name="Non-existent Framework",
        description="This framework does not exist",
        version="1.0"
    )
    
    with pytest.raises(FileNotFoundError):
        repo.update_framework(non_existent)


def test_compliance_repository_delete_framework(temp_dir):
    """Test deleting a compliance framework."""
    repo = ComplianceRepository(temp_dir)
    
    # Create a framework
    framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    # Verify file exists
    file_path = os.path.join(temp_dir, "frameworks", f"{framework.id}.json.enc")
    assert os.path.exists(file_path)
    
    # Delete the framework
    assert repo.delete_framework("PCI-DSS-4.0") == True
    
    # Verify file was deleted
    assert not os.path.exists(file_path)
    
    # Verify can't retrieve the framework
    with pytest.raises(FileNotFoundError):
        repo.get_framework("PCI-DSS-4.0")
    
    # Deleting non-existent framework should return False
    assert repo.delete_framework("NON-EXISTENT") == False


def test_compliance_repository_list_and_count(temp_dir):
    """Test listing and counting frameworks."""
    repo = ComplianceRepository(temp_dir)
    
    # Create multiple frameworks
    repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0",
        tags=["payment", "security"]
    )
    
    repo.create_framework(
        id="NIST-800-53",
        name="NIST Security Controls",
        description="Security controls from NIST SP 800-53",
        version="5",
        tags=["government", "security"]
    )
    
    repo.create_framework(
        id="ISO-27001",
        name="ISO Information Security Standard",
        description="International standard for information security",
        version="2022",
        tags=["international", "security"]
    )
    
    # List all frameworks
    all_frameworks = repo.list_frameworks()
    assert len(all_frameworks) == 3
    
    # Filter by tag
    security_frameworks = repo.list_frameworks(filters={"tags": "security"})
    assert len(security_frameworks) == 3
    
    payment_frameworks = repo.list_frameworks(filters={"tags": "payment"})
    assert len(payment_frameworks) == 1
    assert payment_frameworks[0].id == "PCI-DSS-4.0"
    
    # Check all frameworks are returned when sorted
    sorted_by_name = repo.list_frameworks(sort_by="name")
    names = [framework.name for framework in sorted_by_name]
    # Just check all expected frameworks are present
    assert "Payment Card Industry Data Security Standard" in names
    assert "NIST Security Controls" in names
    assert "ISO Information Security Standard" in names
    assert len(names) == 3
    
    # Count
    count = repo.count_frameworks()
    assert count == 3
    
    count_payment = repo.count_frameworks(filters={"tags": "payment"})
    assert count_payment == 1


def test_compliance_repository_import_framework(temp_dir):
    """Test importing a framework from a dictionary."""
    repo = ComplianceRepository(temp_dir)
    
    # Create a framework dictionary
    framework_dict = {
        "id": "PCI-DSS-4.0",
        "name": "Payment Card Industry Data Security Standard",
        "description": "Standard for organizations that handle credit cards",
        "version": "4.0",
        "controls": [
            {
                "id": "PCI-DSS-6.5.1",
                "name": "Injection Flaws",
                "description": "Prevent injection flaws, particularly SQL injection",
                "section": "6.5.1",
                "guidance": "Use parameterized queries and input validation"
            },
            {
                "id": "PCI-DSS-6.5.2",
                "name": "Buffer Overflows",
                "description": "Prevent buffer overflows",
                "section": "6.5.2",
                "guidance": "Use safe string functions and boundary checking"
            }
        ],
        "references": [
            {
                "title": "PCI SSC Website",
                "url": "https://www.pcisecuritystandards.org/"
            }
        ],
        "tags": ["payment", "card", "security"]
    }
    
    # Import the framework
    framework = repo.import_framework_from_dict(framework_dict)
    
    assert framework.id == "PCI-DSS-4.0"
    assert framework.name == "Payment Card Industry Data Security Standard"
    assert len(framework.controls) == 2
    assert len(framework.references) == 1
    assert len(framework.tags) == 3
    
    # Verify it was saved and can be retrieved
    retrieved = repo.get_framework("PCI-DSS-4.0")
    
    assert retrieved.id == "PCI-DSS-4.0"
    assert len(retrieved.controls) == 2
    
    # This is a valid framework
    valid_framework = ComplianceFramework(
        id="HIPAA",
        name="Health Insurance Portability and Accountability Act",
        description="US healthcare privacy law",
        version="2.0"
    )

    # Let's create a serialized version of the valid framework
    valid_dict = valid_framework.model_dump()
    imported = repo.import_framework_from_dict(valid_dict)
    assert imported.id == "HIPAA"
    assert imported.name == "Health Insurance Portability and Accountability Act"


def test_compliance_performance(temp_dir):
    """Test performance of compliance operations."""
    repo = ComplianceRepository(temp_dir)
    
    # Time the creation of a framework
    start_time = time.time()
    
    framework = repo.create_framework(
        id="PCI-DSS-4.0",
        name="Payment Card Industry Data Security Standard",
        description="Standard for organizations that handle credit cards",
        version="4.0"
    )
    
    create_time = time.time() - start_time
    
    # Add a control
    start_time = time.time()
    
    control = repo.add_control(
        framework_id="PCI-DSS-4.0",
        id="PCI-DSS-6.5.1",
        name="Injection Flaws",
        description="Prevent injection flaws, particularly SQL injection",
        section="6.5.1"
    )
    
    add_control_time = time.time() - start_time
    
    # Map a finding to a control
    finding_id = str(uuid.uuid4())
    
    start_time = time.time()
    repo.map_finding_to_control(finding_id, "PCI-DSS-4.0", "PCI-DSS-6.5.1")
    map_time = time.time() - start_time
    
    # Create a large framework with many controls
    large_framework_id = "NIST-800-53"
    large_framework = repo.create_framework(
        id=large_framework_id,
        name="NIST Security Controls",
        description="Security controls from NIST SP 800-53",
        version="5"
    )
    
    # Add 50 controls (requirement: maintain performance with 50+ frameworks)
    for i in range(1, 51):
        repo.add_control(
            framework_id=large_framework_id,
            id=f"NIST-AC-{i}",
            name=f"Control AC-{i}",
            description=f"Description for AC-{i}",
            section=f"AC-{i}"
        )
    
    # Time retrieving the large framework
    start_time = time.time()
    retrieved_large = repo.get_framework(large_framework_id)
    large_retrieve_time = time.time() - start_time
    
    assert len(retrieved_large.controls) == 50
    
    # Time getting compliance status for the large framework
    start_time = time.time()
    status = repo.get_framework_compliance_status(large_framework_id)
    status_time = time.time() - start_time
    
    # Verify all operations meet performance requirements
    assert create_time < 0.05, f"Framework creation took {create_time*1000:.2f}ms, should be <50ms"
    assert add_control_time < 0.05, f"Control addition took {add_control_time*1000:.2f}ms, should be <50ms"
    assert map_time < 0.05, f"Finding mapping took {map_time*1000:.2f}ms, should be <50ms"
    assert large_retrieve_time < 0.5, f"Large framework retrieval took {large_retrieve_time*1000:.2f}ms"
    assert status_time < 0.05, f"Status retrieval took {status_time*1000:.2f}ms, should be <50ms"