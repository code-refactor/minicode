"""
Tamper-evident audit logging system.

This module provides a secure logging system that ensures log entries cannot
be modified once written, maintains a chain of integrity, and provides
cryptographic verification.
"""

import os
import json
import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple

from pydantic import BaseModel, Field, field_validator

from file_system_analyzer.utils.crypto import CryptoProvider


class AuditEventType(str, Enum):
    """Types of audit events to log."""
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    SCAN_ERROR = "scan_error"
    FILE_SCAN = "file_scan"
    SENSITIVE_DATA_FOUND = "sensitive_data_found"
    REPORT_GENERATION = "report_generation"
    REPORT_EXPORT = "report_export"
    BASELINE_CREATION = "baseline_creation"
    BASELINE_COMPARISON = "baseline_comparison"
    CONFIG_CHANGE = "config_change"
    USER_ACTION = "user_action"
    SYSTEM_ERROR = "system_error"
    CHAIN_VERIFICATION = "chain_verification"


class AuditEntry(BaseModel):
    """A single audit log entry with integrity protection."""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventType
    user_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    source_ip: Optional[str] = None
    previous_entry_hash: Optional[str] = None
    entry_hash: Optional[str] = None

    def model_post_init(self, __context):
        """Post initialization hook to calculate hash if not provided."""
        if self.entry_hash is None:
            self.calculate_hash()

    def calculate_hash(self):
        """Calculate a hash of this entry and set it as the entry_hash."""
        # Create a copy of values without the entry_hash (which doesn't exist yet)
        hashable_values = {k: v for k, v in self.model_dump().items() if k != "entry_hash"}

        # Convert datetime to ISO format for consistent serialization
        if "timestamp" in hashable_values and isinstance(hashable_values["timestamp"], datetime):
            hashable_values["timestamp"] = hashable_values["timestamp"].isoformat()

        # Sort keys for deterministic serialization
        serialized = json.dumps(hashable_values, sort_keys=True, default=str)
        self.entry_hash = hashlib.sha256(serialized.encode()).hexdigest()
        return self.entry_hash

    def hash_entry(self, v, info):
        """Legacy method for compatibility."""
        return self.calculate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary suitable for serialization."""
        data = self.model_dump()
        data["timestamp"] = data["timestamp"].isoformat()
        return data


class AuditLog(BaseModel):
    """A collection of audit log entries with integrity verification."""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entries: List[AuditEntry] = Field(default_factory=list)
    hmac_key_id: Optional[str] = None
    
    def add_entry(self, entry: AuditEntry, crypto_provider: Optional[CryptoProvider] = None) -> None:
        """Add an entry to the log, updating its hash chain and optionally signing it."""
        if self.entries:
            # Link to the previous entry
            entry.previous_entry_hash = self.entries[-1].entry_hash

        # Recalculate the entry hash to include the previous hash link
        entry.entry_hash = None  # Clear it to force recalculation
        entry.calculate_hash()
        
        # Sign the entry if crypto provider is available
        if crypto_provider:
            self.hmac_key_id = crypto_provider.key_id
            entry_data = json.dumps(entry.to_dict(), sort_keys=True).encode()
            signature = crypto_provider.hmac_sign(entry_data)
            # Store the signature in the details
            entry.details["hmac_signature"] = signature.hex()
            
        self.entries.append(entry)
        self.last_modified = datetime.now(timezone.utc)
    
    def verify_integrity(self, crypto_provider: Optional[CryptoProvider] = None) -> Tuple[bool, List[str]]:
        """Verify the integrity of the entire log, optionally checking signatures."""
        if not self.entries:
            return True, []
            
        errors = []
        prev_hash = None
        
        for i, entry in enumerate(self.entries):
            # Check hash link
            if i > 0 and entry.previous_entry_hash != prev_hash:
                errors.append(f"Entry {i}: Hash link broken. Expected {prev_hash}, got {entry.previous_entry_hash}")
            
            # Verify entry hash
            # Save original hash
            original_hash = entry.entry_hash

            # Calculate the hash
            entry.entry_hash = None
            current_hash = entry.calculate_hash()

            # Restore original hash for comparison
            expected_hash = original_hash
            entry.entry_hash = original_hash
            if entry.entry_hash != current_hash:
                errors.append(f"Entry {i}: Hash mismatch. Expected {entry.entry_hash}, calculated {current_hash}")
            
            # Verify HMAC signature if available
            if crypto_provider and "hmac_signature" in entry.details:
                signature_hex = entry.details["hmac_signature"]
                # Create a copy without the signature for verification
                verify_entry = entry.copy(deep=True)
                signature = bytes.fromhex(signature_hex)
                verify_entry.details.pop("hmac_signature")
                entry_data = json.dumps(verify_entry.to_dict(), sort_keys=True).encode()
                
                if not crypto_provider.hmac_verify(entry_data, signature):
                    errors.append(f"Entry {i}: HMAC signature verification failed")
            
            prev_hash = entry.entry_hash
            
        return len(errors) == 0, errors
    
    def to_json(self) -> str:
        """Convert the entire log to a JSON string."""
        data = self.model_dump()
        data["creation_time"] = data["creation_time"].isoformat()
        data["last_modified"] = data["last_modified"].isoformat()
        return json.dumps(data, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))


class AuditLogger:
    """Logger for creating tamper-evident audit records."""
    
    def __init__(
        self, 
        log_file: Optional[str] = None, 
        crypto_provider: Optional[CryptoProvider] = None,
        user_id: str = "system"
    ):
        """Initialize the audit logger."""
        self.log_file = log_file
        self.crypto_provider = crypto_provider
        self.user_id = user_id
        self.audit_log = self._load_log() if log_file and os.path.exists(log_file) else AuditLog()
    
    def _load_log(self) -> AuditLog:
        """Load an existing log file if available."""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                
            # Convert timestamps back to datetime objects
            data["creation_time"] = datetime.fromisoformat(data["creation_time"])
            data["last_modified"] = datetime.fromisoformat(data["last_modified"])
            
            entries = []
            for entry_data in data["entries"]:
                entry_data["timestamp"] = datetime.fromisoformat(entry_data["timestamp"])
                entries.append(AuditEntry(**entry_data))
                
            data["entries"] = entries
            return AuditLog(**data)
        except Exception as e:
            # If there's any error loading the log, create a new one and log the error
            new_log = AuditLog()
            error_entry = AuditEntry(
                event_type=AuditEventType.SYSTEM_ERROR,
                user_id=self.user_id,
                details={"error": f"Failed to load audit log: {str(e)}"}
            )
            new_log.add_entry(error_entry, self.crypto_provider)
            return new_log
    
    def log_event(
        self, 
        event_type: AuditEventType, 
        details: Dict[str, Any], 
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None
    ) -> None:
        """Log an audit event with details."""
        entry = AuditEntry(
            event_type=event_type,
            user_id=user_id or self.user_id,
            details=details,
            source_ip=source_ip
        )
        
        self.audit_log.add_entry(entry, self.crypto_provider)
        
        # Save to file if configured
        if self.log_file:
            self._save_log()
    
    def _save_log(self) -> None:
        """Save the audit log to a file."""
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Write to temporary file first, then rename for atomicity
        temp_file = f"{self.log_file}.tmp"
        with open(temp_file, 'w') as f:
            f.write(self.audit_log.to_json())
            
        os.replace(temp_file, self.log_file)
    
    def verify_log_integrity(self) -> Tuple[bool, List[str]]:
        """Verify the integrity of the audit log."""
        return self.audit_log.verify_integrity(self.crypto_provider)
    
    def get_log_entries(
        self, 
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> List[AuditEntry]:
        """Get log entries filtered by criteria."""
        entries = self.audit_log.entries
        
        if event_types:
            entries = [e for e in entries if e.event_type in event_types]
            
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
            
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
            
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
            
        return entries
    
    def export_log(self, output_file: str, include_signatures: bool = True) -> None:
        """Export the audit log to a file."""
        # Create a copy of the log for export
        export_log = self.audit_log.copy(deep=True)
        
        # Remove signatures if not including them
        if not include_signatures:
            for entry in export_log.entries:
                if "hmac_signature" in entry.details:
                    entry.details.pop("hmac_signature")
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(export_log.to_json())
        
        # Log the export
        self.log_event(
            event_type=AuditEventType.REPORT_EXPORT,
            details={
                "output_file": output_file,
                "include_signatures": include_signatures,
                "entry_count": len(export_log.entries)
            }
        )