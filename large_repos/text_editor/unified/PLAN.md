# Unified Text Editor Library Architecture Plan

## Overview

This document outlines the architecture for creating a unified library from the two persona-specific text editor implementations:
1. **text_editor** (student persona) - focuses on coding practice, interviews, and learning
2. **writer_text_editor** (writer persona) - focuses on document writing, narrative tracking, and revisions

## Common Functionality Identified

### Core Components (Both Implementations Need)

1. **Text Buffer Management**
   - Basic text storage as lines
   - Content insertion/deletion/replacement
   - Line and column-based operations
   
2. **Cursor/Navigation**
   - Position tracking (line, column)
   - Movement operations (up/down/left/right)
   - Buffer start/end navigation
   
3. **History/Undo-Redo**
   - Operation tracking
   - Undo/redo stack management
   - Operation reversal

4. **Document Structure**
   - Hierarchical organization (sections/segments)
   - Content management
   - Metadata storage

5. **File Operations**
   - Reading/writing files
   - Format support
   - Path management

## Architecture Design

### Common Library Structure (`common/`)

```
common/
├── __init__.py
└── core/
    ├── __init__.py
    ├── buffer.py          # Unified text buffer implementation
    ├── cursor.py          # Unified cursor/position management
    ├── history.py         # Unified history/undo-redo system
    ├── document.py        # Base document model
    ├── file_manager.py    # Unified file operations
    ├── models.py          # Common data models (BaseModel extensions)
    └── utils.py           # Shared utility functions
```

### Component Specifications

#### 1. Buffer Component (`buffer.py`)
- **BaseBuffer**: Abstract base class for text storage
- **TextBuffer**: Line-based text buffer (from text_editor)
- **SegmentedBuffer**: Segment-based buffer for structured documents

#### 2. Cursor Component (`cursor.py`)
- **Position**: Base position model (line, column)
- **Cursor**: Basic cursor with movement operations
- **NavigationCursor**: Extended cursor with non-linear navigation support

#### 3. History Component (`history.py`)
- **Operation**: Base operation model
- **EditOperation**: Text editing operation (insert/delete/replace)
- **History**: Undo/redo stack management
- **RevisionHistory**: Extended history with revision support

#### 4. Document Component (`document.py`)
- **BaseDocument**: Abstract document interface
- **Section**: Document section model
- **TextSegment**: Text segment within sections
- **Document**: Full document with sections and metadata

#### 5. File Manager Component (`file_manager.py`)
- **FileManager**: Unified file I/O operations
- **FileFormat**: Enum for supported formats
- **FormatHandler**: Abstract handler for different formats

#### 6. Common Models (`models.py`)
- **BaseModel**: Extended Pydantic BaseModel with common functionality
- **Metadata**: Standard metadata structure
- **Range**: Text range specification (start/end positions)

## Migration Strategy

### Phase 1: Create Common Library
1. Extract and generalize buffer management from text_editor
2. Create unified cursor/position system
3. Merge history implementations (undo/redo + revisions)
4. Design flexible document model supporting both use cases
5. Implement unified file manager

### Phase 2: Refactor text_editor (Student)
1. Replace `text_editor.core.buffer` with `common.core.buffer`
2. Replace `text_editor.core.cursor` with `common.core.cursor`
3. Replace `text_editor.core.history` with `common.core.history`
4. Adapt `text_editor.core.editor` to use common components
5. Update `text_editor.core.file_manager` to use common file operations
6. Keep persona-specific features (interview, learning, study) as extensions

### Phase 3: Refactor writer_text_editor (Writer)
1. Replace document model with common document structure
2. Adapt navigation system to use common cursor
3. Integrate revision system with common history
4. Map client operations to common buffer operations
5. Keep persona-specific features (narrative, focus, statistics) as extensions

## Interface Definitions

### Buffer Interface
```python
class IBuffer(Protocol):
    def get_content(self) -> str: ...
    def insert_text(self, position: Position, text: str) -> None: ...
    def delete_text(self, start: Position, end: Position) -> str: ...
    def replace_text(self, start: Position, end: Position, text: str) -> str: ...
```

### Document Interface
```python
class IDocument(Protocol):
    def get_content(self) -> str: ...
    def add_section(self, title: str) -> Section: ...
    def get_section(self, index: int) -> Optional[Section]: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
```

### History Interface
```python
class IHistory(Protocol):
    def record_operation(self, operation: Operation) -> None: ...
    def undo(self) -> Optional[Operation]: ...
    def redo(self) -> Optional[Operation]: ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
```

## Extension Points

### For text_editor (Student)
- Custom features remain in `text_editor/` package
- Interview problems and solutions
- Learning progress tracking
- Study session management
- Code-specific operations

### For writer_text_editor (Writer)
- Custom features remain in `writer_text_editor/` package
- Narrative element tracking
- Focus mode and sessions
- Writing statistics
- Non-linear navigation views

## Implementation Order

1. **Core Models and Utils** - Basic data structures
2. **Buffer System** - Text storage and manipulation
3. **Cursor/Position** - Navigation and position tracking
4. **History System** - Undo/redo and revisions
5. **Document Model** - Hierarchical document structure
6. **File Manager** - I/O operations
7. **Persona Adapters** - Integration layers for each persona

## Testing Strategy

1. Ensure all existing tests pass without modification
2. Create integration tests for common components
3. Verify performance meets or exceeds original
4. Test cross-persona compatibility where applicable

## Success Metrics

1. **Code Reduction**: Target 40-50% reduction in duplicate code
2. **Test Coverage**: Maintain 100% test pass rate
3. **Performance**: No regression in operation speed
4. **Modularity**: Clean separation between common and persona-specific code
5. **Extensibility**: Easy to add new personas or features