"""Base models and common fields for the unified library."""

from datetime import datetime
from typing import Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base class for all entities in the system."""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def update(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


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
    
    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1
        self.update()