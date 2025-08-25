# SyncDB: In-Memory Database with Mobile Synchronization

## Overview
A specialized in-memory database designed for mobile application backends that efficiently manages data synchronization between server and client applications with intermittent connectivity. The system optimizes for minimal data transfer, handles conflict resolution, and supports evolving application requirements through schema migration.

## Persona Description
Miguel builds backend services for mobile applications with intermittent connectivity. He needs a database solution that can efficiently synchronize data between server and client-side storage while minimizing transfer size.

## Key Requirements

1. **Differential Sync Protocol**
   - Implementation of an efficient sync protocol that identifies and transfers only changed records since last synchronization
   - Support for record-level change tracking with timestamps or version vectors
   - Batched sync operations to minimize connection overhead
   - This feature is critical for Miguel's applications as mobile devices often have limited bandwidth and intermittent connectivity, making full data transfers impractical and expensive

2. **Conflict Resolution Strategies**
   - Customizable conflict resolution mechanisms for handling concurrent client-side modifications
   - Support for multiple resolution strategies (last-write-wins, custom merge functions, etc.)
   - Detailed conflict metadata tracking for auditability and debugging
   - Mobile applications often operate offline with local data changes that must be reconciled with server state when connectivity is restored, making conflict resolution essential for data integrity

3. **Type-Aware Payload Compression**
   - Customized compression algorithms for different data types (text, numeric, binary)
   - Configurable compression settings balancing CPU usage versus transfer size
   - Format-preserving compression that maintains data queryability
   - Minimizing data transfer sizes directly impacts application responsiveness, data usage costs, and battery life for Miguel's mobile application users

4. **Automatic Schema Migration**
   - Support for versioned schema changes that can be seamlessly propagated to clients
   - Backward compatibility mechanisms for supporting older client versions
   - Migration scripts that preserve existing data while adapting to new schemas
   - Mobile applications evolve over time with feature updates, requiring the database to handle schema changes without disrupting existing users or requiring reinstallation

5. **Battery-Aware Operation Modes**
   - Configurable performance profiles that adapt based on device power status
   - Deferred operations when operating on battery power
   - Batch processing options to minimize CPU and network wake cycles
   - Efficient resource usage is critical for mobile applications as excessive battery drain leads to poor user experience and app uninstallation

## Technical Requirements

### Testability Requirements
- Tests must validate correct synchronization under various network conditions
- Conflict resolution tests must cover all supported resolution strategies
- Schema migration tests must verify data integrity during version transitions
- Performance tests must measure data transfer sizes and compression efficiency

### Performance Expectations
- Sync operations should transfer less than 10% of full dataset size for typical incremental changes
- Compression should reduce payload size by at least 50% compared to JSON for typical mobile data
- Schema migrations should complete in under 5 seconds for databases up to 100MB
- Operations in battery-saving mode should use no more than 50% of the resources of standard mode

### Integration Points
- Clean API for mobile developers to integrate with iOS, Android, and cross-platform frameworks
- Support for standard data interchange formats (JSON, Protocol Buffers, etc.)
- Hooks for custom serialization and deserialization of complex objects
- Integration with standard authentication mechanisms for secure synchronization

### Key Constraints
- The implementation must use only Python standard library with no external dependencies
- All functionality must be testable without requiring actual mobile devices
- The solution must operate in memory with optional persistence for server-side storage
- The system must be resilient to unreliable network connections

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality

The system must provide the following core functionality:

1. **In-Memory Database Engine**
   - Implementation of an efficient in-memory data store with table definitions
   - Support for standard CRUD operations with transactional integrity
   - Query capabilities for flexible data access patterns

2. **Change Tracking System**
   - Mechanism to track and version individual record changes
   - Efficient storage of change history for synchronization
   - Pruning strategies to limit change history size

3. **Sync Protocol Implementation**
   - Algorithms to calculate and transmit data differences
   - Mechanisms for handling partial and interrupted syncs
   - State reconciliation logic between server and clients

4. **Conflict Management Framework**
   - Detection of conflicting changes between clients
   - Implementation of various resolution strategies
   - Audit trail for conflict resolution decisions

5. **Schema Version Management**
   - Schema versioning and compatibility checking
   - Data migration utilities for schema evolution
   - Backward compatibility layers for supporting multiple client versions

## Testing Requirements

### Key Functionalities to Verify
- Correct synchronization of data changes between server and simulated clients
- Proper resolution of conflicts based on configured strategies
- Efficient compression of different data types
- Successful schema migration with data preservation
- Correct operation in different power-saving modes

### Critical User Scenarios
- Initial sync of a large dataset to a new client
- Incremental sync after small changes on both server and client
- Handling of concurrent modifications causing conflicts
- Sync after client has been offline for extended periods
- Schema evolution with active clients on multiple versions

### Performance Benchmarks
- Sync payload size must be at least 90% smaller than full data transfer for typical incremental changes
- Compression must achieve at least 50% size reduction for common mobile data types
- Complete sync operation must finish in under 3 seconds for datasets up to 10MB
- Battery-saving mode must reduce CPU usage by at least 50% compared to standard mode
- Schema migrations must preserve 100% of compatible data

### Edge Cases and Error Conditions
- Behavior during interrupted synchronization
- Handling of incompatible schema changes
- Recovery from corrupted client or server data
- Performance with extremely large change sets
- Operation when storage limits are reached

### Required Test Coverage Metrics
- Minimum 90% code coverage across all modules
- 100% coverage of sync protocol and conflict resolution code
- All error recovery paths must be tested
- Performance tests must cover all sync scenarios
- Battery efficiency must be measurable in automated tests

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

The implementation will be considered successful if:

1. Data synchronization occurs with minimal transfer size compared to full data sync
2. Conflicts are correctly identified and resolved according to configured strategies
3. Schema migrations preserve data integrity while enabling application evolution
4. Battery-aware modes demonstrably reduce resource usage
5. All functionality works correctly under simulated poor network conditions

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Development Setup

To set up the development environment:

1. Clone the repository and navigate to the project directory
2. Create a virtual environment using:
   ```
   uv venv
   ```
3. Activate the virtual environment:
   ```
   source .venv/bin/activate
   ```
4. Install the project in development mode:
   ```
   uv pip install -e .
   ```
5. Run tests with:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

CRITICAL REMINDER: Generating and providing the pytest_results.json file is a MANDATORY requirement for project completion.