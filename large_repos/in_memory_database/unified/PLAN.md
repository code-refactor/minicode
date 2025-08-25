# Unified Library Architecture and Migration Plan

## Executive Summary

This document outlines the architecture for a unified common library that consolidates shared functionality between the VectorDB (ML Engineer) and SyncDB (Mobile Developer) implementations. The goal is to reduce code duplication by ~60-70% while maintaining each persona's domain-specific functionality.

## Architecture Overview

### Design Principles

1. **Separation of Concerns**: Core data management separated from domain-specific features
2. **Interface-Based Design**: Well-defined interfaces allowing persona-specific implementations
3. **Composability**: Small, focused modules that can be combined as needed
4. **Extensibility**: Base classes and mixins that can be extended by personas
5. **Zero External Dependencies**: Using only Python standard library

### Common Library Structure

```
common/
├── core/
│   ├── __init__.py
│   ├── storage.py         # In-memory storage abstractions
│   ├── schema.py          # Schema definition and validation
│   ├── version.py         # Version management system
│   ├── transaction.py     # Transaction support
│   ├── index.py          # Indexing abstractions
│   └── serialization.py  # Serialization utilities
├── query/
│   ├── __init__.py
│   ├── interface.py      # Query interface definitions
│   ├── filters.py        # Common filter implementations
│   └── executor.py       # Query execution engine
├── utils/
│   ├── __init__.py
│   ├── threading.py      # Thread-safety utilities
│   ├── validation.py     # Data validation helpers
│   └── types.py          # Type conversion utilities
└── exceptions/
    ├── __init__.py
    └── base.py           # Common exception hierarchy
```

## Core Components

### 1. Storage Layer (`common.core.storage`)

**Base Classes:**

```python
class BaseDataStore:
    """Abstract base for all data storage implementations"""
    - insert(key, data, metadata=None) -> str
    - update(key, data, metadata=None) -> bool
    - delete(key) -> bool
    - get(key) -> Optional[Any]
    - query(conditions=None, limit=None) -> List[Any]
    - batch_operation(operations) -> List[Any]
    - clear() -> None
    - size() -> int

class InMemoryStore(BaseDataStore):
    """Thread-safe in-memory implementation"""
    - Uses Dict for storage
    - RLock for thread safety
    - Metadata tracking
```

**Usage by Personas:**
- VectorDB: Extends for feature storage with entity-based organization
- SyncDB: Extends for table-based storage with record management

### 2. Schema Management (`common.core.schema`)

**Base Classes:**

```python
class Column:
    """Column definition with type and constraints"""
    - name: str
    - data_type: type
    - nullable: bool
    - default: Any
    - constraints: List[Constraint]
    - validate(value) -> Tuple[bool, Optional[str]]

class Schema:
    """Schema definition for structured data"""
    - name: str
    - columns: List[Column]
    - version: int
    - primary_key: List[str]
    - validate_record(record) -> List[str]
    - evolve(changes) -> 'Schema'

class SchemaManager:
    """Manages schema versions and migrations"""
    - register_schema(schema) -> None
    - get_schema(name, version=None) -> Schema
    - migrate_data(data, from_version, to_version) -> Any
```

**Usage by Personas:**
- VectorDB: Light schema usage for feature types and metadata
- SyncDB: Heavy schema usage with migrations and versioning

### 3. Version Management (`common.core.version`)

**Base Classes:**

```python
class Version:
    """Represents a versioned item"""
    - id: str
    - value: Any
    - version_number: int
    - timestamp: datetime
    - created_by: str
    - metadata: Dict[str, Any]

class VersionManager:
    """Manages version history"""
    - add_version(entity_id, item_name, value, **kwargs) -> Version
    - get_version(entity_id, item_name, **selectors) -> Optional[Version]
    - get_history(entity_id, item_name, limit=None) -> List[Version]
    - prune_history(max_versions) -> int
```

**Usage by Personas:**
- VectorDB: Feature versioning with lineage tracking
- SyncDB: Change tracking for synchronization

### 4. Transaction Support (`common.core.transaction`)

**Base Classes:**

```python
class Transaction:
    """ACID transaction support"""
    - begin() -> None
    - commit() -> None
    - rollback() -> None
    - add_operation(operation) -> None
    - is_active() -> bool

class TransactionManager:
    """Manages transaction lifecycle"""
    - begin_transaction() -> Transaction
    - get_current() -> Optional[Transaction]
    - cleanup_abandoned() -> int
```

**Usage by Personas:**
- VectorDB: Atomic feature updates
- SyncDB: Database transaction support

### 5. Query Interface (`common.query`)

**Base Classes:**

```python
class QueryBuilder:
    """Fluent interface for building queries"""
    - select(*fields) -> 'QueryBuilder'
    - filter(**conditions) -> 'QueryBuilder'
    - order_by(field, desc=False) -> 'QueryBuilder'
    - limit(count) -> 'QueryBuilder'
    - offset(count) -> 'QueryBuilder'
    - build() -> Query

class QueryExecutor:
    """Executes queries against data stores"""
    - execute(query, store) -> QueryResult
    - explain(query) -> Dict[str, Any]
```

**Usage by Personas:**
- VectorDB: Extended for vector similarity queries
- SyncDB: Extended for sync-aware queries

### 6. Indexing System (`common.core.index`)

**Base Classes:**

```python
class Index:
    """Abstract index interface"""
    - add(key, value, metadata=None) -> None
    - remove(key) -> bool
    - search(query, limit=None) -> List[Tuple[float, Any]]
    - rebuild() -> None
    - stats() -> Dict[str, Any]

class HashIndex(Index):
    """Hash-based index for exact matches"""

class BTreeIndex(Index):
    """B-tree index for range queries"""
```

**Usage by Personas:**
- VectorDB: Extended with vector-specific indexes (LSH, KD-tree)
- SyncDB: Uses hash indexes for primary keys

### 7. Serialization (`common.core.serialization`)

**Base Classes:**

```python
class Serializable:
    """Mixin for serializable objects"""
    - to_dict() -> Dict[str, Any]
    - from_dict(cls, data) -> 'Serializable'
    - to_json() -> str
    - from_json(cls, json_str) -> 'Serializable'
    - to_bytes() -> bytes
    - from_bytes(cls, data) -> 'Serializable'

class SerializationContext:
    """Context for complex serialization"""
    - register_type(type_class, serializer, deserializer)
    - serialize(obj) -> bytes
    - deserialize(data) -> Any
```

**Usage by Personas:**
- VectorDB: Vector and feature serialization
- SyncDB: Compression-aware serialization

## Migration Strategy

### Phase 1: Common Library Implementation

1. **Week 1**: Core storage and schema modules
   - Implement BaseDataStore and InMemoryStore
   - Implement Column, Schema, and SchemaManager
   - Add comprehensive unit tests

2. **Week 1**: Version and transaction modules
   - Implement Version and VersionManager
   - Implement Transaction and TransactionManager
   - Add unit tests for ACID properties

3. **Week 2**: Query and index modules
   - Implement QueryBuilder and QueryExecutor
   - Implement basic index types
   - Add query optimization tests

4. **Week 2**: Utilities and serialization
   - Implement Serializable mixin
   - Add threading utilities
   - Complete validation helpers

### Phase 2: VectorDB Migration

1. **Refactor Storage Layer**
   - Replace custom storage with InMemoryStore
   - Migrate to common Schema for feature types
   - Update to use common VersionManager

2. **Preserve Domain Features**
   - Keep vector operations in vectordb.core
   - Keep ML transformations in vectordb.transform
   - Keep A/B testing in vectordb.experiment

3. **Integration Points**
   ```python
   from common.core import storage, version, schema
   
   class FeatureStore(storage.InMemoryStore):
       """VectorDB-specific feature store"""
       # Extends common storage with ML features
   ```

### Phase 3: SyncDB Migration

1. **Refactor Database Layer**
   - Replace Database class with common storage
   - Migrate to common Schema system
   - Use common Transaction support

2. **Preserve Domain Features**
   - Keep sync protocols in syncdb.sync
   - Keep conflict resolution in syncdb.sync
   - Keep compression in syncdb.compression

3. **Integration Points**
   ```python
   from common.core import storage, transaction, schema
   
   class SyncDatabase(storage.InMemoryStore):
       """SyncDB-specific database"""
       # Extends common storage with sync features
   ```

## Testing Strategy

### Unit Tests
- Test each common module independently
- Mock dependencies for isolation
- Achieve 95%+ code coverage

### Integration Tests
- Test interaction between common modules
- Verify thread safety under load
- Test transaction isolation levels

### Persona Tests
- Ensure all existing persona tests pass
- No modification to test files
- Performance benchmarks maintained

### Test Execution
```bash
# Run all tests
pytest tests/ --json-report --json-report-file=report.json

# Run common library tests
pytest tests/common/

# Run persona-specific tests
pytest tests/ml_engineer/
pytest tests/mobile_developer/
```

## Performance Considerations

### Memory Optimization
- Lazy loading for large datasets
- Configurable cache sizes
- Efficient data structures (deque for history)

### Concurrency
- Read-write locks for better parallelism
- Lock-free data structures where possible
- Connection pooling patterns

### Query Optimization
- Index usage for filters
- Query plan caching
- Batch operation support

## Risk Mitigation

### Backward Compatibility
- Preserve all public APIs
- Adapter patterns for legacy code
- Gradual migration approach

### Performance Regression
- Benchmark before and after migration
- Profile critical paths
- Optimize hot spots

### Testing Coverage
- Maintain 90%+ coverage
- Test all edge cases
- Stress test concurrent access

## Success Metrics

1. **Code Reduction**: 60-70% reduction in duplicated code
2. **Test Coverage**: All existing tests pass (100%)
3. **Performance**: No regression in benchmarks
4. **Maintainability**: Clear separation of concerns
5. **Extensibility**: Easy to add new personas

## Implementation Timeline

- **Day 1-2**: Implement core common library
- **Day 3**: Migrate VectorDB to use common
- **Day 4**: Migrate SyncDB to use common
- **Day 5**: Test integration and generate report

## Conclusion

This unified architecture provides a solid foundation for both current personas while enabling future extensibility. The common library reduces maintenance burden, improves code quality, and ensures consistent behavior across implementations.