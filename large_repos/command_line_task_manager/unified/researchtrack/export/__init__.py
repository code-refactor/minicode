"""
Academic Markdown Export module for research documentation.

This module provides functionality for creating academic documents with proper
formatting for various journal styles, and exporting them to markdown.
"""

from researchtrack.export.models import (
    Document, Section, TextBlock, ImageBlock,
    TableBlock, CodeBlock, EquationBlock, CitationBlock, JournalFormat
)
from researchtrack.export.storage import ExportStorageInterface, InMemoryExportStorage
from researchtrack.export.formatter import ExportFormatter
from researchtrack.export.service import ExportService

__all__ = [
    # Models
    "Document", "Section", "TextBlock",
    "ImageBlock", "TableBlock", "CodeBlock",
    "EquationBlock", "CitationBlock", "JournalFormat",

    # Storage
    "ExportStorageInterface", "InMemoryExportStorage",

    # Formatter
    "ExportFormatter",

    # Service
    "ExportService",
]