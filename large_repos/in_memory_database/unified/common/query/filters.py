"""Filter definitions for query operations in the unified library."""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime


class FilterType(Enum):
    """Types of filters supported in queries."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_EQUAL = "greater_equal"
    LESS_THAN = "less_than"
    LESS_EQUAL = "less_equal"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    NOT_LIKE = "not_like"
    REGEX = "regex"
    NOT_REGEX = "not_regex"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    CUSTOM = "custom"


class ComparisonOperator(Enum):
    """Comparison operators for filters."""
    EQ = "="  # equals
    NE = "!="  # not equals
    GT = ">"  # greater than
    GE = ">="  # greater than or equal
    LT = "<"  # less than
    LE = "<="  # less than or equal
    IN = "IN"  # in list
    NOT_IN = "NOT IN"  # not in list
    LIKE = "LIKE"  # pattern matching
    NOT_LIKE = "NOT LIKE"  # negative pattern matching
    IS_NULL = "IS NULL"  # is null
    IS_NOT_NULL = "IS NOT NULL"  # is not null
    BETWEEN = "BETWEEN"  # between two values
    REGEX = "REGEX"  # regular expression match


@dataclass
class Filter:
    """Represents a filter condition for queries."""
    field: str
    filter_type: FilterType
    value: Any = None
    values: Optional[List[Any]] = None  # For IN, NOT_IN, BETWEEN
    case_sensitive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate filter after initialization."""
        # Validate required values for specific filter types
        multi_value_types = {FilterType.IN, FilterType.NOT_IN, FilterType.BETWEEN, FilterType.NOT_BETWEEN}
        if self.filter_type in multi_value_types and not self.values:
            raise ValueError(f"Filter type {self.filter_type.value} requires 'values' parameter")
        
        if self.filter_type == FilterType.BETWEEN and len(self.values or []) != 2:
            raise ValueError("BETWEEN filter requires exactly 2 values")
        
        null_check_types = {FilterType.IS_NULL, FilterType.IS_NOT_NULL}
        if self.filter_type in null_check_types and self.value is not None:
            raise ValueError(f"Filter type {self.filter_type.value} should not have a value")
    
    def evaluate(self, record: Dict[str, Any]) -> bool:
        """Evaluate this filter against a record."""
        if self.field not in record:
            # Handle missing fields based on filter type
            if self.filter_type == FilterType.IS_NULL:
                return True
            elif self.filter_type == FilterType.IS_NOT_NULL:
                return False
            else:
                return False
        
        field_value = record[self.field]
        
        # Handle null checks first
        if self.filter_type == FilterType.IS_NULL:
            return field_value is None
        elif self.filter_type == FilterType.IS_NOT_NULL:
            return field_value is not None
        
        # For other filters, if field is null, only NOT_EQUALS can be true
        if field_value is None:
            return self.filter_type == FilterType.NOT_EQUALS
        
        # Apply filter logic
        return self._apply_filter_logic(field_value)
    
    def _apply_filter_logic(self, field_value: Any) -> bool:
        """Apply the specific filter logic to a field value."""
        try:
            if self.filter_type == FilterType.EQUALS:
                return self._compare_values(field_value, self.value, "==")
            
            elif self.filter_type == FilterType.NOT_EQUALS:
                return not self._compare_values(field_value, self.value, "==")
            
            elif self.filter_type == FilterType.GREATER_THAN:
                return self._compare_values(field_value, self.value, ">")
            
            elif self.filter_type == FilterType.GREATER_EQUAL:
                return self._compare_values(field_value, self.value, ">=")
            
            elif self.filter_type == FilterType.LESS_THAN:
                return self._compare_values(field_value, self.value, "<")
            
            elif self.filter_type == FilterType.LESS_EQUAL:
                return self._compare_values(field_value, self.value, "<=")
            
            elif self.filter_type == FilterType.IN:
                return any(self._compare_values(field_value, v, "==") for v in (self.values or []))
            
            elif self.filter_type == FilterType.NOT_IN:
                return not any(self._compare_values(field_value, v, "==") for v in (self.values or []))
            
            elif self.filter_type == FilterType.LIKE:
                return self._apply_like_pattern(field_value, self.value)
            
            elif self.filter_type == FilterType.NOT_LIKE:
                return not self._apply_like_pattern(field_value, self.value)
            
            elif self.filter_type == FilterType.REGEX:
                return self._apply_regex_pattern(field_value, self.value)
            
            elif self.filter_type == FilterType.NOT_REGEX:
                return not self._apply_regex_pattern(field_value, self.value)
            
            elif self.filter_type == FilterType.BETWEEN:
                if not self.values or len(self.values) != 2:
                    return False
                min_val, max_val = self.values
                return (self._compare_values(field_value, min_val, ">=") and 
                       self._compare_values(field_value, max_val, "<="))
            
            elif self.filter_type == FilterType.NOT_BETWEEN:
                if not self.values or len(self.values) != 2:
                    return True
                min_val, max_val = self.values
                return not (self._compare_values(field_value, min_val, ">=") and 
                           self._compare_values(field_value, max_val, "<="))
            
            elif self.filter_type == FilterType.CONTAINS:
                return self._apply_contains(field_value, self.value)
            
            elif self.filter_type == FilterType.NOT_CONTAINS:
                return not self._apply_contains(field_value, self.value)
            
            elif self.filter_type == FilterType.STARTS_WITH:
                return self._apply_starts_with(field_value, self.value)
            
            elif self.filter_type == FilterType.ENDS_WITH:
                return self._apply_ends_with(field_value, self.value)
            
            elif self.filter_type == FilterType.CUSTOM:
                # Custom filter should have a callable in metadata
                custom_func = self.metadata.get('function')
                if callable(custom_func):
                    return custom_func(field_value, self.value)
                return False
            
            else:
                return False
        
        except (TypeError, ValueError, AttributeError):
            # If comparison fails due to type mismatch, return False
            return False
    
    def _compare_values(self, left: Any, right: Any, operator: str) -> bool:
        """Compare two values with the given operator."""
        try:
            if operator == "==":
                return left == right
            elif operator == ">":
                return left > right
            elif operator == ">=":
                return left >= right
            elif operator == "<":
                return left < right
            elif operator == "<=":
                return left <= right
            else:
                return False
        except TypeError:
            # Handle type mismatches (e.g., comparing str to int)
            if operator == "==":
                return False
            # For ordering comparisons, try string comparison as fallback
            try:
                str_left, str_right = str(left), str(right)
                if operator == ">":
                    return str_left > str_right
                elif operator == ">=":
                    return str_left >= str_right
                elif operator == "<":
                    return str_left < str_right
                elif operator == "<=":
                    return str_left <= str_right
            except:
                return False
            return False
    
    def _apply_like_pattern(self, field_value: Any, pattern: Any) -> bool:
        """Apply SQL-like LIKE pattern matching."""
        if not isinstance(field_value, str) or not isinstance(pattern, str):
            return False
        
        # Convert SQL LIKE pattern to regex
        # % matches any sequence of characters
        # _ matches any single character
        regex_pattern = pattern.replace('%', '.*').replace('_', '.')
        regex_pattern = f'^{regex_pattern}$'
        
        flags = 0 if self.case_sensitive else re.IGNORECASE
        try:
            return bool(re.match(regex_pattern, field_value, flags))
        except re.error:
            return False
    
    def _apply_regex_pattern(self, field_value: Any, pattern: Any) -> bool:
        """Apply regular expression pattern matching."""
        if not isinstance(field_value, str) or not isinstance(pattern, str):
            return False
        
        flags = 0 if self.case_sensitive else re.IGNORECASE
        try:
            return bool(re.search(pattern, field_value, flags))
        except re.error:
            return False
    
    def _apply_contains(self, field_value: Any, search_value: Any) -> bool:
        """Check if field contains the search value."""
        if isinstance(field_value, str) and isinstance(search_value, str):
            field_str = field_value if self.case_sensitive else field_value.lower()
            search_str = search_value if self.case_sensitive else search_value.lower()
            return search_str in field_str
        elif isinstance(field_value, (list, tuple)):
            return search_value in field_value
        elif isinstance(field_value, dict):
            return search_value in field_value.values()
        else:
            return False
    
    def _apply_starts_with(self, field_value: Any, prefix: Any) -> bool:
        """Check if field starts with the given prefix."""
        if not isinstance(field_value, str) or not isinstance(prefix, str):
            return False
        
        field_str = field_value if self.case_sensitive else field_value.lower()
        prefix_str = prefix if self.case_sensitive else prefix.lower()
        return field_str.startswith(prefix_str)
    
    def _apply_ends_with(self, field_value: Any, suffix: Any) -> bool:
        """Check if field ends with the given suffix."""
        if not isinstance(field_value, str) or not isinstance(suffix, str):
            return False
        
        field_str = field_value if self.case_sensitive else field_value.lower()
        suffix_str = suffix if self.case_sensitive else suffix.lower()
        return field_str.endswith(suffix_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary representation."""
        result = {
            'field': self.field,
            'filter_type': self.filter_type.value,
            'case_sensitive': self.case_sensitive
        }
        
        if self.value is not None:
            result['value'] = self.value
        
        if self.values is not None:
            result['values'] = self.values
        
        if self.metadata:
            result['metadata'] = self.metadata
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Filter':
        """Create filter from dictionary representation."""
        return cls(
            field=data['field'],
            filter_type=FilterType(data['filter_type']),
            value=data.get('value'),
            values=data.get('values'),
            case_sensitive=data.get('case_sensitive', True),
            metadata=data.get('metadata', {})
        )
    
    def __repr__(self) -> str:
        """String representation of the filter."""
        parts = [f"field={self.field}", f"type={self.filter_type.value}"]
        
        if self.value is not None:
            parts.append(f"value={self.value}")
        
        if self.values is not None:
            parts.append(f"values={self.values}")
        
        if not self.case_sensitive:
            parts.append("case_sensitive=False")
        
        return f"Filter({', '.join(parts)})"


class FilterBuilder:
    """Builder class for creating filters with a fluent interface."""
    
    def __init__(self, field: str):
        """Initialize filter builder for a specific field."""
        self.field = field
        self._case_sensitive = True
        self._metadata: Dict[str, Any] = {}
    
    def case_insensitive(self) -> 'FilterBuilder':
        """Make the filter case insensitive."""
        self._case_sensitive = False
        return self
    
    def with_metadata(self, **metadata) -> 'FilterBuilder':
        """Add metadata to the filter."""
        self._metadata.update(metadata)
        return self
    
    def equals(self, value: Any) -> Filter:
        """Create an equals filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.EQUALS,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def not_equals(self, value: Any) -> Filter:
        """Create a not equals filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.NOT_EQUALS,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def greater_than(self, value: Any) -> Filter:
        """Create a greater than filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.GREATER_THAN,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def greater_equal(self, value: Any) -> Filter:
        """Create a greater than or equal filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.GREATER_EQUAL,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def less_than(self, value: Any) -> Filter:
        """Create a less than filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.LESS_THAN,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def less_equal(self, value: Any) -> Filter:
        """Create a less than or equal filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.LESS_EQUAL,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def in_list(self, values: List[Any]) -> Filter:
        """Create an IN filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.IN,
            values=values,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def not_in_list(self, values: List[Any]) -> Filter:
        """Create a NOT IN filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.NOT_IN,
            values=values,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def like(self, pattern: str) -> Filter:
        """Create a LIKE filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.LIKE,
            value=pattern,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def regex(self, pattern: str) -> Filter:
        """Create a regex filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.REGEX,
            value=pattern,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def is_null(self) -> Filter:
        """Create an IS NULL filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.IS_NULL,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def is_not_null(self) -> Filter:
        """Create an IS NOT NULL filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.IS_NOT_NULL,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def between(self, min_value: Any, max_value: Any) -> Filter:
        """Create a BETWEEN filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.BETWEEN,
            values=[min_value, max_value],
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def contains(self, value: Any) -> Filter:
        """Create a CONTAINS filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.CONTAINS,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def starts_with(self, prefix: str) -> Filter:
        """Create a STARTS_WITH filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.STARTS_WITH,
            value=prefix,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def ends_with(self, suffix: str) -> Filter:
        """Create an ENDS_WITH filter."""
        return Filter(
            field=self.field,
            filter_type=FilterType.ENDS_WITH,
            value=suffix,
            case_sensitive=self._case_sensitive,
            metadata=self._metadata
        )
    
    def custom(self, func: Callable[[Any, Any], bool], value: Any = None) -> Filter:
        """Create a custom filter with a user-defined function."""
        metadata = self._metadata.copy()
        metadata['function'] = func
        
        return Filter(
            field=self.field,
            filter_type=FilterType.CUSTOM,
            value=value,
            case_sensitive=self._case_sensitive,
            metadata=metadata
        )


def filter_field(field: str) -> FilterBuilder:
    """Create a filter builder for the specified field."""
    return FilterBuilder(field)