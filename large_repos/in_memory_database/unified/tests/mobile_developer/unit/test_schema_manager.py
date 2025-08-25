"""
Tests for the schema version management.
"""
import pytest
import time
from typing import Dict, List, Any, Optional

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database
from syncdb.schema.schema_manager import (
    SchemaMigration, ColumnChange, TableChange, MigrationPlan,
    SchemaVersionManager, SchemaMigrator, SchemaSynchronizer
)


def create_schema_v1():
    """Create sample schema version 1."""
    # User table
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("created_at", float, default=time.time)
    ]
    user_table = TableSchema("users", user_columns)
    
    # Task table
    task_columns = [
        Column("id", int, primary_key=True),
        Column("user_id", int),
        Column("title", str),
        Column("completed", bool, default=False)
    ]
    task_table = TableSchema("tasks", task_columns)
    
    # Create the database schema
    tables = {
        "users": user_table,
        "tasks": task_table
    }
    schema = DatabaseSchema(tables, version=1)
    
    return schema


def create_schema_v2():
    """Create sample schema version 2."""
    # User table (unchanged)
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("created_at", float, default=time.time)
    ]
    user_table = TableSchema("users", user_columns)
    
    # Task table (added description field)
    task_columns = [
        Column("id", int, primary_key=True),
        Column("user_id", int),
        Column("title", str),
        Column("description", str, nullable=True),  # New field
        Column("completed", bool, default=False)
    ]
    task_table = TableSchema("tasks", task_columns)
    
    # Note table (new table)
    note_columns = [
        Column("id", int, primary_key=True),
        Column("task_id", int),
        Column("content", str),
        Column("created_at", float, default=time.time)
    ]
    note_table = TableSchema("notes", note_columns)
    
    # Create the database schema
    tables = {
        "users": user_table,
        "tasks": task_table,
        "notes": note_table
    }
    schema = DatabaseSchema(tables, version=2)
    
    return schema


def test_schema_migration_creation():
    """Test creating a schema migration."""
    migration = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    assert migration.source_version == 1
    assert migration.target_version == 2
    assert migration.description == "Add task description and notes table"
    assert migration.timestamp > 0


def test_schema_migration_to_from_dict():
    """Test converting a schema migration to and from a dictionary."""
    # Create a migration
    migration = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Add task description and notes table",
        timestamp=123456789.0  # Fixed timestamp for testing
    )
    
    # Convert to dictionary
    migration_dict = migration.to_dict()
    
    # Check the dictionary
    assert migration_dict["source_version"] == 1
    assert migration_dict["target_version"] == 2
    assert migration_dict["description"] == "Add task description and notes table"
    assert migration_dict["timestamp"] == 123456789.0
    
    # Create from dictionary
    migration2 = SchemaMigration.from_dict(migration_dict)
    
    # Check the migration
    assert migration2.source_version == 1
    assert migration2.target_version == 2
    assert migration2.description == "Add task description and notes table"
    assert migration2.timestamp == 123456789.0


def test_column_change_creation():
    """Test creating a column change."""
    # Create a column change for adding a column
    column = Column("description", str, nullable=True)
    change = ColumnChange(
        operation="add",
        column_name="description",
        column_def=column
    )
    
    assert change.operation == "add"
    assert change.column_name == "description"
    assert change.column_def == column
    
    # Create a column change for removing a column
    change = ColumnChange(
        operation="remove",
        column_name="old_column"
    )
    
    assert change.operation == "remove"
    assert change.column_name == "old_column"
    assert change.column_def is None


def test_column_change_to_from_dict():
    """Test converting a column change to and from a dictionary."""
    # Create a column change
    column = Column("description", str, nullable=True)
    change = ColumnChange(
        operation="add",
        column_name="description",
        column_def=column
    )
    
    # Convert to dictionary
    change_dict = change.to_dict()
    
    # Check the dictionary
    assert change_dict["operation"] == "add"
    assert change_dict["column_name"] == "description"
    assert change_dict["column_def"]["name"] == "description"
    assert change_dict["column_def"]["data_type"] == "str"
    assert change_dict["column_def"]["nullable"] is True
    
    # Create from dictionary
    change2 = ColumnChange.from_dict(change_dict)
    
    # Check the change
    assert change2.operation == "add"
    assert change2.column_name == "description"
    assert change2.column_def.name == "description"
    assert change2.column_def.data_type == str
    assert change2.column_def.nullable is True


def test_table_change_creation():
    """Test creating a table change."""
    # Create a table change for adding a table
    columns = [
        Column("id", int, primary_key=True),
        Column("content", str)
    ]
    table_schema = TableSchema("notes", columns)
    
    change = TableChange(
        operation="add",
        table_name="notes",
        table_schema=table_schema
    )
    
    assert change.operation == "add"
    assert change.table_name == "notes"
    assert change.table_schema == table_schema
    assert change.column_changes == []
    
    # Create a table change for modifying a table
    column_change = ColumnChange(
        operation="add",
        column_name="description",
        column_def=Column("description", str, nullable=True)
    )
    
    change = TableChange(
        operation="modify",
        table_name="tasks",
        column_changes=[column_change]
    )
    
    assert change.operation == "modify"
    assert change.table_name == "tasks"
    assert change.table_schema is None
    assert change.column_changes == [column_change]


def test_table_change_to_from_dict():
    """Test converting a table change to and from a dictionary."""
    # Create a table change
    columns = [
        Column("id", int, primary_key=True),
        Column("content", str)
    ]
    table_schema = TableSchema("notes", columns)
    
    change = TableChange(
        operation="add",
        table_name="notes",
        table_schema=table_schema
    )
    
    # Convert to dictionary
    change_dict = change.to_dict()
    
    # Check the dictionary
    assert change_dict["operation"] == "add"
    assert change_dict["table_name"] == "notes"
    assert change_dict["table_schema"]["name"] == "notes"
    assert len(change_dict["table_schema"]["columns"]) == 2
    assert change_dict["table_schema"]["columns"][0]["name"] == "id"
    assert change_dict["table_schema"]["columns"][0]["data_type"] == "int"
    assert change_dict["table_schema"]["columns"][0]["primary_key"] is True
    
    # Create from dictionary
    change2 = TableChange.from_dict(change_dict)
    
    # Check the change
    assert change2.operation == "add"
    assert change2.table_name == "notes"
    assert change2.table_schema.name == "notes"
    assert len(change2.table_schema.columns) == 2
    assert change2.table_schema.columns[0].name == "id"
    assert change2.table_schema.columns[0].data_type == int
    assert change2.table_schema.columns[0].primary_key is True


def test_migration_plan_creation():
    """Test creating a migration plan."""
    # Create a migration
    migration = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Create table changes
    column_change = ColumnChange(
        operation="add",
        column_name="description",
        column_def=Column("description", str, nullable=True)
    )
    
    table_change1 = TableChange(
        operation="modify",
        table_name="tasks",
        column_changes=[column_change]
    )
    
    columns = [
        Column("id", int, primary_key=True),
        Column("content", str)
    ]
    table_schema = TableSchema("notes", columns)
    
    table_change2 = TableChange(
        operation="add",
        table_name="notes",
        table_schema=table_schema
    )
    
    # Create the migration plan
    plan = MigrationPlan(
        migration=migration,
        table_changes=[table_change1, table_change2]
    )
    
    assert plan.migration == migration
    assert plan.table_changes == [table_change1, table_change2]
    assert plan.data_migrations == {}


def test_migration_plan_to_from_dict():
    """Test converting a migration plan to and from a dictionary."""
    # Create a migration
    migration = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Create table changes
    column_change = ColumnChange(
        operation="add",
        column_name="description",
        column_def=Column("description", str, nullable=True)
    )
    
    table_change = TableChange(
        operation="modify",
        table_name="tasks",
        column_changes=[column_change]
    )
    
    # Create the migration plan
    plan = MigrationPlan(
        migration=migration,
        table_changes=[table_change]
    )
    
    # Convert to dictionary
    plan_dict = plan.to_dict()
    
    # Check the dictionary
    assert plan_dict["migration"]["source_version"] == 1
    assert plan_dict["migration"]["target_version"] == 2
    assert plan_dict["migration"]["description"] == "Add task description and notes table"
    assert len(plan_dict["table_changes"]) == 1
    assert plan_dict["table_changes"][0]["operation"] == "modify"
    assert plan_dict["table_changes"][0]["table_name"] == "tasks"
    
    # Create from dictionary
    plan2 = MigrationPlan.from_dict(plan_dict)
    
    # Check the plan
    assert plan2.migration.source_version == 1
    assert plan2.migration.target_version == 2
    assert plan2.migration.description == "Add task description and notes table"
    assert len(plan2.table_changes) == 1
    assert plan2.table_changes[0].operation == "modify"
    assert plan2.table_changes[0].table_name == "tasks"
    assert len(plan2.table_changes[0].column_changes) == 1
    assert plan2.table_changes[0].column_changes[0].operation == "add"
    assert plan2.table_changes[0].column_changes[0].column_name == "description"


def test_schema_version_manager_creation():
    """Test creating a schema version manager."""
    manager = SchemaVersionManager()
    
    assert manager.schema_versions == {}
    assert manager.current_version == 1
    assert manager.migration_plans == {}


def test_schema_version_manager_register_schema():
    """Test registering schemas with the schema version manager."""
    manager = SchemaVersionManager()
    
    # Create and register schemas
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    manager.register_schema(1, schema1)
    manager.register_schema(2, schema2)
    
    # Check that the schemas were registered
    assert manager.schema_versions[1] == schema1
    assert manager.schema_versions[2] == schema2
    assert manager.current_version == 2  # Highest version
    
    # Get schemas
    assert manager.get_schema(1) == schema1
    assert manager.get_schema(2) == schema2
    assert manager.get_schema(3) is None  # Non-existent version
    assert manager.get_current_schema() == schema2


def test_schema_version_manager_register_migration_plan():
    """Test registering migration plans with the schema version manager."""
    manager = SchemaVersionManager()
    
    # Create a migration plan
    migration = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Migration 1 to 2"
    )
    plan = MigrationPlan(
        migration=migration,
        table_changes=[]
    )
    
    # Register the plan
    manager.register_migration_plan(plan)
    
    # Check that the plan was registered
    assert (1, 2) in manager.migration_plans
    assert manager.migration_plans[(1, 2)] == plan
    
    # Get the plan
    assert manager.get_migration_plan(1, 2) == plan
    assert manager.get_migration_plan(2, 3) is None  # Non-existent plan


def test_schema_version_manager_can_migrate():
    """Test checking if migration is possible."""
    manager = SchemaVersionManager()
    
    # Create and register migration plans
    migration1_2 = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Migration 1 to 2"
    )
    plan1_2 = MigrationPlan(
        migration=migration1_2,
        table_changes=[]
    )
    
    migration2_3 = SchemaMigration(
        source_version=2,
        target_version=3,
        description="Migration 2 to 3"
    )
    plan2_3 = MigrationPlan(
        migration=migration2_3,
        table_changes=[]
    )
    
    # Register the plans
    manager.register_migration_plan(plan1_2)
    manager.register_migration_plan(plan2_3)
    
    # Check migration possibilities
    assert manager.can_migrate(1, 2) is True
    assert manager.can_migrate(2, 3) is True
    
    # No direct plan from 1 to 3, but can migrate via 2
    assert manager.can_migrate(1, 3) is True
    
    # Can't migrate to lower version
    assert manager.can_migrate(3, 2) is False
    
    # Can't migrate to non-existent version
    assert manager.can_migrate(1, 4) is False


def test_schema_version_manager_find_migration_path():
    """Test finding a migration path."""
    manager = SchemaVersionManager()
    
    # Create and register migration plans
    migration1_2 = SchemaMigration(
        source_version=1,
        target_version=2,
        description="Migration 1 to 2"
    )
    plan1_2 = MigrationPlan(
        migration=migration1_2,
        table_changes=[]
    )
    
    migration2_3 = SchemaMigration(
        source_version=2,
        target_version=3,
        description="Migration 2 to 3"
    )
    plan2_3 = MigrationPlan(
        migration=migration2_3,
        table_changes=[]
    )
    
    # Register the plans
    manager.register_migration_plan(plan1_2)
    manager.register_migration_plan(plan2_3)
    
    # Find migration paths
    assert manager.find_migration_path(1, 1) == []  # Same version, no path needed
    assert manager.find_migration_path(1, 2) == [(1, 2)]  # Direct path
    assert manager.find_migration_path(1, 3) == [(1, 2), (2, 3)]  # Path via 2
    assert manager.find_migration_path(1, 4) == []  # No path to non-existent version


def test_schema_migrator_creation():
    """Test creating a schema migrator."""
    manager = SchemaVersionManager()
    migrator = SchemaMigrator(manager)
    
    assert migrator.version_manager == manager


def test_schema_migrator_create_migration_plan():
    """Test creating a migration plan."""
    manager = SchemaVersionManager()
    
    # Register schemas
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    manager.register_schema(1, schema1)
    manager.register_schema(2, schema2)
    
    # Create migrator
    migrator = SchemaMigrator(manager)
    
    # Create migration plan
    plan = migrator.create_migration_plan(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Check the plan
    assert plan.migration.source_version == 1
    assert plan.migration.target_version == 2
    assert plan.migration.description == "Add task description and notes table"
    
    # Check the table changes
    assert len(plan.table_changes) == 2
    
    # Find the "tasks" table change (modify)
    tasks_change = next((c for c in plan.table_changes if c.table_name == "tasks"), None)
    assert tasks_change is not None
    assert tasks_change.operation == "modify"
    assert len(tasks_change.column_changes) == 1
    assert tasks_change.column_changes[0].operation == "add"
    assert tasks_change.column_changes[0].column_name == "description"
    
    # Find the "notes" table change (add)
    notes_change = next((c for c in plan.table_changes if c.table_name == "notes"), None)
    assert notes_change is not None
    assert notes_change.operation == "add"
    assert notes_change.table_schema is not None
    assert notes_change.table_schema.name == "notes"


def test_schema_migrator_analyze_schema_changes():
    """Test analyzing schema changes."""
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    migrator = SchemaMigrator(None)  # Version manager not needed for this test
    
    # Analyze changes
    changes = migrator._analyze_schema_changes(schema1, schema2)
    
    # Should have 2 table changes
    assert len(changes) == 2
    
    # Find the "tasks" table change (modify)
    tasks_change = next((c for c in changes if c.table_name == "tasks"), None)
    assert tasks_change is not None
    assert tasks_change.operation == "modify"
    assert len(tasks_change.column_changes) == 1
    assert tasks_change.column_changes[0].operation == "add"
    assert tasks_change.column_changes[0].column_name == "description"
    
    # Find the "notes" table change (add)
    notes_change = next((c for c in changes if c.table_name == "notes"), None)
    assert notes_change is not None
    assert notes_change.operation == "add"
    assert notes_change.table_schema is not None
    assert notes_change.table_schema.name == "notes"


def test_schema_migrator_analyze_column_changes():
    """Test analyzing column changes."""
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    # Get the task tables
    tasks1 = schema1.tables["tasks"]
    tasks2 = schema2.tables["tasks"]
    
    migrator = SchemaMigrator(None)  # Version manager not needed for this test
    
    # Analyze column changes
    changes = migrator._analyze_column_changes(tasks1, tasks2)
    
    # Should have 1 column change (add description)
    assert len(changes) == 1
    assert changes[0].operation == "add"
    assert changes[0].column_name == "description"
    assert changes[0].column_def is not None
    assert changes[0].column_def.name == "description"
    assert changes[0].column_def.data_type == str
    assert changes[0].column_def.nullable is True


def test_schema_migrator_apply_migration():
    """Test applying a migration to a database."""
    # Create schemas and database
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    database = Database(schema1)
    
    # Add some sample data
    database.insert("users", {"id": 1, "username": "alice", "email": "alice@example.com"})
    database.insert("tasks", {"id": 1, "user_id": 1, "title": "Task 1", "completed": False})
    
    # Set up version manager and migrator
    manager = SchemaVersionManager()
    manager.register_schema(1, schema1)
    manager.register_schema(2, schema2)
    
    migrator = SchemaMigrator(manager)
    
    # Create migration plan
    plan = migrator.create_migration_plan(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Register the plan
    manager.register_migration_plan(plan)
    
    # Apply the migration
    success = migrator.apply_migration(database, 1, 2)
    
    # Check that the migration was successful
    assert success is True
    assert database.schema.version == 2
    
    # Check that the tasks table has the new column
    task = database.get("tasks", [1])
    assert task is not None
    assert "description" in task
    assert task["description"] is None  # New nullable column
    
    # Check that the notes table was added
    assert "notes" in database.tables
    
    # The existing data should still be there
    user = database.get("users", [1])
    assert user is not None
    assert user["username"] == "alice"


def test_schema_synchronizer_creation():
    """Test creating a schema synchronizer."""
    manager = SchemaVersionManager()
    migrator = SchemaMigrator(manager)
    synchronizer = SchemaSynchronizer(manager, migrator)
    
    assert synchronizer.version_manager == manager
    assert synchronizer.migrator == migrator


def test_schema_synchronizer_get_client_upgrade_plan():
    """Test getting a client upgrade plan."""
    # Create schemas
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    # Set up version manager and migrator
    manager = SchemaVersionManager()
    manager.register_schema(1, schema1)
    manager.register_schema(2, schema2)
    
    migrator = SchemaMigrator(manager)
    
    # Create migration plan
    plan = migrator.create_migration_plan(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Register the plan
    manager.register_migration_plan(plan)
    
    # Create synchronizer
    synchronizer = SchemaSynchronizer(manager, migrator)
    
    # Get client upgrade plan
    upgrade_plan = synchronizer.get_client_upgrade_plan(1)
    
    # Check the plan
    assert upgrade_plan.migration.source_version == 1
    assert upgrade_plan.migration.target_version == 2
    assert len(upgrade_plan.table_changes) == 2  # tasks modify, notes add
    
    # Client with current version shouldn't need upgrade
    assert synchronizer.get_client_upgrade_plan(2) is None
    
    # Client with newer version should raise exception
    with pytest.raises(ValueError):
        synchronizer.get_client_upgrade_plan(3)


def test_schema_synchronizer_get_schema_compatibility():
    """Test getting schema compatibility."""
    # Create schemas
    schema1 = create_schema_v1()
    schema2 = create_schema_v2()
    
    # Set up version manager and migrator
    manager = SchemaVersionManager()
    manager.register_schema(1, schema1)
    manager.register_schema(2, schema2)
    
    migrator = SchemaMigrator(manager)
    
    # Create migration plan
    plan = migrator.create_migration_plan(
        source_version=1,
        target_version=2,
        description="Add task description and notes table"
    )
    
    # Register the plan
    manager.register_migration_plan(plan)
    
    # Create synchronizer
    synchronizer = SchemaSynchronizer(manager, migrator)
    
    # Check compatibility
    assert synchronizer.get_schema_compatibility(1, 1) == "compatible"  # Same version
    assert synchronizer.get_schema_compatibility(1, 2) == "upgrade_required"  # Upgrade possible
    assert synchronizer.get_schema_compatibility(2, 1) == "incompatible"  # Newer client
    assert synchronizer.get_schema_compatibility(1, 3) == "incompatible"  # No upgrade path