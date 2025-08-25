"""Query interface definitions for the unified library."""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QueryType(Enum):
    """Types of queries supported."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    AGGREGATE = "aggregate"


class SortOrder(Enum):
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryResult:
    """Result of a query execution."""
    success: bool
    data: List[Any] = field(default_factory=list)
    count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: Optional[float] = None
    
    def __bool__(self) -> bool:
        """Boolean representation based on success."""
        return self.success
    
    def __len__(self) -> int:
        """Length is the count of results."""
        return self.count
    
    def __iter__(self):
        """Iterate over data."""
        return iter(self.data)


@dataclass
class Query:
    """Represents a database query."""
    query_type: QueryType
    target: str  # Table/collection name
    fields: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    order_by: List[Tuple[str, SortOrder]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    data: Optional[Any] = None  # For INSERT/UPDATE
    aggregates: Dict[str, str] = field(default_factory=dict)  # field -> function
    group_by: List[str] = field(default_factory=list)
    having: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary."""
        return {
            'query_type': self.query_type.value,
            'target': self.target,
            'fields': self.fields,
            'conditions': self.conditions,
            'order_by': [(f, o.value) for f, o in self.order_by],
            'limit': self.limit,
            'offset': self.offset,
            'data': self.data,
            'aggregates': self.aggregates,
            'group_by': self.group_by,
            'having': self.having
        }


class QueryBuilder:
    """Fluent interface for building queries."""
    
    def __init__(self, target: str = None):
        """Initialize query builder.
        
        Args:
            target: Target table/collection name
        """
        self._target = target
        self._query_type = QueryType.SELECT
        self._fields: List[str] = []
        self._conditions: Dict[str, Any] = {}
        self._order_by: List[Tuple[str, SortOrder]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._data: Optional[Any] = None
        self._aggregates: Dict[str, str] = {}
        self._group_by: List[str] = []
        self._having: Dict[str, Any] = {}
        self._joins: List[Dict[str, Any]] = []
    
    def from_table(self, target: str) -> 'QueryBuilder':
        """Set the target table/collection.
        
        Args:
            target: Table/collection name
        
        Returns:
            Self for chaining
        """
        self._target = target
        return self
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """Select specific fields.
        
        Args:
            fields: Fields to select
        
        Returns:
            Self for chaining
        """
        self._query_type = QueryType.SELECT
        self._fields.extend(fields)
        return self
    
    def insert(self, data: Any) -> 'QueryBuilder':
        """Set up an insert query.
        
        Args:
            data: Data to insert
        
        Returns:
            Self for chaining
        """
        self._query_type = QueryType.INSERT
        self._data = data
        return self
    
    def update(self, data: Any) -> 'QueryBuilder':
        """Set up an update query.
        
        Args:
            data: Data to update
        
        Returns:
            Self for chaining
        """
        self._query_type = QueryType.UPDATE
        self._data = data
        return self
    
    def delete(self) -> 'QueryBuilder':
        """Set up a delete query.
        
        Returns:
            Self for chaining
        """
        self._query_type = QueryType.DELETE
        return self
    
    def where(self, **conditions) -> 'QueryBuilder':
        """Add WHERE conditions.
        
        Args:
            conditions: Field-value conditions
        
        Returns:
            Self for chaining
        """
        self._conditions.update(conditions)
        return self
    
    def filter(self, **conditions) -> 'QueryBuilder':
        """Alias for where().
        
        Args:
            conditions: Field-value conditions
        
        Returns:
            Self for chaining
        """
        return self.where(**conditions)
    
    def order_by(self, field: str, desc: bool = False) -> 'QueryBuilder':
        """Add ORDER BY clause.
        
        Args:
            field: Field to order by
            desc: Sort descending if True
        
        Returns:
            Self for chaining
        """
        order = SortOrder.DESC if desc else SortOrder.ASC
        self._order_by.append((field, order))
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Set result limit.
        
        Args:
            count: Maximum number of results
        
        Returns:
            Self for chaining
        """
        self._limit = count
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """Set result offset.
        
        Args:
            count: Number of results to skip
        
        Returns:
            Self for chaining
        """
        self._offset = count
        return self
    
    def aggregate(self, **aggregates) -> 'QueryBuilder':
        """Add aggregate functions.
        
        Args:
            aggregates: Field to function mappings (e.g., price='sum')
        
        Returns:
            Self for chaining
        """
        self._query_type = QueryType.AGGREGATE
        self._aggregates.update(aggregates)
        return self
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY clause.
        
        Args:
            fields: Fields to group by
        
        Returns:
            Self for chaining
        """
        self._group_by.extend(fields)
        return self
    
    def having(self, **conditions) -> 'QueryBuilder':
        """Add HAVING conditions.
        
        Args:
            conditions: Conditions for grouped results
        
        Returns:
            Self for chaining
        """
        self._having.update(conditions)
        return self
    
    def join(self, table: str, on: Dict[str, str], join_type: str = 'inner') -> 'QueryBuilder':
        """Add a JOIN clause.
        
        Args:
            table: Table to join
            on: Join conditions
            join_type: Type of join ('inner', 'left', 'right', 'outer')
        
        Returns:
            Self for chaining
        """
        self._joins.append({
            'table': table,
            'on': on,
            'type': join_type
        })
        return self
    
    def build(self) -> Query:
        """Build the final Query object.
        
        Returns:
            The constructed Query
        """
        if not self._target:
            raise ValueError("Target table/collection not specified")
        
        return Query(
            query_type=self._query_type,
            target=self._target,
            fields=self._fields,
            conditions=self._conditions,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            data=self._data,
            aggregates=self._aggregates,
            group_by=self._group_by,
            having=self._having
        )
    
    def __repr__(self) -> str:
        """String representation of the builder state."""
        parts = [f"QueryBuilder(target={self._target}"]
        
        if self._query_type:
            parts.append(f"type={self._query_type.value}")
        
        if self._fields:
            parts.append(f"fields={self._fields}")
        
        if self._conditions:
            parts.append(f"conditions={self._conditions}")
        
        if self._limit:
            parts.append(f"limit={self._limit}")
        
        return ", ".join(parts) + ")"