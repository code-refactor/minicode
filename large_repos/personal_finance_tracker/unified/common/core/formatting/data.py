"""
Data serialization and formatting utilities.

This module provides functions for serializing, deserializing, and formatting
financial data for storage, transmission, and display purposes.
"""

import json
import csv
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Union, TextIO, Callable
from dataclasses import asdict, is_dataclass
from enum import Enum
import io

# Import from our models
from ..models.money import Money, Currency
from ..models.time_period import Period, PeriodType


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    CSV = "csv"
    TSV = "tsv"
    DICT = "dict"


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for financial data types."""
    
    def default(self, obj):
        """Convert special types to JSON-serializable format."""
        if isinstance(obj, datetime):
            return {
                "_type": "datetime",
                "value": obj.isoformat()
            }
        elif isinstance(obj, date):
            return {
                "_type": "date",
                "value": obj.isoformat()
            }
        elif isinstance(obj, timedelta):
            return {
                "_type": "timedelta",
                "value": obj.total_seconds()
            }
        elif isinstance(obj, Decimal):
            return {
                "_type": "decimal",
                "value": str(obj)
            }
        elif isinstance(obj, Money):
            return {
                "_type": "money",
                "amount": str(obj.amount),
                "currency": obj.currency.value
            }
        elif isinstance(obj, Currency):
            return {
                "_type": "currency",
                "value": obj.value
            }
        elif isinstance(obj, Period):
            return {
                "_type": "period",
                "start_date": obj.start_date.isoformat(),
                "end_date": obj.end_date.isoformat()
            }
        elif isinstance(obj, PeriodType):
            return {
                "_type": "period_type",
                "value": obj.value
            }
        elif isinstance(obj, Enum):
            return {
                "_type": "enum",
                "class": obj.__class__.__name__,
                "value": obj.value
            }
        elif is_dataclass(obj):
            return {
                "_type": "dataclass",
                "class": obj.__class__.__name__,
                "data": asdict(obj)
            }
        
        return super().default(obj)


def datetime_decoder(dct: Dict[str, Any]) -> Any:
    """Custom JSON decoder for financial data types."""
    if "_type" not in dct:
        return dct
    
    obj_type = dct["_type"]
    
    if obj_type == "datetime":
        return datetime.fromisoformat(dct["value"])
    elif obj_type == "date":
        return date.fromisoformat(dct["value"])
    elif obj_type == "timedelta":
        return timedelta(seconds=dct["value"])
    elif obj_type == "decimal":
        return Decimal(dct["value"])
    elif obj_type == "money":
        return Money(
            Decimal(dct["amount"]),
            Currency(dct["currency"])
        )
    elif obj_type == "currency":
        return Currency(dct["value"])
    elif obj_type == "period":
        return Period(
            date.fromisoformat(dct["start_date"]),
            date.fromisoformat(dct["end_date"])
        )
    elif obj_type == "period_type":
        return PeriodType(dct["value"])
    
    return dct


def serialize_to_json(
    data: Any,
    indent: Optional[int] = None,
    ensure_ascii: bool = False,
    sort_keys: bool = False
) -> str:
    """
    Serialize data to JSON with custom encoder.
    
    Args:
        data: Data to serialize
        indent: JSON indentation (None for compact)
        ensure_ascii: Whether to ensure ASCII output
        sort_keys: Whether to sort dictionary keys
        
    Returns:
        JSON string
    """
    return json.dumps(
        data,
        cls=DateTimeEncoder,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys
    )


def deserialize_from_json(json_str: str) -> Any:
    """
    Deserialize JSON string with custom decoder.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        Deserialized data
    """
    return json.loads(json_str, object_hook=datetime_decoder)


def serialize_to_dict(
    data: Any,
    flatten_nested: bool = False,
    date_format: str = "iso"
) -> Dict[str, Any]:
    """
    Serialize data to dictionary format.
    
    Args:
        data: Data to serialize
        flatten_nested: Whether to flatten nested dictionaries
        date_format: Format for dates ("iso", "timestamp", "readable")
        
    Returns:
        Dictionary representation
    """
    def convert_value(value):
        if isinstance(value, datetime):
            if date_format == "timestamp":
                return value.timestamp()
            elif date_format == "readable":
                return value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return value.isoformat()
        elif isinstance(value, date):
            if date_format == "timestamp":
                return datetime.combine(value, datetime.min.time()).timestamp()
            elif date_format == "readable":
                return value.strftime("%Y-%m-%d")
            else:
                return value.isoformat()
        elif isinstance(value, (Decimal, Money)):
            return str(value)
        elif isinstance(value, Enum):
            return value.value
        elif is_dataclass(value):
            return serialize_to_dict(asdict(value), flatten_nested, date_format)
        elif isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [convert_value(item) for item in value]
        else:
            return value
    
    if is_dataclass(data):
        result = {k: convert_value(v) for k, v in asdict(data).items()}
    elif isinstance(data, dict):
        result = {k: convert_value(v) for k, v in data.items()}
    else:
        return convert_value(data)
    
    # Flatten nested dictionaries if requested
    if flatten_nested:
        result = flatten_dict(result)
    
    return result


def flatten_dict(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary structure.
    
    Args:
        data: Dictionary to flatten
        parent_key: Parent key for nested items
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)


def serialize_to_csv(
    data: List[Dict[str, Any]],
    fieldnames: Optional[List[str]] = None,
    include_headers: bool = True,
    delimiter: str = ",",
    date_format: str = "iso"
) -> str:
    """
    Serialize list of dictionaries to CSV format.
    
    Args:
        data: List of dictionaries to serialize
        fieldnames: Field names for CSV (auto-detected if None)
        include_headers: Whether to include header row
        delimiter: CSV delimiter character
        date_format: Format for dates
        
    Returns:
        CSV string
    """
    if not data:
        return ""
    
    # Convert data to serializable format
    converted_data = []
    for item in data:
        converted_item = serialize_to_dict(item, flatten_nested=True, date_format=date_format)
        converted_data.append(converted_item)
    
    # Auto-detect fieldnames if not provided
    if fieldnames is None:
        fieldnames = list(set().union(*(d.keys() for d in converted_data)))
        fieldnames.sort()  # Consistent ordering
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter=delimiter,
        extrasaction='ignore'
    )
    
    if include_headers:
        writer.writeheader()
    
    for row in converted_data:
        writer.writerow(row)
    
    return output.getvalue()


def deserialize_from_csv(
    csv_str: str,
    delimiter: str = ",",
    has_headers: bool = True,
    type_converters: Optional[Dict[str, Callable]] = None
) -> List[Dict[str, Any]]:
    """
    Deserialize CSV string to list of dictionaries.
    
    Args:
        csv_str: CSV string to deserialize
        delimiter: CSV delimiter character
        has_headers: Whether CSV has header row
        type_converters: Dictionary of field_name -> converter_function
        
    Returns:
        List of dictionaries
    """
    if not csv_str.strip():
        return []
    
    input_stream = io.StringIO(csv_str)
    
    if has_headers:
        reader = csv.DictReader(input_stream, delimiter=delimiter)
        fieldnames = reader.fieldnames
    else:
        # Read first line to determine number of columns
        first_line = csv_str.split('\n')[0]
        num_columns = len(first_line.split(delimiter))
        fieldnames = [f"column_{i}" for i in range(num_columns)]
        
        input_stream.seek(0)
        reader = csv.DictReader(input_stream, fieldnames=fieldnames, delimiter=delimiter)
    
    data = []
    type_converters = type_converters or {}
    
    for row in reader:
        converted_row = {}
        
        for field, value in row.items():
            if field in type_converters:
                try:
                    converted_value = type_converters[field](value)
                except (ValueError, TypeError):
                    converted_value = value
            else:
                # Try to auto-convert common types
                converted_value = _auto_convert_value(value)
            
            converted_row[field] = converted_value
        
        data.append(converted_row)
    
    return data


def _auto_convert_value(value: str) -> Any:
    """Auto-convert string value to appropriate type."""
    if not value or value.lower() in ('', 'null', 'none'):
        return None
    
    # Try boolean
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    
    # Try integer
    try:
        if '.' not in value and 'e' not in value.lower():
            return int(value)
    except ValueError:
        pass
    
    # Try decimal
    try:
        return Decimal(value)
    except (ValueError, TypeError):
        pass
    
    # Try date/datetime
    try:
        if 'T' in value or ' ' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            return date.fromisoformat(value)
    except ValueError:
        pass
    
    # Return as string
    return value


def format_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    column_widths: Optional[Dict[str, int]] = None,
    alignment: Optional[Dict[str, str]] = None,
    formatters: Optional[Dict[str, Callable]] = None,
    show_index: bool = False,
    max_width: int = 120
) -> str:
    """
    Format data as a text table.
    
    Args:
        data: List of dictionaries to format
        columns: Column names to include (all if None)
        column_widths: Fixed widths for columns
        alignment: Column alignment ('left', 'right', 'center')
        formatters: Custom formatters for specific columns
        show_index: Whether to show row index
        max_width: Maximum table width
        
    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display"
    
    # Determine columns
    if columns is None:
        columns = list(data[0].keys())
    
    # Add index column if requested
    if show_index:
        columns = ['#'] + columns
        for i, row in enumerate(data):
            row = row.copy()
            row['#'] = i + 1
            data[i] = row
    
    # Apply formatters
    formatters = formatters or {}
    formatted_data = []
    
    for row in data:
        formatted_row = {}
        for col in columns:
            value = row.get(col, "")
            
            if col in formatters:
                formatted_value = formatters[col](value)
            else:
                formatted_value = _format_cell_value(value)
            
            formatted_row[col] = str(formatted_value)
        
        formatted_data.append(formatted_row)
    
    # Calculate column widths
    if column_widths is None:
        column_widths = {}
    
    for col in columns:
        if col not in column_widths:
            # Calculate width based on content
            header_width = len(col)
            content_widths = [len(row[col]) for row in formatted_data]
            column_widths[col] = min(max(header_width, max(content_widths, default=0)), 30)
    
    # Adjust widths to fit max_width
    total_width = sum(column_widths.values()) + len(columns) * 3 - 1  # Account for separators
    if total_width > max_width:
        # Proportionally reduce widths
        scale_factor = (max_width - len(columns) * 3 + 1) / sum(column_widths.values())
        for col in columns:
            column_widths[col] = max(int(column_widths[col] * scale_factor), 8)
    
    # Set up alignment
    alignment = alignment or {}
    
    # Build table
    lines = []
    
    # Header
    header_parts = []
    for col in columns:
        width = column_widths[col]
        align = alignment.get(col, 'left')
        
        if align == 'right':
            formatted_header = col.rjust(width)
        elif align == 'center':
            formatted_header = col.center(width)
        else:
            formatted_header = col.ljust(width)
        
        header_parts.append(formatted_header)
    
    lines.append(" | ".join(header_parts))
    
    # Separator
    separator_parts = []
    for col in columns:
        width = column_widths[col]
        separator_parts.append("-" * width)
    
    lines.append("-+-".join(separator_parts))
    
    # Data rows
    for row in formatted_data:
        row_parts = []
        for col in columns:
            width = column_widths[col]
            align = alignment.get(col, 'left')
            value = row[col]
            
            # Truncate if too long
            if len(value) > width:
                value = value[:width-3] + "..."
            
            if align == 'right':
                formatted_value = value.rjust(width)
            elif align == 'center':
                formatted_value = value.center(width)
            else:
                formatted_value = value.ljust(width)
            
            row_parts.append(formatted_value)
        
        lines.append(" | ".join(row_parts))
    
    return "\n".join(lines)


def _format_cell_value(value: Any) -> str:
    """Format a cell value for table display."""
    if value is None:
        return ""
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return str(value)
    elif isinstance(value, Money):
        return value.format()
    elif isinstance(value, bool):
        return "Yes" if value else "No"
    elif isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    else:
        return str(value)


def create_financial_csv_formatter() -> Dict[str, Callable]:
    """
    Create formatters for common financial CSV columns.
    
    Returns:
        Dictionary of column formatters
    """
    def format_currency(value):
        if isinstance(value, Money):
            return value.format(include_currency=False)
        elif isinstance(value, (int, float, Decimal)):
            return f"{Decimal(str(value)):.2f}"
        return str(value)
    
    def format_percentage(value):
        if isinstance(value, (int, float, Decimal)):
            return f"{float(value) * 100:.2f}%"
        return str(value)
    
    def format_date_only(value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        return str(value)
    
    return {
        "amount": format_currency,
        "balance": format_currency,
        "price": format_currency,
        "value": format_currency,
        "rate": format_percentage,
        "percentage": format_percentage,
        "return": format_percentage,
        "date": format_date_only,
        "transaction_date": format_date_only,
        "created_at": format_date_only,
    }


def export_data(
    data: Any,
    format_type: SerializationFormat,
    file_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    Export data to specified format.
    
    Args:
        data: Data to export
        format_type: Export format
        file_path: Optional file path to save to
        **kwargs: Additional arguments for specific formats
        
    Returns:
        Serialized data string
    """
    if format_type == SerializationFormat.JSON:
        result = serialize_to_json(data, **kwargs)
    elif format_type == SerializationFormat.CSV:
        if not isinstance(data, list):
            data = [data]
        result = serialize_to_csv(data, **kwargs)
    elif format_type == SerializationFormat.TSV:
        if not isinstance(data, list):
            data = [data]
        result = serialize_to_csv(data, delimiter='\t', **kwargs)
    elif format_type == SerializationFormat.DICT:
        result = serialize_to_json(serialize_to_dict(data, **kwargs))
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    
    # Save to file if path provided
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result)
    
    return result


def import_data(
    data_str: str,
    format_type: SerializationFormat,
    **kwargs
) -> Any:
    """
    Import data from specified format.
    
    Args:
        data_str: Data string to import
        format_type: Import format
        **kwargs: Additional arguments for specific formats
        
    Returns:
        Deserialized data
    """
    if format_type == SerializationFormat.JSON:
        return deserialize_from_json(data_str)
    elif format_type in [SerializationFormat.CSV, SerializationFormat.TSV]:
        delimiter = '\t' if format_type == SerializationFormat.TSV else ','
        return deserialize_from_csv(data_str, delimiter=delimiter, **kwargs)
    else:
        raise ValueError(f"Unsupported format: {format_type}")