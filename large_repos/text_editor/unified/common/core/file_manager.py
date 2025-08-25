"""Unified file management for the text editor."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Protocol, List
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
from common.core.document import Document, Section, TextSegment


class FileFormat(str, Enum):
    """Supported file formats."""
    PLAIN_TEXT = "txt"
    MARKDOWN = "md"
    JSON = "json"
    HTML = "html"


class IFormatHandler(Protocol):
    """Interface for format handlers."""
    
    def load(self, path: str) -> Document: ...
    def save(self, document: Document, path: str) -> None: ...


class FormatHandler(ABC):
    """Abstract base class for format handlers."""
    
    @abstractmethod
    def load(self, path: str) -> Document:
        """Load a document from file."""
        pass
    
    @abstractmethod
    def save(self, document: Document, path: str) -> None:
        """Save a document to file."""
        pass


class PlainTextHandler(FormatHandler):
    """Handler for plain text files."""
    
    def load(self, path: str) -> Document:
        """Load plain text file as document."""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create document with single section
        doc = Document(title=Path(path).stem)
        section = doc.add_section()
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                section.add_segment(para.strip())
        
        doc.file_path = path
        return doc
    
    def save(self, document: Document, path: str) -> None:
        """Save document as plain text."""
        content = document.get_content()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


class MarkdownHandler(FormatHandler):
    """Handler for Markdown files."""
    
    def load(self, path: str) -> Document:
        """Load Markdown file as document."""
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        doc = Document(title=Path(path).stem)
        current_section = None
        current_content = []
        
        for line in lines:
            # Check for section header
            if line.startswith('# '):
                # Save previous section if exists
                if current_section and current_content:
                    content = ''.join(current_content).strip()
                    if content:
                        # Split into paragraphs
                        for para in content.split('\n\n'):
                            if para.strip():
                                current_section.add_segment(para.strip())
                
                # Start new section
                title = line[2:].strip()
                current_section = doc.add_section(title=title)
                current_content = []
            
            elif line.startswith('## ') and current_section:
                # Sub-header as new segment
                if current_content:
                    content = ''.join(current_content).strip()
                    if content:
                        current_section.add_segment(content)
                    current_content = []
                
                # Add sub-header as segment
                current_section.add_segment(line.strip())
            
            else:
                # Regular content
                if not current_section:
                    current_section = doc.add_section()
                current_content.append(line)
        
        # Save final section content
        if current_section and current_content:
            content = ''.join(current_content).strip()
            if content:
                # Split into paragraphs
                for para in content.split('\n\n'):
                    if para.strip():
                        current_section.add_segment(para.strip())
        
        doc.file_path = path
        return doc
    
    def save(self, document: Document, path: str) -> None:
        """Save document as Markdown."""
        lines = []
        
        for section in document.current_revision.sections:
            if section.title:
                lines.append(f"# {section.title}\n")
            
            for segment in section.segments:
                lines.append(segment.content)
                lines.append("")  # Empty line between segments
            
            lines.append("")  # Extra empty line between sections
        
        content = '\n'.join(lines)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


class JsonHandler(FormatHandler):
    """Handler for JSON format."""
    
    def load(self, path: str) -> Document:
        """Load JSON file as document."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        doc = Document(title=data.get('title', 'Untitled'))
        
        # Load metadata
        if 'metadata' in data:
            doc.metadata.tags = data['metadata'].get('tags', {})
        
        # Load sections
        for section_data in data.get('sections', []):
            section = doc.add_section(
                title=section_data.get('title', ''),
                metadata=section_data.get('metadata', {})
            )
            
            # Load segments
            for segment_data in section_data.get('segments', []):
                section.add_segment(
                    content=segment_data.get('content', ''),
                    metadata=segment_data.get('metadata', {})
                )
        
        doc.file_path = path
        return doc
    
    def save(self, document: Document, path: str) -> None:
        """Save document as JSON."""
        data = {
            'title': document.title,
            'metadata': {
                'id': document.metadata.id,
                'created_at': document.metadata.created_at.isoformat(),
                'updated_at': document.metadata.updated_at.isoformat(),
                'tags': document.metadata.tags
            },
            'sections': []
        }
        
        for section in document.current_revision.sections:
            section_data = {
                'id': section.id,
                'title': section.title,
                'metadata': section.metadata,
                'segments': []
            }
            
            for segment in section.segments:
                segment_data = {
                    'id': segment.id,
                    'content': segment.content,
                    'position': segment.position,
                    'metadata': segment.metadata
                }
                section_data['segments'].append(segment_data)
            
            data['sections'].append(section_data)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


class FileManager:
    """Unified file manager for document I/O."""
    
    handlers: Dict[FileFormat, FormatHandler] = {
        FileFormat.PLAIN_TEXT: PlainTextHandler(),
        FileFormat.MARKDOWN: MarkdownHandler(),
        FileFormat.JSON: JsonHandler()
    }
    
    @classmethod
    def detect_format(cls, path: str) -> FileFormat:
        """Detect file format from extension."""
        ext = Path(path).suffix.lower().lstrip('.')
        
        if ext in ['txt', 'text']:
            return FileFormat.PLAIN_TEXT
        elif ext in ['md', 'markdown']:
            return FileFormat.MARKDOWN
        elif ext == 'json':
            return FileFormat.JSON
        else:
            # Default to plain text
            return FileFormat.PLAIN_TEXT
    
    @classmethod
    def load(cls, path: str, format: Optional[FileFormat] = None) -> Document:
        """Load a document from file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        if format is None:
            format = cls.detect_format(path)
        
        handler = cls.handlers.get(format)
        if not handler:
            raise ValueError(f"Unsupported format: {format}")
        
        return handler.load(path)
    
    @classmethod
    def save(cls, document: Document, path: str, format: Optional[FileFormat] = None) -> None:
        """Save a document to file."""
        if format is None:
            format = cls.detect_format(path)
        
        handler = cls.handlers.get(format)
        if not handler:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create directory if needed
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        handler.save(document, path)
        document.file_path = path
    
    @classmethod
    def create_backup(cls, document: Document, backup_dir: str = ".backups") -> str:
        """Create a backup of the document."""
        from datetime import datetime
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document.title}_{timestamp}.json"
        backup_path = os.path.join(backup_dir, filename)
        
        # Save as JSON for full data preservation
        cls.save(document, backup_path, FileFormat.JSON)
        
        return backup_path
    
    @classmethod
    def list_backups(cls, backup_dir: str = ".backups") -> List[Dict[str, Any]]:
        """List available backups."""
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                path = os.path.join(backup_dir, filename)
                stat = os.stat(path)
                backups.append({
                    'filename': filename,
                    'path': path,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
        
        # Sort by modification time, newest first
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups