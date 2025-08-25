"""
Study session manager for the text editor.
"""
from typing import Dict, List, Set, Optional, Any, Tuple
from pydantic import BaseModel, Field
import time
import uuid
from datetime import datetime, timedelta

from text_editor.study.models import (
    StudyTopic,
    StudySession,
    StudySessionStatus,
    StudySessionEvent,
    TopicStatus,
    StudyTechnique,
    StudySchedule,
    SpacedRepetitionAlgorithm
)


class StudyManager(BaseModel):
    """
    Manages the study session system.
    
    This class provides functionality for scheduling and tracking study sessions,
    managing topics using spaced repetition, and analyzing learning effectiveness.
    """
    topics: Dict[str, StudyTopic] = Field(default_factory=dict)
    schedule: StudySchedule = Field(default_factory=StudySchedule)
    active_session_id: Optional[str] = None
    
    def create_topic(self, name: str, description: str, priority: int = 3,
                    difficulty: int = 3, related_topics: List[str] = None) -> StudyTopic:
        """
        Create a new study topic.
        
        Args:
            name: Name of the topic
            description: Description of the topic
            priority: Priority level (1-5, lower is higher priority)
            difficulty: Difficulty level (1-5, higher is more difficult)
            related_topics: List of related topic IDs (optional)
            
        Returns:
            The created StudyTopic object
        """
        # Generate a unique ID
        topic_id = f"topic_{uuid.uuid4().hex[:8]}"
        
        # Create the topic
        topic = StudyTopic(
            id=topic_id,
            name=name,
            description=description,
            priority=priority,
            difficulty_rating=difficulty,
            related_topics=related_topics or []
        )
        
        # Add to topics dictionary
        self.topics[topic_id] = topic
        
        return topic
    
    def get_topic(self, topic_id: str) -> Optional[StudyTopic]:
        """
        Get a specific topic by ID.
        
        Args:
            topic_id: ID of the topic to retrieve
            
        Returns:
            The StudyTopic object, or None if not found
        """
        return self.topics.get(topic_id)
    
    def get_all_topics(self) -> List[StudyTopic]:
        """
        Get all topics.
        
        Returns:
            List of all StudyTopic objects
        """
        return list(self.topics.values())
    
    def update_topic_status(self, topic_id: str, status: TopicStatus) -> bool:
        """
        Update the status of a topic.
        
        Args:
            topic_id: ID of the topic to update
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return False
            
        topic.status = status
        return True
    
    def update_topic_mastery(self, topic_id: str, mastery_level: float) -> bool:
        """
        Update the mastery level of a topic.
        
        Args:
            topic_id: ID of the topic to update
            mastery_level: New mastery level (0.0 to 1.0)
            
        Returns:
            True if successful, False otherwise
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return False
            
        topic.mastery_level = max(0.0, min(1.0, mastery_level))
        
        # Update status based on mastery level
        if topic.mastery_level >= 0.9:
            topic.status = TopicStatus.MASTERED
        elif topic.mastery_level >= 0.5:
            topic.status = TopicStatus.REVIEWING
        elif topic.mastery_level > 0.0:
            topic.status = TopicStatus.LEARNING
            
        return True
    
    def record_topic_studied(self, topic_id: str, quality: int) -> bool:
        """
        Record that a topic was studied and calculate the next review time.
        
        Args:
            topic_id: ID of the topic that was studied
            quality: Rating of how well the material was recalled (0-5)
            
        Returns:
            True if successful, False otherwise
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return False
            
        # Update topic properties
        topic.last_studied = time.time()
        topic.repetition_count += 1
        
        # Calculate mastery level based on quality
        mastery_delta = (quality - 2.5) / 10  # -0.25 to +0.25
        new_mastery = topic.mastery_level + mastery_delta
        topic.mastery_level = max(0.0, min(1.0, new_mastery))
        
        # Update status based on mastery level
        if topic.mastery_level >= 0.9:
            topic.status = TopicStatus.MASTERED
        elif topic.mastery_level >= 0.5:
            topic.status = TopicStatus.REVIEWING
        else:
            topic.status = TopicStatus.LEARNING
            
        # Calculate next review time
        topic.next_review = self.schedule.calculate_next_review(topic, quality)
        
        return True
    
    def create_session(self, topics: List[str], start_time: float,
                      duration_minutes: int, goals: List[str] = None,
                      techniques: List[StudyTechnique] = None) -> StudySession:
        """
        Create a new study session.
        
        Args:
            topics: List of topic IDs to study
            start_time: Planned start time (timestamp)
            duration_minutes: Planned duration in minutes
            goals: List of goals for the session (optional)
            techniques: List of study techniques to use (optional)
            
        Returns:
            The created StudySession object
        """
        # Generate a unique ID
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Create the session
        session = StudySession(
            id=session_id,
            topics=topics,
            planned_start_time=start_time,
            planned_duration_minutes=duration_minutes,
            goals=goals or [],
            techniques=techniques or []
        )
        
        # Add to schedule
        self.schedule.add_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[StudySession]:
        """
        Get a specific session by ID.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            The StudySession object, or None if not found
        """
        return self.schedule.get_session(session_id)
    
    def get_upcoming_sessions(self, days: int = 7) -> List[StudySession]:
        """
        Get upcoming sessions within the specified number of days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming StudySession objects
        """
        return self.schedule.get_upcoming_sessions(days)
    
    def get_past_sessions(self, days: int = 30) -> List[StudySession]:
        """
        Get past sessions within the specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of past StudySession objects
        """
        return self.schedule.get_past_sessions(days)
    
    def start_session(self, session_id: str) -> bool:
        """
        Start a study session.
        
        Args:
            session_id: ID of the session to start
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session or session.status != StudySessionStatus.PLANNED:
            return False
            
        # Check if another session is already active
        if self.active_session_id:
            return False
            
        # Start the session
        session.start()
        self.active_session_id = session_id
        
        return True
    
    def complete_session(self, achievements: Optional[List[str]] = None,
                         rating: Optional[int] = None) -> bool:
        """
        Complete the active study session.
        
        Args:
            achievements: List of achievements during the session (optional)
            rating: Self-evaluation rating (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.active_session_id:
            return False
            
        session = self.get_session(self.active_session_id)
        if not session:
            self.active_session_id = None
            return False
            
        # Complete the session
        session.complete(achievements, rating)
        
        # Update topics
        for topic_id in session.topics:
            topic = self.get_topic(topic_id)
            if topic:
                # Use the session rating as a proxy for recall quality
                quality = rating or 3
                self.record_topic_studied(topic_id, quality)
                
        # Clear active session
        self.active_session_id = None
        
        return True
    
    def pause_session(self, reason: Optional[str] = None) -> bool:
        """
        Pause the active study session.
        
        Args:
            reason: Reason for pausing (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.active_session_id:
            return False
            
        session = self.get_session(self.active_session_id)
        if not session:
            self.active_session_id = None
            return False
            
        session.pause(reason)
        return True
    
    def resume_session(self) -> bool:
        """
        Resume the active study session.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.active_session_id:
            return False
            
        session = self.get_session(self.active_session_id)
        if not session:
            self.active_session_id = None
            return False
            
        session.resume()
        return True
    
    def add_note_to_session(self, note: str) -> bool:
        """
        Add a note to the active study session.
        
        Args:
            note: The note to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.active_session_id:
            return False
            
        session = self.get_session(self.active_session_id)
        if not session:
            self.active_session_id = None
            return False
            
        session.add_note(note)
        return True
    
    def record_distraction(self, details: Optional[str] = None,
                          duration_seconds: Optional[float] = None) -> bool:
        """
        Record a distraction during the active study session.
        
        Args:
            details: Details about the distraction (optional)
            duration_seconds: Duration of the distraction in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.active_session_id:
            return False
            
        session = self.get_session(self.active_session_id)
        if not session:
            self.active_session_id = None
            return False
            
        session.record_distraction(details, duration_seconds)
        return True
    
    def get_active_session(self) -> Optional[StudySession]:
        """
        Get the currently active study session.
        
        Returns:
            The active StudySession object, or None if no session is active
        """
        if not self.active_session_id:
            return None
            
        return self.get_session(self.active_session_id)
    
    def get_topics_due_for_review(self) -> List[StudyTopic]:
        """
        Get topics that are due for review.
        
        Returns:
            List of StudyTopic objects due for review
        """
        now = time.time()
        
        return [
            topic for topic in self.topics.values()
            if topic.next_review and topic.next_review <= now
            and topic.status != TopicStatus.MASTERED
        ]
    
    def generate_study_plan(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate a study plan for the specified number of days.
        
        Args:
            days: Number of days to plan for
            
        Returns:
            Dictionary mapping dates to lists of study activities
        """
        plan = {}
        now = time.time()
        
        # Get topics due for review
        due_topics = self.get_topics_due_for_review()
        
        # Get upcoming sessions
        upcoming_sessions = self.get_upcoming_sessions(days)
        
        # Generate plan for each day
        for day in range(days):
            date = datetime.fromtimestamp(now + day * 86400)
            date_str = date.strftime("%Y-%m-%d")
            
            day_plan = []
            
            # Add scheduled sessions
            for session in upcoming_sessions:
                session_date = datetime.fromtimestamp(session.planned_start_time)
                if session_date.strftime("%Y-%m-%d") == date_str:
                    session_topics = [
                        self.get_topic(topic_id).name
                        for topic_id in session.topics
                        if self.get_topic(topic_id)
                    ]
                    
                    day_plan.append({
                        "type": "scheduled_session",
                        "id": session.id,
                        "time": session_date.strftime("%H:%M"),
                        "duration_minutes": session.planned_duration_minutes,
                        "topics": session_topics,
                        "goals": session.goals
                    })
            
            # Add topics due for review
            for topic in due_topics:
                if topic.next_review:
                    review_date = datetime.fromtimestamp(topic.next_review)
                    if review_date.strftime("%Y-%m-%d") == date_str:
                        day_plan.append({
                            "type": "review",
                            "topic_id": topic.id,
                            "topic_name": topic.name,
                            "status": topic.status.value,
                            "priority": topic.priority
                        })
            
            # Sort the day's plan by time
            day_plan.sort(key=lambda x: x.get("time", "00:00"))
            
            plan[date_str] = day_plan
            
        return plan
    
    def get_study_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics about study sessions and progress.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with analytics data
        """
        past_sessions = self.schedule.get_past_sessions(days)
        
        # Calculate total study time
        total_minutes = sum(
            session.get_actual_duration_minutes()
            for session in past_sessions
            if session.status == StudySessionStatus.COMPLETED
        )
        
        # Calculate average session length
        completed_sessions = [
            session for session in past_sessions
            if session.status == StudySessionStatus.COMPLETED
        ]
        
        avg_session_minutes = (
            total_minutes / len(completed_sessions)
            if completed_sessions else 0
        )
        
        # Calculate completion rate
        all_sessions = [
            session for session in past_sessions
            if session.status in [StudySessionStatus.COMPLETED, StudySessionStatus.CANCELLED]
        ]
        
        completion_rate = (
            len(completed_sessions) / len(all_sessions) * 100
            if all_sessions else 0
        )
        
        # Calculate average focus percentage
        avg_focus = (
            sum(session.get_focus_percentage() for session in completed_sessions) / len(completed_sessions)
            if completed_sessions else 0
        )
        
        # Calculate topic progress
        topic_progress = {}
        for topic in self.topics.values():
            if topic.last_studied and topic.last_studied >= time.time() - days * 86400:
                topic_progress[topic.name] = {
                    "status": topic.status.value,
                    "mastery_level": topic.mastery_level,
                    "repetition_count": topic.repetition_count
                }
                
        # Most studied topics
        topic_count = {}
        for session in completed_sessions:
            for topic_id in session.topics:
                topic = self.get_topic(topic_id)
                if topic:
                    topic_count[topic.name] = topic_count.get(topic.name, 0) + 1
                    
        most_studied = sorted(
            topic_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "total_study_time_hours": total_minutes / 60,
            "average_session_length_minutes": avg_session_minutes,
            "completed_sessions": len(completed_sessions),
            "cancelled_sessions": len(all_sessions) - len(completed_sessions),
            "completion_rate_percent": completion_rate,
            "average_focus_percent": avg_focus,
            "topic_progress": topic_progress,
            "most_studied_topics": most_studied
        }
    
    def get_next_topics_to_study(self, count: int = 5) -> List[StudyTopic]:
        """
        Get a recommendation of which topics to study next.
        
        Args:
            count: Number of topics to recommend
            
        Returns:
            List of recommended StudyTopic objects
        """
        # Get topics due for review
        due_topics = self.get_topics_due_for_review()
        
        # Sort by priority and status
        def sort_key(topic):
            # Lower priority number means higher priority
            priority_score = topic.priority
            
            # Status multiplier
            status_multiplier = {
                TopicStatus.NEW: 0.9,
                TopicStatus.LEARNING: 1.0,
                TopicStatus.REVIEWING: 1.5,
                TopicStatus.MASTERED: 5.0
            }
            
            # Next review time factors in if available
            time_factor = 0
            if topic.next_review:
                # How overdue is the review (in days)
                overdue_days = max(0, (time.time() - topic.next_review) / 86400)
                time_factor = min(5, overdue_days)  # Cap at 5 days overdue
                
            # Lower score means higher recommendation priority
            return (priority_score * status_multiplier.get(topic.status, 1.0)) - time_factor
            
        # Sort topics by the key
        all_topics = list(self.topics.values())
        all_topics.sort(key=sort_key)
        
        # Prioritize due topics
        result = []
        due_ids = {topic.id for topic in due_topics}
        
        for topic in all_topics:
            if topic.id in due_ids:
                result.append(topic)
                if len(result) >= count:
                    break
                    
        # If we don't have enough due topics, add other topics
        if len(result) < count:
            for topic in all_topics:
                if topic.id not in due_ids:
                    result.append(topic)
                    if len(result) >= count:
                        break
                        
        return result