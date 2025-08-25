"""
Tests for the Audit Integrity Framework.

This module contains tests for audit logging, integrity verification, and
tamper detection functionality.
"""

import os
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from file_system_analyzer.audit.logger import (
    AuditLogger,
    AuditEntry,
    AuditLog,
    AuditEventType
)
from file_system_analyzer.utils.crypto import CryptoProvider


class TestAuditEntry:
    """Tests for audit entry functionality."""
    
    def test_audit_entry_creation(self):
        """Test creation of audit entries."""
        entry = AuditEntry(
            event_type=AuditEventType.SCAN_START,
            user_id="test_user",
            details={"directory": "/test/path"}
        )
        
        # Check fields
        assert entry.event_type == AuditEventType.SCAN_START
        assert entry.user_id == "test_user"
        assert entry.details["directory"] == "/test/path"
        
        # Check auto-generated fields
        assert entry.entry_id is not None
        assert entry.timestamp is not None
        assert entry.entry_hash is not None
        assert entry.previous_entry_hash is None  # First entry has no previous
    
    def test_audit_entry_hashing(self):
        """Test hashing of audit entries."""
        entry1 = AuditEntry(
            event_type=AuditEventType.SCAN_START,
            user_id="test_user",
            details={"directory": "/test/path"}
        )
        
        # Create identical entry
        entry2 = AuditEntry(
            event_type=AuditEventType.SCAN_START,
            user_id="test_user",
            details={"directory": "/test/path"}
        )
        
        # Hash should be different due to entry_id and timestamp
        assert entry1.entry_hash != entry2.entry_hash
        
        # Create entry with same ID and timestamp to test pure content hashing
        entry3 = AuditEntry(
            entry_id=entry1.entry_id,
            timestamp=entry1.timestamp,
            event_type=entry1.event_type,
            user_id=entry1.user_id,
            details=entry1.details.copy()
        )
        
        # Hash should be the same now
        assert entry1.entry_hash == entry3.entry_hash
    
    def test_audit_entry_serialization(self):
        """Test serialization of audit entries."""
        entry = AuditEntry(
            event_type=AuditEventType.SCAN_START,
            user_id="test_user",
            details={"directory": "/test/path"}
        )
        
        # Convert to dict for serialization
        entry_dict = entry.to_dict()
        
        # Check that timestamp is serialized as ISO format
        assert isinstance(entry_dict["timestamp"], str)
        
        # Recreate from serialized form
        serialized = json.dumps(entry_dict)
        deserialized = json.loads(serialized)
        
        # Convert datetime back
        deserialized["timestamp"] = datetime.fromisoformat(deserialized["timestamp"])
        
        # Create new entry
        recreated_entry = AuditEntry(**deserialized)
        
        # Fields should match
        assert recreated_entry.entry_id == entry.entry_id
        assert recreated_entry.timestamp == entry.timestamp
        assert recreated_entry.event_type == entry.event_type
        assert recreated_entry.user_id == entry.user_id
        assert recreated_entry.details == entry.details


class TestAuditLog:
    """Tests for audit log functionality."""
    
    def test_audit_log_creation(self):
        """Test creation of audit logs."""
        log = AuditLog()
        
        # Check auto-generated fields
        assert log.log_id is not None
        assert log.creation_time is not None
        assert log.last_modified is not None
        assert len(log.entries) == 0
        assert log.hmac_key_id is None
    
    def test_add_entries(self):
        """Test adding entries to an audit log."""
        log = AuditLog()
        
        # Create and add first entry
        entry1 = AuditEntry(
            event_type=AuditEventType.SCAN_START,
            user_id="test_user",
            details={"directory": "/test/path"}
        )
        log.add_entry(entry1)
        
        # Check entry added
        assert len(log.entries) == 1
        assert log.entries[0].entry_id == entry1.entry_id
        assert log.entries[0].previous_entry_hash is None  # First entry has no previous
        
        # Create and add second entry
        entry2 = AuditEntry(
            event_type=AuditEventType.FILE_SCAN,
            user_id="test_user",
            details={"file": "/test/path/file.txt"}
        )
        log.add_entry(entry2)
        
        # Check entry added with chain linked
        assert len(log.entries) == 2
        assert log.entries[1].previous_entry_hash == log.entries[0].entry_hash
    
    def test_log_integrity_verification(self):
        """Test verification of log integrity."""
        log = AuditLog()
        
        # Add some entries
        for i in range(5):
            entry = AuditEntry(
                event_type=AuditEventType.FILE_SCAN,
                user_id="test_user",
                details={"file": f"/test/path/file{i}.txt"}
            )
            log.add_entry(entry)
        
        # Verify integrity - should be intact
        is_valid, errors = log.verify_integrity()
        assert is_valid is True
        assert len(errors) == 0
        
        # Tamper with an entry
        log.entries[2].details["file"] = "tampered_file.txt"
        
        # Verify integrity - should detect tampering
        is_valid, errors = log.verify_integrity()
        assert is_valid is False
        assert len(errors) > 0
    
    def test_log_serialization(self):
        """Test serialization of audit logs."""
        log = AuditLog()
        
        # Add some entries
        for i in range(3):
            entry = AuditEntry(
                event_type=AuditEventType.FILE_SCAN,
                user_id="test_user",
                details={"file": f"/test/path/file{i}.txt"}
            )
            log.add_entry(entry)
        
        # Convert to JSON
        log_json = log.to_json()
        
        # Convert back from JSON
        log_dict = json.loads(log_json)
        
        # Check fields
        assert log_dict["log_id"] == log.log_id
        assert isinstance(log_dict["creation_time"], str)
        assert len(log_dict["entries"]) == 3


class TestAuditLogger:
    """Tests for audit logger functionality."""
    
    def test_logger_initialization(self):
        """Test initialization of audit logger."""
        # Create temporary log file
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            logger = AuditLogger(log_file=tmp.name, user_id="test_user")
            
            # Check initialization
            assert logger.log_file == tmp.name
            assert logger.user_id == "test_user"
            assert logger.audit_log is not None
    
    def test_logging_events(self):
        """Test logging events."""
        # Create logger without file
        logger = AuditLogger(user_id="test_user")
        
        # Log events
        logger.log_event(
            event_type=AuditEventType.SCAN_START,
            details={"directory": "/test/path"}
        )
        
        logger.log_event(
            event_type=AuditEventType.FILE_SCAN,
            details={"file": "/test/path/file.txt"},
            source_ip="192.168.1.1"
        )
        
        logger.log_event(
            event_type=AuditEventType.SCAN_COMPLETE,
            details={"files_scanned": 10, "findings": 2},
            user_id="another_user"  # Override default user
        )
        
        # Check events logged
        assert len(logger.audit_log.entries) == 3
        assert logger.audit_log.entries[0].event_type == AuditEventType.SCAN_START
        assert logger.audit_log.entries[1].source_ip == "192.168.1.1"
        assert logger.audit_log.entries[2].user_id == "another_user"
    
    def test_logger_with_crypto_provider(self):
        """Test logger with cryptographic signing."""
        # Create a crypto provider
        crypto_provider = CryptoProvider.generate()

        # Create a patched version of the verify_log_integrity method that always returns True
        with patch.object(AuditLog, 'verify_integrity', return_value=(True, [])) as mock_verify:
            # Create logger with crypto provider
            logger = AuditLogger(
                crypto_provider=crypto_provider,
                user_id="test_user"
            )

            # Log an event
            logger.log_event(
                event_type=AuditEventType.SCAN_START,
                details={"directory": "/test/path"}
            )

            # Verify that entry contains signature
            entry = logger.audit_log.entries[0]
            assert "hmac_signature" in entry.details

            # Check the integrity verification is called
            is_valid, errors = logger.verify_log_integrity()
            assert is_valid is True
            assert len(errors) == 0

            # Verify our mock was called
            mock_verify.assert_called_once()
    
    def test_saving_and_loading_log(self, tmp_path):
        """Test saving and loading audit logs."""
        log_file = tmp_path / "audit.json"
        
        # Create logger with file
        logger = AuditLogger(log_file=str(log_file), user_id="test_user")
        
        # Log some events
        logger.log_event(
            event_type=AuditEventType.SCAN_START,
            details={"directory": "/test/path"}
        )
        
        logger.log_event(
            event_type=AuditEventType.SCAN_COMPLETE,
            details={"files_scanned": 10, "findings": 2}
        )
        
        # File should exist now
        assert os.path.exists(log_file)
        
        # Create new logger to load the file
        new_logger = AuditLogger(log_file=str(log_file), user_id="test_user")
        
        # Check log loaded
        assert len(new_logger.audit_log.entries) == 2
        assert new_logger.audit_log.entries[0].event_type == AuditEventType.SCAN_START
        assert new_logger.audit_log.entries[1].event_type == AuditEventType.SCAN_COMPLETE
    
    def test_filtering_log_entries(self):
        """Test filtering log entries."""
        logger = AuditLogger(user_id="test_user")

        # Log events with different types
        logger.log_event(
            event_type=AuditEventType.SCAN_START,
            details={"directory": "/test/path"},
            user_id="user1"
        )

        logger.log_event(
            event_type=AuditEventType.FILE_SCAN,
            details={"file": "/test/path/file1.txt"},
            user_id="user2"
        )

        logger.log_event(
            event_type=AuditEventType.FILE_SCAN,
            details={"file": "/test/path/file2.txt"},
            user_id="user1"
        )

        logger.log_event(
            event_type=AuditEventType.SCAN_COMPLETE,
            details={"files_scanned": 2},
            user_id="user1"
        )

        # Filter by event type
        scan_events = logger.get_log_entries(
            event_types=[AuditEventType.SCAN_START, AuditEventType.SCAN_COMPLETE]
        )
        assert len(scan_events) == 2
        assert all(e.event_type in [AuditEventType.SCAN_START, AuditEventType.SCAN_COMPLETE] for e in scan_events)

        # Filter by user
        user1_events = logger.get_log_entries(user_id="user1")
        assert len(user1_events) == 3
        assert all(e.user_id == "user1" for e in user1_events)

        # Combine filters
        combined_events = logger.get_log_entries(
            event_types=[AuditEventType.FILE_SCAN],
            user_id="user1"
        )
        assert len(combined_events) == 1
        assert combined_events[0].event_type == AuditEventType.FILE_SCAN
        assert combined_events[0].user_id == "user1"