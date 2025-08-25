"""Client module that integrates all the components of the text editor."""

from typing import Dict, List, Optional, Any, Tuple
from writer_text_editor.document import Document
from writer_text_editor.focus import FocusMode, FocusLevel
from writer_text_editor.statistics import WritingStatistics
from writer_text_editor.narrative import NarrativeTracker, ElementType
from writer_text_editor.navigation import DocumentNavigator, NavigationViewType
from writer_text_editor.revision import RevisionManager


class WriterTextEditor:
    """Main client class for the writer text editor."""
    
    def __init__(self, document_title: str = "Untitled Document"):
        """Initialize the text editor with a new document."""
        self.document = Document(title=document_title)
        self.focus_mode = FocusMode(self.document)
        self.statistics = WritingStatistics(self.document)
        self.narrative_tracker = NarrativeTracker(self.document)
        self.navigator = DocumentNavigator(self.document, self.narrative_tracker)
        self.revision_manager = RevisionManager(self.document)
        
        # Start the background tracking
        self.statistics.start_background_tracking()
        self.narrative_tracker.start_background_tracking()
    
    def close(self):
        """Clean up resources when closing the editor."""
        self.statistics.stop_background_tracking()
        self.narrative_tracker.stop_background_tracking()
    
    # Document operations
    
    def get_document(self) -> Document:
        """Get the current document."""
        return self.document
    
    def add_section(self, title: str) -> str:
        """Add a new section to the document and return its ID."""
        section = self.document.add_section(title)
        return section.id
    
    def add_paragraph(self, section_index: int, content: str) -> Optional[str]:
        """Add a paragraph to a section and return its ID."""
        section = self.document.get_section(section_index)
        if not section:
            return None
        
        segment = section.add_segment(content)
        return segment.id
    
    def get_document_content(self) -> str:
        """Get the full content of the document."""
        return self.document.get_content()
    
    # Focus mode operations
    
    def enter_focus(self, section_index: int, paragraph_index: int, 
                   level: FocusLevel = FocusLevel.PARAGRAPH) -> bool:
        """Enter focus mode for a specific paragraph."""
        focus_context = self.focus_mode.enter_focus(
            section_index=section_index,
            segment_index=paragraph_index,
            level=level
        )
        return focus_context is not None
    
    def exit_focus(self) -> bool:
        """Exit focus mode."""
        return self.focus_mode.exit_focus()
    
    def edit_in_focus(self, new_content: str) -> bool:
        """Edit the content in focus mode."""
        result = self.focus_mode.edit_focused_content(new_content)
        return result is not None
    
    def move_focus(self, direction: int = 1) -> bool:
        """Move focus to the next or previous paragraph."""
        result = self.focus_mode.move_focus(direction)
        return result is not None
    
    def get_focus_context(self) -> Dict[str, Any]:
        """Get information about the current focus context."""
        context = self.focus_mode.get_focus_context()
        if not context:
            return {"active": False}
        
        return {
            "active": True,
            "section_title": context.section.title,
            "content": context.segment.content,
            "level": context.level.value,
            "focus_time": self.focus_mode.get_focus_time()
        }
    
    # Statistics operations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get the current document statistics."""
        stats = self.statistics.calculate_stats()
        
        return {
            "word_count": stats.word_count,
            "character_count": stats.character_count,
            "paragraph_count": stats.paragraph_count,
            "sentence_count": stats.sentence_count,
            "reading_level": stats.reading_level,
            "vocabulary_richness": stats.word_stats.vocabulary_richness,
            "avg_sentence_length": stats.sentence_stats.average_sentence_length
        }
    
    def get_writing_pace(self) -> Dict[str, float]:
        """Get the current writing pace."""
        pace = self.statistics.calculate_writing_pace()
        
        return {
            "words_per_minute": pace.words_per_minute,
            "words_per_hour": pace.words_per_hour,
            "words_per_day": pace.words_per_day
        }
    
    def set_writing_goal(self, goal_id: str, target: int, days: int = 30) -> Dict[str, Any]:
        """Set a writing goal for word count."""
        from datetime import datetime, timedelta
        
        deadline = datetime.now() + timedelta(days=days)
        tracker = self.statistics.set_progress_goal(
            goal_id=goal_id,
            goal_type="word_count",
            target=target,
            deadline=deadline
        )
        
        progress = self.statistics.update_progress(goal_id)
        
        return {
            "goal_id": goal_id,
            "target": target,
            "deadline_days": days,
            "current_word_count": progress["word_count"],
            "progress_percentage": progress["progress_percentage"],
            "remaining": progress["remaining"]
        }
    
    def get_goal_progress(self, goal_id: str) -> Dict[str, Any]:
        """Get progress for a specific goal."""
        report = self.statistics.get_progress_report(goal_id)
        if not report:
            return {"error": f"Goal {goal_id} not found"}
        
        return report
    
    # Narrative element operations
    
    def detect_characters(self) -> List[Dict[str, Any]]:
        """Detect and track characters in the document."""
        elements = self.narrative_tracker.detect_elements()
        characters = elements.get(ElementType.CHARACTER.value, [])
        
        return [
            {
                "id": char.id,
                "name": char.name,
                "occurrences": len(char.occurrences)
            }
            for char in characters
        ]
    
    def get_character_timeline(self, character_id: str) -> List[Dict[str, Any]]:
        """Get a timeline of a character's appearances."""
        timeline = self.narrative_tracker.get_element_timeline(character_id)
        
        return timeline
    
    def check_narrative_consistency(self) -> List[Dict[str, Any]]:
        """Check for consistency issues in the narrative."""
        issues = self.narrative_tracker.check_consistency()
        
        return [
            {
                "id": issue.id,
                "type": issue.issue_type,
                "description": issue.description,
                "severity": issue.severity,
                "resolved": issue.resolved
            }
            for issue in issues
        ]
    
    # Navigation operations
    
    def create_navigation_view(self, name: str, view_type: str) -> str:
        """Create a new navigation view."""
        nav_type = NavigationViewType(view_type)
        view_id = self.navigator.create_view(name, nav_type)
        
        return view_id
    
    def navigate_to(self, view_id: str, element_id: str) -> bool:
        """Navigate to a specific element in a view."""
        return self.navigator.navigate_to(view_id, element_id)
    
    def get_current_location(self) -> Dict[str, Any]:
        """Get information about the current navigation location."""
        element = self.navigator.get_current_element()
        if not element:
            return {"error": "No current position"}
        
        content = self.navigator.get_element_content(element.id)
        
        return {
            "view_id": self.navigator.current_position.view_id,
            "element_id": element.id,
            "element_type": element.element_type,
            "name": element.name,
            "content": content
        }
    
    def navigate_next(self) -> bool:
        """Navigate to the next element at the same level."""
        return self.navigator.navigate_next()
    
    def navigate_previous(self) -> bool:
        """Navigate to the previous element at the same level."""
        return self.navigator.navigate_previous()
    
    def navigate_parent(self) -> bool:
        """Navigate to the parent of the current element."""
        return self.navigator.navigate_parent()
    
    def get_navigation_children(self) -> List[Dict[str, Any]]:
        """Get the children of the current element."""
        children = self.navigator.navigate_children()
        
        return [
            {
                "id": child.id,
                "type": child.element_type,
                "name": child.name
            }
            for child in children
        ]
    
    # Revision operations
    
    def create_revision(self, name: str) -> str:
        """Create a new revision of the document."""
        revision = self.revision_manager.create_revision(name)
        return revision.id
    
    def compare_revisions(self, old_revision: str, new_revision: str) -> Dict[str, Any]:
        """Compare two revisions and return the differences."""
        diff = self.revision_manager.compare_revisions(old_revision, new_revision)
        if not diff:
            return {"error": "Could not compare revisions"}
        
        # Convert diff to a simplified format
        result = {
            "old_revision": old_revision,
            "new_revision": new_revision,
            "timestamp": diff.timestamp.isoformat(),
            "sections": []
        }
        
        for section_diff in diff.section_diffs:
            section_info = {
                "id": section_diff.section_id,
                "type": section_diff.diff_type.value,
                "old_title": section_diff.old_title,
                "new_title": section_diff.new_title,
                "segments": []
            }
            
            for segment_diff in section_diff.segment_diffs:
                segment_info = {
                    "id": segment_diff.segment_id,
                    "type": segment_diff.diff_type.value,
                    "position": segment_diff.position,
                    "has_content_change": segment_diff.old_content != segment_diff.new_content
                }
                section_info["segments"].append(segment_info)
            
            result["sections"].append(section_info)
        
        return result
    
    def switch_revision(self, revision_name: str) -> bool:
        """Switch to a different revision."""
        return self.document.switch_to_revision(revision_name)
    
    def get_revision_history(self) -> Dict[str, Any]:
        """Get the revision history."""
        return self.revision_manager.export_revision_history()
    
    def merge_revisions(self, base_revision: str, revisions: List[str]) -> str:
        """Merge multiple revisions into a new revision."""
        merged = self.revision_manager.merge_revisions(base_revision, revisions)
        if not merged:
            return ""
        
        return merged.name