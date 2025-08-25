# Unified Library Architecture Plan

## Executive Summary

This document outlines the architecture and migration strategy for creating a unified library from the `researchtrack` and `securetask` persona implementations. The unified library will extract ~60-70% of common functionality while preserving persona-specific features.

## 1. Core Components Architecture

### 1.1 Base Models (`common/core/models.py`)

#### BaseEntity
Abstract base class for all entities with common fields:
```python
- id: str (UUID)
- created_at: datetime
- updated_at: datetime  
- metadata: Dict[str, Any]
```

#### TimestampedMixin
Mixin for automatic timestamp management:
```python
- created_at: datetime (auto-set on creation)
- updated_at: datetime (auto-update on modification)
```

#### StatusMixin
Generic status tracking with transitions:
```python
- status: Enum
- status_history: List[StatusChange]
- valid_transitions: Dict[Status, List[Status]]
```

#### TaggedMixin
Common tagging functionality:
```python
- tags: Set[str]
- add_tag(tag: str)
- remove_tag(tag: str)
- has_tag(tag: str) -> bool
```

### 1.2 Storage Layer (`common/core/storage.py`)

#### StorageInterface (ABC)
Abstract interface for all storage implementations:
```python
class StorageInterface(ABC):
    - create(entity: T) -> str
    - get(id: str) -> Optional[T]
    - update(entity: T) -> Optional[T]
    - delete(id: str) -> bool
    - list(filters: Dict, sort_by: str, limit: int, offset: int) -> List[T]
    - count(filters: Dict) -> int
    - clear() -> None
```

#### InMemoryStorage
Generic in-memory implementation for development/testing:
```python
class InMemoryStorage(StorageInterface):
    - _items: Dict[str, T]
    - _apply_filters(items, filters) -> List[T]
    - _apply_sorting(items, sort_by) -> List[T]
```

#### FileStorage  
Generic file-based storage with JSON serialization:
```python
class FileStorage(StorageInterface):
    - filepath: Path
    - _load() -> Dict[str, T]
    - _save(data: Dict[str, T])
    - _ensure_directory()
```

### 1.3 Service Layer (`common/core/service.py`)

#### BaseService
Abstract service with common operations:
```python
class BaseService(ABC):
    - storage: StorageInterface
    - validators: List[Callable]
    - create_with_validation(entity) -> str
    - update_with_validation(entity) -> Optional[T]
    - validate(entity) -> List[ValidationError]
```

#### ServiceRegistry
Central registry for service discovery:
```python
class ServiceRegistry:
    - register(name: str, service: BaseService)
    - get(name: str) -> Optional[BaseService]
    - list_services() -> List[str]
```

### 1.4 Validation (`common/core/validation.py`)

#### ValidationError
Structured validation error:
```python
class ValidationError:
    - field: str
    - message: str
    - code: str
    - context: Dict[str, Any]
```

#### Validators
Common validation functions:
```python
- validate_uuid(value: str) -> bool
- validate_email(value: str) -> bool
- validate_date_range(start: datetime, end: datetime) -> bool
- validate_enum_value(value: Any, enum_class: Type[Enum]) -> bool
```

#### ValidationMixin
Mixin for entities with self-validation:
```python
class ValidationMixin:
    - validate_fields() -> List[ValidationError]
    - is_valid() -> bool
```

### 1.5 Utilities (`common/core/utils.py`)

#### Serialization
```python
- to_dict(entity: BaseEntity) -> Dict
- from_dict(data: Dict, entity_class: Type[T]) -> T
- json_encoder(obj: Any) -> Any
```

#### File Operations
```python
- ensure_directory(path: Path)
- safe_file_write(path: Path, content: str)
- atomic_file_update(path: Path, updater: Callable)
```

#### Data Transformations
```python
- merge_metadata(base: Dict, updates: Dict) -> Dict
- filter_dict(data: Dict, keys: List[str]) -> Dict
- deep_update(base: Dict, updates: Dict) -> Dict
```

## 2. Migration Strategy

### 2.1 ResearchTrack Migration

#### Phase 1: Core Model Migration
1. **Task Management**
   - Extend `BaseEntity` for `Task` model
   - Use `StatusMixin` for task status tracking
   - Use `TaggedMixin` for task tagging
   - Preserve `subtasks` relationship

2. **Experiment Tracking**
   - Extend `BaseEntity` for `Experiment` model
   - Use `TimestampedMixin` for automatic timestamps
   - Preserve `parameters`, `metrics`, `artifacts` structure

3. **Bibliography**
   - Extend `BaseEntity` for `Reference` model
   - Keep citation-specific fields (authors, title, year)
   - Preserve formatting capabilities

#### Phase 2: Storage Migration
1. Replace custom storage with `InMemoryStorage`
2. Configure storage with entity-specific serialization
3. Maintain backward compatibility with existing data structures

#### Phase 3: Service Migration  
1. Extend `BaseService` for each domain service
2. Register services with `ServiceRegistry`
3. Preserve domain-specific business logic
4. Maintain cross-module validation callbacks

### 2.2 SecureTask Migration

#### Phase 1: Core Model Migration
1. **Findings**
   - Extend `BaseEntity` for `Finding` model
   - Use custom status transitions for security workflow
   - Preserve CVSS scoring and remediation tracking

2. **Evidence**
   - Extend `BaseEntity` for `Evidence` model
   - Add encryption layer on top of base storage
   - Preserve hash verification and integrity checks

3. **Compliance**
   - Extend `BaseEntity` for compliance checks
   - Preserve framework-specific validations

#### Phase 2: Storage Migration
1. Extend `FileStorage` with encryption capabilities
2. Implement `EncryptedFileStorage` subclass
3. Preserve user-based access control
4. Maintain backward compatibility with encrypted data

#### Phase 3: Service Migration
1. Extend `BaseService` with security-specific validations
2. Preserve redaction and sanitization logic
3. Maintain audit trail functionality

## 3. Implementation Phases

### Phase 1: Common Library Implementation (Week 1)
- [ ] Implement base models and mixins
- [ ] Implement storage interfaces and implementations
- [ ] Implement service base classes
- [ ] Implement validation framework
- [ ] Implement utility functions
- [ ] Write unit tests for common library

### Phase 2: ResearchTrack Refactoring (Week 2)
- [ ] Migrate task_management module
- [ ] Migrate experiment_tracking module
- [ ] Migrate bibliography module
- [ ] Migrate dataset_versioning module
- [ ] Migrate environment module
- [ ] Migrate export module
- [ ] Ensure all researcher tests pass

### Phase 3: SecureTask Refactoring (Week 3)
- [ ] Migrate findings module
- [ ] Migrate evidence module
- [ ] Migrate compliance module
- [ ] Migrate cvss module
- [ ] Migrate remediation module
- [ ] Migrate reporting module
- [ ] Ensure all security_analyst tests pass

### Phase 4: Integration Testing (Week 4)
- [ ] Run full test suite
- [ ] Performance benchmarking
- [ ] Documentation updates
- [ ] Final code review

## 4. Key Design Decisions

### 4.1 UUID Strategy
- Use string UUIDs for universal compatibility
- Auto-generate UUIDs in base entity constructor
- Preserve existing UUID values during migration

### 4.2 Storage Abstraction
- Single interface supporting multiple implementations
- In-memory for development/testing
- File-based for production
- Encrypted file-based for security persona

### 4.3 Validation Architecture
- Declarative validation in models
- Service-layer validation orchestration
- Extensible validator registration
- Consistent error reporting

### 4.4 Backward Compatibility
- Preserve all existing public APIs
- Maintain data structure compatibility
- No changes to test files
- Gradual migration path

## 5. Risk Mitigation

### 5.1 Testing Strategy
- Run tests after each migration phase
- Maintain 100% test coverage
- Performance regression testing
- Integration testing between personas

### 5.2 Rollback Plan
- Version control for incremental changes
- Feature flags for gradual rollout
- Parallel implementation during migration
- Comprehensive backup before migration

## 6. Success Metrics

### 6.1 Code Reduction
- Target: 60-70% reduction in duplicated code
- Measure: Lines of code analysis before/after

### 6.2 Performance
- No regression in test execution time
- Memory usage within 10% of original
- File I/O operations optimized

### 6.3 Maintainability
- Single source of truth for common logic
- Clear separation of concerns
- Improved code organization
- Enhanced documentation

## 7. Technical Debt Addressed

### 7.1 Code Duplication
- Eliminate duplicate model definitions
- Consolidate storage implementations
- Unify validation logic
- Standardize error handling

### 7.2 Inconsistencies
- Standardize naming conventions
- Unify API patterns
- Consistent error messages
- Aligned data structures

### 7.3 Testability
- Improved mocking capabilities
- Clearer test boundaries
- Reusable test fixtures
- Better test isolation

## Appendix A: Module Mapping

### ResearchTrack Modules
| Original Module | Common Components | Persona-Specific |
|----------------|-------------------|------------------|
| task_management | BaseEntity, InMemoryStorage, BaseService | Task relationships, priority logic |
| experiment_tracking | BaseEntity, StatusMixin, InMemoryStorage | Metrics, artifacts, parameters |
| bibliography | BaseEntity, InMemoryStorage | Citation formats, bibliography styles |
| dataset_versioning | BaseEntity, TimestampedMixin | Version comparison, checksums |
| environment | BaseEntity, InMemoryStorage | Package management, snapshots |
| export | BaseService | Format-specific exporters |

### SecureTask Modules
| Original Module | Common Components | Persona-Specific |
|----------------|-------------------|------------------|
| findings | BaseEntity, StatusMixin, FileStorage | CVSS scoring, severity calc |
| evidence | BaseEntity, EncryptedFileStorage | Integrity verification, hashing |
| compliance | BaseEntity, FileStorage | Framework-specific checks |
| cvss | Validation utilities | CVSS calculation logic |
| remediation | BaseEntity, StatusMixin | Workflow automation |
| reporting | BaseService | Redaction, report generation |

## Appendix B: API Compatibility Matrix

All existing public APIs will be preserved through facade patterns and adapter layers to ensure zero breaking changes for existing test suites.