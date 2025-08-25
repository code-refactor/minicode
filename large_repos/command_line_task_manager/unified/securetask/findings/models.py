"""Data models for security findings."""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator, model_validator

from common.core import BaseEntity, StatusMixin, TaggedMixin, ValidationError, TimestampedMixin
from securetask.utils.validation import ValidationError as SecureValidationError


@dataclass
class Finding(BaseEntity, StatusMixin, TaggedMixin):
    """
    Model representing a security finding or vulnerability.
    
    Contains comprehensive metadata about security issues, including
    technical details, affected systems, and tracking information.
    """
    
    title: str = ""
    description: str = ""
    affected_systems: List[str] = field(default_factory=list)
    discovered_date: datetime = field(default_factory=datetime.now)
    discovered_by: str = ""
    severity: str = ""  # critical, high, medium, low, info
    cvss_vector: Optional[str] = None
    cvss_score: Optional[float] = None
    cvss_severity: Optional[str] = None
    remediation_plan: Optional[str] = None
    remediation_date: Optional[datetime] = None
    remediated_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    verified_by: Optional[str] = None
    references: List[str] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    compliance_controls: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize mixins and set up status transitions."""
        StatusMixin.__init__(self)
        TaggedMixin.__init__(self)
        
        # Set initial status
        self.status = "open"
        
        # Define valid status transitions
        self.valid_transitions = {
            "open": ["in_progress", "closed", "false_positive"],
            "in_progress": ["remediated", "open", "closed"],
            "remediated": ["verified", "open"],
            "verified": ["closed"],
            "closed": ["open"],
            "false_positive": ["open"]
        }
    
    def validate_status(self, value: str) -> str:
        """Validate that the status is a known value."""
        allowed_statuses = {
            "open", "in_progress", "remediated", "verified", "closed", "false_positive"
        }
        if value not in allowed_statuses:
            raise SecureValidationError(
                f"Invalid status: {value}. Allowed values: {', '.join(allowed_statuses)}", 
                "status"
            )
        return value
    
    def validate_severity(self, value: str) -> str:
        """Validate that the severity is a known value."""
        allowed_severities = {"critical", "high", "medium", "low", "info"}
        if value not in allowed_severities:
            raise SecureValidationError(
                f"Invalid severity: {value}. Allowed values: {', '.join(allowed_severities)}", 
                "severity"
            )
        return value
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        # Validate required fields
        if not self.title:
            errors.append(ValidationError(field="title", message="Title is required"))
        if not self.description:
            errors.append(ValidationError(field="description", message="Description is required"))
        if not self.discovered_by:
            errors.append(ValidationError(field="discovered_by", message="Discovered by is required"))
        if not self.severity:
            errors.append(ValidationError(field="severity", message="Severity is required"))
        
        # Validate status
        try:
            self.validate_status(self.status)
        except SecureValidationError as e:
            errors.append(ValidationError(field="status", message=str(e)))
        
        # Validate severity
        try:
            self.validate_severity(self.severity)
        except SecureValidationError as e:
            errors.append(ValidationError(field="severity", message=str(e)))
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add Finding-specific fields
        data.update({
            'title': self.title,
            'description': self.description,
            'affected_systems': self.affected_systems,
            'discovered_date': self.discovered_date.isoformat() if isinstance(self.discovered_date, datetime) else self.discovered_date,
            'discovered_by': self.discovered_by,
            'severity': self.severity,
            'cvss_vector': self.cvss_vector,
            'cvss_score': self.cvss_score,
            'cvss_severity': self.cvss_severity,
            'remediation_plan': self.remediation_plan,
            'remediation_date': self.remediation_date.isoformat() if self.remediation_date and isinstance(self.remediation_date, datetime) else self.remediation_date,
            'remediated_by': self.remediated_by,
            'verification_date': self.verification_date.isoformat() if self.verification_date and isinstance(self.verification_date, datetime) else self.verification_date,
            'verified_by': self.verified_by,
            'references': self.references,
            'notes': self.notes,
            'evidence_ids': self.evidence_ids,
            'compliance_controls': self.compliance_controls,
            'status': self.status,
            'tags': list(self.tags) if hasattr(self, 'tags') else []
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Finding':
        """Create finding from dictionary representation."""
        # Parse datetime fields
        if 'discovered_date' in data and isinstance(data['discovered_date'], str):
            data['discovered_date'] = datetime.fromisoformat(data['discovered_date'])
        if 'remediation_date' in data and isinstance(data['remediation_date'], str):
            data['remediation_date'] = datetime.fromisoformat(data['remediation_date'])
        if 'verification_date' in data and isinstance(data['verification_date'], str):
            data['verification_date'] = datetime.fromisoformat(data['verification_date'])
        
        # Create instance without calling parent from_dict (to avoid recursion)
        finding = cls(
            title=data.get('title', ''),
            description=data.get('description', ''),
            affected_systems=data.get('affected_systems', []),
            discovered_date=data.get('discovered_date', datetime.now()),
            discovered_by=data.get('discovered_by', ''),
            severity=data.get('severity', ''),
            cvss_vector=data.get('cvss_vector'),
            cvss_score=data.get('cvss_score'),
            cvss_severity=data.get('cvss_severity'),
            remediation_plan=data.get('remediation_plan'),
            remediation_date=data.get('remediation_date'),
            remediated_by=data.get('remediated_by'),
            verification_date=data.get('verification_date'),
            verified_by=data.get('verified_by'),
            references=data.get('references', []),
            notes=data.get('notes', []),
            evidence_ids=data.get('evidence_ids', []),
            compliance_controls=data.get('compliance_controls', [])
        )
        
        # Set ID if provided
        if 'id' in data:
            finding.id = data['id']
        
        # Set status if provided
        if 'status' in data:
            finding.status = data['status']
        
        # Set tags if provided
        if 'tags' in data and hasattr(finding, 'tags'):
            finding.tags = set(data['tags'])
        
        return finding
    
    def add_note(self, content: str, author: str) -> Dict[str, Any]:
        """
        Add a timestamped note to the finding.
        
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
    
    def add_evidence(self, evidence_id: str) -> None:
        """
        Link evidence to the finding.
        
        Args:
            evidence_id: ID of the evidence to link
        """
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            
    def remove_evidence(self, evidence_id: str) -> bool:
        """
        Remove linked evidence from the finding.
        
        Args:
            evidence_id: ID of the evidence to remove
            
        Returns:
            True if evidence was removed, False if not found
        """
        if evidence_id in self.evidence_ids:
            self.evidence_ids.remove(evidence_id)
            return True
        return False
            
    def add_compliance_control(self, control_id: str) -> None:
        """
        Link a compliance control to the finding.
        
        Args:
            control_id: ID of the compliance control to link
        """
        if control_id not in self.compliance_controls:
            self.compliance_controls.append(control_id)
    
    def remove_compliance_control(self, control_id: str) -> bool:
        """
        Remove a linked compliance control from the finding.
        
        Args:
            control_id: ID of the compliance control to remove
            
        Returns:
            True if control was removed, False if not found
        """
        if control_id in self.compliance_controls:
            self.compliance_controls.remove(control_id)
            return True
        return False
    
    def update_cvss(self, vector: str, score: float, severity: str) -> None:
        """
        Update the CVSS information for this finding.
        
        Args:
            vector: CVSS vector string
            score: Calculated CVSS score
            severity: CVSS severity rating
        """
        self.cvss_vector = vector
        self.cvss_score = score
        self.cvss_severity = severity
        
    def update_status(self, new_status: str, user: str) -> bool:
        """
        Update the status of the finding using status transition system.
        
        Args:
            new_status: New status value
            user: User making the status change
            
        Returns:
            True if status was updated successfully
        
        Raises:
            ValidationError: If the status transition is invalid
        """
        # Use StatusMixin's transition_to method
        if not self.transition_to(new_status, f"Status changed by {user}"):
            raise SecureValidationError(
                f"Invalid status transition from '{self.status}' to '{new_status}'",
                "status"
            )
        
        # Update related fields
        if new_status == "remediated":
            self.remediation_date = datetime.now()
            self.remediated_by = user
        elif new_status == "verified":
            self.verification_date = datetime.now()
            self.verified_by = user
            
        # Add a note about the status change
        self.add_note(f"Status changed to '{new_status}'", user)
        return True