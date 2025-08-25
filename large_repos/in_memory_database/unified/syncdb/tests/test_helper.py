"""
Simple test helper to simulate conflict resolution without using the full sync protocol.
"""
from typing import Dict, List, Any, Optional, Tuple
import time

from ..db.schema import DatabaseSchema, TableSchema, Column
from ..db.database import Database
from ..sync.change_tracker import ChangeTracker, ChangeRecord, VersionVector
from ..sync.conflict_resolution import MergeFieldsResolver, ClientWinsResolver


def simulate_conflict_resolution():
    """
    A simple helper function that directly simulates a conflict resolution
    scenario without using the sync protocol machinery.
    
    Returns:
        True if the conflict was resolved correctly, False otherwise
    """
    # Create a schema
    user_columns = [
        Column("id", int, primary_key=True),
        Column("username", str),
        Column("email", str),
        Column("description", str, nullable=True)
    ]
    user_table = TableSchema("users", user_columns)
    tables = {"users": user_table}
    schema = DatabaseSchema(tables, version=1)
    
    # Create a database and a conflict resolver
    db = Database(schema)
    
    # Insert a record
    db.insert("users", {
        "id": 0,
        "username": "original_user",
        "email": "original@example.com",
        "description": "Original description"
    })
    
    # Simulate client and server changes to the same record
    client_record = {
        "id": 0,
        "username": "client_user",
        "email": "client@example.com",
        "description": "Client description"
    }
    
    server_record = db.get("users", [0])
    
    # Create a change record to represent client change
    client_change = ChangeRecord(
        id=1,
        table_name="users",
        primary_key=(0,),
        operation="update",
        timestamp=time.time(),
        client_id="test_client",
        old_data=None,  # We don't have the old data from client perspective
        new_data=client_record
    )
    
    # Create a resolver
    field_priorities = {
        "users": ["username", "email"]  # Prioritize these fields from client
    }
    resolver = MergeFieldsResolver(field_priorities)
    
    # Resolve the conflict
    result = resolver.resolve("users", client_change, server_record)
    
    # Check if it worked as expected
    if (result and 
        result["username"] == "client_user" and 
        result["email"] == "client@example.com"):
        return True
    
    return False