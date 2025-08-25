"""
Tests for the differential sync protocol.
"""
import pytest
import json
import time
from typing import Dict, List, Any, Tuple

from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database
from syncdb.sync.change_tracker import ChangeTracker, VersionVector
from syncdb.sync.sync_protocol import (
    SyncEngine, NetworkSimulator, SyncRequest, SyncResponse,
    SyncState
)


def test_network_simulator_no_loss():
    """Test that the network simulator doesn't lose packets by default."""
    simulator = NetworkSimulator()
    data = "test data"
    result = simulator.send(data)
    assert result == data


def test_network_simulator_with_loss():
    """Test that the network simulator can simulate packet loss."""
    simulator = NetworkSimulator(packet_loss_percent=100.0)  # Always lose packets
    data = "test data"
    result = simulator.send(data)
    assert result is None


def test_network_simulator_with_latency():
    """Test that the network simulator can simulate latency."""
    latency_ms = 100
    simulator = NetworkSimulator(latency_ms=latency_ms)
    data = "test data"
    
    start_time = time.time()
    result = simulator.send(data)
    end_time = time.time()
    
    assert result == data
    elapsed_ms = (end_time - start_time) * 1000
    assert elapsed_ms >= latency_ms  # Allow for some processing time


def test_sync_state_creation():
    """Test creating a sync state."""
    state = SyncState("client1")
    assert state.client_id == "client1"
    assert state.last_sync_time == 0.0
    assert state.sync_count == 0
    assert state.table_change_ids == {}
    assert state.version_vectors == {}


def test_sync_state_update_table_change_id():
    """Test updating the table change ID in a sync state."""
    state = SyncState("client1")
    
    # Update for the first time
    state.update_table_change_id("users", 5)
    assert state.table_change_ids["users"] == 5
    
    # Update to a higher ID
    state.update_table_change_id("users", 10)
    assert state.table_change_ids["users"] == 10
    
    # Update to a lower ID (should not change)
    state.update_table_change_id("users", 3)
    assert state.table_change_ids["users"] == 10


def test_sync_state_get_table_change_id():
    """Test getting the table change ID from a sync state."""
    state = SyncState("client1")
    
    # Initially, the ID is -1 (no changes)
    assert state.get_table_change_id("users") == -1
    
    # After updating, the ID should reflect the update
    state.update_table_change_id("users", 5)
    assert state.get_table_change_id("users") == 5


def test_sync_state_update_version_vector():
    """Test updating the version vector in a sync state."""
    state = SyncState("client1")
    
    # Create a version vector
    vector = VersionVector("client1")
    vector.increment()  # client1: 1
    
    # Update the state with the vector
    state.update_version_vector("users", vector)
    
    # Check that the vector was added
    assert "users" in state.version_vectors
    assert state.version_vectors["users"].vector["client1"] == 1
    
    # Update with another vector
    vector2 = VersionVector("client2")
    vector2.increment()  # client2: 1
    vector2.increment()  # client2: 2
    
    state.update_version_vector("users", vector2)
    
    # Check that the vectors were merged
    assert state.version_vectors["users"].vector["client1"] == 1
    assert state.version_vectors["users"].vector["client2"] == 2


def test_sync_state_get_version_vector():
    """Test getting the version vector from a sync state."""
    state = SyncState("client1")
    
    # Initially, a new vector is created
    vector = state.get_version_vector("users")
    assert vector.client_id == "client1"
    assert vector.vector["client1"] == 0
    
    # After updating, the vector should reflect the update
    vector.increment()  # client1: 1
    state.version_vectors["users"] = vector
    
    retrieved_vector = state.get_version_vector("users")
    assert retrieved_vector.vector["client1"] == 1


def test_sync_state_mark_sync_complete():
    """Test marking a sync as complete."""
    state = SyncState("client1")
    
    # Initially, last_sync_time is 0 and sync_count is 0
    assert state.last_sync_time == 0.0
    assert state.sync_count == 0
    
    # Mark sync complete
    state.mark_sync_complete()
    
    # last_sync_time should be updated and sync_count incremented
    assert state.last_sync_time > 0.0
    assert state.sync_count == 1


def test_sync_request_from_dict():
    """Test creating a sync request from a dictionary."""
    request_dict = {
        "client_id": "client1",
        "table_change_ids": {"users": 5, "tasks": 3},
        "client_changes": {
            "users": [
                {
                    "id": 0,
                    "table_name": "users",
                    "primary_key": [1],
                    "operation": "insert",
                    "timestamp": 123456789.0,
                    "client_id": "client1",
                    "old_record": None,
                    "new_record": {"id": 1, "name": "Alice"}
                }
            ]
        },
        "version_vectors": {
            "users": {"client1": 1},
            "tasks": {"client1": 1}
        }
    }
    
    request = SyncRequest.from_dict(request_dict)
    
    assert request.client_id == "client1"
    assert request.table_change_ids == {"users": 5, "tasks": 3}
    assert len(request.client_changes["users"]) == 1
    assert request.version_vectors == {
        "users": {"client1": 1},
        "tasks": {"client1": 1}
    }


def test_sync_request_to_dict():
    """Test converting a sync request to a dictionary."""
    # Create a sync request
    request = SyncRequest(
        client_id="client1",
        table_change_ids={"users": 5, "tasks": 3},
        client_changes={},
        version_vectors={
            "users": {"client1": 1},
            "tasks": {"client1": 1}
        }
    )
    
    # Convert to dictionary
    request_dict = request.to_dict()
    
    # Check the dictionary
    assert request_dict["client_id"] == "client1"
    assert request_dict["table_change_ids"] == {"users": 5, "tasks": 3}
    assert request_dict["client_changes"] == {}
    assert request_dict["version_vectors"] == {
        "users": {"client1": 1},
        "tasks": {"client1": 1}
    }


def test_sync_response_from_dict():
    """Test creating a sync response from a dictionary."""
    response_dict = {
        "server_changes": {
            "users": [
                {
                    "id": 0,
                    "table_name": "users",
                    "primary_key": [1],
                    "operation": "insert",
                    "timestamp": 123456789.0,
                    "client_id": "server",
                    "old_record": None,
                    "new_record": {"id": 1, "name": "Alice"}
                }
            ]
        },
        "conflicts": {},
        "success": True,
        "current_change_ids": {"users": 0, "tasks": 0},
        "version_vectors": {
            "users": {"server": 1},
            "tasks": {"server": 0}
        }
    }
    
    response = SyncResponse.from_dict(response_dict)
    
    assert len(response.server_changes["users"]) == 1
    assert response.conflicts == {}
    assert response.success is True
    assert response.current_change_ids == {"users": 0, "tasks": 0}
    assert response.version_vectors == {
        "users": {"server": 1},
        "tasks": {"server": 0}
    }


def test_sync_response_to_dict():
    """Test converting a sync response to a dictionary."""
    # Create a sync response
    response = SyncResponse(
        server_changes={},
        conflicts={},
        success=True,
        current_change_ids={"users": 0, "tasks": 0},
        version_vectors={
            "users": {"server": 1},
            "tasks": {"server": 0}
        }
    )
    
    # Convert to dictionary
    response_dict = response.to_dict()
    
    # Check the dictionary
    assert response_dict["server_changes"] == {}
    assert response_dict["conflicts"] == {}
    assert response_dict["success"] is True
    assert response_dict["current_change_ids"] == {"users": 0, "tasks": 0}
    assert response_dict["version_vectors"] == {
        "users": {"server": 1},
        "tasks": {"server": 0}
    }


def test_sync_engine_creation(sample_database, change_tracker, network_simulator):
    """Test creating a sync engine."""
    engine = SyncEngine(
        database=sample_database,
        change_tracker=change_tracker,
        network=network_simulator
    )
    
    assert engine.database == sample_database
    assert engine.change_tracker == change_tracker
    assert engine.network == network_simulator
    assert engine.client_sync_states == {}


def test_sync_engine_get_or_create_client_state():
    """Test getting or creating a client state."""
    engine = SyncEngine(None, None)
    
    # Initially, no client state exists
    assert engine.client_sync_states == {}
    
    # Get or create a client state
    state = engine.get_or_create_client_state("client1")
    
    # Check that the state was created
    assert state.client_id == "client1"
    assert "client1" in engine.client_sync_states
    
    # Getting the state again should return the same object
    state2 = engine.get_or_create_client_state("client1")
    assert state2 is state


def test_sync_engine_process_sync_request(sync_engine):
    """Test processing a sync request."""
    # Create a sync request
    request = SyncRequest(
        client_id="client1",
        table_change_ids={"users": -1, "tasks": -1, "notes": -1},
        client_changes={},
        version_vectors={
            "users": {"client1": 0},
            "tasks": {"client1": 0},
            "notes": {"client1": 0}
        }
    )
    
    # Convert to JSON
    request_json = json.dumps(request.to_dict())
    
    # Process the request
    response_json = sync_engine.process_sync_request(request_json)
    
    # Parse the response
    response_dict = json.loads(response_json)
    response = SyncResponse.from_dict(response_dict)
    
    # Check the response
    assert response.success is True
    assert "users" in response.server_changes
    assert "tasks" in response.server_changes
    assert "notes" in response.server_changes
    
    # Check that the changes include the initial sample data
    assert len(response.server_changes["users"]) > 0
    assert len(response.server_changes["tasks"]) > 0
    assert len(response.server_changes["notes"]) > 0


def test_sync_engine_create_sync_request(sync_engine, sample_database, change_tracker):
    """Test creating a sync request."""
    # Create a sync request
    request_json = sync_engine.create_sync_request(
        client_id="client1",
        tables=["users", "tasks", "notes"],
        client_database=sample_database,
        client_change_tracker=change_tracker
    )
    
    # Parse the request
    request_dict = json.loads(request_json)
    request = SyncRequest.from_dict(request_dict)
    
    # Check the request
    assert request.client_id == "client1"
    assert set(request.table_change_ids.keys()) == {"users", "tasks", "notes"}
    assert "users" in request.version_vectors
    assert "tasks" in request.version_vectors
    assert "notes" in request.version_vectors


def test_sync_engine_process_sync_response(sync_engine, sample_database, change_tracker):
    """Test processing a sync response."""
    # Create a sync response
    response = SyncResponse(
        server_changes={
            "users": [
                {
                    "id": 0,
                    "table_name": "users",
                    "primary_key": (3,),
                    "operation": "insert",
                    "timestamp": time.time(),
                    "client_id": "server",
                    "old_data": None,
                    "new_data": {"id": 3, "username": "charlie", "email": "charlie@example.com"}
                }
            ]
        },
        conflicts={},
        success=True,
        current_change_ids={"users": 0, "tasks": 0, "notes": 0},
        version_vectors={
            "users": {"server": 1},
            "tasks": {"server": 0},
            "notes": {"server": 0}
        }
    )
    
    # Convert to JSON
    response_json = json.dumps(response.to_dict())
    
    # Process the response
    success, error = sync_engine.process_sync_response(
        client_id="client1",
        response_json=response_json,
        client_database=sample_database,
        client_change_tracker=change_tracker
    )
    
    # Check the result
    assert success is True
    assert error is None
    
    # Check that the new user was added to the database
    user = sample_database.get("users", [3])
    assert user is not None
    assert user["username"] == "charlie"
    assert user["email"] == "charlie@example.com"


def test_sync_engine_with_changes(sync_engine, sample_database, change_tracker):
    """Test a full sync cycle with changes from client to server."""
    # Make a change on the client
    sample_database.insert("users", {
        "id": 3,
        "username": "charlie",
        "email": "charlie@example.com"
    }, client_id="client1")
    
    # Create a sync request
    request_json = sync_engine.create_sync_request(
        client_id="client1",
        tables=["users"],
        client_database=sample_database,
        client_change_tracker=change_tracker
    )
    
    # Process the request
    response_json = sync_engine.process_sync_request(request_json)
    
    # Process the response
    success, error = sync_engine.process_sync_response(
        client_id="client1",
        response_json=response_json,
        client_database=sample_database,
        client_change_tracker=change_tracker
    )
    
    # Check the result
    assert success is True
    assert error is None
    
    # Check that the server now has the new user
    user = sync_engine.database.get("users", [3])
    assert user is not None
    assert user["username"] == "charlie"
    assert user["email"] == "charlie@example.com"