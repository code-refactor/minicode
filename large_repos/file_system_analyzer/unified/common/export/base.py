"""
Base exporter class for the File System Analyzer unified library.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.base import BaseExporter as CoreBaseExporter
from ..core.types import ExportFormat, FilePath


class BaseExporter(CoreBaseExporter):
    """Enhanced base exporter with common functionality."""
    
    def __init__(self, output_dir: Optional[FilePath] = None):
        super().__init__()
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _ensure_serializable(self, data: Any) -> Any:
        """Ensure data is serializable."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, Path):
            return str(data)
        elif isinstance(data, dict):
            return {k: self._ensure_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._ensure_serializable(item) for item in data]
        elif hasattr(data, '__dict__'):
            return self._ensure_serializable(data.__dict__)
        return data
        
    def _format_bytes(self, size_bytes: int) -> str:
        """Format bytes to human readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
        
    def validate(self) -> bool:
        """Validate exporter configuration."""
        return self.output_dir.exists() and self.output_dir.is_dir()