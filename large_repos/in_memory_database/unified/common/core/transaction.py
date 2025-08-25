"""Transaction support for the unified library."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock, current_thread
from enum import Enum
import uuid
from contextlib import contextmanager


class TransactionState(Enum):
    """States of a transaction."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


@dataclass
class Operation:
    """Represents a single operation in a transaction."""
    type: str  # 'insert', 'update', 'delete', 'custom'
    target: str  # Target object/table
    key: Any
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary."""
        return {
            'type': self.type,
            'target': self.target,
            'key': self.key,
            'data': self.data,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class Transaction:
    """ACID transaction support."""
    
    def __init__(self, transaction_id: Optional[str] = None,
                 isolation_level: str = "read_committed"):
        """Initialize a transaction.
        
        Args:
            transaction_id: Optional transaction ID
            isolation_level: Isolation level for the transaction
        """
        self.id = transaction_id or str(uuid.uuid4())
        self.state = TransactionState.PENDING
        self.isolation_level = isolation_level
        self.operations: List[Operation] = []
        self.savepoints: Dict[str, int] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.thread_id = current_thread().ident
        self._rollback_handlers: List[Callable] = []
        self._commit_handlers: List[Callable] = []
    
    def begin(self) -> None:
        """Begin the transaction."""
        if self.state != TransactionState.PENDING:
            raise RuntimeError(f"Cannot begin transaction in state {self.state}")
        
        self.state = TransactionState.ACTIVE
        self.start_time = datetime.now()
    
    def add_operation(self, operation: Operation) -> None:
        """Add an operation to the transaction.
        
        Args:
            operation: The operation to add
        """
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot add operation to transaction in state {self.state}")
        
        self.operations.append(operation)
    
    def savepoint(self, name: str) -> None:
        """Create a savepoint in the transaction.
        
        Args:
            name: Name of the savepoint
        """
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot create savepoint in transaction state {self.state}")
        
        self.savepoints[name] = len(self.operations)
    
    def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a specific savepoint.
        
        Args:
            name: Name of the savepoint to rollback to
        """
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot rollback to savepoint in transaction state {self.state}")
        
        if name not in self.savepoints:
            raise ValueError(f"Savepoint {name} does not exist")
        
        # Remove operations after the savepoint
        index = self.savepoints[name]
        self.operations = self.operations[:index]
        
        # Remove savepoints created after this one
        self.savepoints = {k: v for k, v in self.savepoints.items() if v <= index}
    
    def commit(self) -> None:
        """Commit the transaction."""
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot commit transaction in state {self.state}")
        
        # Execute commit handlers
        for handler in self._commit_handlers:
            handler(self)
        
        self.state = TransactionState.COMMITTED
        self.end_time = datetime.now()
    
    def rollback(self) -> None:
        """Rollback the transaction."""
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot rollback transaction in state {self.state}")
        
        # Execute rollback handlers
        for handler in self._rollback_handlers:
            handler(self)
        
        self.operations.clear()
        self.savepoints.clear()
        self.state = TransactionState.ABORTED
        self.end_time = datetime.now()
    
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self.state == TransactionState.ACTIVE
    
    def add_rollback_handler(self, handler: Callable) -> None:
        """Add a rollback handler."""
        self._rollback_handlers.append(handler)
    
    def add_commit_handler(self, handler: Callable) -> None:
        """Add a commit handler."""
        self._commit_handlers.append(handler)
    
    def get_duration(self) -> Optional[float]:
        """Get transaction duration in seconds."""
        if self.start_time is None:
            return None
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def __enter__(self) -> 'Transaction':
        """Context manager entry."""
        self.begin()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


class TransactionManager:
    """Manages transaction lifecycle and coordination."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self._transactions: Dict[str, Transaction] = {}
        self._thread_transactions: Dict[int, Transaction] = {}
        self._lock = RLock()
        self._default_isolation = "read_committed"
        self._transaction_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000
    
    def begin_transaction(self, transaction_id: Optional[str] = None,
                         isolation_level: Optional[str] = None) -> Transaction:
        """Begin a new transaction.
        
        Args:
            transaction_id: Optional transaction ID
            isolation_level: Optional isolation level
        
        Returns:
            The created Transaction
        """
        with self._lock:
            # Check if thread already has a transaction
            thread_id = current_thread().ident
            if thread_id in self._thread_transactions:
                existing = self._thread_transactions[thread_id]
                if existing.is_active():
                    raise RuntimeError("Thread already has an active transaction")
            
            # Create new transaction
            txn = Transaction(
                transaction_id=transaction_id,
                isolation_level=isolation_level or self._default_isolation
            )
            txn.begin()
            
            # Register transaction
            self._transactions[txn.id] = txn
            self._thread_transactions[thread_id] = txn
            
            # Log transaction start
            self._log_transaction_event(txn, "begin")
            
            return txn
    
    def get_current(self) -> Optional[Transaction]:
        """Get the current transaction for this thread.
        
        Returns:
            The current Transaction or None
        """
        with self._lock:
            thread_id = current_thread().ident
            txn = self._thread_transactions.get(thread_id)
            
            if txn and txn.is_active():
                return txn
            
            return None
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID.
        
        Args:
            transaction_id: ID of the transaction
        
        Returns:
            The Transaction or None
        """
        with self._lock:
            return self._transactions.get(transaction_id)
    
    def commit_transaction(self, transaction_id: str) -> None:
        """Commit a specific transaction.
        
        Args:
            transaction_id: ID of the transaction to commit
        """
        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            txn.commit()
            self._log_transaction_event(txn, "commit")
            self._cleanup_transaction(txn)
    
    def rollback_transaction(self, transaction_id: str) -> None:
        """Rollback a specific transaction.
        
        Args:
            transaction_id: ID of the transaction to rollback
        """
        with self._lock:
            txn = self._transactions.get(transaction_id)
            if not txn:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            txn.rollback()
            self._log_transaction_event(txn, "rollback")
            self._cleanup_transaction(txn)
    
    def cleanup_abandoned(self, timeout_seconds: float = 300) -> int:
        """Clean up abandoned transactions.
        
        Args:
            timeout_seconds: Transactions older than this are considered abandoned
        
        Returns:
            Number of transactions cleaned up
        """
        with self._lock:
            now = datetime.now()
            cleaned = 0
            
            for txn_id in list(self._transactions.keys()):
                txn = self._transactions[txn_id]
                
                if txn.is_active():
                    duration = txn.get_duration()
                    if duration and duration > timeout_seconds:
                        # Rollback abandoned transaction
                        txn.rollback()
                        self._log_transaction_event(txn, "abandoned_rollback")
                        self._cleanup_transaction(txn)
                        cleaned += 1
            
            return cleaned
    
    @contextmanager
    def transaction(self, transaction_id: Optional[str] = None,
                   isolation_level: Optional[str] = None):
        """Context manager for transactions.
        
        Args:
            transaction_id: Optional transaction ID
            isolation_level: Optional isolation level
        
        Yields:
            The Transaction object
        """
        txn = self.begin_transaction(transaction_id, isolation_level)
        try:
            yield txn
            self.commit_transaction(txn.id)
        except Exception:
            self.rollback_transaction(txn.id)
            raise
    
    def get_active_transactions(self) -> List[Transaction]:
        """Get all active transactions.
        
        Returns:
            List of active Transaction objects
        """
        with self._lock:
            return [txn for txn in self._transactions.values() if txn.is_active()]
    
    def get_transaction_log(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get transaction log entries.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of log entries
        """
        with self._lock:
            if limit:
                return self._transaction_log[-limit:]
            return self._transaction_log.copy()
    
    def _cleanup_transaction(self, txn: Transaction) -> None:
        """Clean up a completed transaction."""
        # Remove from thread mapping
        if txn.thread_id in self._thread_transactions:
            if self._thread_transactions[txn.thread_id] == txn:
                del self._thread_transactions[txn.thread_id]
        
        # Optionally remove from transaction list (keep for history)
        # del self._transactions[txn.id]
    
    def _log_transaction_event(self, txn: Transaction, event: str) -> None:
        """Log a transaction event."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': txn.id,
            'event': event,
            'state': txn.state.value,
            'thread_id': txn.thread_id,
            'operations_count': len(txn.operations),
            'duration': txn.get_duration()
        }
        
        self._transaction_log.append(log_entry)
        
        # Trim log if too large
        if len(self._transaction_log) > self._max_log_size:
            self._transaction_log = self._transaction_log[-self._max_log_size:]