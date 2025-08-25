"""
Feature manager for the progressive feature system.
"""
from typing import Dict, List, Set, Optional, Any, Callable
from pydantic import BaseModel, Field
import time

from text_editor.features.models import (
    Feature, 
    UserProgress, 
    SkillLevel, 
    FeatureCategory
)

# Define default features with their skill levels
DEFAULT_FEATURES = [
    # Beginner features
    Feature(
        id="basic_cursor_movement",
        name="Basic Cursor Movement",
        description="Move the cursor using arrow keys",
        category=FeatureCategory.TEXT_NAVIGATION,
        required_skill_level=SkillLevel.BEGINNER,
        usage_examples=["Use arrow keys to navigate through text"],
    ),
    Feature(
        id="basic_text_insertion",
        name="Basic Text Insertion",
        description="Insert text at the cursor position",
        category=FeatureCategory.BASIC_EDITING,
        required_skill_level=SkillLevel.BEGINNER,
        usage_examples=["Type characters to insert them at the cursor position"],
    ),
    Feature(
        id="basic_text_deletion",
        name="Basic Text Deletion",
        description="Delete text using backspace and delete keys",
        category=FeatureCategory.BASIC_EDITING,
        required_skill_level=SkillLevel.BEGINNER,
        usage_examples=["Press Backspace to delete the character before the cursor",
                      "Press Delete to delete the character after the cursor"],
    ),
    Feature(
        id="load_save_file",
        name="Load and Save Files",
        description="Open existing files and save changes",
        category=FeatureCategory.FILE_OPERATIONS,
        required_skill_level=SkillLevel.BEGINNER,
        usage_examples=["Use load_file() to open a file",
                      "Use save_file() to save changes"],
    ),
    
    # Intermediate features
    Feature(
        id="word_navigation",
        name="Word Navigation",
        description="Move the cursor word by word",
        category=FeatureCategory.TEXT_NAVIGATION,
        required_skill_level=SkillLevel.INTERMEDIATE,
        prerequisites=["basic_cursor_movement"],
        usage_examples=["Use Ctrl+Left/Right to move by words"],
    ),
    Feature(
        id="line_operations",
        name="Line Operations",
        description="Move to start/end of line, delete entire lines",
        category=FeatureCategory.TEXT_NAVIGATION,
        required_skill_level=SkillLevel.INTERMEDIATE,
        prerequisites=["basic_cursor_movement"],
        usage_examples=["Use Home to move to start of line",
                      "Use End to move to end of line"],
    ),
    Feature(
        id="undo_redo",
        name="Undo and Redo",
        description="Undo and redo editing operations",
        category=FeatureCategory.HISTORY_OPERATIONS,
        required_skill_level=SkillLevel.INTERMEDIATE,
        prerequisites=["basic_text_insertion", "basic_text_deletion"],
        usage_examples=["Use undo() to reverse the last operation",
                      "Use redo() to re-apply an operation after undoing"],
    ),
    Feature(
        id="find_text",
        name="Find Text",
        description="Search for text in the document",
        category=FeatureCategory.SEARCH_REPLACE,
        required_skill_level=SkillLevel.INTERMEDIATE,
        usage_examples=["Use find() to locate text in the document"],
    ),
    
    # Advanced features
    Feature(
        id="find_replace",
        name="Find and Replace",
        description="Search for text and replace it",
        category=FeatureCategory.SEARCH_REPLACE,
        required_skill_level=SkillLevel.ADVANCED,
        prerequisites=["find_text"],
        usage_examples=["Use replace() to find and replace text",
                      "Use replace_all() to replace all occurrences"],
    ),
    Feature(
        id="regex_search",
        name="Regular Expression Search",
        description="Search using regular expressions",
        category=FeatureCategory.SEARCH_REPLACE,
        required_skill_level=SkillLevel.ADVANCED,
        prerequisites=["find_replace"],
        usage_examples=["Use regex_find() to search with regular expressions"],
    ),
    Feature(
        id="selection_operations",
        name="Selection Operations",
        description="Select and manipulate blocks of text",
        category=FeatureCategory.ADVANCED_EDITING,
        required_skill_level=SkillLevel.ADVANCED,
        prerequisites=["basic_cursor_movement", "word_navigation"],
        usage_examples=["Select text and apply operations to the selection"],
    ),
    Feature(
        id="bookmarks",
        name="Bookmarks",
        description="Set and jump to bookmarks in the document",
        category=FeatureCategory.TEXT_NAVIGATION,
        required_skill_level=SkillLevel.ADVANCED,
        usage_examples=["Set bookmarks at important positions",
                      "Jump quickly between bookmarked positions"],
    ),
    
    # Expert features
    Feature(
        id="macros",
        name="Macros",
        description="Record and replay sequences of operations",
        category=FeatureCategory.AUTOMATION,
        required_skill_level=SkillLevel.EXPERT,
        usage_examples=["Record a sequence of editing operations",
                      "Replay the sequence with a single command"],
    ),
    Feature(
        id="code_folding",
        name="Code Folding",
        description="Collapse and expand sections of code",
        category=FeatureCategory.CODE_INTELLIGENCE,
        required_skill_level=SkillLevel.EXPERT,
        usage_examples=["Fold function definitions to hide implementation details",
                      "Unfold sections when you need to see the details"],
    ),
    Feature(
        id="multi_cursor",
        name="Multiple Cursors",
        description="Edit text at multiple positions simultaneously",
        category=FeatureCategory.ADVANCED_EDITING,
        required_skill_level=SkillLevel.EXPERT,
        prerequisites=["selection_operations"],
        usage_examples=["Add multiple cursors at different positions",
                      "Make the same edit at all cursor positions"],
    ),
    Feature(
        id="code_snippets",
        name="Code Snippets",
        description="Insert commonly used code patterns",
        category=FeatureCategory.CODE_INTELLIGENCE,
        required_skill_level=SkillLevel.EXPERT,
        usage_examples=["Insert a for loop snippet",
                      "Insert a function definition snippet"],
    ),
]


class FeatureManager(BaseModel):
    """
    Manages the progressive feature system.
    
    This class handles feature unlocking, tracking user progress,
    and providing appropriate features based on skill level.
    """
    features: Dict[str, Feature] = Field(default_factory=dict)
    user_progress: UserProgress = Field(default_factory=UserProgress)
    feature_hooks: Dict[str, List[Callable]] = Field(default_factory=dict)
    assessment_interval: int = 3600  # Time in seconds between skill assessments
    
    def __init__(self, **kwargs):
        """Initialize the feature manager with default features."""
        super().__init__(**kwargs)
        
        # Initialize with default features
        for feature in DEFAULT_FEATURES:
            self.features[feature.id] = feature
        
        # Enable all beginner features by default
        self._enable_beginner_features()
    
    def _enable_beginner_features(self) -> None:
        """Enable all beginner-level features by default."""
        for feature_id, feature in self.features.items():
            if feature.required_skill_level == SkillLevel.BEGINNER:
                feature.enable()
                self.user_progress.unlock_feature(feature_id)
    
    def get_available_features(self) -> List[Feature]:
        """
        Get a list of all available (enabled) features.
        
        Returns:
            List of enabled Feature objects
        """
        return [f for f in self.features.values() if f.is_enabled()]
    
    def get_pending_features(self) -> List[Feature]:
        """
        Get a list of features that could be unlocked next.
        
        Returns:
            List of Feature objects that can be unlocked
        """
        user_level = self.user_progress.skill_level
        unlocked_feature_ids = self.user_progress.unlocked_features
        
        pending = []
        for feature_id, feature in self.features.items():
            # Skip already unlocked features
            if feature_id in unlocked_feature_ids:
                continue
                
            # Check if the feature is appropriate for the user's level
            if feature.required_skill_level.value <= user_level.value:
                # Check if prerequisites are met
                prerequisites_met = all(
                    prereq in unlocked_feature_ids
                    for prereq in feature.prerequisites
                )
                
                if prerequisites_met:
                    pending.append(feature)
        
        return pending
    
    def unlock_feature(self, feature_id: str) -> Optional[Feature]:
        """
        Unlock a specific feature for the user.
        
        Args:
            feature_id: ID of the feature to unlock
            
        Returns:
            The unlocked Feature object, or None if the feature doesn't exist
            or prerequisites are not met
        """
        # Check if the feature exists
        if feature_id not in self.features:
            return None
            
        feature = self.features[feature_id]
        unlocked_feature_ids = self.user_progress.unlocked_features
        
        # Check if the feature is already unlocked
        if feature_id in unlocked_feature_ids:
            return feature
            
        # Check if the user has the required skill level
        if feature.required_skill_level.value > self.user_progress.skill_level.value:
            return None
            
        # Check if prerequisites are met
        for prereq in feature.prerequisites:
            if prereq not in unlocked_feature_ids:
                return None
                
        # Unlock the feature
        start_time = time.time()
        self.user_progress.unlock_feature(feature_id)
        feature.enable()
        
        # Calculate unlock time for performance metrics
        unlock_time_ms = (time.time() - start_time) * 1000
        
        # Call any registered hooks for this feature
        if feature_id in self.feature_hooks:
            for hook in self.feature_hooks[feature_id]:
                hook(feature)
                
        return feature
    
    def unlock_appropriate_features(self) -> List[Feature]:
        """
        Unlock all features that are appropriate for the user's current skill level.
        
        Returns:
            List of newly unlocked Feature objects
        """
        pending_features = self.get_pending_features()
        newly_unlocked = []
        
        for feature in pending_features:
            unlocked_feature = self.unlock_feature(feature.id)
            if unlocked_feature:
                newly_unlocked.append(unlocked_feature)
                
        return newly_unlocked
    
    def record_feature_usage(self, feature_id: str) -> None:
        """
        Record that the user has used a feature.
        
        Args:
            feature_id: ID of the feature that was used
        """
        if feature_id in self.features:
            self.user_progress.record_feature_usage(feature_id)
            
            # Check if we should assess skill level
            last_assessment = self.user_progress.last_assessment_time
            if (last_assessment is None or 
                time.time() - last_assessment > self.assessment_interval):
                self.user_progress.assess_skill()
                
                # After assessment, unlock appropriate features
                self.unlock_appropriate_features()
    
    def register_feature_hook(self, feature_id: str, hook: Callable[[Feature], None]) -> None:
        """
        Register a hook to be called when a feature is unlocked.
        
        Args:
            feature_id: ID of the feature to hook
            hook: Callback function to call when the feature is unlocked
        """
        if feature_id not in self.feature_hooks:
            self.feature_hooks[feature_id] = []
            
        self.feature_hooks[feature_id].append(hook)
    
    def is_feature_enabled(self, feature_id: str) -> bool:
        """
        Check if a feature is enabled for the current user.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the feature is enabled, False otherwise
        """
        return (feature_id in self.features and 
                self.features[feature_id].is_enabled())
    
    def get_feature_guidance(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """
        Get guidance information for a feature.
        
        Args:
            feature_id: ID of the feature to get guidance for
            
        Returns:
            Dictionary with guidance information, or None if the feature doesn't exist
        """
        if feature_id not in self.features:
            return None
            
        feature = self.features[feature_id]
        return {
            "name": feature.name,
            "description": feature.description,
            "usage_examples": feature.usage_examples,
            "documentation": feature.documentation
        }
    
    def get_user_progress_report(self) -> Dict[str, Any]:
        """
        Get a report of the user's progress.
        
        Returns:
            Dictionary with progress information
        """
        return self.user_progress.get_progress_report()
    
    def set_skill_level(self, level: SkillLevel) -> List[Feature]:
        """
        Set the user's skill level directly.
        
        Args:
            level: The new skill level to set
            
        Returns:
            List of newly unlocked features
        """
        self.user_progress.skill_level = level
        return self.unlock_appropriate_features()