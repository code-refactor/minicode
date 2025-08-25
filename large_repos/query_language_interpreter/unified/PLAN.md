# Unified Query Language Interpreter - Architecture Plan

## Executive Summary

This document outlines the architecture for unifying two persona-specific query language interpreter implementations (privacy_query_interpreter and legal_discovery_interpreter) into a shared common library. The unified architecture maintains backward compatibility while eliminating code duplication and providing a flexible, extensible framework.

## Core Architecture Components

### 1. Common Core Library Structure

```
common/
├── core/
│   ├── __init__.py
│   ├── base_models.py       # Base data models (Document, Query, Result)
│   ├── query_parser.py      # Common query parsing logic
│   ├── query_engine.py      # Base query engine interface
│   ├── execution.py         # Query execution framework
│   ├── operators.py         # Common query operators and enums
│   └── exceptions.py        # Common exception classes
├── services/
│   ├── __init__.py
│   ├── base_services.py     # Abstract service interfaces
│   ├── detector.py          # Base detector service (PII/Privilege)
│   ├── enforcer.py          # Base enforcement service
│   └── registry.py          # Service registry for plugins
├── utils/
│   ├── __init__.py
│   ├── validation.py        # Input validation utilities
│   ├── formatting.py        # Result formatting utilities
│   └── logging.py           # Logging utilities
└── plugins/
    ├── __init__.py
    └── loader.py            # Plugin loading mechanism
```

### 2. Core Component Responsibilities

#### 2.1 Base Models (`base_models.py`)

**Unified Data Models:**
```python
class BaseDocument(BaseModel):
    """Base document/data source abstraction"""
    id: str
    metadata: Dict[str, Any]
    content: Any  # Can be text, DataFrame, etc.
    document_type: str
    
class QueryClause(BaseModel):
    """Base query clause"""
    clause_type: str
    operator: Optional[str]
    parameters: Dict[str, Any]
    
class QueryResult(BaseModel):
    """Unified query result"""
    query_id: str
    status: str
    execution_time_ms: int
    data: Any
    metadata: Dict[str, Any]
    persona_specific: Dict[str, Any]
```

#### 2.2 Query Parser (`query_parser.py`)

**Common Parsing Interface:**
```python
class BaseQueryParser:
    def parse(self, query_string: str) -> ParsedQuery
    def validate_syntax(self, query_string: str) -> bool
    def extract_clauses(self, parsed: ParsedQuery) -> List[QueryClause]
```

#### 2.3 Query Engine (`query_engine.py`)

**Unified Engine Interface:**
```python
class BaseQueryEngine(ABC):
    def __init__(self, config: EngineConfig):
        self.services = ServiceRegistry()
        self.data_sources = {}
        
    @abstractmethod
    def execute_query(self, query: Union[str, Query]) -> QueryResult
    
    def add_data_source(self, name: str, source: DataSource) -> None
    def register_service(self, service_type: str, service: BaseService) -> None
```

#### 2.4 Execution Framework (`execution.py`)

**Common Execution Pipeline:**
```python
class QueryExecutor:
    def execute(self, query: Query, context: ExecutionContext) -> QueryResult:
        # 1. Pre-execution hooks (validation, policy checks)
        # 2. Clause-by-clause execution
        # 3. Result aggregation
        # 4. Post-execution hooks (anonymization, filtering)
        # 5. Result formatting
```

### 3. Service Architecture

#### 3.1 Service Interfaces

```python
class BaseDetectorService(ABC):
    """Interface for detection services (PII, Privilege, etc.)"""
    @abstractmethod
    def detect(self, content: Any, config: Dict) -> List[Detection]
    
class BaseEnforcerService(ABC):
    """Interface for enforcement services"""
    @abstractmethod
    def enforce(self, query: Query, context: Context) -> EnforcementResult
    
class BaseAnalyzerService(ABC):
    """Interface for analysis services"""
    @abstractmethod
    def analyze(self, data: Any, params: Dict) -> AnalysisResult
```

#### 3.2 Service Registry

```python
class ServiceRegistry:
    def register(self, service_type: str, service: BaseService)
    def get_service(self, service_type: str) -> Optional[BaseService]
    def list_services(self) -> Dict[str, List[str]]
```

### 4. Persona-Specific Extensions

#### 4.1 Privacy Query Interpreter Migration

```python
# privacy_query_interpreter/engine.py
from common.core import BaseQueryEngine, QueryResult
from common.services import ServiceRegistry

class PrivacyQueryEngine(BaseQueryEngine):
    def __init__(self):
        super().__init__(PrivacyConfig())
        # Register privacy-specific services
        self.services.register("detector", PIIDetector())
        self.services.register("anonymizer", DataAnonymizer())
        self.services.register("enforcer", PolicyEnforcer())
        
    def execute_query(self, query: Union[str, Query]) -> QueryResult:
        # Use common execution framework with privacy-specific hooks
        result = super().execute_query(query)
        # Apply privacy-specific transformations
        return self._apply_privacy_filters(result)
```

#### 4.2 Legal Discovery Interpreter Migration

```python
# legal_discovery_interpreter/core/interpreter.py
from common.core import BaseQueryEngine, QueryResult
from common.services import ServiceRegistry

class LegalDiscoveryInterpreter(BaseQueryEngine):
    def __init__(self):
        super().__init__(LegalConfig())
        # Register legal-specific services
        self.services.register("detector", PrivilegeDetector())
        self.services.register("analyzer", CommunicationAnalyzer())
        self.services.register("ontology", OntologyService())
        
    def execute_query(self, query: Union[str, Query]) -> QueryResult:
        # Use common execution framework with legal-specific hooks
        result = super().execute_query(query)
        # Apply legal-specific enrichments
        return self._apply_legal_analysis(result)
```

### 5. Migration Strategy

#### Phase 1: Implement Common Core (Days 1-2)
1. Create base models and interfaces
2. Implement common query parsing logic
3. Build execution framework
4. Set up service registry

#### Phase 2: Extract Common Functionality (Days 2-3)
1. Identify and extract common utilities
2. Create shared validation logic
3. Implement common operators and enums
4. Build result formatting utilities

#### Phase 3: Migrate Privacy Query Interpreter (Day 3)
1. Extend base engine with privacy-specific logic
2. Adapt existing services to common interfaces
3. Update imports to use common library
4. Ensure all privacy tests pass

#### Phase 4: Migrate Legal Discovery Interpreter (Day 4)
1. Extend base engine with legal-specific logic
2. Adapt existing services to common interfaces
3. Update imports to use common library
4. Ensure all legal tests pass

#### Phase 5: Integration Testing (Day 5)
1. Run full test suite
2. Performance validation
3. Documentation updates
4. Final refactoring

### 6. Extension Points

The architecture provides several extension points for persona-specific functionality:

1. **Custom Query Clauses**: Personas can define additional clause types
2. **Service Plugins**: New services can be registered dynamically
3. **Execution Hooks**: Pre/post execution hooks for custom logic
4. **Result Transformers**: Custom result formatting and filtering
5. **Configuration**: Persona-specific behavior via configuration

### 7. Configuration System

```python
class EngineConfig(BaseModel):
    """Base configuration for query engines"""
    max_results: int = 1000
    timeout_seconds: int = 30
    enable_caching: bool = True
    services: List[ServiceConfig] = []
    
class PrivacyConfig(EngineConfig):
    """Privacy-specific configuration"""
    anonymization_level: str = "medium"
    pii_detection_enabled: bool = True
    data_minimization: bool = True
    
class LegalConfig(EngineConfig):
    """Legal-specific configuration"""
    privilege_detection_enabled: bool = True
    communication_analysis: bool = True
    temporal_analysis: bool = True
```

### 8. Benefits of Unified Architecture

1. **Code Reduction**: ~40-50% reduction in duplicated code
2. **Maintainability**: Single source of truth for core functionality
3. **Extensibility**: Easy to add new personas or features
4. **Testing**: Shared test utilities and fixtures
5. **Performance**: Optimized common execution path

### 9. Backward Compatibility

The refactored implementations maintain 100% backward compatibility:
- All existing public APIs preserved
- Test signatures unchanged
- Import paths updated transparently
- Existing configurations still work

### 10. Future Enhancements

This architecture enables future enhancements:
1. Additional persona implementations
2. Plugin marketplace for services
3. Performance optimizations in common layer
4. Shared caching and resource pooling
5. Unified monitoring and metrics

## Implementation Checklist

- [ ] Create common/core base models
- [ ] Implement query parser base class
- [ ] Build query engine interface
- [ ] Create execution framework
- [ ] Implement service registry
- [ ] Extract common utilities
- [ ] Migrate privacy_query_interpreter
- [ ] Migrate legal_discovery_interpreter
- [ ] Run all tests
- [ ] Update documentation
- [ ] Performance validation
- [ ] Generate test report

## Success Metrics

1. All existing tests pass without modification
2. Code duplication reduced by >40%
3. Performance equal or better than original
4. Clean separation of concerns
5. Easy to understand and extend