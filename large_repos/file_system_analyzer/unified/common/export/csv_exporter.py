"""
CSV exporter for the File System Analyzer unified library.
"""

import csv
import json
from datetime import datetime
from typing import Any, List, Dict

from ..core.types import FilePath
from .base import BaseExporter


class CsvExporter(BaseExporter):
    """CSV format exporter with data flattening."""
    
    def export(self, data: Any, output_path: FilePath, **kwargs) -> bool:
        """Export data to CSV format."""
        try:
            # Convert data to list of dictionaries
            if isinstance(data, dict):
                if 'results' in data and isinstance(data['results'], list):
                    csv_data = self._flatten_results(data['results'])
                else:
                    csv_data = [self._flatten_dict(data)]
            elif isinstance(data, list):
                csv_data = [self._flatten_dict(item) for item in data]
            else:
                csv_data = [{'value': str(data)}]
                
            if not csv_data:
                csv_data = [{'message': 'No data to export'}]
                
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if csv_data:
                    fieldnames = list(csv_data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV to {output_path}: {e}")
            return False
            
    def _flatten_dict(self, data: Dict, prefix: str = '') -> Dict[str, Any]:
        """Flatten nested dictionaries for CSV export."""
        flattened = {}
        
        for key, value in data.items():
            new_key = f"{prefix}_{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, new_key))
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Handle list of dictionaries
                    flattened[f"{new_key}_count"] = len(value)
                    for i, item in enumerate(value[:3]):  # Limit to first 3 items
                        flattened.update(self._flatten_dict(item, f"{new_key}_{i}"))
                else:
                    flattened[new_key] = json.dumps(value) if value else ''
            else:
                flattened[new_key] = str(value) if value is not None else ''
                
        return flattened
        
    def _flatten_results(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Flatten a list of results for CSV export."""
        flattened_results = []
        
        for result in results:
            if hasattr(result, '__dict__'):
                result_dict = result.__dict__
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {'result': str(result)}
                
            flattened_results.append(self._flatten_dict(result_dict))
            
        return flattened_results
        
    def get_supported_formats(self) -> List[str]:
        """Get supported formats."""
        return ['csv']
        
    def validate_configuration(self) -> bool:
        """
        Validate the CsvExporter configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        # Validate base configuration (output directory)
        return super().validate()