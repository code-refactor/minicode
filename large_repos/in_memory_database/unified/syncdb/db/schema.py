"""
Schema definition for SyncDB tables - extended from common library.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Type

# Import from common library
from common.core.schema import (
    Schema as CommonSchema,
    Column as CommonColumn,
    DataType,
    Constraint,
    NotNullConstraint,
    UniqueConstraint,
    RangeConstraint
)
from common.utils.validation import ValidationError


@dataclass
class Column:
    """Defines a column in a database table - compatibility wrapper around common Column."""
    name: str
    data_type: Type
    primary_key: bool = False
    nullable: bool = True
    default: Optional[Any] = None
    
    def __post_init__(self):
        """Convert to common library DataType if needed."""
        # Convert Python types to DataType enum
        if self.data_type == int:
            self._common_data_type = DataType.INTEGER
        elif self.data_type == float:
            self._common_data_type = DataType.FLOAT
        elif self.data_type == str:
            self._common_data_type = DataType.STRING
        elif self.data_type == bool:
            self._common_data_type = DataType.BOOLEAN
        elif self.data_type == dict:
            self._common_data_type = DataType.JSON
        elif self.data_type == list:
            self._common_data_type = DataType.JSON
        else:
            self._common_data_type = DataType.ANY
    
    def validate_value(self, value: Any) -> bool:
        """Validate that a value matches the column's type."""
        if value is None:
            return self.nullable
        
        # Check if the value is of the expected data type
        try:
            if not isinstance(value, self.data_type):
                # Try to convert the value to the expected type
                converted_value = self.data_type(value)
                return True
            return True
        except (ValueError, TypeError):
            return False
    
    def to_common_column(self) -> CommonColumn:
        """Convert to common library Column."""
        constraints = []
        if not self.nullable:
            constraints.append(NotNullConstraint())
        
        return CommonColumn(
            name=self.name,
            data_type=self._common_data_type,
            nullable=self.nullable,
            default=self.default,
            constraints=constraints
        )


@dataclass
class TableSchema:
    """Defines the schema for a database table - extended from common Schema."""
    name: str
    columns: List[Column]
    version: int = 1
    _column_dict: Dict[str, Column] = field(default_factory=dict, init=False)
    _common_schema: Optional[CommonSchema] = field(default=None, init=False)
    
    def __post_init__(self) -> None:
        """Process columns after initialization."""
        # Build a dictionary of columns by name for faster access
        self._column_dict = {col.name: col for col in self.columns}
        
        # Ensure there's at least one primary key
        primary_keys = [col for col in self.columns if col.primary_key]
        if not primary_keys:
            raise ValueError(f"Table {self.name} must have at least one primary key column")
        
        # Create common schema representation
        common_columns = [col.to_common_column() for col in self.columns]
        primary_key_names = [col.name for col in self.columns if col.primary_key]
        
        self._common_schema = CommonSchema(
            name=self.name,
            columns=common_columns,
            version=self.version,
            primary_key=primary_key_names
        )
    
    @property
    def primary_keys(self) -> List[str]:
        """Return the names of primary key columns."""
        return [col.name for col in self.columns if col.primary_key]
    
    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        return self._column_dict.get(name)
    
    def validate_record(self, record: Dict[str, Any]) -> List[str]:
        """
        Validate a record against the schema.
        Returns a list of error messages, empty if valid.
        """
        # Use common schema validation when available
        if self._common_schema:
            return self._common_schema.validate_record(record)
        
        # Fallback to original validation logic
        errors = []
        
        # Check that all primary keys are present
        for pk in self.primary_keys:
            if pk not in record:
                errors.append(f"Missing primary key {pk}")
        
        # Check that all provided values are valid
        for field_name, value in record.items():
            column = self.get_column(field_name)
            if not column:
                errors.append(f"Unknown column {field_name}")
                continue
            
            if not column.validate_value(value):
                errors.append(f"Invalid value for {field_name}, expected {column.data_type.__name__}")
        
        return errors


@dataclass
class DatabaseSchema:
    """Defines the schema for the entire database - uses common SchemaManager internally."""
    tables: Dict[str, TableSchema]
    version: int = 1
    _schema_manager: Optional[object] = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize schema manager with tables."""
        from common.core.schema import SchemaManager
        self._schema_manager = SchemaManager()
        
        # Register all tables with the common schema manager
        for table_schema in self.tables.values():
            if table_schema._common_schema:
                self._schema_manager.register_schema(table_schema._common_schema)
    
    def get_table(self, name: str) -> Optional[TableSchema]:
        """Get a table schema by name."""
        return self.tables.get(name)
    
    def add_table(self, table: TableSchema) -> None:
        """Add a table to the schema."""
        self.tables[table.name] = table
        # Also register with schema manager if available
        if self._schema_manager and table._common_schema:
            self._schema_manager.register_schema(table._common_schema)