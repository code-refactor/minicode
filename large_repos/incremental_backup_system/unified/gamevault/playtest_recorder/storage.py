"""
Storage module for playtest data.

This module handles the storage and retrieval of playtest session data.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.config import get_config
from gamevault.models import PlaytestSession
from gamevault.utils import compress_data, decompress_data, generate_timestamp


class PlaytestStorage:
    """
    Storage manager for playtest data.
    
    This class handles the persistence of playtest session data,
    including game states and event records.
    """
    
    def __init__(self, project_name: str, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the playtest storage.
        
        Args:
            project_name: Name of the project
            storage_dir: Directory where playtest data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir / "playtest" / project_name
        
        # Create the directory structure
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Subdirectories for different data types
        self.sessions_dir = self.storage_dir / "sessions"
        self.checkpoints_dir = self.storage_dir / "checkpoints"
        
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.checkpoints_dir, exist_ok=True)
        
        # Database for indexing and querying
        self.db_path = self.storage_dir / "playtest.db"
        self._init_database()
    
    def _init_database(self) -> None:
        """
        Initialize the database schema.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                duration REAL NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
            ''')
            
            # Create metrics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                session_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                PRIMARY KEY (session_id, metric_name),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            ''')
            
            # Create checkpoints table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                description TEXT,
                file_path TEXT NOT NULL,
                data_size INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_version ON sessions(version_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_player ON sessions(player_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id)')
            
            conn.commit()
    
    def _get_session_path(self, session_id: str) -> Path:
        """
        Get the storage path for a session file.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Path: Path to the session file
        """
        return self.sessions_dir / f"{session_id}.json"
    
    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """
        Get the storage path for a checkpoint file.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            Path: Path to the checkpoint file
        """
        return self.checkpoints_dir / f"{checkpoint_id}.dat"
    
    def save_session(self, session: PlaytestSession) -> str:
        """
        Save a playtest session.
        
        Args:
            session: The session to save
            
        Returns:
            str: ID of the saved session
        """
        # Save session file
        session_path = self._get_session_path(session.id)
        
        with open(session_path, "w") as f:
            json.dump(session.model_dump(), f, indent=2)
        
        # Add to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert or update session
            cursor.execute(
                '''
                INSERT OR REPLACE INTO sessions (
                    id, version_id, player_id, timestamp, duration, completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    session.id,
                    session.version_id,
                    session.player_id,
                    session.timestamp,
                    session.duration,
                    1 if session.completed else 0,
                    generate_timestamp()
                )
            )
            
            # Delete existing metrics
            cursor.execute('DELETE FROM metrics WHERE session_id = ?', (session.id,))
            
            # Insert metrics
            for metric_name, metric_value in session.metrics.items():
                cursor.execute(
                    'INSERT INTO metrics (session_id, metric_name, metric_value) VALUES (?, ?, ?)',
                    (session.id, metric_name, metric_value)
                )
            
            conn.commit()
        
        return session.id
    
    def get_session(self, session_id: str) -> Optional[PlaytestSession]:
        """
        Get a playtest session by ID.
        
        Args:
            session_id: ID of the session to get
            
        Returns:
            Optional[PlaytestSession]: The session, or None if not found
        """
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            return None
        
        with open(session_path, "r") as f:
            session_data = json.load(f)
        
        return PlaytestSession.model_validate(session_data)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a playtest session.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            bool: True if the session was deleted, False if it doesn't exist
        """
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            return False
        
        # Delete session file
        os.remove(session_path)
        
        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get checkpoint IDs
            cursor.execute('SELECT id FROM checkpoints WHERE session_id = ?', (session_id,))
            checkpoint_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete session (cascades to metrics and checkpoints)
            cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
            
            conn.commit()
        
        # Delete checkpoint files
        for checkpoint_id in checkpoint_ids:
            checkpoint_path = self._get_checkpoint_path(checkpoint_id)
            if checkpoint_path.exists():
                os.remove(checkpoint_path)
        
        return True
    
    def list_sessions(
        self,
        version_id: Optional[str] = None,
        player_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        completed: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List playtest sessions with optional filtering.
        
        Args:
            version_id: Filter by version ID
            player_id: Filter by player ID
            start_time: Filter by minimum timestamp
            end_time: Filter by maximum timestamp
            completed: Filter by completed status
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            
        Returns:
            List[Dict[str, Any]]: List of session metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            query = 'SELECT * FROM sessions'
            params = []
            
            # Add WHERE clause
            where_clauses = []
            
            if version_id is not None:
                where_clauses.append('version_id = ?')
                params.append(version_id)
            
            if player_id is not None:
                where_clauses.append('player_id = ?')
                params.append(player_id)
            
            if start_time is not None:
                where_clauses.append('timestamp >= ?')
                params.append(start_time)
            
            if end_time is not None:
                where_clauses.append('timestamp <= ?')
                params.append(end_time)
            
            if completed is not None:
                where_clauses.append('completed = ?')
                params.append(1 if completed else 0)
            
            if where_clauses:
                query += ' WHERE ' + ' AND '.join(where_clauses)
            
            # Add ORDER BY
            query += ' ORDER BY timestamp DESC'
            
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
            
            # Convert rows to dictionaries
            sessions = []
            for row in rows:
                session_dict = dict(row)
                
                # Get metrics
                cursor.execute('SELECT metric_name, metric_value FROM metrics WHERE session_id = ?', (row['id'],))
                metrics = {name: value for name, value in cursor.fetchall()}
                session_dict['metrics'] = metrics
                
                # Get checkpoint count
                cursor.execute('SELECT COUNT(*) FROM checkpoints WHERE session_id = ?', (row['id'],))
                session_dict['checkpoint_count'] = cursor.fetchone()[0]
                
                sessions.append(session_dict)
            
            return sessions
    
    def save_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
        data: bytes,
        description: Optional[str] = None
    ) -> str:
        """
        Save a game state checkpoint.
        
        Args:
            session_id: ID of the session this checkpoint belongs to
            checkpoint_id: ID of the checkpoint
            data: Binary checkpoint data
            description: Optional description of the checkpoint
            
        Returns:
            str: ID of the saved checkpoint
            
        Raises:
            ValueError: If the session doesn't exist
        """
        # Check if the session exists
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM sessions WHERE id = ?', (session_id,))
            if cursor.fetchone() is None:
                raise ValueError(f"Session {session_id} not found")
        
        # Compress the data
        compressed_data = compress_data(data)
        
        # Save checkpoint file
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)
        
        with open(checkpoint_path, "wb") as f:
            f.write(compressed_data)
        
        # Add to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                INSERT OR REPLACE INTO checkpoints (
                    id, session_id, timestamp, description, file_path, data_size
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    checkpoint_id,
                    session_id,
                    generate_timestamp(),
                    description,
                    str(checkpoint_path),
                    len(data)
                )
            )
            
            conn.commit()
        
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Get a checkpoint by ID.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            Optional[Tuple[bytes, Dict[str, Any]]]: Tuple of (checkpoint data, metadata), 
                                                 or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM checkpoints WHERE id = ?', (checkpoint_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            checkpoint_path = Path(row['file_path'])
            
            if not checkpoint_path.exists():
                return None
            
            with open(checkpoint_path, "rb") as f:
                compressed_data = f.read()
                data = decompress_data(compressed_data)
            
            metadata = dict(row)
            del metadata['file_path']  # Don't expose internal file path
            
            return data, metadata
    
    def list_checkpoints(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            List[Dict[str, Any]]: List of checkpoint metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT id, timestamp, description, data_size FROM checkpoints WHERE session_id = ? ORDER BY timestamp',
                (session_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def add_event_to_session(self, session_id: str, event: Dict[str, Any]) -> bool:
        """
        Add an event to a session's event list.
        
        Args:
            session_id: ID of the session
            event: Event data
            
        Returns:
            bool: True if the event was added, False if the session doesn't exist
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        # Add event to the session
        session.events.append(event)
        
        # Save the updated session
        self.save_session(session)
        
        return True
    
    def update_session_metrics(self, session_id: str, metrics: Dict[str, float]) -> bool:
        """
        Update metrics for a session.
        
        Args:
            session_id: ID of the session
            metrics: Dictionary of metric names to values
            
        Returns:
            bool: True if metrics were updated, False if the session doesn't exist
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        # Update metrics
        session.metrics.update(metrics)
        
        # Save the updated session
        self.save_session(session)
        
        return True
    
    def mark_session_completed(self, session_id: str, duration: Optional[float] = None) -> bool:
        """
        Mark a session as completed.
        
        Args:
            session_id: ID of the session
            duration: Final duration of the session. If None, calculated from timestamp.
            
        Returns:
            bool: True if the session was updated, False if it doesn't exist
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        # Update completion status and duration
        session.completed = True
        
        if duration is not None:
            session.duration = duration
        else:
            # Calculate duration based on start time and current time
            current_time = generate_timestamp()
            session.duration = current_time - session.timestamp
        
        # Save the updated session
        self.save_session(session)
        
        return True