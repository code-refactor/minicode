"""
Multi-format exporter for the File System Analyzer unified library.
"""

from typing import Any, List, Set, Dict
from pathlib import Path

from ..core.types import ExportFormat, FilePath
from .base import BaseExporter
from .json_exporter import JsonExporter
from .csv_exporter import CsvExporter
from .html_exporter import HtmlExporter


class MultiFormatExporter(BaseExporter):
    """Exporter that supports multiple output formats."""
    
    def __init__(self, output_dir: FilePath = None):
        super().__init__(output_dir)
        self.exporters = {
            ExportFormat.JSON: JsonExporter(output_dir),
            ExportFormat.CSV: CsvExporter(output_dir), 
            ExportFormat.HTML: HtmlExporter(output_dir)
        }
        
    def export(self, data: Any, output_path: FilePath, formats: Set[ExportFormat] = None, **kwargs) -> bool:
        """Export data in multiple formats."""
        if formats is None:
            formats = {ExportFormat.JSON}
            
        success_count = 0
        base_path = Path(output_path)
        
        for format_type in formats:
            if format_type in self.exporters:
                # Generate format-specific filename
                format_path = base_path.with_suffix(f'.{format_type.value}')
                
                try:
                    exporter = self.exporters[format_type]
                    if exporter.export(data, format_path, **kwargs):
                        success_count += 1
                        self.logger.info(f"Successfully exported {format_type.value} to {format_path}")
                    else:
                        self.logger.error(f"Failed to export {format_type.value}")
                except Exception as e:
                    self.logger.error(f"Error exporting {format_type.value}: {e}")
            else:
                self.logger.warning(f"Unsupported format: {format_type}")
                
        return success_count > 0
        
    def export_all_formats(self, data: Any, base_name: str, **kwargs) -> Dict[ExportFormat, bool]:
        """Export data in all supported formats."""
        results = {}
        
        for format_type, exporter in self.exporters.items():
            output_path = self.output_dir / f"{base_name}.{format_type.value}"
            try:
                results[format_type] = exporter.export(data, output_path, **kwargs)
            except Exception as e:
                self.logger.error(f"Error exporting {format_type.value}: {e}")
                results[format_type] = False
                
        return results
        
    def get_supported_formats(self) -> List[str]:
        """Get all supported formats."""
        formats = []
        for exporter in self.exporters.values():
            formats.extend(exporter.get_supported_formats())
        return list(set(formats))
        
    def validate_configuration(self) -> bool:
        """
        Validate the MultiFormatExporter configuration.
        
        Returns:
            True if all exporters have valid configurations, False otherwise
        """
        # First validate the base configuration (output directory)
        if not super().validate():
            return False
            
        # Validate each child exporter
        for format_type, exporter in self.exporters.items():
            try:
                if not exporter.validate_configuration():
                    self.logger.error(f"Invalid configuration for {format_type.value} exporter")
                    return False
            except Exception as e:
                self.logger.error(f"Error validating {format_type.value} exporter: {e}")
                return False
                
        return True