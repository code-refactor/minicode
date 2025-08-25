"""Base models and mixins for the unified library."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union
import uuid
from uuid import UUID

T = TypeVar('T')


@dataclass
class BaseEntity(ABC):
    """Abstract base class for all entities with common fields."""
    
    id: Union[UUID, str] = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure id is a UUID object for backward compatibility."""
        # If id is a string that looks like a UUID, convert it to UUID object
        # Otherwise, keep it as-is for custom IDs
        if isinstance(self.id, str):
            try:
                # Try to parse as UUID - if successful, convert to UUID object
                parsed_uuid = UUID(self.id)
                # Only convert if the string was a valid UUID format
                if str(parsed_uuid) == self.id.lower():
                    self.id = parsed_uuid
                # Otherwise keep the custom string ID
            except (ValueError, AttributeError, TypeError):
                # Not a valid UUID, keep as string
                pass
    
    def update(self, **kwargs) -> 'BaseEntity':
        """Update entity fields and refresh updated_at timestamp."""
        kwargs['updated_at'] = datetime.now()
        return replace(self, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        data = asdict(self)
        # Handle UUID serialization
        if isinstance(data.get('id'), UUID):
            data['id'] = str(data['id'])
        # Handle datetime serialization
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('updated_at'), datetime):
            data['updated_at'] = data['updated_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEntity':
        """Create entity from dictionary representation."""
        # Handle UUID deserialization
        if 'id' in data and isinstance(data['id'], str):
            try:
                data['id'] = UUID(data['id'])
            except (ValueError, AttributeError):
                pass
        # Handle datetime deserialization
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class TimestampedMixin:
    """Mixin for automatic timestamp management."""
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


@dataclass
class StatusChange:
    """Record of a status change."""
    
    from_status: Any
    to_status: Any
    timestamp: datetime = field(default_factory=datetime.now)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StatusMixin:
    """Mixin for entities with status tracking and transitions."""
    
    def __init__(self):
        self.status = None
        self.status_history: List[StatusChange] = []
        self.valid_transitions: Dict[Any, List[Any]] = {}
    
    def can_transition_to(self, new_status: Any) -> bool:
        """Check if transition to new status is valid."""
        if not self.valid_transitions:
            return True  # No restrictions if transitions not defined
        
        current_valid = self.valid_transitions.get(self.status, [])
        return new_status in current_valid
    
    def transition_to(self, new_status: Any, reason: Optional[str] = None) -> bool:
        """Transition to a new status if valid."""
        if not self.can_transition_to(new_status):
            return False
        
        change = StatusChange(
            from_status=self.status,
            to_status=new_status,
            reason=reason
        )
        self.status_history.append(change)
        self.status = new_status
        return True
    
    def get_status_history(self) -> List[StatusChange]:
        """Get the complete status change history."""
        return self.status_history.copy()


class TaggedMixin:
    """Mixin for entities that support tagging."""
    
    def __init__(self):
        self.tags: Set[str] = set()
    
    def add_tag(self, tag: str) -> bool:
        """Add a tag to the entity."""
        if tag in self.tags:
            return False
        self.tags.add(tag)
        return True
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the entity."""
        if tag not in self.tags:
            return False
        self.tags.remove(tag)
        return True
    
    def has_tag(self, tag: str) -> bool:
        """Check if entity has a specific tag."""
        return tag in self.tags
    
    def has_any_tag(self, tags: Set[str]) -> bool:
        """Check if entity has any of the specified tags."""
        return bool(self.tags & tags)
    
    def has_all_tags(self, tags: Set[str]) -> bool:
        """Check if entity has all of the specified tags."""
        return tags.issubset(self.tags)
    
    def clear_tags(self) -> None:
        """Remove all tags from the entity."""
        self.tags.clear()


@dataclass
class ValidationError:
    """Structured validation error information."""
    
    field: str
    message: str
    code: str = "validation_error"
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of the validation error."""
        return f"{self.field}: {self.message}"


class ValidationMixin:
    """Mixin for entities with self-validation capabilities."""
    
    def validate_fields(self) -> List[ValidationError]:
        """Validate entity fields and return list of errors."""
        return []
    
    def is_valid(self) -> bool:
        """Check if entity is valid."""
        return len(self.validate_fields()) == 0
    
    def validate_or_raise(self) -> None:
        """Validate entity and raise exception if invalid."""
        errors = self.validate_fields()
        if errors:
            error_messages = [str(e) for e in errors]
            raise ValueError(f"Validation failed: {'; '.join(error_messages)}")


@dataclass
class NamedEntity(BaseEntity):
    """Base class for entities with a name."""
    
    name: str = ""
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate name is not empty."""
        if not self.name:
            raise ValueError("Name cannot be empty")


@dataclass  
class HierarchicalEntity(BaseEntity):
    """Base class for entities with parent-child relationships."""
    
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    def add_child(self, child_id: str) -> bool:
        """Add a child to this entity."""
        if child_id in self.children_ids:
            return False
        self.children_ids.append(child_id)
        return True
    
    def remove_child(self, child_id: str) -> bool:
        """Remove a child from this entity."""
        if child_id not in self.children_ids:
            return False
        self.children_ids.remove(child_id)
        return True
    
    def has_children(self) -> bool:
        """Check if entity has any children."""
        return len(self.children_ids) > 0
    
    def is_root(self) -> bool:
        """Check if entity is a root (no parent)."""
        return self.parent_id is None