"""
Shared test fixtures for the SyncDB test suite.
"""
import pytest
import time
from typing import Dict, List, Any, Optional

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database
from syncdb.sync.change_tracker import ChangeTracker
from syncdb.sync.sync_protocol import SyncEngine, NetworkSimulator
from syncdb.sync.conflict_resolution import (
    ConflictResolver, LastWriteWinsResolver, ConflictManager, ConflictAuditLog
)
from syncdb.client import SyncClient, SyncServer


@pytest.fixture
def sample_schema():
    """Create a sample database schema for testing."""
    # User table
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("created_at", float, default=time.time),
        Column("active", bool, default=True)
    ]
    user_table = TableSchema("users", user_columns)
    
    # Task table
    task_columns = [
        Column("id", int, primary_key=True),
        Column("user_id", int),
        Column("title", str),
        Column("description", str, nullable=True),
        Column("due_date", float, nullable=True),
        Column("completed", bool, default=False),
        Column("created_at", float, default=time.time),
        Column("updated_at", float, default=time.time)
    ]
    task_table = TableSchema("tasks", task_columns)
    
    # Note table
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
    schema = DatabaseSchema(tables, version=1)
    
    return schema


@pytest.fixture
def sample_database(sample_schema):
    """Create a sample database with the sample schema."""
    database = Database(sample_schema)
    
    # Add some sample data
    # Users
    database.insert("users", {"id": 1, "username": "alice", "email": "alice@example.com"})
    database.insert("users", {"id": 2, "username": "bob", "email": "bob@example.com"})
    
    # Tasks
    database.insert("tasks", {
        "id": 1, 
        "user_id": 1, 
        "title": "Complete project", 
        "description": "Finish the SyncDB implementation"
    })
    database.insert("tasks", {
        "id": 2, 
        "user_id": 1, 
        "title": "Write tests", 
        "description": "Create comprehensive tests for SyncDB"
    })
    database.insert("tasks", {
        "id": 3, 
        "user_id": 2, 
        "title": "Review code", 
        "description": "Review the SyncDB implementation"
    })
    
    # Notes
    database.insert("notes", {
        "id": 1,
        "task_id": 1,
        "content": "Make sure to implement all requirements"
    })
    database.insert("notes", {
        "id": 2,
        "task_id": 2,
        "content": "Include unit, integration, and performance tests"
    })
    
    return database


@pytest.fixture
def change_tracker():
    """Create a change tracker for testing."""
    return ChangeTracker()


@pytest.fixture
def network_simulator():
    """Create a network simulator for testing."""
    return NetworkSimulator()


@pytest.fixture
def perfect_network_simulator():
    """Create a perfect network simulator (no latency, no packet loss)."""
    return NetworkSimulator(latency_ms=0, packet_loss_percent=0.0)


@pytest.fixture
def poor_network_simulator():
    """Create a poor network simulator (high latency, some packet loss)."""
    return NetworkSimulator(latency_ms=200, packet_loss_percent=10.0)


@pytest.fixture
def sync_engine(sample_database, change_tracker, perfect_network_simulator):
    """Create a sync engine for testing."""
    return SyncEngine(
        database=sample_database,
        change_tracker=change_tracker,
        network=perfect_network_simulator
    )


@pytest.fixture
def conflict_audit_log():
    """Create a conflict audit log for testing."""
    return ConflictAuditLog()


@pytest.fixture
def conflict_manager(conflict_audit_log):
    """Create a conflict manager for testing."""
    manager = ConflictManager(conflict_audit_log)
    manager.set_default_resolver(LastWriteWinsResolver())
    return manager


@pytest.fixture
def sync_server(sample_schema):
    """Create a sync server for testing."""
    return SyncServer(sample_schema)


@pytest.fixture
def sync_client(sample_schema):
    """Create a sync client for testing."""
    client = SyncClient(
        schema=sample_schema,
        client_id="test_client",
        power_aware=False  # Disable power management for testing
    )
    return client


@pytest.fixture
def connected_client_server(sync_client, sync_server):
    """Create a connected client-server pair for testing."""
    # Set up the client to connect to the server
    sync_client.server_url = "mock://server"
    # Instead of sharing a sync engine, we just use the server's sync engine
    # for communication but maintain separate databases
    sync_client.sync_engine = sync_server.sync_engine
    sync_client.server_connected = True

    # Make sure the server's sync engine has the proper database reference
    sync_server.sync_engine.database = sync_server.database

    # Register the client with the server
    sync_server.register_client(sync_client.client_id)

    return sync_client, sync_server