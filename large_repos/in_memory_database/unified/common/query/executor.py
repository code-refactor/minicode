"""Query execution engine for the unified library."""

from typing import Any, Dict, List, Optional, Union, Callable, Iterator
from abc import ABC, abstractmethod
import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager

from .interface import Query, QueryResult, QueryType, SortOrder
from .filters import Filter, FilterType


logger = logging.getLogger(__name__)


class QueryExecutorError(Exception):
    """Base exception for query execution errors."""
    pass


class QueryValidationError(QueryExecutorError):
    """Raised when query validation fails."""
    pass


class QueryExecutionError(QueryExecutorError):
    """Raised when query execution fails."""
    pass


class DataAdapter(ABC):
    """Abstract adapter for different data sources."""
    
    @abstractmethod
    def get_records(self, target: str, filters: List[Filter] = None) -> Iterator[Dict[str, Any]]:
        """Get records from the data source."""
        pass
    
    @abstractmethod
    def insert_records(self, target: str, records: Union[Dict[str, Any], List[Dict[str, Any]]]) -> int:
        """Insert records into the data source. Returns number of inserted records."""
        pass
    
    @abstractmethod
    def update_records(self, target: str, filters: List[Filter], updates: Dict[str, Any]) -> int:
        """Update records in the data source. Returns number of updated records."""
        pass
    
    @abstractmethod
    def delete_records(self, target: str, filters: List[Filter]) -> int:
        """Delete records from the data source. Returns number of deleted records."""
        pass
    
    @abstractmethod
    def get_target_info(self, target: str) -> Dict[str, Any]:
        """Get information about the target (table/collection)."""
        pass


class InMemoryAdapter(DataAdapter):
    """Simple in-memory data adapter for testing and basic operations."""
    
    def __init__(self):
        """Initialize the in-memory adapter."""
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self.target_info: Dict[str, Dict[str, Any]] = {}
    
    def create_target(self, target: str, schema: Optional[Dict[str, Any]] = None) -> None:
        """Create a new target (table/collection)."""
        if target not in self.data:
            self.data[target] = []
            self.target_info[target] = {
                'schema': schema or {},
                'created_at': time.time(),
                'record_count': 0
            }
    
    def get_records(self, target: str, filters: List[Filter] = None) -> Iterator[Dict[str, Any]]:
        """Get records from the target."""
        if target not in self.data:
            return iter([])
        
        records = self.data[target]
        
        if not filters:
            yield from records
            return
        
        for record in records:
            if all(f.evaluate(record) for f in filters):
                yield record
    
    def insert_records(self, target: str, records: Union[Dict[str, Any], List[Dict[str, Any]]]) -> int:
        """Insert records into the target."""
        if target not in self.data:
            self.create_target(target)
        
        if isinstance(records, dict):
            records = [records]
        
        self.data[target].extend(records)
        self.target_info[target]['record_count'] = len(self.data[target])
        
        return len(records)
    
    def update_records(self, target: str, filters: List[Filter], updates: Dict[str, Any]) -> int:
        """Update records in the target."""
        if target not in self.data:
            return 0
        
        updated_count = 0
        records = self.data[target]
        
        for i, record in enumerate(records):
            if all(f.evaluate(record) for f in (filters or [])):
                # Apply updates
                for field, value in updates.items():
                    records[i][field] = value
                updated_count += 1
        
        return updated_count
    
    def delete_records(self, target: str, filters: List[Filter]) -> int:
        """Delete records from the target."""
        if target not in self.data:
            return 0
        
        original_count = len(self.data[target])
        
        if not filters:
            # Delete all records
            self.data[target] = []
        else:
            # Delete matching records
            self.data[target] = [
                record for record in self.data[target]
                if not all(f.evaluate(record) for f in filters)
            ]
        
        deleted_count = original_count - len(self.data[target])
        self.target_info[target]['record_count'] = len(self.data[target])
        
        return deleted_count
    
    def get_target_info(self, target: str) -> Dict[str, Any]:
        """Get information about the target."""
        return self.target_info.get(target, {})


class QueryExecutor:
    """Main query execution engine."""
    
    def __init__(self, adapter: DataAdapter, max_workers: int = 4):
        """Initialize the query executor.
        
        Args:
            adapter: Data adapter for accessing the data source
            max_workers: Maximum number of worker threads for parallel execution
        """
        self.adapter = adapter
        self.max_workers = max_workers
        self.executor_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._query_hooks: Dict[str, List[Callable]] = {
            'before_execute': [],
            'after_execute': [],
            'on_error': []
        }
    
    def register_hook(self, hook_type: str, callback: Callable) -> None:
        """Register a hook callback for query execution events.
        
        Args:
            hook_type: Type of hook ('before_execute', 'after_execute', 'on_error')
            callback: Callback function to register
        """
        if hook_type not in self._query_hooks:
            raise ValueError(f"Unknown hook type: {hook_type}")
        
        self._query_hooks[hook_type].append(callback)
    
    def execute(self, query: Query, async_execution: bool = False) -> Union[QueryResult, Future[QueryResult]]:
        """Execute a query.
        
        Args:
            query: Query to execute
            async_execution: Whether to execute asynchronously
            
        Returns:
            QueryResult or Future[QueryResult] if async
        """
        if async_execution:
            return self.executor_pool.submit(self._execute_sync, query)
        else:
            return self._execute_sync(query)
    
    def execute_batch(self, queries: List[Query], parallel: bool = True) -> List[QueryResult]:
        """Execute multiple queries.
        
        Args:
            queries: List of queries to execute
            parallel: Whether to execute queries in parallel
            
        Returns:
            List of query results
        """
        if not parallel or len(queries) <= 1:
            return [self._execute_sync(query) for query in queries]
        
        # Execute queries in parallel
        futures = [self.executor_pool.submit(self._execute_sync, query) for query in queries]
        return [future.result() for future in futures]
    
    def _execute_sync(self, query: Query) -> QueryResult:
        """Synchronously execute a query."""
        start_time = time.time()
        
        try:
            # Run before_execute hooks
            for hook in self._query_hooks['before_execute']:
                hook(query)
            
            # Validate query
            self._validate_query(query)
            
            # Execute based on query type
            if query.query_type == QueryType.SELECT:
                result = self._execute_select(query)
            elif query.query_type == QueryType.INSERT:
                result = self._execute_insert(query)
            elif query.query_type == QueryType.UPDATE:
                result = self._execute_update(query)
            elif query.query_type == QueryType.DELETE:
                result = self._execute_delete(query)
            elif query.query_type == QueryType.AGGREGATE:
                result = self._execute_aggregate(query)
            else:
                raise QueryExecutionError(f"Unsupported query type: {query.query_type}")
            
            # Set execution time
            result.execution_time = time.time() - start_time
            
            # Run after_execute hooks
            for hook in self._query_hooks['after_execute']:
                hook(query, result)
            
            return result
        
        except Exception as e:
            # Run error hooks
            for hook in self._query_hooks['on_error']:
                try:
                    hook(query, e)
                except Exception as hook_error:
                    logger.error(f"Error in error hook: {hook_error}")
            
            # Create error result
            result = QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
            
            return result
    
    def _validate_query(self, query: Query) -> None:
        """Validate a query before execution."""
        if not query.target:
            raise QueryValidationError("Query must specify a target")
        
        if query.query_type == QueryType.INSERT and query.data is None:
            raise QueryValidationError("INSERT query must specify data")
        
        if query.query_type == QueryType.UPDATE and query.data is None:
            raise QueryValidationError("UPDATE query must specify data")
        
        # Validate filter conditions
        if query.conditions:
            for field, value in query.conditions.items():
                if not isinstance(field, str):
                    raise QueryValidationError(f"Filter field must be string, got {type(field)}")
        
        # Validate order by fields
        for field, order in query.order_by:
            if not isinstance(field, str):
                raise QueryValidationError(f"Order by field must be string, got {type(field)}")
    
    def _execute_select(self, query: Query) -> QueryResult:
        """Execute a SELECT query."""
        try:
            # Convert conditions to filters
            filters = self._conditions_to_filters(query.conditions)
            
            # Get records from adapter
            records = list(self.adapter.get_records(query.target, filters))
            
            # Apply field projection
            if query.fields:
                projected_records = []
                for record in records:
                    projected = {field: record.get(field) for field in query.fields if field in record}
                    projected_records.append(projected)
                records = projected_records
            
            # Apply sorting
            if query.order_by:
                records = self._sort_records(records, query.order_by)
            
            # Apply offset and limit
            if query.offset:
                records = records[query.offset:]
            
            if query.limit:
                records = records[:query.limit]
            
            return QueryResult(
                success=True,
                data=records,
                count=len(records),
                metadata={'query_type': 'select'}
            )
        
        except Exception as e:
            raise QueryExecutionError(f"SELECT query failed: {str(e)}")
    
    def _execute_insert(self, query: Query) -> QueryResult:
        """Execute an INSERT query."""
        try:
            inserted_count = self.adapter.insert_records(query.target, query.data)
            
            return QueryResult(
                success=True,
                count=inserted_count,
                metadata={'query_type': 'insert', 'inserted_count': inserted_count}
            )
        
        except Exception as e:
            raise QueryExecutionError(f"INSERT query failed: {str(e)}")
    
    def _execute_update(self, query: Query) -> QueryResult:
        """Execute an UPDATE query."""
        try:
            filters = self._conditions_to_filters(query.conditions)
            updated_count = self.adapter.update_records(query.target, filters, query.data)
            
            return QueryResult(
                success=True,
                count=updated_count,
                metadata={'query_type': 'update', 'updated_count': updated_count}
            )
        
        except Exception as e:
            raise QueryExecutionError(f"UPDATE query failed: {str(e)}")
    
    def _execute_delete(self, query: Query) -> QueryResult:
        """Execute a DELETE query."""
        try:
            filters = self._conditions_to_filters(query.conditions)
            deleted_count = self.adapter.delete_records(query.target, filters)
            
            return QueryResult(
                success=True,
                count=deleted_count,
                metadata={'query_type': 'delete', 'deleted_count': deleted_count}
            )
        
        except Exception as e:
            raise QueryExecutionError(f"DELETE query failed: {str(e)}")
    
    def _execute_aggregate(self, query: Query) -> QueryResult:
        """Execute an AGGREGATE query."""
        try:
            # Get base records
            filters = self._conditions_to_filters(query.conditions)
            records = list(self.adapter.get_records(query.target, filters))
            
            # Group records if needed
            if query.group_by:
                grouped_records = self._group_records(records, query.group_by)
            else:
                grouped_records = {'all': records}
            
            # Apply aggregates to each group
            results = []
            for group_key, group_records in grouped_records.items():
                if not group_records:
                    continue
                
                group_result = {}
                
                # Add group by fields
                if query.group_by and isinstance(group_key, dict):
                    group_result.update(group_key)
                
                # Calculate aggregates
                for field, func_name in query.aggregates.items():
                    value = self._calculate_aggregate(group_records, field, func_name)
                    group_result[f"{func_name}_{field}"] = value
                
                results.append(group_result)
            
            # Apply HAVING filters
            if query.having:
                having_filters = self._conditions_to_filters(query.having)
                results = [
                    result for result in results
                    if all(f.evaluate(result) for f in having_filters)
                ]
            
            # Apply sorting
            if query.order_by:
                results = self._sort_records(results, query.order_by)
            
            # Apply offset and limit
            if query.offset:
                results = results[query.offset:]
            
            if query.limit:
                results = results[:query.limit]
            
            return QueryResult(
                success=True,
                data=results,
                count=len(results),
                metadata={'query_type': 'aggregate'}
            )
        
        except Exception as e:
            raise QueryExecutionError(f"AGGREGATE query failed: {str(e)}")
    
    def _conditions_to_filters(self, conditions: Dict[str, Any]) -> List[Filter]:
        """Convert query conditions to Filter objects."""
        filters = []
        
        for field, value in conditions.items():
            # Handle special condition formats
            if isinstance(value, dict) and len(value) == 1:
                # Handle operators like {'$gt': 10}, {'$in': [1,2,3]}
                operator, op_value = next(iter(value.items()))
                
                if operator == '$gt':
                    filter_type = FilterType.GREATER_THAN
                elif operator == '$gte':
                    filter_type = FilterType.GREATER_EQUAL
                elif operator == '$lt':
                    filter_type = FilterType.LESS_THAN
                elif operator == '$lte':
                    filter_type = FilterType.LESS_EQUAL
                elif operator == '$ne':
                    filter_type = FilterType.NOT_EQUALS
                elif operator == '$in':
                    filter_type = FilterType.IN
                    filters.append(Filter(field, filter_type, values=op_value))
                    continue
                elif operator == '$nin':
                    filter_type = FilterType.NOT_IN
                    filters.append(Filter(field, filter_type, values=op_value))
                    continue
                else:
                    # Default to equals
                    filter_type = FilterType.EQUALS
                    op_value = value
                
                filters.append(Filter(field, filter_type, value=op_value))
            else:
                # Simple equality
                filters.append(Filter(field, FilterType.EQUALS, value=value))
        
        return filters
    
    def _sort_records(self, records: List[Dict[str, Any]], order_by: List[tuple]) -> List[Dict[str, Any]]:
        """Sort records based on order_by specification."""
        if not records or not order_by:
            return records
        
        # Create sort key function
        def sort_key(record):
            keys = []
            for field, order in order_by:
                value = record.get(field)
                # Handle None values - put them last
                if value is None:
                    keys.append((1, ''))  # Tuple for stable sort
                else:
                    keys.append((0, value))
            return keys
        
        # Sort with reverse for descending orders
        for field, order in reversed(order_by):
            reverse = (order == SortOrder.DESC)
            records = sorted(records, key=lambda r: (r.get(field) is None, r.get(field)), reverse=reverse)
        
        return records
    
    def _group_records(self, records: List[Dict[str, Any]], group_by: List[str]) -> Dict[Any, List[Dict[str, Any]]]:
        """Group records by the specified fields."""
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        
        for record in records:
            # Create group key
            if len(group_by) == 1:
                group_key = record.get(group_by[0])
            else:
                group_key = tuple(record.get(field) for field in group_by)
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(record)
        
        return groups
    
    def _calculate_aggregate(self, records: List[Dict[str, Any]], field: str, func_name: str) -> Any:
        """Calculate aggregate function on a field."""
        if not records:
            return None
        
        values = [record.get(field) for record in records if record.get(field) is not None]
        
        if not values:
            return None
        
        func_name = func_name.lower()
        
        if func_name == 'count':
            return len(values)
        elif func_name == 'sum':
            return sum(values) if all(isinstance(v, (int, float)) for v in values) else None
        elif func_name == 'avg' or func_name == 'average':
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            return sum(numeric_values) / len(numeric_values) if numeric_values else None
        elif func_name == 'min':
            return min(values)
        elif func_name == 'max':
            return max(values)
        elif func_name == 'first':
            return values[0]
        elif func_name == 'last':
            return values[-1]
        else:
            raise QueryExecutionError(f"Unknown aggregate function: {func_name}")
    
    @contextmanager
    def transaction(self):
        """Context manager for transactional query execution."""
        # Simple implementation - in a real system this would coordinate with the adapter
        transaction_queries = []
        try:
            # Store queries executed in transaction
            original_execute = self._execute_sync
            
            def transactional_execute(query):
                transaction_queries.append(query)
                return original_execute(query)
            
            self._execute_sync = transactional_execute
            yield self
            
        except Exception as e:
            # In a real implementation, this would rollback changes
            logger.error(f"Transaction failed, would rollback {len(transaction_queries)} queries: {e}")
            raise
        
        finally:
            # Restore original execute method
            self._execute_sync = original_execute
    
    def close(self) -> None:
        """Close the executor and cleanup resources."""
        self.executor_pool.shutdown(wait=True)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()