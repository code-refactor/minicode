"""
Tests for the conflict resolution strategies.
"""
import pytest
import time
import json
from typing import Dict, List, Any, Optional

from syncdb.sync.change_tracker import ChangeRecord
from syncdb.sync.conflict_resolution import (
    ConflictResolver, LastWriteWinsResolver, ServerWinsResolver,
    ClientWinsResolver, MergeFieldsResolver, CustomMergeResolver,
    ConflictManager, ConflictAuditLog, ConflictMetadata
)


def test_conflict_metadata_creation():
    """Test creating conflict metadata."""
    metadata = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    assert metadata.table_name == "users"
    assert metadata.primary_key == (1,)
    assert metadata.client_id == "client1"
    assert metadata.client_change == {"operation": "update"}
    assert metadata.server_record == {"id": 1, "name": "Server"}
    assert metadata.resolution == {"id": 1, "name": "Resolved"}
    assert metadata.resolution_strategy == "LastWriteWins"


def test_conflict_metadata_to_dict():
    """Test converting conflict metadata to a dictionary."""
    metadata = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=123456789.0,
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    # Convert to dictionary
    metadata_dict = metadata.to_dict()
    
    # Check the dictionary
    assert metadata_dict["table_name"] == "users"
    assert metadata_dict["primary_key"] == (1,)
    assert metadata_dict["conflict_time"] == 123456789.0
    assert metadata_dict["client_id"] == "client1"
    assert metadata_dict["client_change"] == {"operation": "update"}
    assert metadata_dict["server_record"] == {"id": 1, "name": "Server"}
    assert metadata_dict["resolution"] == {"id": 1, "name": "Resolved"}
    assert metadata_dict["resolution_strategy"] == "LastWriteWins"


def test_conflict_metadata_from_dict():
    """Test creating conflict metadata from a dictionary."""
    metadata_dict = {
        "table_name": "users",
        "primary_key": (1,),
        "conflict_time": 123456789.0,
        "client_id": "client1",
        "client_change": {"operation": "update"},
        "server_record": {"id": 1, "name": "Server"},
        "resolution": {"id": 1, "name": "Resolved"},
        "resolution_strategy": "LastWriteWins"
    }
    
    # Create metadata from dictionary
    metadata = ConflictMetadata.from_dict(metadata_dict)
    
    # Check the metadata
    assert metadata.table_name == "users"
    assert metadata.primary_key == (1,)
    assert metadata.conflict_time == 123456789.0
    assert metadata.client_id == "client1"
    assert metadata.client_change == {"operation": "update"}
    assert metadata.server_record == {"id": 1, "name": "Server"}
    assert metadata.resolution == {"id": 1, "name": "Resolved"}
    assert metadata.resolution_strategy == "LastWriteWins"


def test_conflict_audit_log_creation():
    """Test creating a conflict audit log."""
    log = ConflictAuditLog()
    assert log.conflicts == []
    assert log.max_history_size > 0


def test_conflict_audit_log_log_conflict():
    """Test logging a conflict."""
    log = ConflictAuditLog()
    
    # Create conflict metadata
    metadata = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    # Log the conflict
    log.log_conflict(metadata)
    
    # Check that the conflict was logged
    assert len(log.conflicts) == 1
    assert log.conflicts[0] == metadata


def test_conflict_audit_log_get_conflicts_for_table():
    """Test getting conflicts for a specific table."""
    log = ConflictAuditLog()
    
    # Create and log conflicts for different tables
    metadata1 = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    metadata2 = ConflictMetadata(
        table_name="tasks",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "title": "Task"},
        resolution={"id": 1, "title": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    log.log_conflict(metadata1)
    log.log_conflict(metadata2)
    
    # Get conflicts for the users table
    users_conflicts = log.get_conflicts_for_table("users")
    
    # Check that only the users conflict was returned
    assert len(users_conflicts) == 1
    assert users_conflicts[0] == metadata1


def test_conflict_audit_log_get_conflicts_for_record():
    """Test getting conflicts for a specific record."""
    log = ConflictAuditLog()
    
    # Create and log conflicts for different records
    metadata1 = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    metadata2 = ConflictMetadata(
        table_name="users",
        primary_key=(2,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 2, "name": "Server 2"},
        resolution={"id": 2, "name": "Resolved 2"},
        resolution_strategy="LastWriteWins"
    )
    
    log.log_conflict(metadata1)
    log.log_conflict(metadata2)
    
    # Get conflicts for user 1
    user1_conflicts = log.get_conflicts_for_record("users", (1,))
    
    # Check that only the user 1 conflict was returned
    assert len(user1_conflicts) == 1
    assert user1_conflicts[0] == metadata1


def test_conflict_audit_log_get_conflicts_for_client():
    """Test getting conflicts for a specific client."""
    log = ConflictAuditLog()
    
    # Create and log conflicts for different clients
    metadata1 = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=time.time(),
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    metadata2 = ConflictMetadata(
        table_name="users",
        primary_key=(2,),
        conflict_time=time.time(),
        client_id="client2",
        client_change={"operation": "update"},
        server_record={"id": 2, "name": "Server 2"},
        resolution={"id": 2, "name": "Resolved 2"},
        resolution_strategy="LastWriteWins"
    )
    
    log.log_conflict(metadata1)
    log.log_conflict(metadata2)
    
    # Get conflicts for client1
    client1_conflicts = log.get_conflicts_for_client("client1")
    
    # Check that only the client1 conflict was returned
    assert len(client1_conflicts) == 1
    assert client1_conflicts[0] == metadata1


def test_conflict_audit_log_export_import():
    """Test exporting and importing the conflict audit log."""
    log = ConflictAuditLog()
    
    # Create and log a conflict
    metadata = ConflictMetadata(
        table_name="users",
        primary_key=(1,),
        conflict_time=123456789.0,  # Use a fixed timestamp for deterministic comparison
        client_id="client1",
        client_change={"operation": "update"},
        server_record={"id": 1, "name": "Server"},
        resolution={"id": 1, "name": "Resolved"},
        resolution_strategy="LastWriteWins"
    )
    
    log.log_conflict(metadata)
    
    # Export the log
    exported = log.export_to_json()
    
    # Create a new log
    new_log = ConflictAuditLog()
    
    # Import the exported log
    new_log.import_from_json(exported)
    
    # Check that the imported log has the same conflicts
    assert len(new_log.conflicts) == 1
    assert new_log.conflicts[0].table_name == "users"
    assert new_log.conflicts[0].primary_key == (1,)
    assert new_log.conflicts[0].conflict_time == 123456789.0
    assert new_log.conflicts[0].client_id == "client1"
    assert new_log.conflicts[0].client_change == {"operation": "update"}
    assert new_log.conflicts[0].server_record == {"id": 1, "name": "Server"}
    assert new_log.conflicts[0].resolution == {"id": 1, "name": "Resolved"}
    assert new_log.conflicts[0].resolution_strategy == "LastWriteWins"


def test_last_write_wins_resolver():
    """Test the last-write-wins resolver."""
    resolver = LastWriteWinsResolver()
    
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),  # Current time (newer)
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Client"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution = resolver.resolve("users", client_change, server_record)
    
    # The client change should win (it's newer)
    assert resolution == {"id": 1, "name": "Client"}


def test_server_wins_resolver():
    """Test the server-wins resolver."""
    resolver = ServerWinsResolver()
    
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Client"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution = resolver.resolve("users", client_change, server_record)
    
    # The server should win
    assert resolution == {"id": 1, "name": "Server"}


def test_client_wins_resolver():
    """Test the client-wins resolver."""
    resolver = ClientWinsResolver()
    
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Client"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution = resolver.resolve("users", client_change, server_record)
    
    # The client should win
    assert resolution == {"id": 1, "name": "Client"}


def test_merge_fields_resolver():
    """Test the merge-fields resolver."""
    # Create a resolver that prioritizes client "name" field and server "email" field
    field_priorities = {
        "users": ["name"]  # Fields to prioritize from client
    }
    resolver = MergeFieldsResolver(field_priorities)
    
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old", "email": "old@example.com"},
        new_data={"id": 1, "name": "Client", "email": "client@example.com"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server", "email": "server@example.com"}
    
    # Resolve the conflict
    resolution = resolver.resolve("users", client_change, server_record)
    
    # Check that the fields were merged correctly
    assert resolution["id"] == 1
    assert resolution["name"] == "Client"  # From client (prioritized)
    assert resolution["email"] == "server@example.com"  # From server (not prioritized)


def test_custom_merge_resolver():
    """Test the custom-merge resolver."""
    # Create a custom merge function
    def custom_merge(client_change, server_record):
        # Create a merged record
        merged = dict(server_record)
        
        # Use client's name if it contains "Admin"
        if client_change.new_data and "name" in client_change.new_data:
            client_name = client_change.new_data["name"]
            if "Admin" in client_name:
                merged["name"] = client_name
        
        return merged
    
    # Create a resolver with the custom merge function
    merge_functions = {
        "users": custom_merge
    }
    resolver = CustomMergeResolver(merge_functions)
    
    # Create a change record (client change) with "Admin" in the name
    client_change1 = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Admin User"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution1 = resolver.resolve("users", client_change1, server_record)
    
    # The client's name should be used (it contains "Admin")
    assert resolution1["id"] == 1
    assert resolution1["name"] == "Admin User"
    
    # Create another change record without "Admin" in the name
    client_change2 = ChangeRecord(
        id=1,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Regular User"}
    )
    
    # Resolve the conflict
    resolution2 = resolver.resolve("users", client_change2, server_record)
    
    # The server's name should be used (client name doesn't contain "Admin")
    assert resolution2["id"] == 1
    assert resolution2["name"] == "Server"


def test_conflict_manager_creation(conflict_audit_log):
    """Test creating a conflict manager."""
    manager = ConflictManager(conflict_audit_log)
    
    # Check that the default resolver is LastWriteWinsResolver
    assert isinstance(manager.default_resolver, LastWriteWinsResolver)
    assert manager.resolvers == {}
    assert manager.audit_log == conflict_audit_log


def test_conflict_manager_register_resolver(conflict_manager):
    """Test registering a resolver with the conflict manager."""
    # Register a resolver for a specific table
    resolver = ServerWinsResolver()
    conflict_manager.register_resolver("users", resolver)
    
    # Check that the resolver was registered
    assert conflict_manager.resolvers["users"] == resolver


def test_conflict_manager_set_default_resolver(conflict_manager):
    """Test setting the default resolver in the conflict manager."""
    # Set a new default resolver
    resolver = ClientWinsResolver()
    conflict_manager.set_default_resolver(resolver)
    
    # Check that the default resolver was set
    assert conflict_manager.default_resolver == resolver


def test_conflict_manager_resolve_conflict(conflict_manager):
    """Test resolving a conflict using the conflict manager."""
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Client"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution = conflict_manager.resolve_conflict("users", client_change, server_record)
    
    # The last-write-wins resolver should be used (default)
    assert resolution == {"id": 1, "name": "Client"}
    
    # Check that the conflict was logged
    assert len(conflict_manager.audit_log.conflicts) == 1
    conflict = conflict_manager.audit_log.conflicts[0]
    assert conflict.table_name == "users"
    assert conflict.primary_key == (1,)
    assert conflict.client_id == "client1"
    assert conflict.resolution == {"id": 1, "name": "Client"}
    assert conflict.resolution_strategy == "LastWriteWinsResolver"


def test_conflict_manager_resolve_with_specific_resolver(conflict_manager):
    """Test resolving a conflict using a specific resolver."""
    # Register a resolver for the users table
    resolver = ServerWinsResolver()
    conflict_manager.register_resolver("users", resolver)
    
    # Create a change record (client change)
    client_change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="update",
        timestamp=time.time(),
        client_id="client1",
        old_data={"id": 1, "name": "Old"},
        new_data={"id": 1, "name": "Client"}
    )
    
    # Create a server record
    server_record = {"id": 1, "name": "Server"}
    
    # Resolve the conflict
    resolution = conflict_manager.resolve_conflict("users", client_change, server_record)
    
    # The server-wins resolver should be used
    assert resolution == {"id": 1, "name": "Server"}
    
    # Check that the conflict was logged
    assert len(conflict_manager.audit_log.conflicts) == 1
    conflict = conflict_manager.audit_log.conflicts[0]
    assert conflict.resolution_strategy == "ServerWinsResolver"