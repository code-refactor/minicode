"""
Database module for the feedback correlation system.

This module manages the storage and retrieval of feedback data linked to game versions.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.config import get_config
from gamevault.models import FeedbackEntry


class FeedbackDatabase:
    """
    SQLite database for storing and querying feedback data.
    
    This class provides a persistent storage solution for feedback data,
    with indexing and querying capabilities.
    """
    
    def __init__(self, project_name: str, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the feedback database.
        
        Args:
            project_name: Name of the project
            storage_dir: Directory where the database will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir / "feedback" / project_name
        
        # Create the directory structure
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.db_path = self.storage_dir / "feedback.db"
        self._init_database()
    
    def _init_database(self) -> None:
        """
        Initialize the database schema.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create feedback table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER,
                resolved INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
            ''')
            
            # Create metadata table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_metadata (
                feedback_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (feedback_id, key),
                FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
            )
            ''')
            
            # Create tags table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_tags (
                feedback_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (feedback_id, tag),
                FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_version ON feedback(version_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_player ON feedback(player_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_key ON feedback_metadata(key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON feedback_tags(tag)')
            
            conn.commit()
    
    def add_feedback(self, feedback: FeedbackEntry) -> str:
        """
        Add a feedback entry to the database.
        
        Args:
            feedback: The feedback entry to add
            
        Returns:
            str: ID of the added feedback
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert feedback
            cursor.execute(
                '''
                INSERT INTO feedback (
                    id, player_id, version_id, timestamp, category, content, priority, resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    feedback.id,
                    feedback.player_id,
                    feedback.version_id,
                    feedback.timestamp,
                    feedback.category,
                    feedback.content,
                    feedback.priority,
                    1 if feedback.resolved else 0,
                    datetime.now().timestamp()
                )
            )
            
            # Insert metadata - convert non-string values to JSON strings
            for key, value in feedback.metadata.items():
                if not isinstance(value, str):
                    # Convert non-string values to JSON strings
                    value = json.dumps(value)
                cursor.execute(
                    'INSERT INTO feedback_metadata (feedback_id, key, value) VALUES (?, ?, ?)',
                    (feedback.id, key, str(value))
                )
            
            # Insert tags
            for tag in feedback.tags:
                cursor.execute(
                    'INSERT INTO feedback_tags (feedback_id, tag) VALUES (?, ?)',
                    (feedback.id, tag)
                )
            
            conn.commit()
            
            return feedback.id
    
    def update_feedback(self, feedback: FeedbackEntry) -> bool:
        """
        Update an existing feedback entry.
        
        Args:
            feedback: The updated feedback entry
            
        Returns:
            bool: True if the feedback was updated, False if it doesn't exist
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if the feedback exists
            cursor.execute('SELECT id FROM feedback WHERE id = ?', (feedback.id,))
            if cursor.fetchone() is None:
                return False
            
            # Update feedback
            cursor.execute(
                '''
                UPDATE feedback 
                SET player_id = ?, version_id = ?, timestamp = ?, category = ?, 
                    content = ?, priority = ?, resolved = ?
                WHERE id = ?
                ''',
                (
                    feedback.player_id,
                    feedback.version_id,
                    feedback.timestamp,
                    feedback.category,
                    feedback.content,
                    feedback.priority,
                    1 if feedback.resolved else 0,
                    feedback.id
                )
            )
            
            # Delete existing metadata and tags
            cursor.execute('DELETE FROM feedback_metadata WHERE feedback_id = ?', (feedback.id,))
            cursor.execute('DELETE FROM feedback_tags WHERE feedback_id = ?', (feedback.id,))
            
            # Insert new metadata - convert non-string values to JSON strings
            for key, value in feedback.metadata.items():
                if not isinstance(value, str):
                    # Convert non-string values to JSON strings
                    value = json.dumps(value)
                cursor.execute(
                    'INSERT INTO feedback_metadata (feedback_id, key, value) VALUES (?, ?, ?)',
                    (feedback.id, key, str(value))
                )
            
            # Insert new tags
            for tag in feedback.tags:
                cursor.execute(
                    'INSERT INTO feedback_tags (feedback_id, tag) VALUES (?, ?)',
                    (feedback.id, tag)
                )
            
            conn.commit()
            
            return True
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """
        Get a feedback entry by ID.
        
        Args:
            feedback_id: ID of the feedback to get
            
        Returns:
            Optional[FeedbackEntry]: The feedback entry, or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get feedback
            cursor.execute('SELECT * FROM feedback WHERE id = ?', (feedback_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            # Get metadata
            cursor.execute('SELECT key, value FROM feedback_metadata WHERE feedback_id = ?', (feedback_id,))
            metadata = {key: value for key, value in cursor.fetchall()}
            
            # Get tags
            cursor.execute('SELECT tag FROM feedback_tags WHERE feedback_id = ?', (feedback_id,))
            tags = [tag[0] for tag in cursor.fetchall()]
            
            # Create FeedbackEntry
            return FeedbackEntry(
                id=row['id'],
                player_id=row['player_id'],
                version_id=row['version_id'],
                timestamp=row['timestamp'],
                category=row['category'],
                content=row['content'],
                metadata=metadata,
                tags=tags,
                priority=row['priority'],
                resolved=bool(row['resolved'])
            )
    
    def delete_feedback(self, feedback_id: str) -> bool:
        """
        Delete a feedback entry.
        
        Args:
            feedback_id: ID of the feedback to delete
            
        Returns:
            bool: True if the feedback was deleted, False if it doesn't exist
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if the feedback exists
            cursor.execute('SELECT id FROM feedback WHERE id = ?', (feedback_id,))
            if cursor.fetchone() is None:
                return False
            
            # Delete feedback (cascade will delete metadata and tags)
            cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
            conn.commit()
            
            return True
    
    def _row_to_feedback(self, row: sqlite3.Row, include_metadata: bool = True, include_tags: bool = True) -> FeedbackEntry:
        """
        Convert a database row to a FeedbackEntry.
        
        Args:
            row: The database row
            include_metadata: Whether to include metadata
            include_tags: Whether to include tags
            
        Returns:
            FeedbackEntry: The feedback entry
        """
        metadata = {}
        tags = []
        
        if include_metadata:
            # Get metadata
            cursor = sqlite3.connect(self.db_path).cursor()
            cursor.execute('SELECT key, value FROM feedback_metadata WHERE feedback_id = ?', (row['id'],))

            metadata = {}
            for key, value in cursor.fetchall():
                # Try to parse as JSON for non-string values
                try:
                    # Check if it might be a JSON value (starts with standard JSON indicators)
                    if value.startswith(('[', '{', '"', 'true', 'false', 'null')) or value.isdigit() or value == 'true' or value == 'false':
                        parsed_value = json.loads(value)
                        metadata[key] = parsed_value
                    else:
                        metadata[key] = value
                except (json.JSONDecodeError, AttributeError):
                    # If parsing fails, keep the original string value
                    metadata[key] = value
        
        if include_tags:
            # Get tags
            cursor = sqlite3.connect(self.db_path).cursor()
            cursor.execute('SELECT tag FROM feedback_tags WHERE feedback_id = ?', (row['id'],))
            tags = [tag[0] for tag in cursor.fetchall()]
        
        # Create FeedbackEntry
        return FeedbackEntry(
            id=row['id'],
            player_id=row['player_id'],
            version_id=row['version_id'],
            timestamp=row['timestamp'],
            category=row['category'],
            content=row['content'],
            metadata=metadata,
            tags=tags,
            priority=row['priority'],
            resolved=bool(row['resolved'])
        )
    
    def list_feedback(
        self,
        version_id: Optional[str] = None,
        player_id: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include_metadata: bool = True,
        include_tags: bool = True
    ) -> List[FeedbackEntry]:
        """
        List feedback entries with optional filtering.
        
        Args:
            version_id: Filter by version ID
            player_id: Filter by player ID
            category: Filter by category
            tag: Filter by tag
            resolved: Filter by resolved status
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            include_metadata: Whether to include metadata
            include_tags: Whether to include tags
            
        Returns:
            List[FeedbackEntry]: List of feedback entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT f.* FROM feedback f'
            params = []
            
            # Add tag join if needed
            if tag is not None:
                query += ' JOIN feedback_tags t ON f.id = t.feedback_id AND t.tag = ?'
                params.append(tag)
            
            # Add WHERE clause
            where_clauses = []
            
            if version_id is not None:
                where_clauses.append('f.version_id = ?')
                params.append(version_id)
            
            if player_id is not None:
                where_clauses.append('f.player_id = ?')
                params.append(player_id)
            
            if category is not None:
                where_clauses.append('f.category = ?')
                params.append(category)
            
            if resolved is not None:
                where_clauses.append('f.resolved = ?')
                params.append(1 if resolved else 0)
            
            if where_clauses:
                query += ' WHERE ' + ' AND '.join(where_clauses)
            
            # Add ORDER BY
            query += ' ORDER BY f.timestamp DESC'
            
            # Add LIMIT and OFFSET
            if limit is not None:
                query += ' LIMIT ?'
                params.append(limit)
            
            if offset is not None:
                query += ' OFFSET ?'
                params.append(offset)
            
            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert rows to FeedbackEntry objects
            return [self._row_to_feedback(row, include_metadata, include_tags) for row in rows]
    
    def count_feedback(
        self,
        version_id: Optional[str] = None,
        player_id: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> int:
        """
        Count feedback entries with optional filtering.
        
        Args:
            version_id: Filter by version ID
            player_id: Filter by player ID
            category: Filter by category
            tag: Filter by tag
            resolved: Filter by resolved status
            
        Returns:
            int: Number of matching feedback entries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT COUNT(*) FROM feedback f'
            params = []
            
            # Add tag join if needed
            if tag is not None:
                query += ' JOIN feedback_tags t ON f.id = t.feedback_id AND t.tag = ?'
                params.append(tag)
            
            # Add WHERE clause
            where_clauses = []
            
            if version_id is not None:
                where_clauses.append('f.version_id = ?')
                params.append(version_id)
            
            if player_id is not None:
                where_clauses.append('f.player_id = ?')
                params.append(player_id)
            
            if category is not None:
                where_clauses.append('f.category = ?')
                params.append(category)
            
            if resolved is not None:
                where_clauses.append('f.resolved = ?')
                params.append(1 if resolved else 0)
            
            if where_clauses:
                query += ' WHERE ' + ' AND '.join(where_clauses)
            
            # Execute query
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            return count
    
    def get_feedback_by_versions(self, version_ids: List[str]) -> Dict[str, List[FeedbackEntry]]:
        """
        Get feedback entries grouped by version ID.
        
        Args:
            version_ids: List of version IDs
            
        Returns:
            Dict[str, List[FeedbackEntry]]: Dictionary of version IDs to feedback entries
        """
        result = {version_id: [] for version_id in version_ids}
        
        for version_id in version_ids:
            result[version_id] = self.list_feedback(version_id=version_id)
        
        return result
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get statistics about feedback data.
        
        Returns:
            Dict[str, Any]: Dictionary with feedback statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total count
            cursor.execute('SELECT COUNT(*) FROM feedback')
            stats['total_count'] = cursor.fetchone()[0]
            
            # Count by category
            cursor.execute('SELECT category, COUNT(*) FROM feedback GROUP BY category')
            stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Count by resolved status
            cursor.execute('SELECT resolved, COUNT(*) FROM feedback GROUP BY resolved')
            resolved_results = cursor.fetchall()
            stats['by_resolved'] = {
                'resolved': next((row[1] for row in resolved_results if row[0] == 1), 0),
                'unresolved': next((row[1] for row in resolved_results if row[0] == 0), 0)
            }
            
            # Count by tag
            cursor.execute('''
            SELECT tag, COUNT(DISTINCT feedback_id) FROM feedback_tags
            GROUP BY tag ORDER BY COUNT(DISTINCT feedback_id) DESC LIMIT 10
            ''')
            stats['top_tags'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Timeline stats (feedback per day)
            cursor.execute('''
            SELECT DATE(timestamp, 'unixepoch') as date, COUNT(*) FROM feedback
            GROUP BY date ORDER BY date
            ''')
            stats['timeline'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            return stats