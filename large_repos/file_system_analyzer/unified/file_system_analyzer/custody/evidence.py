"""
Evidence chain-of-custody system.

This module provides cryptographic verification systems for exported reports to 
maintain evidence integrity, including cryptographic signing, tamper detection, 
and timestamping.
"""

import os
import json
import uuid
import zipfile
import hashlib
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Tuple, BinaryIO

from pydantic import BaseModel, Field

from file_system_analyzer.utils.crypto import CryptoProvider
from file_system_analyzer.reporting.reports import ComplianceReport
from file_system_analyzer.differential.analyzer import ScanBaseline
from file_system_analyzer.audit.logger import AuditLog, AuditEntry, AuditEventType


class EvidenceType(str, Enum):
    """Types of evidence that can be packaged."""
    COMPLIANCE_REPORT = "compliance_report"
    SCAN_BASELINE = "scan_baseline"
    AUDIT_LOG = "audit_log"
    SCAN_RESULT = "scan_result"
    DIFF_RESULT = "diff_result"
    RAW_DATA = "raw_data"
    SCREENSHOT = "screenshot"
    METADATA = "metadata"


class EvidenceAccess(BaseModel):
    """Record of access to an evidence package."""
    access_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    access_type: str
    file_path: str
    source_ip: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """A single item in an evidence package."""
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_type: EvidenceType
    file_name: str
    description: Optional[str] = None
    hash_sha256: str
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    verification_info: Optional[Dict[str, Any]] = None


class EvidencePackage(BaseModel):
    """A package of evidence with chain-of-custody tracking."""
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    description: Optional[str] = None
    items: Dict[str, EvidenceItem] = Field(default_factory=dict)
    access_log: List[EvidenceAccess] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    verification_info: Optional[Dict[str, Any]] = None
    
    def sign(self, crypto_provider: CryptoProvider) -> None:
        """Sign the package with cryptographic verification."""
        # Create a canonical representation of the package
        package_data = self.model_dump(exclude={"verification_info"})
        package_json = json.dumps(package_data, sort_keys=True, default=str).encode()
        
        # Create a hash of the package
        package_hash = crypto_provider.secure_hash(package_json)
        
        # Create a timestamped signature
        signature = crypto_provider.timestamp_signature(package_json)
        
        self.verification_info = {
            "package_hash": package_hash,
            "signature": signature,
            "verification_method": "crypto_provider",
            "key_id": crypto_provider.key_id
        }
    
    def verify(self, crypto_provider: CryptoProvider) -> bool:
        """Verify the cryptographic signature of the package."""
        if not self.verification_info:
            return False
            
        # Recreate the package data without verification_info
        package_data = self.model_dump(exclude={"verification_info"})
        package_json = json.dumps(package_data, sort_keys=True, default=str).encode()
        
        # Verify the hash
        calculated_hash = crypto_provider.secure_hash(package_json)
        stored_hash = self.verification_info.get("package_hash")
        if calculated_hash != stored_hash:
            return False
            
        # Verify the signature
        signature = self.verification_info.get("signature", {})
        return crypto_provider.verify_timestamped_signature(package_json, signature)
    
    def log_access(
        self, 
        user_id: str, 
        access_type: str, 
        file_path: str, 
        source_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log access to the evidence package."""
        access = EvidenceAccess(
            user_id=user_id,
            access_type=access_type,
            file_path=file_path,
            source_ip=source_ip,
            metadata=metadata or {}
        )
        
        self.access_log.append(access)


class EvidencePackager:
    """Tool for packaging and verifying evidence."""
    
    def __init__(self, crypto_provider: Optional[CryptoProvider] = None):
        """Initialize with optional crypto provider."""
        self.crypto_provider = crypto_provider
    
    def create_package(
        self, 
        name: str, 
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidencePackage:
        """Create a new evidence package."""
        package = EvidencePackage(
            name=name,
            description=description,
            metadata=metadata or {}
        )
        
        # Sign the package if a crypto provider is available
        if self.crypto_provider:
            package.sign(self.crypto_provider)
            
        return package
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate the SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def add_file_to_package(
        self, 
        package: EvidencePackage, 
        file_path: str, 
        evidence_type: EvidenceType,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceItem:
        """Add a file to an evidence package."""
        file_name = os.path.basename(file_path)
        file_hash = self._calculate_file_hash(file_path)
        
        item = EvidenceItem(
            evidence_type=evidence_type,
            file_name=file_name,
            description=description,
            hash_sha256=file_hash,
            metadata=metadata or {}
        )
        
        # Sign the item if a crypto provider is available
        if self.crypto_provider:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            signature = self.crypto_provider.timestamp_signature(data)
            
            item.verification_info = {
                "file_hash": file_hash,
                "signature": signature,
                "verification_method": "crypto_provider",
                "key_id": self.crypto_provider.key_id
            }
        
        package.items[item.item_id] = item
        
        # Sign the updated package
        if self.crypto_provider:
            package.sign(self.crypto_provider)
            
        return item
    
    def verify_package_item(
        self, 
        item: EvidenceItem,
        file_path: str
    ) -> bool:
        """Verify the integrity of an evidence item against a file."""
        # Verify file hash
        file_hash = self._calculate_file_hash(file_path)
        if file_hash != item.hash_sha256:
            return False
            
        # Verify cryptographic signature if available
        if self.crypto_provider and item.verification_info:
            with open(file_path, 'rb') as f:
                data = f.read()
                
            signature = item.verification_info.get("signature", {})
            return self.crypto_provider.verify_timestamped_signature(data, signature)
            
        return True
    
    def export_package(
        self, 
        package: EvidencePackage, 
        output_dir: str,
        files_dir: str,
        user_id: str,
        source_ip: Optional[str] = None
    ) -> str:
        """Export an evidence package to a directory."""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a unique filename for the package
        package_filename = f"evidence_{package.package_id}.zip"
        package_path = os.path.join(output_dir, package_filename)
        
        # Create zip file
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add manifest
            manifest_data = package.model_dump()
            manifest_json = json.dumps(manifest_data, default=str, indent=2)
            zipf.writestr("manifest.json", manifest_json)
            
            # Add items
            for item_id, item in package.items.items():
                # Source file path
                source_file = os.path.join(files_dir, item.file_name)
                
                # Verify file integrity
                if not os.path.exists(source_file):
                    raise FileNotFoundError(f"Evidence file not found: {source_file}")
                    
                if not self.verify_package_item(item, source_file):
                    raise ValueError(f"Evidence file integrity check failed: {source_file}")
                
                # Add to zip with item ID to avoid name collisions
                zipf.write(source_file, f"evidence/{item_id}_{item.file_name}")
        
        # Log access to the package
        package.log_access(
            user_id=user_id,
            access_type="export",
            file_path=package_path,
            source_ip=source_ip,
            metadata={"output_format": "zip"}
        )
        
        # Sign the updated package
        if self.crypto_provider:
            package.sign(self.crypto_provider)
            
        return package_path
    
    def import_package(
        self, 
        package_path: str, 
        user_id: str,
        source_ip: Optional[str] = None
    ) -> Tuple[EvidencePackage, Dict[str, bytes]]:
        """Import an evidence package from a file."""
        if not os.path.exists(package_path):
            raise FileNotFoundError(f"Evidence package not found: {package_path}")
            
        # Extract files from the package
        files = {}
        package = None
        
        with zipfile.ZipFile(package_path, 'r') as zipf:
            # Load manifest
            try:
                manifest_data = json.loads(zipf.read("manifest.json"))
                package = EvidencePackage(**manifest_data)
            except (KeyError, json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Invalid evidence package format: {str(e)}")
                
            # Extract evidence files
            for zipinfo in zipf.infolist():
                if zipinfo.filename.startswith("evidence/"):
                    # Extract the file
                    file_data = zipf.read(zipinfo.filename)
                    
                    # Parse the item ID from the filename
                    filename_parts = os.path.basename(zipinfo.filename).split("_", 1)
                    if len(filename_parts) != 2:
                        logging.warning(f"Skipping file with invalid name format: {zipinfo.filename}")
                        continue
                        
                    item_id, file_name = filename_parts
                    
                    # Find the corresponding item in the manifest
                    if item_id not in package.items:
                        logging.warning(f"Skipping file with unknown item ID: {item_id}")
                        continue
                    
                    # Verify the file content against the hash in the manifest
                    item = package.items[item_id]
                    file_hash = hashlib.sha256(file_data).hexdigest()
                    
                    if file_hash != item.hash_sha256:
                        raise ValueError(f"File integrity check failed for {file_name}")
                    
                    files[item_id] = file_data
        
        # Log access to the package
        package.log_access(
            user_id=user_id,
            access_type="import",
            file_path=package_path,
            source_ip=source_ip
        )
        
        # Verify the package integrity
        if self.crypto_provider and package.verification_info:
            if not package.verify(self.crypto_provider):
                raise ValueError("Package integrity verification failed")
        
        return package, files
    
    def verify_package(self, package: EvidencePackage) -> bool:
        """Verify the integrity of an evidence package."""
        if not self.crypto_provider:
            return False
        
        return package.verify(self.crypto_provider)