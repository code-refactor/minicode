"""Query module for the unified library."""

from .interface import Query, QueryBuilder, QueryResult, QueryType
from .filters import Filter, FilterType, ComparisonOperator
from .executor import QueryExecutor

__all__ = [
    'Query',
    'QueryBuilder',
    'QueryResult',
    'QueryType',
    'Filter',
    'FilterType',
    'ComparisonOperator',
    'QueryExecutor'
]