"""
Playtest recorder module for GameVault.

This module provides the main interface for recording and managing playtest data.
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, BinaryIO

from gamevault.config import get_config
from gamevault.models import PlaytestSession
from gamevault.playtest_recorder.analysis import PlaytestAnalyzer
from gamevault.playtest_recorder.storage import PlaytestStorage
from gamevault.utils import generate_timestamp


class PlaytestRecorder:
    """
    Recorder for playtest sessions.
    
    This class provides tools for capturing and storing player progression,
    in-game states, and session information.
    """
    
    def __init__(
        self,
        project_name: str,
        storage_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the playtest recorder.
        
        Args:
            project_name: Name of the project
            storage_dir: Directory where playtest data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        
        # Initialize components
        self.storage = PlaytestStorage(project_name, self.storage_dir)
        self.analyzer = PlaytestAnalyzer(self.storage)
        
        # Active sessions being recorded
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start_session(
        self,
        version_id: str,
        player_id: str,
        initial_metrics: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Start a new playtest session.
        
        Args:
            version_id: ID of the game version being tested
            player_id: ID of the player
            initial_metrics: Initial metrics for the session
            
        Returns:
            str: ID of the created session
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create session
        session = PlaytestSession(
            id=session_id,
            version_id=version_id,
            player_id=player_id,
            timestamp=generate_timestamp(),
            duration=0.0,
            completed=False,
            events=[],
            metrics=initial_metrics or {},
            checkpoint_ids=[]
        )
        
        # Save the session
        self.storage.save_session(session)
        
        # Track as an active session
        self.active_sessions[session_id] = {
            "start_time": session.timestamp,
            "events_buffer": [],
            "metrics_buffer": {},
            "event_count": 0
        }
        
        return session_id
    
    def end_session(self, session_id: str) -> bool:
        """
        End a playtest session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            bool: True if the session was ended, False if it doesn't exist
        """
        if session_id not in self.active_sessions:
            # Try to mark an inactive session as completed
            return self.storage.mark_session_completed(session_id)
        
        # Flush any buffered data
        self._flush_session_data(session_id)
        
        # Calculate final duration
        start_time = self.active_sessions[session_id]["start_time"]
        duration = generate_timestamp() - start_time
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        # Mark as completed
        return self.storage.mark_session_completed(session_id, duration)
    
    def record_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Record a gameplay event.
        
        Args:
            session_id: ID of the session
            event_type: Type of the event
            event_data: Event data
            timestamp: Time of the event. If None, uses current time.
            
        Returns:
            bool: True if the event was recorded, False if the session doesn't exist
        """
        if session_id not in self.active_sessions:
            # Try to add to an inactive session
            event = {
                "type": event_type,
                "timestamp": timestamp or generate_timestamp(),
                "data": event_data
            }
            return self.storage.add_event_to_session(session_id, event)
        
        # Add to buffer
        event = {
            "type": event_type,
            "timestamp": timestamp or generate_timestamp(),
            "data": event_data
        }
        self.active_sessions[session_id]["events_buffer"].append(event)
        self.active_sessions[session_id]["event_count"] += 1
        
        # Flush if buffer is large
        if len(self.active_sessions[session_id]["events_buffer"]) >= 100:
            self._flush_session_data(session_id)
        
        return True
    
    def update_metrics(
        self,
        session_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Update session metrics.
        
        Args:
            session_id: ID of the session
            metrics: Metrics to update
            
        Returns:
            bool: True if metrics were updated, False if the session doesn't exist
        """
        if session_id not in self.active_sessions:
            # Try to update an inactive session
            return self.storage.update_session_metrics(session_id, metrics)
        
        # Update buffer
        self.active_sessions[session_id]["metrics_buffer"].update(metrics)
        
        # Flush if this is a substantial update
        if len(self.active_sessions[session_id]["metrics_buffer"]) >= 10:
            self._flush_session_data(session_id)
        
        return True
    
    def save_checkpoint(
        self,
        session_id: str,
        data: bytes,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Save a game state checkpoint.
        
        Args:
            session_id: ID of the session
            data: Binary checkpoint data
            description: Optional description of the checkpoint
            
        Returns:
            Optional[str]: ID of the saved checkpoint, or None if the session doesn't exist
        """
        if session_id not in self.active_sessions and not self._session_exists(session_id):
            return None
        
        # Generate checkpoint ID
        checkpoint_id = str(uuid.uuid4())
        
        # Flush any buffered data for the session
        if session_id in self.active_sessions:
            self._flush_session_data(session_id)
        
        try:
            # Save the checkpoint
            self.storage.save_checkpoint(session_id, checkpoint_id, data, description)
            
            # Add to session's checkpoint list
            session = self.storage.get_session(session_id)
            if session:
                session.checkpoint_ids.append(checkpoint_id)
                self.storage.save_session(session)
            
            return checkpoint_id
        
        except ValueError:
            return None
    
    def get_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Get a checkpoint by ID.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            Optional[Tuple[bytes, Dict[str, Any]]]: Tuple of (checkpoint data, metadata), 
                                                 or None if not found
        """
        return self.storage.get_checkpoint(checkpoint_id)
    
    def _session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: ID of the session
            
        Returns:
            bool: True if the session exists
        """
        return self.storage.get_session(session_id) is not None
    
    def _flush_session_data(self, session_id: str) -> None:
        """
        Flush buffered session data to storage.
        
        Args:
            session_id: ID of the session
        """
        if session_id not in self.active_sessions:
            return
        
        session = self.storage.get_session(session_id)
        if not session:
            # Session was deleted, remove from active sessions
            del self.active_sessions[session_id]
            return
        
        # Add buffered events
        events_buffer = self.active_sessions[session_id]["events_buffer"]
        if events_buffer:
            session.events.extend(events_buffer)
            self.active_sessions[session_id]["events_buffer"] = []
        
        # Update metrics
        metrics_buffer = self.active_sessions[session_id]["metrics_buffer"]
        if metrics_buffer:
            session.metrics.update(metrics_buffer)
            self.active_sessions[session_id]["metrics_buffer"] = {}
        
        # Update duration
        current_time = generate_timestamp()
        start_time = self.active_sessions[session_id]["start_time"]
        session.duration = current_time - start_time
        
        # Save the updated session
        self.storage.save_session(session)
    
    def get_session(self, session_id: str) -> Optional[PlaytestSession]:
        """
        Get a playtest session by ID.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Optional[PlaytestSession]: The session, or None if not found
        """
        # Flush if active
        if session_id in self.active_sessions:
            self._flush_session_data(session_id)
        
        return self.storage.get_session(session_id)
    
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
        # Flush all active sessions
        for session_id in list(self.active_sessions.keys()):
            self._flush_session_data(session_id)
        
        return self.storage.list_sessions(
            version_id=version_id,
            player_id=player_id,
            start_time=start_time,
            end_time=end_time,
            completed=completed,
            limit=limit,
            offset=offset
        )
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a playtest session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            bool: True if the session was deleted, False if it doesn't exist
        """
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return self.storage.delete_session(session_id)
    
    def get_analyzer(self) -> PlaytestAnalyzer:
        """
        Get the playtest analyzer.
        
        Returns:
            PlaytestAnalyzer: The analyzer instance
        """
        return self.analyzer