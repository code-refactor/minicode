# Unified Library Architecture and Migration Plan

## Executive Summary

This document outlines the architecture for creating a unified library that extracts common functionality from the `researchbrain` and `productmind` packages. The goal is to eliminate code duplication while maintaining all existing functionality and ensuring backward compatibility.

## Architecture Overview

### Common Library Structure

```
common/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py          # Base models and common fields
│   ├── enums.py           # Shared enumerations
│   ├── storage.py         # Unified storage layer
│   ├── interfaces.py      # Abstract base classes
│   ├── exceptions.py      # Common exceptions
│   └── utils.py           # Utility functions
├── search/
│   ├── __init__.py
│   ├── engine.py          # Text search functionality
│   └── query.py           # Query building and filtering
├── analysis/
│   ├── __init__.py
│   ├── statistics.py      # Statistical calculations
│   ├── relationships.py   # Relationship analysis
│   └── reporting.py       # Export functionality
└── validation/
    ├── __init__.py
    └── validators.py      # Common validators
```

## Core Components

### 1. Base Models (`common.core.models`)

#### BaseEntity
```python
class BaseEntity(BaseModel):
    """Base class for all entities in the system."""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def update(self):
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()
```

#### TaggableEntity
```python
class TaggableEntity(BaseEntity):
    """Base class for entities that support tagging."""
    tags: Set[str] = Field(default_factory=set)
```

#### LinkableEntity
```python
class LinkableEntity(BaseEntity):
    """Base class for entities that can be linked to others."""
    related_ids: Set[UUID] = Field(default_factory=set)
```

### 2. Storage Layer (`common.core.storage`)

#### EntityStorage
Generic storage class that provides:
- CRUD operations
- JSON/YAML serialization
- File-based persistence
- In-memory caching
- Thread-safe operations
- Backup/restore functionality
- Search capabilities

Key methods:
- `save(entity: T) -> None`
- `get(entity_id: UUID) -> Optional[T]`
- `delete(entity_id: UUID) -> bool`
- `list_all() -> List[T]`
- `query(**filters) -> List[T]`
- `search_text(query: str, fields: List[str]) -> List[T]`
- `backup(backup_dir: Path) -> Path`
- `restore(backup_path: Path) -> None`

### 3. Common Enumerations (`common.core.enums`)

```python
class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EntityStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ExportFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    PDF = "pdf"
    BIBTEX = "bibtex"
```

### 4. Interfaces (`common.core.interfaces`)

```python
class EntityManager(ABC, Generic[T]):
    """Abstract base class for entity managers."""
    @abstractmethod
    def add(self, entity: Union[T, List[T]]) -> List[str]: pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[T]: pass
    
    @abstractmethod
    def get_all(self) -> List[T]: pass
    
    @abstractmethod
    def update(self, entity_id: str, updates: Dict) -> bool: pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool: pass
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[T]: pass
```

### 5. Search Engine (`common.search.engine`)

Provides unified text search functionality:
- Full-text search across multiple fields
- Index building and management
- Query parsing and execution
- Result ranking and scoring
- Field-specific search

### 6. Analysis Utilities (`common.analysis`)

Common analysis functions:
- Statistical calculations (mean, median, distribution)
- Relationship network analysis
- Trend detection
- Data aggregation
- Report generation

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1)
1. **Extract Base Models**
   - Create `common.core.models` with BaseEntity, TaggableEntity, LinkableEntity
   - Define common field types and validators
   
2. **Implement Storage Layer**
   - Extract storage patterns from researchbrain
   - Create generic EntityStorage class
   - Implement caching and thread safety

3. **Define Common Enumerations**
   - Extract shared enums from both packages
   - Create standardized naming conventions

### Phase 2: Shared Functionality (Week 2)
1. **Search and Query**
   - Extract text search from both packages
   - Create unified search engine
   - Implement query builder

2. **Analysis and Reporting**
   - Extract common analysis patterns
   - Create shared statistical functions
   - Implement export functionality

3. **Validation and Utilities**
   - Extract common validators
   - Create utility functions for UUID handling
   - Implement date/time utilities

### Phase 3: ResearchBrain Migration (Week 3)
1. **Update Core Models**
   - Refactor KnowledgeNode to extend TaggableEntity
   - Update Paper, Note, Experiment to use BaseEntity
   - Migrate Grant, Collaboration models

2. **Replace Storage Layer**
   - Replace custom storage with EntityStorage
   - Update file paths and naming
   - Migrate existing data

3. **Update Dependencies**
   - Update imports to use common library
   - Remove duplicate code
   - Update tests

### Phase 4: ProductMind Migration (Week 4)
1. **Update Models**
   - Refactor Decision, Feedback, etc. to use BaseEntity
   - Implement shared interfaces
   - Update field definitions

2. **Replace Storage Patterns**
   - Update DecisionRegistry to use EntityStorage
   - Migrate FeedbackAnalysisEngine storage
   - Update other managers

3. **Update Dependencies**
   - Update imports throughout package
   - Remove duplicate implementations
   - Update tests

### Phase 5: Testing and Optimization (Week 5)
1. **Comprehensive Testing**
   - Run all existing tests
   - Add integration tests
   - Performance testing

2. **Optimization**
   - Profile and optimize common operations
   - Improve caching strategies
   - Optimize search performance

3. **Documentation**
   - Update README files
   - Create migration guide
   - Document API changes

## Migration Details by Package

### ResearchBrain Package Migration

#### Models to Migrate
- `KnowledgeNode` → Extends `TaggableEntity`
- `Paper` → Extends `BaseEntity`, adds citation fields
- `Note` → Extends `TaggableEntity`
- `Experiment` → Extends `BaseEntity`, adds status from common enums
- `Grant` → Extends `BaseEntity`, uses common Priority enum
- `Collaboration` → Extends `LinkableEntity`

#### Storage Migration
- Replace `ResearchBrainStorage` with `EntityStorage[T]`
- Update file naming to use common patterns
- Migrate cache to common caching system

#### Function Migration
- Move citation formatting to domain-specific module
- Keep experiment templates as domain-specific
- Use common search for all text queries

### ProductMind Package Migration

#### Models to Migrate
- `Decision` → Extends `BaseEntity`, uses common Priority
- `Feedback` → Extends `TaggableEntity`
- `RoadmapItem` → Extends `BaseEntity`, uses common Priority
- `Stakeholder` → Extends `BaseEntity`
- `CompetitorInsight` → Extends `TaggableEntity`

#### Manager Migration
- `DecisionRegistry` → Implements `EntityManager[Decision]`
- `FeedbackAnalysisEngine` → Uses common analysis utilities
- `PrioritizationFramework` → Uses common Priority enum
- `StakeholderInsightsManager` → Implements `EntityManager[Stakeholder]`
- `CompetitiveAnalysisSystem` → Uses common search engine

## Interface Contracts

### Storage Interface
All storage operations must maintain these contracts:
- Thread-safe operations
- Atomic writes
- Consistent error handling
- Backup compatibility

### Model Interface
All models must:
- Extend appropriate base class
- Implement required validators
- Support JSON serialization
- Maintain backward compatibility

### Manager Interface
All managers must:
- Implement EntityManager interface
- Support batch operations
- Provide search functionality
- Handle errors consistently

## Performance Considerations

### Caching Strategy
- In-memory cache for frequently accessed items
- LRU eviction for cache management
- Cache invalidation on updates
- Configurable cache sizes

### Search Optimization
- Pre-built search indices
- Incremental index updates
- Query result caching
- Field-specific indexing

### Storage Optimization
- Lazy loading for large datasets
- Batch operations for bulk updates
- Compressed storage for backups
- Efficient serialization

## Testing Strategy

### Unit Tests
- Test each common component independently
- Mock dependencies
- Test edge cases and error conditions
- Ensure thread safety

### Integration Tests
- Test interaction between common and domain modules
- Verify data migration
- Test backup/restore functionality
- Validate search accuracy

### Regression Tests
- Run all existing package tests
- Ensure no functionality is lost
- Verify performance is maintained
- Check API compatibility

## Risk Mitigation

### Data Migration Risks
- Create automated migration scripts
- Implement rollback functionality
- Validate data integrity after migration
- Keep backups of original data

### API Compatibility Risks
- Maintain wrapper functions during transition
- Provide deprecation warnings
- Document all breaking changes
- Create migration guides

### Performance Risks
- Profile before and after migration
- Optimize critical paths
- Monitor memory usage
- Implement performance tests

## Success Metrics

1. **Code Reduction**: Achieve 60-70% reduction in duplicate code
2. **Test Coverage**: Maintain 100% test pass rate
3. **Performance**: No degradation in operation speed
4. **Maintainability**: Single source of truth for common functionality
5. **Extensibility**: Easy addition of new persona packages

## Implementation Timeline

- **Week 1**: Core infrastructure and base models
- **Week 2**: Shared functionality and utilities
- **Week 3**: ResearchBrain migration
- **Week 4**: ProductMind migration
- **Week 5**: Testing, optimization, and documentation

## Conclusion

This migration plan provides a systematic approach to creating a unified library that eliminates code duplication while maintaining all existing functionality. The phased approach ensures minimal disruption and allows for thorough testing at each stage.