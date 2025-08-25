"""Remediation tracking system for vulnerability management."""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Tuple

from pydantic import ValidationError as PydanticValidationError

from common.core import BaseService, FileStorage, StorageInterface, ValidationError
from securetask.remediation.workflow import (
    RemediationTask, StateTransition, RemediationState, 
    RemediationPriority, WorkflowEngine
)
from securetask.utils.crypto import CryptoManager
from securetask.utils.validation import ValidationError as SecureValidationError


class EncryptedTaskStorage(StorageInterface[RemediationTask]):
    """Encrypted file storage for remediation tasks with individual files per task."""
    
    def __init__(self, storage_dir: Path, crypto_manager: Optional[CryptoManager] = None):
        """Initialize encrypted storage."""
        self.storage_dir = Path(storage_dir)
        self.tasks_dir = self.storage_dir / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.crypto_manager = crypto_manager or CryptoManager()
        self._cache: Dict[str, RemediationTask] = {}
    
    def _get_file_paths(self, task_id: str) -> tuple[Path, Path]:
        """Get encrypted file and HMAC digest paths for a task."""
        task_id_str = str(task_id) if isinstance(task_id, uuid.UUID) else task_id
        enc_path = self.tasks_dir / f"{task_id_str}.json.enc"
        hmac_path = self.tasks_dir / f"{task_id_str}.hmac"
        return enc_path, hmac_path
    
    def create(self, entity: RemediationTask) -> str:
        """Create a new task."""
        task_id = str(entity.id) if hasattr(entity, 'id') else str(uuid.uuid4())
        
        # Serialize to JSON
        task_dict = entity.to_dict()
        json_data = json.dumps(task_dict, default=str).encode()
        
        # Encrypt
        encrypted_data, digest = self.crypto_manager.encrypt(json_data)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(task_id)
        
        # Save encrypted data
        with open(enc_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Save HMAC digest
        with open(hmac_path, 'wb') as f:
            f.write(digest)
        
        # Cache the task
        self._cache[task_id] = entity
        
        return task_id
    
    def get(self, entity_id: Union[str, uuid.UUID]) -> Optional[RemediationTask]:
        """Get a task by ID."""
        task_id = str(entity_id)
        
        # Check cache first
        if task_id in self._cache:
            return self._cache[task_id]
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(task_id)
        
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
        task_dict = json.loads(decrypted_data.decode())
        
        # Create RemediationTask instance
        task = RemediationTask.from_dict(task_dict)
        
        # Cache it
        self._cache[task_id] = task
        
        return task
    
    def update(self, entity: RemediationTask) -> Optional[RemediationTask]:
        """Update an existing task."""
        task_id = str(entity.id)
        
        # Check if exists
        enc_path, hmac_path = self._get_file_paths(task_id)
        if not enc_path.exists():
            return None
        
        # Update timestamp
        if hasattr(entity, 'updated_at'):
            entity.updated_at = datetime.now()
        
        # Save updated task
        self.create(entity)
        
        return entity
    
    def delete(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Delete a task."""
        task_id = str(entity_id)
        
        # Get file paths
        enc_path, hmac_path = self._get_file_paths(task_id)
        
        # Delete files
        deleted = False
        if enc_path.exists():
            enc_path.unlink()
            deleted = True
        if hmac_path.exists():
            hmac_path.unlink()
        
        # Remove from cache
        if task_id in self._cache:
            del self._cache[task_id]
        
        return deleted
    
    def list(self, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[str] = None,
             limit: Optional[int] = None, offset: int = 0) -> List[RemediationTask]:
        """List all tasks."""
        tasks = []
        
        # Load all tasks from disk
        for enc_file in self.tasks_dir.glob("*.json.enc"):
            task_id = enc_file.stem.replace('.json', '')
            task = self.get(task_id)
            if task:
                tasks.append(task)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                tasks = [t for t in tasks if getattr(t, key, None) == value]
        
        # Sort if requested
        if sort_by:
            reverse = sort_by.startswith('-')
            key = sort_by[1:] if reverse else sort_by
            tasks.sort(key=lambda x: getattr(x, key, ''), reverse=reverse)
        
        # Apply pagination
        if offset:
            tasks = tasks[offset:]
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count tasks."""
        return len(self.list(filters=filters))
    
    def clear(self) -> None:
        """Clear all tasks."""
        for enc_file in self.tasks_dir.glob("*.json.enc"):
            enc_file.unlink()
        for hmac_file in self.tasks_dir.glob("*.hmac"):
            hmac_file.unlink()
        self._cache.clear()
    
    def exists(self, entity_id: Union[str, uuid.UUID]) -> bool:
        """Check if a task exists."""
        task_id = str(entity_id)
        enc_path, _ = self._get_file_paths(task_id)
        return enc_path.exists()


class RemediationTracker(BaseService[RemediationTask]):
    """
    System for tracking vulnerability remediation progress.
    
    Manages remediation tasks, workflow state transitions, and reporting on
    remediation status across security findings.
    """
    
    def __init__(self, storage_dir: str, crypto_manager: Optional[CryptoManager] = None):
        """
        Initialize the remediation tracker.
        
        Args:
            storage_dir: Directory where remediation data will be stored
            crypto_manager: Optional crypto manager for encryption
        """
        # Create encrypted storage for tasks with individual files
        storage = EncryptedTaskStorage(Path(storage_dir), crypto_manager)
        
        # Initialize base service
        super().__init__(storage)
        
        # Add custom validators
        self.add_validator(self._validate_task_business_rules)
        
        # Set up additional components
        self.crypto_manager = crypto_manager or CryptoManager()
        self.workflow_engine = WorkflowEngine()
        
        # Set up transitions directory
        self.transitions_dir = Path(storage_dir) / "transitions"
        self.transitions_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_task_business_rules(self, task: RemediationTask) -> List[ValidationError]:
        """Custom business rule validation for tasks."""
        errors = []
        
        # Validate due date is not in the past for new tasks
        if task.due_date and task.due_date < datetime.now() and task.state == RemediationState.OPEN:
            errors.append(ValidationError(
                field="due_date",
                message="Due date cannot be in the past for new tasks"
            ))
        
        # Validate assigned_to is present when state is ASSIGNED
        if task.state == RemediationState.ASSIGNED and not task.assigned_to:
            errors.append(ValidationError(
                field="assigned_to",
                message="Assigned to field is required for assigned tasks"
            ))
        
        return errors
    
    def create_task(
        self,
        finding_id: str,
        title: str,
        description: str,
        priority: Union[RemediationPriority, str],
        created_by: str,
        due_date: Optional[datetime] = None,
        assigned_to: Optional[str] = None,
        initial_state: RemediationState = RemediationState.OPEN
    ) -> RemediationTask:
        """
        Create a new remediation task for a finding.
        
        Args:
            finding_id: ID of the finding to create a task for
            title: Task title
            description: Task description
            priority: Task priority
            created_by: ID of the user creating the task
            due_date: Optional due date for the task
            assigned_to: Optional ID of user assigned to the task
            initial_state: Initial state for the task
            
        Returns:
            The created remediation task
            
        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        try:
            # Create the task with initial OPEN state
            task = RemediationTask(
                finding_id=finding_id,
                title=title,
                description=description,
                priority=priority,
                assigned_to=assigned_to,
                due_date=due_date
            )
            
            # Add initial note
            task.add_note(
                content=f"Task created with priority {priority} and initial state open",
                author=created_by
            )
            
            # Create using base service
            task_id = self.create_with_validation(task)
            
            # If the initial state is not OPEN or we need to assign a user, transition the task
            if initial_state != RemediationState.OPEN or assigned_to:
                comments = f"Task assigned to {assigned_to}" if assigned_to else None
                updated_task, transition = self.workflow_engine.transition(
                    task=task,
                    to_state=initial_state,
                    performed_by=created_by,
                    comments=comments
                )
                
                # Save the transition
                self._save_transition(transition)
                
                # Update the task in storage
                self.update_with_validation(updated_task)
                task = updated_task
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Task creation took {execution_time*1000:.2f}ms")
                
            return task
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def get_task(self, task_id: str) -> RemediationTask:
        """
        Retrieve a remediation task by ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            The retrieved task
            
        Raises:
            FileNotFoundError: If the task does not exist
        """
        task = self.get(task_id)
        if task is None:
            raise FileNotFoundError(f"Task not found: {task_id}")
        return task
    
    def update_task(self, task: RemediationTask) -> RemediationTask:
        """
        Update an existing remediation task.
        
        Args:
            task: The task to update
            
        Returns:
            The updated task
            
        Raises:
            FileNotFoundError: If the task does not exist
            ValidationError: If validation fails
        """
        start_time = time.time()
        
        try:
            updated = self.update_with_validation(task)
            if updated is None:
                raise FileNotFoundError(f"Task not found: {task.id}")
            
            execution_time = time.time() - start_time
            if execution_time > 0.05:  # 50ms
                print(f"Warning: Task update took {execution_time*1000:.2f}ms")
            
            return updated
            
        except Exception as e:
            raise SecureValidationError(str(e))
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a remediation task.
        
        Args:
            task_id: ID of the task to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Get the task to get finding_id for cleanup
        try:
            task = self.get_task(task_id)
            finding_id = task.finding_id
        except FileNotFoundError:
            return False
        
        # Delete the task using base service
        if not self.delete_with_hooks(task_id):
            return False
        
        # Delete related transitions
        for filename in os.listdir(self.transitions_dir):
            if filename.endswith(".json.enc"):
                try:
                    transition_id = filename.replace(".json.enc", "")
                    transition = self.get_transition(transition_id)
                    
                    # If this transition belongs to the deleted task
                    if transition.finding_id == finding_id:
                        # Delete this transition too
                        transition_path = self.transitions_dir / filename
                        transition_digest = self.transitions_dir / f"{transition_id}.hmac"
                        
                        transition_path.unlink(missing_ok=True)
                        transition_digest.unlink(missing_ok=True)
                except Exception:
                    # Ignore errors and continue
                    pass
                    
        return True
    
    def transition_task(
        self,
        task_id: str,
        to_state: Union[RemediationState, str],
        performed_by: str,
        comments: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None,
        approver: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Tuple[RemediationTask, StateTransition]:
        """
        Transition a task to a new state.

        Args:
            task_id: ID of the task to transition
            to_state: Target state
            performed_by: ID of user performing the transition
            comments: Optional comments
            evidence_ids: Optional list of evidence IDs
            approver: Optional ID of approver (required for some transitions)
            assigned_to: Optional ID of user to assign the task to (for ASSIGNED state)

        Returns:
            Tuple of (updated task, state transition record)

        Raises:
            FileNotFoundError: If the task does not exist
            ValidationError: If the transition is invalid
        """
        start_time = time.time()

        # Get the task
        task = self.get_task(task_id)

        # Update assigned_to if provided and transitioning to ASSIGNED state
        if assigned_to is not None and (
            (isinstance(to_state, str) and to_state == "assigned") or 
            (isinstance(to_state, RemediationState) and to_state == RemediationState.ASSIGNED)
        ):
            task.assigned_to = assigned_to

        # Perform the transition
        updated_task, transition = self.workflow_engine.transition(
            task=task,
            to_state=to_state,
            performed_by=performed_by,
            comments=comments,
            evidence_ids=evidence_ids,
            approver=approver
        )
        
        # Save the transition
        self._save_transition(transition)
        
        # Update the task in storage
        self.update_with_validation(updated_task)
        
        execution_time = time.time() - start_time
        if execution_time > 0.05:  # 50ms
            print(f"Warning: Task transition took {execution_time*1000:.2f}ms")
            
        return updated_task, transition
    
    def get_transition(self, transition_id: str) -> StateTransition:
        """
        Retrieve a state transition by ID.
        
        Args:
            transition_id: ID of the transition to retrieve
            
        Returns:
            The retrieved transition
            
        Raises:
            FileNotFoundError: If the transition does not exist
        """
        file_path = self.transitions_dir / f"{transition_id}.json.enc"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Transition not found: {transition_id}")
        
        # Load and decrypt
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        
        # Load HMAC digest
        digest_path = self.transitions_dir / f"{transition_id}.hmac"
        with open(digest_path, "rb") as f:
            digest = f.read()
        
        decrypted_data = self.crypto_manager.decrypt(encrypted_data, digest)
        transition_dict = json.loads(decrypted_data.decode())
        
        return StateTransition.from_dict(transition_dict)
    
    def get_task_by_finding(self, finding_id: str) -> Optional[RemediationTask]:
        """
        Get the remediation task for a finding.
        
        Args:
            finding_id: ID of the finding
            
        Returns:
            The remediation task or None if not found
        """
        # Use storage filtering to find task by finding_id
        tasks = self.list(filters={"finding_id": finding_id}, limit=1)
        return tasks[0] if tasks else None
    
    def get_transition_history(self, task_id: str) -> List[StateTransition]:
        """
        Get the full transition history for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            List of state transitions in chronological order
        """
        # Get the task to get the finding ID
        try:
            task = self.get_task(task_id)
            finding_id = task.finding_id
        except FileNotFoundError:
            return []
        
        # Find all transitions for this finding
        transitions = []
        
        for filename in os.listdir(self.transitions_dir):
            if not filename.endswith(".json.enc"):
                continue
                
            transition_id = filename.replace(".json.enc", "")
            
            try:
                transition = self.get_transition(transition_id)
                if transition.finding_id == finding_id:
                    transitions.append(transition)
            except Exception:
                # Skip invalid transitions
                continue
        
        # Sort by timestamp
        return sorted(transitions, key=lambda t: t.timestamp)
    
    def list_tasks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        reverse: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[RemediationTask]:
        """
        List tasks with optional filtering and sorting.

        Args:
            filters: Optional filters as field-value pairs
            sort_by: Field to sort by
            reverse: Whether to sort in reverse order
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of tasks matching criteria
        """
        # Convert sort direction to storage format
        storage_sort_by = f"-{sort_by}" if reverse else sort_by
        
        return self.list(
            filters=filters,
            sort_by=storage_sort_by,
            limit=limit,
            offset=offset
        )
    
    def count_tasks(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count tasks matching filters.
        
        Args:
            filters: Optional filters as field-value pairs
            
        Returns:
            Number of tasks matching criteria
        """
        return self.count(filters)
    
    def get_remediation_metrics(self) -> Dict[str, Any]:
        """
        Get metrics on remediation status across all tasks.
        
        Returns:
            Dictionary of metrics
        """
        metrics = {
            "total_tasks": 0,
            "by_state": {s.value: 0 for s in RemediationState},
            "by_priority": {p.value: 0 for p in RemediationPriority},
            "overdue_tasks": 0,
            "avg_resolution_time_days": 0,
            "avg_verification_time_days": 0,
            "tasks_requiring_approval": 0
        }
        
        # Temporary data for calculating averages
        resolution_times = []
        verification_times = []
        
        # Process all tasks
        all_tasks = self.list()
        for task in all_tasks:
            metrics["total_tasks"] += 1
            
            # Count by state
            metrics["by_state"][task.state.value] += 1
            
            # Count by priority
            metrics["by_priority"][task.priority.value] += 1
            
            # Check if overdue
            if task.due_date and task.due_date < datetime.now() and task.state not in [
                RemediationState.VERIFIED, RemediationState.CLOSED,
                RemediationState.FALSE_POSITIVE, RemediationState.DUPLICATE
            ]:
                metrics["overdue_tasks"] += 1
            
            # Get transition history
            transitions = self.get_transition_history(task.id)
            
            # Calculate resolution time (time to remediated state)
            open_time = None
            remediated_time = None
            verified_time = None
            
            for t in transitions:
                if t.to_state == RemediationState.OPEN:
                    open_time = t.timestamp
                elif t.to_state == RemediationState.REMEDIATED:
                    remediated_time = t.timestamp
                elif t.to_state == RemediationState.VERIFIED:
                    verified_time = t.timestamp
            
            # If we have both open and remediated times, calculate resolution time
            if open_time and remediated_time:
                resolution_days = (remediated_time - open_time).total_seconds() / (60 * 60 * 24)
                resolution_times.append(resolution_days)
            
            # If we have both remediated and verified times, calculate verification time
            if remediated_time and verified_time:
                verification_days = (verified_time - remediated_time).total_seconds() / (60 * 60 * 24)
                verification_times.append(verification_days)
            
            # Check if task requires approval
            if task.state in [s for s in RemediationState if self.workflow_engine.requires_approval(s)]:
                metrics["tasks_requiring_approval"] += 1
        
        # Calculate averages
        if resolution_times:
            metrics["avg_resolution_time_days"] = sum(resolution_times) / len(resolution_times)
            
        if verification_times:
            metrics["avg_verification_time_days"] = sum(verification_times) / len(verification_times)
        
        return metrics
    
    def _save_transition(self, transition: StateTransition) -> None:
        """
        Save a state transition with encryption.
        
        Args:
            transition: The transition to save
        """
        # Convert to JSON
        transition_json = json.dumps(transition.to_dict(), default=str).encode()
        
        # Encrypt
        encrypted_data, digest = self.crypto_manager.encrypt(transition_json)
        
        # Save encrypted data
        file_path = self.transitions_dir / f"{transition.id}.json.enc"
        with open(file_path, "wb") as f:
            f.write(encrypted_data)
            
        # Save HMAC digest separately for integrity verification
        digest_path = self.transitions_dir / f"{transition.id}.hmac"
        with open(digest_path, "wb") as f:
            f.write(digest)
    
    # Legacy compatibility methods
    def create(self, *args, **kwargs) -> RemediationTask:
        """Legacy compatibility method."""
        return self.create_task(*args, **kwargs)
    
    def get(self, task_id: str) -> RemediationTask:
        """Legacy compatibility method."""
        # Call storage directly to avoid recursion
        task = self.storage.get(task_id)
        if task is None:
            raise FileNotFoundError(f"Task not found: {task_id}")
        return task
    
    def update(self, task: RemediationTask) -> RemediationTask:
        """Legacy compatibility method."""
        return self.update_task(task)
    
    def delete(self, task_id: str) -> bool:
        """Legacy compatibility method."""
        return self.delete_task(task_id)
    
    def list(self, *args, **kwargs) -> List[RemediationTask]:
        """Legacy compatibility method."""
        return self.list_tasks(*args, **kwargs)
    
    def count(self, *args, **kwargs) -> int:
        """Legacy compatibility method."""
        return self.count_tasks(*args, **kwargs)