# CreativeVault - Incremental Backup System for Digital Artists

## Overview
A specialized incremental backup system designed for digital artists who create complex project files with numerous iterations and dependencies. The system enables visual timeline tracking of creative works, selective restoration of specific elements, and intelligent handling of large asset libraries while preserving relationships between projects and reference materials.

## Persona Description
Sofia creates digital art for animation studios, working with complex project files and reference materials. She needs to track iterations of creative works while maintaining large texture and asset libraries.

## Key Requirements
1. **Visual Difference Comparison**: Implement an intelligent system that can visually represent changes between versions of image and 3D model files, allowing side-by-side comparison. This feature enables Sofia to quickly understand what changed between iterations, helping her track the creative evolution of her work and make informed decisions when restoring previous elements.

2. **Timeline-based Version Browsing**: Create an advanced version history system with thumbnail previews that visually represents the evolution of projects over time. This capability allows Sofia to navigate through the creative development history of any file, understanding the progression of her work and confidently selecting specific versions to reference or restore.

3. **Selective Element Restoration**: Develop functionality for extracting and restoring specific elements or layers from previous versions without losing recent changes to other components. This precision restoration capability enables Sofia to recover specific creative elements that were removed or altered, while preserving all the progress made on other aspects of the project.

4. **Asset Library Deduplication**: Implement specialized handling for creative asset libraries that understands references and linked files in projects, ensuring that shared assets are backed up efficiently while maintaining all relationships. This feature dramatically reduces storage requirements for Sofia's extensive texture and model libraries while ensuring all project dependencies remain intact.

5. **Workspace State Preservation**: Create a comprehensive system for capturing application layouts, tool configurations, and workspace states alongside creative files. This ensures that Sofia can restore not just her creative works but also the precise working environment in which they were created, enhancing productivity when revisiting projects.

## Technical Requirements

### Testability Requirements
- All components must have isolated unit tests with dependency injection for external systems
- Visual difference algorithms must be tested with standardized image and model datasets
- Timeline representation must be verified with various project evolution patterns
- Selective restoration must be tested with complex layered file formats
- Asset reference handling must be verified with various project-reference relationships
- Workspace state capture must be tested across multiple creative application formats

### Performance Expectations
- The system must efficiently handle projects with thousands of linked assets
- Visual difference generation must complete in under 5 seconds for typical image files
- Timeline data processing must handle projects with 500+ saved versions
- Selective restoration must extract components in under 10 seconds even from large files
- Asset library deduplication must achieve at least 60% storage reduction for typical libraries
- Workspace state capture must add less than 2 seconds overhead to project save operations

### Integration Points
- Creative application file formats (Adobe Creative Cloud, Autodesk, Blender, etc.)
- Image and 3D model processing libraries
- Asset management systems and digital asset managers (DAMs)
- Rendering engines and output processors
- Version control systems with binary file support
- Cloud storage providers for off-site backup

### Key Constraints
- The implementation must work across macOS and Windows platforms (primary artist workstations)
- All operations must be non-destructive with original files always preserved
- The system must accommodate both small project files and very large asset libraries
- Storage formats must support high bit-depth color and precision 3D data without degradation
- Processing must be optimized to handle graphics-intensive files without excessive resource consumption
- System must operate efficiently on workstations also running resource-intensive creative applications

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The core of this implementation centers on a Python library that provides:

1. **Incremental Backup Engine**: A core module handling creative file change detection, efficient delta storage, and versioned backup creation with perfect fidelity for artistic content.

2. **Visual Diff Generator**: Sophisticated algorithms for creating visual representations of changes between versions of images, 3D models, and other visual assets with meaningful highlighting of differences.

3. **Creative Timeline Manager**: A specialized version history system that maintains visual thumbnails and metadata about project evolution, enabling intuitive navigation through creative iterations.

4. **Element Extraction Framework**: Tools for parsing complex file formats and selectively extracting components, layers, or elements for targeted restoration while preserving file integrity.

5. **Asset Reference Tracker**: Intelligence for identifying and maintaining relationships between project files and their dependent assets, ensuring efficient storage while preserving all links.

6. **Application Environment Capture**: Specialized adapters for extracting, storing, and restoring application states, workspace layouts, and tool configurations from major creative software.

The system should be designed as a collection of Python modules with clear interfaces between components, allowing them to be used independently or as an integrated solution. All functionality should be accessible through a programmatic API that could be called by various tools (though implementing a UI is not part of this project).

## Testing Requirements

### Key Functionalities to Verify
- Visual difference generation with accurate representation of creative changes
- Timeline creation with proper version ordering and preview generation
- Selective element extraction and restoration with file integrity maintenance
- Asset reference tracking with complete relationship preservation
- Workspace state capture and restoration across application restarts
- Storage efficiency compared to direct file versioning

### Critical User Scenarios
- Complete project iteration tracking for a complex animation sequence
- Recovery of specific creative elements from previous versions
- Migration of projects between workstations with environment preservation
- Storage optimization for large texture and model libraries
- Collaborative workflow with shared asset references
- Disaster recovery with complete project and environment restoration

### Performance Benchmarks
- Initial backup of a 50GB project folder completing in under 30 minutes
- Incremental backup completing in under 5 minutes for daily work sessions
- Visual difference generation at a rate of at least 5 comparison sets per minute
- Timeline processing handling 100+ versions in under 15 seconds
- Selective restoration completing in under 30 seconds even for complex files
- Storage efficiency achieving at least 5:1 ratio for version history through deduplication

### Edge Cases and Error Conditions
- Handling of corrupt or partially saved creative files
- Recovery from interrupted backups during render or export operations
- Proper functioning with extremely large individual files (high-res textures, complex scenes)
- Correct behavior with circular references between project components
- Appropriate handling of proprietary and evolving file formats
- Graceful operation when applications modify files during backup operations

### Required Test Coverage Metrics
- Minimum 90% line coverage for all functional components
- 100% coverage of all public APIs
- All error handling paths must be explicitly tested
- Performance tests must verify all stated benchmarks
- Integration tests must verify all external system interfaces

IMPORTANT:
- ALL functionality must be testable via pytest without any manual intervention
- Tests should verify behavior against requirements, not implementation details
- Tests should be designed to validate the WHAT (requirements) not the HOW (implementation)
- Tests should be comprehensive enough to verify all aspects of the requirements
- Tests should not assume or dictate specific implementation approaches
- REQUIRED: Tests must be run with pytest-json-report to generate a pytest_results.json file:
  ```
  pip install pytest-json-report
  pytest --json-report --json-report-file=pytest_results.json
  ```
- The pytest_results.json file must be included as proof that all tests pass

## Success Criteria
The implementation will be considered successful when:

1. All five key requirements are fully implemented and pass their respective test cases.
2. The system demonstrates effective visual difference comparison between creative file versions.
3. Timeline-based version browsing works correctly with appropriate previews and metadata.
4. Selective element restoration successfully extracts specific components while preserving file integrity.
5. Asset library deduplication achieves significant storage savings while maintaining all references.
6. Workspace state is properly captured and restored across application sessions.
7. All performance benchmarks are met under the specified load conditions.
8. Code quality meets professional standards with appropriate documentation.

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Development Setup
1. Use `uv venv` to setup a virtual environment. From within the project directory, activate it with `source .venv/bin/activate`.
2. Install the project with `uv pip install -e .`
3. CRITICAL: Before submitting, run the tests with pytest-json-report:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```
4. Verify that all tests pass and the pytest_results.json file has been generated.

REMINDER: Generating and providing the pytest_results.json file is a critical requirement for project completion.