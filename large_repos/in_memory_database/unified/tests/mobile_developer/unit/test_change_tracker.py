"""
Tests for the change tracking system.
"""
import pytest
import time
from typing import Dict, List, Any, Tuple

from syncdb.sync.change_tracker import ChangeTracker, ChangeRecord, VersionVector


def test_change_tracker_creation():
    """Test creating a change tracker."""
    tracker = ChangeTracker()
    assert tracker.changes == {}
    assert tracker.counters == {}
    assert tracker.max_history_size > 0


def test_record_change():
    """Test recording a change."""
    tracker = ChangeTracker()
    
    # Record an insert change
    change = tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    # Check the change record
    assert change.id == 0  # First change gets ID 0
    assert change.table_name == "users"
    assert change.primary_key == (1,)
    assert change.operation == "insert"
    assert change.old_data is None
    assert change.new_data == {"id": 1, "name": "Alice"}
    assert change.client_id == "client1"
    
    # Check that the change was added to the tracker
    assert "users" in tracker.changes
    assert len(tracker.changes["users"]) == 1
    assert tracker.changes["users"][0] == change


def test_record_multiple_changes():
    """Test recording multiple changes."""
    tracker = ChangeTracker()
    
    # Record multiple changes
    change1 = tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    change2 = tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="update",
        old_data={"id": 1, "name": "Alice"},
        new_data={"id": 1, "name": "Alice Updated"},
        client_id="client1"
    )
    
    # Check that both changes were added to the tracker
    assert len(tracker.changes["users"]) == 2
    assert tracker.changes["users"][0] == change1
    assert tracker.changes["users"][1] == change2
    
    # Check that the counter was incremented
    assert tracker.counters["users"] == 2


def test_record_changes_different_tables():
    """Test recording changes to different tables."""
    tracker = ChangeTracker()
    
    # Record changes to different tables
    change1 = tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    change2 = tracker.record_change(
        table_name="tasks",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "title": "Task 1"},
        client_id="client1"
    )
    
    # Check that changes were added to the correct tables
    assert len(tracker.changes["users"]) == 1
    assert len(tracker.changes["tasks"]) == 1
    assert tracker.changes["users"][0] == change1
    assert tracker.changes["tasks"][0] == change2
    
    # Check that each table has its own counter
    assert tracker.counters["users"] == 1
    assert tracker.counters["tasks"] == 1


def test_get_changes_since():
    """Test getting changes since a specific change ID."""
    tracker = ChangeTracker()
    
    # Record multiple changes
    tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    tracker.record_change(
        table_name="users",
        primary_key=(2,),
        operation="insert",
        old_data=None,
        new_data={"id": 2, "name": "Bob"},
        client_id="client1"
    )
    
    tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="update",
        old_data={"id": 1, "name": "Alice"},
        new_data={"id": 1, "name": "Alice Updated"},
        client_id="client1"
    )
    
    # Get changes since ID 0
    changes = tracker.get_changes_since("users", 0)
    
    # Should get the last two changes
    assert len(changes) == 2
    assert changes[0].id == 1
    assert changes[1].id == 2


def test_get_changes_since_with_client_exclusion():
    """Test getting changes since a specific change ID, excluding a client."""
    tracker = ChangeTracker()
    
    # Record changes from different clients
    tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    tracker.record_change(
        table_name="users",
        primary_key=(2,),
        operation="insert",
        old_data=None,
        new_data={"id": 2, "name": "Bob"},
        client_id="client2"
    )
    
    tracker.record_change(
        table_name="users",
        primary_key=(3,),
        operation="insert",
        old_data=None,
        new_data={"id": 3, "name": "Charlie"},
        client_id="client1"
    )
    
    # Get changes since ID 0, excluding client1
    changes = tracker.get_changes_since("users", 0, exclude_client_id="client1")
    
    # Should only get the change from client2
    assert len(changes) == 1
    assert changes[0].id == 1
    assert changes[0].client_id == "client2"


def test_get_latest_change_id():
    """Test getting the latest change ID."""
    tracker = ChangeTracker()
    
    # Initially there are no changes
    assert tracker.get_latest_change_id("users") == -1
    
    # Record some changes
    tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    tracker.record_change(
        table_name="users",
        primary_key=(2,),
        operation="insert",
        old_data=None,
        new_data={"id": 2, "name": "Bob"},
        client_id="client1"
    )
    
    # The latest change ID should be 1
    assert tracker.get_latest_change_id("users") == 1


def test_serialize_deserialize_changes():
    """Test serializing and deserializing changes."""
    tracker = ChangeTracker()
    
    # Record some changes
    change1 = tracker.record_change(
        table_name="users",
        primary_key=(1,),
        operation="insert",
        old_data=None,
        new_data={"id": 1, "name": "Alice"},
        client_id="client1"
    )
    
    change2 = tracker.record_change(
        table_name="users",
        primary_key=(2,),
        operation="insert",
        old_data=None,
        new_data={"id": 2, "name": "Bob"},
        client_id="client1"
    )
    
    # Serialize the changes
    changes = [change1, change2]
    serialized = tracker.serialize_changes(changes)
    
    # Deserialize the changes
    deserialized = tracker.deserialize_changes(serialized)
    
    # Check that the deserialized changes match the original
    assert len(deserialized) == 2
    assert deserialized[0].id == change1.id
    assert deserialized[0].table_name == change1.table_name
    assert deserialized[0].primary_key == change1.primary_key
    assert deserialized[0].operation == change1.operation
    assert deserialized[0].client_id == change1.client_id
    assert deserialized[0].new_data == change1.new_data
    
    assert deserialized[1].id == change2.id
    assert deserialized[1].table_name == change2.table_name
    assert deserialized[1].primary_key == change2.primary_key
    assert deserialized[1].operation == change2.operation
    assert deserialized[1].client_id == change2.client_id
    assert deserialized[1].new_data == change2.new_data


def test_change_record_to_dict():
    """Test converting a change record to a dictionary."""
    # Create a change record
    change = ChangeRecord(
        id=0,
        table_name="users",
        primary_key=(1,),
        operation="insert",
        timestamp=123456789.0,
        client_id="client1",
        old_data=None,
        new_data={"id": 1, "name": "Alice"}
    )
    
    # Convert to dictionary
    change_dict = change.to_dict()
    
    # Check the dictionary
    assert change_dict["id"] == 0
    assert change_dict["table_name"] == "users"
    assert change_dict["primary_key"] == (1,)
    assert change_dict["operation"] == "insert"
    assert change_dict["timestamp"] == 123456789.0
    assert change_dict["client_id"] == "client1"
    assert change_dict["old_data"] is None
    assert change_dict["new_data"] == {"id": 1, "name": "Alice"}


def test_change_record_from_dict():
    """Test creating a change record from a dictionary."""
    # Create a dictionary
    change_dict = {
        "id": 0,
        "table_name": "users",
        "primary_key": (1,),
        "operation": "insert",
        "timestamp": 123456789.0,
        "client_id": "client1",
        "old_data": None,
        "new_data": {"id": 1, "name": "Alice"}
    }
    
    # Create a change record from the dictionary
    change = ChangeRecord.from_dict(change_dict)
    
    # Check the change record
    assert change.id == 0
    assert change.table_name == "users"
    assert change.primary_key == (1,)
    assert change.operation == "insert"
    assert change.timestamp == 123456789.0
    assert change.client_id == "client1"
    assert change.old_data is None
    assert change.new_data == {"id": 1, "name": "Alice"}


def test_version_vector_creation():
    """Test creating a version vector."""
    vector = VersionVector("client1")
    assert vector.vector == {"client1": 0}
    assert vector.client_id == "client1"


def test_version_vector_increment():
    """Test incrementing a version vector."""
    vector = VersionVector("client1")
    
    # Initial value
    assert vector.vector["client1"] == 0
    
    # Increment
    vector.increment()
    assert vector.vector["client1"] == 1
    
    # Increment again
    vector.increment()
    assert vector.vector["client1"] == 2


def test_version_vector_update():
    """Test updating a version vector with another vector."""
    vector1 = VersionVector("client1")
    vector1.increment()  # client1: 1
    
    vector2 = VersionVector("client2")
    vector2.increment()  # client2: 1
    vector2.increment()  # client2: 2
    
    # Update vector1 with vector2
    vector1.update(vector2)
    
    # vector1 should now have entries for both clients
    assert vector1.vector["client1"] == 1
    assert vector1.vector["client2"] == 2


def test_version_vector_dominates():
    """Test checking if one vector dominates another."""
    vector1 = VersionVector("client1")
    vector1.vector = {"client1": 2, "client2": 3}
    
    vector2 = VersionVector("client2")
    vector2.vector = {"client1": 1, "client2": 2}
    
    # vector1 dominates vector2
    assert vector1.dominates(vector2)
    
    # vector2 does not dominate vector1
    assert not vector2.dominates(vector1)


def test_version_vector_not_dominates():
    """Test cases where one vector does not dominate another."""
    vector1 = VersionVector("client1")
    vector1.vector = {"client1": 2, "client2": 1}
    
    vector2 = VersionVector("client2")
    vector2.vector = {"client1": 1, "client2": 2}
    
    # Neither vector dominates the other
    assert not vector1.dominates(vector2)
    assert not vector2.dominates(vector1)


def test_version_vector_concurrent():
    """Test checking if two vectors are concurrent."""
    vector1 = VersionVector("client1")
    vector1.vector = {"client1": 2, "client2": 1}
    
    vector2 = VersionVector("client2")
    vector2.vector = {"client1": 1, "client2": 2}
    
    # The vectors are concurrent
    assert vector1.concurrent_with(vector2)
    
    # Symmetrically
    assert vector2.concurrent_with(vector1)


def test_version_vector_not_concurrent():
    """Test cases where two vectors are not concurrent."""
    vector1 = VersionVector("client1")
    vector1.vector = {"client1": 2, "client2": 3}
    
    vector2 = VersionVector("client2")
    vector2.vector = {"client1": 1, "client2": 2}
    
    # vector1 dominates vector2, so they are not concurrent
    assert not vector1.concurrent_with(vector2)
    
    # Symmetrically
    assert not vector2.concurrent_with(vector1)


def test_version_vector_to_dict():
    """Test converting a version vector to a dictionary."""
    vector = VersionVector("client1")
    vector.vector = {"client1": 2, "client2": 3}
    
    # Convert to dictionary
    vector_dict = vector.to_dict()
    
    # Check the dictionary
    assert vector_dict == {"client1": 2, "client2": 3}


def test_version_vector_from_dict():
    """Test creating a version vector from a dictionary."""
    # Create a dictionary
    vector_dict = {"client1": 2, "client2": 3}
    
    # Create a version vector from the dictionary
    vector = VersionVector.from_dict(vector_dict, "client1")
    
    # Check the version vector
    assert vector.client_id == "client1"
    assert vector.vector == {"client1": 2, "client2": 3}