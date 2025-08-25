"""
Core in-memory database engine implementation.
"""
from typing import Dict, List, Any, Optional, Tuple, Callable, Set
import copy
import time
import uuid

# Import from common library
from common.core.storage import TableStore
from common.core.transaction import Transaction as CommonTransaction, TransactionManager, Operation
from common.core.schema import Schema as CommonSchema, SchemaManager
from common.core.version import VersionManager
from common.utils.threading import ThreadSafeCache, atomic_operation
from common.utils.validation import ValidationError

# Keep compatibility with existing schema imports
from .schema import DatabaseSchema, TableSchema


class Table(TableStore):
    """
    A database table that stores records in memory using common TableStore.
    """
    def __init__(self, schema: TableSchema):
        # Initialize parent TableStore
        super().__init__(name=schema.name, primary_key=schema.primary_keys)
        self.schema = schema
        self.last_modified: Dict[Tuple, float] = {}
        self.change_log: List[Dict[str, Any]] = []
        self.index_counter = 0  # Used for assigning sequential IDs to changes
        
        # Create indexes for primary key columns
        for pk_col in schema.primary_keys:
            self.create_index(pk_col)
    
    def _get_primary_key_tuple(self, record: Dict[str, Any]) -> Tuple:
        """Extract primary key values as a tuple for indexing."""
        return tuple(record[pk] for pk in self.schema.primary_keys)
    
    def _validate_record(self, record: Dict[str, Any]) -> None:
        """Validate a record against the schema and raise exception if invalid."""
        errors = self.schema.validate_record(record)
        if errors:
            raise ValueError(f"Invalid record: {', '.join(errors)}")
    
    def insert(self, record: Dict[str, Any], client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Insert a new record into the table.
        Returns the inserted record.
        """
        self._validate_record(record)
        pk_tuple = self._get_primary_key_tuple(record)

        # Check if record already exists
        if super().get(pk_tuple) is not None:
            raise ValueError(f"Record with primary key {pk_tuple} already exists")

        # Create a copy to avoid modifying the original
        stored_record = copy.deepcopy(record)

        # Apply default values for missing fields
        for column in self.schema.columns:
            if column.name not in stored_record and column.default is not None:
                stored_record[column.name] = column.default() if callable(column.default) else column.default

        # Use parent class insert
        super().insert(pk_tuple, stored_record)
        
        current_time = time.time()
        self.last_modified[pk_tuple] = current_time

        # Record the change in the log
        self._record_change("insert", pk_tuple, None, stored_record, client_id)

        return stored_record
    
    def update(self, record: Dict[str, Any], client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing record in the table.
        Returns the updated record.
        """
        self._validate_record(record)
        pk_tuple = self._get_primary_key_tuple(record)
        
        # Get the old record before updating
        old_record = super().get(pk_tuple)
        if old_record is None:
            raise ValueError(f"Record with primary key {pk_tuple} does not exist")
        
        old_record = copy.deepcopy(old_record)
        
        # Create a copy to avoid modifying the original
        stored_record = copy.deepcopy(record)
        
        # Use parent class update
        super().update(pk_tuple, stored_record)
        
        current_time = time.time()
        self.last_modified[pk_tuple] = current_time
        
        # Record the change in the log
        self._record_change("update", pk_tuple, old_record, stored_record, client_id)
        
        return stored_record
    
    def delete(self, primary_key_values: List[Any], client_id: Optional[str] = None) -> None:
        """Delete a record from the table by its primary key values."""
        pk_tuple = tuple(primary_key_values)
        
        # Get the record before deleting
        old_record = super().get(pk_tuple)
        if old_record is None:
            raise ValueError(f"Record with primary key {pk_tuple} does not exist")
        
        old_record = copy.deepcopy(old_record)
        
        # Use parent class delete
        super().delete(pk_tuple)
        
        # Clean up timestamps
        self.last_modified.pop(pk_tuple, None)
        
        # Record the change in the log
        self._record_change("delete", pk_tuple, old_record, None, client_id)
    
    def get(self, primary_key_values: List[Any]) -> Optional[Dict[str, Any]]:
        """Get a record by its primary key values."""
        pk_tuple = tuple(primary_key_values)
        record = super().get(pk_tuple)
        return copy.deepcopy(record) if record else None
    
    def query(self, 
              conditions: Optional[Dict[str, Any]] = None, 
              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query records that match the given conditions.
        
        Args:
            conditions: Dictionary of column name to value that records must match
            limit: Maximum number of records to return
            
        Returns:
            List of matching records
        """
        # Use parent class query method
        results = super().query(conditions, limit)
        return [copy.deepcopy(record) for record in results]
    
    # _matches_conditions method removed - handled by parent TableStore class
    
    def _record_change(self, 
                      operation: str, 
                      pk_tuple: Tuple, 
                      old_record: Optional[Dict[str, Any]], 
                      new_record: Optional[Dict[str, Any]],
                      client_id: Optional[str] = None) -> None:
        """Record a change in the change log."""
        self.index_counter += 1
        change = {
            "id": self.index_counter,
            "operation": operation,
            "primary_key": pk_tuple,
            "timestamp": time.time(),
            "old_record": old_record,
            "new_record": new_record,
            "client_id": client_id or "server"
        }
        self.change_log.append(change)
    
    def get_changes_since(self, index: int) -> List[Dict[str, Any]]:
        """Get all changes that occurred after the given index."""
        return [change for change in self.change_log if change["id"] > index]


class Transaction:
    """
    Manages a database transaction - wrapper around common Transaction.
    """
    def __init__(self, database: 'Database'):
        self.database = database
        self.tables_snapshot: Dict[str, Dict[Tuple, Dict[str, Any]]] = {}
        self.operations: List[Tuple[str, str, Dict[str, Any]]] = []
        self.committed = False
        self.rolled_back = False
        # Use common transaction for underlying operations
        self._common_txn: Optional[CommonTransaction] = None
    
    def __enter__(self):
        """Begin the transaction by creating snapshots of tables."""
        # Create snapshots from the underlying storage
        for table_name, table in self.database.tables.items():
            # Get all records from TableStore
            all_records = {}
            for pk_tuple, record in table._data.items():
                all_records[pk_tuple] = copy.deepcopy(record)
            self.tables_snapshot[table_name] = all_records
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Rollback the transaction if not committed and an exception occurred."""
        if exc_type is not None and not self.committed and not self.rolled_back:
            self.rollback()
        return False  # Don't suppress exceptions
    
    def insert(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record as part of this transaction."""
        if self.committed or self.rolled_back:
            raise ValueError("Transaction already completed")

        result = self.database.insert(table_name, record, client_id="transaction")
        self.operations.append(("insert", table_name, copy.deepcopy(record)))
        return result

    def update(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record as part of this transaction."""
        if self.committed or self.rolled_back:
            raise ValueError("Transaction already completed")

        result = self.database.update(table_name, record, client_id="transaction")
        self.operations.append(("update", table_name, copy.deepcopy(record)))
        return result

    def delete(self, table_name: str, primary_key_values: List[Any]) -> None:
        """Delete a record as part of this transaction."""
        if self.committed or self.rolled_back:
            raise ValueError("Transaction already completed")

        self.database.delete(table_name, primary_key_values, client_id="transaction")
        self.operations.append(("delete", table_name, {"primary_key_values": primary_key_values}))
    
    def commit(self) -> None:
        """Commit the transaction."""
        if self.committed or self.rolled_back:
            raise ValueError("Transaction already completed")
        
        self.committed = True
        # All changes have already been applied to the database tables
        # We just need to mark the transaction as committed
    
    def rollback(self) -> None:
        """Roll back the transaction."""
        if self.committed or self.rolled_back:
            raise ValueError("Transaction already completed")

        # Step 1: Remove any newly added records
        for op_type, table_name, data in self.operations:
            if op_type == "insert":
                # For inserts, we need to remove the record
                table = self.database.tables.get(table_name)
                if table:
                    # Extract the primary key to identify the record
                    primary_keys = self.database.schema.tables[table_name].primary_keys
                    pk_values = [data[pk_name] for pk_name in primary_keys if pk_name in data]
                    if pk_values:
                        pk_tuple = tuple(pk_values)
                        # Remove the record that was inserted using TableStore method
                        try:
                            super(Table, table).delete(pk_tuple)
                            # Also remove from last_modified
                            table.last_modified.pop(pk_tuple, None)
                        except:
                            pass  # Record might not exist

        # Step 2: Restore previous state for updated records
        for table_name, records_snapshot in self.tables_snapshot.items():
            table = self.database.tables[table_name]
            # Clear the table and restore all records from the snapshot
            table.clear()
            for pk_tuple, record in records_snapshot.items():
                table._data[pk_tuple] = copy.deepcopy(record)
                # Restore timestamps
                if hasattr(table, '_created_at'):
                    table._created_at[pk_tuple] = getattr(table, '_created_at', {}).get(pk_tuple, time.time())
                if hasattr(table, '_updated_at'):
                    table._updated_at[pk_tuple] = time.time()

        # Step 3: Remove transaction changes from change logs
        for table_name in self.database.tables:
            table = self.database.tables[table_name]
            # Remove changes with this transaction's client ID
            original_length = len(table.change_log)
            table.change_log = [
                change for change in table.change_log
                if change.get("client_id") != "transaction"
            ]
            # If we removed changes, reset the index counter
            if len(table.change_log) < original_length:
                table.index_counter = max([0] + [c.get("id", 0) for c in table.change_log])

        self.rolled_back = True


class Database:
    """
    An in-memory database that stores tables and supports transactions.
    """
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.tables: Dict[str, Table] = {}
        
        # Initialize common components
        self.transaction_manager = TransactionManager()
        self.version_manager = VersionManager()

        # Create tables based on the schema
        for table_name, table_schema in schema.tables.items():
            self._create_table(table_schema)

    def _create_table(self, table_schema: TableSchema) -> Table:
        """Create a new table based on the schema."""
        table = Table(table_schema)
        self.tables[table_schema.name] = table
        return table
    
    def _get_table(self, table_name: str) -> Table:
        """Get a table by name or raise an exception if it doesn't exist."""
        table = self.tables.get(table_name)
        if table is None:
            raise ValueError(f"Table {table_name} does not exist")
        return table
    
    def insert(self, 
              table_name: str, 
              record: Dict[str, Any], 
              client_id: Optional[str] = None,
              transaction: Optional[Transaction] = None) -> Dict[str, Any]:
        """
        Insert a record into a table.
        
        Args:
            table_name: The name of the table
            record: The record to insert
            client_id: Optional ID of the client making the change
            transaction: Optional transaction to use
            
        Returns:
            The inserted record
        """
        table = self._get_table(table_name)
        return table.insert(record, client_id)
    
    def update(self, 
              table_name: str, 
              record: Dict[str, Any], 
              client_id: Optional[str] = None,
              transaction: Optional[Transaction] = None) -> Dict[str, Any]:
        """
        Update a record in a table.
        
        Args:
            table_name: The name of the table
            record: The record to update (must include primary key)
            client_id: Optional ID of the client making the change
            transaction: Optional transaction to use
            
        Returns:
            The updated record
        """
        table = self._get_table(table_name)
        return table.update(record, client_id)
    
    def delete(self, 
              table_name: str, 
              primary_key_values: List[Any], 
              client_id: Optional[str] = None,
              transaction: Optional[Transaction] = None) -> None:
        """
        Delete a record from a table.
        
        Args:
            table_name: The name of the table
            primary_key_values: The values for the primary key columns
            client_id: Optional ID of the client making the change
            transaction: Optional transaction to use
        """
        table = self._get_table(table_name)
        table.delete(primary_key_values, client_id)
    
    def get(self, table_name: str, primary_key_values: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Get a record from a table by its primary key.
        
        Args:
            table_name: The name of the table
            primary_key_values: The values for the primary key columns
            
        Returns:
            The record if found, None otherwise
        """
        table = self._get_table(table_name)
        return table.get(primary_key_values)
    
    def query(self, 
             table_name: str, 
             conditions: Optional[Dict[str, Any]] = None, 
             limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query records from a table.
        
        Args:
            table_name: The name of the table
            conditions: Optional conditions that records must match
            limit: Optional maximum number of records to return
            
        Returns:
            List of matching records
        """
        table = self._get_table(table_name)
        return table.query(conditions, limit)
    
    def begin_transaction(self) -> Transaction:
        """Begin a new transaction."""
        # Can optionally use the common transaction manager for more advanced features
        # For now, maintain compatibility with existing Transaction class
        return Transaction(self)
    
    def get_changes_since(self, table_name: str, index: int) -> List[Dict[str, Any]]:
        """
        Get all changes to a table since the given index.
        
        Args:
            table_name: The name of the table
            index: The index to get changes after
            
        Returns:
            List of changes
        """
        table = self._get_table(table_name)
        return table.get_changes_since(index)
    
    def generate_client_id(self) -> str:
        """Generate a unique client ID."""
        return str(uuid.uuid4())