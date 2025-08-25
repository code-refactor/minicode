# Unified Backup System Architecture Plan

## Executive Summary

This document outlines the architecture for creating a unified library that consolidates common functionality from the creative_vault and gamevault implementations while preserving their domain-specific capabilities. The unified library provides a shared foundation for incremental backup, storage management, versioning, and data processing while allowing persona-specific extensions.

## Architecture Overview

### Design Principles

1. **Separation of Concerns**: Core functionality separated from domain-specific logic
2. **Interface-Based Design**: Clear contracts between components via abstract base classes
3. **Extensibility**: Plugin architecture for file type handlers and processing strategies
4. **Performance**: Efficient storage through content-addressed systems and deduplication
5. **Testability**: Dependency injection and mockable interfaces throughout

### System Architecture

```
unified/
├── common/                         # Shared library
│   ├── core/                      # Core abstractions and interfaces
│   ├── storage/                   # Content-addressed storage system
│   ├── versioning/                # Version management and DAG
│   ├── chunking/                  # Chunking strategies
│   ├── compression/               # Compression utilities
│   ├── models/                    # Shared data models
│   └── utils/                     # Common utilities
├── creative_vault/                # Digital artist persona
│   └── (refactored to use common)
└── gamevault/                     # Game developer persona
    └── (refactored to use common)
```

## Common Library Components

### 1. Core Abstractions (`common/core/`)

#### Base Interfaces
```python
# interfaces.py
class BackupEngine(ABC):
    """Base interface for backup operations"""
    @abstractmethod
    def initialize_repository(self, path: Path) -> None
    @abstractmethod
    def create_snapshot(self, source_path: Path) -> str
    @abstractmethod
    def restore_snapshot(self, snapshot_id: str, target_path: Path) -> None
    @abstractmethod
    def list_snapshots(self) -> List[SnapshotInfo]

class StorageBackend(ABC):
    """Base interface for storage operations"""
    @abstractmethod
    def store(self, data: bytes, key: str) -> str
    @abstractmethod
    def retrieve(self, key: str) -> bytes
    @abstractmethod
    def exists(self, key: str) -> bool
    @abstractmethod
    def delete(self, key: str) -> bool

class VersionManager(ABC):
    """Base interface for version management"""
    @abstractmethod
    def create_version(self, metadata: Dict) -> Version
    @abstractmethod
    def get_version(self, version_id: str) -> Version
    @abstractmethod
    def list_versions(self) -> List[Version]
    @abstractmethod
    def get_version_history(self, version_id: str) -> List[Version]
```

### 2. Storage System (`common/storage/`)

#### Content-Addressed Storage
```python
# content_store.py
class ContentAddressedStorage:
    """Hash-based storage with automatic deduplication"""
    def __init__(self, storage_backend: StorageBackend)
    def store_file(self, file_path: Path) -> str
    def store_data(self, data: bytes) -> str
    def retrieve_file(self, hash: str, target_path: Path) -> None
    def get_storage_stats(self) -> StorageStats

# deduplicator.py
class Deduplicator:
    """Manages deduplication with reference counting"""
    def __init__(self)
    def add_reference(self, hash: str, source: str) -> None
    def remove_reference(self, hash: str, source: str) -> bool
    def get_reference_count(self, hash: str) -> int
    def find_duplicates(self) -> Dict[str, List[str]]
```

### 3. Version Management (`common/versioning/`)

#### Version DAG Management
```python
# version_dag.py
class VersionDAG:
    """Directed acyclic graph for version relationships"""
    def __init__(self)
    def add_version(self, version: Version, parent_id: Optional[str]) -> None
    def get_lineage(self, version_id: str) -> List[Version]
    def find_common_ancestor(self, v1: str, v2: str) -> Optional[Version]
    def get_branches(self) -> Dict[str, List[Version]]

# snapshot.py
class SnapshotManager:
    """Manages backup snapshots"""
    def __init__(self, storage: ContentAddressedStorage)
    def create_snapshot(self, files: List[FileInfo]) -> Snapshot
    def restore_snapshot(self, snapshot: Snapshot, target: Path) -> None
    def diff_snapshots(self, s1: Snapshot, s2: Snapshot) -> SnapshotDiff
```

### 4. Chunking Strategies (`common/chunking/`)

#### Modular Chunking System
```python
# base.py
class ChunkingStrategy(ABC):
    """Base interface for chunking strategies"""
    @abstractmethod
    def chunk_data(self, data: bytes) -> List[Chunk]
    @abstractmethod
    def reassemble_chunks(self, chunks: List[Chunk]) -> bytes

# strategies.py
class FixedSizeChunker(ChunkingStrategy):
    """Fixed-size chunking for simple data"""
    
class RollingHashChunker(ChunkingStrategy):
    """Content-defined chunking using rolling hash"""
    
class DeltaChunker(ChunkingStrategy):
    """Delta-based chunking for versioned data"""

# factory.py
class ChunkerFactory:
    """Factory for selecting appropriate chunking strategy"""
    def get_chunker(self, file_type: str, config: ChunkConfig) -> ChunkingStrategy
```

### 5. Compression (`common/compression/`)

#### Compression Utilities
```python
# compressor.py
class CompressionManager:
    """Manages different compression algorithms"""
    def __init__(self, algorithm: str = "zstd")
    def compress(self, data: bytes, level: int = 3) -> bytes
    def decompress(self, data: bytes) -> bytes
    def estimate_ratio(self, data: bytes) -> float

# delta.py
class DeltaCompressor:
    """Binary delta compression for versioned files"""
    def create_delta(self, old: bytes, new: bytes) -> bytes
    def apply_delta(self, old: bytes, delta: bytes) -> bytes
    def is_delta_efficient(self, old: bytes, new: bytes) -> bool
```

### 6. Data Models (`common/models/`)

#### Shared Data Structures
```python
# file_info.py
@dataclass
class FileInfo:
    """Universal file metadata"""
    path: Path
    size: int
    modified_time: float
    hash: str
    content_type: str
    chunks: List[str] = field(default_factory=list)

# version.py
@dataclass
class Version:
    """Version metadata"""
    id: str
    timestamp: float
    parent_id: Optional[str]
    metadata: Dict[str, Any]
    snapshot_id: str
    tags: List[str] = field(default_factory=list)

# snapshot.py
@dataclass
class Snapshot:
    """Backup snapshot metadata"""
    id: str
    timestamp: float
    files: List[FileInfo]
    total_size: int
    file_count: int
    metadata: Dict[str, Any]
```

### 7. Utilities (`common/utils/`)

#### Common Utilities
```python
# hashing.py
def calculate_hash(data: bytes, algorithm: str = "sha256") -> str
def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str
def calculate_xxhash(data: bytes) -> str

# filesystem.py
def scan_directory(path: Path, patterns: List[str] = None) -> List[Path]
def get_file_info(path: Path) -> FileInfo
def ensure_directory(path: Path) -> None
def atomic_write(path: Path, data: bytes) -> None

# serialization.py
def save_json(data: Any, path: Path) -> None
def load_json(path: Path) -> Any
def serialize_model(model: BaseModel) -> Dict
def deserialize_model(data: Dict, model_class: Type[BaseModel]) -> BaseModel
```

## Persona-Specific Extensions

### Creative Vault Extensions

The creative_vault package will extend the common library with:

1. **Visual Diff Generator**: Image and 3D model comparison
2. **Timeline Manager**: Visual version browsing with thumbnails
3. **Element Extractor**: Layer and component extraction
4. **Asset Reference Tracker**: Project-asset dependency management
5. **Workspace Capture**: Application state preservation

### GameVault Extensions

The gamevault package will extend the common library with:

1. **Feedback System**: Build-feedback correlation
2. **Playtest Recorder**: Session capture and analysis
3. **Asset Optimizer**: Game-specific chunking and compression
4. **Milestone Manager**: Development phase tracking
5. **Platform Config**: Multi-platform configuration management

## Migration Strategy

### Phase 1: Common Library Implementation
1. Create core interfaces and abstractions
2. Implement storage and versioning systems
3. Add chunking and compression utilities
4. Define shared data models
5. Create common utilities

### Phase 2: Refactor Creative Vault
1. Replace storage backend with common implementation
2. Adapt backup engine to use common interfaces
3. Refactor utilities to use common functions
4. Update data models to extend common models
5. Preserve all domain-specific functionality

### Phase 3: Refactor GameVault
1. Replace storage and chunking with common implementation
2. Adapt backup engine to common interfaces
3. Refactor utilities to use common functions
4. Update models to extend common models
5. Preserve all domain-specific functionality

### Phase 4: Testing and Validation
1. Run all existing tests for both personas
2. Verify no functionality regression
3. Validate performance metrics
4. Generate test report

## Implementation Details

### Dependency Injection Pattern

All components will use dependency injection for flexibility:

```python
class UnifiedBackupEngine:
    def __init__(
        self,
        storage: StorageBackend,
        chunker_factory: ChunkerFactory,
        compressor: CompressionManager,
        version_manager: VersionManager
    ):
        self.storage = storage
        self.chunker_factory = chunker_factory
        self.compressor = compressor
        self.version_manager = version_manager
```

### Plugin Architecture

Support for extending functionality via plugins:

```python
class PluginRegistry:
    def register_handler(self, file_type: str, handler: FileHandler) -> None
    def get_handler(self, file_type: str) -> Optional[FileHandler]
    def list_handlers(self) -> Dict[str, FileHandler]
```

### Configuration Management

Unified configuration system with persona-specific overrides:

```python
class UnifiedConfig(BaseSettings):
    # Common settings
    storage_path: Path
    compression_level: int
    chunk_size: int
    
    # Extensible for personas
    extra_settings: Dict[str, Any] = {}
    
    class Config:
        env_prefix = "BACKUP_"
```

## Benefits of Unified Architecture

### Code Reduction
- **Storage Layer**: ~60% reduction through shared implementation
- **Utilities**: ~80% reduction in duplicated utility functions
- **Data Models**: ~50% reduction in model definitions
- **Testing**: Shared test fixtures and utilities

### Improved Maintainability
- Single source of truth for core functionality
- Consistent interfaces across personas
- Easier to add new features
- Simplified debugging and troubleshooting

### Performance Optimization
- Shared optimization efforts benefit all personas
- Consistent caching strategies
- Unified resource management
- Better memory utilization

### Extensibility
- Easy to add new personas
- Plugin architecture for file handlers
- Configurable strategies via factories
- Clean separation of concerns

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock dependencies using interfaces
- Verify contract compliance
- Test error handling paths

### Integration Tests
- Test component interactions
- Verify data flow between layers
- Test storage and retrieval
- Validate version management

### Persona Tests
- Run all existing persona tests
- Verify no regression in functionality
- Test persona-specific extensions
- Validate performance requirements

## Success Metrics

1. **All tests pass**: 100% of existing tests must pass
2. **Code reduction**: At least 40% reduction in duplicated code
3. **Performance**: No degradation in performance metrics
4. **Extensibility**: Clean addition of new features
5. **Maintainability**: Clear separation of concerns

## Next Steps

1. Implement common library components
2. Refactor creative_vault to use common library
3. Refactor gamevault to use common library
4. Run comprehensive test suite
5. Generate test report with pytest-json-report
6. Update documentation

This architecture provides a solid foundation for the unified backup system while preserving the unique capabilities of each persona implementation.