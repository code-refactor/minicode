# Instructions for Library Refactoring Project

This document provides instructions for creating a unified library from multiple persona-specific implementations.

## Objective

Your task is to create a shared unified library that can be used by all persona implementations by:
1. Identifying common functionality across implementations
2. Creating a shared library structure in the unified directory
3. Refactoring each persona's implementation to use the unified library
4. Ensuring all tests pass for each persona

## Rules and Constraints

### What You Can Modify
- **Unified Library (`common/`)**: You can create, modify, or delete any files in this directory.
- **Persona packages**: You can modify the persona implementation files to use the unified library `common`.
- **PLAN.md**: Please put your plan for refactoring here. This should include both the new `common` library as well as migrating the perona packages to use `common`.
- **README.md**: Please update the README as you go.

### What You Cannot Modify
- **Test Files**: All test files are considered ground truth and must not be modified.
- **External Dependencies**: The unified library must use only the Python standard library unless otherwise specified.

## Project Structure

The unified library should have the following structure:
```
./
├── common/                        # Common functionality across all implementations
│   └── core/                      # Core data structures and algorithms
├── <package_name_1>/              # First persona implementation
│   └── ...                        # Preserve original package structure
├── <package_name_2>/              # Second persona implementation
│   └── ...                        # Preserve original package structure
├── tests/                         # Tests directory
│   ├── <persona_1>/               # Tests for first persona implementation
│   └── <persona_2>/               # Tests for second persona implementation
├── INSTRUCTIONS_<persona_1>.md    # Original instructions for first persona
├── INSTRUCTIONS_<persona_2>.md    # Original instructions for second persona
├── PLAN.md                        # Architecture and design plan
├── README.md                      # Project documentation
├── conftest.py                    # Pytest configuration
├── pyproject.toml                 # Project configuration
└── setup.py                       # Installation script
```

## Task Steps

### 1. Analyze Implementations

Begin by examining all persona implementations to identify common patterns:
- Look for similar data structures, algorithms, and utility functions
- Note common interfaces and abstractions
- Identify domain-specific extensions and customizations
- Map the core functionality that can be shared across implementations

### 2. Design and Document Architecture

Create a detailed architecture plan in `PLAN.md` that outlines:
- Core components and their responsibilities
- Interface definitions and abstractions
- Extension points for persona-specific functionality
- Relationship between components
- Migration strategy for each implementation

### 3. Implement Common Library

Implement the core shared functionality in the `common` package:
- Create modular, reusable components
- Design clean interfaces that can be extended
- Implement shared data structures and algorithms
- Provide utility functions used across implementations
- Document code clearly with docstrings and comments

You can import from the common library in all packages using:
```python
from common import core
from common.core import some_function
```

### 4. Implement Persona-Specific Extensions

For each persona implementation:
1. Preserve the original package name and structure
2. Refactor the existing code to use the new `common` library
3. Utilize the common library components where possible
4. Ensure backward compatibility with existing tests
YOU MUST REFACTOR THE PERSONA LIBRARIES TO USE `common`

### 5. Integration and Testing

For EVERY persona implementation:
1. Update import paths to use the unified library
2. Add the unified library as a dependency
3. Run all tests to ensure functionality is preserved
4. Verify performance meets or exceeds original implementation

Test the unified and persona libraries using pytest:
```bash
pytest tests/ --json-report --json-report-file=report.json --continue-on-collection-errors
```
Note that this will run all persona tests, as they are in `tests/{persona}`.

YOU MUST RUN THE TESTS AND RECORD THE OUTPUT.

## Tips for Success

1. **Focus on Common Patterns**: Prioritize implementing components that can be used across all implementations.

2. **Use Proper Abstraction**: Create clear interfaces that allow for persona-specific customization.

3. **Preserve Original Behavior**: The refactored implementations must behave exactly like the originals.

4. **Incremental Testing**: Test continuously as you refactor to catch issues early.

5. **Document Design Decisions**: Keep thorough notes in PLAN.md about architectural decisions.

COMPLETE THE `common` LIBRARY AND FULLY MIGRATE THE PERSONA PACKAGES.

## Evaluation Criteria

Your solution will be evaluated based on:

1. **Correctness**: All tests for all implementations must pass.
2. **Code Reduction**: Minimization of code duplication across implementations.
3. **Architecture Quality**: Clean separation of concerns and appropriate abstractions.
4. **Performance**: The unified library must maintain or improve performance.
5. **Completeness**: All requirements from all personas must be satisfied.

## Development Setup

To set up the development environment:

1. Install the unified library in development mode:
   ```bash
   pip install -e .
   ```

2. Run tests with:
   ```bash
   pytest tests/ --json-report --json-report-file=report.json --continue-on-collection-errors
   ```
   or just
   ```bash
   pytest
   ```
   if debugging

CRITICAL REMINDER: Generating and providing the report.json file is a MANDATORY requirement for project completion.
