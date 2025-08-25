"""Schema definition and validation for the unified library."""

from typing import Any, Dict, List, Optional, Tuple, Type, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class DataType(Enum):
    """Supported data types for schema columns."""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    JSON = "json"
    BINARY = "binary"
    VECTOR = "vector"
    ANY = "any"


@dataclass
class Constraint:
    """Base class for column constraints."""
    name: str
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against this constraint."""
        return True, None


@dataclass
class NotNullConstraint(Constraint):
    """Constraint ensuring value is not null."""
    
    def __init__(self):
        super().__init__(name="not_null")
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, "Value cannot be null"
        return True, None


@dataclass
class UniqueConstraint(Constraint):
    """Constraint ensuring value is unique."""
    
    def __init__(self):
        super().__init__(name="unique")
        self.seen_values = set()
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        if value in self.seen_values:
            return False, f"Value {value} is not unique"
        return True, None
    
    def register_value(self, value: Any) -> None:
        """Register a value as seen."""
        if value is not None:
            self.seen_values.add(value)


@dataclass
class RangeConstraint(Constraint):
    """Constraint ensuring value is within a range."""
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    
    def __init__(self, min_value: Optional[Any] = None, max_value: Optional[Any] = None):
        super().__init__(name="range")
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        
        if self.min_value is not None and value < self.min_value:
            return False, f"Value {value} is less than minimum {self.min_value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"Value {value} is greater than maximum {self.max_value}"
        
        return True, None


@dataclass
class Column:
    """Column definition with type and constraints."""
    name: str
    data_type: DataType
    nullable: bool = True
    default: Any = None
    constraints: List[Constraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against this column's type and constraints."""
        # Check null values
        if value is None:
            if not self.nullable:
                return False, f"Column {self.name} cannot be null"
            return True, None
        
        # Type validation
        if not self._validate_type(value):
            return False, f"Value {value} is not of type {self.data_type.value}"
        
        # Constraint validation
        for constraint in self.constraints:
            valid, error = constraint.validate(value)
            if not valid:
                return False, f"Column {self.name}: {error}"
        
        return True, None
    
    def _validate_type(self, value: Any) -> bool:
        """Validate value matches column type."""
        if self.data_type == DataType.ANY:
            return True
        
        type_validators = {
            DataType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            DataType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            DataType.STRING: lambda v: isinstance(v, str),
            DataType.BOOLEAN: lambda v: isinstance(v, bool),
            DataType.DATETIME: lambda v: isinstance(v, datetime),
            DataType.JSON: lambda v: self._is_json_serializable(v),
            DataType.BINARY: lambda v: isinstance(v, bytes),
            DataType.VECTOR: lambda v: isinstance(v, (list, tuple)) and all(isinstance(x, (int, float)) for x in v),
        }
        
        validator = type_validators.get(self.data_type)
        return validator(value) if validator else False
    
    def _is_json_serializable(self, value: Any) -> bool:
        """Check if value is JSON serializable."""
        try:
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False
    
    def apply_default(self) -> Any:
        """Apply default value for this column."""
        if callable(self.default):
            return self.default()
        return self.default


@dataclass
class Schema:
    """Schema definition for structured data."""
    name: str
    columns: List[Column]
    version: int = 1
    primary_key: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate schema after initialization."""
        self._column_map = {col.name: col for col in self.columns}
        
        # Validate primary key columns exist
        for pk_col in self.primary_key:
            if pk_col not in self._column_map:
                raise ValueError(f"Primary key column {pk_col} not found in schema")
    
    def validate_record(self, record: Dict[str, Any]) -> List[str]:
        """Validate a record against this schema."""
        errors = []
        
        # Check for missing required columns
        for column in self.columns:
            if column.name not in record:
                if not column.nullable and column.default is None:
                    errors.append(f"Missing required column: {column.name}")
                continue
            
            # Validate column value
            valid, error = column.validate(record[column.name])
            if not valid:
                errors.append(error)
        
        # Check for extra columns
        extra_columns = set(record.keys()) - set(self._column_map.keys())
        if extra_columns:
            errors.append(f"Extra columns not in schema: {extra_columns}")
        
        return errors
    
    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        return self._column_map.get(name)
    
    def apply_defaults(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to missing columns in record."""
        result = record.copy()
        
        for column in self.columns:
            if column.name not in result and column.default is not None:
                result[column.name] = column.apply_default()
        
        return result
    
    def project(self, record: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
        """Project specific columns from a record."""
        return {col: record[col] for col in columns if col in record}
    
    def evolve(self, changes: Dict[str, Any]) -> 'Schema':
        """Create a new schema version with changes."""
        new_columns = self.columns.copy()
        new_version = self.version + 1
        new_primary_key = self.primary_key.copy()
        new_metadata = self.metadata.copy()
        
        # Apply changes
        if 'add_columns' in changes:
            for col_def in changes['add_columns']:
                new_columns.append(Column(**col_def))
        
        if 'remove_columns' in changes:
            cols_to_remove = set(changes['remove_columns'])
            new_columns = [col for col in new_columns if col.name not in cols_to_remove]
            new_primary_key = [pk for pk in new_primary_key if pk not in cols_to_remove]
        
        if 'modify_columns' in changes:
            col_mods = {mod['name']: mod for mod in changes['modify_columns']}
            for i, col in enumerate(new_columns):
                if col.name in col_mods:
                    mod = col_mods[col.name]
                    # Create modified column
                    new_col = Column(
                        name=col.name,
                        data_type=DataType[mod.get('data_type', col.data_type.value).upper()],
                        nullable=mod.get('nullable', col.nullable),
                        default=mod.get('default', col.default),
                        constraints=col.constraints.copy(),
                        metadata=col.metadata.copy()
                    )
                    new_columns[i] = new_col
        
        if 'primary_key' in changes:
            new_primary_key = changes['primary_key']
        
        if 'metadata' in changes:
            new_metadata.update(changes['metadata'])
        
        return Schema(
            name=self.name,
            columns=new_columns,
            version=new_version,
            primary_key=new_primary_key,
            metadata=new_metadata
        )


class SchemaManager:
    """Manages schema versions and migrations."""
    
    def __init__(self):
        """Initialize schema manager."""
        self._schemas: Dict[str, Dict[int, Schema]] = {}
        self._current_versions: Dict[str, int] = {}
        self._migration_handlers: Dict[Tuple[str, int, int], Callable] = {}
    
    def register_schema(self, schema: Schema) -> None:
        """Register a schema version."""
        if schema.name not in self._schemas:
            self._schemas[schema.name] = {}
        
        self._schemas[schema.name][schema.version] = schema
        
        # Update current version if this is newer
        if schema.name not in self._current_versions or \
           schema.version > self._current_versions[schema.name]:
            self._current_versions[schema.name] = schema.version
    
    def get_schema(self, name: str, version: Optional[int] = None) -> Optional[Schema]:
        """Get a schema by name and version."""
        if name not in self._schemas:
            return None
        
        if version is None:
            version = self._current_versions.get(name)
            if version is None:
                return None
        
        return self._schemas[name].get(version)
    
    def register_migration(self, schema_name: str, from_version: int, 
                         to_version: int, handler: Callable) -> None:
        """Register a migration handler between schema versions."""
        key = (schema_name, from_version, to_version)
        self._migration_handlers[key] = handler
    
    def migrate_data(self, data: Any, schema_name: str, 
                    from_version: int, to_version: int) -> Any:
        """Migrate data from one schema version to another."""
        if from_version == to_version:
            return data
        
        # Find migration path
        if from_version < to_version:
            # Forward migration
            current_version = from_version
            migrated_data = data
            
            while current_version < to_version:
                next_version = current_version + 1
                key = (schema_name, current_version, next_version)
                
                if key in self._migration_handlers:
                    migrated_data = self._migration_handlers[key](migrated_data)
                else:
                    # Default migration: just copy compatible fields
                    from_schema = self.get_schema(schema_name, current_version)
                    to_schema = self.get_schema(schema_name, next_version)
                    
                    if from_schema and to_schema:
                        migrated_data = self._default_migrate(
                            migrated_data, from_schema, to_schema
                        )
                
                current_version = next_version
            
            return migrated_data
        else:
            # Backward migration
            raise NotImplementedError("Backward migration not yet supported")
    
    def _default_migrate(self, data: Any, from_schema: Schema, 
                        to_schema: Schema) -> Any:
        """Default migration between schemas."""
        if isinstance(data, dict):
            # Single record
            result = {}
            
            # Copy compatible columns
            for col in to_schema.columns:
                if col.name in data:
                    result[col.name] = data[col.name]
                elif col.default is not None:
                    result[col.name] = col.apply_default()
                elif not col.nullable:
                    raise ValueError(f"Cannot migrate: required column {col.name} has no value")
            
            return result
        
        elif isinstance(data, list):
            # Multiple records
            return [self._default_migrate(record, from_schema, to_schema) 
                   for record in data]
        
        else:
            return data