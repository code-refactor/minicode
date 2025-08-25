"""Revision management system for the writer text editor."""

from __future__ import annotations
import difflib
import time
import threading
import copy
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any, Union, Callable
from common.core import BaseModel, Position
from pydantic import Field

from writer_text_editor.document import Document, Section, TextSegment, Revision


class DiffType(str, Enum):
    """Types of differences."""
    
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


class SegmentDiff(BaseModel):
    """A difference between two segments."""
    
    diff_type: DiffType
    segment_id: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    position: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SectionDiff(BaseModel):
    """A difference between two sections."""
    
    diff_type: DiffType
    section_id: Optional[str] = None
    old_title: Optional[str] = None
    new_title: Optional[str] = None
    segment_diffs: List[SegmentDiff] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RevisionDiff(BaseModel):
    """A difference between two revisions."""
    
    old_revision_id: str
    new_revision_id: str
    old_revision_name: str
    new_revision_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    section_diffs: List[SectionDiff] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RevisionManager:
    """Revision management system."""
    
    def __init__(self, document: Document):
        """Initialize the revision manager with the given document."""
        self.document = document
        self.diffs: Dict[str, RevisionDiff] = {}
    
    def create_revision(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Revision:
        """Create a new revision of the document."""
        return self.document.create_revision(name=name, metadata=metadata)
    
    def compare_revisions(self, old_revision_name: str, new_revision_name: str) -> Optional[RevisionDiff]:
        """Compare two revisions and generate a diff."""
        old_revision = self.document.get_revision(old_revision_name)
        new_revision = self.document.get_revision(new_revision_name)
        
        if not old_revision or not new_revision:
            return None
        
        # Create a unique ID for this diff
        diff_id = f"{old_revision_name}_{new_revision_name}"
        
        # Check if we already have this diff
        if diff_id in self.diffs:
            return self.diffs[diff_id]
        
        # Create a new diff
        revision_diff = RevisionDiff(
            old_revision_id=old_revision.id,
            new_revision_id=new_revision.id,
            old_revision_name=old_revision_name,
            new_revision_name=new_revision_name
        )
        
        # Compare sections
        old_sections_by_id = {section.id: section for section in old_revision.sections}
        new_sections_by_id = {section.id: section for section in new_revision.sections}
        
        # Find common section IDs
        common_section_ids = set(old_sections_by_id.keys()) & set(new_sections_by_id.keys())
        
        # Find added and removed sections
        added_section_ids = set(new_sections_by_id.keys()) - set(old_sections_by_id.keys())
        removed_section_ids = set(old_sections_by_id.keys()) - set(new_sections_by_id.keys())
        
        # Process added sections
        for section_id in added_section_ids:
            section = new_sections_by_id[section_id]
            section_diff = SectionDiff(
                diff_type=DiffType.INSERT,
                section_id=section_id,
                new_title=section.title
            )
            
            # Add all segments as inserted
            for segment in section.segments:
                segment_diff = SegmentDiff(
                    diff_type=DiffType.INSERT,
                    segment_id=segment.id,
                    new_content=segment.content,
                    position=segment.position
                )
                section_diff.segment_diffs.append(segment_diff)
            
            revision_diff.section_diffs.append(section_diff)
        
        # Process removed sections
        for section_id in removed_section_ids:
            section = old_sections_by_id[section_id]
            section_diff = SectionDiff(
                diff_type=DiffType.DELETE,
                section_id=section_id,
                old_title=section.title
            )
            
            # Add all segments as deleted
            for segment in section.segments:
                segment_diff = SegmentDiff(
                    diff_type=DiffType.DELETE,
                    segment_id=segment.id,
                    old_content=segment.content,
                    position=segment.position
                )
                section_diff.segment_diffs.append(segment_diff)
            
            revision_diff.section_diffs.append(section_diff)
        
        # Process common sections
        for section_id in common_section_ids:
            old_section = old_sections_by_id[section_id]
            new_section = new_sections_by_id[section_id]
            
            # Check if title changed
            if old_section.title != new_section.title:
                section_diff = SectionDiff(
                    diff_type=DiffType.REPLACE,
                    section_id=section_id,
                    old_title=old_section.title,
                    new_title=new_section.title
                )
            else:
                section_diff = SectionDiff(
                    diff_type=DiffType.EQUAL,
                    section_id=section_id,
                    old_title=old_section.title,
                    new_title=new_section.title
                )
            
            # Compare segments within the section
            old_segments_by_id = {segment.id: segment for segment in old_section.segments}
            new_segments_by_id = {segment.id: segment for segment in new_section.segments}
            
            # Find common segment IDs
            common_segment_ids = set(old_segments_by_id.keys()) & set(new_segments_by_id.keys())
            
            # Find added and removed segments
            added_segment_ids = set(new_segments_by_id.keys()) - set(old_segments_by_id.keys())
            removed_segment_ids = set(old_segments_by_id.keys()) - set(new_segments_by_id.keys())
            
            # Process added segments
            for segment_id in added_segment_ids:
                segment = new_segments_by_id[segment_id]
                segment_diff = SegmentDiff(
                    diff_type=DiffType.INSERT,
                    segment_id=segment_id,
                    new_content=segment.content,
                    position=segment.position
                )
                section_diff.segment_diffs.append(segment_diff)
            
            # Process removed segments
            for segment_id in removed_segment_ids:
                segment = old_segments_by_id[segment_id]
                segment_diff = SegmentDiff(
                    diff_type=DiffType.DELETE,
                    segment_id=segment_id,
                    old_content=segment.content,
                    position=segment.position
                )
                section_diff.segment_diffs.append(segment_diff)
            
            # Process common segments
            for segment_id in common_segment_ids:
                old_segment = old_segments_by_id[segment_id]
                new_segment = new_segments_by_id[segment_id]
                
                # Check if content changed
                if old_segment.content != new_segment.content:
                    segment_diff = SegmentDiff(
                        diff_type=DiffType.REPLACE,
                        segment_id=segment_id,
                        old_content=old_segment.content,
                        new_content=new_segment.content,
                        position=new_segment.position
                    )
                    section_diff.segment_diffs.append(segment_diff)
            
            # Only add section diff if there are changes
            if section_diff.diff_type != DiffType.EQUAL or section_diff.segment_diffs:
                revision_diff.section_diffs.append(section_diff)
        
        # Store and return the diff
        self.diffs[diff_id] = revision_diff
        return revision_diff
    
    def get_html_diff(self, old_content: str, new_content: str) -> str:
        """Generate an HTML diff of two texts."""
        differ = difflib.HtmlDiff()
        return differ.make_file(
            old_content.splitlines(),
            new_content.splitlines(),
            "Old Version",
            "New Version",
            context=True
        )
    
    def get_unified_diff(self, old_content: str, new_content: str, context_lines: int = 3) -> str:
        """Generate a unified diff of two texts."""
        return "\n".join(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            "Old Version",
            "New Version",
            n=context_lines
        ))
    
    def get_detailed_segment_diff(self, old_content: str, new_content: str) -> List[Dict[str, Any]]:
        """Generate a detailed word-level diff of two segment contents."""
        # Split into words
        old_words = old_content.split()
        new_words = new_content.split()
        
        # Get opcodes
        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        opcodes = matcher.get_opcodes()
        
        result = []
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                result.append({
                    'type': 'equal',
                    'content': ' '.join(old_words[i1:i2])
                })
            elif tag == 'replace':
                result.append({
                    'type': 'delete',
                    'content': ' '.join(old_words[i1:i2])
                })
                result.append({
                    'type': 'insert',
                    'content': ' '.join(new_words[j1:j2])
                })
            elif tag == 'delete':
                result.append({
                    'type': 'delete',
                    'content': ' '.join(old_words[i1:i2])
                })
            elif tag == 'insert':
                result.append({
                    'type': 'insert',
                    'content': ' '.join(new_words[j1:j2])
                })
        
        return result
    
    def apply_diff(self, diff: RevisionDiff, target_revision_name: Optional[str] = None) -> Optional[Revision]:
        """Apply a diff to a revision to create a new revision."""
        # If target_revision_name is not provided, create a new revision
        if not target_revision_name:
            target_revision_name = f"Merged_{diff.old_revision_name}_{diff.new_revision_name}"
        
        # Create a new revision based on the old revision
        old_revision = self.document.get_revision(diff.old_revision_name)
        if not old_revision:
            return None
        
        # Create a deep copy of the old revision
        target_revision = self.create_revision(
            name=target_revision_name,
            metadata={"merged_from": [diff.old_revision_name, diff.new_revision_name]}
        )
        
        # Apply section changes
        for section_diff in diff.section_diffs:
            section_id = section_diff.section_id
            
            if section_diff.diff_type == DiffType.INSERT:
                # Add new section
                new_section = Section(
                    id=section_id,
                    title=section_diff.new_title or "",
                    segments=[]
                )
                
                # Add segment diffs
                for segment_diff in section_diff.segment_diffs:
                    if segment_diff.diff_type == DiffType.INSERT:
                        segment = TextSegment(
                            id=segment_diff.segment_id or "",
                            content=segment_diff.new_content or "",
                            position=segment_diff.position or 0
                        )
                        new_section.segments.append(segment)
                
                # Add to target revision
                target_revision.sections.append(new_section)
            
            elif section_diff.diff_type == DiffType.DELETE:
                # Remove section
                for i, section in enumerate(target_revision.sections):
                    if section.id == section_id:
                        target_revision.sections.pop(i)
                        break
            
            elif section_diff.diff_type in (DiffType.REPLACE, DiffType.EQUAL):
                # Update section title if it changed
                for section in target_revision.sections:
                    if section.id == section_id:
                        if section_diff.new_title:
                            section.title = section_diff.new_title
                        
                        # Process segment changes
                        for segment_diff in section_diff.segment_diffs:
                            segment_id = segment_diff.segment_id
                            
                            if segment_diff.diff_type == DiffType.INSERT:
                                # Add new segment
                                segment = TextSegment(
                                    id=segment_id or "",
                                    content=segment_diff.new_content or "",
                                    position=segment_diff.position or 0
                                )
                                
                                # Insert at the right position
                                if segment_diff.position is not None:
                                    if segment_diff.position < len(section.segments):
                                        section.segments.insert(segment_diff.position, segment)
                                    else:
                                        section.segments.append(segment)
                                else:
                                    section.segments.append(segment)
                                
                                # Update positions
                                for i, seg in enumerate(section.segments):
                                    seg.position = i
                            
                            elif segment_diff.diff_type == DiffType.DELETE:
                                # Remove segment
                                for i, segment in enumerate(section.segments):
                                    if segment.id == segment_id:
                                        section.segments.pop(i)
                                        break
                                
                                # Update positions
                                for i, seg in enumerate(section.segments):
                                    seg.position = i
                            
                            elif segment_diff.diff_type == DiffType.REPLACE:
                                # Update segment content
                                for segment in section.segments:
                                    if segment.id == segment_id and segment_diff.new_content:
                                        segment.content = segment_diff.new_content
                                        break
                        
                        break
        
        # Update document's current revision
        self.document.current_revision = target_revision
        
        return target_revision
    
    def merge_revisions(
        self, 
        base_revision_name: str, 
        revision_names: List[str], 
        merge_strategy: Dict[str, str] = None
    ) -> Optional[Revision]:
        """Merge multiple revisions into a new revision."""
        # Get base revision
        base_revision = self.document.get_revision(base_revision_name)
        if not base_revision:
            return None
        
        # Create a new revision based on the base revision
        merged_revision_name = f"Merged_{base_revision_name}_{'_'.join(revision_names)}"
        merged_revision = self.create_revision(
            name=merged_revision_name,
            metadata={"merged_from": [base_revision_name] + revision_names}
        )
        
        # Default merge strategy: last writer wins
        if not merge_strategy:
            merge_strategy = {}
        
        # Apply diffs from each revision
        for revision_name in revision_names:
            # Compare with base revision
            diff = self.compare_revisions(base_revision_name, revision_name)
            if not diff:
                continue
            
            # Apply changes
            for section_diff in diff.section_diffs:
                section_id = section_diff.section_id
                
                # Check merge strategy for this section
                section_strategy = merge_strategy.get(section_id, "last_writer_wins")
                
                if section_strategy == "ignore":
                    # Skip this section
                    continue
                
                if section_diff.diff_type == DiffType.INSERT:
                    # Add new section
                    new_section = Section(
                        id=section_id,
                        title=section_diff.new_title or "",
                        segments=[]
                    )
                    
                    # Add segment diffs
                    for segment_diff in section_diff.segment_diffs:
                        if segment_diff.diff_type == DiffType.INSERT:
                            segment = TextSegment(
                                id=segment_diff.segment_id or "",
                                content=segment_diff.new_content or "",
                                position=segment_diff.position or 0
                            )
                            new_section.segments.append(segment)
                    
                    # Add to merged revision
                    merged_revision.sections.append(new_section)
                
                elif section_diff.diff_type == DiffType.DELETE:
                    if section_strategy == "last_writer_wins":
                        # Remove section
                        for i, section in enumerate(merged_revision.sections):
                            if section.id == section_id:
                                merged_revision.sections.pop(i)
                                break
                
                elif section_diff.diff_type in (DiffType.REPLACE, DiffType.EQUAL):
                    # Update section title if it changed
                    for section in merged_revision.sections:
                        if section.id == section_id:
                            if section_diff.new_title and section_strategy == "last_writer_wins":
                                section.title = section_diff.new_title
                            
                            # Process segment changes
                            for segment_diff in section_diff.segment_diffs:
                                segment_id = segment_diff.segment_id
                                
                                # Check merge strategy for this segment
                                segment_strategy = merge_strategy.get(f"{section_id}_{segment_id}", section_strategy)
                                
                                if segment_strategy == "ignore":
                                    # Skip this segment
                                    continue
                                
                                if segment_diff.diff_type == DiffType.INSERT:
                                    # Add new segment
                                    segment = TextSegment(
                                        id=segment_id or "",
                                        content=segment_diff.new_content or "",
                                        position=segment_diff.position or 0
                                    )
                                    
                                    # Insert at the right position
                                    if segment_diff.position is not None:
                                        if segment_diff.position < len(section.segments):
                                            section.segments.insert(segment_diff.position, segment)
                                        else:
                                            section.segments.append(segment)
                                    else:
                                        section.segments.append(segment)
                                    
                                    # Update positions
                                    for i, seg in enumerate(section.segments):
                                        seg.position = i
                                
                                elif segment_diff.diff_type == DiffType.DELETE:
                                    if segment_strategy == "last_writer_wins":
                                        # Remove segment
                                        for i, segment in enumerate(section.segments):
                                            if segment.id == segment_id:
                                                section.segments.pop(i)
                                                break
                                        
                                        # Update positions
                                        for i, seg in enumerate(section.segments):
                                            seg.position = i
                                
                                elif segment_diff.diff_type == DiffType.REPLACE:
                                    if segment_strategy == "last_writer_wins":
                                        # Update segment content
                                        for segment in section.segments:
                                            if segment.id == segment_id and segment_diff.new_content:
                                                segment.content = segment_diff.new_content
                                                break
                            
                            break
        
        # Update document's current revision
        self.document.current_revision = merged_revision
        
        return merged_revision
    
    def export_revision_history(self) -> Dict[str, Any]:
        """Export the revision history as a structured dictionary."""
        history = {
            "current_revision": self.document.current_revision.name,
            "revisions": {}
        }
        
        for name, revision in self.document.revisions.items():
            history["revisions"][name] = {
                "id": revision.id,
                "timestamp": revision.timestamp.isoformat(),
                "metadata": revision.metadata,
                "section_count": len(revision.sections),
                "word_count": sum(
                    sum(segment.get_word_count() for segment in section.segments)
                    for section in revision.sections
                )
            }
        
        return history
    
    def get_revision_by_timestamp(self, timestamp: datetime) -> Optional[Revision]:
        """Get the revision closest to the specified timestamp."""
        closest_revision = None
        min_diff = None
        
        for revision in self.document.revisions.values():
            diff = abs((revision.timestamp - timestamp).total_seconds())
            
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_revision = revision
        
        return closest_revision