"""
Simple test focusing only on conflict resolution.
"""
import pytest
import time

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database
from syncdb.sync.change_tracker import ChangeTracker, ChangeRecord, VersionVector
from syncdb.sync.conflict_resolution import (
    MergeFieldsResolver, ClientWinsResolver
)
from syncdb.client import SyncClient, SyncServer


def test_simple_conflict_resolution():
    """Simple test that directly creates and resolves a conflict."""
    # Create a schema
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("description", str, nullable=True)
    ]
    user_table = TableSchema("users", user_columns)
    schema = DatabaseSchema({"users": user_table}, version=1)
    
    # Create a database
    db = Database(schema)
    
    # Insert a record
    original_record = {
        "id": 0,
        "username": "original_user",
        "email": "original@example.com",
        "description": "Original description"
    }
    db.insert("users", original_record)
    
    # Create server and client changes representing a conflict
    server_record = {
        "id": 0,
        "username": "server_user",
        "email": "server@example.com",
        "description": "Server description"
    }
    
    client_record = {
        "id": 0,
        "username": "client_user",
        "email": "client@example.com",
        "description": "Client description"
    }
    
    # Create a change record for the client change
    client_change = ChangeRecord(
        id=1,
        table_name="users",
        primary_key=(0,),
        operation="update",
        timestamp=time.time(),
        client_id="test_client",
        old_data=original_record,
        new_data=client_record
    )
    
    # Create resolvers to test
    client_resolver = ClientWinsResolver()
    field_resolver = MergeFieldsResolver({"users": ["username", "email"]})
    
    # Test client wins resolver
    client_result = client_resolver.resolve("users", client_change, server_record)
    assert client_result["username"] == "client_user"
    assert client_result["email"] == "client@example.com"
    assert client_result["description"] == "Client description"
    
    # Test merge fields resolver
    merge_result = field_resolver.resolve("users", client_change, server_record)
    assert merge_result["username"] == "client_user"
    assert merge_result["email"] == "client@example.com"
    assert merge_result["description"] == "Server description"
    
    print("Conflict resolution strategies working correctly at the resolver level")
    
    # Now test with the actual SyncClient and SyncServer
    server = SyncServer(schema)
    client = SyncClient(schema, client_id="test_client")
    client.server_url = "mock://server"
    client.sync_engine = server.sync_engine
    client.server_connected = True
    server.register_client(client.client_id)
    
    # Set client-wins resolver on both client and server
    client.register_conflict_resolver("users", ClientWinsResolver())
    server.register_conflict_resolver("users", ClientWinsResolver())
    
    # Make sure the conflict resolver is connected to the sync engine
    # This is where conflicts are detected and resolved during sync
    server.sync_engine.conflict_resolver = lambda table, change, record: server.conflict_manager.resolve_conflict(table, change, record)
    
    # Insert the same record on both server and client
    server.insert("users", {
        "id": 1,
        "username": "original",
        "email": "original@example.com",
        "description": "Original description"
    })
    
    client.insert("users", {
        "id": 1,
        "username": "original",
        "email": "original@example.com",
        "description": "Original description"
    })
    
    # Update the record differently on server and client to create a conflict
    server.update("users", {
        "id": 1,
        "username": "server_updated",
        "email": "server@example.com",
        "description": "Server description"
    })
    
    client.update("users", {
        "id": 1,
        "username": "client_updated",
        "email": "client@example.com",
        "description": "Client description"
    })
    
    # Perform sync
    client.sync()
    
    # Check the results - with ClientWinsResolver, client changes should be applied
    server_result = server.get("users", [1])
    client_result = client.get("users", [1])
    
    print("After sync:")
    print(f"Server record: {server_result}")
    print(f"Client record: {client_result}")
    
    # Test should be successful if conflict resolution is working
    assert server_result is not None, "Server record missing"
    assert client_result is not None, "Client record missing"
    
    # With ClientWinsResolver, server record should match client record
    assert server_result["username"] == "client_updated", "Username not from client"
    assert server_result["email"] == "client@example.com", "Email not from client"
    assert server_result["description"] == "Client description", "Description not from client"
    
    # There should be conflicts in the history
    conflicts = server.get_conflict_history()
    print(f"Conflicts in history: {len(conflicts)}")
    for conflict in conflicts:
        print(f"Conflict: {conflict.get('table_name')} - {conflict.get('primary_key')}")
        print(f"  Resolution: {conflict.get('resolution')}")