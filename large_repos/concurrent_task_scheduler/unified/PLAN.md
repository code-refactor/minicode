# Unified Task Scheduler Library - Architecture and Migration Plan

## Executive Summary

This document outlines the architecture for a unified task scheduling library that consolidates common functionality from two persona implementations:
- **concurrent_task_scheduler**: Scientific computing scheduler for long-running simulations
- **render_farm_manager**: 3D rendering farm orchestrator

The refactoring will extract ~60-70% shared functionality into a common library while preserving domain-specific behaviors through extensible interfaces.

## Architecture Overview

### Design Principles

1. **Separation of Concerns**: Core scheduling logic separated from domain-specific requirements
2. **Interface-Based Design**: Clear contracts between components for testability
3. **Extensibility**: Plugin architecture for persona-specific customizations
4. **Zero External Dependencies**: Common library uses only Python standard library
5. **Backward Compatibility**: All existing tests must pass after migration

### Component Hierarchy

```
common/
├── core/                      # Fundamental data structures and interfaces
├── scheduling/                # Scheduling algorithms and priority management
├── resource_management/       # Resource allocation and reservation
├── dependency_tracking/       # Dependency graph and resolution
├── failure_handling/         # Failure detection and recovery
├── monitoring/               # Audit logging and performance tracking
└── utils/                    # Shared utility functions
```

## Common Library Components

### 1. Core Module (`common/core/`)

#### Purpose
Define fundamental data structures and interfaces used throughout the system.

#### Components

**models.py**
- `BaseJob`: Common job model with status, priority, dependencies
- `BaseNode`: Node representation with capabilities and status
- `Priority`: Unified priority enumeration
- `JobStatus`: Common job status states
- `NodeStatus`: Node availability states
- `ResourceType`: CPU, GPU, Memory, Storage types
- `ResourceRequirement`: Resource specification model

**interfaces.py**
- `SchedulerInterface`: Abstract base for all schedulers
- `ResourceManagerInterface`: Resource allocation contract
- `MonitoringInterface`: Logging and metrics contract
- `FailureHandlerInterface`: Failure detection/recovery contract

**result.py**
- `Result[T]`: Generic result wrapper for error handling
- `OperationResult`: Extended result with metadata
- Common error types and exceptions

### 2. Scheduling Module (`common/scheduling/`)

#### Purpose
Provide base scheduling functionality that can be extended by personas.

#### Components

**base_scheduler.py**
- `BaseScheduler`: Abstract scheduler with common logic
  - Priority calculation framework
  - Preemption decision logic
  - Job queue management
  - Schedule optimization patterns

**priority_manager.py**
- `PriorityManager`: Dynamic priority adjustment
  - Base priority calculation
  - Deadline-based urgency
  - Dependency priority inheritance
  - Starvation prevention

**queue_manager.py**
- `QueueManager`: Job queue operations
  - Multi-level priority queues
  - Queue reordering strategies
  - Batch processing support

### 3. Resource Management Module (`common/resource_management/`)

#### Purpose
Handle resource allocation, reservation, and optimization.

#### Components

**allocator.py**
- `ResourceAllocator`: Resource distribution algorithms
  - Best-fit allocation
  - Load balancing strategies
  - Resource fragmentation handling

**node_manager.py**
- `NodeManager`: Node lifecycle and capability management
  - Node registration/deregistration
  - Capability matching
  - Health monitoring integration

**reservation.py**
- `ReservationManager`: Time-based resource reservation
  - Reservation scheduling
  - Conflict detection
  - Overflow handling

**partitioner.py**
- `ResourcePartitioner`: Client/project resource partitioning
  - Guaranteed minimum allocation
  - Dynamic borrowing/lending
  - Fair-share algorithms

### 4. Dependency Tracking Module (`common/dependency_tracking/`)

#### Purpose
Manage job dependencies and workflow orchestration.

#### Components

**dependency_graph.py**
- `DependencyGraph`: DAG for dependency management
  - Circular dependency detection
  - Topological sorting
  - Status propagation

**dependency_resolver.py**
- `DependencyResolver`: Resolution and readiness checking
  - Ready job identification
  - Blocked job tracking
  - Dependency completion handling

### 5. Failure Handling Module (`common/failure_handling/`)

#### Purpose
Detect and recover from various failure scenarios.

#### Components

**failure_detector.py**
- `FailureDetector`: Identify system failures
  - Node health monitoring
  - Job progress tracking
  - Timeout detection

**recovery_strategies.py**
- `RecoveryStrategy`: Base recovery patterns
  - Job restart logic
  - Node migration
  - Checkpoint restoration hooks

**resilience_coordinator.py**
- `ResilienceCoordinator`: Coordinate recovery actions
  - Strategy selection
  - Recovery orchestration
  - Failure history tracking

### 6. Monitoring Module (`common/monitoring/`)

#### Purpose
Provide unified logging, metrics, and observability.

#### Components

**audit_logger.py**
- `AuditLogger`: Structured event logging
  - Event recording
  - Query interfaces
  - Compliance support

**performance_monitor.py**
- `PerformanceMonitor`: Performance tracking
  - Operation timing
  - Resource utilization metrics
  - Throughput measurement

**metrics_collector.py**
- `MetricsCollector`: System-wide metrics
  - Job statistics
  - Node utilization
  - Failure rates

### 7. Utilities Module (`common/utils/`)

#### Purpose
Shared utility functions used across components.

#### Components

**time_utils.py**
- `TimeRange`: Time interval operations
- Date/time helpers
- Duration calculations

**id_generation.py**
- Unique ID generation
- ID formatting utilities

**data_structures.py**
- Common data structure helpers
- Collection utilities

## Migration Strategy

### Phase 1: Common Library Implementation

1. **Create core models and interfaces**
   - Extract common job/node models
   - Define standard interfaces
   - Implement Result pattern

2. **Build scheduling foundation**
   - Implement BaseScheduler
   - Create PriorityManager
   - Add QueueManager

3. **Add resource management**
   - Implement ResourceAllocator
   - Create NodeManager
   - Add reservation support

4. **Implement support modules**
   - Add dependency tracking
   - Create failure handling
   - Build monitoring components

### Phase 2: Scientific Computing Migration

1. **Update imports**
   ```python
   # Before
   from concurrent_task_scheduler.models import Simulation
   
   # After
   from common.core.models import BaseJob
   from concurrent_task_scheduler.models import Simulation
   ```

2. **Extend base classes**
   ```python
   class Simulation(BaseJob):
       # Add scientific-specific fields
       checkpoint_frequency: timedelta
       resource_forecast: ResourceForecast
   ```

3. **Customize schedulers**
   ```python
   class ScientificScheduler(BaseScheduler):
       def calculate_priority(self, job: Simulation) -> float:
           base_priority = super().calculate_priority(job)
           # Add scientific-specific adjustments
           return base_priority * self.research_impact_factor(job)
   ```

4. **Preserve specialized features**
   - Keep checkpoint management
   - Maintain resource forecasting
   - Preserve scenario evaluation

### Phase 3: Render Farm Migration

1. **Update models**
   ```python
   class RenderJob(BaseJob):
       # Add rendering-specific fields
       frame_range: FrameRange
       quality_settings: QualitySettings
       client_id: str
   ```

2. **Extend schedulers**
   ```python
   class DeadlineScheduler(BaseScheduler):
       def schedule_jobs(self, jobs, nodes):
           # Use base scheduling
           schedule = super().schedule_jobs(jobs, nodes)
           # Apply deadline-specific logic
           return self.optimize_for_deadlines(schedule)
   ```

3. **Customize resource management**
   ```python
   class RenderResourceManager(ResourceAllocator):
       def allocate_resources(self, jobs, nodes):
           # Use base allocation
           allocation = super().allocate_resources(jobs, nodes)
           # Apply node specialization
           return self.match_specialized_nodes(allocation)
   ```

4. **Maintain specialized features**
   - Keep progressive rendering
   - Preserve energy optimization
   - Maintain node specialization

### Phase 4: Integration Testing

1. **Run existing tests**
   ```bash
   pytest tests/scientific_computing/ -v
   pytest tests/render_farm_manager/ -v
   ```

2. **Verify performance**
   - Ensure no performance regression
   - Validate resource utilization
   - Check scheduling efficiency

3. **Generate test report**
   ```bash
   pytest tests/ --json-report --json-report-file=report.json
   ```

## Implementation Order

### Priority 1: Core Foundation (Week 1)
- [ ] Core models
- [ ] Base interfaces
- [ ] Result pattern
- [ ] Basic utilities

### Priority 2: Scheduling System (Week 1-2)
- [ ] BaseScheduler
- [ ] PriorityManager
- [ ] QueueManager
- [ ] Basic preemption

### Priority 3: Resource Management (Week 2)
- [ ] ResourceAllocator
- [ ] NodeManager
- [ ] ReservationManager
- [ ] ResourcePartitioner

### Priority 4: Support Systems (Week 2-3)
- [ ] Dependency tracking
- [ ] Failure detection
- [ ] Recovery strategies
- [ ] Audit logging

### Priority 5: Migration (Week 3-4)
- [ ] Scientific computing migration
- [ ] Render farm migration
- [ ] Test verification
- [ ] Documentation update

## Testing Strategy

### Unit Tests for Common Library
- Test each component in isolation
- Mock interfaces for dependency injection
- Validate edge cases and error conditions

### Integration Tests
- Test component interactions
- Validate end-to-end workflows
- Ensure persona compatibility

### Regression Tests
- Run all existing persona tests
- Verify no functionality loss
- Check performance metrics

## Success Metrics

1. **Code Reduction**: >50% reduction in duplicated code
2. **Test Coverage**: >90% coverage for common library
3. **Performance**: No regression in scheduling efficiency
4. **Compatibility**: All existing tests pass
5. **Extensibility**: Easy to add new personas

## Risk Mitigation

### Risk: Breaking existing functionality
**Mitigation**: Incremental migration with continuous testing

### Risk: Performance regression
**Mitigation**: Benchmark before/after each phase

### Risk: Over-abstraction
**Mitigation**: Keep interfaces simple and focused

### Risk: Tight coupling
**Mitigation**: Use dependency injection and interfaces

## Documentation Requirements

1. **API Documentation**: Complete docstrings for all public methods
2. **Usage Examples**: Show how to extend for new personas
3. **Migration Guide**: Step-by-step migration instructions
4. **Architecture Diagrams**: Visual representation of component relationships

## Conclusion

This architecture provides a solid foundation for unifying the two task scheduler implementations while preserving their unique capabilities. The phased migration approach ensures minimal disruption and continuous validation of functionality.

The common library will eliminate significant code duplication, improve maintainability, and make it easier to add new scheduling personas in the future.