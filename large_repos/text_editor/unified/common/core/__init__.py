"""Core components of the unified text editor library."""

from common.core.models import (
    BaseModel, Position, Range, Metadata, TextSegment, Section
)
from common.core.buffer import (
    IBuffer, BaseBuffer, TextBuffer
)
from common.core.cursor import Cursor
from common.core.history import (
    OperationType, EditOperation, History, RevisionHistory
)
from common.core.document import (
    IDocument, Document, Revision
)
from common.core.file_manager import (
    FileFormat, FileManager, FormatHandler,
    PlainTextHandler, MarkdownHandler, JsonHandler
)
from common.core import utils

__all__ = [
    # Models
    'BaseModel', 'Position', 'Range', 'Metadata', 'TextSegment', 'Section',
    # Buffer
    'IBuffer', 'BaseBuffer', 'TextBuffer',
    # Cursor
    'Cursor',
    # History
    'OperationType', 'EditOperation', 'History', 'RevisionHistory',
    # Document
    'IDocument', 'Document', 'Revision',
    # File Manager
    'FileFormat', 'FileManager', 'FormatHandler',
    'PlainTextHandler', 'MarkdownHandler', 'JsonHandler',
    # Utils
    'utils'
]
