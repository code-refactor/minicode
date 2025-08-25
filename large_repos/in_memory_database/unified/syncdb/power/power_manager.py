"""
Battery-aware operation modes for efficient resource usage.
"""
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Union
from enum import Enum
import time
import threading
import queue
from dataclasses import dataclass, field

from ..compression.type_compressor import CompressionLevel


class PowerMode(Enum):
    """Power modes for different battery conditions."""
    PLUGGED_IN = 1  # Device is connected to power
    BATTERY_NORMAL = 2  # Battery level is good
    BATTERY_LOW = 3  # Battery level is low
    BATTERY_CRITICAL = 4  # Battery level is critically low
    
    @classmethod
    def from_battery_level(cls, level: float, is_plugged_in: bool) -> 'PowerMode':
        """
        Determine the power mode based on battery level and plugged in status.
        
        Args:
            level: Battery level from 0.0 to 1.0
            is_plugged_in: Whether the device is plugged in
            
        Returns:
            Appropriate power mode
        """
        if is_plugged_in:
            return cls.PLUGGED_IN
        
        if level <= 0.1:
            return cls.BATTERY_CRITICAL
        elif level <= 0.2:
            return cls.BATTERY_LOW
        else:
            return cls.BATTERY_NORMAL


@dataclass
class PowerProfile:
    """Profile for resource usage based on power mode."""
    sync_interval_seconds: int  # How often to sync with server
    batch_size: int  # Maximum number of operations in a batch
    compression_level: CompressionLevel  # Compression level for data transfer
    max_concurrent_operations: int  # Maximum number of concurrent operations
    defer_non_critical: bool  # Whether to defer non-critical operations
    
    @classmethod
    def get_default_profile(cls, mode: PowerMode) -> 'PowerProfile':
        """
        Get the default profile for a power mode.
        
        Args:
            mode: Power mode
            
        Returns:
            Default power profile for the mode
        """
        if mode == PowerMode.PLUGGED_IN:
            return cls(
                sync_interval_seconds=60,  # Sync every minute
                batch_size=100,
                compression_level=CompressionLevel.MEDIUM,
                max_concurrent_operations=4,
                defer_non_critical=False
            )
        
        elif mode == PowerMode.BATTERY_NORMAL:
            return cls(
                sync_interval_seconds=300,  # Sync every 5 minutes
                batch_size=50,
                compression_level=CompressionLevel.HIGH,
                max_concurrent_operations=2,
                defer_non_critical=False
            )
        
        elif mode == PowerMode.BATTERY_LOW:
            return cls(
                sync_interval_seconds=900,  # Sync every 15 minutes
                batch_size=25,
                compression_level=CompressionLevel.HIGH,
                max_concurrent_operations=1,
                defer_non_critical=True
            )
        
        else:  # BATTERY_CRITICAL
            return cls(
                sync_interval_seconds=1800,  # Sync every 30 minutes
                batch_size=10,
                compression_level=CompressionLevel.HIGH,
                max_concurrent_operations=1,
                defer_non_critical=True
            )


class OperationPriority(Enum):
    """Priority levels for database operations."""
    CRITICAL = 1  # Must be executed immediately (e.g. user-initiated actions)
    HIGH = 2  # Important but can be briefly delayed
    MEDIUM = 3  # Normal operations
    LOW = 4  # Background tasks
    MAINTENANCE = 5  # Maintenance tasks (e.g. cleanup)


@dataclass
class DeferredOperation:
    """An operation that has been deferred for later execution."""
    operation_type: str  # Type of operation (e.g. "sync", "query", "insert")
    priority: OperationPriority
    creation_time: float
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None

    def __lt__(self, other: 'DeferredOperation') -> bool:
        """
        Compare operations for sorting in the priority queue.

        Args:
            other: Another operation to compare with

        Returns:
            True if this operation has higher priority (lower value)
        """
        # Needed for priority queue ordering
        # Use creation time as tie-breaker
        return (self.priority.value, self.creation_time) < (other.priority.value, other.creation_time)

    def execute(self, target_obj: Any) -> Any:
        """
        Execute the operation on the target object.

        Args:
            target_obj: Object to execute the operation on

        Returns:
            Result of the operation
        """
        method = getattr(target_obj, self.operation_type, None)
        if not method:
            raise ValueError(f"Unknown operation type: {self.operation_type}")
        
        result = method(*self.args, **self.kwargs)
        
        if self.callback:
            self.callback(result)
        
        return result


class PowerManager:
    """
    Manages power profiles and deferred operations based on device power status.
    """
    def __init__(self, initial_mode: PowerMode = PowerMode.BATTERY_NORMAL):
        self.current_mode = initial_mode
        self.current_profile = PowerProfile.get_default_profile(initial_mode)
        self.custom_profiles: Dict[PowerMode, PowerProfile] = {}
        self.deferred_operations: Dict[OperationPriority, List[DeferredOperation]] = {
            priority: [] for priority in OperationPriority
        }
        self.operation_queue: "queue.PriorityQueue[Tuple[int, DeferredOperation]]" = queue.PriorityQueue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self._last_battery_check = 0
        self._battery_level = 1.0
        self._is_plugged_in = False
    
    def set_power_mode(self, mode: PowerMode) -> None:
        """Set the current power mode and update the profile."""
        self.current_mode = mode
        self.current_profile = self.custom_profiles.get(
            mode, PowerProfile.get_default_profile(mode)
        )
    
    def set_custom_profile(self, mode: PowerMode, profile: PowerProfile) -> None:
        """Set a custom profile for a power mode."""
        self.custom_profiles[mode] = profile
        if self.current_mode == mode:
            self.current_profile = profile
    
    def update_battery_status(self, level: float, is_plugged_in: bool) -> None:
        """
        Update the battery status and adjust power mode accordingly.
        
        Args:
            level: Battery level from 0.0 to 1.0
            is_plugged_in: Whether the device is plugged in
        """
        self._battery_level = level
        self._is_plugged_in = is_plugged_in
        self._last_battery_check = time.time()
        
        # Determine the appropriate power mode
        mode = PowerMode.from_battery_level(level, is_plugged_in)
        
        # Update the power mode if it changed
        if mode != self.current_mode:
            self.set_power_mode(mode)
    
    def simulate_battery_drain(self, drain_rate: float = 0.0001) -> None:
        """
        Simulate battery drain for testing.
        
        Args:
            drain_rate: How much to drain per second
        """
        if self._is_plugged_in:
            return
        
        current_time = time.time()
        elapsed = current_time - self._last_battery_check
        
        # Adjust battery level
        new_level = max(0.0, self._battery_level - (drain_rate * elapsed))
        self.update_battery_status(new_level, self._is_plugged_in)
    
    def should_defer_operation(self, priority: OperationPriority) -> bool:
        """
        Check if an operation should be deferred based on priority and power mode.
        
        Args:
            priority: Priority of the operation
            
        Returns:
            True if the operation should be deferred
        """
        if not self.current_profile.defer_non_critical:
            return False
        
        # Always execute critical operations
        if priority == OperationPriority.CRITICAL:
            return False
        
        # In low or critical battery mode, defer all non-critical operations
        if self.current_mode in (PowerMode.BATTERY_LOW, PowerMode.BATTERY_CRITICAL):
            return True
        
        # In normal battery mode, defer only low priority operations
        if self.current_mode == PowerMode.BATTERY_NORMAL:
            return priority in (OperationPriority.LOW, OperationPriority.MAINTENANCE)
        
        return False
    
    def enqueue_operation(self, 
                         operation_type: str, 
                         priority: OperationPriority,
                         *args, 
                         **kwargs) -> None:
        """
        Enqueue an operation for execution.
        
        Args:
            operation_type: Type of operation
            priority: Priority of the operation
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation
        """
        callback = kwargs.pop('callback', None)
        
        operation = DeferredOperation(
            operation_type=operation_type,
            priority=priority,
            creation_time=time.time(),
            args=args,
            kwargs=kwargs,
            callback=callback
        )
        
        # Add to the deferred operations list
        self.deferred_operations[priority].append(operation)
        
        # Add to the priority queue
        self.operation_queue.put(operation)
    
    def start_worker(self, target_obj: Any) -> None:
        """
        Start the worker thread for processing deferred operations.
        
        Args:
            target_obj: Object to execute operations on
        """
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(target_obj,),
            daemon=True
        )
        self.worker_thread.start()
    
    def stop_worker(self) -> None:
        """Stop the worker thread."""
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
    
    def _worker_loop(self, target_obj: Any) -> None:
        """
        Worker loop for processing deferred operations.
        
        Args:
            target_obj: Object to execute operations on
        """
        while not self.stop_event.is_set():
            try:
                # Try to get an operation from the queue with a timeout
                operation = self.operation_queue.get(timeout=1.0)

                # Check if we should execute this operation now
                if self._should_execute_now(operation):
                    try:
                        operation.execute(target_obj)
                    except Exception as e:
                        # In a real implementation, we would log this error
                        print(f"Error executing deferred operation: {e}")
                else:
                    # Put it back in the queue for later
                    self.operation_queue.put(operation)
                
                # Mark task as done
                self.operation_queue.task_done()
                
            except queue.Empty:
                # No operations in the queue, just continue
                pass
    
    def _should_execute_now(self, operation: DeferredOperation) -> bool:
        """
        Check if an operation should be executed now.
        
        Args:
            operation: Operation to check
            
        Returns:
            True if the operation should be executed now
        """
        # Critical operations always execute immediately
        if operation.priority == OperationPriority.CRITICAL:
            return True
        
        # Check if we're under the concurrent operation limit
        in_progress = sum(1 for p, o in self.operation_queue.queue 
                         if o.operation_type == operation.operation_type)
        if in_progress >= self.current_profile.max_concurrent_operations:
            return False
        
        # Check if we're deferring operations of this priority
        if self.should_defer_operation(operation.priority):
            # Check if the operation has been waiting too long
            max_wait_time = {
                OperationPriority.HIGH: 60,  # 1 minute
                OperationPriority.MEDIUM: 300,  # 5 minutes
                OperationPriority.LOW: 1800,  # 30 minutes
                OperationPriority.MAINTENANCE: 3600  # 1 hour
            }.get(operation.priority, 0)
            
            wait_time = time.time() - operation.creation_time
            if wait_time < max_wait_time:
                return False
        
        return True
    
    def get_batch_size(self) -> int:
        """Get the current batch size based on power profile."""
        return self.current_profile.batch_size
    
    def get_sync_interval(self) -> int:
        """Get the current sync interval based on power profile."""
        return self.current_profile.sync_interval_seconds
    
    def get_compression_level(self) -> CompressionLevel:
        """Get the current compression level based on power profile."""
        return self.current_profile.compression_level
    
    def get_max_concurrent_operations(self) -> int:
        """Get the maximum number of concurrent operations."""
        return self.current_profile.max_concurrent_operations


class BatteryAwareClient:
    """
    Wrapper for a client that adjusts behavior based on battery status.
    """
    def __init__(self, 
                client_obj: Any, 
                power_manager: PowerManager,
                default_priority: OperationPriority = OperationPriority.MEDIUM):
        self.client = client_obj
        self.power_manager = power_manager
        self.default_priority = default_priority
        self._sync_timer = None
        self._last_sync_time = 0
    
    def __getattr__(self, name: str) -> Callable:
        """
        Proxy method calls to the client object with battery awareness.
        
        Args:
            name: Method name
            
        Returns:
            Wrapped method
        """
        # Get the method from the client
        method = getattr(self.client, name, None)
        if not method or not callable(method):
            raise AttributeError(f"Client has no method '{name}'")
        
        # Wrap the method to apply battery awareness
        def wrapped_method(*args, **kwargs):
            priority = kwargs.pop('priority', self.default_priority)
            
            # Check if this operation should be deferred
            if self.power_manager.should_defer_operation(priority):
                # Enqueue for later execution
                self.power_manager.enqueue_operation(name, priority, *args, **kwargs)
                return None  # Return None for deferred operations
            
            # Execute immediately
            return method(*args, **kwargs)
        
        return wrapped_method
    
    def start_sync_timer(self) -> None:
        """Start the periodic sync timer."""
        if self._sync_timer:
            self._sync_timer.cancel()
        
        interval = self.power_manager.get_sync_interval()
        self._sync_timer = threading.Timer(interval, self._sync_callback)
        self._sync_timer.daemon = True
        self._sync_timer.start()
    
    def stop_sync_timer(self) -> None:
        """Stop the periodic sync timer."""
        if self._sync_timer:
            self._sync_timer.cancel()
            self._sync_timer = None
    
    def _sync_callback(self) -> None:
        """Callback for periodic sync."""
        # Perform a sync
        if hasattr(self.client, 'sync'):
            # Use MEDIUM priority for automatic syncs
            self.client.sync(priority=OperationPriority.MEDIUM)
        
        # Restart the timer
        self.start_sync_timer()
    
    def force_sync(self) -> Any:
        """Force an immediate sync with HIGH priority."""
        if hasattr(self.client, 'sync'):
            return self.client.sync(priority=OperationPriority.HIGH)
        return None