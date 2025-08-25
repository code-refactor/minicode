"""Result formatting and data transformation utilities for the unified query language interpreter."""

import json
import csv
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TextIO
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from io import StringIO

from ..core.base_models import QueryResult, BaseDocument


class OutputFormat(str, Enum):
    """Supported output formats for query results."""
    
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    HTML = "html"
    YAML = "yaml"
    TSV = "tsv"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class DataTransformationType(str, Enum):
    """Types of data transformations that can be applied."""
    
    FLATTEN = "flatten"
    NORMALIZE = "normalize"
    AGGREGATE = "aggregate"
    PIVOT = "pivot"
    FILTER = "filter"
    SORT = "sort"
    GROUP = "group"
    JOIN = "join"
    UNION = "union"


class BaseFormatter(ABC):
    """Base class for result formatters."""
    
    @abstractmethod
    def format(self, data: Any, **kwargs) -> str:
        """Format data into a string representation.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
            
        Returns:
            Formatted string
        """
        pass
    
    @abstractmethod
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if this formatter supports a specific format.
        
        Args:
            format_type: Format type to check
            
        Returns:
            True if format is supported
        """
        pass


class JSONFormatter(BaseFormatter):
    """Formatter for JSON output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as JSON.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
                - indent: Number of spaces for indentation
                - sort_keys: Whether to sort keys
                
        Returns:
            JSON string
        """
        indent = kwargs.get('indent', 2)
        sort_keys = kwargs.get('sort_keys', True)
        
        return json.dumps(
            self._serialize_for_json(data),
            indent=indent,
            sort_keys=sort_keys,
            default=self._json_default
        )
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if JSON format is supported."""
        return format_type == OutputFormat.JSON
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Serialize object for JSON output."""
        if hasattr(obj, 'dict'):  # Pydantic models
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        else:
            return obj
    
    def _json_default(self, obj: Any) -> Any:
        """Default JSON serializer for non-serializable objects."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, 'dict'):  # Pydantic models
            return obj.dict()
        else:
            return str(obj)


class CSVFormatter(BaseFormatter):
    """Formatter for CSV output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as CSV.
        
        Args:
            data: Data to format (should be list of dicts or similar)
            **kwargs: Additional formatting options
                - delimiter: Field delimiter (default: ',')
                - include_header: Whether to include header row
                
        Returns:
            CSV string
        """
        delimiter = kwargs.get('delimiter', ',')
        include_header = kwargs.get('include_header', True)
        
        if not data:
            return ""
        
        # Convert data to list of dictionaries
        rows = self._convert_to_rows(data)
        if not rows:
            return ""
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=delimiter)
        
        if include_header:
            writer.writeheader()
        
        for row in rows:
            # Convert non-string values to strings
            string_row = {k: self._format_cell_value(v) for k, v in row.items()}
            writer.writerow(string_row)
        
        return output.getvalue()
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if CSV format is supported."""
        return format_type in [OutputFormat.CSV, OutputFormat.TSV]
    
    def _convert_to_rows(self, data: Any) -> List[Dict[str, Any]]:
        """Convert data to list of dictionaries for CSV output."""
        if isinstance(data, list):
            rows = []
            for item in data:
                if hasattr(item, 'dict'):  # Pydantic model
                    rows.append(item.dict())
                elif isinstance(item, dict):
                    rows.append(item)
                elif hasattr(item, '__dict__'):
                    rows.append(item.__dict__)
                else:
                    # Single value - create a row with 'value' column
                    rows.append({'value': item})
            return rows
        elif isinstance(data, dict):
            return [data]
        elif hasattr(data, 'dict'):  # Pydantic model
            return [data.dict()]
        else:
            return [{'value': data}]
    
    def _format_cell_value(self, value: Any) -> str:
        """Format a cell value for CSV output."""
        if value is None:
            return ""
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, (list, dict)):
            return json.dumps(value)
        else:
            return str(value)


class XMLFormatter(BaseFormatter):
    """Formatter for XML output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as XML.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
                - root_element: Name of root XML element
                - item_element: Name of item elements for lists
                
        Returns:
            XML string
        """
        root_element = kwargs.get('root_element', 'data')
        item_element = kwargs.get('item_element', 'item')
        
        root = ET.Element(root_element)
        self._build_xml_element(root, data, item_element)
        
        return ET.tostring(root, encoding='unicode')
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if XML format is supported."""
        return format_type == OutputFormat.XML
    
    def _build_xml_element(self, parent: ET.Element, data: Any, item_element: str) -> None:
        """Build XML elements recursively."""
        if isinstance(data, dict):
            for key, value in data.items():
                child = ET.SubElement(parent, str(key))
                if isinstance(value, (dict, list)):
                    self._build_xml_element(child, value, item_element)
                else:
                    child.text = str(value) if value is not None else ""
        elif isinstance(data, list):
            for item in data:
                child = ET.SubElement(parent, item_element)
                self._build_xml_element(child, item, item_element)
        else:
            parent.text = str(data) if data is not None else ""


class HTMLFormatter(BaseFormatter):
    """Formatter for HTML table output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as HTML table.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
                - table_class: CSS class for table
                - include_header: Whether to include header row
                
        Returns:
            HTML string
        """
        table_class = kwargs.get('table_class', 'query-results')
        include_header = kwargs.get('include_header', True)
        
        rows = self._convert_to_rows(data)
        if not rows:
            return "<p>No data</p>"
        
        html = [f'<table class="{table_class}">']
        
        # Add header
        if include_header and rows:
            html.append('<thead><tr>')
            for header in rows[0].keys():
                html.append(f'<th>{self._escape_html(str(header))}</th>')
            html.append('</tr></thead>')
        
        # Add data rows
        html.append('<tbody>')
        for row in rows:
            html.append('<tr>')
            for value in row.values():
                formatted_value = self._format_html_cell(value)
                html.append(f'<td>{formatted_value}</td>')
            html.append('</tr>')
        html.append('</tbody>')
        
        html.append('</table>')
        return '\n'.join(html)
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if HTML format is supported."""
        return format_type == OutputFormat.HTML
    
    def _convert_to_rows(self, data: Any) -> List[Dict[str, Any]]:
        """Convert data to list of dictionaries for HTML table."""
        # Reuse CSV formatter logic
        csv_formatter = CSVFormatter()
        return csv_formatter._convert_to_rows(data)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
    
    def _format_html_cell(self, value: Any) -> str:
        """Format a cell value for HTML output."""
        if value is None:
            return ""
        elif isinstance(value, (datetime, date)):
            return self._escape_html(value.isoformat())
        elif isinstance(value, (list, dict)):
            return self._escape_html(json.dumps(value))
        else:
            return self._escape_html(str(value))


class MarkdownFormatter(BaseFormatter):
    """Formatter for Markdown table output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as Markdown table.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
                
        Returns:
            Markdown string
        """
        rows = self._convert_to_rows(data)
        if not rows:
            return "No data"
        
        headers = list(rows[0].keys())
        
        # Build markdown table
        lines = []
        
        # Header row
        header_line = "| " + " | ".join(headers) + " |"
        lines.append(header_line)
        
        # Separator row
        separator_line = "|" + "|".join([" --- "] * len(headers)) + "|"
        lines.append(separator_line)
        
        # Data rows
        for row in rows:
            values = [self._format_markdown_cell(row.get(header, "")) for header in headers]
            data_line = "| " + " | ".join(values) + " |"
            lines.append(data_line)
        
        return "\n".join(lines)
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if Markdown format is supported."""
        return format_type == OutputFormat.MARKDOWN
    
    def _convert_to_rows(self, data: Any) -> List[Dict[str, Any]]:
        """Convert data to list of dictionaries for Markdown table."""
        # Reuse CSV formatter logic
        csv_formatter = CSVFormatter()
        return csv_formatter._convert_to_rows(data)
    
    def _format_markdown_cell(self, value: Any) -> str:
        """Format a cell value for Markdown output."""
        if value is None:
            return ""
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, (list, dict)):
            return json.dumps(value).replace("|", "\\|")
        else:
            return str(value).replace("|", "\\|")


class PlainTextFormatter(BaseFormatter):
    """Formatter for plain text output."""
    
    def format(self, data: Any, **kwargs) -> str:
        """Format data as plain text.
        
        Args:
            data: Data to format
            **kwargs: Additional formatting options
                - separator: Field separator
                - include_labels: Whether to include field labels
                
        Returns:
            Plain text string
        """
        separator = kwargs.get('separator', ': ')
        include_labels = kwargs.get('include_labels', True)
        
        if isinstance(data, (QueryResult, BaseDocument)):
            return self._format_model(data, separator, include_labels)
        elif isinstance(data, dict):
            return self._format_dict(data, separator, include_labels)
        elif isinstance(data, list):
            return self._format_list(data, separator, include_labels)
        else:
            return str(data)
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if plain text format is supported."""
        return format_type == OutputFormat.PLAIN_TEXT
    
    def _format_model(self, model: Any, separator: str, include_labels: bool) -> str:
        """Format a Pydantic model as plain text."""
        if hasattr(model, 'dict'):
            return self._format_dict(model.dict(), separator, include_labels)
        else:
            return str(model)
    
    def _format_dict(self, data: Dict[str, Any], separator: str, include_labels: bool) -> str:
        """Format a dictionary as plain text."""
        lines = []
        for key, value in data.items():
            if include_labels:
                if isinstance(value, (dict, list)):
                    lines.append(f"{key}{separator}")
                    nested = self.format(value, separator=separator, include_labels=include_labels)
                    indented = '\n'.join(f"  {line}" for line in nested.split('\n'))
                    lines.append(indented)
                else:
                    lines.append(f"{key}{separator}{value}")
            else:
                lines.append(str(value))
        return '\n'.join(lines)
    
    def _format_list(self, data: List[Any], separator: str, include_labels: bool) -> str:
        """Format a list as plain text."""
        lines = []
        for i, item in enumerate(data):
            if include_labels:
                lines.append(f"Item {i + 1}:")
            item_text = self.format(item, separator=separator, include_labels=include_labels)
            if include_labels:
                indented = '\n'.join(f"  {line}" for line in item_text.split('\n'))
                lines.append(indented)
            else:
                lines.append(item_text)
        return '\n'.join(lines)


class ResultFormatter:
    """Main formatter that delegates to specific format handlers."""
    
    def __init__(self):
        """Initialize the result formatter."""
        self.formatters: Dict[OutputFormat, BaseFormatter] = {
            OutputFormat.JSON: JSONFormatter(),
            OutputFormat.CSV: CSVFormatter(),
            OutputFormat.TSV: CSVFormatter(),
            OutputFormat.XML: XMLFormatter(),
            OutputFormat.HTML: HTMLFormatter(),
            OutputFormat.MARKDOWN: MarkdownFormatter(),
            OutputFormat.PLAIN_TEXT: PlainTextFormatter()
        }
    
    def register_formatter(self, format_type: OutputFormat, formatter: BaseFormatter) -> None:
        """Register a custom formatter.
        
        Args:
            format_type: Format type
            formatter: Formatter instance
        """
        self.formatters[format_type] = formatter
    
    def format(
        self,
        data: Any,
        format_type: OutputFormat = OutputFormat.JSON,
        **kwargs
    ) -> str:
        """Format data in the specified format.
        
        Args:
            data: Data to format
            format_type: Output format
            **kwargs: Additional formatting options
            
        Returns:
            Formatted string
            
        Raises:
            ValueError: If format is not supported
        """
        formatter = self.formatters.get(format_type)
        if not formatter:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Special handling for TSV
        if format_type == OutputFormat.TSV:
            kwargs['delimiter'] = '\t'
        
        return formatter.format(data, **kwargs)
    
    def format_query_result(
        self,
        result: QueryResult,
        format_type: OutputFormat = OutputFormat.JSON,
        **kwargs
    ) -> str:
        """Format a query result.
        
        Args:
            result: Query result to format
            format_type: Output format
            **kwargs: Additional formatting options
            
        Returns:
            Formatted string
        """
        return self.format(result, format_type, **kwargs)
    
    def supports_format(self, format_type: OutputFormat) -> bool:
        """Check if a format is supported.
        
        Args:
            format_type: Format to check
            
        Returns:
            True if format is supported
        """
        return format_type in self.formatters


class DataTransformer:
    """Utility class for transforming data structures."""
    
    def __init__(self):
        """Initialize the data transformer."""
        self.transformers = {
            DataTransformationType.FLATTEN: self._flatten_data,
            DataTransformationType.NORMALIZE: self._normalize_data,
            DataTransformationType.FILTER: self._filter_data,
            DataTransformationType.SORT: self._sort_data,
            DataTransformationType.GROUP: self._group_data
        }
    
    def transform(
        self,
        data: Any,
        transformation_type: DataTransformationType,
        **kwargs
    ) -> Any:
        """Transform data using the specified transformation.
        
        Args:
            data: Data to transform
            transformation_type: Type of transformation
            **kwargs: Transformation parameters
            
        Returns:
            Transformed data
            
        Raises:
            ValueError: If transformation type is not supported
        """
        transformer = self.transformers.get(transformation_type)
        if not transformer:
            raise ValueError(f"Unsupported transformation: {transformation_type}")
        
        return transformer(data, **kwargs)
    
    def _flatten_data(self, data: Any, **kwargs) -> Any:
        """Flatten nested data structures."""
        separator = kwargs.get('separator', '.')
        
        if isinstance(data, dict):
            return self._flatten_dict(data, separator)
        elif isinstance(data, list):
            return [self._flatten_data(item, separator=separator) for item in data]
        else:
            return data
    
    def _flatten_dict(self, data: Dict[str, Any], separator: str, prefix: str = '') -> Dict[str, Any]:
        """Flatten a nested dictionary."""
        flattened = {}
        
        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, separator, new_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flattened.update(self._flatten_dict(item, separator, f"{new_key}{separator}{i}"))
                    else:
                        flattened[f"{new_key}{separator}{i}"] = item
            else:
                flattened[new_key] = value
        
        return flattened
    
    def _normalize_data(self, data: Any, **kwargs) -> Any:
        """Normalize data (convert to consistent format)."""
        if isinstance(data, list):
            # Ensure all items have the same keys
            all_keys = set()
            for item in data:
                if isinstance(item, dict):
                    all_keys.update(item.keys())
            
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    normalized_item = {key: item.get(key) for key in all_keys}
                    normalized.append(normalized_item)
                else:
                    normalized.append(item)
            
            return normalized
        else:
            return data
    
    def _filter_data(self, data: Any, **kwargs) -> Any:
        """Filter data based on criteria."""
        filter_func = kwargs.get('filter_func')
        if not filter_func:
            return data
        
        if isinstance(data, list):
            return [item for item in data if filter_func(item)]
        elif isinstance(data, dict):
            return {key: value for key, value in data.items() if filter_func({key: value})}
        else:
            return data if filter_func(data) else None
    
    def _sort_data(self, data: Any, **kwargs) -> Any:
        """Sort data."""
        if not isinstance(data, list):
            return data
        
        sort_key = kwargs.get('sort_key')
        reverse = kwargs.get('reverse', False)
        
        if sort_key:
            if isinstance(sort_key, str):
                # Sort by dictionary key
                return sorted(data, key=lambda x: x.get(sort_key) if isinstance(x, dict) else x, reverse=reverse)
            else:
                # Sort by function
                return sorted(data, key=sort_key, reverse=reverse)
        else:
            return sorted(data, reverse=reverse)
    
    def _group_data(self, data: Any, **kwargs) -> Any:
        """Group data by key."""
        if not isinstance(data, list):
            return data
        
        group_key = kwargs.get('group_key')
        if not group_key:
            return data
        
        groups = {}
        for item in data:
            if isinstance(item, dict):
                key_value = item.get(group_key)
            else:
                key_value = str(item)
            
            if key_value not in groups:
                groups[key_value] = []
            groups[key_value].append(item)
        
        return groups


# Default instances
default_formatter = ResultFormatter()
default_transformer = DataTransformer()