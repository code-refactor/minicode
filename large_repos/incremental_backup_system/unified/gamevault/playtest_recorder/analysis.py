"""
Analysis module for playtest data.

This module provides tools for analyzing playtest session data.
"""

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import numpy as np

from gamevault.models import PlaytestSession
from gamevault.playtest_recorder.storage import PlaytestStorage


class PlaytestAnalyzer:
    """
    Analyzer for playtest data.
    
    This class provides methods for extracting insights from playtest sessions.
    """
    
    def __init__(self, playtest_storage: PlaytestStorage):
        """
        Initialize the playtest analyzer.
        
        Args:
            playtest_storage: Storage manager for playtest data
        """
        self.storage = playtest_storage
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of a playtest session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict[str, Any]: Session summary
            
        Raises:
            ValueError: If the session doesn't exist
        """
        session = self.storage.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        
        # Get checkpoints
        checkpoints = self.storage.list_checkpoints(session_id)
        
        # Analyze events
        events_by_type = defaultdict(int)
        for event in session.events:
            event_type = event.get("type", "unknown")
            events_by_type[event_type] += 1
        
        # Calculate event frequency
        event_frequency = {}
        if session.duration > 0:
            for event_type, count in events_by_type.items():
                event_frequency[event_type] = count / session.duration * 60  # Events per minute
        
        return {
            "id": session.id,
            "version_id": session.version_id,
            "player_id": session.player_id,
            "timestamp": session.timestamp,
            "duration": session.duration,
            "completed": session.completed,
            "metrics": session.metrics,
            "event_count": len(session.events),
            "events_by_type": dict(events_by_type),
            "event_frequency": event_frequency,
            "checkpoint_count": len(checkpoints),
            "checkpoints": checkpoints
        }
    
    def compare_sessions(
        self,
        session_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple playtest sessions.
        
        Args:
            session_ids: List of session IDs to compare
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Raises:
            ValueError: If any session doesn't exist
        """
        sessions = []
        for session_id in session_ids:
            session = self.storage.get_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            sessions.append(session)
        
        if not sessions:
            return {"count": 0}
        
        # Gather metrics for all sessions
        metric_values: Dict[str, List[float]] = defaultdict(list)
        for session in sessions:
            for metric_name, value in session.metrics.items():
                metric_values[metric_name].append(value)
        
        # Calculate metric statistics
        metric_stats = {}
        for metric_name, values in metric_values.items():
            if values:
                metric_stats[metric_name] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "std": np.std(values),
                    "count": len(values)
                }
        
        # Gather event types across all sessions
        event_counts: Dict[str, List[int]] = defaultdict(list)
        for session in sessions:
            # Count events by type for this session
            session_counts = Counter(event.get("type", "unknown") for event in session.events)
            
            # Add to overall counts
            for event_type, count in session_counts.items():
                event_counts[event_type].append(count)
        
        # Calculate event statistics
        event_stats = {}
        for event_type, counts in event_counts.items():
            if counts:
                event_stats[event_type] = {
                    "min": min(counts),
                    "max": max(counts),
                    "mean": sum(counts) / len(counts),
                    "std": np.std(counts),
                    "count": len(counts)
                }
        
        # Gather durations
        durations = [session.duration for session in sessions]
        
        return {
            "count": len(sessions),
            "version_ids": list(set(session.version_id for session in sessions)),
            "player_ids": list(set(session.player_id for session in sessions)),
            "completed_count": sum(1 for session in sessions if session.completed),
            "duration_stats": {
                "min": min(durations),
                "max": max(durations),
                "mean": sum(durations) / len(durations),
                "std": np.std(durations)
            },
            "metric_stats": metric_stats,
            "event_stats": event_stats,
            "total_events": sum(len(session.events) for session in sessions)
        }
    
    def get_version_statistics(
        self,
        version_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics for all playtest sessions of a game version.
        
        Args:
            version_id: ID of the game version
            
        Returns:
            Dict[str, Any]: Version statistics
        """
        # Get all sessions for this version
        sessions = self.storage.list_sessions(version_id=version_id)
        
        if not sessions:
            return {
                "version_id": version_id,
                "session_count": 0
            }
        
        # Count unique players
        player_ids = set(session["player_id"] for session in sessions)
        
        # Calculate completion rate
        completed_count = sum(1 for session in sessions if session["completed"])
        completion_rate = completed_count / len(sessions) if sessions else 0
        
        # Gather durations
        durations = [session["duration"] for session in sessions]
        
        # Aggregate metrics
        metric_values: Dict[str, List[float]] = defaultdict(list)
        for session in sessions:
            for metric_name, value in session["metrics"].items():
                metric_values[metric_name].append(value)
        
        # Calculate metric statistics
        metric_stats = {}
        for metric_name, values in metric_values.items():
            if values:
                metric_stats[metric_name] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "std": np.std(values),
                    "count": len(values)
                }
        
        return {
            "version_id": version_id,
            "session_count": len(sessions),
            "player_count": len(player_ids),
            "completed_count": completed_count,
            "completion_rate": completion_rate,
            "duration_stats": {
                "min": min(durations) if durations else 0,
                "max": max(durations) if durations else 0,
                "mean": sum(durations) / len(durations) if durations else 0,
                "std": np.std(durations) if durations else 0
            },
            "metric_stats": metric_stats,
            "checkpoint_counts": [session.get("checkpoint_count", 0) for session in sessions]
        }
    
    def compare_versions(
        self,
        version_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare playtest data across different game versions.
        
        Args:
            version_ids: List of version IDs to compare
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        version_stats = {}
        
        for version_id in version_ids:
            version_stats[version_id] = self.get_version_statistics(version_id)
        
        # Find common metrics across versions
        common_metrics = set()
        for version_id, stats in version_stats.items():
            if "metric_stats" in stats:
                if not common_metrics:
                    common_metrics = set(stats["metric_stats"].keys())
                else:
                    common_metrics &= set(stats["metric_stats"].keys())
        
        # Compare metrics across versions
        metric_comparisons = {}
        for metric_name in common_metrics:
            values = [
                stats["metric_stats"][metric_name]["mean"]
                for version_id, stats in version_stats.items()
                if "metric_stats" in stats and metric_name in stats["metric_stats"]
            ]
            
            if len(values) > 1:
                # Calculate percent change from first to last version
                percent_change = (values[-1] - values[0]) / values[0] * 100 if values[0] != 0 else 0
                
                metric_comparisons[metric_name] = {
                    "values": values,
                    "percent_change": percent_change
                }
        
        # Compare completion rates
        completion_rates = [
            stats["completion_rate"]
            for version_id, stats in version_stats.items()
        ]
        
        if len(completion_rates) > 1:
            completion_change = (completion_rates[-1] - completion_rates[0]) * 100  # Percentage points
        else:
            completion_change = 0
        
        # Compare durations
        mean_durations = [
            stats["duration_stats"]["mean"]
            for version_id, stats in version_stats.items()
            if "duration_stats" in stats
        ]
        
        if len(mean_durations) > 1 and mean_durations[0] != 0:
            duration_change = (mean_durations[-1] - mean_durations[0]) / mean_durations[0] * 100
        else:
            duration_change = 0
        
        return {
            "versions": version_ids,
            "version_stats": version_stats,
            "metric_comparisons": metric_comparisons,
            "completion_rates": completion_rates,
            "completion_change": completion_change,
            "mean_durations": mean_durations,
            "duration_change": duration_change
        }
    
    def get_player_statistics(
        self,
        player_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics for all playtest sessions of a player.
        
        Args:
            player_id: ID of the player
            
        Returns:
            Dict[str, Any]: Player statistics
        """
        # Get all sessions for this player
        sessions = self.storage.list_sessions(player_id=player_id)
        
        if not sessions:
            return {
                "player_id": player_id,
                "session_count": 0
            }
        
        # Count versions played
        version_ids = set(session["version_id"] for session in sessions)
        
        # Calculate completion rate
        completed_count = sum(1 for session in sessions if session["completed"])
        completion_rate = completed_count / len(sessions) if sessions else 0
        
        # Gather durations
        durations = [session["duration"] for session in sessions]
        
        # Aggregate metrics
        metric_values: Dict[str, List[float]] = defaultdict(list)
        for session in sessions:
            for metric_name, value in session["metrics"].items():
                metric_values[metric_name].append(value)
        
        # Calculate metric statistics
        metric_stats = {}
        for metric_name, values in metric_values.items():
            if values:
                metric_stats[metric_name] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "std": np.std(values),
                    "count": len(values)
                }
        
        # Get player progression across versions
        version_progression = []
        for version_id in sorted(version_ids, key=lambda v: min(session["timestamp"] for session in sessions if session["version_id"] == v)):
            version_sessions = [session for session in sessions if session["version_id"] == version_id]
            
            # Calculate version-specific metrics
            version_completed = sum(1 for session in version_sessions if session["completed"])
            version_duration = sum(session["duration"] for session in version_sessions)
            
            version_progression.append({
                "version_id": version_id,
                "session_count": len(version_sessions),
                "completed_count": version_completed,
                "total_duration": version_duration,
                "first_played": min(session["timestamp"] for session in version_sessions),
                "last_played": max(session["timestamp"] for session in version_sessions)
            })
        
        return {
            "player_id": player_id,
            "session_count": len(sessions),
            "version_count": len(version_ids),
            "completed_count": completed_count,
            "completion_rate": completion_rate,
            "duration_stats": {
                "min": min(durations) if durations else 0,
                "max": max(durations) if durations else 0,
                "mean": sum(durations) / len(durations) if durations else 0,
                "std": np.std(durations) if durations else 0,
                "total": sum(durations)
            },
            "metric_stats": metric_stats,
            "version_progression": version_progression,
            "first_session": min(sessions, key=lambda s: s["timestamp"]),
            "last_session": max(sessions, key=lambda s: s["timestamp"])
        }