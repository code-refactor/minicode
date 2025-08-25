"""
JSON exporter for the File System Analyzer unified library.
"""

import json
from datetime import datetime
from typing import Any, List

from ..core.types import FilePath
from .base import BaseExporter


class JsonExporter(BaseExporter):
    """JSON format exporter."""
    
    def export(self, data: Any, output_path: FilePath, pretty_print: bool = True, **kwargs) -> bool:
        """Export data to JSON format."""
        try:
            serializable_data = self._ensure_serializable(data)
            
            # Add export metadata
            if isinstance(serializable_data, dict):
                serializable_data['_export_metadata'] = {
                    'timestamp': datetime.now().isoformat(),
                    'format': 'json',
                    'exporter': 'JsonExporter'
                }
                
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(serializable_data, f, indent=2, default=str, ensure_ascii=False)
                else:
                    json.dump(serializable_data, f, default=str, ensure_ascii=False)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting JSON to {output_path}: {e}")
            return False
            
    def get_supported_formats(self) -> List[str]:
        """Get supported formats."""
        return ['json']
        
    def validate_configuration(self) -> bool:
        """
        Validate the JsonExporter configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        # Validate base configuration (output directory)
        return super().validate()