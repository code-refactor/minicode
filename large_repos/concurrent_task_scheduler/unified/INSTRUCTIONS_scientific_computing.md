# Long-Running Simulation Orchestrator

## Overview
A specialized concurrent task scheduler designed for managing large-scale scientific simulations that run for months across hundreds of compute nodes. This system maximizes research output through efficient scheduling with robust checkpointing, fault tolerance, and scenario prioritization capabilities tailored to long-duration computational science workloads.

## Persona Description
Dr. Jackson runs large-scale climate simulations requiring months of continuous computing across hundreds of nodes. His primary goal is to maximize research output by efficiently scheduling simulation tasks with checkpointing and fault tolerance.

## Key Requirements

1. **Long-Running Job Management System**
   - Implement a sophisticated job management system that protects extended simulations from preemption while efficiently managing resource allocation over periods of months
   - This feature is critical for Dr. Jackson as climate simulations can require continuous computation for extremely long durations, and interruptions can invalidate results or waste substantial computing time
   - The system must balance the protection of long-running jobs against the need for system maintenance and fair resource sharing

2. **Simulation Dependency Tracking**
   - Create a comprehensive dependency management framework that tracks relationships between simulation stages and automates transitions between phases of complex models
   - This feature is essential for Dr. Jackson as climate models involve multiple interdependent simulation stages (atmospheric, oceanic, land surface, etc.) that must be coordinated precisely
   - Must support both predetermined workflows and dynamically generated dependencies based on intermediate results

3. **Equipment Failure Resilience**
   - Develop a fault tolerance system that minimizes recalculation after hardware failures by combining intelligent checkpointing with partial result preservation
   - This feature is crucial for Dr. Jackson as extended simulations running across hundreds of nodes have a high probability of experiencing hardware failures during their lifecycle
   - Must include configurable checkpointing strategies optimized for different simulation types and failure scenarios

4. **Resource Usage Forecasting**
   - Implement a predictive resource modeling system that generates accurate forecasts of simulation resource requirements for grant reporting and capacity planning
   - This feature is vital for Dr. Jackson to manage research budgets effectively and provide accurate information to funding agencies about computational resource utilization
   - Must track historical usage patterns and project future needs based on planned research activities

5. **Scenario Priority Management**
   - Create an adaptive prioritization system that adjusts resource allocation among different simulation scenarios based on preliminary result promise and research potential
   - This feature is important for Dr. Jackson to maximize scientific output by identifying and prioritizing the most productive simulation variants while deprioritizing less promising approaches
   - Must include evaluation mechanisms for assessing preliminary results and adjusting priorities dynamically

## Technical Requirements

### Testability Requirements
- All components must be independently testable with well-defined interfaces
- System must support simulation of long-duration jobs without requiring actual months-long execution
- Test coverage should exceed 90% for all checkpoint and recovery functionality
- Tests must validate behavior under various failure scenarios and resource conditions

### Performance Expectations
- Support for at least 100 concurrent long-running simulations across hundreds of nodes
- Checkpoint operations should not impact simulation performance by more than 2%
- Recovery from node failures should complete in under 5 minutes with less than 1 hour of lost computation
- Resource forecasting should achieve prediction accuracy within 15% for 6-month projections

### Integration Points
- Integration with common scientific computing frameworks (MPI, OpenMP)
- Support for high-performance file systems and archival storage
- Interfaces for supercomputing job schedulers (Slurm, PBS, LSF)
- Compatibility with scientific data formats and visualization tools

### Key Constraints
- IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.
- The system must maintain data integrity through all failure scenarios
- All checkpointing operations must be storage-efficient due to the scale of data
- Must operate effectively in multi-institution shared computing environments
- System must accommodate both planned maintenance and unexpected outages

## Core Functionality

The Long-Running Simulation Orchestrator must provide:

1. **Simulation Definition and Management**
   - A comprehensive API for defining complex multi-stage simulation workflows
   - Support for resource requirements specification and duration estimation
   - Mechanisms for monitoring and controlling long-running processes

2. **Checkpoint and Recovery**
   - Efficient state preservation with configurable frequency and scope
   - Intelligent recovery from various failure scenarios
   - Storage management for checkpoint data with retention policies

3. **Resource Allocation and Scheduling**
   - Long-term reservation of computational resources for extended simulations
   - Fair-sharing among competing research projects with priority adjustments
   - Accommodation of system maintenance with minimal disruption

4. **Performance Monitoring and Optimization**
   - Collection of detailed resource utilization metrics across simulation components
   - Analysis of performance patterns to identify optimization opportunities
   - Prediction of resource needs based on current and planned activities

5. **Scenario Management**
   - Comparison of preliminary results across simulation variants
   - Dynamic priority adjustment based on scientific promise
   - Resource reallocation from less promising to more promising scenarios

## Testing Requirements

### Key Functionalities to Verify
- Long-running job protection correctly shields simulations from preemption
- Dependency tracking properly manages transitions between simulation stages
- Failure resilience effectively minimizes recalculation after hardware failures
- Resource forecasting generates accurate predictions for future usage
- Scenario priority management appropriately adjusts based on preliminary results

### Critical Scenarios to Test
- Recovery from various hardware failure patterns affecting different nodes
- Management of competing high-priority simulations with limited resources
- Handling of system maintenance periods with minimal disruption
- Correct behavior during storage subsystem performance degradation
- Adaptation to unexpected resource contention from other users

### Performance Benchmarks
- Checkpointing overhead should not exceed 2% of total simulation time
- Recovery operations should restore operation within 5 minutes of failure detection
- Resource usage forecasts should be accurate within 15% for 6-month projections
- System should achieve at least 95% average node utilization across the cluster

### Edge Cases and Error Conditions
- Handling of corrupted checkpoint data or partial failures
- Recovery from simultaneous failures across multiple nodes
- Correct behavior when storage capacity for checkpoints is constrained
- Proper management of simulation deadlocks or infinite loops
- Graceful degradation when resource demands exceed system capacity

### Required Test Coverage
- Minimum 90% line coverage for all checkpoint and recovery components
- Comprehensive integration tests for multi-stage simulation workflows
- Performance tests for resource utilization and checkpointing overhead
- Failure scenario tests covering various hardware and software errors

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

1. Long-running job management successfully protects extended simulations from interruption
2. Simulation dependency tracking correctly manages transitions between stages
3. Equipment failure resilience limits recalculation to less than 1 hour of simulation time
4. Resource usage forecasting predictions are accurate within 15% for 6-month periods
5. Scenario priority management improves overall research output by at least 20%

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Setup Instructions

1. Setup a virtual environment using UV:
   ```
   uv venv
   source .venv/bin/activate
   ```

2. Install the project in development mode:
   ```
   uv pip install -e .
   ```

3. CRITICAL: Run tests with pytest-json-report to generate pytest_results.json:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

REMINDER: Generating and providing pytest_results.json is a critical requirement for project completion.