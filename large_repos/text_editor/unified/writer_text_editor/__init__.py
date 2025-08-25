"""Writer Text Editor - A specialized text editor library for fiction writers."""

from writer_text_editor.document import Document, Section, TextSegment, Revision
from writer_text_editor.focus import FocusMode, FocusLevel, FocusContext
from writer_text_editor.statistics import WritingStatistics, ReadingLevel, DocumentStats
from writer_text_editor.narrative import NarrativeTracker, ElementType, NarrativeElement
from writer_text_editor.navigation import DocumentNavigator, NavigationViewType
from writer_text_editor.revision import RevisionManager, DiffType
from writer_text_editor.client import WriterTextEditor

__version__ = "0.1.0"

__all__ = [
    "Document", "Section", "TextSegment", "Revision",
    "FocusMode", "FocusLevel", "FocusContext",
    "WritingStatistics", "ReadingLevel", "DocumentStats",
    "NarrativeTracker", "ElementType", "NarrativeElement",
    "DocumentNavigator", "NavigationViewType",
    "RevisionManager", "DiffType",
    "WriterTextEditor"
]