"""
Feedback Correlation Manager for GameVault.

This module provides the main interface for managing feedback data
and correlating it with game versions.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.config import get_config
from gamevault.feedback_system.database import FeedbackDatabase
from gamevault.models import FeedbackEntry, ProjectVersion
from gamevault.utils import generate_timestamp


class FeedbackManager:
    """
    Manager for handling feedback correlation with game versions.
    
    This class provides a high-level interface for managing feedback data
    and correlating it with game versions.
    """
    
    def __init__(
        self,
        project_name: str,
        version_tracker: Optional[VersionTracker] = None,
        storage_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the feedback manager.
        
        Args:
            project_name: Name of the project
            version_tracker: Version tracker instance. If None, a new one will be created.
            storage_dir: Directory where feedback data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        
        # Create version tracker if not provided
        self.version_tracker = version_tracker or VersionTracker(project_name, self.storage_dir)
        
        # Initialize feedback database
        self.feedback_db = FeedbackDatabase(project_name, self.storage_dir)
    
    def add_feedback(
        self,
        player_id: str,
        version_id: str,
        category: str,
        content: str,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[int] = None,
        timestamp: Optional[float] = None,
        resolved: bool = False
    ) -> FeedbackEntry:
        """
        Add a new feedback entry.
        
        Args:
            player_id: ID of the player who provided the feedback
            version_id: ID of the game version this feedback is for
            category: Category of the feedback (bug, suggestion, etc.)
            content: Actual feedback text
            metadata: Additional metadata
            tags: Tags assigned to this feedback
            priority: Priority level (if applicable)
            timestamp: Time the feedback was recorded. If None, uses current time.
            resolved: Whether the feedback item is already resolved or not
            
        Returns:
            FeedbackEntry: The created feedback entry
            
        Raises:
            ValueError: If the version doesn't exist
        """
        # Check if the version exists
        try:
            self.version_tracker.get_version(version_id)
        except FileNotFoundError:
            raise ValueError(f"Version {version_id} not found")
        
        # Create feedback entry
        feedback = FeedbackEntry(
            player_id=player_id,
            version_id=version_id,
            timestamp=timestamp or generate_timestamp(),
            category=category,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            priority=priority,
            resolved=resolved
        )
        
        # Add to database
        self.feedback_db.add_feedback(feedback)
        
        return feedback
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """
        Get a feedback entry by ID.
        
        Args:
            feedback_id: ID of the feedback to get
            
        Returns:
            Optional[FeedbackEntry]: The feedback entry, or None if not found
        """
        return self.feedback_db.get_feedback(feedback_id)
    
    def update_feedback(self, feedback: FeedbackEntry) -> bool:
        """
        Update an existing feedback entry.
        
        Args:
            feedback: The updated feedback entry
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        return self.feedback_db.update_feedback(feedback)
    
    def delete_feedback(self, feedback_id: str) -> bool:
        """
        Delete a feedback entry.
        
        Args:
            feedback_id: ID of the feedback to delete
            
        Returns:
            bool: True if the feedback was deleted, False if it doesn't exist
        """
        return self.feedback_db.delete_feedback(feedback_id)
    
    def mark_feedback_resolved(self, feedback_id: str, resolved: bool = True) -> bool:
        """
        Mark a feedback entry as resolved or unresolved.
        
        Args:
            feedback_id: ID of the feedback to update
            resolved: Whether the feedback is resolved
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        feedback = self.feedback_db.get_feedback(feedback_id)
        if feedback is None:
            return False
        
        feedback.resolved = resolved
        return self.feedback_db.update_feedback(feedback)
    
    def add_tags_to_feedback(self, feedback_id: str, tags: List[str]) -> bool:
        """
        Add tags to a feedback entry.
        
        Args:
            feedback_id: ID of the feedback to update
            tags: Tags to add
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        feedback = self.feedback_db.get_feedback(feedback_id)
        if feedback is None:
            return False
        
        # Add new tags (avoid duplicates)
        feedback.tags = list(set(feedback.tags + tags))
        return self.feedback_db.update_feedback(feedback)
    
    def remove_tags_from_feedback(self, feedback_id: str, tags: List[str]) -> bool:
        """
        Remove tags from a feedback entry.
        
        Args:
            feedback_id: ID of the feedback to update
            tags: Tags to remove
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        feedback = self.feedback_db.get_feedback(feedback_id)
        if feedback is None:
            return False
        
        # Remove tags
        feedback.tags = [tag for tag in feedback.tags if tag not in tags]
        return self.feedback_db.update_feedback(feedback)
    
    def add_metadata_to_feedback(self, feedback_id: str, metadata: Dict[str, str]) -> bool:
        """
        Add metadata to a feedback entry.
        
        Args:
            feedback_id: ID of the feedback to update
            metadata: Metadata to add
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        feedback = self.feedback_db.get_feedback(feedback_id)
        if feedback is None:
            return False
        
        # Add new metadata (overwrite existing keys)
        feedback.metadata.update(metadata)
        return self.feedback_db.update_feedback(feedback)
    
    def get_feedback_for_version(
        self,
        version_id: str,
        category: Optional[str] = None,
        resolved: Optional[bool] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """
        Get feedback entries for a specific version.
        
        Args:
            version_id: ID of the version
            category: Filter by category
            resolved: Filter by resolved status
            tag: Filter by tag
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List[FeedbackEntry]: List of feedback entries
            
        Raises:
            ValueError: If the version doesn't exist
        """
        # Check if the version exists
        try:
            self.version_tracker.get_version(version_id)
        except FileNotFoundError:
            raise ValueError(f"Version {version_id} not found")
        
        return self.feedback_db.list_feedback(
            version_id=version_id,
            category=category,
            resolved=resolved,
            tag=tag,
            limit=limit,
            offset=offset
        )
    
    def get_feedback_for_player(
        self,
        player_id: str,
        category: Optional[str] = None,
        resolved: Optional[bool] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """
        Get feedback entries for a specific player.
        
        Args:
            player_id: ID of the player
            category: Filter by category
            resolved: Filter by resolved status
            tag: Filter by tag
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List[FeedbackEntry]: List of feedback entries
        """
        return self.feedback_db.list_feedback(
            player_id=player_id,
            category=category,
            resolved=resolved,
            tag=tag,
            limit=limit,
            offset=offset
        )
    
    def search_feedback(
        self,
        query: str,
        version_id: Optional[str] = None,
        category: Optional[str] = None,
        resolved: Optional[bool] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """
        Search for feedback entries.
        
        Args:
            query: Search query
            version_id: Filter by version ID
            category: Filter by category
            resolved: Filter by resolved status
            tag: Filter by tag
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List[FeedbackEntry]: List of matching feedback entries
        """
        # Get filtered feedback
        feedback = self.feedback_db.list_feedback(
            version_id=version_id,
            category=category,
            resolved=resolved,
            tag=tag
        )
        
        # Filter by search query
        query = query.lower()
        results = [
            f for f in feedback
            if query in f.content.lower() or
               query in f.category.lower() or
               any(query in tag.lower() for tag in f.tags) or
               any(query in value.lower() for value in f.metadata.values())
        ]
        
        # Apply limit and offset
        if offset is not None:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]
        
        return results
    
    def get_feedback_history(
        self,
        version_history: List[ProjectVersion],
        category: Optional[str] = None
    ) -> Dict[str, List[FeedbackEntry]]:
        """
        Get feedback entries for a version history.
        
        Args:
            version_history: List of versions in the history
            category: Filter by category
            
        Returns:
            Dict[str, List[FeedbackEntry]]: Dictionary of version IDs to feedback entries
        """
        version_ids = [version.id for version in version_history]
        
        feedback_by_version: Dict[str, List[FeedbackEntry]] = {}
        
        for version_id in version_ids:
            feedback_by_version[version_id] = self.get_feedback_for_version(
                version_id=version_id,
                category=category
            )
        
        return feedback_by_version
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get statistics about feedback data.
        
        Returns:
            Dict[str, Any]: Dictionary with feedback statistics
        """
        return self.feedback_db.get_feedback_stats()
    
    def bulk_import_feedback(self, feedback_entries: List[FeedbackEntry]) -> int:
        """
        Import multiple feedback entries.
        
        Args:
            feedback_entries: List of feedback entries to import
            
        Returns:
            int: Number of entries imported
        """
        imported_count = 0
        
        for feedback in feedback_entries:
            try:
                self.feedback_db.add_feedback(feedback)
                imported_count += 1
            except Exception:
                # Skip entries that fail to import
                continue
        
        return imported_count