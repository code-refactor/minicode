# Secure Systems Vulnerability Simulator

## Overview
A specialized virtual machine emulator designed for security research and education, providing a controlled environment to safely demonstrate and analyze memory corruption, code injection, privilege escalation, and other low-level security vulnerabilities without real-world consequences.

## Persona Description
Dr. Chen studies low-level security vulnerabilities and exploitation techniques. He needs a controlled environment to demonstrate memory corruption, code injection, and other attack vectors without real-world consequences.

## Key Requirements
1. **Memory Protection Simulation**: Implement a configurable memory protection system with adjustable enforcement levels, permission controls, and boundary checking. This feature is critical for Dr. Chen to demonstrate how memory safety mechanisms work, how they can be bypassed, and how different protection strategies affect vulnerability exploitability.

2. **Exploitation Playground**: Create a safe environment for demonstrating buffer overflows, format string vulnerabilities, code injection, and return-oriented programming attacks. This capability allows Dr. Chen to showcase real attack techniques in a contained environment, providing hands-on experience with exploitation mechanics without risk to actual systems.

3. **Permission and Privilege Models**: Develop a comprehensive permission and privilege level system to illustrate access control mechanisms, privilege escalation vulnerabilities, and security boundaries. This feature helps explain the critical concept of least privilege and demonstrates how attackers can move laterally through a system by exploiting permission weaknesses.

4. **Control Flow Integrity Visualization**: Implement visualization tools showing normal and compromised execution paths, highlighting how attacks manipulate program flow. This visualization makes abstract concepts like return address manipulation concrete for students, demonstrating exactly how control flow hijacking attacks redirect execution in exploited programs.

5. **Isolation Breach Detection**: Create mechanisms for detecting and analyzing when virtualization or protection boundaries are compromised, with detailed forensic information. This feature is essential for security researchers to understand the indicators of successful attacks and develop detection methods for real-world exploitation attempts.

## Technical Requirements
- **Testability Requirements**:
  - All security mechanisms must be independently testable
  - Exploitation scenarios must be repeatable and deterministic
  - Memory corruption attacks must produce consistent, verifiable results
  - Protection bypasses must be detectable and measurable
  - Attack success or failure must be programmatically verifiable
  
- **Performance Expectations**:
  - Memory operations must be traceable with minimal overhead
  - Protection checks should add no more than 10% execution overhead
  - Attack demonstrations should complete within seconds, not minutes
  - System should handle programs with at least 10,000 instructions
  - Forensic data collection should not significantly impact system performance

- **Integration Points**:
  - Clean separation between VM core and security monitoring components
  - Well-defined interfaces for custom protection mechanisms
  - Extensible logging and event notification system
  - Export formats for execution traces and memory state
  - Hooks for custom analysis and detection modules

- **Key Constraints**:
  - Implementation must be in pure Python for educational clarity and portability
  - No dependencies beyond standard library to ensure easy deployment
  - System must never execute arbitrary code on the host machine
  - All exploitation techniques must be contained within the VM
  - Security boundaries between simulator and host must be absolute

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The core functionality of this secure systems vulnerability simulator includes:

1. A virtual machine with a detailed memory model supporting various protection mechanisms

2. A comprehensive instruction set supporting both legitimate and attack-oriented operations

3. Configurable security boundaries with adjustable enforcement levels

4. Memory corruption vulnerability demonstrations (buffer overflows, heap spraying, use-after-free)

5. Code injection capabilities with various payload execution methods

6. Privilege separation with multiple security domains and transition mechanisms

7. Control flow integrity monitoring and visualization

8. Return-oriented programming (ROP) and jump-oriented programming (JOP) attack support

9. Format string vulnerability demonstrations and exploitation

10. Data execution prevention (DEP) and address space layout randomization (ASLR) implementations

11. Detailed forensic logging of system state before, during, and after attacks

12. Predefined scenarios demonstrating common vulnerability classes and exploitation techniques

## Testing Requirements
- **Key Functionalities that Must be Verified**:
  - Correct implementation of memory protection mechanisms
  - Accurate simulation of various attack vectors
  - Proper privilege level enforcement and transitions
  - Reliable detection of protection boundary violations
  - Accurate control flow tracking and visualization
  - Consistent behavior of exploitation techniques

- **Critical User Scenarios**:
  - Demonstrating classic buffer overflow attacks
  - Illustrating return-oriented programming techniques
  - Showing privilege escalation through various vectors
  - Testing effectiveness of different protection strategies
  - Creating and analyzing novel exploitation techniques
  - Comparing different mitigation approaches

- **Performance Benchmarks**:
  - Memory protection checks adding no more than 10% overhead
  - Support for programs with at least 10,000 instructions
  - Attack demonstrations completing in under 10 seconds
  - Forensic data collection with less than 15% performance impact
  - Memory operations processing at least 10,000 accesses per second

- **Edge Cases and Error Conditions**:
  - Handling of extremely large buffer overflows
  - Proper detection of subtle control flow manipulations
  - Accurate tracking of complex memory corruption chains
  - Correct behavior with unusual instruction sequences
  - Appropriate response to sophisticated protection bypasses

- **Required Test Coverage Metrics**:
  - Minimum 95% line coverage for core security mechanisms
  - 100% coverage for privilege transition code
  - At least 90% branch coverage for attack detection logic
  - Complete coverage of memory protection implementations
  - At least 85% coverage for exploit demonstration code

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

1. Accurately simulates a variety of memory protection mechanisms with adjustable enforcement

2. Provides a safe and effective environment for demonstrating exploitation techniques

3. Implements a proper privilege model with security boundaries and transitions

4. Clearly visualizes control flow paths before and after exploitation

5. Reliably detects and reports security boundary violations

6. Supports common attack vectors like buffer overflows, ROP chains, and code injection

7. Provides detailed forensic information about successful and attempted exploits

8. Enables comparison between different protection strategies

9. Maintains complete isolation between simulated attacks and the host system

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