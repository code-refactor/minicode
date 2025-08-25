# GameVault - Incremental Backup System for Game Development

## Overview
A specialized incremental backup system designed for indie game developers who create frequent iterations with extensive playtesting feedback. The system enables tracking game builds alongside player data, efficiently managing large binary assets, and preserving development milestones while correlating player feedback with specific versions.

## Persona Description
Mateo creates indie games with frequent iterations and extensive playtesting feedback. He needs to track game builds alongside player feedback data to reference when making design decisions.

## Key Requirements
1. **Build-Feedback Correlation**: Implement a system that links player feedback data with the specific game versions that generated it. This capability allows Mateo to accurately connect player comments, bug reports, and analytics with the exact build that produced them, making it much easier to understand the context of feedback and address issues effectively.

2. **Asset Bundle Tracking**: Create specialized handling for large binary game resources that optimizes storage through intelligent chunking, deduplication, and delta compression. This feature dramatically reduces backup storage requirements for Mateo's game assets while ensuring complete recoverability of any version, even as these assets evolve throughout development.

3. **Playtesting Session Preservation**: Develop functionality to capture and store in-game states and player progression data alongside code and asset backups. This ensures that Mateo can reference not just the game builds but also specific player experiences within those builds, providing critical context for understanding how players interacted with different game versions.

4. **Development Milestone Snapshots**: Implement a system for marking significant progress points with comprehensive annotations and tags. This capability allows Mateo to maintain a clear history of his game's evolution with important versions like "first playable," "alpha," "beta," and feature releases explicitly marked for easy reference and potential rollback.

5. **Cross-platform Configuration Management**: Create a framework for backing up settings across multiple deployment targets (PC, mobile, console) while maintaining platform-specific differences. This ensures that Mateo can track how his game is configured for different platforms, making it easier to identify platform-specific issues and maintain consistency where appropriate.

## Technical Requirements

### Testability Requirements
- All components must have isolated unit tests with dependency injection for external systems
- Build-feedback correlation must be tested with simulated player data and build sequences
- Asset bundle handling must be verified with various game resource types and modifications
- Playtesting capture must be testable with standardized session data formats
- Milestone snapshots must be verified for completeness and annotation integrity
- Cross-platform configuration must be tested across multiple target environment specifications

### Performance Expectations
- The system must efficiently handle game projects up to 500GB with thousands of assets
- Build-feedback linking must process correlation data at a rate of at least 1000 records per minute
- Asset bundle tracking must achieve at least 70% storage reduction for iterative binary files
- Playtesting data capture must add less than 5% overhead to game performance during testing
- Milestone snapshots must complete within 5 minutes even for large projects
- Configuration comparison must identify platform-specific differences in under 10 seconds

### Integration Points
- Game engines (Unity, Unreal Engine, custom engines)
- Version control systems (Git, Perforce, Plastic SCM)
- Player analytics and feedback collection systems
- Build automation and continuous integration pipelines
- Asset management and bundling tools
- Platform-specific SDK and deployment systems

### Key Constraints
- The implementation must work across Windows, macOS, and Linux development environments
- All operations must be performant even with very large binary asset files
- The system must accommodate both text-based source files and binary game assets
- Storage formats must be efficient while maintaining perfect fidelity for game resources
- Processing must operate seamlessly with common game development workflows
- System must provide clear visualization of changes between game versions

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The core of this implementation centers on a Python library that provides:

1. **Incremental Backup Engine**: A core module handling game project change detection, efficient delta storage, and versioned backup creation with special handling for both source code and binary assets.

2. **Feedback Correlation System**: A sophisticated database that maintains relationships between specific game builds and all associated player feedback, analytics, and testing data.

3. **Asset Optimization Framework**: Specialized handling for game assets using content-aware chunking, delta compression, and deduplication optimized for common game file formats.

4. **Playtest Data Recorder**: Tools for capturing, indexing, and storing player progression, in-game states, and session information alongside the corresponding game builds.

5. **Milestone Management**: A flexible system for marking, annotating, and preserving important development points with comprehensive metadata and tagging capabilities.

6. **Platform Configuration Tracker**: Logic for managing and comparing game settings across different target platforms, identifying both common elements and platform-specific differences.

The system should be designed as a collection of Python modules with clear interfaces between components, allowing them to be used independently or as an integrated solution. All functionality should be accessible through a programmatic API that could be called by various game development tools (though implementing a UI is not part of this project).

## Testing Requirements

### Key Functionalities to Verify
- Build-feedback correlation with accurate relationship maintenance
- Asset bundle optimization with proper storage efficiency
- Playtesting data capture with complete session preservation
- Milestone snapshot creation with appropriate metadata
- Cross-platform configuration tracking with proper difference identification
- Project-wide version history with correct chronological ordering

### Critical User Scenarios
- Complete game development cycle from concept to release with milestone tracking
- Correlation of player feedback with specific gameplay mechanics across versions
- Recovery of precise game state from previous development iterations
- Storage optimization for projects with large texture and model assets
- Configuration management across PC, mobile, and console deployments
- Identification of changes that caused specific player feedback or issues

### Performance Benchmarks
- Initial backup of a 200GB game project completing in under 2 hours
- Incremental backup completing in under 10 minutes for typical daily changes
- Build-feedback correlation queries returning results in under 3 seconds
- Asset optimization achieving at least 4:1 storage reduction for typical binary changes
- Playtesting data recording adding less than 100ms overhead to game frame times
- Milestone snapshot creation processing at least 1GB/minute including verification

### Edge Cases and Error Conditions
- Handling of corrupted game builds or asset bundles
- Recovery from interrupted backups during large asset imports
- Proper functioning with proprietary or encrypted game assets
- Correct behavior with extremely large individual files (textures, audio, videos)
- Appropriate handling of third-party plugins and dependencies
- Graceful operation during rapid iteration cycles (multiple builds per day)

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
2. The system demonstrates effective correlation between builds and player feedback.
3. Asset bundle tracking achieves significant storage optimization for binary game resources.
4. Playtesting session data is properly captured and associated with game versions.
5. Development milestones are clearly marked and preserved with appropriate annotations.
6. Cross-platform configurations are properly managed with difference identification.
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