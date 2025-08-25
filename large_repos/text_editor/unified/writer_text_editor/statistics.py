"""Writing statistics tracking system for the writer text editor."""

from __future__ import annotations
import re
import time
import threading
import statistics
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from pydantic import BaseModel, Field
import textstat

from writer_text_editor.document import Document, Section, TextSegment


class ReadingLevel(str, Enum):
    """Different reading level metrics."""
    
    FLESCH_KINCAID_GRADE = "flesch_kincaid_grade"
    FLESCH_READING_EASE = "flesch_reading_ease"
    GUNNING_FOG = "gunning_fog"
    SMOG_INDEX = "smog_index"
    AUTOMATED_READABILITY_INDEX = "automated_readability_index"
    COLEMAN_LIAU_INDEX = "coleman_liau_index"
    DALE_CHALL_READABILITY_SCORE = "dale_chall_readability_score"
    LINSEAR_WRITE_FORMULA = "linsear_write_formula"
    SPACHE_READABILITY = "spache_readability"


class WritingPace(BaseModel):
    """Information about the writing pace."""
    
    words_per_minute: float
    words_per_hour: float
    words_per_day: float
    timestamp: datetime = Field(default_factory=datetime.now)


class WordStats(BaseModel):
    """Statistics about word usage."""
    
    total_words: int
    unique_words: int
    average_word_length: float
    most_common_words: Dict[str, int]
    vocabulary_richness: float  # Type-token ratio (unique words / total words)


class SentenceStats(BaseModel):
    """Statistics about sentence structure."""
    
    total_sentences: int
    average_sentence_length: float  # In words
    sentence_length_variance: float
    complex_sentences: int  # Sentences with multiple clauses
    sentence_types: Dict[str, int]  # Declarative, interrogative, etc.


class DocumentStats(BaseModel):
    """Overall document statistics."""
    
    word_count: int
    character_count: int
    paragraph_count: int
    sentence_count: int
    reading_level: Dict[str, float]
    word_stats: WordStats
    sentence_stats: SentenceStats
    timestamp: datetime = Field(default_factory=datetime.now)


class ProgressTracker(BaseModel):
    """Tracks progress over time."""
    
    start_date: datetime
    goal_type: str  # "word_count", "time", etc.
    goal_target: int
    goal_deadline: Optional[datetime] = None
    progress_history: List[Dict[str, Any]] = Field(default_factory=list)


class WritingStatistics:
    """Writing statistics tracking system."""
    
    def __init__(self, document: Document):
        """Initialize the writing statistics system with the given document."""
        self.document = document
        self.stats_history: List[DocumentStats] = []
        self.pace_history: List[WritingPace] = []
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self._last_word_count: int = 0
        self._last_check_time: float = time.time()
        self._background_thread: Optional[threading.Thread] = None
        self._stop_background_thread: bool = False
    
    def _count_sentences(self, text: str) -> int:
        """Count the number of sentences in the text."""
        # Simple sentence counting - this could be improved with NLP
        return len(re.findall(r'[.!?]+\s+', text)) + 1
    
    def _identify_sentence_type(self, sentence: str) -> str:
        """Identify the type of a sentence."""
        sentence = sentence.strip()
        if not sentence:
            return "unknown"
        
        if sentence.endswith('?'):
            return "interrogative"
        elif sentence.endswith('!'):
            return "exclamatory"
        elif ',' in sentence and ('but' in sentence.lower() or 'however' in sentence.lower()):
            return "complex"
        else:
            return "declarative"
    
    def _is_complex_sentence(self, sentence: str) -> bool:
        """Check if a sentence is complex (has multiple clauses)."""
        # Simple check for coordinating conjunctions and subordinating conjunctions
        coordinating_conjunctions = [
            ' and ', ' but ', ' or ', ' nor ', ' so ', ' for ', ' yet '
        ]

        subordinating_conjunctions = [
            ' because ', ' although ', ' though ', ' since ', ' unless ',
            ' if ', ' when ', ' where ', ' while '
        ]

        # Check for conjunction at beginning of sentence too
        sentence_starts = [
            'when ', 'if ', 'while ', 'because ', 'although ', 'though ',
            'since ', 'unless ', 'where '
        ]

        sentence = sentence.lower()

        # Check for any coordinating conjunctions within the sentence
        has_coordinating = any(conj in sentence for conj in coordinating_conjunctions)

        # Check for any subordinating conjunctions within the sentence
        has_subordinating = any(conj in sentence for conj in subordinating_conjunctions)

        # Check if the sentence starts with a subordinating conjunction
        starts_with_subordinating = any(sentence.startswith(start) for start in sentence_starts)

        return has_coordinating or has_subordinating or starts_with_subordinating
    
    def _calculate_vocabulary_richness(self, total_words: int, unique_words: int) -> float:
        """Calculate vocabulary richness (Type-Token Ratio)."""
        if total_words == 0:
            return 0.0
        return unique_words / total_words
    
    def calculate_stats(self) -> DocumentStats:
        """Calculate the current document statistics."""
        text = self.document.get_content()
        
        # Basic counts
        word_count = len(re.findall(r'\b\w+\b', text))
        character_count = len(text)
        paragraph_count = len(re.findall(r'\n\s*\n', text)) + 1
        
        # Split into sentences for sentence analysis
        sentences = re.split(r'[.!?]+\s+', text)
        sentence_count = len(sentences)
        
        # Analyze sentence structure
        sentence_lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences if s.strip()]
        avg_sentence_length = statistics.mean(sentence_lengths) if sentence_lengths else 0
        sentence_length_variance = statistics.variance(sentence_lengths) if len(sentence_lengths) > 1 else 0
        
        complex_sentences = sum(1 for s in sentences if self._is_complex_sentence(s))
        
        sentence_types = {}
        for s in sentences:
            if not s.strip():
                continue
            sent_type = self._identify_sentence_type(s)
            sentence_types[sent_type] = sentence_types.get(sent_type, 0) + 1
        
        # Analyze word usage
        words = re.findall(r'\b\w+\b', text.lower())
        unique_words = len(set(words))
        
        word_lengths = [len(w) for w in words]
        avg_word_length = statistics.mean(word_lengths) if word_lengths else 0
        
        # Count word frequencies
        word_frequencies = {}
        for word in words:
            if len(word) > 3:  # Ignore very short words
                word_frequencies[word] = word_frequencies.get(word, 0) + 1
        
        # Get most common words (top 20)
        most_common = dict(sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:20])
        
        # Calculate reading level metrics
        reading_level = {
            ReadingLevel.FLESCH_KINCAID_GRADE.value: textstat.flesch_kincaid_grade(text),
            ReadingLevel.FLESCH_READING_EASE.value: textstat.flesch_reading_ease(text),
            ReadingLevel.GUNNING_FOG.value: textstat.gunning_fog(text),
            ReadingLevel.SMOG_INDEX.value: textstat.smog_index(text),
            ReadingLevel.AUTOMATED_READABILITY_INDEX.value: textstat.automated_readability_index(text),
            ReadingLevel.COLEMAN_LIAU_INDEX.value: textstat.coleman_liau_index(text)
        }
        
        # Create stats objects
        word_stats = WordStats(
            total_words=word_count,
            unique_words=unique_words,
            average_word_length=avg_word_length,
            most_common_words=most_common,
            vocabulary_richness=self._calculate_vocabulary_richness(word_count, unique_words)
        )
        
        sentence_stats = SentenceStats(
            total_sentences=sentence_count,
            average_sentence_length=avg_sentence_length,
            sentence_length_variance=sentence_length_variance,
            complex_sentences=complex_sentences,
            sentence_types=sentence_types
        )
        
        document_stats = DocumentStats(
            word_count=word_count,
            character_count=character_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
            reading_level=reading_level,
            word_stats=word_stats,
            sentence_stats=sentence_stats
        )
        
        # Update history
        self.stats_history.append(document_stats)
        
        # Update last word count for pace tracking
        self._last_word_count = word_count
        
        return document_stats
    
    def calculate_writing_pace(self) -> WritingPace:
        """Calculate the current writing pace."""
        current_time = time.time()
        current_word_count = self.document.get_word_count()
        
        time_diff_seconds = current_time - self._last_check_time
        word_diff = current_word_count - self._last_word_count
        
        if time_diff_seconds <= 0:
            words_per_minute = 0.0
        else:
            # Calculate words per minute
            words_per_minute = (word_diff / time_diff_seconds) * 60
        
        # Update for next calculation
        self._last_check_time = current_time
        self._last_word_count = current_word_count
        
        # Create pace object
        pace = WritingPace(
            words_per_minute=words_per_minute,
            words_per_hour=words_per_minute * 60,
            words_per_day=words_per_minute * 60 * 24
        )
        
        # Update history
        self.pace_history.append(pace)
        
        return pace
    
    def set_progress_goal(
        self, 
        goal_id: str,
        goal_type: str, 
        target: int, 
        deadline: Optional[datetime] = None
    ) -> ProgressTracker:
        """Set a new progress goal."""
        tracker = ProgressTracker(
            start_date=datetime.now(),
            goal_type=goal_type,
            goal_target=target,
            goal_deadline=deadline
        )
        
        self.progress_trackers[goal_id] = tracker
        return tracker
    
    def update_progress(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Update the progress for a specific goal."""
        if goal_id not in self.progress_trackers:
            return None
        
        tracker = self.progress_trackers[goal_id]
        current_stats = self.calculate_stats()
        
        progress_entry = {
            "timestamp": datetime.now(),
            "word_count": current_stats.word_count,
            "goal_type": tracker.goal_type,
            "goal_target": tracker.goal_target
        }
        
        if tracker.goal_type == "word_count":
            progress_entry["progress_percentage"] = (current_stats.word_count / tracker.goal_target) * 100
            progress_entry["remaining"] = max(0, tracker.goal_target - current_stats.word_count)
        
        if tracker.goal_deadline:
            now = datetime.now()
            if now < tracker.goal_deadline:
                time_remaining = tracker.goal_deadline - now
                progress_entry["time_remaining_days"] = time_remaining.days
                
                # Estimate completion date based on current pace
                if self.pace_history and tracker.goal_type == "word_count":
                    latest_pace = self.pace_history[-1]
                    words_remaining = max(0, tracker.goal_target - current_stats.word_count)
                    
                    if latest_pace.words_per_day > 0:
                        days_needed = words_remaining / latest_pace.words_per_day
                        progress_entry["estimated_completion_date"] = now + timedelta(days=days_needed)
        
        tracker.progress_history.append(progress_entry)
        return progress_entry
    
    def get_progress_report(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a detailed progress report for a specific goal."""
        if goal_id not in self.progress_trackers:
            return None
        
        tracker = self.progress_trackers[goal_id]
        current_progress = self.update_progress(goal_id)
        
        if not current_progress or not tracker.progress_history:
            return None
        
        report = {
            "goal_id": goal_id,
            "goal_type": tracker.goal_type,
            "goal_target": tracker.goal_target,
            "start_date": tracker.start_date,
            "deadline": tracker.goal_deadline,
            "current_progress": current_progress,
            "history_summary": {
                "start_value": tracker.progress_history[0].get("word_count", 0),
                "current_value": current_progress.get("word_count", 0),
                "total_progress": current_progress.get("word_count", 0) - tracker.progress_history[0].get("word_count", 0)
            }
        }
        
        # Calculate average daily progress
        if len(tracker.progress_history) > 1:
            first_entry = tracker.progress_history[0]
            last_entry = tracker.progress_history[-1]
            
            first_time = first_entry["timestamp"]
            last_time = last_entry["timestamp"]
            
            time_diff_days = (last_time - first_time).days or 1  # Avoid division by zero
            progress_diff = last_entry.get("word_count", 0) - first_entry.get("word_count", 0)
            
            report["average_daily_progress"] = progress_diff / time_diff_days
        
        return report
    
    def start_background_tracking(self, interval_seconds: int = 60) -> None:
        """Start tracking statistics in a background thread."""
        if self._background_thread and self._background_thread.is_alive():
            return  # Already running
        
        self._stop_background_thread = False
        
        def tracking_task():
            while not self._stop_background_thread:
                try:
                    self.calculate_stats()
                    self.calculate_writing_pace()
                    
                    # Update all progress trackers
                    for goal_id in self.progress_trackers:
                        self.update_progress(goal_id)
                except Exception as e:
                    print(f"Error in background tracking: {e}")
                
                # Sleep for the specified interval
                for _ in range(interval_seconds):
                    if self._stop_background_thread:
                        break
                    time.sleep(1)
        
        self._background_thread = threading.Thread(target=tracking_task, daemon=True)
        self._background_thread.start()
    
    def stop_background_tracking(self) -> None:
        """Stop the background tracking thread."""
        self._stop_background_thread = True
        if self._background_thread:
            self._background_thread.join(timeout=5)
    
    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze trends in writing statistics over the specified number of days."""
        now = datetime.now()
        cutoff_date = now - timedelta(days=days)
        
        # Filter history to the specified time range
        recent_stats = [s for s in self.stats_history if s.timestamp >= cutoff_date]
        recent_pace = [p for p in self.pace_history if p.timestamp >= cutoff_date]
        
        if not recent_stats:
            return {"error": "Not enough data for trend analysis"}
        
        # Calculate daily word counts
        daily_word_counts = {}
        for stats in recent_stats:
            day_key = stats.timestamp.strftime("%Y-%m-%d")
            if day_key not in daily_word_counts:
                daily_word_counts[day_key] = []
            daily_word_counts[day_key].append(stats.word_count)
        
        # Get the last word count for each day
        daily_progress = {
            day: counts[-1] for day, counts in daily_word_counts.items()
        }
        
        # Calculate daily difference
        days_sorted = sorted(daily_progress.keys())
        daily_change = {}
        for i in range(1, len(days_sorted)):
            prev_day = days_sorted[i-1]
            curr_day = days_sorted[i]
            daily_change[curr_day] = daily_progress[curr_day] - daily_progress[prev_day]
        
        # Calculate reading level trends
        reading_level_trends = {}
        for level_type in ReadingLevel:
            level_values = [s.reading_level.get(level_type.value, 0) for s in recent_stats]
            if level_values:
                reading_level_trends[level_type.value] = {
                    "start": level_values[0],
                    "end": level_values[-1],
                    "change": level_values[-1] - level_values[0],
                    "average": sum(level_values) / len(level_values)
                }
        
        # Calculate pace trends
        pace_trends = {}
        if recent_pace:
            wpm_values = [p.words_per_minute for p in recent_pace]
            pace_trends["words_per_minute"] = {
                "start": wpm_values[0],
                "end": wpm_values[-1],
                "change": wpm_values[-1] - wpm_values[0],
                "average": sum(wpm_values) / len(wpm_values)
            }
        
        return {
            "period_days": days,
            "total_word_count_change": recent_stats[-1].word_count - recent_stats[0].word_count,
            "daily_progress": daily_progress,
            "daily_change": daily_change,
            "average_daily_change": sum(daily_change.values()) / len(daily_change) if daily_change else 0,
            "reading_level_trends": reading_level_trends,
            "pace_trends": pace_trends,
            "vocabulary_richness_change": (
                recent_stats[-1].word_stats.vocabulary_richness - 
                recent_stats[0].word_stats.vocabulary_richness
            )
        }