"""Abstract base classes and interfaces for the unified library."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from common.core.models import BaseEntity
from common.core.enums import ExportFormat


T = TypeVar('T', bound=BaseEntity)


class EntityManager(ABC, Generic[T]):
    """Abstract base class for entity managers."""
    
    @abstractmethod
    def add(self, entity: Union[T, List[T]]) -> List[UUID]:
        """Add one or more entities.
        
        Args:
            entity: Entity or list of entities to add.
            
        Returns:
            List of entity IDs.
        """
        pass
    
    @abstractmethod
    def get(self, entity_id: UUID) -> Optional[T]:
        """Get an entity by ID.
        
        Args:
            entity_id: The entity ID.
            
        Returns:
            The entity if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities.
        """
        pass
    
    @abstractmethod
    def update(self, entity_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update an entity.
        
        Args:
            entity_id: The entity ID.
            updates: Dictionary of field updates.
            
        Returns:
            True if updated, False if not found.
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: The entity ID.
            
        Returns:
            True if deleted, False if not found.
        """
        pass
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[T]:
        """Search for entities.
        
        Args:
            query: Search query string.
            **kwargs: Additional search parameters.
            
        Returns:
            List of matching entities.
        """
        pass
    
    @abstractmethod
    def filter(self, **criteria) -> List[T]:
        """Filter entities by criteria.
        
        Args:
            **criteria: Filter criteria as field-value pairs.
            
        Returns:
            List of matching entities.
        """
        pass


class Searchable(ABC):
    """Interface for searchable entities."""
    
    @abstractmethod
    def search(self, query: str, fields: Optional[List[str]] = None) -> List[Any]:
        """Search for items.
        
        Args:
            query: Search query.
            fields: Optional fields to search in.
            
        Returns:
            List of search results.
        """
        pass
    
    @abstractmethod
    def build_search_index(self) -> None:
        """Build or rebuild the search index."""
        pass
    
    @abstractmethod
    def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on a prefix.
        
        Args:
            prefix: Search prefix.
            limit: Maximum number of suggestions.
            
        Returns:
            List of suggestions.
        """
        pass


class Exportable(ABC):
    """Interface for exportable entities."""
    
    @abstractmethod
    def export(self, format: ExportFormat, path: Optional[Path] = None) -> Union[str, bytes, Path]:
        """Export data in the specified format.
        
        Args:
            format: Export format.
            path: Optional path to save the export.
            
        Returns:
            Exported data or path to exported file.
        """
        pass
    
    @abstractmethod
    def get_supported_export_formats(self) -> List[ExportFormat]:
        """Get list of supported export formats.
        
        Returns:
            List of supported formats.
        """
        pass


class Importable(ABC):
    """Interface for importable entities."""
    
    @abstractmethod
    def import_data(self, data: Union[str, bytes, Path], format: ExportFormat) -> int:
        """Import data from the specified format.
        
        Args:
            data: Data to import or path to import file.
            format: Import format.
            
        Returns:
            Number of items imported.
        """
        pass
    
    @abstractmethod
    def validate_import_data(self, data: Union[str, bytes, Path], format: ExportFormat) -> Dict[str, Any]:
        """Validate import data before importing.
        
        Args:
            data: Data to validate.
            format: Import format.
            
        Returns:
            Validation results.
        """
        pass


class Analyzable(ABC):
    """Interface for analyzable entities."""
    
    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """Perform analysis on the entity collection.
        
        Returns:
            Analysis results.
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical information.
        
        Returns:
            Statistics dictionary.
        """
        pass
    
    @abstractmethod
    def get_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get trends over a time period.
        
        Args:
            start_date: Start of the period.
            end_date: End of the period.
            
        Returns:
            Trends data.
        """
        pass


class Versionable(ABC):
    """Interface for versionable entities."""
    
    @abstractmethod
    def create_version(self, entity_id: UUID, message: Optional[str] = None) -> UUID:
        """Create a new version of an entity.
        
        Args:
            entity_id: The entity to version.
            message: Optional version message.
            
        Returns:
            ID of the new version.
        """
        pass
    
    @abstractmethod
    def get_version_history(self, entity_id: UUID) -> List[Dict[str, Any]]:
        """Get version history for an entity.
        
        Args:
            entity_id: The entity ID.
            
        Returns:
            List of version information.
        """
        pass
    
    @abstractmethod
    def revert_to_version(self, entity_id: UUID, version_id: UUID) -> bool:
        """Revert an entity to a previous version.
        
        Args:
            entity_id: The entity ID.
            version_id: The version to revert to.
            
        Returns:
            True if successful, False otherwise.
        """
        pass


class Taggable(ABC):
    """Interface for taggable entities."""
    
    @abstractmethod
    def add_tags(self, entity_id: UUID, tags: Union[str, List[str]]) -> bool:
        """Add tags to an entity.
        
        Args:
            entity_id: The entity ID.
            tags: Tag or list of tags to add.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def remove_tags(self, entity_id: UUID, tags: Union[str, List[str]]) -> bool:
        """Remove tags from an entity.
        
        Args:
            entity_id: The entity ID.
            tags: Tag or list of tags to remove.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_by_tags(self, tags: Union[str, List[str]], match_all: bool = False) -> List[Any]:
        """Get entities by tags.
        
        Args:
            tags: Tag or list of tags to match.
            match_all: If True, match all tags; if False, match any tag.
            
        Returns:
            List of matching entities.
        """
        pass
    
    @abstractmethod
    def get_all_tags(self) -> Dict[str, int]:
        """Get all tags with their usage count.
        
        Returns:
            Dictionary of tag to count.
        """
        pass


class Collaborative(ABC):
    """Interface for collaborative features."""
    
    @abstractmethod
    def share(self, entity_id: UUID, user_ids: List[str], permissions: Dict[str, Any]) -> bool:
        """Share an entity with other users.
        
        Args:
            entity_id: The entity to share.
            user_ids: List of user IDs to share with.
            permissions: Permission settings.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def unshare(self, entity_id: UUID, user_ids: Optional[List[str]] = None) -> bool:
        """Remove sharing for an entity.
        
        Args:
            entity_id: The entity to unshare.
            user_ids: Optional list of user IDs to unshare with.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_shared_with(self, entity_id: UUID) -> List[Dict[str, Any]]:
        """Get list of users an entity is shared with.
        
        Args:
            entity_id: The entity ID.
            
        Returns:
            List of user information with permissions.
        """
        pass
    
    @abstractmethod
    def get_shared_by_user(self, user_id: str) -> List[Any]:
        """Get entities shared by a specific user.
        
        Args:
            user_id: The user ID.
            
        Returns:
            List of shared entities.
        """
        pass


class Linkable(ABC):
    """Interface for linkable entities."""
    
    @abstractmethod
    def link(self, source_id: UUID, target_id: UUID, relationship: Optional[str] = None) -> bool:
        """Create a link between two entities.
        
        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.
            relationship: Optional relationship type.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def unlink(self, source_id: UUID, target_id: UUID) -> bool:
        """Remove a link between two entities.
        
        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.
            
        Returns:
            True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_linked_entities(self, entity_id: UUID, relationship: Optional[str] = None) -> List[Any]:
        """Get entities linked to a specific entity.
        
        Args:
            entity_id: The entity ID.
            relationship: Optional relationship type filter.
            
        Returns:
            List of linked entities.
        """
        pass
    
    @abstractmethod
    def get_link_graph(self, root_id: UUID, depth: int = 1) -> Dict[str, Any]:
        """Get a graph of linked entities.
        
        Args:
            root_id: Root entity ID.
            depth: Maximum depth to traverse.
            
        Returns:
            Graph representation of links.
        """
        pass