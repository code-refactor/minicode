"""
Data models for the study session system.
"""
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel, Field
import time
from datetime import datetime, timedelta


class StudySessionStatus(Enum):
    """Status of a study session."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TopicStatus(Enum):
    """Status of a study topic."""
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


class StudyTechnique(Enum):
    """Study techniques that can be applied."""
    POMODORO = "pomodoro"
    SPACED_REPETITION = "spaced_repetition"
    ACTIVE_RECALL = "active_recall"
    FEYNMAN_TECHNIQUE = "feynman_technique"
    MIND_MAPPING = "mind_mapping"
    INTERLEAVING = "interleaving"


class StudyTopic(BaseModel):
    """
    Represents a topic to be studied.
    """
    id: str
    name: str
    description: str
    status: TopicStatus = TopicStatus.NEW
    priority: int = 1  # 1 (highest) to 5 (lowest)
    last_studied: Optional[float] = None
    next_review: Optional[float] = None
    repetition_count: int = 0
    difficulty_rating: int = 3  # 1 (easiest) to 5 (hardest)
    mastery_level: float = 0.0  # 0.0 to 1.0
    related_topics: List[str] = Field(default_factory=list)
    notes: str = ""


class StudySessionEvent(BaseModel):
    """
    Represents an event that occurred during a study session.
    """
    timestamp: float = Field(default_factory=time.time)
    event_type: str  # "start", "pause", "resume", "end", "note", "distraction"
    details: Optional[str] = None
    duration: Optional[float] = None  # For "pause" and "distraction" events


class StudySession(BaseModel):
    """
    Represents a study session for learning.
    """
    id: str
    topics: List[str]  # List of topic IDs
    planned_start_time: float
    planned_duration_minutes: int
    actual_start_time: Optional[float] = None
    actual_end_time: Optional[float] = None
    status: StudySessionStatus = StudySessionStatus.PLANNED
    events: List[StudySessionEvent] = Field(default_factory=list)
    techniques: List[StudyTechnique] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    rating: Optional[int] = None  # 1 to 5, self-evaluation of productivity
    notes: str = ""
    
    def start(self) -> None:
        """Start the study session."""
        self.actual_start_time = time.time()
        self.status = StudySessionStatus.IN_PROGRESS
        self.events.append(
            StudySessionEvent(
                event_type="start",
                details="Session started"
            )
        )
    
    def pause(self, reason: Optional[str] = None) -> None:
        """
        Pause the study session.
        
        Args:
            reason: Reason for pausing (optional)
        """
        if self.status != StudySessionStatus.IN_PROGRESS:
            return
            
        self.events.append(
            StudySessionEvent(
                event_type="pause",
                details=reason
            )
        )
    
    def resume(self) -> None:
        """Resume the study session."""
        if self.status != StudySessionStatus.IN_PROGRESS:
            return
            
        self.events.append(
            StudySessionEvent(
                event_type="resume",
                details="Session resumed"
            )
        )
    
    def complete(self, achievements: Optional[List[str]] = None, 
                rating: Optional[int] = None) -> None:
        """
        Complete the study session.
        
        Args:
            achievements: List of achievements during the session (optional)
            rating: Self-evaluation rating (optional)
        """
        self.actual_end_time = time.time()
        self.status = StudySessionStatus.COMPLETED
        
        if achievements:
            self.achievements = achievements
            
        if rating:
            self.rating = rating
            
        self.events.append(
            StudySessionEvent(
                event_type="end",
                details="Session completed"
            )
        )
    
    def cancel(self, reason: str) -> None:
        """
        Cancel the study session.
        
        Args:
            reason: Reason for cancellation
        """
        self.status = StudySessionStatus.CANCELLED
        self.events.append(
            StudySessionEvent(
                event_type="end",
                details=f"Session cancelled: {reason}"
            )
        )
    
    def add_note(self, note: str) -> None:
        """
        Add a note to the study session.
        
        Args:
            note: The note to add
        """
        self.events.append(
            StudySessionEvent(
                event_type="note",
                details=note
            )
        )
    
    def record_distraction(self, details: Optional[str] = None, 
                          duration_seconds: Optional[float] = None) -> None:
        """
        Record a distraction during the study session.
        
        Args:
            details: Details about the distraction (optional)
            duration_seconds: Duration of the distraction in seconds (optional)
        """
        self.events.append(
            StudySessionEvent(
                event_type="distraction",
                details=details,
                duration=duration_seconds
            )
        )
    
    def get_actual_duration_minutes(self) -> float:
        """
        Get the actual duration of the study session in minutes.
        
        Returns:
            Duration in minutes, or -1 if the session hasn't ended
        """
        if not self.actual_start_time:
            return 0
            
        end_time = self.actual_end_time or time.time()
        
        # Calculate total time
        total_seconds = end_time - self.actual_start_time
        
        # Subtract pause durations
        pause_start = None
        for event in self.events:
            if event.event_type == "pause":
                pause_start = event.timestamp
            elif event.event_type == "resume" and pause_start:
                total_seconds -= (event.timestamp - pause_start)
                pause_start = None
                
        # If there's an active pause, subtract that too
        if pause_start:
            total_seconds -= (end_time - pause_start)
            
        return total_seconds / 60  # Convert to minutes
    
    def get_distractions_count(self) -> int:
        """
        Get the number of distractions during the session.
        
        Returns:
            Number of distractions
        """
        return sum(1 for event in self.events if event.event_type == "distraction")
    
    def get_distraction_time_minutes(self) -> float:
        """
        Get the total time spent on distractions in minutes.
        
        Returns:
            Total distraction time in minutes
        """
        total_seconds = sum(
            event.duration or 0
            for event in self.events
            if event.event_type == "distraction" and event.duration
        )
        
        return total_seconds / 60  # Convert to minutes
    
    def get_focus_percentage(self) -> float:
        """
        Get the percentage of time spent focused (not distracted).
        
        Returns:
            Focus percentage (0-100)
        """
        total_minutes = self.get_actual_duration_minutes()
        distraction_minutes = self.get_distraction_time_minutes()
        
        if total_minutes <= 0:
            return 0
            
        return max(0, min(100, ((total_minutes - distraction_minutes) / total_minutes) * 100))


class SpacedRepetitionAlgorithm(BaseModel):
    """
    Algorithm for calculating spaced repetition intervals.
    
    This implements a simplified version of the SM-2 algorithm used in
    spaced repetition systems like Anki.
    """
    ease_factor_min: float = 1.3
    ease_factor_default: float = 2.5
    ease_factor_max: float = 4.0
    interval_min_days: int = 1
    interval_max_days: int = 365
    
    def calculate_next_review(self, topic: StudyTopic, quality: int) -> float:
        """
        Calculate the next review time for a topic.
        
        Args:
            topic: The topic to calculate for
            quality: Rating of how well the material was recalled (0-5)
            
        Returns:
            Timestamp for the next review
        """
        # Initialize values for new topics
        if topic.next_review is None:
            ease_factor = self.ease_factor_default
            interval_days = self.interval_min_days
            repetition_count = 0
        else:
            # Use existing values for topics that have been reviewed before
            ease_factor = 2.5  # This would be stored with the topic in a real implementation
            repetition_count = topic.repetition_count
            
            # Calculate interval based on repetition count
            if repetition_count == 0:
                interval_days = 1
            elif repetition_count == 1:
                interval_days = 6
            else:
                # This is a simplification; real SM-2 uses more complex calculations
                last_interval = (topic.next_review - topic.last_studied) / 86400  # Convert to days
                interval_days = int(last_interval * ease_factor)
        
        # Adjust ease factor based on quality
        ease_factor = max(
            self.ease_factor_min,
            min(
                self.ease_factor_max,
                ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            )
        )
        
        # Failed recall (quality < 3) means start over
        if quality < 3:
            interval_days = self.interval_min_days
            repetition_count = 0
        else:
            repetition_count += 1
            
        # Cap the interval
        interval_days = min(self.interval_max_days, max(self.interval_min_days, interval_days))
        
        # Calculate next review time
        next_review = time.time() + (interval_days * 86400)  # Convert days to seconds
        
        return next_review


class StudySchedule(BaseModel):
    """
    Represents a schedule of study sessions.
    """
    sessions: Dict[str, StudySession] = Field(default_factory=dict)
    spaced_repetition: SpacedRepetitionAlgorithm = Field(default_factory=SpacedRepetitionAlgorithm)
    
    def add_session(self, session: StudySession) -> None:
        """
        Add a session to the schedule.
        
        Args:
            session: The session to add
        """
        self.sessions[session.id] = session
    
    def get_session(self, session_id: str) -> Optional[StudySession]:
        """
        Get a specific session by ID.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            The StudySession object, or None if not found
        """
        return self.sessions.get(session_id)
    
    def get_upcoming_sessions(self, days: int = 7) -> List[StudySession]:
        """
        Get upcoming sessions within the specified number of days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming StudySession objects
        """
        now = time.time()
        cutoff = now + (days * 86400)  # Convert days to seconds
        
        return [
            session for session in self.sessions.values()
            if session.status == StudySessionStatus.PLANNED
            and now <= session.planned_start_time <= cutoff
        ]
    
    def get_past_sessions(self, days: int = 30) -> List[StudySession]:
        """
        Get past sessions within the specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of past StudySession objects
        """
        now = time.time()
        cutoff = now - (days * 86400)  # Convert days to seconds
        
        return [
            session for session in self.sessions.values()
            if (session.status == StudySessionStatus.COMPLETED or
                session.status == StudySessionStatus.CANCELLED)
            and session.planned_start_time >= cutoff
        ]
    
    def reschedule_session(self, session_id: str, new_start_time: float) -> bool:
        """
        Reschedule a session to a new time.
        
        Args:
            session_id: ID of the session to reschedule
            new_start_time: New start time (timestamp)
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session or session.status != StudySessionStatus.PLANNED:
            return False
            
        session.planned_start_time = new_start_time
        return True
    
    def cancel_session(self, session_id: str, reason: str) -> bool:
        """
        Cancel a session.
        
        Args:
            session_id: ID of the session to cancel
            reason: Reason for cancellation
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session or session.status != StudySessionStatus.PLANNED:
            return False
            
        session.cancel(reason)
        return True
    
    def calculate_next_review(self, topic: StudyTopic, quality: int) -> float:
        """
        Calculate the next review time for a topic.
        
        Args:
            topic: The topic to calculate for
            quality: Rating of how well the material was recalled (0-5)
            
        Returns:
            Timestamp for the next review
        """
        return self.spaced_repetition.calculate_next_review(topic, quality)