# Educational Text Editor for Computer Science Students

A specialized text editor library designed for computer science students learning software development and text editor implementation.

## Overview

This project implements a text editor library specifically designed for computer science students who want to understand editor internals while developing their programming skills. It provides a progressive complexity interface, implementation learning mode, customization playground, interview preparation tools, and study session capabilities.

## Persona Description

Jamal is learning about software development and text editor implementation. He wants to understand the inner workings of editors while having a tool that grows with his programming capabilities.

## Key Requirements

1. **Progressive Complexity Interface**: Implement a system that gradually reveals advanced features as the user's skills develop. This is critical for Jamal as it prevents overwhelming him with complex functionality while he's still mastering basics, but ensures the editor can grow with his capabilities as he advances in his studies.

2. **Implementation Learning Mode**: Develop a mode that provides annotated source code and guided extension projects to understand the editor's inner workings. This allows Jamal to learn about text editor implementation by exploring actual production code with educational annotations, supporting his desire to understand how editors function internally.

3. **Customization Playground**: Create an environment for safely experimenting with different editor behaviors and algorithms. This enables Jamal to modify editor functionality, test alternative implementations, and understand the implications of different design decisions without breaking his main development environment.

4. **Interview Preparation Tools**: Implement functionality specifically designed for practicing common programming challenges. This helps Jamal prepare for technical interviews by providing integrated tools for algorithm practice, time tracking, and solution comparison that are directly relevant to the job search process.

5. **Study Session Capabilities**: Develop features for organizing focused learning periods with integrated time tracking and review scheduling. This supports Jamal's academic work by helping him manage study time effectively, track progress on learning objectives, and schedule regular reviews to reinforce knowledge retention.

## Technical Requirements

### Testability Requirements
- Progressive feature levels must be programmatically testable
- Learning mode annotations must be verifiable through content inspection
- Customization experiments must be isolated and revertible
- Interview practice scenarios must produce consistent, measurable results
- Study session metrics must be accurately recorded and retrievable

### Performance Expectations
- Feature level transitions should occur in under 50ms
- Learning mode documentation should load within 100ms
- Customization changes should apply in under 200ms
- Interview practice environments should initialize in under 1 second
- Study session tracking should have minimal impact on editor performance

### Integration Points
- Programming language syntax and semantics systems
- Algorithm visualization and execution framework
- Study tracking and scheduling systems
- Learning progress analytics
- Source code documentation generation

### Key Constraints
- No UI/UX components; all functionality should be implemented as library code
- Learning materials must be programmatically integrated, not just linked
- Customizations must maintain editor stability and recover from errors
- Practice environments must be secure and isolated
- Compatible with Python 3.8+ ecosystem

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality

The library should implement a text editor core with the following functionality:

1. A progressive feature system that:
   - Organizes editor features into skill-appropriate levels
   - Tracks user proficiency and experience
   - Gradually unlocks advanced capabilities
   - Provides guidance for newly accessible features

2. A learning mode system that:
   - Provides annotated access to editor source code
   - Links implementations to computer science concepts
   - Offers guided extension projects
   - Tracks progress through implementation concepts

3. A customization system that:
   - Allows experimental modification of editor components
   - Provides safe testing environments for changes
   - Explains the implications of different implementations
   - Supports reverting to stable configurations

4. An interview preparation system that:
   - Provides common algorithm problems and exercises
   - Times solution attempts with appropriate constraints
   - Analyzes solution quality and performance
   - Compares approaches against standard implementations

5. A study session system that:
   - Schedules focused learning periods
   - Tracks time spent on different topics
   - Manages review scheduling using spaced repetition
   - Analyzes learning effectiveness and progress

## Testing Requirements

### Key Functionalities to Verify
- Progressive feature system correctly manages available functionality based on user level
- Learning mode properly displays annotated source code and tracks concept understanding
- Customization playground safely allows experimentation with editor modifications
- Interview preparation tools accurately present and evaluate programming challenges
- Study session capabilities effectively track learning time and manage review scheduling

### Critical User Scenarios
- A beginner advancing through progressive feature levels as skills develop
- Exploring editor internals through annotated source code in learning mode
- Experimenting with a custom text storage algorithm in the customization playground
- Preparing for interviews by solving timed algorithm challenges
- Managing study sessions for a semester-long programming course

### Performance Benchmarks
- Progressive feature changes should process in under 50ms
- Learning mode documentation should render at least 1000 lines per second
- Customization experiments should apply changes in under 200ms
- Interview practice environments should execute test cases at a rate of at least 100 per second
- Study session tracking should handle at least 100 events per minute

### Edge Cases and Error Conditions
- Handling conflicting customizations or experimental implementations
- Managing incomplete or incorrect solutions in interview preparation
- Dealing with interrupted study sessions or scheduling conflicts
- Recovering from crashes caused by experimental modifications
- Adapting to widely varying skill progression rates

### Required Test Coverage Metrics
- Minimum 90% code coverage across all core modules
- 100% coverage of feature progression paths
- Complete coverage of all public API methods
- All interview problem types must have verification tests
- All study tracking features must have test coverage

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

1. Progressive complexity interface effectively adapts to the user's skill level
2. Implementation learning mode provides clear insight into editor internals
3. Customization playground safely enables experimentation with editor components
4. Interview preparation tools effectively support algorithm practice
5. Study session capabilities accurately track learning time and manage review scheduling

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Environment Setup

To set up the development environment:

1. Create a virtual environment:
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

4. CRITICAL: For running tests and generating the required json report:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

REMINDER: Generating and providing pytest_results.json is a critical requirement for project completion.