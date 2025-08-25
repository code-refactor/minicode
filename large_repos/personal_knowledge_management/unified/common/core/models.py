"""Base models and common fields for the unified library."""

from datetime import datetime
from typing import Any, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_serializer


class BaseEntity(BaseModel):
    """Base class for all entities in the system."""
    
    model_config = ConfigDict()
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return value.isoformat()
    
    def update(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()


class TaggableEntity(BaseEntity):
    """Base class for entities that support tagging."""
    
    tags: Set[str] = Field(default_factory=set)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the entity."""
        self.tags.add(tag)
        self.update()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the entity."""
        self.tags.discard(tag)
        self.update()
    
    def has_tag(self, tag: str) -> bool:
        """Check if the entity has a specific tag."""
        return tag in self.tags


class LinkableEntity(BaseEntity):
    """Base class for entities that can be linked to others."""
    
    related_ids: Set[UUID] = Field(default_factory=set)
    
    @field_serializer('related_ids')
    def serialize_related_ids(self, value: Set[UUID]) -> list[str]:
        """Serialize UUID set to list of strings."""
        return [str(uid) for uid in value]
    
    def add_link(self, entity_id: UUID) -> None:
        """Add a link to another entity."""
        self.related_ids.add(entity_id)
        self.update()
    
    def remove_link(self, entity_id: UUID) -> None:
        """Remove a link to another entity."""
        self.related_ids.discard(entity_id)
        self.update()
    
    def is_linked_to(self, entity_id: UUID) -> bool:
        """Check if the entity is linked to another entity."""
        return entity_id in self.related_ids


class NamedEntity(BaseEntity):
    """Base class for entities with a name and description."""
    
    name: str
    description: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the entity."""
        return self.name


class HierarchicalEntity(LinkableEntity):
    """Base class for entities that can have parent-child relationships."""
    
    parent_id: Optional[UUID] = None
    child_ids: Set[UUID] = Field(default_factory=set)
    
    @field_serializer('parent_id')
    def serialize_parent_id(self, value: Optional[UUID]) -> Optional[str]:
        """Serialize parent UUID to string."""
        return str(value) if value else None
    
    @field_serializer('child_ids')
    def serialize_child_ids(self, value: Set[UUID]) -> list[str]:
        """Serialize child UUID set to list of strings."""
        return [str(uid) for uid in value]
    
    def add_child(self, child_id: UUID) -> None:
        """Add a child entity."""
        self.child_ids.add(child_id)
        self.update()
    
    def remove_child(self, child_id: UUID) -> None:
        """Remove a child entity."""
        self.child_ids.discard(child_id)
        self.update()
    
    def set_parent(self, parent_id: Optional[UUID]) -> None:
        """Set the parent entity."""
        self.parent_id = parent_id
        self.update()
    
    def has_parent(self) -> bool:
        """Check if the entity has a parent."""
        return self.parent_id is not None
    
    def has_children(self) -> bool:
        """Check if the entity has children."""
        return len(self.child_ids) > 0


class VersionedEntity(BaseEntity):
    """Base class for entities that track version history."""
    
    version: int = 1
    previous_version_id: Optional[UUID] = None
    
    @field_serializer('previous_version_id')
    def serialize_previous_version_id(self, value: Optional[UUID]) -> Optional[str]:
        """Serialize previous version UUID to string."""
        return str(value) if value else None
    
    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1
        self.update()