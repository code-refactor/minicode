# 3D Rendering Farm Orchestrator

## Overview
A specialized concurrent task scheduler designed for managing complex 3D rendering operations across hundreds of machines. This system optimizes rendering job distribution while adapting to changing project priorities and deadlines, with particular focus on deadline-driven scheduling, resource partitioning, and progressive result generation.

## Persona Description
Carlos oversees a 3D rendering operation that processes animation and visual effects for film studios. His primary goal is to balance rendering jobs across hundreds of machines while adapting to changing project priorities and deadlines.

## Key Requirements

1. **Deadline-Driven Scheduling System**
   - Implement an intelligent scheduling mechanism with dynamic priority adjustment based on project deadlines, completion status, and business importance
   - This feature is critical for Carlos as it ensures that rendering jobs for time-sensitive projects are completed on schedule while maintaining fair resource allocation for all clients
   - The system must automatically adjust priorities as deadlines approach and provide clear visibility into whether deliverables will be met on time

2. **Client-Specific Resource Partitioning**
   - Create a sophisticated resource allocation system that partitions rendering capacity among clients with guaranteed minimums while allowing flexible overflow usage
   - This feature is essential for Carlos as it allows the rendering farm to maintain service level agreements with premium clients while maximizing overall hardware utilization
   - Must support both static allocation and dynamic borrowing with configurable policies

3. **Render Node Specialization**
   - Develop a task distribution system that matches rendering jobs to nodes based on hardware capabilities, job characteristics, and historical performance
   - This feature is crucial for Carlos as it optimizes rendering time by ensuring that jobs are executed on the most appropriate hardware (e.g., GPU vs. CPU rendering, memory-intensive tasks, etc.)
   - Must learn from past job performance to improve future allocation decisions

4. **Progressive Result Generation**
   - Implement a framework for generating progressive or partial rendering results to provide early feedback while full-quality rendering continues
   - This feature is vital for Carlos as it allows artists and directors to identify issues early in the rendering process without waiting for complete high-resolution frames
   - Must manage the additional computational overhead while minimizing impact on final delivery schedules

5. **Energy and Cost Optimization**
   - Create a scheduling system that optimizes power consumption and infrastructure costs, especially for overnight or low-priority rendering
   - This feature is important for Carlos to manage operational expenses while still meeting all client deadlines
   - Must include configurable modes that balance performance against energy usage and factor in time-of-day electricity costs

## Technical Requirements

### Testability Requirements
- All components must be independently testable with well-defined interfaces
- System must support simulation of large render farms without requiring actual hardware
- Test coverage should exceed 90% for all scheduling and resource allocation components
- Performance tests must validate behavior under realistic rendering workloads

### Performance Expectations
- Support for at least 1,000 concurrent rendering tasks across hundreds of nodes
- Scheduling decisions must complete in under 500ms even with complex constraints
- System should achieve at least 95% resource utilization under normal conditions
- Node allocation should improve rendering efficiency by at least 20% compared to simple round-robin distribution

### Integration Points
- Integration with common rendering engines (Arnold, V-Ray, RenderMan)
- Support for industry-standard job submission formats and protocols
- Interfaces for digital asset management systems and production tracking tools
- Compatibility with infrastructure monitoring and management platforms

### Key Constraints
- IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.
- The system must maintain detailed audit trails of all rendering activities
- All operations must be resilient to individual node failures
- Must operate effectively in heterogeneous hardware environments
- System should minimize unnecessary re-rendering due to interruptions

## Core Functionality

The 3D Rendering Farm Orchestrator must provide:

1. **Render Job Definition and Submission**
   - A comprehensive API for defining rendering jobs with their technical requirements and business parameters
   - Support for complex dependencies between scene elements, shots, and sequences
   - Detailed specification of quality parameters and output format requirements

2. **Resource Management and Allocation**
   - Intelligent partitioning of rendering resources among clients and projects
   - Dynamic adjustment of allocations based on deadlines and priorities
   - Optimal matching of jobs to hardware based on job characteristics

3. **Scheduling and Prioritization**
   - Deadline-aware scheduling that guarantees on-time completion of critical projects
   - Dynamic priority adjustment as deadlines approach or project status changes
   - Support for preemption of lower-priority jobs when necessary

4. **Performance Optimization**
   - Hardware-aware job distribution to maximize rendering efficiency
   - Learning mechanisms to improve allocation based on historical performance
   - Energy-efficient scheduling for non-time-critical rendering tasks

5. **Monitoring and Feedback**
   - Collection of detailed performance metrics for all rendering operations
   - Generation of progressive results for early feedback
   - Prediction of completion times based on current progress and historical data

## Testing Requirements

### Key Functionalities to Verify
- Deadline-driven scheduling correctly prioritizes jobs based on due dates
- Resource partitioning properly enforces client guarantees while allowing overflow
- Node specialization effectively matches jobs to optimal hardware
- Progressive result generation provides useful early feedback without excessive overhead
- Energy optimization reduces power consumption during appropriate periods

### Critical Scenarios to Test
- Management of competing high-priority projects with imminent deadlines
- Response to simulated node failures during critical rendering jobs
- Handling of emergency high-priority jobs requiring immediate resources
- Performance under maximum load with heterogeneous job types
- Correct behavior during gradual hardware upgrades and farm expansion

### Performance Benchmarks
- Scheduling overhead should not exceed 1% of total rendering time
- System should achieve at least 95% resource utilization under normal conditions
- Node specialization should improve rendering times by at least 20% compared to random allocation
- Energy optimization should reduce power consumption by at least 15% during overnight operations

### Edge Cases and Error Conditions
- Handling of corrupt scene files or rendering errors
- Recovery from node failures during long-running renders
- Correct behavior when client resource demands exceed total capacity
- Proper management of deadline conflicts between high-priority clients
- Graceful degradation under extreme farm usage conditions

### Required Test Coverage
- Minimum 90% line coverage for all scheduling and allocation components
- Comprehensive integration tests for end-to-end rendering workflows
- Performance tests simulating production-scale rendering operations
- Power consumption simulations for energy optimization validation

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

1. Deadline-driven scheduling ensures that 99% of jobs complete by their due dates
2. Client resource partitioning maintains guaranteed minimums while achieving 95% overall utilization
3. Node specialization improves rendering efficiency by at least 20% for specialized tasks
4. Progressive result generation provides usable feedback within 10% of final rendering time
5. Energy optimization reduces power consumption by at least 15% during appropriate periods

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