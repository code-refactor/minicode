"""
Specific performance tests for conflict resolution.
"""
import pytest
import time
import random
import string
from typing import Dict, List, Any, Optional, Tuple

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database
from syncdb.sync.change_tracker import ChangeTracker
from syncdb.sync.sync_protocol import SyncEngine, NetworkSimulator
from syncdb.sync.conflict_resolution import MergeFieldsResolver
from syncdb.client import SyncClient, SyncServer
from syncdb.sync.manual_sync import register_server_changes_with_client


def generate_random_string(length: int) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def create_schema():
    """Create a schema for conflict resolution testing."""
    # User table
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("description", str, nullable=True),
        Column("created_at", float, default=time.time),
        Column("active", bool, default=True),
        Column("preferences", dict, nullable=True),
        Column("tags", list, nullable=True)
    ]
    user_table = TableSchema("users", user_columns)
    
    # Create the database schema
    tables = {
        "users": user_table,
    }
    schema = DatabaseSchema(tables, version=1)
    
    return schema


def create_test_client_server():
    """Create a test client and server for conflict resolution testing."""
    # Create the schema
    schema = create_schema()
    
    # Create server
    server = SyncServer(schema)
    
    # Create client
    client = SyncClient(
        schema=schema,
        client_id="conflict_test_client",
        power_aware=False  # Disable power management for testing
    )
    
    # Connect client to server
    client.server_url = "mock://server"
    client.sync_engine = server.sync_engine
    client.server_connected = True
    
    # Register the client with the server
    server.register_client(client.client_id)
    
    return client, server


@pytest.mark.parametrize("conflict_count", [10, 50])
def test_conflict_resolution_performance(conflict_count):
    """Test the performance of conflict resolution with different conflict volumes."""
    # Create a client and server
    client, server = create_test_client_server()

    # Create a merge fields resolver
    field_priorities = {
        "users": ["username", "email"]  # Prioritize these fields from client
    }
    merge_resolver = MergeFieldsResolver(field_priorities)

    # Set up conflict resolvers on client, server, and sync engine
    client.register_conflict_resolver("users", merge_resolver)
    server.register_conflict_resolver("users", merge_resolver)

    # The key part: connect the conflict resolver to the sync engine
    # This is where conflicts are actually detected and resolved during sync
    server.sync_engine.conflict_resolver = lambda table, change, record: server.conflict_manager.resolve_conflict(table, change, record)

    # Create test records on client
    for i in range(conflict_count):
        client.insert("users", {
            "id": i,
            "username": f"original_user_{i}",
            "email": f"original_{i}@example.com",
            "description": f"Original description {i}"
        })

    # Manually sync these records to the server
    register_server_changes_with_client(
        server.database,
        client.database,
        "users",
        server.sync_engine.server_id
    )
    
    # Verify all test records exist on both sides
    for i in range(conflict_count):
        server_record = server.get("users", [i])
        client_record = client.get("users", [i])
        assert server_record is not None, f"Record {i} missing on server"
        assert client_record is not None, f"Record {i} missing on client"
    
    # Create conflicts by updating the same records on both client and server
    for i in range(conflict_count):
        # Update on server
        server.update("users", {
            "id": i,
            "username": f"server_{i}",
            "email": f"server_{i}@example.com",
            "description": f"Server description {i}"
        })

        # Update on client
        client.update("users", {
            "id": i,
            "username": f"client_{i}",
            "email": f"client_{i}@example.com",
            "description": f"Client description {i}"
        })
    
    # Sync and measure the time
    start_time = time.time()
    client.sync()
    sync_time = time.time() - start_time
    
    # Check that conflict resolution is reasonably fast
    assert sync_time < conflict_count * 0.01, f"Conflict resolution too slow: {sync_time} for {conflict_count} conflicts"
    
    # Check that the correct conflict resolution was applied
    resolved_count = 0
    for i in range(conflict_count):
        server_record = server.get("users", [i])
        client_record = client.get("users", [i])
        
        # Check if client-side values were used (as per our resolver configuration)
        if server_record and client_record:
            if (server_record["username"] == f"client_{i}" and 
                server_record["email"] == f"client_{i}@example.com"):
                resolved_count += 1
                # Also verify client was updated with the resolved data
                assert client_record["username"] == server_record["username"]
                assert client_record["email"] == server_record["email"]
    
    # Check that at least some conflicts were resolved correctly
    assert resolved_count > 0, "No conflicts were properly resolved"
    
    # Some conflicts should be recorded in the audit log
    server_conflicts = server.get_conflict_history()
    assert len(server_conflicts) > 0, "No conflicts were recorded in the audit log"
    
    # Assert success instead of returning data
    assert conflict_count > 0
    assert sync_time > 0
    assert resolved_count > 0
    # No return value needed