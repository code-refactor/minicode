"""Repository for managing security findings."""

import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Generator

from pydantic import ValidationError as PydanticValidationError

from common.core import BaseService, StorageInterface, ValidationError
from securetask.findings.models import Finding
from securetask.utils.crypto import CryptoManager
from securetask.utils.validation import ValidationError as SecureValidationError


class EncryptedFindingStorage(StorageInterface[Finding]):
    """Encrypted file storage for security findings with individual files per finding."""
    
    def __init__(self, storage_dir: Path, crypto_manager: Optional[CryptoManager] = None):
        """Initialize encrypted storage."""
        self.storage_dir = Path(storage_dir)
        self.findings_dir = self.storage_dir / "findings"
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        self.crypto_manager = crypto_manager or CryptoManager()
        self._cache: Dict[str, Finding] = {}
    
    def _get_file_paths(self, finding_id: str) -> tuple[Path, Path]:
        """Get encrypted file and HMAC digest paths for a finding."""
        finding_id_str = str(finding_id) if isinstance(finding_id, uuid.UUID) else finding_id
        enc_path = self.findings_dir / f"{finding_id_str}.json.enc"
        hmac_path = self.findings_dir / f"{finding_id_str}.hmac"
        return enc_path, hmac_path
    
    def create(self, entity: Finding) -> str:
        """Create a new finding."""
        finding_id = str(entity.id) if hasattr(entity, 'id') else str(uuid.uuid4())
        
        # Serialize to JSON
        finding_dict = entity.to_dict()
        json_data = json.dumps(finding_dict, default=str).encode()
        
        # Encrypt
        encrypted_data, digest = self.crypto_manager.encrypt(json_data)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(finding_id)
        
        # Save encrypted data
        with open(enc_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Save HMAC digest
        with open(hmac_path, 'wb') as f:
            f.write(digest)
        
        # Cache the finding
        self._cache[finding_id] = entity
        
        return finding_id
    
    def get(self, entity_id: Union[str, uuid.UUID]) -> Optional[Finding]:
        """Get a finding by ID."""
        finding_id = str(entity_id)
        
        # Check cache first
        if finding_id in self._cache:
            return self._cache[finding_id]
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(finding_id)
        
        if not enc_path.exists() or not hmac_path.exists():
            return None
        
        # Read encrypted data and digest
        with open(enc_path, 'rb') as f:
            encrypted_data = f.read()
        with open(hmac_path, 'rb') as f:
            digest = f.read()
        
        # Decrypt
        decrypted_data = self.crypto_manager.decrypt(encrypted_data, digest)
        
        # Parse JSON
        finding_dict = json.loads(decrypted_data.decode())
        
        # Create Finding instance
        finding = Finding.from_dict(finding_dict)
        
        # Cache it
        self._cache[finding_id] = finding
        
        return finding
    
    def update(self, entity: Finding) -> Optional[Finding]:
        """Update an existing finding."""
        finding_id = str(entity.id)
        
        # Check if exists
        enc_path, hmac_path = self._get_file_paths(finding_id)
        if not enc_path.exists():
            return None
        
        # Update timestamp
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.now()
        
        # Save updated finding
        self.create(entity)
        
        return entity
    
    def delete(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Delete a finding."""
        finding_id = str(entity_id)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(finding_id)
        
        # Delete files
        deleted = False
        if enc_path.exists():
            enc_path.unlink()
            deleted = True
        if hmac_path.exists():
            hmac_path.unlink()
        
        # Remove from cache
        if finding_id in self._cache:
            del self._cache[finding_id]
        
        return deleted
    
    def list(self, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None,
             limit: Optional[int] = None, offset: int = 0) -> List[Finding]:
        """List all findings."""
        findings = []
        
        # Load all findings from disk
        for enc_file in self.findings_dir.glob("*.json.enc"):
            finding_id = enc_file.stem.replace('.json', '')
            finding = self.get(finding_id)
            if finding:
                findings.append(finding)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                findings = [f for f in findings if getattr(f, key, None) == value]
        
        # Sort if requested
        if sort_by:
            reverse = sort_by.startswith('-')
            key = sort_by[1:] if reverse else sort_by
            findings.sort(key=lambda x: getattr(x, key, ''), reverse=reverse)
        
        # Apply pagination
        if offset:
            findings = findings[offset:]
        if limit:
            findings = findings[:limit]
        
        return findings
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count findings."""
        return len(self.list(filters=filters))
    
    def clear(self) -> None:
        """Clear all findings."""
        for enc_file in self.findings_dir.glob("*.json.enc"):
            enc_file.unlink()
        for hmac_file in self.findings_dir.glob("*.hmac"):
            hmac_file.unlink()
        self._cache.clear()
    
    def exists(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Check if a finding exists."""
        finding_id = str(entity_id)
        enc_path, _ = self._get_file_paths(finding_id)
        return enc_path.exists()


class FindingRepository(BaseService[Finding]):
    """
    Service for CRUD operations on security findings.
    
    Provides encrypted storage and retrieval of finding data with
    additional functionality for searching and filtering findings.
    """
    
    def __init__(self, storage_dir: str, crypto_manager: Optional[CryptoManager] = None):
        """
        Initialize the finding repository.
        
        Args:
            storage_dir: Directory where findings will be stored
            crypto_manager: Optional crypto manager for encryption
        """
        # Create encrypted storage with individual files per finding
        storage = EncryptedFindingStorage(storage_dir, crypto_manager)
        
        # Initialize base service
        super().__init__(storage)
        
        # Add custom validators
        self.add_validator(self._validate_finding_business_rules)
    
    def _validate_finding_business_rules(self, finding: Finding) -> List[ValidationError]:
        """Custom business rule validation for findings."""
        errors = []
        
        # Check CVSS consistency
        if finding.cvss_score and not finding.cvss_vector:
            errors.append(ValidationError(
                field="cvss_vector",
                message="CVSS vector is required when CVSS score is provided"
            ))
        
        # Check remediation fields consistency
        if finding.status == "remediated":
            if not finding.remediation_date:
                finding.remediation_date = datetime.now()
            if not finding.remediated_by:
                errors.append(ValidationError(
                    field="remediated_by",
                    message="Remediated by field is required for remediated findings"
                ))
        
        return errors
    
    def create_finding(self, finding: Finding) -> str:
        """
        Create a new security finding with validation and timing.
        
        Args:
            finding: The finding to create
            
        Returns:
            The ID of the created finding
            
        Raises:
            ValidationError: If finding validation fails
        """
        start_time = time.time()
        
        try:
            # Use base service's create_with_validation
            finding_id = self.create_with_validation(finding)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Finding creation took {execution_time*1000:.2f}ms")
                
            return finding_id
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def get_finding(self, finding_id: str) -> Optional[Finding]:
        """
        Retrieve a finding by ID with timing.
        
        Args:
            finding_id: ID of the finding to retrieve
            
        Returns:
            The retrieved finding or None if not found
        """
        start_time = time.time()
        
        finding = self.get(finding_id)
        
        # Track execution time
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Finding retrieval took {execution_time*1000:.2f}ms")
        
        return finding
    
    def update_finding(self, finding: Finding) -> Optional[Finding]:
        """
        Update an existing finding with validation and timing.
        
        Args:
            finding: The finding to update
            
        Returns:
            The updated finding or None if not found
            
        Raises:
            ValidationError: If finding validation fails
        """
        start_time = time.time()
        
        try:
            # Use base service's update_with_validation
            updated = self.update_with_validation(finding)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Finding update took {execution_time*1000:.2f}ms")
            
            return updated
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def delete_finding(self, finding_id: str) -> bool:
        """
        Delete a finding by ID.
        
        Args:
            finding_id: ID of the finding to delete
            
        Returns:
            True if deleted, False if not found
        """
        return self.delete_with_hooks(finding_id)
    
    def list_findings(
        self, 
        filters: Optional[Dict[str, Any]] = None, 
        sort_by: str = "discovered_date", 
        reverse: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Finding]:
        """
        List findings with optional filtering and sorting.
        
        Args:
            filters: Optional filters as field-value pairs
            sort_by: Field to sort by
            reverse: Whether to sort in reverse order
            limit: Maximum number of findings to return
            offset: Number of findings to skip
            
        Returns:
            List of findings matching criteria
        """
        # Convert sort direction to storage format
        storage_sort_by = f"-{sort_by}" if reverse else sort_by
        
        return self.list(
            filters=filters,
            sort_by=storage_sort_by,
            limit=limit,
            offset=offset
        )
    
    def count_findings(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count findings matching filters.
        
        Args:
            filters: Optional filters as field-value pairs
            
        Returns:
            Number of findings matching criteria
        """
        return self.count(filters)
    
    # Legacy compatibility methods
    def create(self, finding: Finding) -> Finding:
        """Legacy compatibility method."""
        self.create_finding(finding)
        return finding
    
    def get(self, finding_id: str) -> Finding:
        """Legacy compatibility method."""
        finding = self.get_finding(finding_id)
        if finding is None:
            raise FileNotFoundError(f"Finding not found: {finding_id}")
        return finding
    
    def update(self, finding: Finding) -> Finding:
        """Legacy compatibility method."""
        updated = self.update_finding(finding)
        if updated is None:
            raise FileNotFoundError(f"Finding not found: {finding.id}")
        return updated
    
    def delete(self, finding_id: str) -> bool:
        """Legacy compatibility method."""
        return self.delete_finding(finding_id)
    
    def list(self, *args, **kwargs) -> List[Finding]:
        """Legacy compatibility method."""
        return self.list_findings(*args, **kwargs)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Legacy compatibility method."""
        return self.count_findings(filters)