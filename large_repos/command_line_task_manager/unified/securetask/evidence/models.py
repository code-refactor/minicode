"""Data models for evidence storage."""

import uuid
import os
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union, Set
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from common.core import BaseEntity, TaggedMixin, ValidationError
from securetask.utils.validation import ValidationError as SecureValidationError, validate_file_size


class EvidenceType(str, Enum):
    """Types of evidence that can be stored."""
    
    SCREENSHOT = "screenshot"
    LOG = "log"
    CODE = "code"
    NETWORK_CAPTURE = "network_capture"
    DATABASE_DUMP = "database_dump"
    CONFIG = "config"
    EXPLOIT = "exploit"
    DOCUMENT = "document"
    OTHER = "other"


class AccessLevel(str, Enum):
    """Access levels for evidence."""
    
    PUBLIC = "public"  # Available to all team members
    RESTRICTED = "restricted"  # Available to specified team members
    CONFIDENTIAL = "confidential"  # Available only to authorized personnel
    TOP_SECRET = "top_secret"  # Available only to specified individuals


@dataclass
class Evidence(BaseEntity, TaggedMixin):
    """
    Model representing stored evidence for security findings.
    
    Holds metadata about evidence files, including origin, access controls,
    and cryptographic verification information.
    """
    
    title: str = ""
    description: str = ""
    type: EvidenceType = EvidenceType.OTHER
    file_path: str = ""  # Path to the encrypted evidence file
    original_filename: str = ""
    content_type: str = ""
    hash_original: str = ""  # SHA-256 hash of original content
    hash_encrypted: str = ""  # SHA-256 hash of encrypted content
    size_bytes: int = 0
    uploaded_date: datetime = field(default_factory=datetime.now)
    uploaded_by: str = ""
    access_level: AccessLevel = AccessLevel.RESTRICTED
    authorized_users: List[str] = field(default_factory=list)
    related_finding_ids: List[str] = field(default_factory=list)
    encryption_info: Dict[str, Any] = field(default_factory=dict)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize mixins and validate fields."""
        TaggedMixin.__init__(self)
        
        # Convert string types to enums if needed
        if isinstance(self.type, str):
            self.type = self.validate_type(self.type)
        if isinstance(self.access_level, str):
            self.access_level = self.validate_access_level(self.access_level)
    
    def validate_type(self, value):
        """Validate the evidence type."""
        if isinstance(value, EvidenceType):
            return value
            
        if isinstance(value, str) and value in [v.value for v in EvidenceType]:
            return EvidenceType(value)
            
        raise SecureValidationError(
            f"Invalid evidence type: {value}. Must be one of: {', '.join([v.value for v in EvidenceType])}",
            "type"
        )
    
    def validate_access_level(self, value):
        """Validate the access level."""
        if isinstance(value, AccessLevel):
            return value
            
        if isinstance(value, str) and value in [v.value for v in AccessLevel]:
            return AccessLevel(value)
            
        raise SecureValidationError(
            f"Invalid access level: {value}. Must be one of: {', '.join([v.value for v in AccessLevel])}",
            "access_level"
        )
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        # Validate required fields
        if not self.title:
            errors.append(ValidationError(field="title", message="Title is required"))
        if not self.description:
            errors.append(ValidationError(field="description", message="Description is required"))
        if not self.original_filename:
            errors.append(ValidationError(field="original_filename", message="Original filename is required"))
        if not self.uploaded_by:
            errors.append(ValidationError(field="uploaded_by", message="Uploaded by is required"))
        
        # Validate type
        try:
            self.validate_type(self.type)
        except SecureValidationError as e:
            errors.append(ValidationError(field="type", message=str(e)))
        
        # Validate access level
        try:
            self.validate_access_level(self.access_level)
        except SecureValidationError as e:
            errors.append(ValidationError(field="access_level", message=str(e)))
        
        return errors
    
    def add_related_finding(self, finding_id: str) -> None:
        """
        Associate evidence with a finding.
        
        Args:
            finding_id: ID of the finding to associate
        """
        if finding_id not in self.related_finding_ids:
            self.related_finding_ids.append(finding_id)
    
    def add_note(self, content: str, author: str) -> Dict[str, Any]:
        """
        Add a timestamped note to the evidence.
        
        Args:
            content: The note content
            author: The author of the note
            
        Returns:
            The created note as a dictionary
        """
        note = {
            "id": str(uuid.uuid4()),
            "content": content,
            "author": author,
            "timestamp": datetime.now()
        }
        self.notes.append(note)
        return note
    
    def is_accessible_by(self, user_id: str) -> bool:
        """
        Check if a user has access to this evidence.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            True if the user has access, False otherwise
        """
        if self.access_level == AccessLevel.PUBLIC:
            return True
            
        if user_id == self.uploaded_by:
            return True
            
        if user_id in self.authorized_users:
            return True
            
        # Confidential and top_secret require explicit authorization
        if self.access_level in [AccessLevel.CONFIDENTIAL, AccessLevel.TOP_SECRET]:
            return False
            
        # For restricted, we could implement custom logic here
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add Evidence-specific fields
        data.update({
            'title': self.title,
            'description': self.description,
            'type': self.type.value if isinstance(self.type, EvidenceType) else self.type,
            'file_path': self.file_path,
            'original_filename': self.original_filename,
            'content_type': self.content_type,
            'hash_original': self.hash_original,
            'hash_encrypted': self.hash_encrypted,
            'size_bytes': self.size_bytes,
            'uploaded_date': self.uploaded_date.isoformat() if isinstance(self.uploaded_date, datetime) else self.uploaded_date,
            'uploaded_by': self.uploaded_by,
            'access_level': self.access_level.value if isinstance(self.access_level, AccessLevel) else self.access_level,
            'authorized_users': self.authorized_users,
            'related_finding_ids': self.related_finding_ids,
            'encryption_info': self.encryption_info,
            'notes': self.notes,
            'tags': list(self.tags) if hasattr(self, 'tags') else []
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Evidence':
        """Create evidence from dictionary representation."""
        # Parse datetime fields
        if 'uploaded_date' in data and isinstance(data['uploaded_date'], str):
            data['uploaded_date'] = datetime.fromisoformat(data['uploaded_date'])
        
        # Convert enum fields from strings if needed
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = EvidenceType(data['type'])
        if 'access_level' in data and isinstance(data['access_level'], str):
            data['access_level'] = AccessLevel(data['access_level'])
        
        # Create instance
        evidence = cls(
            title=data.get('title', ''),
            description=data.get('description', ''),
            type=data.get('type', EvidenceType.OTHER),
            file_path=data.get('file_path', ''),
            original_filename=data.get('original_filename', ''),
            content_type=data.get('content_type', ''),
            hash_original=data.get('hash_original', ''),
            hash_encrypted=data.get('hash_encrypted', ''),
            size_bytes=data.get('size_bytes', 0),
            uploaded_date=data.get('uploaded_date', datetime.now()),
            uploaded_by=data.get('uploaded_by', ''),
            access_level=data.get('access_level', AccessLevel.RESTRICTED),
            authorized_users=data.get('authorized_users', []),
            related_finding_ids=data.get('related_finding_ids', []),
            encryption_info=data.get('encryption_info', {}),
            notes=data.get('notes', [])
        )
        
        # Set ID if provided
        if 'id' in data:
            evidence.id = data['id']
        
        # Set tags if provided
        if 'tags' in data and hasattr(evidence, 'tags'):
            evidence.tags = set(data['tags'])
        
        return evidence