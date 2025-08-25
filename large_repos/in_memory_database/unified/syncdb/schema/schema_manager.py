"""
Schema version management for handling schema evolution.
Integrated with common library schema and transaction support.
"""
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Type, Union
import json
import time
from dataclasses import dataclass, field
import copy

# Import from common library
from common.core.schema import SchemaManager as CommonSchemaManager, Schema as CommonSchema
from common.core.transaction import TransactionManager, Transaction as CommonTransaction, Operation
from common.core.serialization import Serializable, ExtendedJSONEncoder, ExtendedJSONDecoder
from common.utils.threading import ThreadSafeCache, atomic_operation
from common.utils.validation import ValidationError

from ..db.schema import DatabaseSchema, TableSchema, Column


@dataclass
class SchemaMigration(Serializable):
    """Represents a schema migration from one version to another - extends common Serializable."""
    source_version: int
    target_version: int
    description: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "source_version": self.source_version,
            "target_version": self.target_version,
            "description": self.description,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaMigration':
        """Create from a dictionary."""
        return cls(
            source_version=data["source_version"],
            target_version=data["target_version"],
            description=data["description"],
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class ColumnChange(Serializable):
    """Represents a change to a column in a schema migration - extends common Serializable."""
    operation: str  # "add", "remove", "modify"
    column_name: str
    column_def: Optional[Column] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        result = {
            "operation": self.operation,
            "column_name": self.column_name
        }
        
        if self.column_def:
            result["column_def"] = {
                "name": self.column_def.name,
                "data_type": self.column_def.data_type.__name__,
                "primary_key": self.column_def.primary_key,
                "nullable": self.column_def.nullable,
                "default": self.column_def.default
            }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnChange':
        """Create from a dictionary."""
        column_def = None
        if "column_def" in data:
            col_data = data["column_def"]
            data_type = eval(col_data["data_type"])  # This is risky in production
            column_def = Column(
                name=col_data["name"],
                data_type=data_type,
                primary_key=col_data["primary_key"],
                nullable=col_data["nullable"],
                default=col_data["default"]
            )
        
        return cls(
            operation=data["operation"],
            column_name=data["column_name"],
            column_def=column_def
        )


@dataclass
class TableChange(Serializable):
    """Represents a change to a table in a schema migration - extends common Serializable."""
    operation: str  # "add", "remove", "modify"
    table_name: str
    column_changes: List[ColumnChange] = field(default_factory=list)
    table_schema: Optional[TableSchema] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        result = {
            "operation": self.operation,
            "table_name": self.table_name,
            "column_changes": [c.to_dict() for c in self.column_changes]
        }
        
        if self.table_schema:
            # For a new table, include the full schema
            # A simplified representation for serialization
            result["table_schema"] = {
                "name": self.table_schema.name,
                "version": self.table_schema.version,
                "columns": [
                    {
                        "name": col.name,
                        "data_type": col.data_type.__name__,
                        "primary_key": col.primary_key,
                        "nullable": col.nullable,
                        "default": col.default
                    }
                    for col in self.table_schema.columns
                ]
            }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableChange':
        """Create from a dictionary."""
        column_changes = [ColumnChange.from_dict(c) for c in data.get("column_changes", [])]
        
        table_schema = None
        if "table_schema" in data:
            schema_data = data["table_schema"]
            columns = []
            
            for col_data in schema_data["columns"]:
                data_type = eval(col_data["data_type"])  # This is risky in production
                columns.append(Column(
                    name=col_data["name"],
                    data_type=data_type,
                    primary_key=col_data["primary_key"],
                    nullable=col_data["nullable"],
                    default=col_data["default"]
                ))
            
            table_schema = TableSchema(
                name=schema_data["name"],
                columns=columns,
                version=schema_data["version"]
            )
        
        return cls(
            operation=data["operation"],
            table_name=data["table_name"],
            column_changes=column_changes,
            table_schema=table_schema
        )


@dataclass
class MigrationPlan(Serializable):
    """Represents a plan for migrating a schema from one version to another - extends common Serializable."""
    migration: SchemaMigration
    table_changes: List[TableChange] = field(default_factory=list)
    data_migrations: Dict[str, Callable] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "migration": self.migration.to_dict(),
            "table_changes": [c.to_dict() for c in self.table_changes],
            # Data migrations are functions and can't be easily serialized
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationPlan':
        """Create from a dictionary."""
        migration = SchemaMigration.from_dict(data["migration"])
        table_changes = [TableChange.from_dict(c) for c in data["table_changes"]]
        
        return cls(
            migration=migration,
            table_changes=table_changes,
            data_migrations={}  # Data migrations can't be deserialized
        )


class SchemaVersionManager:
    """
    Manages schema versions and migrations.
    Uses common SchemaManager for underlying operations.
    """
    def __init__(self):
        self.schema_versions: Dict[int, DatabaseSchema] = {}
        self.current_version: int = 1
        self.migration_plans: Dict[Tuple[int, int], MigrationPlan] = {}
        
        # Use common library components
        self.common_schema_manager = CommonSchemaManager()
        self.transaction_manager = TransactionManager()
        self.schema_cache = ThreadSafeCache(max_size=50)  # Cache schema versions
    
@atomic_operation
    def register_schema(self, version: int, schema: DatabaseSchema) -> None:
        """Register a schema version with thread safety."""
        self.schema_versions[version] = schema
        if version > self.current_version:
            self.current_version = version
        
        # Cache the schema
        cache_key = f"schema:{version}"
        self.schema_cache.put(cache_key, schema)
        
        # Register with common schema manager if available
        if schema._schema_manager:
            for table_schema in schema.tables.values():
                if table_schema._common_schema:
                    self.common_schema_manager.register_schema(table_schema._common_schema)
    
    def get_schema(self, version: int) -> Optional[DatabaseSchema]:
        """Get a schema by version with caching."""
        # Check cache first
        cache_key = f"schema:{version}"
        cached_schema = self.schema_cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Get from storage
        schema = self.schema_versions.get(version)
        if schema:
            self.schema_cache.put(cache_key, schema)
        
        return schema
    
    def get_current_schema(self) -> Optional[DatabaseSchema]:
        """Get the current schema version."""
        return self.get_schema(self.current_version)
    
    def register_migration_plan(self, plan: MigrationPlan) -> None:
        """Register a migration plan."""
        key = (plan.migration.source_version, plan.migration.target_version)
        self.migration_plans[key] = plan
    
    def get_migration_plan(self, source_version: int, target_version: int) -> Optional[MigrationPlan]:
        """Get a migration plan for a specific version transition."""
        key = (source_version, target_version)
        return self.migration_plans.get(key)
    
    def can_migrate(self, source_version: int, target_version: int) -> bool:
        """Check if a migration path exists between two versions."""
        # Direct migration
        if (source_version, target_version) in self.migration_plans:
            return True
        
        # Find intermediate migrations (simple path finding)
        visited = set()
        to_visit = [source_version]
        
        while to_visit:
            current = to_visit.pop(0)
            if current == target_version:
                return True
            
            if current in visited:
                continue
                
            visited.add(current)
            
            # Find all migrations from current
            for (src, tgt) in self.migration_plans.keys():
                if src == current and tgt not in visited:
                    to_visit.append(tgt)
        
        return False
    
    def find_migration_path(self, source_version: int, target_version: int) -> List[Tuple[int, int]]:
        """Find a path of migrations from source to target version."""
        if source_version == target_version:
            return []
        
        # Direct migration
        if (source_version, target_version) in self.migration_plans:
            return [(source_version, target_version)]
        
        # Find path using BFS
        visited = set()
        to_visit = [(source_version, [])]
        
        while to_visit:
            current, path = to_visit.pop(0)
            if current == target_version:
                return path
            
            if current in visited:
                continue
                
            visited.add(current)
            
            # Find all migrations from current
            for (src, tgt) in self.migration_plans.keys():
                if src == current and tgt not in visited:
                    new_path = path + [(src, tgt)]
                    to_visit.append((tgt, new_path))
        
        return []  # No path found


class SchemaMigrator:
    """
    Performs schema migrations.
    Uses common transaction support for atomic migrations.
    """
    def __init__(self, version_manager: SchemaVersionManager):
        self.version_manager = version_manager
        # Use common components
        self.migration_cache = ThreadSafeCache(max_size=20)  # Cache migration plans
    
    def create_migration_plan(self, 
                             source_version: int, 
                             target_version: int, 
                             description: str) -> MigrationPlan:
        """
        Create a migration plan from source to target schema.
        
        Args:
            source_version: Source schema version
            target_version: Target schema version
            description: Description of the migration
            
        Returns:
            Migration plan
        """
        source_schema = self.version_manager.get_schema(source_version)
        target_schema = self.version_manager.get_schema(target_version)
        
        if not source_schema or not target_schema:
            raise ValueError(f"Missing schema for version {source_version} or {target_version}")
        
        # Create the migration
        migration = SchemaMigration(
            source_version=source_version,
            target_version=target_version,
            description=description
        )
        
        # Analyze the differences between schemas
        table_changes = self._analyze_schema_changes(source_schema, target_schema)
        
        # Create the migration plan
        plan = MigrationPlan(
            migration=migration,
            table_changes=table_changes
        )
        
        return plan
    
    def _analyze_schema_changes(self, 
                              source_schema: DatabaseSchema, 
                              target_schema: DatabaseSchema) -> List[TableChange]:
        """
        Analyze the changes between two schemas.
        
        Args:
            source_schema: Source schema
            target_schema: Target schema
            
        Returns:
            List of table changes
        """
        table_changes = []
        
        # Tables removed
        for table_name in source_schema.tables:
            if table_name not in target_schema.tables:
                change = TableChange(
                    operation="remove",
                    table_name=table_name
                )
                table_changes.append(change)
        
        # Tables added
        for table_name, table_schema in target_schema.tables.items():
            if table_name not in source_schema.tables:
                change = TableChange(
                    operation="add",
                    table_name=table_name,
                    table_schema=table_schema
                )
                table_changes.append(change)
        
        # Tables modified
        for table_name, target_table in target_schema.tables.items():
            if table_name in source_schema.tables:
                source_table = source_schema.tables[table_name]
                column_changes = self._analyze_column_changes(source_table, target_table)
                
                if column_changes:
                    change = TableChange(
                        operation="modify",
                        table_name=table_name,
                        column_changes=column_changes
                    )
                    table_changes.append(change)
        
        return table_changes
    
    def _analyze_column_changes(self, 
                               source_table: TableSchema, 
                               target_table: TableSchema) -> List[ColumnChange]:
        """
        Analyze the changes between two table schemas.
        
        Args:
            source_table: Source table schema
            target_table: Target table schema
            
        Returns:
            List of column changes
        """
        column_changes = []
        
        # Get columns by name
        source_columns = {col.name: col for col in source_table.columns}
        target_columns = {col.name: col for col in target_table.columns}
        
        # Columns removed
        for col_name in source_columns:
            if col_name not in target_columns:
                change = ColumnChange(
                    operation="remove",
                    column_name=col_name
                )
                column_changes.append(change)
        
        # Columns added
        for col_name, column in target_columns.items():
            if col_name not in source_columns:
                change = ColumnChange(
                    operation="add",
                    column_name=col_name,
                    column_def=column
                )
                column_changes.append(change)
        
        # Columns modified
        for col_name, target_col in target_columns.items():
            if col_name in source_columns:
                source_col = source_columns[col_name]
                
                # Check for changes in the column
                if (source_col.data_type != target_col.data_type or
                    source_col.primary_key != target_col.primary_key or
                    source_col.nullable != target_col.nullable or
                    source_col.default != target_col.default):
                    
                    change = ColumnChange(
                        operation="modify",
                        column_name=col_name,
                        column_def=target_col
                    )
                    column_changes.append(change)
        
        return column_changes
    
    def add_data_migration(self, 
                          plan: MigrationPlan, 
                          table_name: str, 
                          migration_func: Callable) -> None:
        """
        Add a data migration function to a migration plan.
        
        Args:
            plan: Migration plan
            table_name: Name of the table to migrate data for
            migration_func: Function that takes the old and new schemas and
                           transforms the data
        """
        plan.data_migrations[table_name] = migration_func
    
@atomic_operation  
    def apply_migration(self, 
                       database: 'Database', 
                       source_version: int, 
                       target_version: int) -> bool:
        """
        Apply a migration to a database with transaction support.
        
        Args:
            database: Database to migrate
            source_version: Source schema version
            target_version: Target schema version
            
        Returns:
            True if migration was successful
        """
        # Use transaction for atomicity
        with database.transaction_manager.transaction() as txn:
            try:
                # Get the migration plan
                plan = self.version_manager.get_migration_plan(source_version, target_version)
                if not plan:
                    # Try to find a path
                    path = self.version_manager.find_migration_path(source_version, target_version)
                    if not path:
                        return False
                    
                    # Apply each migration in the path
                    current_version = source_version
                    for src, tgt in path:
                        success = self.apply_migration(database, src, tgt)
                        if not success:
                            return False
                        current_version = tgt
                    
                    return current_version == target_version
                
                # Apply schema changes
                for table_change in plan.table_changes:
                    self._apply_table_change(database, table_change, plan.data_migrations)
                
                # Update the database schema version
                database.schema.version = target_version
                
                return True
                
            except Exception as e:
                # Transaction will automatically rollback
                print(f"Migration failed: {e}")
                return False
    
    def _apply_table_change(self, 
                          database: 'Database', 
                          table_change: TableChange,
                          data_migrations: Dict[str, Callable]) -> None:
        """
        Apply a table change to a database.
        
        Args:
            database: Database to modify
            table_change: Change to apply
            data_migrations: Data migration functions
        """
        table_name = table_change.table_name
        
        if table_change.operation == "add":
            # Add a new table
            if table_change.table_schema:
                database.schema.add_table(table_change.table_schema)
                # Create the table in the database
                database._create_table(table_change.table_schema)
        
        elif table_change.operation == "remove":
            # Remove a table
            if table_name in database.schema.tables:
                del database.schema.tables[table_name]
            
            # Remove the table from the database
            if table_name in database.tables:
                del database.tables[table_name]
        
        elif table_change.operation == "modify":
            # Modify an existing table
            if table_name not in database.schema.tables:
                return

            # Get the current table schema and records
            table_schema = database.schema.tables[table_name]
            table = database.tables.get(table_name)

            if not table:
                return

            # Get all records and their primary keys
            records_by_pk = {pk: record for pk, record in table.records.items()}

            # Apply column changes to the schema
            for col_change in table_change.column_changes:
                self._apply_column_change(table_schema, col_change)

            # Now update all records to match the new schema
            for pk_tuple, record in records_by_pk.items():
                # For added columns, add default values
                for col_change in table_change.column_changes:
                    if col_change.operation == "add":
                        col_name = col_change.column_name
                        col = table_schema.get_column(col_name)

                        # Add the new column with default value
                        if col and col_name not in record:
                            if col.default is not None:
                                record[col_name] = col.default() if callable(col.default) else col.default
                            elif not col.nullable:
                                # For non-nullable columns without default, add a placeholder
                                if col.data_type == str:
                                    record[col_name] = ""
                                elif col.data_type == int:
                                    record[col_name] = 0
                                elif col.data_type == float:
                                    record[col_name] = 0.0
                                elif col.data_type == bool:
                                    record[col_name] = False
                                elif col.data_type == list:
                                    record[col_name] = []
                                elif col.data_type == dict:
                                    record[col_name] = {}
                                else:
                                    record[col_name] = None
                            else:
                                # For nullable columns, default to None
                                record[col_name] = None

                # Remove columns that have been removed from the schema
                for col_change in table_change.column_changes:
                    if col_change.operation == "remove":
                        col_name = col_change.column_name
                        if col_name in record:
                            del record[col_name]

            # Apply data migration if available
            if table_name in data_migrations:
                migration_func = data_migrations[table_name]
                for record in records_by_pk.values():
                    migration_func(record, table_schema)
            
            # Rebuild the table's indexes if needed
            # This would be needed if primary keys changed
    
    def _apply_column_change(self, 
                            table_schema: TableSchema, 
                            column_change: ColumnChange) -> None:
        """
        Apply a column change to a table schema.
        
        Args:
            table_schema: Table schema to modify
            column_change: Change to apply
        """
        column_name = column_change.column_name
        
        if column_change.operation == "add":
            # Add a new column
            if column_change.column_def:
                table_schema.columns.append(column_change.column_def)
                # Update column dict
                table_schema._column_dict[column_name] = column_change.column_def
        
        elif column_change.operation == "remove":
            # Remove a column
            table_schema.columns = [c for c in table_schema.columns if c.name != column_name]
            # Update column dict
            if column_name in table_schema._column_dict:
                del table_schema._column_dict[column_name]
        
        elif column_change.operation == "modify":
            # Modify an existing column
            for i, col in enumerate(table_schema.columns):
                if col.name == column_name and column_change.column_def:
                    table_schema.columns[i] = column_change.column_def
                    # Update column dict
                    table_schema._column_dict[column_name] = column_change.column_def
                    break


class SchemaSynchronizer:
    """
    Synchronizes schema changes between server and clients.
    Uses common serialization for schema synchronization.
    """
    def __init__(self, version_manager: SchemaVersionManager, migrator: SchemaMigrator):
        self.version_manager = version_manager
        self.migrator = migrator
        # Use common components
        self.sync_cache = ThreadSafeCache(max_size=30)  # Cache sync plans
    
    def get_client_upgrade_plan(self, client_version: int) -> Optional[MigrationPlan]:
        """
        Get a migration plan to upgrade a client to the current server schema.
        
        Args:
            client_version: Client's current schema version
            
        Returns:
            Migration plan or None if no upgrade is needed
        """
        server_version = self.version_manager.current_version
        
        if client_version == server_version:
            return None
        
        if client_version > server_version:
            raise ValueError(f"Client version {client_version} is newer than server version {server_version}")
        
        # Find a migration path
        path = self.version_manager.find_migration_path(client_version, server_version)
        if not path:
            raise ValueError(f"No migration path from version {client_version} to {server_version}")
        
        # If there's a direct migration, return it
        if len(path) == 1:
            src, tgt = path[0]
            return self.version_manager.get_migration_plan(src, tgt)
        
        # Otherwise, create a synthetic plan that combines all migrations
        source_schema = self.version_manager.get_schema(client_version)
        target_schema = self.version_manager.get_schema(server_version)
        
        if not source_schema or not target_schema:
            raise ValueError(f"Missing schema for version {client_version} or {server_version}")
        
        # Create a synthetic migration
        migration = SchemaMigration(
            source_version=client_version,
            target_version=server_version,
            description=f"Upgrade from version {client_version} to {server_version}"
        )
        
        # Analyze the differences directly
        table_changes = self.migrator._analyze_schema_changes(source_schema, target_schema)
        
        # Create a synthetic plan
        plan = MigrationPlan(
            migration=migration,
            table_changes=table_changes
        )
        
        return plan
    
    def get_schema_compatibility(self, client_version: int, server_version: int) -> str:
        """
        Check if a client schema is compatible with a server schema.
        
        Args:
            client_version: Client's schema version
            server_version: Server's schema version
            
        Returns:
            "compatible", "upgrade_required", or "incompatible"
        """
        if client_version == server_version:
            return "compatible"
        
        if client_version < server_version:
            # Check if an upgrade path exists
            if self.version_manager.can_migrate(client_version, server_version):
                return "upgrade_required"
            else:
                return "incompatible"
        
        # Client version is newer than server
        return "incompatible"
    
    def serialize_migration_plan(self, plan: MigrationPlan) -> str:
        """
        Serialize a migration plan to JSON using common serialization.
        
        Args:
            plan: Migration plan
            
        Returns:
            JSON string
        """
        return json.dumps(plan.to_dict(), cls=ExtendedJSONEncoder)
    
    def deserialize_migration_plan(self, json_str: str) -> MigrationPlan:
        """
        Deserialize a migration plan from JSON using common serialization.
        
        Args:
            json_str: JSON string
            
        Returns:
            Migration plan
        """
        data = json.loads(json_str, cls=ExtendedJSONDecoder)
        return MigrationPlan.from_dict(data)