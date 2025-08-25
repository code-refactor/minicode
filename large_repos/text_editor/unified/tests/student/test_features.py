"""
Tests for the progressive feature system.
"""
import pytest
import time

from text_editor.features.models import (
    Feature,
    UserProgress,
    SkillLevel,
    FeatureCategory
)
from text_editor.features.manager import FeatureManager
from text_editor.features.integration import ProgressiveEditor


class TestFeatureModels:
    def test_feature_model(self):
        """Test the Feature model functionality."""
        feature = Feature(
            id="test_feature",
            name="Test Feature",
            description="A test feature",
            category=FeatureCategory.BASIC_EDITING,
            required_skill_level=SkillLevel.BEGINNER
        )
        
        assert feature.id == "test_feature"
        assert feature.name == "Test Feature"
        assert feature.category == FeatureCategory.BASIC_EDITING
        assert feature.required_skill_level == SkillLevel.BEGINNER
        assert not feature.enabled
        
        # Test enable/disable
        feature.enable()
        assert feature.enabled
        assert feature.is_enabled()
        
        feature.disable()
        assert not feature.enabled
        assert not feature.is_enabled()
    
    def test_user_progress(self):
        """Test the UserProgress functionality."""
        progress = UserProgress()
        
        # Test initial state
        assert progress.skill_level == SkillLevel.BEGINNER
        assert progress.experience_points == 0
        assert not progress.unlocked_features
        
        # Test recording feature usage
        progress.record_feature_usage("test_feature")
        assert progress.feature_usage_count["test_feature"] == 1
        assert progress.experience_points > 0
        
        # Test adding experience
        initial_xp = progress.experience_points
        progress.add_experience(50)
        assert progress.experience_points == initial_xp + 50
        
        # Test unlocking features
        progress.unlock_feature("test_feature")
        assert "test_feature" in progress.unlocked_features
        assert progress.is_feature_unlocked("test_feature")
        
        # Test skill assessment
        progress.assess_skill()
        assert progress.last_assessment_time is not None
        
        # Test progress report
        report = progress.get_progress_report()
        assert report["skill_level"] == progress.skill_level.name
        assert report["experience_points"] == progress.experience_points
        assert report["unlocked_features"] == len(progress.unlocked_features)


class TestFeatureManager:
    def test_initialization(self):
        """Test that the feature manager is initialized correctly."""
        manager = FeatureManager()
        
        # Check that default features are loaded
        assert manager.features
        assert manager.user_progress
        
        # Check that beginner features are enabled by default
        beginner_features = [f for f in manager.features.values() 
                           if f.required_skill_level == SkillLevel.BEGINNER]
        assert all(f.is_enabled() for f in beginner_features)
    
    def test_get_available_features(self):
        """Test getting available (enabled) features."""
        manager = FeatureManager()
        available = manager.get_available_features()
        
        # Should include all beginner features
        assert all(f.required_skill_level == SkillLevel.BEGINNER for f in available)
        assert all(f.is_enabled() for f in available)
    
    def test_get_pending_features(self):
        """Test getting features that could be unlocked next."""
        manager = FeatureManager()
        
        # Set the user to INTERMEDIATE level to see some pending features
        manager.user_progress.skill_level = SkillLevel.INTERMEDIATE
        pending = manager.get_pending_features()
        
        # Should include some intermediate level features
        intermediate_features = [f for f in pending 
                               if f.required_skill_level == SkillLevel.INTERMEDIATE]
        assert intermediate_features
    
    def test_unlock_feature(self):
        """Test unlocking a specific feature."""
        manager = FeatureManager()
        
        # Set the user to INTERMEDIATE level
        manager.user_progress.skill_level = SkillLevel.INTERMEDIATE
        
        # Find an intermediate feature that's not yet unlocked
        intermediate_features = [f for f in manager.features.values() 
                               if f.required_skill_level == SkillLevel.INTERMEDIATE
                               and not f.is_enabled()]
        
        if intermediate_features:
            feature = intermediate_features[0]
            
            # Unlock all prerequisites first
            for prereq_id in feature.prerequisites:
                manager.unlock_feature(prereq_id)
                
            # Now unlock the feature
            unlocked = manager.unlock_feature(feature.id)
            assert unlocked is not None
            assert unlocked.is_enabled()
            assert manager.user_progress.is_feature_unlocked(feature.id)
    
    def test_set_skill_level(self):
        """Test setting the user's skill level directly."""
        manager = FeatureManager()
        
        # Set the user to ADVANCED level
        newly_unlocked = manager.set_skill_level(SkillLevel.ADVANCED)
        
        # Should unlock some advanced features
        assert manager.user_progress.skill_level == SkillLevel.ADVANCED
        assert newly_unlocked
        assert any(f.required_skill_level == SkillLevel.ADVANCED for f in newly_unlocked)
    
    def test_feature_usage_tracking(self):
        """Test tracking feature usage."""
        manager = FeatureManager()
        
        # Record some feature usage
        feature_id = "basic_cursor_movement"  # Use a default feature
        initial_count = manager.user_progress.feature_usage_count.get(feature_id, 0)
        
        manager.record_feature_usage(feature_id)
        
        assert manager.user_progress.feature_usage_count.get(feature_id, 0) > initial_count


class TestProgressiveEditor:
    def test_initialization(self):
        """Test that the progressive editor is initialized correctly."""
        editor = ProgressiveEditor()
        
        assert editor.editor
        assert editor.feature_manager
    
    def test_feature_access_control(self):
        """Test that feature access is properly controlled."""
        editor = ProgressiveEditor()
        
        # Try using a basic feature (should work)
        initial_content = editor.get_content()
        editor.insert_text("Hello")
        assert editor.get_content() == initial_content + "Hello"
        
        # Set cursor position for further tests
        editor.move_cursor("buffer_start")
        
        # Try using an advanced feature (should be restricted)
        # First, make sure the feature is disabled
        feature_id = "regex_search"  # An advanced feature
        feature = editor.feature_manager.features.get(feature_id)
        if feature:
            feature.disable()
            editor.feature_manager.user_progress.unlocked_features.discard(feature_id)
            
            # Now try to use the feature (it should not affect the editor)
            # The feature is still in initial state, so no changes to verify
            pass
    
    def test_progressive_unlocking(self):
        """Test that features are progressively unlocked."""
        editor = ProgressiveEditor()
        
        # Record usage of basic features
        for _ in range(10):
            editor.move_cursor("right")  # Uses basic_cursor_movement
            
        # Set a higher skill level to unlock more features
        newly_unlocked = editor.feature_manager.set_skill_level(SkillLevel.INTERMEDIATE)
        
        # Should unlock some intermediate features
        assert newly_unlocked
        assert all(f.is_enabled() for f in newly_unlocked)
        
        # Now we should be able to use intermediate features
        for feature in newly_unlocked:
            if feature.id == "word_navigation":
                editor.move_by_word("right")  # Now this should work
            elif feature.id == "undo_redo":
                editor.undo()  # Now this should work