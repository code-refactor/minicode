"""
Tests for the Differential Analysis Engine.

This module contains tests for baseline creation, comparison, and change detection
functionality of the Differential Analysis Engine.
"""

import os
import json
import pytest
from datetime import datetime

from file_system_analyzer.differential.analyzer import (
    DifferentialAnalyzer,
    ScanBaseline,
    BaselineEntry,
    DifferentialScanResult,
    FileChange,
    ChangeType
)
from file_system_analyzer.detection.scanner import (
    ScanResult,
    FileMetadata,
    SensitiveDataMatch
)
from file_system_analyzer.detection.patterns import (
    ComplianceCategory,
    SensitivityLevel
)
from file_system_analyzer.utils.crypto import CryptoProvider


class TestBaseline:
    """Tests for scan baseline functionality."""
    
    def test_baseline_creation(self):
        """Test creation of a scan baseline."""
        baseline = ScanBaseline(
            baseline_id="test-baseline",
            name="Test Baseline",
            description="Baseline for testing"
        )
        
        # Check fields
        assert baseline.baseline_id == "test-baseline"
        assert baseline.name == "Test Baseline"
        assert baseline.description == "Baseline for testing"
        assert baseline.creation_time is not None
        assert len(baseline.files) == 0
        assert baseline.verification_info is None
    
    def test_baseline_signing_and_verification(self):
        """Test baseline signing and verification."""
        baseline = ScanBaseline(
            baseline_id="test-baseline",
            name="Test Baseline",
            description="Baseline for testing"
        )
        
        # Add a file
        baseline.files["/test/file.txt"] = BaselineEntry(
            file_path="/test/file.txt",
            file_hash="abc123",
            last_modified=datetime.now()
        )
        
        # Create crypto provider
        crypto_provider = CryptoProvider.generate()
        
        # Sign the baseline
        baseline.sign(crypto_provider)
        
        # Check signature
        assert baseline.verification_info is not None
        assert "baseline_hash" in baseline.verification_info
        assert "signature" in baseline.verification_info
        
        # Verify signature
        assert baseline.verify(crypto_provider) is True
        
        # Tamper with the baseline
        original_name = baseline.name
        baseline.name = "Tampered Baseline"
        
        # Verification should fail
        assert baseline.verify(crypto_provider) is False
        
        # Restore original value
        baseline.name = original_name
        
        # Verification should succeed again
        assert baseline.verify(crypto_provider) is True


class TestDifferentialAnalyzer:
    """Tests for differential analyzer functionality."""
    
    @pytest.fixture
    def sample_scan_results(self):
        """Create sample scan results for testing."""
        # Create file metadata
        metadata1 = FileMetadata(
            file_path="/test/path/file1.txt",
            file_size=1024,
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="abc123"
        )
        
        metadata2 = FileMetadata(
            file_path="/test/path/file2.txt",
            file_size=2048,
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="def456"
        )
        
        # Create sensitive data matches
        match1 = SensitiveDataMatch(
            pattern_name="Social Security Number",
            pattern_description="US Social Security Number",
            matched_content="123-45-6789",
            context="Context around the SSN",
            line_number=10,
            category=ComplianceCategory.PII,
            sensitivity=SensitivityLevel.HIGH
        )
        
        match2 = SensitiveDataMatch(
            pattern_name="Credit Card Number",
            pattern_description="Credit card number",
            matched_content="4111111111111111",
            context="Context around the credit card",
            line_number=20,
            category=ComplianceCategory.PCI,
            sensitivity=SensitivityLevel.HIGH
        )
        
        # Create scan results
        result1 = ScanResult(
            file_metadata=metadata1,
            matches=[match1],
            scan_time=datetime.now(),
            scan_duration=0.5
        )
        
        result2 = ScanResult(
            file_metadata=metadata2,
            matches=[match2],
            scan_time=datetime.now(),
            scan_duration=0.7
        )
        
        return [result1, result2]
    
    @pytest.fixture
    def modified_scan_results(self, sample_scan_results):
        """Create modified scan results for testing."""
        # Start with copy of original results
        original_results = sample_scan_results
        
        # Create new result for modified file
        # Use same path but different hash and new match
        metadata1 = FileMetadata(
            file_path="/test/path/file1.txt",
            file_size=1500,  # Size changed
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="xyz789"  # Hash changed
        )
        
        # Original match remains
        match1 = SensitiveDataMatch(
            pattern_name="Social Security Number",
            pattern_description="US Social Security Number",
            matched_content="123-45-6789",
            context="Context around the SSN",
            line_number=10,
            category=ComplianceCategory.PII,
            sensitivity=SensitivityLevel.HIGH
        )
        
        # New match added
        match_new = SensitiveDataMatch(
            pattern_name="Email Address",
            pattern_description="Email address",
            matched_content="user@example.com",
            context="Context around the email",
            line_number=30,
            category=ComplianceCategory.PII,
            sensitivity=SensitivityLevel.MEDIUM
        )
        
        # Create result for modified file
        modified_result = ScanResult(
            file_metadata=metadata1,
            matches=[match1, match_new],  # Now has both matches
            scan_time=datetime.now(),
            scan_duration=0.6
        )
        
        # Create result for new file
        metadata_new = FileMetadata(
            file_path="/test/path/file3.txt",  # New file
            file_size=512,
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="new123"
        )
        
        match_new_file = SensitiveDataMatch(
            pattern_name="Password",
            pattern_description="Password in configuration or code",
            matched_content="password='secret'",
            context="Context around the password",
            line_number=5,
            category=ComplianceCategory.CREDENTIALS,
            sensitivity=SensitivityLevel.CRITICAL
        )
        
        new_file_result = ScanResult(
            file_metadata=metadata_new,
            matches=[match_new_file],
            scan_time=datetime.now(),
            scan_duration=0.3
        )
        
        # Keep only the second original file and add the modified and new files
        return [original_results[1], modified_result, new_file_result]
    
    def test_create_baseline(self, sample_scan_results):
        """Test creating a baseline from scan results."""
        analyzer = DifferentialAnalyzer()
        
        # Create baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Test Baseline",
            description="Baseline for testing"
        )
        
        # Check baseline
        assert baseline.name == "Test Baseline"
        assert baseline.description == "Baseline for testing"
        assert len(baseline.files) == 2
        
        # Check that files are included
        assert "/test/path/file1.txt" in baseline.files
        assert "/test/path/file2.txt" in baseline.files
        
        # Check file details
        file1 = baseline.files["/test/path/file1.txt"]
        assert file1.file_path == "/test/path/file1.txt"
        assert file1.file_hash == "abc123"
        assert len(file1.matches) == 1
        assert file1.matches[0].pattern_name == "Social Security Number"
    
    def test_save_and_load_baseline(self, sample_scan_results, tmp_path):
        """Test saving and loading a baseline."""
        analyzer = DifferentialAnalyzer()
        
        # Create baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Test Baseline",
            description="Baseline for testing"
        )
        
        # Save baseline
        baseline_path = tmp_path / "test_baseline.json"
        analyzer.save_baseline(baseline, str(baseline_path))
        
        # Check file exists
        assert os.path.exists(baseline_path)
        
        # Load baseline
        loaded_baseline = analyzer.load_baseline(str(baseline_path))
        
        # Check loaded baseline
        assert loaded_baseline.baseline_id == baseline.baseline_id
        assert loaded_baseline.name == baseline.name
        assert loaded_baseline.description == baseline.description
        assert len(loaded_baseline.files) == len(baseline.files)
        
        # Check files
        for file_path, entry in baseline.files.items():
            assert file_path in loaded_baseline.files
            loaded_entry = loaded_baseline.files[file_path]
            assert loaded_entry.file_hash == entry.file_hash
            assert len(loaded_entry.matches) == len(entry.matches)
    
    def test_signed_baseline(self, sample_scan_results, tmp_path):
        """Test creating and verifying a signed baseline."""
        analyzer = DifferentialAnalyzer()
        crypto_provider = CryptoProvider.generate()
        
        # Create signed baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Signed Baseline",
            description="Signed baseline for testing",
            crypto_provider=crypto_provider
        )
        
        # Check signature
        assert baseline.verification_info is not None
        assert baseline.verify(crypto_provider) is True
        
        # Save and load baseline
        baseline_path = tmp_path / "signed_baseline.json"
        analyzer.save_baseline(baseline, str(baseline_path))
        loaded_baseline = analyzer.load_baseline(str(baseline_path))
        
        # Signature should be preserved
        assert loaded_baseline.verification_info is not None
        assert loaded_baseline.verify(crypto_provider) is True
    
    def test_compare_unchanged(self, sample_scan_results):
        """Test comparing identical scan results."""
        analyzer = DifferentialAnalyzer()
        
        # Create baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Test Baseline"
        )
        
        # Compare to identical results
        diff_result = analyzer.compare_to_baseline(baseline, sample_scan_results)
        
        # Check diff result
        assert diff_result.baseline_id == baseline.baseline_id
        assert len(diff_result.changes) == 2  # Both files unchanged
        assert len(diff_result.new_files) == 0
        assert len(diff_result.modified_files) == 0
        assert len(diff_result.removed_files) == 0
        assert len(diff_result.unchanged_files) == 2
        assert diff_result.has_sensitive_changes is False
        assert diff_result.total_new_matches == 0
        assert diff_result.total_removed_matches == 0
    
    def test_compare_with_changes(self, sample_scan_results, modified_scan_results):
        """Test comparing with modified scan results."""
        analyzer = DifferentialAnalyzer()
        
        # Create baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Test Baseline"
        )
        
        # Compare to modified results
        diff_result = analyzer.compare_to_baseline(baseline, modified_scan_results)
        
        # Check diff result
        assert diff_result.baseline_id == baseline.baseline_id
        assert len(diff_result.changes) == 3  # 1 unchanged, 1 modified, 1 new
        assert len(diff_result.new_files) == 1
        assert len(diff_result.modified_files) == 1
        assert len(diff_result.removed_files) == 0
        assert len(diff_result.unchanged_files) == 1
        assert diff_result.has_sensitive_changes is True
        assert diff_result.total_new_matches > 0
        
        # Check new file
        new_file = diff_result.new_files[0]
        assert new_file.file_path == "/test/path/file3.txt"
        assert new_file.change_type == ChangeType.NEW_FILE
        assert len(new_file.new_matches) == 1
        assert new_file.new_matches[0].pattern_name == "Password"
        
        # Check modified file
        modified_file = diff_result.modified_files[0]
        assert modified_file.file_path == "/test/path/file1.txt"
        assert modified_file.change_type == ChangeType.MODIFIED_FILE
        assert modified_file.baseline_hash == "abc123"
        assert modified_file.current_hash == "xyz789"
        assert len(modified_file.new_matches) == 1
        assert modified_file.new_matches[0].pattern_name == "Email Address"
    
    def test_compare_with_removals(self, sample_scan_results):
        """Test comparing with removed files."""
        analyzer = DifferentialAnalyzer()
        
        # Create baseline
        baseline = analyzer.create_baseline(
            scan_results=sample_scan_results,
            name="Test Baseline"
        )
        
        # Compare to subset of results (one file removed)
        diff_result = analyzer.compare_to_baseline(baseline, [sample_scan_results[0]])
        
        # Check diff result
        assert len(diff_result.changes) == 2  # 1 unchanged, 1 removed
        assert len(diff_result.new_files) == 0
        assert len(diff_result.modified_files) == 0
        assert len(diff_result.removed_files) == 1
        assert len(diff_result.unchanged_files) == 1
        
        # Check removed file
        removed_file = diff_result.removed_files[0]
        assert removed_file.file_path == "/test/path/file2.txt"
        assert removed_file.change_type == ChangeType.REMOVED_FILE
        assert removed_file.baseline_hash == "def456"
        assert len(removed_file.removed_matches) == 1
        assert removed_file.removed_matches[0].pattern_name == "Credit Card Number"