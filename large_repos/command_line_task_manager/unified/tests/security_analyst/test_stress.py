"""Stress tests for SecureTask with larger data volumes."""

import os
import uuid
import time
import random
import json
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import pytest

from securetask.utils.crypto import CryptoManager
from securetask.findings.models import Finding
from securetask.findings.repository import FindingRepository
from securetask.evidence.vault import EvidenceVault
from securetask.evidence.models import Evidence, EvidenceType, AccessLevel
from securetask.remediation.tracker import RemediationTracker
from securetask.remediation.workflow import RemediationState, RemediationPriority
from securetask.compliance.repository import ComplianceRepository
from securetask.compliance.frameworks import ComplianceFramework, ComplianceControl, ComplianceControlStatus
from securetask.reporting.generator import ReportGenerator, ReportType, ReportFormat, Report
from securetask.reporting.redaction import RedactionEngine, RedactionLevel, RedactionPattern


@pytest.fixture
def stress_test_env():
    """Setup a test environment for stress testing."""
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


def generate_lorem_ipsum(paragraphs: int = 1, sentences_per_paragraph: int = 5) -> str:
    """Generate lorem ipsum text for testing."""
    words = [
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
        "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
        "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud", "exercitation",
        "ullamco", "laboris", "nisi", "ut", "aliquip", "ex", "ea", "commodo", "consequat",
        "duis", "aute", "irure", "dolor", "in", "reprehenderit", "in", "voluptate", "velit",
        "esse", "cillum", "dolore", "eu", "fugiat", "nulla", "pariatur", "excepteur", "sint",
        "occaecat", "cupidatat", "non", "proident", "sunt", "in", "culpa", "qui", "officia",
        "deserunt", "mollit", "anim", "id", "est", "laborum", "security", "vulnerability",
        "exploit", "attack", "vector", "system", "network", "application", "server", "database",
        "encryption", "authentication", "authorization", "mitigation", "remediation"
    ]
    
    result = []
    
    for _ in range(paragraphs):
        paragraph = []
        
        for _ in range(sentences_per_paragraph):
            sentence_length = random.randint(5, 15)
            sentence = " ".join(random.choice(words).capitalize() if i == 0 else random.choice(words) 
                              for i in range(sentence_length))
            sentence += "."
            paragraph.append(sentence)
        
        result.append(" ".join(paragraph))
    
    return "\n\n".join(result)


def create_random_finding(index: int, created_days_ago: Optional[int] = None) -> Finding:
    """Create a random finding for stress testing."""
    severities = ["critical", "high", "medium", "low", "info"]
    statuses = ["open", "in_progress", "remediated", "false_positive", "closed"]
    
    affected_systems = []
    system_count = random.randint(1, 5)
    for i in range(system_count):
        system_type = random.choice(["web", "app", "db", "api", "auth", "proxy", "storage"])
        system_id = random.randint(1, 20)
        affected_systems.append(f"{system_type}-server-{system_id}.example.com")
    
    # Generate discovery date
    if created_days_ago is None:
        created_days_ago = random.randint(1, 365)
    discovered_date = datetime.now() - timedelta(days=created_days_ago)
    
    # Random CVSS score
    cvss_score = round(random.uniform(0.1, 10.0), 1)
    
    # Determine CVSS severity based on score
    if cvss_score >= 9.0:
        cvss_severity = "Critical"
    elif cvss_score >= 7.0:
        cvss_severity = "High"
    elif cvss_score >= 4.0:
        cvss_severity = "Medium"
    elif cvss_score >= 0.1:
        cvss_severity = "Low"
    else:
        cvss_severity = "None"
    
    # Generate a somewhat realistic finding with template
    finding_types = [
        "SQL Injection", "Cross-Site Scripting", "Cross-Site Request Forgery",
        "Server Misconfiguration", "Insecure Direct Object Reference", "Authentication Bypass",
        "Authorization Bypass", "Information Disclosure", "Remote Code Execution",
        "Command Injection", "Insecure Cryptography", "Insecure Communication",
        "Improper Access Control", "Default Credentials", "Session Fixation",
        "Business Logic Vulnerability", "Race Condition", "Integer Overflow",
        "Unvalidated Redirect", "Insecure Deserialization"
    ]
    
    vulnerability_type = random.choice(finding_types)
    title = f"{vulnerability_type} in {random.choice(['Login', 'Search', 'Admin', 'User', 'Payment', 'API', 'Profile', 'Settings', 'Checkout'])} {random.choice(['Page', 'Module', 'Function', 'Feature', 'Service', 'Endpoint'])}"
    
    # Generate a more detailed description
    description = generate_lorem_ipsum(paragraphs=random.randint(2, 5), sentences_per_paragraph=random.randint(3, 8))
    
    # Generate remediation details if status is remediated
    remediation_details = None
    remediation_date = None
    if random.choice(statuses) == "remediated":
        remediation_details = generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=random.randint(2, 5))
        remediation_date = discovered_date + timedelta(days=random.randint(1, 90))
    
    # Create a remediation plan for most findings
    remediation_plan = None
    if random.random() > 0.2:  # 80% chance to have a remediation plan
        remediation_plan = generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=random.randint(2, 5))
    
    # Build the finding with valid fields
    finding_data = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "affected_systems": affected_systems,
        "discovered_date": discovered_date,
        "discovered_by": random.choice(["security_analyst", "penetration_tester", "security_scanner", "developer", "auditor"]),
        "status": random.choice(statuses),
        "severity": random.choice(severities),
        "cvss_vector": f"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",  # Simplified for tests
        "cvss_score": cvss_score,
        "cvss_severity": cvss_severity,
        "remediation_plan": remediation_plan,
        "tags": [random.choice(["web", "api", "database", "network", "authentication", "authorization", "input-validation"]) 
                for _ in range(random.randint(1, 5))],
        "references": [],
        "notes": [],
        "evidence_ids": [],
        "compliance_controls": []
    }
    
    # Add optional fields if they have values
    if remediation_date:
        finding_data["remediation_date"] = remediation_date
        finding_data["remediated_by"] = "remediation_engineer"
        
    return Finding(**finding_data)


# Long-running stress test
def test_large_findings_repository(stress_test_env):
    """Test repository performance with a large number of findings."""
    env = stress_test_env
    findings_count = 1000
    findings = []
    finding_ids = []
    
    # Measure creation time
    start_time = time.time()
    
    # Create 1000 findings
    for i in range(findings_count):
        finding = create_random_finding(i)
        saved_finding = env["findings_repo"].create(finding)
        findings.append(finding)
        finding_ids.append(finding.id)
        
        # Add some progress indicators
        if (i + 1) % 200 == 0:
            print(f"Created {i + 1}/{findings_count} findings")
    
    create_time = time.time() - start_time
    print(f"Created {findings_count} findings in {create_time:.2f} seconds ({findings_count/create_time:.2f} findings/second)")
    
    # Measure read performance
    start_time = time.time()
    for _ in range(100):  # Read 100 random findings
        finding_id = random.choice(finding_ids)
        _ = env["findings_repo"].get(finding_id)
    
    read_time = time.time() - start_time
    print(f"Read 100 random findings in {read_time:.2f} seconds ({100/read_time:.2f} findings/second)")
    
    # Measure list performance (no filters)
    start_time = time.time()
    all_findings = env["findings_repo"].list()
    list_time = time.time() - start_time
    print(f"Listed all {len(all_findings)} findings in {list_time:.2f} seconds")
    
    # Measure filtered list performance
    start_time = time.time()
    high_findings = env["findings_repo"].list(filters={"severity": "high"})
    filter_time = time.time() - start_time
    print(f"Listed {len(high_findings)} high severity findings in {filter_time:.2f} seconds")
    
    # Measure paginated list performance 
    start_time = time.time()
    for i in range(5):  # Get 5 pages of 100 findings
        _ = env["findings_repo"].list(limit=100, offset=i*100)
    
    pagination_time = time.time() - start_time
    print(f"Retrieved 5 pages of 100 findings in {pagination_time:.2f} seconds")
    
    # Performance assertions
    assert create_time / findings_count < 0.050, f"Average finding creation took {create_time/findings_count*1000:.2f}ms, should be <50ms"
    assert read_time / 100 < 0.050, f"Average finding read took {read_time/100*1000:.2f}ms, should be <50ms"
    assert list_time < 5.0, f"Listing {findings_count} findings took {list_time:.2f}s, should be <5s"
    assert filter_time < 3.0, f"Filtering {findings_count} findings took {filter_time:.2f}s, should be <3s"
    assert pagination_time / 5 < 1.0, f"Average pagination took {pagination_time/5:.2f}s, should be <1s"


# Long-running stress test
def test_large_evidence_vault(stress_test_env):
    """Test the performance of the evidence vault with many large files."""
    env = stress_test_env
    evidence_count = 100  # Lower count since this involves file I/O
    evidence_items = []
    evidence_ids = []
    
    # Create test files of different sizes
    evidence_files = []
    file_sizes = [10, 50, 100, 500, 1000]  # KB
    
    for size in file_sizes:
        for i in range(evidence_count // len(file_sizes)):
            file_path = os.path.join(env["base_dir"], f"evidence_{size}kb_{i}.txt")
            with open(file_path, "w") as f:
                # Write a file of approximate size
                content = generate_lorem_ipsum(paragraphs=size // 2, sentences_per_paragraph=10)
                f.write(content)
            evidence_files.append(file_path)
    
    # Measure storage time
    start_time = time.time()
    
    for i, file_path in enumerate(evidence_files):
        evidence_type = random.choice(list(EvidenceType))
        access_level = random.choice(list(AccessLevel))
        
        evidence = env["evidence_vault"].store(
            file_path=file_path,
            title=f"Evidence #{i+1}",
            description=f"Test evidence file #{i+1}",
            evidence_type=evidence_type,
            uploaded_by="stress_tester",
            access_level=access_level
        )
        
        evidence_items.append(evidence)
        evidence_ids.append(evidence.id)
        
        # Add some progress indicators
        if (i + 1) % 20 == 0:
            print(f"Stored {i + 1}/{len(evidence_files)} evidence files")
    
    store_time = time.time() - start_time
    print(f"Stored {len(evidence_files)} evidence files in {store_time:.2f} seconds ({len(evidence_files)/store_time:.2f} files/second)")
    
    # Measure retrieval time
    start_time = time.time()
    for _ in range(20):  # Retrieve 20 random evidence items
        evidence_id = random.choice(evidence_ids)
        _ = env["evidence_vault"].get_metadata(evidence_id)
    
    retrieve_time = time.time() - start_time
    print(f"Retrieved 20 random evidence items in {retrieve_time:.2f} seconds ({20/retrieve_time:.2f} items/second)")
    
    # Measure list performance
    start_time = time.time()
    all_evidence = env["evidence_vault"].list()
    list_time = time.time() - start_time
    print(f"Listed all {len(all_evidence)} evidence items in {list_time:.2f} seconds")
    
    # Measure filtered list performance
    start_time = time.time()
    filtered_evidence = env["evidence_vault"].list(
        filters={"type": EvidenceType.NETWORK_CAPTURE.value}
    )
    filter_time = time.time() - start_time
    print(f"Listed {len(filtered_evidence)} filtered evidence items in {filter_time:.2f} seconds")
    
    # Performance assertions
    assert store_time / len(evidence_files) < 0.500, f"Average evidence storage took {store_time/len(evidence_files)*1000:.2f}ms, should be <500ms"
    assert retrieve_time / 20 < 0.200, f"Average evidence retrieval took {retrieve_time/20*1000:.2f}ms, should be <200ms"
    assert list_time < 1.0, f"Listing {len(evidence_files)} evidence items took {list_time:.2f}s, should be <1s"
    assert filter_time < 1.0, f"Filtering {len(evidence_files)} evidence items took {filter_time:.2f}s, should be <1s"


# Long-running stress test
def test_large_remediation_tracking(stress_test_env):
    """Test remediation tracking with a large number of tasks and updates."""
    env = stress_test_env
    findings_count = 200
    findings = []
    finding_ids = []
    
    # Create findings first
    for i in range(findings_count):
        finding = create_random_finding(i)
        saved_finding = env["findings_repo"].create(finding)
        findings.append(finding)
        finding_ids.append(finding.id)
    
    # Measure task creation time
    start_time = time.time()
    
    tasks = []
    task_ids = []
    
    for i, finding_id in enumerate(finding_ids):
        # Create 1-3 tasks per finding
        task_count = random.randint(1, 3)
        for j in range(task_count):
            priority = random.choice(list(RemediationPriority))
            state = random.choice(list(RemediationState))
            
            task = env["remediation_tracker"].create_task(
                finding_id=finding_id,
                title=f"Remediation task #{j+1} for finding #{i+1}",
                description=generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=3),
                priority=priority,
                created_by="stress_tester",
                due_date=datetime.now() + timedelta(days=random.randint(1, 30)),
                assigned_to=f"developer_{random.randint(1, 10)}"
            )
            
            # Update task state if not "open" (initial state)
            if state != RemediationState.OPEN:
                task.state = state
                # Set progress based on state
                if state in [RemediationState.CLOSED, RemediationState.FALSE_POSITIVE, RemediationState.DUPLICATE]:
                    task.progress_percentage = 0
                else:
                    task.progress_percentage = random.randint(10, 100)
                # Notes should be a list of dicts, not a string
                if random.random() > 0.5:
                    task.notes = [{
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now(),
                        "author": "stress_tester",
                        "content": generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=2)
                    }]
                task = env["remediation_tracker"].update_task(task)
            
            tasks.append(task)
            task_ids.append(task.id)
            
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Created tasks for {i + 1}/{findings_count} findings")
    
    create_time = time.time() - start_time
    print(f"Created and updated {len(tasks)} remediation tasks in {create_time:.2f} seconds ({len(tasks)/create_time:.2f} tasks/second)")
    
    # Measure retrieval time
    start_time = time.time()
    for _ in range(50):  # Retrieve 50 random tasks
        task_id = random.choice(task_ids)
        _ = env["remediation_tracker"].get_task(task_id)
    
    retrieve_time = time.time() - start_time
    print(f"Retrieved 50 random tasks in {retrieve_time:.2f} seconds ({50/retrieve_time:.2f} tasks/second)")
    
    # Measure listing tasks by finding
    start_time = time.time()
    for _ in range(20):  # Get tasks for 20 random findings
        finding_id = random.choice(finding_ids)
        # Use list_tasks with a filter instead of get_tasks_by_finding
        _ = env["remediation_tracker"].list_tasks(filters={"finding_id": finding_id})
    
    list_by_finding_time = time.time() - start_time
    print(f"Listed tasks for 20 random findings in {list_by_finding_time:.2f} seconds ({20/list_by_finding_time:.2f} findings/second)")
    
    # Measure filtering tasks
    start_time = time.time()
    high_priority_tasks = env["remediation_tracker"].list_tasks(
        filters={"priority": RemediationPriority.HIGH.value}
    )
    filter_time = time.time() - start_time
    print(f"Filtered to find {len(high_priority_tasks)} high priority tasks in {filter_time:.2f} seconds")
    
    # Performance assertions
    assert create_time / len(tasks) < 0.100, f"Average task creation took {create_time/len(tasks)*1000:.2f}ms, should be <100ms"
    assert retrieve_time / 50 < 0.050, f"Average task retrieval took {retrieve_time/50*1000:.2f}ms, should be <50ms"
    assert list_by_finding_time / 20 < 0.100, f"Average task listing by finding took {list_by_finding_time/20*1000:.2f}ms, should be <100ms"
    assert filter_time < 1.0, f"Filtering {len(tasks)} tasks took {filter_time:.2f}s, should be <1s"


# Long-running stress test
def test_large_compliance_framework(stress_test_env):
    """Test compliance framework with many controls, frameworks, and mappings."""
    env = stress_test_env
    framework_count = 5
    controls_per_framework = 50
    findings_count = 100
    
    # Create findings first
    findings = []
    finding_ids = []
    
    for i in range(findings_count):
        finding = create_random_finding(i)
        saved_finding = env["findings_repo"].create(finding)
        findings.append(finding)
        finding_ids.append(finding.id)
    
    # Create compliance frameworks
    frameworks = []
    all_controls = []
    
    start_time = time.time()
    
    for i in range(framework_count):
        # Create framework
        framework_id = f"FRAMEWORK-{i+1}"
        framework = env["compliance_repo"].create_framework(
            id=framework_id,
            name=f"Test Framework {i+1}",
            description=f"Stress test framework #{i+1}",
            version=f"1.{i+1}"
        )
        frameworks.append(framework)
        
        # Create controls for this framework
        framework_controls = []
        for j in range(controls_per_framework):
            control_id = f"{framework_id}-CONTROL-{j+1}"
            control = env["compliance_repo"].add_control(
                framework_id=framework_id,
                id=control_id,
                name=f"Control {j+1} for Framework {i+1}",
                description=generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=2),
                section=f"Section {j // 10 + 1}.{j % 10 + 1}"
            )
            framework_controls.append(control)
            all_controls.append((framework_id, control_id))
        
        # Progress indicator
        print(f"Created framework {i+1}/{framework_count} with {len(framework_controls)} controls")
    
    framework_create_time = time.time() - start_time
    print(f"Created {framework_count} frameworks with {len(all_controls)} total controls in {framework_create_time:.2f} seconds")
    
    # Create mappings between findings and controls
    start_time = time.time()
    mappings_count = 0
    
    for finding_id in finding_ids:
        # Map each finding to 1-5 random controls
        mapping_count = random.randint(1, 5)
        used_controls = set()
        
        for _ in range(mapping_count):
            framework_id, control_id = random.choice(all_controls)
            control_key = (framework_id, control_id)
            
            # Avoid duplicate mappings
            if control_key not in used_controls:
                env["compliance_repo"].map_finding_to_control(finding_id, framework_id, control_id)
                used_controls.add(control_key)
                mappings_count += 1
        
        # Progress indicator
        if finding_ids.index(finding_id) % 20 == 0:
            print(f"Mapped finding {finding_ids.index(finding_id)+1}/{len(finding_ids)}")
    
    mapping_time = time.time() - start_time
    print(f"Created {mappings_count} mappings between findings and controls in {mapping_time:.2f} seconds")
    
    # Update control statuses
    start_time = time.time()
    status_updates = 0
    
    for framework_id, control_id in all_controls:
        if random.random() > 0.3:  # 70% chance to update status
            status = random.choice(list(ComplianceControlStatus))
            env["compliance_repo"].update_control_status(
                framework_id,
                control_id,
                status,
                f"Status update for control {control_id}"
            )
            status_updates += 1
    
    status_update_time = time.time() - start_time
    print(f"Updated {status_updates} control statuses in {status_update_time:.2f} seconds")
    
    # Measure retrieval performance
    start_time = time.time()
    
    # Get all frameworks
    all_frameworks = env["compliance_repo"].list_frameworks()
    
    # Get 10 random frameworks
    for _ in range(10):
        framework_id = random.choice([f.id for f in all_frameworks])
        _ = env["compliance_repo"].get_framework(framework_id)
    
    # Get 20 random controls
    for _ in range(20):
        framework_id, control_id = random.choice(all_controls)
        _ = env["compliance_repo"].get_control(framework_id, control_id)
    
    # Get findings for 20 random controls
    for _ in range(20):
        framework_id, control_id = random.choice(all_controls)
        _ = env["compliance_repo"].get_findings_for_control(framework_id, control_id)
    
    retrieval_time = time.time() - start_time
    print(f"Performed various compliance retrieval operations in {retrieval_time:.2f} seconds")
    
    # Performance assertions
    assert framework_create_time / (framework_count * controls_per_framework) < 0.010, f"Average control creation took {framework_create_time/(framework_count*controls_per_framework)*1000:.2f}ms, should be <10ms"
    assert mapping_time / mappings_count < 0.020, f"Average mapping creation took {mapping_time/mappings_count*1000:.2f}ms, should be <20ms"
    assert status_update_time / status_updates < 0.020, f"Average status update took {status_update_time/status_updates*1000:.2f}ms, should be <20ms"
    assert retrieval_time < 5.0, f"Compliance retrieval operations took {retrieval_time:.2f}s, should be <5s"


# Long-running stress test
def test_large_report_generation(stress_test_env):
    """Test report generation with a large number of findings and evidence."""
    env = stress_test_env
    
    # Create a large set of findings
    findings_count = 200
    findings = []
    finding_ids = []
    
    for i in range(findings_count):
        finding = create_random_finding(i)
        saved_finding = env["findings_repo"].create(finding)
        findings.append(finding)
        finding_ids.append(finding.id)
    
    # Create a smaller set of evidence items (for performance reasons)
    evidence_count = 50
    evidence_items = []
    
    for i in range(evidence_count):
        # Create an evidence file
        file_path = os.path.join(env["base_dir"], f"evidence_{i}.txt")
        with open(file_path, "w") as f:
            content = generate_lorem_ipsum(paragraphs=random.randint(2, 10), sentences_per_paragraph=random.randint(3, 8))
            f.write(content)
        
        # Store the evidence
        evidence = env["evidence_vault"].store(
            file_path=file_path,
            title=f"Evidence #{i+1}",
            description=f"Test evidence #{i+1}",
            evidence_type=random.choice(list(EvidenceType)),
            uploaded_by="stress_tester",
            access_level=random.choice(list(AccessLevel))
        )
        
        evidence_items.append(evidence)
    
    # Link evidence to findings (1-3 evidence items per finding)
    for i, finding in enumerate(findings):
        if i % 2 == 0:  # Only link evidence to every other finding
            evidence_count = random.randint(1, 3)
            for _ in range(evidence_count):
                evidence = random.choice(evidence_items)
                finding.add_evidence(evidence.id)
            env["findings_repo"].update(finding)
    
    # Create a compliance framework for reports
    framework_id = "REPORT-FRAMEWORK"
    env["compliance_repo"].create_framework(
        id=framework_id,
        name="Report Test Framework",
        description="Framework for testing large reports",
        version="1.0"
    )
    
    # Add controls
    for i in range(20):
        control_id = f"CONTROL-{i+1}"
        env["compliance_repo"].add_control(
            framework_id=framework_id,
            id=control_id,
            name=f"Control {i+1}",
            description=generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=2),
            section=f"Section {i // 5 + 1}.{i % 5 + 1}"
        )
    
    # Map findings to controls
    for i, finding_id in enumerate(finding_ids):
        if i % 5 == 0:  # Map every 5th finding
            control_id = f"CONTROL-{(i % 20) + 1}"
            env["compliance_repo"].map_finding_to_control(finding_id, framework_id, control_id)
    
    # Generate various report types and measure performance
    
    # 1. Technical Report with all findings
    start_time = time.time()
    technical_report = env["report_generator"].generate_report(
        report_type=ReportType.DETAILED_FINDINGS,
        title="Large Technical Report",
        findings=finding_ids,
        audience_level=RedactionLevel.MEDIUM,
        report_format=ReportFormat.JSON,
        generated_by="stress_tester",
        metadata={
            "target": "Large Test Environment",
            "assessment_date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    technical_time = time.time() - start_time
    print(f"Generated technical report with {len(finding_ids)} findings in {technical_time:.2f} seconds")
    
    # 2. Executive Summary with all findings
    start_time = time.time()
    executive_report = env["report_generator"].generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        title="Large Executive Summary",
        findings=finding_ids,
        audience_level=RedactionLevel.HIGH,
        report_format=ReportFormat.MARKDOWN,
        generated_by="stress_tester",
        metadata={
            "target": "Large Test Environment",
            "assessment_date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    executive_time = time.time() - start_time
    print(f"Generated executive report with {len(finding_ids)} findings in {executive_time:.2f} seconds")
    
    # 3. Compliance Report
    start_time = time.time()
    compliance_report = env["report_generator"].generate_report(
        report_type=ReportType.COMPLIANCE_REPORT,
        title="Large Compliance Report",
        findings=finding_ids,
        audience_level=RedactionLevel.MEDIUM,
        report_format=ReportFormat.JSON,
        generated_by="stress_tester",
        metadata={
            "target": "Large Test Environment",
            "framework": framework_id,
            "assessment_date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    compliance_time = time.time() - start_time
    print(f"Generated compliance report with {len(finding_ids)} findings in {compliance_time:.2f} seconds")
    
    # 4. Evidence Report
    start_time = time.time()
    evidence_report = env["report_generator"].generate_report(
        report_type=ReportType.EVIDENCE_REPORT,
        title="Large Evidence Report",
        findings=finding_ids[:50],  # Use a smaller set for evidence report
        audience_level=RedactionLevel.LOW,
        report_format=ReportFormat.JSON,
        generated_by="stress_tester",
        metadata={
            "target": "Large Test Environment",
            "assessment_date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    evidence_time = time.time() - start_time
    print(f"Generated evidence report with {len(finding_ids[:50])} findings in {evidence_time:.2f} seconds")
    
    # Measure rendering performance
    start_time = time.time()
    
    # Render reports in different formats
    json_report = env["report_generator"].render_report(technical_report, ReportFormat.JSON)
    markdown_report = env["report_generator"].render_report(executive_report, ReportFormat.MARKDOWN)
    html_report = env["report_generator"].render_report(technical_report, ReportFormat.HTML)
    text_report = env["report_generator"].render_report(compliance_report, ReportFormat.TEXT)
    
    render_time = time.time() - start_time
    print(f"Rendered reports in different formats in {render_time:.2f} seconds")
    
    # Save the largest report
    report_path = os.path.join(env["reports_dir"], "large_technical_report.json")
    
    start_time = time.time()
    env["report_generator"].save_report(technical_report, report_path, ReportFormat.JSON)
    save_time = time.time() - start_time
    print(f"Saved large technical report in {save_time:.2f} seconds")
    
    # Verify report file size
    report_size_kb = os.path.getsize(report_path) / 1024
    print(f"Technical report size: {report_size_kb:.2f} KB")
    
    # Performance assertions
    max_time_per_finding = 0.050  # 50ms per finding
    assert technical_time / len(finding_ids) < max_time_per_finding, f"Technical report generation took {technical_time/len(finding_ids)*1000:.2f}ms per finding, should be <{max_time_per_finding*1000}ms"
    assert executive_time / len(finding_ids) < max_time_per_finding, f"Executive report generation took {executive_time/len(finding_ids)*1000:.2f}ms per finding, should be <{max_time_per_finding*1000}ms"
    assert compliance_time / len(finding_ids) < max_time_per_finding, f"Compliance report generation took {compliance_time/len(finding_ids)*1000:.2f}ms per finding, should be <{max_time_per_finding*1000}ms"
    assert evidence_time / len(finding_ids[:50]) < max_time_per_finding * 2, f"Evidence report generation took {evidence_time/len(finding_ids[:50])*1000:.2f}ms per finding, should be <{max_time_per_finding*2*1000}ms"
    
    assert render_time < 10.0, f"Rendering reports took {render_time:.2f}s, should be <10s"
    assert save_time < 5.0, f"Saving large report took {save_time:.2f}s, should be <5s"


# Long-running stress test
def test_redaction_performance_large_data(stress_test_env):
    """Test redaction performance with large data structures."""
    # Create a large nested data structure with sensitive information
    data_generator = lambda size: create_large_data_structure(size)
    
    # Create RedactionEngine
    engine = RedactionEngine()
    
    # Add patterns
    engine.add_pattern(RedactionPattern(
        name="ip_address",
        pattern=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        replacement="[IP REDACTED]",
        description="IP address",
        levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    engine.add_pattern(RedactionPattern(
        name="email",
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        replacement="[EMAIL REDACTED]",
        description="Email address",
        levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    engine.add_pattern(RedactionPattern(
        name="credit_card",
        pattern=r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        replacement="[CREDIT CARD REDACTED]",
        description="Credit card number",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    engine.add_pattern(RedactionPattern(
        name="hostname",
        pattern=r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|org|net|edu|gov|mil|io|internal|local)\b",
        replacement="[HOSTNAME REDACTED]",
        description="Hostname or domain",
        levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    # Test with different data sizes
    sizes = [100, 500, 1000, 5000]  # KB
    
    results = {}
    
    for size in sizes:
        # Generate test data
        data = data_generator(size)
        
        # Measure redaction time
        start_time = time.time()
        redacted = engine.redact_dict(data, RedactionLevel.MEDIUM)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Store results
        results[size] = {
            "time": execution_time,
            "data_size_kb": size,
            "redactions_per_second": size / execution_time if execution_time > 0 else float('inf')
        }
        
        print(f"Redacted {size}KB of data in {execution_time:.2f} seconds ({results[size]['redactions_per_second']:.2f} KB/second)")
        
        # Verify redactions occurred
        json_data = json.dumps(data)
        json_redacted = json.dumps(redacted)
        
        assert "192.168" not in json_redacted
        assert "@example.com" not in json_redacted
        assert "4111-1111-1111-1111" not in json_redacted
        assert "server-01.internal" not in json_redacted
    
    # Performance assertions - allow reasonable time for larger data structures
    assert results[100]["time"] < 0.500, f"Redacting 100KB took {results[100]['time']:.2f}s, should be <0.5s"
    assert results[500]["time"] < 2.500, f"Redacting 500KB took {results[500]['time']:.2f}s, should be <2.5s"
    assert results[1000]["time"] < 5.000, f"Redacting 1000KB took {results[1000]['time']:.2f}s, should be <5.0s"
    assert results[5000]["time"] < 25.000, f"Redacting 5000KB took {results[5000]['time']:.2f}s, should be <25.0s"


def create_large_data_structure(size_kb: int) -> Dict[str, Any]:
    """Create a large nested data structure with sensitive information for testing."""
    # Create a data structure with size of approximately size_kb
    result = {
        "metadata": {
            "title": "Large Data Structure",
            "description": "Test data for stress testing",
            "created_at": datetime.now().isoformat(),
            "size_kb": size_kb
        },
        "systems": [],
        "users": [],
        "network": {
            "subnets": [],
            "devices": []
        },
        "findings": [],
        "reports": []
    }
    
    # Generate hostname pool
    hostnames = [
        f"server-{i:02d}.internal" for i in range(1, 51)
    ] + [
        f"web-{i:02d}.example.com" for i in range(1, 31)
    ] + [
        f"db-{i:02d}.internal" for i in range(1, 21)
    ] + [
        f"app-{i:02d}.example.com" for i in range(1, 41)
    ]
    
    # Generate IP address pool
    ip_addresses = [
        f"192.168.{i}.{j}" for i in range(1, 11) for j in range(1, 31)
    ] + [
        f"10.0.{i}.{j}" for i in range(1, 11) for j in range(1, 31)
    ]
    
    # Generate email pool
    emails = [
        f"user{i}@example.com" for i in range(1, 101)
    ] + [
        f"admin{i}@internal.com" for i in range(1, 21)
    ] + [
        f"dev{i}@example.com" for i in range(1, 51)
    ]
    
    # Generate credit card pool
    credit_cards = [
        f"4111-1111-1111-{i:04d}" for i in range(1, 21)
    ] + [
        f"5555-5555-5555-{i:04d}" for i in range(1, 11)
    ]
    
    # Helper to add a random sensitive value to a text
    def add_sensitive_data(text: str) -> str:
        roll = random.random()
        if roll < 0.25:
            return text + " IP: " + random.choice(ip_addresses)
        elif roll < 0.50:
            return text + " Email: " + random.choice(emails)
        elif roll < 0.75:
            return text + " Server: " + random.choice(hostnames)
        else:
            return text + " CC: " + random.choice(credit_cards)
    
    # Generate systems
    for i in range(min(int(size_kb / 2), 200)):
        system = {
            "id": str(uuid.uuid4()),
            "hostname": random.choice(hostnames),
            "ip_address": random.choice(ip_addresses),
            "type": random.choice(["server", "workstation", "database", "application"]),
            "status": random.choice(["online", "offline", "maintenance"]),
            "owner": random.choice(emails),
            "description": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=2)),
            "services": []
        }
        
        # Add services to system
        for j in range(random.randint(1, 5)):
            service = {
                "name": random.choice(["http", "https", "ssh", "ftp", "smtp", "database", "application"]),
                "port": random.randint(20, 9000),
                "status": random.choice(["running", "stopped"]),
                "config": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=1))
            }
            system["services"].append(service)
        
        result["systems"].append(system)
    
    # Generate users
    for i in range(min(int(size_kb / 3), 100)):
        user = {
            "id": str(uuid.uuid4()),
            "username": f"user{i}",
            "email": random.choice(emails),
            "full_name": f"Test User {i}",
            "department": random.choice(["IT", "Security", "Development", "Operations", "Finance"]),
            "access_level": random.choice(["admin", "user", "guest"]),
            "workstation": random.choice(hostnames),
            "ip_address": random.choice(ip_addresses),
            "notes": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=1))
        }
        result["users"].append(user)
    
    # Generate network entries
    for i in range(min(int(size_kb / 4), 50)):
        subnet = {
            "id": str(uuid.uuid4()),
            "cidr": f"192.168.{i}.0/24" if i < 25 else f"10.0.{i-25}.0/24",
            "description": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=1)),
            "gateway": f"192.168.{i}.1" if i < 25 else f"10.0.{i-25}.1",
            "dhcp_server": random.choice(hostnames),
            "dns_servers": [random.choice(ip_addresses) for _ in range(2)],
            "admin_contact": random.choice(emails)
        }
        result["network"]["subnets"].append(subnet)
    
    # Generate network devices
    for i in range(min(int(size_kb / 3), 80)):
        device = {
            "id": str(uuid.uuid4()),
            "name": f"device-{i}",
            "type": random.choice(["router", "switch", "firewall", "load-balancer"]),
            "ip_address": random.choice(ip_addresses),
            "hostname": random.choice(hostnames),
            "model": f"Model-{random.randint(1000, 9999)}",
            "admin_interface": f"https://{random.choice(ip_addresses)}:443",
            "admin_credentials": {
                "username": f"admin{random.randint(1, 10)}",
                "password": f"Password{random.randint(1000, 9999)}!"
            },
            "description": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=1))
        }
        result["network"]["devices"].append(device)
    
    # Generate findings
    for i in range(min(int(size_kb / 2), 150)):
        finding = {
            "id": str(uuid.uuid4()),
            "title": f"Test Finding {i+1}",
            "severity": random.choice(["critical", "high", "medium", "low", "info"]),
            "status": random.choice(["open", "in_progress", "remediated", "false_positive"]),
            "description": add_sensitive_data(generate_lorem_ipsum(paragraphs=2, sentences_per_paragraph=4)),
            "affected_systems": [random.choice(hostnames) for _ in range(random.randint(1, 5))],
            "affected_ips": [random.choice(ip_addresses) for _ in range(random.randint(1, 3))],
            "discovery_details": {
                "discovered_by": random.choice(emails),
                "discovered_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "discovery_method": random.choice(["automated_scan", "manual_testing", "code_review"]),
                "discovery_tools": random.choice(["nmap", "burp", "zap", "manual", "custom"])
            },
            "remediation_details": {
                "assigned_to": random.choice(emails),
                "plan": add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=3)),
                "due_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat()
            },
            "evidence": {
                "screenshots": [f"screenshot_{j}.png" for j in range(random.randint(0, 3))],
                "network_captures": [f"capture_{j}.pcap" for j in range(random.randint(0, 2))],
                "logs": [add_sensitive_data(generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=1)) for _ in range(random.randint(0, 5))]
            }
        }
        result["findings"].append(finding)
    
    # Generate reports
    for i in range(min(int(size_kb / 5), 30)):
        report = {
            "id": str(uuid.uuid4()),
            "title": f"Test Report {i+1}",
            "type": random.choice(["technical", "executive", "compliance"]),
            "generated_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            "generated_by": random.choice(emails),
            "target_audience": random.choice(["technical", "management", "auditors"]),
            "sections": {
                "executive_summary": add_sensitive_data(generate_lorem_ipsum(paragraphs=3, sentences_per_paragraph=5)),
                "methodology": generate_lorem_ipsum(paragraphs=2, sentences_per_paragraph=4),
                "findings_summary": add_sensitive_data(generate_lorem_ipsum(paragraphs=4, sentences_per_paragraph=6)),
                "recommendations": add_sensitive_data(generate_lorem_ipsum(paragraphs=3, sentences_per_paragraph=4)),
                "conclusion": generate_lorem_ipsum(paragraphs=1, sentences_per_paragraph=4)
            },
            "appendices": {
                "tools_used": ["nmap", "burp", "zap", "metasploit"],
                "team_members": [random.choice(emails) for _ in range(random.randint(2, 5))],
                "references": [f"https://{random.choice(hostnames)}/ref{j}" for j in range(random.randint(1, 5))]
            }
        }
        result["reports"].append(report)
    
    # Check if we need to add more data to reach the target size
    current_size = len(json.dumps(result).encode('utf-8')) / 1024
    
    while current_size < size_kb:
        # Add more lorem ipsum text to metadata
        for _ in range(5):
            result["metadata"][f"additional_info_{len(result['metadata'])}"] = add_sensitive_data(
                generate_lorem_ipsum(paragraphs=random.randint(5, 10), sentences_per_paragraph=random.randint(5, 10))
            )
        
        # Check size again
        current_size = len(json.dumps(result).encode('utf-8')) / 1024
        if current_size >= size_kb:
            break
    
    return result