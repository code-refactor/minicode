"""
Data models for the progressive feature system.
"""
from enum import Enum, auto
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field
import time


class SkillLevel(Enum):
    """Enum representing different skill levels for users."""
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class FeatureCategory(Enum):
    """Categories of editor features that can be progressively unlocked."""
    BASIC_EDITING = "basic_editing"
    TEXT_NAVIGATION = "text_navigation"
    SEARCH_REPLACE = "search_replace"
    ADVANCED_EDITING = "advanced_editing"
    FILE_OPERATIONS = "file_operations"
    HISTORY_OPERATIONS = "history_operations"
    CODE_FORMATTING = "code_formatting"
    CODE_INTELLIGENCE = "code_intelligence"
    CUSTOMIZATION = "customization"
    AUTOMATION = "automation"


class Feature(BaseModel):
    """
    Represents a feature in the text editor that can be progressively unlocked.
    """
    id: str
    name: str
    description: str
    category: FeatureCategory
    required_skill_level: SkillLevel
    prerequisites: List[str] = Field(default_factory=list)
    usage_examples: List[str] = Field(default_factory=list)
    documentation: str = ""
    enabled: bool = False
    
    def enable(self) -> None:
        """Enable this feature."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable this feature."""
        self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if this feature is enabled."""
        return self.enabled


class UserProgress(BaseModel):
    """
    Tracks a user's progress and skill level for the progressive feature system.
    """
    skill_level: SkillLevel = SkillLevel.BEGINNER
    experience_points: int = 0
    feature_usage_count: Dict[str, int] = Field(default_factory=dict)
    unlocked_features: Set[str] = Field(default_factory=set)
    last_assessment_time: Optional[float] = None
    progress_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def record_feature_usage(self, feature_id: str, count: int = 1) -> None:
        """
        Record that a feature was used by the user.
        
        Args:
            feature_id: The ID of the feature that was used
            count: How many times the feature was used (default: 1)
        """
        if feature_id not in self.feature_usage_count:
            self.feature_usage_count[feature_id] = 0
        
        self.feature_usage_count[feature_id] += count
        
        # Award experience points for using features
        # More points for using advanced features less frequently
        if feature_id in self.feature_usage_count and self.feature_usage_count[feature_id] <= 10:
            self.add_experience(2)
        else:
            self.add_experience(1)
    
    def add_experience(self, points: int) -> None:
        """
        Add experience points to the user's progress.
        
        Args:
            points: The number of experience points to add
        """
        self.experience_points += points
        
        # Check if the user should level up based on experience points
        if (self.skill_level == SkillLevel.BEGINNER and 
            self.experience_points >= 100):
            self.skill_level = SkillLevel.INTERMEDIATE
            self._record_level_up()
        elif (self.skill_level == SkillLevel.INTERMEDIATE and 
              self.experience_points >= 300):
            self.skill_level = SkillLevel.ADVANCED
            self._record_level_up()
        elif (self.skill_level == SkillLevel.ADVANCED and 
              self.experience_points >= 600):
            self.skill_level = SkillLevel.EXPERT
            self._record_level_up()
    
    def unlock_feature(self, feature_id: str) -> None:
        """
        Unlock a feature for the user.
        
        Args:
            feature_id: The ID of the feature to unlock
        """
        self.unlocked_features.add(feature_id)
        
        # Record this event in progress history
        self.progress_history.append({
            "timestamp": time.time(),
            "event": "feature_unlocked",
            "feature_id": feature_id
        })
    
    def is_feature_unlocked(self, feature_id: str) -> bool:
        """
        Check if a feature is unlocked for the user.
        
        Args:
            feature_id: The ID of the feature to check
            
        Returns:
            True if the feature is unlocked, False otherwise
        """
        return feature_id in self.unlocked_features
    
    def _record_level_up(self) -> None:
        """Record a level-up event in the progress history."""
        self.progress_history.append({
            "timestamp": time.time(),
            "event": "level_up",
            "new_level": self.skill_level.name,
            "experience_points": self.experience_points
        })
    
    def assess_skill(self) -> None:
        """
        Assess the user's skill level based on feature usage patterns.
        This would use a more sophisticated algorithm in a real implementation.
        """
        # Record that an assessment was performed
        self.last_assessment_time = time.time()
        
        # Simple assessment: count number of different features used
        unique_features_used = len([k for k, v in self.feature_usage_count.items() if v > 5])
        
        # Update skill level based on unique features used
        if unique_features_used >= 15 and self.skill_level.value < SkillLevel.EXPERT.value:
            self.skill_level = SkillLevel.EXPERT
            self._record_level_up()
        elif unique_features_used >= 10 and self.skill_level.value < SkillLevel.ADVANCED.value:
            self.skill_level = SkillLevel.ADVANCED
            self._record_level_up()
        elif unique_features_used >= 5 and self.skill_level.value < SkillLevel.INTERMEDIATE.value:
            self.skill_level = SkillLevel.INTERMEDIATE
            self._record_level_up()
    
    def get_progress_report(self) -> Dict[str, Any]:
        """
        Generate a report of the user's progress.
        
        Returns:
            A dictionary containing progress information
        """
        return {
            "skill_level": self.skill_level.name,
            "experience_points": self.experience_points,
            "features_used": len(self.feature_usage_count),
            "unlocked_features": len(self.unlocked_features),
            "most_used_features": sorted(
                self.feature_usage_count.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5] if self.feature_usage_count else []
        }