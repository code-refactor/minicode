"""
Tests for the battery-aware operation modes.
"""
import pytest
import time
import threading
from typing import Dict, List, Any, Optional

from syncdb.power.power_manager import (
    PowerMode, PowerProfile, OperationPriority, DeferredOperation,
    PowerManager, BatteryAwareClient
)
from syncdb.compression.type_compressor import CompressionLevel


class MockObject:
    """A mock object for testing the power manager."""
    def __init__(self):
        self.operations = []
        self.last_operation = None
    
    def sync(self, *args, **kwargs):
        """Mock sync operation."""
        self.operations.append(("sync", args, kwargs))
        self.last_operation = ("sync", args, kwargs)
        return "sync_result"
    
    def query(self, *args, **kwargs):
        """Mock query operation."""
        self.operations.append(("query", args, kwargs))
        self.last_operation = ("query", args, kwargs)
        return "query_result"
    
    def insert(self, *args, **kwargs):
        """Mock insert operation."""
        self.operations.append(("insert", args, kwargs))
        self.last_operation = ("insert", args, kwargs)
        return "insert_result"


def test_power_mode_from_battery_level():
    """Test determining power mode from battery level."""
    # Plugged in
    assert PowerMode.from_battery_level(1.0, True) == PowerMode.PLUGGED_IN
    assert PowerMode.from_battery_level(0.5, True) == PowerMode.PLUGGED_IN
    assert PowerMode.from_battery_level(0.1, True) == PowerMode.PLUGGED_IN
    
    # Battery normal
    assert PowerMode.from_battery_level(1.0, False) == PowerMode.BATTERY_NORMAL
    assert PowerMode.from_battery_level(0.5, False) == PowerMode.BATTERY_NORMAL
    assert PowerMode.from_battery_level(0.3, False) == PowerMode.BATTERY_NORMAL
    
    # Battery low
    assert PowerMode.from_battery_level(0.2, False) == PowerMode.BATTERY_LOW
    assert PowerMode.from_battery_level(0.15, False) == PowerMode.BATTERY_LOW
    
    # Battery critical
    assert PowerMode.from_battery_level(0.1, False) == PowerMode.BATTERY_CRITICAL
    assert PowerMode.from_battery_level(0.05, False) == PowerMode.BATTERY_CRITICAL
    assert PowerMode.from_battery_level(0.0, False) == PowerMode.BATTERY_CRITICAL


def test_power_profile_creation():
    """Test creating a power profile."""
    profile = PowerProfile(
        sync_interval_seconds=60,
        batch_size=100,
        compression_level=CompressionLevel.MEDIUM,
        max_concurrent_operations=4,
        defer_non_critical=False
    )
    
    assert profile.sync_interval_seconds == 60
    assert profile.batch_size == 100
    assert profile.compression_level == CompressionLevel.MEDIUM
    assert profile.max_concurrent_operations == 4
    assert profile.defer_non_critical is False


def test_power_profile_get_default_profile():
    """Test getting default power profiles for different modes."""
    # Plugged in
    plugged_in = PowerProfile.get_default_profile(PowerMode.PLUGGED_IN)
    assert plugged_in.sync_interval_seconds < 300  # More frequent sync
    assert plugged_in.batch_size > 50  # Larger batches
    assert plugged_in.defer_non_critical is False  # Don't defer operations
    
    # Battery normal
    normal = PowerProfile.get_default_profile(PowerMode.BATTERY_NORMAL)
    assert normal.sync_interval_seconds > plugged_in.sync_interval_seconds  # Less frequent sync
    assert normal.batch_size <= plugged_in.batch_size  # Smaller batches
    
    # Battery low
    low = PowerProfile.get_default_profile(PowerMode.BATTERY_LOW)
    assert low.sync_interval_seconds > normal.sync_interval_seconds  # Even less frequent sync
    assert low.batch_size < normal.batch_size  # Even smaller batches
    assert low.defer_non_critical is True  # Defer non-critical operations
    
    # Battery critical
    critical = PowerProfile.get_default_profile(PowerMode.BATTERY_CRITICAL)
    assert critical.sync_interval_seconds > low.sync_interval_seconds  # Least frequent sync
    assert critical.batch_size < low.batch_size  # Smallest batches
    assert critical.defer_non_critical is True  # Defer non-critical operations


def test_deferred_operation_creation():
    """Test creating a deferred operation."""
    def callback(result):
        pass
    
    operation = DeferredOperation(
        operation_type="sync",
        priority=OperationPriority.MEDIUM,
        creation_time=time.time(),
        args=(1, 2),
        kwargs={"param": "value"},
        callback=callback
    )
    
    assert operation.operation_type == "sync"
    assert operation.priority == OperationPriority.MEDIUM
    assert operation.creation_time > 0
    assert operation.args == (1, 2)
    assert operation.kwargs == {"param": "value"}
    assert operation.callback == callback


def test_deferred_operation_execute():
    """Test executing a deferred operation."""
    # Create a mock object
    mock = MockObject()
    
    # Create a callback function
    callback_called = False
    callback_result = None
    
    def callback(result):
        nonlocal callback_called, callback_result
        callback_called = True
        callback_result = result
    
    # Create a deferred operation
    operation = DeferredOperation(
        operation_type="sync",
        priority=OperationPriority.MEDIUM,
        creation_time=time.time(),
        args=(1, 2),
        kwargs={"param": "value"},
        callback=callback
    )
    
    # Execute the operation
    result = operation.execute(mock)
    
    # Check that the operation was executed
    assert result == "sync_result"
    assert mock.last_operation == ("sync", (1, 2), {"param": "value"})
    
    # Check that the callback was called
    assert callback_called is True
    assert callback_result == "sync_result"


def test_power_manager_creation():
    """Test creating a power manager."""
    manager = PowerManager()
    
    assert manager.current_mode == PowerMode.BATTERY_NORMAL
    assert manager.current_profile is not None
    assert manager.custom_profiles == {}
    assert manager.deferred_operations is not None
    assert manager.operation_queue is not None
    assert manager.stop_event is not None
    assert manager.worker_thread is None


def test_power_manager_set_power_mode():
    """Test setting the power mode."""
    manager = PowerManager()
    
    # Initially in battery normal mode
    assert manager.current_mode == PowerMode.BATTERY_NORMAL
    
    # Set to plugged in mode
    manager.set_power_mode(PowerMode.PLUGGED_IN)
    assert manager.current_mode == PowerMode.PLUGGED_IN
    
    # Profile should change
    assert manager.current_profile.sync_interval_seconds < 300  # More frequent sync for plugged in


def test_power_manager_set_custom_profile():
    """Test setting a custom power profile."""
    manager = PowerManager()
    
    # Create a custom profile
    custom_profile = PowerProfile(
        sync_interval_seconds=42,
        batch_size=42,
        compression_level=CompressionLevel.HIGH,
        max_concurrent_operations=2,
        defer_non_critical=True
    )
    
    # Set the custom profile
    manager.set_custom_profile(PowerMode.BATTERY_NORMAL, custom_profile)
    
    # Check that the custom profile was set
    assert manager.custom_profiles[PowerMode.BATTERY_NORMAL] == custom_profile
    
    # Since we're in battery normal mode, the current profile should be updated
    assert manager.current_profile == custom_profile
    assert manager.current_profile.sync_interval_seconds == 42


def test_power_manager_update_battery_status():
    """Test updating the battery status."""
    manager = PowerManager()
    
    # Initially in battery normal mode
    assert manager.current_mode == PowerMode.BATTERY_NORMAL
    
    # Update to plugged in
    manager.update_battery_status(0.8, True)
    assert manager.current_mode == PowerMode.PLUGGED_IN
    
    # Update to low battery
    manager.update_battery_status(0.15, False)
    assert manager.current_mode == PowerMode.BATTERY_LOW
    
    # Update to critical battery
    manager.update_battery_status(0.05, False)
    assert manager.current_mode == PowerMode.BATTERY_CRITICAL


def test_power_manager_should_defer_operation():
    """Test checking if operations should be deferred."""
    manager = PowerManager(PowerMode.BATTERY_NORMAL)
    
    # In normal mode with default profile, non-critical operations are not deferred
    assert manager.should_defer_operation(OperationPriority.CRITICAL) is False
    assert manager.should_defer_operation(OperationPriority.HIGH) is False
    assert manager.should_defer_operation(OperationPriority.MEDIUM) is False
    
    # Set to low battery mode
    manager.set_power_mode(PowerMode.BATTERY_LOW)
    
    # In low battery mode, non-critical operations are deferred
    assert manager.should_defer_operation(OperationPriority.CRITICAL) is False
    assert manager.should_defer_operation(OperationPriority.HIGH) is True
    assert manager.should_defer_operation(OperationPriority.MEDIUM) is True
    assert manager.should_defer_operation(OperationPriority.LOW) is True


def test_power_manager_enqueue_operation():
    """Test enqueueing an operation."""
    manager = PowerManager()
    
    # Enqueue an operation
    manager.enqueue_operation(
        operation_type="sync",
        priority=OperationPriority.MEDIUM,
        param="value"
    )
    
    # Check that the operation was added to the deferred operations
    assert len(manager.deferred_operations[OperationPriority.MEDIUM]) == 1
    operation = manager.deferred_operations[OperationPriority.MEDIUM][0]
    assert operation.operation_type == "sync"
    assert operation.kwargs == {"param": "value"}
    
    # Check that the operation was added to the queue
    assert manager.operation_queue.qsize() == 1


def test_power_manager_worker():
    """Test the worker thread."""
    manager = PowerManager()
    
    # Create a mock object
    mock = MockObject()
    
    # Enqueue a critical operation (should execute immediately)
    manager.enqueue_operation(
        operation_type="sync",
        priority=OperationPriority.CRITICAL
    )
    
    # Start the worker
    manager.start_worker(mock)
    
    # Wait a short time for the worker to process the operation
    time.sleep(0.1)
    
    # Check that the operation was executed
    assert len(mock.operations) == 1
    assert mock.operations[0][0] == "sync"
    
    # Stop the worker
    manager.stop_worker()


def test_power_manager_should_execute_now():
    """Test checking if an operation should be executed now."""
    manager = PowerManager()
    
    # Create operations with different priorities
    critical_op = DeferredOperation(
        operation_type="sync",
        priority=OperationPriority.CRITICAL,
        creation_time=time.time(),
        args=(),
        kwargs={}
    )
    
    high_op = DeferredOperation(
        operation_type="sync",
        priority=OperationPriority.HIGH,
        creation_time=time.time(),
        args=(),
        kwargs={}
    )
    
    # Critical operations should always execute immediately
    assert manager._should_execute_now(critical_op) is True
    
    # In normal mode, high priority operations should execute
    assert manager._should_execute_now(high_op) is True
    
    # In low battery mode, non-critical operations are deferred
    manager.set_power_mode(PowerMode.BATTERY_LOW)
    assert manager._should_execute_now(critical_op) is True
    assert manager._should_execute_now(high_op) is False
    
    # But if they've been waiting too long, they should execute
    old_high_op = DeferredOperation(
        operation_type="sync",
        priority=OperationPriority.HIGH,
        creation_time=time.time() - 120,  # 2 minutes ago (longer than high priority max wait)
        args=(),
        kwargs={}
    )
    assert manager._should_execute_now(old_high_op) is True


def test_battery_aware_client_creation():
    """Test creating a battery-aware client."""
    # Create a mock object
    mock = MockObject()
    
    # Create a power manager
    manager = PowerManager()
    
    # Create a battery-aware client
    client = BatteryAwareClient(mock, manager)
    
    assert client.client == mock
    assert client.power_manager == manager
    assert client.default_priority == OperationPriority.MEDIUM
    assert client._sync_timer is None
    assert client._last_sync_time == 0


def test_battery_aware_client_method_proxy():
    """Test that method calls are proxied to the client."""
    # Create a mock object
    mock = MockObject()
    
    # Create a power manager
    manager = PowerManager()
    
    # Create a battery-aware client
    client = BatteryAwareClient(mock, manager)
    
    # Call a method
    result = client.sync(1, 2, param="value")
    
    # Check that the method was called on the mock
    assert mock.last_operation == ("sync", (1, 2), {"param": "value"})
    assert result == "sync_result"


def test_battery_aware_client_deferred_operation():
    """Test that operations are deferred when appropriate."""
    # Create a mock object
    mock = MockObject()
    
    # Create a power manager in low battery mode
    manager = PowerManager(PowerMode.BATTERY_LOW)
    
    # Create a battery-aware client
    client = BatteryAwareClient(mock, manager)
    
    # Call a method with medium priority (should be deferred)
    result = client.sync(1, 2, param="value", priority=OperationPriority.MEDIUM)
    
    # The operation should be deferred, not executed immediately
    assert result is None
    assert len(mock.operations) == 0
    
    # Call a method with critical priority (should execute immediately)
    result = client.sync(3, 4, param="critical", priority=OperationPriority.CRITICAL)
    
    # The operation should be executed immediately
    assert result == "sync_result"
    assert len(mock.operations) == 1
    assert mock.last_operation == ("sync", (3, 4), {"param": "critical"})


def test_battery_aware_client_sync_timer():
    """Test the sync timer."""
    # Create a mock object
    mock = MockObject()
    
    # Add a sync method that records calls
    sync_calls = []
    
    def sync(*args, **kwargs):
        sync_calls.append((args, kwargs))
        return "sync_result"
    
    mock.sync = sync
    
    # Create a power manager with a short sync interval
    manager = PowerManager()
    profile = PowerProfile.get_default_profile(PowerMode.PLUGGED_IN)
    profile.sync_interval_seconds = 0.1  # 100ms for testing
    manager.set_custom_profile(PowerMode.PLUGGED_IN, profile)
    manager.set_power_mode(PowerMode.PLUGGED_IN)
    
    # Create a battery-aware client
    client = BatteryAwareClient(mock, manager)
    
    # Start the sync timer
    client.start_sync_timer()
    
    # Wait for the timer to fire a couple of times
    time.sleep(0.25)
    
    # Stop the timer
    client.stop_sync_timer()
    
    # Check that sync was called at least once
    assert len(sync_calls) >= 1
    
    # And it was called with medium priority
    for args, kwargs in sync_calls:
        assert kwargs.get("priority") == OperationPriority.MEDIUM


def test_battery_aware_client_force_sync():
    """Test forcing a sync."""
    # Create a mock object
    mock = MockObject()
    
    # Create a power manager
    manager = PowerManager()
    
    # Create a battery-aware client
    client = BatteryAwareClient(mock, manager)
    
    # Force a sync
    result = client.force_sync()
    
    # Check that sync was called with high priority
    assert result == "sync_result"
    assert mock.last_operation[0] == "sync"
    assert mock.last_operation[2]["priority"] == OperationPriority.HIGH