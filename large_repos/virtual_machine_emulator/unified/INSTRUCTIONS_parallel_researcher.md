# Parallel Computing Simulation Framework

## Overview
A specialized virtual machine implementation designed for parallel algorithm research, providing accurate simulation of multi-core execution, synchronization primitives, and concurrency patterns to support the visualization and analysis of parallel computational behaviors.

## Persona Description
Dr. Patel studies parallel algorithm design and needs to visualize concurrent execution patterns. He requires a virtual machine that can demonstrate multi-threaded behavior and synchronization mechanisms.

## Key Requirements
1. **Multi-core Simulation**: Implement a true parallel execution engine capable of demonstrating multiple instruction streams running simultaneously across virtual cores. This feature is critical for Dr. Patel to analyze how parallel algorithms distribute workloads across processing units, observe genuine concurrency, and experiment with different core allocation strategies for computational tasks.

2. **Race Condition Demonstration**: Create a deterministic environment for reproducing and analyzing race conditions with controllable thread interleaving and memory access patterns. This capability allows Dr. Patel to systematically study concurrency bugs, demonstrate why they occur, and test solutions in a controlled environment where typically non-deterministic behaviors become reproducible.

3. **Synchronization Primitive Implementation**: Develop a comprehensive suite of synchronization mechanisms including locks, semaphores, barriers, and atomic operations with detailed state tracking. These primitives are essential tools for parallel algorithm research, allowing Dr. Patel to explore different coordination strategies, measure their overhead, and evaluate their effectiveness in various concurrent scenarios.

4. **Thread Scheduling Visualization**: Implement a detailed visualization of thread scheduling decisions, context switches, and core allocation over time. This feature provides critical insight into how parallel workloads are managed by the system, helping Dr. Patel understand scheduling impacts on algorithm performance and identify optimization opportunities in thread management.

5. **Memory Coherence Modeling**: Create an accurate simulation of cache coherence protocols showing how memory updates propagate across multiple cores. This modeling is fundamental for understanding the performance characteristics of parallel algorithms, as memory coherence maintenance significantly impacts scalability and often creates bottlenecks that aren't apparent in single-threaded execution models.

## Technical Requirements
- **Testability Requirements**:
  - Thread execution must be deterministic when seed values are specified
  - Race condition scenarios must be reproducible on demand
  - Synchronization primitive operations must be independently verifiable
  - Memory coherence protocol behavior must match documented specifications
  - Scheduling decisions must be traceable and explainable
  
- **Performance Expectations**:
  - Must support simulation of at least 32 concurrent execution threads
  - Context switching overhead should be configurable to model different systems
  - Memory coherence simulation should accurately reflect real-world latencies
  - Thread creation and destruction should complete in millisecond range
  - Complete system should handle moderately complex parallel algorithms in reasonable time

- **Integration Points**:
  - Standard interface for loading parallel programs and algorithms
  - Export formats for execution traces and scheduling visualizations
  - API for custom synchronization primitive implementation
  - Hooks for specialized memory consistency models
  - Integration with parallel algorithm metrics and benchmarks

- **Key Constraints**:
  - Implementation must be in pure Python for educational clarity
  - No dependencies beyond standard library to ensure portability
  - All concurrency simulations must be deterministic when using fixed seeds
  - System must provide accurate timing ratios even if absolute performance differs
  - Synchronization behavior must match standard parallel computing models

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The core functionality of this parallel computing simulation framework includes:

1. A virtual machine capable of simulating true parallel execution across multiple cores

2. A thread management system supporting creation, scheduling, and synchronization

3. A comprehensive set of synchronization primitives (mutexes, semaphores, barriers, etc.)

4. A memory model supporting various coherence protocols (MESI, MOESI, etc.)

5. A deterministic scheduler with configurable policies and priorities

6. Race condition detection and reproduction capabilities

7. Thread execution visualization and tracing facilities

8. Performance metrics for parallel execution efficiency

9. Memory access pattern analysis tools

10. Configurable communication latency between cores

11. Support for common parallel algorithm patterns (map-reduce, producer-consumer, etc.)

12. Serializable execution state for reproducibility and testing

## Testing Requirements
- **Key Functionalities that Must be Verified**:
  - Correct parallel execution across multiple virtual cores
  - Proper implementation of all synchronization primitives
  - Accurate detection and reproduction of race conditions
  - Correct thread scheduling according to specified policies
  - Proper simulation of memory coherence protocols
  - Accurate timing of parallel operations and synchronization

- **Critical User Scenarios**:
  - Running classic parallel algorithms with correct results (parallel sort, matrix multiplication)
  - Demonstrating common concurrency issues (deadlocks, race conditions, priority inversion)
  - Visualizing different thread scheduling strategies and their impact
  - Comparing performance with different synchronization approaches
  - Analyzing memory access patterns in parallel code
  - Testing scalability of algorithms across varying numbers of cores

- **Performance Benchmarks**:
  - Support for at least 32 concurrent execution threads
  - Processing of at least 1 million virtual instructions per second (aggregated across all cores)
  - Thread creation and synchronization with less than 1ms overhead per operation
  - Memory coherence simulation with realistic latency ratios
  - Complete execution tracing with less than 50% overhead

- **Edge Cases and Error Conditions**:
  - Handling of complex deadlock scenarios
  - Proper detection of subtle race conditions
  - Correct behavior with extreme thread counts
  - Appropriate response to priority inversion
  - Graceful handling of resource exhaustion

- **Required Test Coverage Metrics**:
  - Minimum 90% line coverage for all components
  - 100% coverage for synchronization primitive implementations
  - At least 95% branch coverage for scheduler logic
  - Complete coverage of memory coherence protocol states
  - At least 85% coverage for race condition detection code

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
The implementation will be considered successful if it:

1. Correctly simulates true parallel execution across multiple virtual cores

2. Provides accurate implementations of standard synchronization primitives

3. Successfully demonstrates and allows analysis of race conditions

4. Clearly visualizes thread scheduling decisions and context switches

5. Accurately models memory coherence protocols and their performance impact

6. Reproduces known parallel algorithm behaviors and bottlenecks

7. Enables deterministic testing of non-deterministic concurrent behaviors

8. Provides useful insights into parallel algorithm performance characteristics

9. Scales reasonably with increased thread counts and problem sizes

10. Successfully passes all test cases demonstrating the required functionality

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Environment Setup
To set up the development environment:

1. Create a virtual environment using:
   ```
   uv venv
   ```

2. Activate the virtual environment:
   ```
   source .venv/bin/activate
   ```

3. Install the project in development mode:
   ```
   uv pip install -e .
   ```

4. CRITICAL: For test execution and reporting:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

REMINDER: Generating and providing the pytest_results.json file is a critical requirement for project completion. This file must be included as proof that all tests pass successfully.