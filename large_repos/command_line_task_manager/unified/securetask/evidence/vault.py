"""Evidence Vault for secure storage of vulnerability evidence."""

import os
import shutil
import json
import base64
import hashlib
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO, Tuple, Union, Set

from pydantic import ValidationError as PydanticValidationError

from common.core import BaseService, FileStorage, StorageInterface, ValidationError
from securetask.evidence.models import Evidence, EvidenceType, AccessLevel
from securetask.utils.crypto import CryptoManager
from securetask.utils.validation import ValidationError as SecureValidationError, validate_file_size


class EncryptedEvidenceStorage(StorageInterface[Evidence]):
    """Encrypted file storage for evidence with individual files per evidence item."""
    
    def __init__(self, storage_dir: Path, crypto_manager: Optional[CryptoManager] = None):
        """Initialize encrypted storage."""
        self.storage_dir = Path(storage_dir)
        self.evidence_dir = self.storage_dir / "metadata"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.crypto_manager = crypto_manager or CryptoManager()
        self._cache: Dict[str, Evidence] = {}
    
    def _get_file_paths(self, evidence_id: str) -> tuple[Path, Path]:
        """Get encrypted file and HMAC digest paths for evidence metadata."""
        evidence_id_str = str(evidence_id) if isinstance(evidence_id, uuid.UUID) else evidence_id
        enc_path = self.evidence_dir / f"{evidence_id_str}.json.enc"
        hmac_path = self.evidence_dir / f"{evidence_id_str}.hmac"
        return enc_path, hmac_path
    
    def create(self, entity: Evidence) -> str:
        """Create a new evidence."""
        evidence_id = str(entity.id) if hasattr(entity, 'id') else str(uuid.uuid4())
        
        # Serialize to JSON
        evidence_dict = entity.to_dict()
        json_data = json.dumps(evidence_dict, default=str).encode()
        
        # Encrypt
        encrypted_data, digest = self.crypto_manager.encrypt(json_data)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(evidence_id)
        
        # Save encrypted data
        with open(enc_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Save HMAC digest
        with open(hmac_path, 'wb') as f:
            f.write(digest)
        
        # Cache the evidence
        self._cache[evidence_id] = entity
        
        return evidence_id
    
    def get(self, entity_id: Union[str, uuid.UUID]) -> Optional[Evidence]:
        """Get evidence by ID."""
        evidence_id = str(entity_id)
        
        # Check cache first
        if evidence_id in self._cache:
            return self._cache[evidence_id]
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(evidence_id)
        
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
        evidence_dict = json.loads(decrypted_data.decode())
        
        # Create Evidence instance
        evidence = Evidence.from_dict(evidence_dict)
        
        # Cache it
        self._cache[evidence_id] = evidence
        
        return evidence
    
    def update(self, entity: Evidence) -> Optional[Evidence]:
        """Update an existing evidence."""
        evidence_id = str(entity.id)
        
        # Check if exists
        enc_path, hmac_path = self._get_file_paths(evidence_id)
        if not enc_path.exists():
            return None
        
        # Update timestamp
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.now()
        
        # Save updated evidence
        self.create(entity)
        
        return entity
    
    def delete(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Delete evidence."""
        evidence_id = str(entity_id)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(evidence_id)
        
        # Delete files
        deleted = False
        if enc_path.exists():
            enc_path.unlink()
            deleted = True
        if hmac_path.exists():
            hmac_path.unlink()
        
        # Remove from cache
        if evidence_id in self._cache:
            del self._cache[evidence_id]
        
        return deleted
    
    def list(self, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None,
             limit: Optional[int] = None, offset: int = 0) -> List[Evidence]:
        """List all evidence."""
        evidence_list = []
        
        # Load all evidence from disk
        for enc_file in self.evidence_dir.glob("*.json.enc"):
            evidence_id = enc_file.stem.replace('.json', '')
            evidence = self.get(evidence_id)
            if evidence:
                evidence_list.append(evidence)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if key == "tags":
                    # Special handling for tags - check if the tag is in the set
                    evidence_list = [e for e in evidence_list if hasattr(e, 'tags') and value in e.tags]
                elif key == "type":
                    # Special handling for enum types
                    evidence_list = [e for e in evidence_list if e.type == value or (hasattr(e.type, 'value') and e.type.value == value)]
                elif key == "access_level":
                    # Special handling for enum access levels
                    evidence_list = [e for e in evidence_list if e.access_level == value or (hasattr(e.access_level, 'value') and e.access_level.value == value)]
                else:
                    # Standard equality check
                    evidence_list = [e for e in evidence_list if getattr(e, key, None) == value]
        
        # Sort if requested
        if sort_by:
            reverse = sort_by.startswith('-')
            key = sort_by[1:] if reverse else sort_by
            evidence_list.sort(key=lambda x: getattr(x, key, ''), reverse=reverse)
        
        # Apply pagination
        if offset:
            evidence_list = evidence_list[offset:]
        if limit:
            evidence_list = evidence_list[:limit]
        
        return evidence_list
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count evidence."""
        return len(self.list(filters=filters))
    
    def clear(self) -> None:
        """Clear all evidence."""
        for enc_file in self.evidence_dir.glob("*.json.enc"):
            enc_file.unlink()
        for hmac_file in self.evidence_dir.glob("*.hmac"):
            hmac_file.unlink()
        self._cache.clear()
    
    def exists(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Check if evidence exists."""
        evidence_id = str(entity_id)
        enc_path, _ = self._get_file_paths(evidence_id)
        return enc_path.exists()


class EvidenceVault(BaseService[Evidence]):
    """
    Secure storage system for vulnerability evidence.
    
    Provides encrypted storage and retrieval of evidence files with
    access controls, integrity verification, and metadata management.
    """
    
    def __init__(
        self, 
        storage_dir: str, 
        crypto_manager: Optional[CryptoManager] = None,
        max_file_size_mb: int = 100
    ):
        """
        Initialize the evidence vault.
        
        Args:
            storage_dir: Directory where evidence will be stored
            crypto_manager: Optional crypto manager for encryption
            max_file_size_mb: Maximum allowed file size in megabytes
        """
        # Set up directories
        self.storage_dir = Path(storage_dir)
        self.evidence_dir = self.storage_dir / "evidence"
        self.metadata_dir = self.storage_dir / "metadata"
        
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.crypto_manager = crypto_manager or CryptoManager()
        self.max_file_size_mb = max_file_size_mb
        
        # Create encrypted storage for metadata with individual files
        storage = EncryptedEvidenceStorage(self.storage_dir, crypto_manager)
        
        # Initialize base service
        super().__init__(storage)
        
        # Add custom validators
        self.add_validator(self._validate_evidence_business_rules)
        
        # Add hooks for file operations
        self.add_post_delete_hook(self._cleanup_evidence_files)
    
    def _validate_evidence_business_rules(self, evidence: Evidence) -> List[ValidationError]:
        """Custom business rule validation for evidence."""
        errors = []
        
        # Validate file path if provided
        if evidence.file_path and not os.path.exists(evidence.file_path):
            errors.append(ValidationError(
                field="file_path",
                message="Evidence file does not exist at specified path"
            ))
        
        # Validate hash consistency
        if evidence.hash_original and evidence.hash_encrypted:
            if len(evidence.hash_original) != 64:  # SHA-256 should be 64 chars
                errors.append(ValidationError(
                    field="hash_original",
                    message="Original hash should be a 64-character SHA-256 hash"
                ))
        
        return errors
    
    def _cleanup_evidence_files(self, evidence_id: str) -> None:
        """Clean up evidence files after deletion."""
        # Remove evidence file and digest
        evidence_file = self.evidence_dir / f"{evidence_id}.enc"
        digest_file = self.evidence_dir / f"{evidence_id}.hmac"
        
        for file_path in [evidence_file, digest_file]:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass  # Continue cleanup even if some files fail
    
    def store(
        self, 
        file_path: str, 
        title: str,
        description: str,
        evidence_type: Union[str, EvidenceType],
        uploaded_by: str,
        access_level: Union[str, AccessLevel] = AccessLevel.RESTRICTED,
        authorized_users: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        related_finding_ids: Optional[List[str]] = None
    ) -> Evidence:
        """
        Store evidence securely with encryption and metadata.
        
        Args:
            file_path: Path to the evidence file to store
            title: Title of the evidence
            description: Description of the evidence
            evidence_type: Type of evidence (e.g., screenshot, log)
            uploaded_by: ID of the user uploading the evidence
            access_level: Access level for the evidence
            authorized_users: List of users authorized to access the evidence
            tags: List of tags for the evidence
            related_finding_ids: List of related findings
            
        Returns:
            Evidence object with metadata
            
        Raises:
            FileNotFoundError: If the file does not exist
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Validate file size
        validate_file_size(file_path, self.max_file_size_mb)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # Determine content type (simplified)
        content_type = self._guess_content_type(file_name)
        
        # Generate ID for the evidence
        evidence_id = str(uuid.uuid4())
        
        # Hash the original file
        hash_original = self._hash_file(file_path)
        
        # Create encrypted storage path
        encrypted_path = self.evidence_dir / f"{evidence_id}.enc"
        
        # Encrypt the file
        with open(file_path, "rb") as f:
            file_data = f.read()
            
        encrypted_data, digest = self.crypto_manager.encrypt(file_data)
        
        # Store encrypted file
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)
            
        # Store HMAC digest separately
        digest_path = self.evidence_dir / f"{evidence_id}.hmac"
        with open(digest_path, "wb") as f:
            f.write(digest)
            
        # Hash the encrypted file
        hash_encrypted = hashlib.sha256(encrypted_data).hexdigest()
        
        # Create evidence metadata
        evidence = Evidence(
            id=evidence_id,
            title=title,
            description=description,
            type=evidence_type,
            file_path=str(encrypted_path),
            original_filename=file_name,
            content_type=content_type,
            hash_original=hash_original,
            hash_encrypted=hash_encrypted,
            size_bytes=file_size,
            uploaded_by=uploaded_by,
            access_level=access_level,
            authorized_users=authorized_users or [],
            related_finding_ids=related_finding_ids or [],
            encryption_info={
                "algorithm": "AES-256-GCM",
                "key_id": self.crypto_manager.hash_data(self.crypto_manager.key)[:8]
            }
        )
        
        # Add tags if provided
        if tags:
            for tag in tags:
                evidence.add_tag(tag)
        
        # Save using base service
        evidence_id = self.create_with_validation(evidence)
        
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Evidence storage took {execution_time*1000:.2f}ms")
            
        return evidence
    
    def get_metadata(self, evidence_id: str, user_id: Optional[str] = None) -> Evidence:
        """
        Retrieve evidence metadata by ID, checking access if user_id is provided.
        
        Args:
            evidence_id: ID of the evidence
            user_id: Optional ID of the user retrieving the metadata
            
        Returns:
            Evidence object with metadata
            
        Raises:
            FileNotFoundError: If the evidence does not exist
            PermissionError: If the user does not have access
        """
        evidence = self.get(evidence_id)
        
        if evidence is None:
            raise FileNotFoundError(f"Evidence not found: {evidence_id}")
        
        # Check access if user_id is provided
        if user_id and not evidence.is_accessible_by(user_id):
            raise PermissionError(f"User {user_id} does not have access to evidence {evidence_id}")
            
        return evidence
    
    def retrieve(self, evidence_id: str, output_path: str, user_id: Optional[str] = None) -> Evidence:
        """
        Retrieve and decrypt evidence, writing to output_path.
        
        Args:
            evidence_id: ID of the evidence to retrieve
            output_path: Path where decrypted evidence will be written
            user_id: Optional ID of the user retrieving the evidence
            
        Returns:
            Evidence metadata
            
        Raises:
            FileNotFoundError: If the evidence does not exist
            PermissionError: If the user does not have access
            ValueError: If integrity verification fails
        """
        start_time = time.time()
        
        # Get metadata (will check access if user_id is provided)
        evidence = self.get_metadata(evidence_id, user_id)
        
        # Load encrypted evidence
        encrypted_path = Path(evidence.file_path)
        
        if not encrypted_path.exists():
            raise FileNotFoundError(f"Evidence file not found: {encrypted_path}")
            
        # Load data and HMAC digest
        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()
            
        digest_path = self.evidence_dir / f"{evidence_id}.hmac"
        with open(digest_path, "rb") as f:
            digest = f.read()
            
        # Decrypt data
        try:
            decrypted_data = self.crypto_manager.decrypt(encrypted_data, digest)
        except ValueError as e:
            raise ValueError(f"Evidence integrity verification failed: {str(e)}")
            
        # Calculate hash of decrypted data to verify
        hash_decrypted = hashlib.sha256(decrypted_data).hexdigest()
        
        if hash_decrypted != evidence.hash_original:
            raise ValueError(
                "Evidence integrity check failed: hash of decrypted data does not match original hash"
            )
            
        # Write decrypted data to output path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(decrypted_data)
            
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Evidence retrieval took {execution_time*1000:.2f}ms")
            
        return evidence
    
    def update_metadata(self, evidence: Evidence) -> Evidence:
        """
        Update evidence metadata.
        
        Args:
            evidence: Evidence object with updated metadata
            
        Returns:
            Updated evidence
            
        Raises:
            FileNotFoundError: If the evidence does not exist
        """
        updated = self.update_with_validation(evidence)
        if updated is None:
            raise FileNotFoundError(f"Evidence not found: {evidence.id}")
        return updated
    
    def delete_evidence(self, evidence_id: str) -> bool:
        """
        Delete evidence and its metadata.
        
        Args:
            evidence_id: ID of the evidence to delete
            
        Returns:
            True if deleted, False if not found
        """
        return self.delete_with_hooks(evidence_id)
    
    def list_evidence(
        self, 
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "uploaded_date",
        reverse: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Evidence]:
        """
        List evidence with optional filtering and access control.
        
        Args:
            user_id: Optional ID of the user for access control
            filters: Optional filters as field-value pairs
            sort_by: Field to sort by
            reverse: Whether to sort in reverse order
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of evidence matching criteria and accessible to the user
        """
        # Get all evidence first
        storage_sort_by = f"-{sort_by}" if reverse else sort_by
        all_evidence = self.list(
            filters=filters,
            sort_by=storage_sort_by,
            limit=None,  # Get all first for access filtering
            offset=0
        )
        
        # Filter by access if user_id is provided
        if user_id:
            accessible_evidence = [
                evidence for evidence in all_evidence 
                if evidence.is_accessible_by(user_id)
            ]
        else:
            accessible_evidence = all_evidence
        
        # Apply pagination
        if offset > 0:
            accessible_evidence = accessible_evidence[offset:]
        
        if limit is not None and limit > 0:
            accessible_evidence = accessible_evidence[:limit]
        
        return accessible_evidence
    
    def count_evidence(
        self, 
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count evidence matching filters and accessible to the user.
        
        Args:
            user_id: Optional ID of the user for access control
            filters: Optional filters as field-value pairs
            
        Returns:
            Number of evidence items matching criteria
        """
        if not user_id and not filters:
            return self.count()
        
        # Get filtered evidence and count accessible ones
        evidence_list = self.list_evidence(
            user_id=user_id,
            filters=filters,
            limit=None,
            offset=0
        )
        
        return len(evidence_list)
    
    def verify_integrity(self, evidence_id: str) -> bool:
        """
        Verify the integrity of stored evidence.
        
        Args:
            evidence_id: ID of the evidence to verify
            
        Returns:
            True if integrity check passes
            
        Raises:
            FileNotFoundError: If the evidence does not exist
            ValueError: If integrity verification fails
        """
        # Get metadata
        evidence = self.get_metadata(evidence_id)
        
        # Load encrypted evidence
        encrypted_path = Path(evidence.file_path)
        
        if not encrypted_path.exists():
            raise FileNotFoundError(f"Evidence file not found: {encrypted_path}")
            
        # Verify hash of encrypted file
        hash_encrypted = self._hash_file(str(encrypted_path))
        
        if hash_encrypted != evidence.hash_encrypted:
            raise ValueError("Evidence integrity check failed: encrypted file hash mismatch")
            
        # Load data and HMAC digest
        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()
            
        digest_path = self.evidence_dir / f"{evidence_id}.hmac"
        
        if not digest_path.exists():
            raise FileNotFoundError(f"Evidence digest not found: {digest_path}")
            
        with open(digest_path, "rb") as f:
            digest = f.read()
            
        # Decrypt to verify HMAC
        try:
            decrypted_data = self.crypto_manager.decrypt(encrypted_data, digest)
        except ValueError as e:
            raise ValueError(f"Evidence integrity verification failed: {str(e)}")
            
        # Verify hash of decrypted data
        hash_decrypted = hashlib.sha256(decrypted_data).hexdigest()
        
        if hash_decrypted != evidence.hash_original:
            raise ValueError(
                "Evidence integrity check failed: hash of decrypted data does not match original hash"
            )
            
        return True
    
    def _hash_file(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of the hash
        """
        h = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
                
        return h.hexdigest()
    
    def _guess_content_type(self, filename: str) -> str:
        """
        Guess the content type from a filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Guessed content type
        """
        extension = os.path.splitext(filename)[1].lower()
        
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".log": "text/plain",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".html": "text/html",
            ".xml": "application/xml",
            ".json": "application/json",
            ".pcap": "application/vnd.tcpdump.pcap",
            ".sql": "application/sql"
        }
        
        return content_types.get(extension, "application/octet-stream")
    
    # Legacy compatibility methods
    def delete(self, evidence_id: str) -> bool:
        """Legacy compatibility method."""
        return self.delete_evidence(evidence_id)
    
    def list(self, *args, **kwargs) -> List[Evidence]:
        """Legacy compatibility method."""
        # Handle reverse parameter by converting to sort_by prefix
        if 'reverse' in kwargs:
            reverse = kwargs.pop('reverse')
            if 'sort_by' in kwargs and reverse:
                sort_by = kwargs['sort_by']
                if not sort_by.startswith('-'):
                    kwargs['sort_by'] = f"-{sort_by}"
        
        # Call the storage directly to avoid recursion
        return self.storage.list(*args, **kwargs)
    
    def count(self, *args, **kwargs) -> int:
        """Legacy compatibility method."""
        # Call the storage directly to avoid recursion
        return self.storage.count(*args, **kwargs)