"""
Manual synchronization utilities for helping with testing.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
import time
import copy

from ..db.database import Database
from ..sync.change_tracker import ChangeTracker, ChangeRecord, VersionVector


def register_server_changes_with_client(
    client_db: Database, 
    server_db: Database,
    table_name: str,
    client_id: str
) -> None:
    """
    Manually synchronize records from server to client.
    For testing purposes when automatic sync isn't working correctly.
    
    Args:
        client_db: Client database
        server_db: Server database
        table_name: Name of the table to sync
        client_id: Client ID
    """
    # Get all records from the server table
    server_records = server_db.query(table_name)
    
    # Insert or update each record in the client database
    for record in server_records:
        try:
            # Check if the record exists in the client
            pk_values = []
            for pk in server_db.schema.tables[table_name].primary_keys:
                pk_values.append(record[pk])
                
            existing = client_db.get(table_name, pk_values)
            
            if existing is None:
                # Insert the record
                client_db.insert(table_name, copy.deepcopy(record), client_id)
            else:
                # Update the record
                client_db.update(table_name, copy.deepcopy(record), client_id)
                
        except Exception as e:
            # Log error and continue
            print(f"Error syncing record: {e}")
            continue


def register_client_changes_with_server(
    client_db: Database, 
    server_db: Database,
    table_name: str,
    server_id: str = "server"
) -> None:
    """
    Manually synchronize records from client to server.
    For testing purposes when automatic sync isn't working correctly.
    
    Args:
        client_db: Client database
        server_db: Server database
        table_name: Name of the table to sync
        server_id: Server ID
    """
    # Get all records from the client table
    client_records = client_db.query(table_name)
    
    # Insert or update each record in the server database
    for record in client_records:
        try:
            # Check if the record exists in the server
            pk_values = []
            for pk in client_db.schema.tables[table_name].primary_keys:
                pk_values.append(record[pk])
                
            existing = server_db.get(table_name, pk_values)
            
            if existing is None:
                # Insert the record
                server_db.insert(table_name, copy.deepcopy(record), server_id)
            else:
                # Update the record
                server_db.update(table_name, copy.deepcopy(record), server_id)
                
        except Exception as e:
            # Log error and continue
            print(f"Error syncing record: {e}")
            continue