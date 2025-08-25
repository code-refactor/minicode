"""Remediation Tracker for managing vulnerability lifecycle."""

import time
import uuid
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union, Tuple
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator, model_validator

from common.core import BaseEntity, StatusMixin, ValidationError
from securetask.utils.validation import ValidationError as SecureValidationError


class RemediationState(str, Enum):
    """States in the vulnerability remediation workflow."""

    OPEN = "open"  # Initial state, vulnerability identified
    ASSIGNED = "assigned"  # Vulnerability assigned for remediation
    IN_PROGRESS = "in_progress"  # Remediation in progress
    REMEDIATED = "remediated"  # Remediation implemented, awaiting verification
    VERIFICATION_FAILED = "verification_failed"  # Verification failed, needs further remediation
    VERIFIED = "verified"  # Remediation verified as effective
    CLOSED = "closed"  # Issue closed
    ACCEPTED_RISK = "accepted_risk"  # Risk accepted, no remediation planned
    DEFERRED = "deferred"  # Remediation deferred to a later date
    FALSE_POSITIVE = "false_positive"  # Determined to be a false positive
    DUPLICATE = "duplicate"  # Duplicate of another finding


class RemediationPriority(str, Enum):
    """Priority levels for vulnerability remediation."""

    CRITICAL = "critical"  # Must be fixed immediately
    HIGH = "high"  # Must be fixed in next release
    MEDIUM = "medium"  # Should be fixed soon
    LOW = "low"  # Fix when convenient


@dataclass
class StateTransition(BaseEntity):
    """Model representing a state transition in the remediation workflow."""

    finding_id: str = ""
    from_state: Optional[RemediationState] = None
    to_state: RemediationState = RemediationState.OPEN
    timestamp: datetime = field(default_factory=datetime.now)
    performed_by: str = ""
    comments: Optional[str] = None
    require_approval: bool = False
    approver: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    evidence_ids: List[str] = field(default_factory=list)
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        if not self.finding_id:
            errors.append(ValidationError(field="finding_id", message="Finding ID is required"))
        if not self.performed_by:
            errors.append(ValidationError(field="performed_by", message="Performed by is required"))
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state transition to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add StateTransition-specific fields
        data.update({
            'finding_id': self.finding_id,
            'from_state': self.from_state.value if self.from_state else None,
            'to_state': self.to_state.value if isinstance(self.to_state, RemediationState) else self.to_state,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'performed_by': self.performed_by,
            'comments': self.comments,
            'require_approval': self.require_approval,
            'approver': self.approver,
            'approval_timestamp': self.approval_timestamp.isoformat() if self.approval_timestamp and isinstance(self.approval_timestamp, datetime) else self.approval_timestamp,
            'evidence_ids': self.evidence_ids
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateTransition':
        """Create state transition from dictionary representation."""
        # Parse datetime fields
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'approval_timestamp' in data and isinstance(data['approval_timestamp'], str):
            data['approval_timestamp'] = datetime.fromisoformat(data['approval_timestamp'])
        
        # Convert enum fields from strings if needed
        if 'from_state' in data and isinstance(data['from_state'], str):
            data['from_state'] = RemediationState(data['from_state']) if data['from_state'] else None
        if 'to_state' in data and isinstance(data['to_state'], str):
            data['to_state'] = RemediationState(data['to_state'])
        
        # Create instance
        transition = cls(
            finding_id=data.get('finding_id', ''),
            from_state=data.get('from_state'),
            to_state=data.get('to_state', RemediationState.OPEN),
            timestamp=data.get('timestamp', datetime.now()),
            performed_by=data.get('performed_by', ''),
            comments=data.get('comments'),
            require_approval=data.get('require_approval', False),
            approver=data.get('approver'),
            approval_timestamp=data.get('approval_timestamp'),
            evidence_ids=data.get('evidence_ids', [])
        )
        
        # Set ID if provided
        if 'id' in data:
            transition.id = data['id']
        
        return transition


@dataclass
class RemediationTask(BaseEntity, StatusMixin):
    """Model representing a remediation task for a vulnerability."""

    finding_id: str = ""
    title: str = ""
    description: str = ""
    priority: RemediationPriority = RemediationPriority.MEDIUM
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: int = 0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    
    def __init__(self, finding_id: str = "", title: str = "", description: str = "", 
                 priority: Union[RemediationPriority, str] = RemediationPriority.MEDIUM,
                 assigned_to: Optional[str] = None, due_date: Optional[datetime] = None,
                 completed_at: Optional[datetime] = None, progress_percentage: int = 0,
                 steps: Optional[List[Dict[str, Any]]] = None, 
                 notes: Optional[List[Dict[str, Any]]] = None,
                 state: Optional[Union[RemediationState, str]] = None,
                 status: Optional[Union[RemediationState, str]] = None,
                 **kwargs):
        """Initialize remediation task with support for both state and status parameters."""
        self.finding_id = finding_id
        self.title = title
        self.description = description
        self.priority = priority
        self.assigned_to = assigned_to
        self.due_date = due_date
        self.completed_at = completed_at
        self.progress_percentage = progress_percentage
        self.steps = steps or []
        self.notes = notes or []
        
        # Initialize parent classes first
        BaseEntity.__init__(self, **kwargs)
        
        # Handle state/status parameter - state takes precedence for backward compatibility
        initial_status = state if state is not None else status
        
        # Call __post_init__ manually since we override __init__
        self.__post_init__()
        
        # Set status AFTER __post_init__ to override default initialization
        if initial_status is not None:
            self.status = self.validate_state(initial_status) if isinstance(initial_status, str) else initial_status
    
    def __post_init__(self):
        """Initialize mixins and set up status transitions."""
        StatusMixin.__init__(self)
        
        # Convert string values to enums if needed
        if isinstance(self.priority, str):
            self.priority = self.validate_priority(self.priority)
        if isinstance(self.status, str):
            self.status = self.validate_state(self.status)
        
        # Set initial status if not already set - only if status is None
        if not hasattr(self, 'status') or getattr(self, 'status', None) is None:
            self.status = RemediationState.OPEN
        
        # Define valid status transitions (same as WorkflowEngine)
        self.valid_transitions = {
            None: [RemediationState.OPEN],
            RemediationState.OPEN: [
                RemediationState.ASSIGNED, RemediationState.ACCEPTED_RISK, 
                RemediationState.FALSE_POSITIVE, RemediationState.DUPLICATE
            ],
            RemediationState.ASSIGNED: [
                RemediationState.IN_PROGRESS, RemediationState.DEFERRED,
                RemediationState.ACCEPTED_RISK, RemediationState.FALSE_POSITIVE,
                RemediationState.DUPLICATE
            ],
            RemediationState.IN_PROGRESS: [
                RemediationState.REMEDIATED, RemediationState.DEFERRED,
                RemediationState.ACCEPTED_RISK, RemediationState.FALSE_POSITIVE,
                RemediationState.DUPLICATE
            ],
            RemediationState.REMEDIATED: [
                RemediationState.VERIFIED, RemediationState.VERIFICATION_FAILED
            ],
            RemediationState.VERIFICATION_FAILED: [
                RemediationState.IN_PROGRESS, RemediationState.ASSIGNED,
                RemediationState.ACCEPTED_RISK
            ],
            RemediationState.VERIFIED: [RemediationState.CLOSED],
            RemediationState.CLOSED: [],
            RemediationState.ACCEPTED_RISK: [RemediationState.OPEN],
            RemediationState.DEFERRED: [RemediationState.OPEN, RemediationState.ASSIGNED],
            RemediationState.FALSE_POSITIVE: [],
            RemediationState.DUPLICATE: []
        }
    
    # Expose status as state property for backward compatibility
    @property
    def state(self) -> RemediationState:
        return self.status
    
    @state.setter
    def state(self, value: RemediationState):
        self.status = value

    def validate_priority(self, value):
        """Validate the priority level."""
        if isinstance(value, RemediationPriority):
            return value

        if isinstance(value, str) and value in [p.value for p in RemediationPriority]:
            return RemediationPriority(value)

        raise SecureValidationError(
            f"Invalid priority: {value}. Allowed values: {', '.join([p.value for p in RemediationPriority])}",
            "priority"
        )

    def validate_state(self, value):
        """Validate the state."""
        if isinstance(value, RemediationState):
            return value

        if isinstance(value, str) and value in [s.value for s in RemediationState]:
            return RemediationState(value)

        raise SecureValidationError(
            f"Invalid state: {value}. Allowed values: {', '.join([s.value for s in RemediationState])}",
            "state"
        )
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate all fields and return list of errors."""
        errors = []
        
        # Validate required fields
        if not self.finding_id:
            errors.append(ValidationError(field="finding_id", message="Finding ID is required"))
        if not self.title:
            errors.append(ValidationError(field="title", message="Title is required"))
        if not self.description:
            errors.append(ValidationError(field="description", message="Description is required"))
        
        # Validate priority
        try:
            self.validate_priority(self.priority)
        except SecureValidationError as e:
            errors.append(ValidationError(field="priority", message=str(e)))
        
        # Validate state
        try:
            self.validate_state(self.state)
        except SecureValidationError as e:
            errors.append(ValidationError(field="state", message=str(e)))
        
        return errors
    
    def add_step(self, title: str, description: str, estimate_hours: Optional[float] = None) -> Dict[str, Any]:
        """
        Add a remediation step to this task.
        
        Args:
            title: Step title
            description: Step description
            estimate_hours: Estimated hours to complete
            
        Returns:
            The created step
        """
        step = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "estimate_hours": estimate_hours,
            "completed": False,
            "created_at": datetime.now()
        }
        
        self.steps.append(step)
        return step
    
    def complete_step(self, step_id: str, completed_by: str) -> bool:
        """
        Mark a step as completed.
        
        Args:
            step_id: ID of the step to complete
            completed_by: ID of the user completing the step
            
        Returns:
            True if step was found and completed, False otherwise
        """
        for step in self.steps:
            if step["id"] == step_id:
                step["completed"] = True
                step["completed_at"] = datetime.now()
                step["completed_by"] = completed_by
                
                # Recalculate progress percentage
                self._update_progress()
                
                return True
                
        return False
    
    def add_note(self, content: str, author: str) -> Dict[str, Any]:
        """
        Add a note to the remediation task.
        
        Args:
            content: Note content
            author: Note author
            
        Returns:
            The created note
        """
        note = {
            "id": str(uuid.uuid4()),
            "content": content,
            "author": author,
            "timestamp": datetime.now()
        }
        
        self.notes.append(note)
        return note
    
    def _update_progress(self) -> None:
        """Update the progress percentage based on completed steps."""
        if not self.steps:
            self.progress_percentage = 0
            return
            
        completed = sum(1 for step in self.steps if step.get("completed", False))
        self.progress_percentage = int((completed / len(self.steps)) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert remediation task to dictionary representation."""
        # Get base dict from parent
        data = super().to_dict()
        
        # Add RemediationTask-specific fields
        data.update({
            'finding_id': self.finding_id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value if isinstance(self.priority, RemediationPriority) else self.priority,
            'assigned_to': self.assigned_to,
            'due_date': self.due_date.isoformat() if self.due_date and isinstance(self.due_date, datetime) else self.due_date,
            'completed_at': self.completed_at.isoformat() if self.completed_at and isinstance(self.completed_at, datetime) else self.completed_at,
            'progress_percentage': self.progress_percentage,
            'steps': self.steps,
            'notes': self.notes,
            'status': self.status.value if isinstance(self.status, RemediationState) else self.status,
            'state': self.status.value if isinstance(self.status, RemediationState) else self.status  # For backward compatibility
        })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RemediationTask':
        """Create remediation task from dictionary representation."""
        # Parse datetime fields
        if 'due_date' in data and isinstance(data['due_date'], str):
            data['due_date'] = datetime.fromisoformat(data['due_date'])
        if 'completed_at' in data and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        # Convert enum fields from strings if needed
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = RemediationPriority(data['priority'])
        
        # Handle both status and state fields for backward compatibility
        status_value = data.get('status', data.get('state', RemediationState.OPEN))
        if isinstance(status_value, str):
            status_value = RemediationState(status_value)
        
        # Create instance
        task = cls(
            finding_id=data.get('finding_id', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            priority=data.get('priority', RemediationPriority.MEDIUM),
            assigned_to=data.get('assigned_to'),
            due_date=data.get('due_date'),
            completed_at=data.get('completed_at'),
            progress_percentage=data.get('progress_percentage', 0),
            steps=data.get('steps', []),
            notes=data.get('notes', [])
        )
        
        # Set ID if provided
        if 'id' in data:
            task.id = data['id']
        
        # Set status after __post_init__ has run
        task.status = status_value
        
        return task


class WorkflowEngine:
    """
    Engine for managing the vulnerability remediation workflow.
    
    Manages state transitions, tasks, and approval processes for 
    vulnerability remediation.
    """
    
    def __init__(self):
        """Initialize the workflow engine with the valid state transitions."""
        # Define allowed state transitions
        self.allowed_transitions = {
            None: {RemediationState.OPEN},  # Initial state
            RemediationState.OPEN: {
                RemediationState.ASSIGNED, RemediationState.ACCEPTED_RISK, 
                RemediationState.FALSE_POSITIVE, RemediationState.DUPLICATE
            },
            RemediationState.ASSIGNED: {
                RemediationState.IN_PROGRESS, RemediationState.DEFERRED,
                RemediationState.ACCEPTED_RISK, RemediationState.FALSE_POSITIVE,
                RemediationState.DUPLICATE
            },
            RemediationState.IN_PROGRESS: {
                RemediationState.REMEDIATED, RemediationState.DEFERRED,
                RemediationState.ACCEPTED_RISK, RemediationState.FALSE_POSITIVE,
                RemediationState.DUPLICATE
            },
            RemediationState.REMEDIATED: {
                RemediationState.VERIFIED, RemediationState.VERIFICATION_FAILED
            },
            RemediationState.VERIFICATION_FAILED: {
                RemediationState.IN_PROGRESS, RemediationState.ASSIGNED,
                RemediationState.ACCEPTED_RISK
            },
            RemediationState.VERIFIED: {RemediationState.CLOSED},
            RemediationState.CLOSED: set(),  # Terminal state
            RemediationState.ACCEPTED_RISK: {RemediationState.OPEN},  # Can be reopened
            RemediationState.DEFERRED: {RemediationState.OPEN, RemediationState.ASSIGNED},
            RemediationState.FALSE_POSITIVE: set(),  # Terminal state
            RemediationState.DUPLICATE: set()  # Terminal state
        }
        
        # Define states requiring approval
        self.approval_required = {
            RemediationState.ACCEPTED_RISK,
            RemediationState.VERIFIED,
            RemediationState.CLOSED
        }
    
    def is_valid_transition(self, from_state: Optional[Union[RemediationState, str]], to_state: Union[RemediationState, str]) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if the transition is valid, False otherwise
        """
        # Handle string values
        if isinstance(from_state, str):
            try:
                from_state = RemediationState(from_state)
            except ValueError:
                return False
                
        if isinstance(to_state, str):
            try:
                to_state = RemediationState(to_state)
            except ValueError:
                return False
                
        # Special case to handle the same state transition
        if from_state == to_state:
            return True
        
        if from_state not in self.allowed_transitions:
            return False
            
        return to_state in self.allowed_transitions[from_state]
    
    def requires_approval(self, to_state: Union[RemediationState, str]) -> bool:
        """
        Check if a state transition requires approval.
        
        Args:
            to_state: Target state
            
        Returns:
            True if approval is required, False otherwise
        """
        if isinstance(to_state, str):
            try:
                to_state = RemediationState(to_state)
            except ValueError:
                return False
                
        return to_state in self.approval_required
    
    def transition(
        self,
        task: RemediationTask,
        to_state: Union[RemediationState, str],
        performed_by: str,
        comments: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None,
        approver: Optional[str] = None
    ) -> Tuple[RemediationTask, StateTransition]:
        """
        Transition a remediation task to a new state.
        
        Args:
            task: The remediation task to transition
            to_state: The target state
            performed_by: ID of the user performing the transition
            comments: Optional comments about the transition
            evidence_ids: Optional list of evidence IDs
            approver: Optional ID of the approver (required for some transitions)
            
        Returns:
            Tuple of (updated task, state transition record)
            
        Raises:
            ValidationError: If the transition is invalid
        """
        start_time = time.time()
        
        # Convert string to enum if needed
        if isinstance(to_state, str):
            try:
                to_state = RemediationState(to_state)
            except ValueError:
                raise SecureValidationError(f"Invalid state: {to_state}", "to_state")
        
        # Special case to handle the same state transition
        if task.state == to_state:
            # Create a state transition record anyway but mark it as a no-op
            transition = StateTransition(
                finding_id=task.finding_id,
                from_state=task.state,
                to_state=to_state,
                performed_by=performed_by,
                comments=comments or "No state change",
                evidence_ids=evidence_ids or []
            )
            return task, transition
        
        # Check if transition is valid
        if not self.is_valid_transition(task.state, to_state):
            raise SecureValidationError(
                f"Invalid state transition from {task.state} to {to_state}",
                "to_state"
            )
        
        # Check if approval is required
        require_approval = self.requires_approval(to_state)
        
        if require_approval and not approver:
            raise SecureValidationError(
                f"Transition to {to_state} requires approval",
                "approver"
            )
        
        # Create state transition record
        transition = StateTransition(
            finding_id=task.finding_id,
            from_state=task.state,
            to_state=to_state,
            performed_by=performed_by,
            comments=comments,
            require_approval=require_approval,
            approver=approver,
            approval_timestamp=datetime.now() if approver else None,
            evidence_ids=evidence_ids or []
        )
        
        # Update task state
        task.state = to_state
        
        # Handle special state transitions
        if to_state == RemediationState.ASSIGNED and not task.assigned_to:
            task.assigned_to = performed_by
            
        if to_state == RemediationState.CLOSED:
            task.completed_at = datetime.now()
            task.progress_percentage = 100
            
        if to_state == RemediationState.REMEDIATED:
            task.progress_percentage = 100
            
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: State transition took {execution_time*1000:.2f}ms")
            
        return task, transition