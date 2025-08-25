"""
Tests for the in-memory database engine.
"""
import pytest
import time
from typing import Dict, List, Any

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database, Transaction


def test_database_creation(sample_schema):
    """Test creating a database with a schema."""
    db = Database(sample_schema)
    
    # Check that the database has the correct tables
    assert set(db.tables.keys()) == {"users", "tasks", "notes"}
    assert db.schema == sample_schema


def test_insert_record(sample_database):
    """Test inserting a record."""
    # Insert a new user
    user = {
        "id": 3,
        "username": "charlie",
        "email": "charlie@example.com"
    }
    
    result = sample_database.insert("users", user)
    
    # Check that the record was inserted correctly
    assert result["id"] == 3
    assert result["username"] == "charlie"
    assert result["email"] == "charlie@example.com"
    assert "created_at" in result
    assert result["active"] is True  # Default value
    
    # Check that the record can be retrieved
    retrieved = sample_database.get("users", [3])
    assert retrieved == result


def test_insert_duplicate_primary_key(sample_database):
    """Test inserting a record with a duplicate primary key."""
    # Try to insert a user with an existing ID
    user = {
        "id": 1,  # This ID already exists
        "username": "duplicate",
        "email": "duplicate@example.com"
    }
    
    # This should raise an exception
    with pytest.raises(ValueError):
        sample_database.insert("users", user)


def test_update_record(sample_database):
    """Test updating a record."""
    # Update an existing user
    user = {
        "id": 1,
        "username": "alice_updated",
        "email": "alice_updated@example.com",
        "active": False
    }
    
    result = sample_database.update("users", user)
    
    # Check that the record was updated correctly
    assert result["id"] == 1
    assert result["username"] == "alice_updated"
    assert result["email"] == "alice_updated@example.com"
    assert result["active"] is False
    
    # Check that the record can be retrieved with updated values
    retrieved = sample_database.get("users", [1])
    assert retrieved == result


def test_update_nonexistent_record(sample_database):
    """Test updating a record that doesn't exist."""
    # Try to update a non-existent user
    user = {
        "id": 999,  # This ID doesn't exist
        "username": "nonexistent",
        "email": "nonexistent@example.com"
    }
    
    # This should raise an exception
    with pytest.raises(ValueError):
        sample_database.update("users", user)


def test_delete_record(sample_database):
    """Test deleting a record."""
    # The record exists before deletion
    assert sample_database.get("users", [1]) is not None
    
    # Delete the record
    sample_database.delete("users", [1])
    
    # The record should no longer exist
    assert sample_database.get("users", [1]) is None


def test_delete_nonexistent_record(sample_database):
    """Test deleting a record that doesn't exist."""
    # Try to delete a non-existent user
    with pytest.raises(ValueError):
        sample_database.delete("users", [999])  # This ID doesn't exist


def test_get_record(sample_database):
    """Test retrieving a record by primary key."""
    # Get an existing user
    user = sample_database.get("users", [1])
    
    # Check the record values
    assert user["id"] == 1
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"


def test_get_nonexistent_record(sample_database):
    """Test retrieving a record that doesn't exist."""
    # Try to get a non-existent user
    user = sample_database.get("users", [999])
    
    # This should return None
    assert user is None


def test_query_records(sample_database):
    """Test querying records with conditions."""
    # Query tasks for a specific user
    tasks = sample_database.query("tasks", {"user_id": 1})
    
    # Should return 2 tasks
    assert len(tasks) == 2
    assert tasks[0]["user_id"] == 1
    assert tasks[1]["user_id"] == 1


def test_query_with_limit(sample_database):
    """Test querying records with a limit."""
    # Query tasks with a limit
    tasks = sample_database.query("tasks", {"user_id": 1}, limit=1)
    
    # Should return 1 task
    assert len(tasks) == 1
    assert tasks[0]["user_id"] == 1


def test_query_no_results(sample_database):
    """Test querying with conditions that match no records."""
    # Query with conditions that don't match any records
    tasks = sample_database.query("tasks", {"user_id": 999})
    
    # Should return an empty list
    assert tasks == []


def test_transaction_commit(sample_database):
    """Test committing a transaction."""
    # Start a transaction
    with sample_database.begin_transaction() as transaction:
        # Insert a record in the transaction
        transaction.insert("users", {
            "id": 3,
            "username": "charlie",
            "email": "charlie@example.com"
        })
        
        # Record shouldn't be visible outside the transaction until committed
        assert sample_database.get("users", [3]) is not None
        
        # Commit the transaction
        transaction.commit()
    
    # Record should now be visible
    user = sample_database.get("users", [3])
    assert user is not None
    assert user["username"] == "charlie"


def test_transaction_rollback(sample_database):
    """Test rolling back a transaction."""
    try:
        # Start a transaction
        with sample_database.begin_transaction() as transaction:
            # Insert a record in the transaction
            transaction.insert("users", {
                "id": 3,
                "username": "charlie",
                "email": "charlie@example.com"
            })
            
            # Record should be visible within the transaction
            assert sample_database.get("users", [3]) is not None
            
            # Raise an exception to trigger rollback
            raise ValueError("Trigger rollback")
    except ValueError:
        pass
    
    # Record should not be visible after rollback
    assert sample_database.get("users", [3]) is None


def test_transaction_explicit_rollback(sample_database):
    """Test explicitly rolling back a transaction."""
    # Start a transaction
    transaction = sample_database.begin_transaction()
    
    # Insert a record in the transaction
    transaction.insert("users", {
        "id": 3,
        "username": "charlie",
        "email": "charlie@example.com"
    })
    
    # Record should be visible within the transaction
    assert sample_database.get("users", [3]) is not None
    
    # Explicitly roll back the transaction
    transaction.rollback()
    
    # Record should not be visible after rollback
    assert sample_database.get("users", [3]) is None


def test_change_log(sample_database):
    """Test that changes are recorded in the change log."""
    # Insert a record
    sample_database.insert("users", {
        "id": 3,
        "username": "charlie",
        "email": "charlie@example.com"
    }, client_id="test_client")
    
    # Get the changes for the users table
    changes = sample_database.get_changes_since("users", -1)
    
    # There should be at least one change
    assert len(changes) >= 1
    
    # The last change should be the insert we just did
    last_change = changes[-1]
    assert last_change["operation"] == "insert"
    assert last_change["primary_key"] == (3,)
    assert last_change["client_id"] == "test_client"
    assert last_change["new_record"]["username"] == "charlie"