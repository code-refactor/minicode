"""Pytest configuration for the Compliance Data Discovery Analyzer tests."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def sample_data_dir():
    """Create a temporary directory with sample data for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create subdirectories
    os.makedirs(os.path.join(temp_dir, "documents"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "database"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "logs"), exist_ok=True)
    
    # Create sample files with sensitive data
    with open(os.path.join(temp_dir, "documents", "report.txt"), "w") as f:
        f.write("This report contains sensitive information for John Doe (SSN: 123-45-6789).\n")
        f.write("His credit card number is 4111-1111-1111-1111 with CVV 123.\n")
        f.write("Contact him at johndoe@example.com or +1-555-123-4567.\n")
    
    with open(os.path.join(temp_dir, "database", "customers.csv"), "w") as f:
        f.write("id,name,email,phone,ssn\n")
        f.write("1,Jane Smith,janesmith@example.com,+1-555-987-6543,987-65-4321\n")
        f.write("2,Bob Johnson,bjohnson@example.com,+1-555-456-7890,456-78-9012\n")
    
    with open(os.path.join(temp_dir, "logs", "app.log"), "w") as f:
        f.write("2023-01-01 12:00:00 User login: admin\n")
        f.write("2023-01-01 12:05:00 Data access: customer record 1\n")
        f.write("2023-01-01 12:10:00 Error: Failed to process payment for card ending in 1111\n")
    
    # Create a file without sensitive data
    with open(os.path.join(temp_dir, "documents", "policy.txt"), "w") as f:
        f.write("This is the company data retention policy.\n")
        f.write("All customer data should be retained for a maximum of 7 years.\n")
    
    # Create a file with password-protected content marker
    with open(os.path.join(temp_dir, "documents", "protected.txt"), "w") as f:
        f.write("ENCRYPTED_CONTENT\n")
        f.write("This file is encrypted and password-protected.\n")
    
    # Create a large file
    with open(os.path.join(temp_dir, "large_file.bin"), "wb") as f:
        f.write(b"\x00" * 1024 * 1024)  # 1MB of null bytes
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def baseline_scan_dir():
    """Create a temporary directory with baseline scan data."""
    temp_dir = tempfile.mkdtemp()
    
    # Create initial files
    with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
        f.write("Initial content without sensitive data.\n")
    
    with open(os.path.join(temp_dir, "file2.txt"), "w") as f:
        f.write("This file has a phone number: 555-123-4567.\n")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def modified_scan_dir(baseline_scan_dir):
    """Create a modified version of the baseline scan directory."""
    # Make a copy of the baseline directory
    modified_dir = tempfile.mkdtemp()
    for item in os.listdir(baseline_scan_dir):
        src = os.path.join(baseline_scan_dir, item)
        dst = os.path.join(modified_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    
    # Modify file1.txt to add sensitive data
    with open(os.path.join(modified_dir, "file1.txt"), "w") as f:
        f.write("Modified content with SSN: 123-45-6789.\n")
    
    # Create a new file with sensitive data
    with open(os.path.join(modified_dir, "file3.txt"), "w") as f:
        f.write("New file with credit card: 4111-1111-1111-1111.\n")
    
    # Leave file2.txt unchanged
    
    yield modified_dir
    
    # Cleanup
    shutil.rmtree(modified_dir)


@pytest.fixture
def temp_report_dir():
    """Create a temporary directory for report output."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)