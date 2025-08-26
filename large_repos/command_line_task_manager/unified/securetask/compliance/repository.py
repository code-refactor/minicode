"""Repository for storing and retrieving compliance frameworks."""

import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Tuple

from pydantic import ValidationError as PydanticValidationError

from common.core import BaseService, FileStorage, StorageInterface, ValidationError
from securetask.compliance.frameworks import (
    ComplianceControl, ComplianceFramework, ComplianceControlStatus, ComplianceMapping
)
from securetask.utils.crypto import CryptoManager
from securetask.utils.validation import ValidationError as SecureValidationError


class EncryptedComplianceStorage(StorageInterface[ComplianceFramework]):
    """Encrypted file storage for compliance frameworks with individual files per framework."""
    
    def __init__(self, storage_dir: Path, crypto_manager: Optional[CryptoManager] = None):
        """Initialize encrypted storage."""
        self.storage_dir = Path(storage_dir)
        self.frameworks_dir = self.storage_dir / "frameworks"
        self.frameworks_dir.mkdir(parents=True, exist_ok=True)
        self.crypto_manager = crypto_manager or CryptoManager()
        self._cache: Dict[str, ComplianceFramework] = {}
    
    def _get_file_paths(self, framework_id: str) -> tuple[Path, Path]:
        """Get encrypted file and HMAC digest paths for a framework."""
        framework_id_str = str(framework_id) if isinstance(framework_id, uuid.UUID) else framework_id
        enc_path = self.frameworks_dir / f"{framework_id_str}.json.enc"
        hmac_path = self.frameworks_dir / f"{framework_id_str}.hmac"
        return enc_path, hmac_path
    
    def create(self, entity: ComplianceFramework) -> str:
        """Create a new framework."""
        framework_id = str(entity.id) if hasattr(entity, 'id') else str(uuid.uuid4())
        
        # Serialize to JSON
        framework_dict = entity.to_dict()
        json_data = json.dumps(framework_dict, default=str).encode()
        
        # Encrypt
        encrypted_data, digest = self.crypto_manager.encrypt(json_data)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(framework_id)
        
        # Save encrypted data
        with open(enc_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Save HMAC digest
        with open(hmac_path, 'wb') as f:
            f.write(digest)
        
        # Cache the framework
        self._cache[framework_id] = entity
        
        return framework_id
    
    def get(self, entity_id: Union[str, uuid.UUID]) -> Optional[ComplianceFramework]:
        """Get a framework by ID."""
        framework_id = str(entity_id)
        
        # Check cache first
        if framework_id in self._cache:
            return self._cache[framework_id]
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(framework_id)
        
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
        framework_dict = json.loads(decrypted_data.decode())
        
        # Create ComplianceFramework instance
        framework = ComplianceFramework.from_dict(framework_dict)
        
        # Cache it
        self._cache[framework_id] = framework
        
        return framework
    
    def update(self, entity: ComplianceFramework) -> Optional[ComplianceFramework]:
        """Update an existing framework."""
        framework_id = str(entity.id)
        
        # Check if exists
        enc_path, hmac_path = self._get_file_paths(framework_id)
        if not enc_path.exists():
            return None
        
        # Update timestamp
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.now()
        
        # Save updated framework
        self.create(entity)
        
        return entity
    
    def delete(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Delete a framework."""
        framework_id = str(entity_id)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(framework_id)
        
        # Delete files
        deleted = False
        if enc_path.exists():
            enc_path.unlink()
            deleted = True
        if hmac_path.exists():
            hmac_path.unlink()
        
        # Remove from cache
        if framework_id in self._cache:
            del self._cache[framework_id]
        
        return deleted
    
    def list(self, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None,
             limit: Optional[int] = None, offset: int = 0) -> List[ComplianceFramework]:
        """List all frameworks."""
        frameworks = []
        
        # Load all frameworks from disk
        for enc_file in self.frameworks_dir.glob("*.json.enc"):
            framework_id = enc_file.stem.replace('.json', '')
            framework = self.get(framework_id)
            if framework:
                frameworks.append(framework)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                filtered = []
                for f in frameworks:
                    field_value = getattr(f, key, None)
                    # Handle set membership check
                    if isinstance(field_value, set):
                        if value in field_value:
                            filtered.append(f)
                    # Simple equality check for other types
                    elif field_value == value:
                        filtered.append(f)
                frameworks = filtered
        
        # Sort if requested
        if sort_by:
            reverse = sort_by.startswith('-')
            key = sort_by[1:] if reverse else sort_by
            frameworks.sort(key=lambda x: getattr(x, key, ''), reverse=reverse)
        
        # Apply pagination
        if offset:
            frameworks = frameworks[offset:]
        if limit:
            frameworks = frameworks[:limit]
        
        return frameworks
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count frameworks."""
        return len(self.list(filters=filters))
    
    def clear(self) -> None:
        """Clear all frameworks."""
        for enc_file in self.frameworks_dir.glob("*.json.enc"):
            enc_file.unlink()
        for hmac_file in self.frameworks_dir.glob("*.hmac"):
            hmac_file.unlink()
        self._cache.clear()
    
    def exists(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Check if a framework exists."""
        framework_id = str(entity_id)
        enc_path, _ = self._get_file_paths(framework_id)
        return enc_path.exists()


class ComplianceRepository(BaseService[ComplianceFramework]):
    """
    Service for managing compliance frameworks.
    
    Provides storage, retrieval, and management of compliance frameworks,
    controls, and their mappings to security findings.
    """
    
    def __init__(self, storage_dir: str, crypto_manager: Optional[CryptoManager] = None):
        """
        Initialize the compliance repository.
        
        Args:
            storage_dir: Directory where compliance data will be stored
            crypto_manager: Optional crypto manager for encryption
        """
        # Create encrypted storage with individual files
        storage = EncryptedComplianceStorage(Path(storage_dir), crypto_manager)
        
        # Initialize base service
        super().__init__(storage)
        
        # Add custom validators
        self.add_validator(self._validate_framework_business_rules)
        
        # Initialize compliance mapping
        self.mapping = ComplianceMapping()
        
        # Load existing frameworks into mapping
        self._load_frameworks_into_mapping()
    
    def _validate_framework_business_rules(self, framework: ComplianceFramework) -> List[ValidationError]:
        """Custom business rule validation for frameworks."""
        errors = []
        
        # Validate control IDs are unique within framework
        control_ids = [c.id for c in framework.controls]
        if len(control_ids) != len(set(control_ids)):
            errors.append(ValidationError(
                field="controls",
                message="Duplicate control IDs found in framework"
            ))
        
        # Validate parent-child relationships
        for control in framework.controls:
            if control.parent_id:
                parent_found = any(c.id == control.parent_id for c in framework.controls)
                if not parent_found:
                    errors.append(ValidationError(
                        field="controls",
                        message=f"Parent control {control.parent_id} not found for control {control.id}"
                    ))
        
        return errors
    
    def _load_frameworks_into_mapping(self) -> None:
        """Load all frameworks from storage into memory mapping."""
        try:
            all_frameworks = self.list()
            for framework in all_frameworks:
                self.mapping.add_framework(framework)
        except Exception:
            # Continue if loading fails
            pass
    
    def create_framework(
        self,
        id: str,
        name: str,
        description: str,
        version: str,
        references: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None
    ) -> ComplianceFramework:
        """
        Create a new compliance framework.
        
        Args:
            id: Identifier for the framework
            name: Name of the framework
            description: Description of the framework
            version: Version of the framework
            references: Optional list of references
            tags: Optional list of tags
            
        Returns:
            The created framework
            
        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        try:
            # Create the framework
            framework = ComplianceFramework(
                id=id,
                name=name,
                description=description,
                version=version,
                references=references or []
            )
            
            # Add tags if provided
            if tags:
                for tag in tags:
                    framework.add_tag(tag)
            
            # Save using base service
            framework_id = self.create_with_validation(framework)
            
            # Add to mapping
            self.mapping.add_framework(framework)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Framework creation took {execution_time*1000:.2f}ms")
                
            return framework
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def get_framework(self, framework_id: str) -> ComplianceFramework:
        """
        Retrieve a compliance framework by ID.
        
        Args:
            framework_id: ID of the framework to retrieve
            
        Returns:
            The retrieved framework
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        framework = self.get(framework_id)
        if framework is None:
            raise FileNotFoundError(f"Framework not found: {framework_id}")
        return framework
    
    def update_framework(self, framework: ComplianceFramework) -> ComplianceFramework:
        """
        Update an existing compliance framework.
        
        Args:
            framework: The framework to update
            
        Returns:
            The updated framework
            
        Raises:
            FileNotFoundError: If the framework does not exist
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        try:
            # Update using base service
            updated = self.update_with_validation(framework)
            if updated is None:
                raise FileNotFoundError(f"Framework not found: {framework.id}")
            
            # Update mapping
            self.mapping.add_framework(updated)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Framework update took {execution_time*1000:.2f}ms")
            
            return updated
            
        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def delete_framework(self, framework_id: str) -> bool:
        """
        Delete a compliance framework.
        
        Args:
            framework_id: ID of the framework to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from mapping first
        self.mapping.remove_framework(framework_id)
        
        # Delete from storage
        return self.delete_with_hooks(framework_id)
    
    def add_control(
        self,
        framework_id: str,
        id: str,
        name: str,
        description: str,
        section: str,
        parent_id: Optional[str] = None,
        guidance: Optional[str] = None,
        links: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None
    ) -> ComplianceControl:
        """
        Add a control to a framework.
        
        Args:
            framework_id: ID of the framework
            id: ID for the control
            name: Name of the control
            description: Description of the control
            section: Section identifier
            parent_id: Optional ID of parent control
            guidance: Optional implementation guidance
            links: Optional list of reference links
            tags: Optional list of tags
            
        Returns:
            The created control
            
        Raises:
            FileNotFoundError: If the framework does not exist
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        # Get the framework
        framework = self.get_framework(framework_id)
        
        try:
            # Create the control
            control = ComplianceControl(
                id=id,
                name=name,
                description=description,
                section=section,
                parent_id=parent_id,
                guidance=guidance,
                links=links or []
            )
            
            # Add tags if provided
            if tags:
                for tag in tags:
                    control.add_tag(tag)
            
            # Add to framework
            framework.add_control(control)
            
            # Update the framework
            self.update_framework(framework)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Control addition took {execution_time*1000:.2f}ms")
                
            return control
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def get_control(self, framework_id: str, control_id: str) -> Optional[ComplianceControl]:
        """
        Get a control from a framework.
        
        Args:
            framework_id: ID of the framework
            control_id: ID of the control
            
        Returns:
            The control or None if not found
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        # Get the framework
        framework = self.get_framework(framework_id)
        
        # Get the control
        return framework.get_control(control_id)
    
    def update_control(
        self,
        framework_id: str,
        control: ComplianceControl
    ) -> ComplianceControl:
        """
        Update a control in a framework.
        
        Args:
            framework_id: ID of the framework
            control: The control to update
            
        Returns:
            The updated control
            
        Raises:
            FileNotFoundError: If the framework or control does not exist
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        # Get the framework
        framework = self.get_framework(framework_id)
        
        # Check if control exists
        existing_control = framework.get_control(control.id)
        if not existing_control:
            raise FileNotFoundError(f"Control not found: {control.id}")
        
        try:
            # Update control in framework
            framework.add_control(control)
            
            # Update the framework
            self.update_framework(framework)
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Control update took {execution_time*1000:.2f}ms")
                
            return control
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def remove_control(self, framework_id: str, control_id: str) -> bool:
        """
        Remove a control from a framework.
        
        Args:
            framework_id: ID of the framework
            control_id: ID of the control
            
        Returns:
            True if removed, False if not found
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        # Get the framework
        framework = self.get_framework(framework_id)
        
        # Remove the control
        if not framework.remove_control(control_id):
            return False
            
        # Update the framework
        self.update_framework(framework)
        
        return True
    
    def list_frameworks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "name",
        reverse: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ComplianceFramework]:
        """
        List compliance frameworks.
        
        Args:
            filters: Optional filters as field-value pairs
            sort_by: Field to sort by
            reverse: Whether to sort in reverse order
            limit: Maximum number of frameworks to return
            offset: Number of frameworks to skip
            
        Returns:
            List of frameworks matching criteria
        """
        # Convert sort direction to storage format
        storage_sort_by = f"-{sort_by}" if reverse else sort_by
        
        return super().list(
            filters=filters,
            sort_by=storage_sort_by,
            limit=limit,
            offset=offset
        )
    
    def count_frameworks(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count frameworks matching filters.
        
        Args:
            filters: Optional filters as field-value pairs
            
        Returns:
            Number of frameworks matching criteria
        """
        return super().count(filters)
    
    def map_finding_to_control(
        self, 
        finding_id: str, 
        framework_id: str, 
        control_id: str
    ) -> bool:
        """
        Map a finding to a control.
        
        Args:
            finding_id: ID of the finding
            framework_id: ID of the framework
            control_id: ID of the control
            
        Returns:
            True if mapping successful, False if control not found
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        start_time = time.time()
        
        # Check if mapping exists in memory
        if not self.mapping.map_finding_to_control(finding_id, framework_id, control_id):
            return False
            
        # Get updated framework from mapping
        framework = self.mapping.get_framework(framework_id)
        if not framework:
            return False
            
        # Update the framework in storage
        self.update_framework(framework)
        
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Mapping creation took {execution_time*1000:.2f}ms")
            
        return True
    
    def unmap_finding_from_control(
        self, 
        finding_id: str, 
        framework_id: str, 
        control_id: str
    ) -> bool:
        """
        Remove a mapping between a finding and a control.
        
        Args:
            finding_id: ID of the finding
            framework_id: ID of the framework
            control_id: ID of the control
            
        Returns:
            True if mapping removed, False if mapping or control not found
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        start_time = time.time()
        
        # Remove mapping in memory
        if not self.mapping.unmap_finding_from_control(finding_id, framework_id, control_id):
            return False
            
        # Get updated framework from mapping
        framework = self.mapping.get_framework(framework_id)
        if not framework:
            return False
            
        # Update the framework in storage
        self.update_framework(framework)
        
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Mapping removal took {execution_time*1000:.2f}ms")
            
        return True
    
    def get_controls_for_finding(self, finding_id: str) -> Dict[str, List[ComplianceControl]]:
        """
        Get all controls mapped to a finding, grouped by framework.

        Args:
            finding_id: ID of the finding

        Returns:
            Dictionary mapping framework IDs to lists of controls
        """
        return self.mapping.get_controls_for_finding(finding_id)
    
    def get_findings_for_control(
        self, 
        framework_id: str, 
        control_id: str
    ) -> List[str]:
        """
        Get all findings mapped to a control.
        
        Args:
            framework_id: ID of the framework
            control_id: ID of the control
            
        Returns:
            List of finding IDs
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        # Check if framework exists
        if framework_id not in self.mapping.frameworks:
            raise FileNotFoundError(f"Framework not found: {framework_id}")
            
        return self.mapping.get_findings_for_control(framework_id, control_id)
    
    def update_control_status(
        self,
        framework_id: str,
        control_id: str,
        status: Union[ComplianceControlStatus, str],
        justification: Optional[str] = None
    ) -> bool:
        """
        Update the compliance status of a control.
        
        Args:
            framework_id: ID of the framework
            control_id: ID of the control
            status: New compliance status
            justification: Optional justification for the status
            
        Returns:
            True if status updated, False if control not found
            
        Raises:
            FileNotFoundError: If the framework does not exist
        """
        start_time = time.time()
        
        # Update status in memory
        if not self.mapping.update_control_status(framework_id, control_id, status, justification):
            return False
            
        # Get updated framework from mapping
        framework = self.mapping.get_framework(framework_id)
        if not framework:
            return False
            
        # Update the framework in storage
        self.update_framework(framework)
        
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Status update took {execution_time*1000:.2f}ms")
            
        return True
    
    def get_framework_compliance_status(self, framework_id: str) -> Optional[Dict[str, int]]:
        """
        Get the compliance status for a framework.
        
        Args:
            framework_id: ID of the framework
            
        Returns:
            Dictionary mapping status values to counts, or None if framework not found
        """
        return self.mapping.get_framework_compliance_status(framework_id)
    
    def get_overall_compliance_status(self) -> Dict[str, Dict[str, int]]:
        """
        Get the compliance status across all frameworks.
        
        Returns:
            Dictionary mapping framework IDs to status counts
        """
        return self.mapping.get_overall_compliance_status()
    
    def import_framework_from_dict(self, framework_dict: Dict[str, Any]) -> ComplianceFramework:
        """
        Import a framework from a dictionary.
        
        Args:
            framework_dict: Dictionary representation of a framework
            
        Returns:
            The imported framework
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Create the framework from dict
            framework = ComplianceFramework.from_dict(framework_dict)

            # Save using base service
            self.create_with_validation(framework)

            # Add to mapping
            self.mapping.add_framework(framework)
            
            return framework
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    # Legacy compatibility methods
    def create(self, *args, **kwargs) -> ComplianceFramework:
        """Legacy compatibility method."""
        return self.create_framework(*args, **kwargs)
    
    def get(self, framework_id: str) -> ComplianceFramework:
        """Legacy compatibility method."""
        # Call storage directly to avoid recursion
        framework = self.storage.get(framework_id)
        if framework is None:
            raise FileNotFoundError(f"Framework not found: {framework_id}")
        return framework
    
    def update(self, framework: ComplianceFramework) -> ComplianceFramework:
        """Legacy compatibility method."""
        return self.update_framework(framework)
    
    def delete(self, framework_id: str) -> bool:
        """Legacy compatibility method."""
        return self.delete_framework(framework_id)
    
    def list(self, *args, **kwargs) -> List[ComplianceFramework]:
        """Legacy compatibility method."""
        return self.list_frameworks(*args, **kwargs)
    
    def count(self, *args, **kwargs) -> int:
        """Legacy compatibility method."""
        return self.count_frameworks(*args, **kwargs)