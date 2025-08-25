"""Compliance framework models and definitions."""

import uuid
from enum import Enum
from typing import List, Dict, Optional, Any, Set, Union
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from common.core import BaseEntity, HierarchicalEntity, TaggedMixin, ValidationError
from securetask.utils.validation import ValidationError as SecureValidationError


class ComplianceControlStatus(str, Enum):
    """Status of a compliance control."""
    
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


@dataclass
class ComplianceControl(HierarchicalEntity, TaggedMixin):
    """Model representing a compliance control within a framework."""
    
    name: str = ""
    description: str = ""
    section: str = ""
    guidance: Optional[str] = None
    links: List[Dict[str, str]] = field(default_factory=list)
    finding_ids: List[str] = field(default_factory=list)
    status: ComplianceControlStatus = ComplianceControlStatus.UNKNOWN
    status_justification: Optional[str] = None
    
    def __post_init__(self):
        """Initialize mixins and validate fields."""
        # Call parent __post_init__ if it exists (for BaseEntity UUID handling)
        if hasattr(super(), '__post_init__'):
            super().__post_init__()
        TaggedMixin.__init__(self)
        
        # Convert string status to enum if needed
        if isinstance(self.status, str):
            self.status = self.validate_status(self.status)
    
    def validate_status(self, value):
        """Validate the control status."""
        if isinstance(value, ComplianceControlStatus):
            return value
            
        if isinstance(value, str) and value in [s.value for s in ComplianceControlStatus]:
            return ComplianceControlStatus(value)
            
        raise SecureValidationError(
            f"Invalid status: {value}. Allowed values: {', '.join([s.value for s in ComplianceControlStatus])}",
            "status"
        )
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        # Validate required fields
        if not self.name:
            errors.append(ValidationError(field="name", message="Name is required"))
        if not self.description:
            errors.append(ValidationError(field="description", message="Description is required"))
        if not self.section:
            errors.append(ValidationError(field="section", message="Section is required"))
        
        # Validate status
        try:
            self.validate_status(self.status)
        except SecureValidationError as e:
            errors.append(ValidationError(field="status", message=str(e)))
        
        return errors
    
    def add_finding(self, finding_id: str) -> None:
        """
        Associate a finding with this control.
        
        Args:
            finding_id: ID of the finding to associate
        """
        if finding_id not in self.finding_ids:
            self.finding_ids.append(finding_id)
    
    def remove_finding(self, finding_id: str) -> bool:
        """
        Remove a finding association from this control.
        
        Args:
            finding_id: ID of the finding to remove
            
        Returns:
            True if finding was removed, False if it wasn't associated
        """
        if finding_id in self.finding_ids:
            self.finding_ids.remove(finding_id)
            return True
        return False
    
    def update_status(self, status: Union[ComplianceControlStatus, str], justification: Optional[str] = None) -> None:
        """
        Update the compliance status of this control.
        
        Args:
            status: New compliance status
            justification: Optional justification for the status
        """
        # Validate and set status
        if isinstance(status, str):
            status = ComplianceControlStatus(status)
            
        self.status = status
        
        if justification:
            self.status_justification = justification
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert compliance control to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add ComplianceControl-specific fields
        data.update({
            'name': self.name,
            'description': self.description,
            'section': self.section,
            'guidance': self.guidance,
            'links': self.links,
            'finding_ids': self.finding_ids,
            'status': self.status.value if isinstance(self.status, ComplianceControlStatus) else self.status,
            'status_justification': self.status_justification,
            'tags': list(self.tags) if hasattr(self, 'tags') else []
        })
        
        # Add hierarchical fields if available
        if hasattr(self, 'parent_id'):
            data['parent_id'] = self.parent_id
        if hasattr(self, 'children_ids'):
            data['children_ids'] = self.children_ids
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceControl':
        """Create compliance control from dictionary representation."""
        # Convert enum fields from strings if needed
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ComplianceControlStatus(data['status'])
        
        # Create instance
        control = cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            section=data.get('section', ''),
            guidance=data.get('guidance'),
            links=data.get('links', []),
            finding_ids=data.get('finding_ids', []),
            status=data.get('status', ComplianceControlStatus.UNKNOWN),
            status_justification=data.get('status_justification')
        )
        
        # Set ID if provided
        if 'id' in data:
            control.id = data['id']
        
        # Set hierarchical fields if provided
        if 'parent_id' in data:
            control.parent_id = data['parent_id']
        if 'children_ids' in data:
            control.children_ids = data['children_ids']
        
        # Set tags if provided
        if 'tags' in data and hasattr(control, 'tags'):
            control.tags = set(data['tags'])
        
        return control


@dataclass
class ComplianceFramework(BaseEntity, TaggedMixin):
    """Model representing a compliance framework with controls."""
    
    name: str = ""
    description: str = ""
    version: str = ""
    controls: List[ComplianceControl] = field(default_factory=list)
    references: List[Dict[str, str]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize mixins."""
        # Call parent __post_init__ if it exists (for BaseEntity UUID handling)
        if hasattr(super(), '__post_init__'):
            super().__post_init__()
        TaggedMixin.__init__(self)
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        # Validate required fields
        if not self.name:
            errors.append(ValidationError(field="name", message="Name is required"))
        if not self.description:
            errors.append(ValidationError(field="description", message="Description is required"))
        if not self.version:
            errors.append(ValidationError(field="version", message="Version is required"))
        
        return errors
    
    def add_control(self, control: ComplianceControl) -> None:
        """
        Add a control to the framework.
        
        Args:
            control: The control to add
        """
        # Check if control already exists
        for i, existing in enumerate(self.controls):
            if existing.id == control.id:
                # Replace the existing control
                self.controls[i] = control
                return
                
        # Add the new control
        self.controls.append(control)
    
    def get_control(self, control_id: str) -> Optional[ComplianceControl]:
        """
        Get a control from the framework by ID.
        
        Args:
            control_id: ID of the control to get
            
        Returns:
            The control or None if not found
        """
        for control in self.controls:
            if control.id == control_id:
                return control
        return None
    
    def remove_control(self, control_id: str) -> bool:
        """
        Remove a control from the framework.
        
        Args:
            control_id: ID of the control to remove
            
        Returns:
            True if control was removed, False if not found
        """
        for i, control in enumerate(self.controls):
            if control.id == control_id:
                self.controls.pop(i)
                return True
        return False
    
    def get_controls_by_section(self, section: str) -> List[ComplianceControl]:
        """
        Get all controls in a specific section.
        
        Args:
            section: Section identifier
            
        Returns:
            List of controls in the section
        """
        return [c for c in self.controls if c.section.startswith(section)]
    
    def get_controls_with_findings(self) -> List[ComplianceControl]:
        """
        Get all controls that have associated findings.
        
        Returns:
            List of controls with findings
        """
        return [c for c in self.controls if c.finding_ids]
    
    def get_compliance_status(self) -> Dict[str, int]:
        """
        Get counts of controls by compliance status.
        
        Returns:
            Dictionary mapping status values to counts
        """
        status_counts = {s.value: 0 for s in ComplianceControlStatus}
        
        for control in self.controls:
            status_counts[control.status.value] += 1
            
        return status_counts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert compliance framework to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add ComplianceFramework-specific fields
        data.update({
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'controls': [control.to_dict() for control in self.controls],
            'references': self.references,
            'tags': list(self.tags) if hasattr(self, 'tags') else []
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceFramework':
        """Create compliance framework from dictionary representation."""
        # Parse controls
        controls = []
        if 'controls' in data and data['controls']:
            for control_data in data['controls']:
                controls.append(ComplianceControl.from_dict(control_data))
        
        # Create instance
        framework = cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            version=data.get('version', ''),
            controls=controls,
            references=data.get('references', [])
        )
        
        # Set ID if provided
        if 'id' in data:
            framework.id = data['id']
        
        # Set tags if provided
        if 'tags' in data and hasattr(framework, 'tags'):
            framework.tags = set(data['tags'])
        
        return framework


class ComplianceMapping:
    """
    Mapping between security findings and compliance framework controls.
    
    Provides functionality to associate findings with controls and track
    compliance status across frameworks.
    """
    
    def __init__(self):
        """Initialize the compliance mapping."""
        # Dictionary mapping framework IDs to framework objects
        self.frameworks: Dict[str, ComplianceFramework] = {}
        
        # Dictionary mapping finding IDs to control IDs
        self.finding_to_controls: Dict[str, Set[str]] = {}
        
        # Dictionary mapping control IDs to finding IDs
        self.control_to_findings: Dict[str, Set[str]] = {}
    
    def add_framework(self, framework: ComplianceFramework) -> None:
        """
        Add a compliance framework.
        
        Args:
            framework: The framework to add
        """
        self.frameworks[framework.id] = framework
        
        # Initialize control mappings
        for control in framework.controls:
            control_id = control.id
            
            # Add existing findings
            for finding_id in control.finding_ids:
                if finding_id not in self.finding_to_controls:
                    self.finding_to_controls[finding_id] = set()
                    
                self.finding_to_controls[finding_id].add(control_id)
                
                if control_id not in self.control_to_findings:
                    self.control_to_findings[control_id] = set()
                    
                self.control_to_findings[control_id].add(finding_id)
    
    def get_framework(self, framework_id: str) -> Optional[ComplianceFramework]:
        """
        Get a framework by ID.
        
        Args:
            framework_id: ID of the framework to get
            
        Returns:
            The framework or None if not found
        """
        return self.frameworks.get(framework_id)
    
    def list_frameworks(self) -> List[ComplianceFramework]:
        """
        List all frameworks.
        
        Returns:
            List of compliance frameworks
        """
        return list(self.frameworks.values())
    
    def remove_framework(self, framework_id: str) -> bool:
        """
        Remove a framework and all its mappings.
        
        Args:
            framework_id: ID of the framework to remove
            
        Returns:
            True if framework was removed, False if not found
        """
        if framework_id not in self.frameworks:
            return False
            
        framework = self.frameworks[framework_id]
        
        # Remove all mappings for this framework's controls
        for control in framework.controls:
            control_id = control.id
            
            if control_id in self.control_to_findings:
                # Get findings associated with this control
                finding_ids = self.control_to_findings[control_id]
                
                # Remove control from finding mappings
                for finding_id in finding_ids:
                    if finding_id in self.finding_to_controls:
                        self.finding_to_controls[finding_id].discard(control_id)
                        
                        # Remove finding entry if it has no more controls
                        if not self.finding_to_controls[finding_id]:
                            del self.finding_to_controls[finding_id]
                
                # Remove control mapping
                del self.control_to_findings[control_id]
        
        # Remove the framework
        del self.frameworks[framework_id]
        return True
    
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
        """
        # Check if framework and control exist
        framework = self.frameworks.get(framework_id)
        if not framework:
            return False
            
        control = framework.get_control(control_id)
        if not control:
            return False
            
        # Add mapping
        if finding_id not in self.finding_to_controls:
            self.finding_to_controls[finding_id] = set()
            
        self.finding_to_controls[finding_id].add(control_id)
        
        if control_id not in self.control_to_findings:
            self.control_to_findings[control_id] = set()
            
        self.control_to_findings[control_id].add(finding_id)
        
        # Update control's finding list
        control.add_finding(finding_id)
        
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
        """
        # Check if framework and control exist
        framework = self.frameworks.get(framework_id)
        if not framework:
            return False
            
        control = framework.get_control(control_id)
        if not control:
            return False
            
        # Check if mapping exists
        if (finding_id not in self.finding_to_controls or
            control_id not in self.finding_to_controls[finding_id]):
            return False
            
        # Remove mapping
        self.finding_to_controls[finding_id].discard(control_id)
        
        # Remove finding entry if it has no more controls
        if not self.finding_to_controls[finding_id]:
            del self.finding_to_controls[finding_id]
            
        if control_id in self.control_to_findings:
            self.control_to_findings[control_id].discard(finding_id)
            
            # Remove control entry if it has no more findings
            if not self.control_to_findings[control_id]:
                del self.control_to_findings[control_id]
        
        # Update control's finding list
        control.remove_finding(finding_id)
        
        return True
    
    def get_controls_for_finding(self, finding_id: str) -> Dict[str, List[ComplianceControl]]:
        """
        Get all controls mapped to a finding, grouped by framework.

        Args:
            finding_id: ID of the finding

        Returns:
            Dictionary mapping framework IDs to lists of controls
        """
        result = {}

        if finding_id not in self.finding_to_controls:
            return result

        control_ids = self.finding_to_controls[finding_id]

        for framework_id, framework in self.frameworks.items():
            controls = []

            for control_id in sorted(control_ids):  # Sort control IDs for deterministic order
                control = framework.get_control(control_id)
                if control:
                    controls.append(control)

            if controls:
                result[framework_id] = controls

        return result
    
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
        """
        # Check if framework and control exist
        framework = self.frameworks.get(framework_id)
        if not framework:
            return []
            
        control = framework.get_control(control_id)
        if not control:
            return []
            
        return list(control.finding_ids)
    
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
        """
        # Check if framework and control exist
        framework = self.frameworks.get(framework_id)
        if not framework:
            return False
            
        control = framework.get_control(control_id)
        if not control:
            return False
            
        # Update control status
        control.update_status(status, justification)
        return True
    
    def get_framework_compliance_status(self, framework_id: str) -> Optional[Dict[str, int]]:
        """
        Get the compliance status for a framework.
        
        Args:
            framework_id: ID of the framework
            
        Returns:
            Dictionary mapping status values to counts, or None if framework not found
        """
        framework = self.frameworks.get(framework_id)
        if not framework:
            return None
            
        return framework.get_compliance_status()
    
    def get_overall_compliance_status(self) -> Dict[str, Dict[str, int]]:
        """
        Get the compliance status across all frameworks.
        
        Returns:
            Dictionary mapping framework IDs to status counts
        """
        result = {}
        
        for framework_id, framework in self.frameworks.items():
            result[framework_id] = framework.get_compliance_status()
            
        return result