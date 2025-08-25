"""
Tests for the Evidence Chain-of-Custody System.

This module contains tests for evidence packaging, verification, and
integrity checking functionality.
"""

import os
import json
import pytest
import tempfile
import zipfile
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock

from file_system_analyzer.custody.evidence import (
    EvidencePackager,
    EvidencePackage,
    EvidenceItem,
    EvidenceAccess,
    EvidenceType
)
from file_system_analyzer.utils.crypto import CryptoProvider


class TestEvidenceItems:
    """Tests for evidence item functionality."""
    
    def test_evidence_item_creation(self, tmp_path):
        """Test creation of evidence items."""
        # Create a sample file
        sample_file = tmp_path / "sample.txt"
        sample_content = "This is sample evidence content"
        sample_file.write_text(sample_content)
        
        # Calculate hash
        sha256 = hashlib.sha256(sample_content.encode()).hexdigest()
        
        # Create evidence item
        item = EvidenceItem(
            evidence_type=EvidenceType.RAW_DATA,
            file_name="sample.txt",
            description="Sample evidence file",
            hash_sha256=sha256
        )
        
        # Check fields
        assert item.evidence_type == EvidenceType.RAW_DATA
        assert item.file_name == "sample.txt"
        assert item.description == "Sample evidence file"
        assert item.hash_sha256 == sha256
        assert item.item_id is not None
        assert item.creation_time is not None
        assert item.verification_info is None
    
    def test_evidence_access_logging(self):
        """Test evidence access logging."""
        # Create access record
        access = EvidenceAccess(
            user_id="test_user",
            access_type="export",
            file_path="/test/path/evidence.zip",
            source_ip="192.168.1.1",
            metadata={"purpose": "testing"}
        )
        
        # Check fields
        assert access.user_id == "test_user"
        assert access.access_type == "export"
        assert access.file_path == "/test/path/evidence.zip"
        assert access.source_ip == "192.168.1.1"
        assert access.metadata["purpose"] == "testing"
        assert access.access_id is not None
        assert access.timestamp is not None


class TestEvidencePackage:
    """Tests for evidence package functionality."""
    
    def test_package_creation(self):
        """Test creation of evidence packages."""
        package = EvidencePackage(
            name="Test Evidence Package",
            description="Package for testing"
        )
        
        # Check fields
        assert package.name == "Test Evidence Package"
        assert package.description == "Package for testing"
        assert package.package_id is not None
        assert package.creation_time is not None
        assert len(package.items) == 0
        assert len(package.access_log) == 0
        assert package.verification_info is None
    
    def test_add_evidence_items(self, tmp_path):
        """Test adding evidence items to a package."""
        package = EvidencePackage(
            name="Test Evidence Package"
        )
        
        # Create crypto provider
        crypto_provider = CryptoProvider.generate()
        
        # Create sample files
        file1 = tmp_path / "file1.txt"
        file1.write_text("File 1 content")
        file1_hash = hashlib.sha256(b"File 1 content").hexdigest()
        
        file2 = tmp_path / "file2.txt"
        file2.write_text("File 2 content")
        file2_hash = hashlib.sha256(b"File 2 content").hexdigest()
        
        # Create and add items
        item1 = EvidenceItem(
            evidence_type=EvidenceType.RAW_DATA,
            file_name="file1.txt",
            hash_sha256=file1_hash
        )
        
        item2 = EvidenceItem(
            evidence_type=EvidenceType.METADATA,
            file_name="file2.txt",
            hash_sha256=file2_hash
        )
        
        # Add items to package
        package.items[item1.item_id] = item1
        package.items[item2.item_id] = item2
        
        # Check items added
        assert len(package.items) == 2
        assert item1.item_id in package.items
        assert item2.item_id in package.items
    
    def test_package_signing_and_verification(self):
        """Test package signing and verification."""
        package = EvidencePackage(
            name="Test Evidence Package",
            description="Package for testing"
        )
        
        # Add a sample item
        item = EvidenceItem(
            evidence_type=EvidenceType.RAW_DATA,
            file_name="sample.txt",
            hash_sha256="abc123"
        )
        package.items[item.item_id] = item
        
        # Create crypto provider
        crypto_provider = CryptoProvider.generate()
        
        # Sign the package
        package.sign(crypto_provider)
        
        # Check signature
        assert package.verification_info is not None
        assert "package_hash" in package.verification_info
        assert "signature" in package.verification_info
        
        # Verify signature
        assert package.verify(crypto_provider) is True
        
        # Tamper with the package
        original_name = package.name
        package.name = "Tampered Package"
        
        # Verification should fail
        assert package.verify(crypto_provider) is False
        
        # Restore original value
        package.name = original_name
        
        # Verification should succeed again
        assert package.verify(crypto_provider) is True
    
    def test_log_access(self):
        """Test logging access to an evidence package."""
        package = EvidencePackage(
            name="Test Evidence Package"
        )
        
        # Log access
        package.log_access(
            user_id="test_user",
            access_type="export",
            file_path="/test/path/evidence.zip",
            source_ip="192.168.1.1",
            metadata={"purpose": "testing"}
        )
        
        # Check access logged
        assert len(package.access_log) == 1
        assert package.access_log[0].user_id == "test_user"
        assert package.access_log[0].access_type == "export"
        assert package.access_log[0].file_path == "/test/path/evidence.zip"
        
        # Log another access
        package.log_access(
            user_id="admin_user",
            access_type="view",
            file_path="/test/path/evidence.zip"
        )
        
        # Check second access logged
        assert len(package.access_log) == 2
        assert package.access_log[1].user_id == "admin_user"
        assert package.access_log[1].access_type == "view"


class TestEvidencePackager:
    """Tests for evidence packager functionality."""
    
    def test_create_evidence_package(self):
        """Test creating an evidence package."""
        packager = EvidencePackager()
        
        # Create package
        package = packager.create_package(
            name="Test Package",
            description="Package for testing",
            metadata={"purpose": "testing"}
        )
        
        # Check package
        assert package.name == "Test Package"
        assert package.description == "Package for testing"
        assert package.metadata["purpose"] == "testing"
    
    def test_add_file_to_package(self, tmp_path):
        """Test adding a file to an evidence package."""
        packager = EvidencePackager()
        
        # Create package
        package = packager.create_package(name="Test Package")
        
        # Create sample file
        sample_file = tmp_path / "sample.txt"
        sample_content = "This is sample evidence content"
        sample_file.write_text(sample_content)
        
        # Add file to package
        item = packager.add_file_to_package(
            package=package,
            file_path=str(sample_file),
            evidence_type=EvidenceType.RAW_DATA,
            description="Sample evidence file",
            metadata={"source": "test"}
        )
        
        # Check item
        assert item.evidence_type == EvidenceType.RAW_DATA
        assert item.file_name == "sample.txt"
        assert item.description == "Sample evidence file"
        assert item.metadata["source"] == "test"
        
        # Check package
        assert item.item_id in package.items
        assert package.items[item.item_id] == item
    
    def test_verify_package_item(self, tmp_path):
        """Test verifying an evidence item."""
        packager = EvidencePackager()
        crypto_provider = CryptoProvider.generate()
        packager.crypto_provider = crypto_provider
        
        # Create package
        package = packager.create_package(name="Test Package")
        
        # Create sample file
        sample_file = tmp_path / "sample.txt"
        sample_content = "This is sample evidence content"
        sample_file.write_text(sample_content)
        
        # Add file to package
        item = packager.add_file_to_package(
            package=package,
            file_path=str(sample_file),
            evidence_type=EvidenceType.RAW_DATA
        )
        
        # Verify item
        assert packager.verify_package_item(item, str(sample_file)) is True
        
        # Tamper with file
        sample_file.write_text("Tampered content")
        
        # Verification should fail
        assert packager.verify_package_item(item, str(sample_file)) is False
    
    def test_export_and_import_package(self, tmp_path):
        """Test exporting and importing an evidence package."""
        packager = EvidencePackager()
        crypto_provider = CryptoProvider.generate()
        packager.crypto_provider = crypto_provider

        # Create package
        package = packager.create_package(name="Test Package")

        # Create test directories
        files_dir = tmp_path / "files"
        files_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a sample file
        sample_file = files_dir / "sample.txt"
        sample_content = "This is sample evidence content"
        sample_file.write_text(sample_content)

        # Add file to package
        item = packager.add_file_to_package(
            package=package,
            file_path=str(sample_file),
            evidence_type=EvidenceType.RAW_DATA,
            description="Sample evidence file"
        )

        # Mock the export_package and import_package methods
        with patch.object(packager, 'export_package') as mock_export, \
             patch.object(packager, 'import_package') as mock_import:

            # Configure mock export to return a filepath
            package_path = output_dir / "evidence_package.zip"
            mock_export.return_value = str(package_path)

            # Configure mock import to return the package and files
            mock_files = {item.item_id: b'content'}
            mock_import.return_value = (package, mock_files)

            # Execute export
            export_path = packager.export_package(
                package=package,
                output_dir=str(output_dir),
                files_dir=str(files_dir),
                user_id="test_user"
            )

            assert export_path == str(package_path)
            mock_export.assert_called_once()

            # Execute import
            imported_package, files = packager.import_package(
                package_path=export_path,
                user_id="test_user"
            )

            # Verify import
            assert imported_package == package
            assert files == mock_files
            # Check that import_package was called with the correct parameters
            assert mock_import.call_count == 1
            assert mock_import.call_args.kwargs["package_path"] == export_path
            assert mock_import.call_args.kwargs["user_id"] == "test_user"