# Creative Writing Text Editor

A specialized text editor library designed for fiction writers with focus on distraction-free writing and narrative management.

## Overview

This project implements a text editor library specifically designed for fiction writers who need a distraction-free environment with powerful narrative management features. It provides focus mode, writing statistics tracking, character and plot tracking, non-linear document navigation, and revision marking with draft comparison.

## Persona Description

Elena writes novels and short stories, focusing on creative writing rather than programming. She needs a distraction-free environment that helps manage narrative elements while providing powerful text manipulation capabilities.

## Key Requirements

1. **Focus Mode**: Implement a system that can isolate and highlight the current paragraph or sentence while visually de-emphasizing surrounding content. This is critical for Elena to eliminate distractions and immerse herself in the current section of writing, improving concentration and creative flow.

2. **Writing Statistics Tracking**: Develop analytics functionality that tracks word count, reading level metrics, and writing pace over time. This allows Elena to monitor her productivity, set goals, manage project deadlines, and assess the complexity and consistency of her writing style across different works.

3. **Character and Plot Element Tracking**: Create a system that identifies and tracks character names and key terms across chapters or sections. This helps Elena maintain consistency in character descriptions and behaviors throughout long narratives, preventing continuity errors common in complex stories.

4. **Non-linear Document Navigation**: Implement a document organization system based on narrative elements (scenes, chapters, character arcs) rather than simple linear text. This enables Elena to work with the story structure conceptually, moving between related scenes or character perspectives regardless of their sequential placement in the document.

5. **Revision Marking with Draft Comparison**: Develop functionality for maintaining multiple drafts of the same document with the ability to compare and selectively merge changes. This supports Elena's editing workflow, allowing her to experiment with alternative versions of scenes or dialogue while maintaining the ability to revert or combine elements from different drafts.

## Technical Requirements

### Testability Requirements
- Focus mode state must be programmatically testable without visual rendering
- Statistics calculations must be verifiable with known input text samples
- Character/plot tracking must be testable with predefined narrative content
- Navigation structure must be verifiable through programmatic state inspection
- Revision comparison and merging must be testable with predetermined diff scenarios

### Performance Expectations
- Text operations must remain responsive even in documents over 300,000 words (novel length)
- Statistics calculations should run in background threads without impacting editing performance
- Character/plot element indexing should complete within 5 seconds for full novel-length documents
- Navigation between narrative elements should occur in under 100ms
- Revision comparison should scale efficiently to handle documents with thousands of differences

### Integration Points
- Natural language processing tools for character and term recognition
- Text statistics libraries for reading level and linguistic analysis
- Diff algorithms for revision comparison
- Document structure representation for non-linear navigation
- Export capabilities to standard document formats

### Key Constraints
- No UI/UX components; all functionality should be implemented as library code
- Character recognition must work without requiring manual tagging
- Navigation structure must preserve original document ordering when needed
- Revision tracking must maintain complete history without excessive storage requirements
- Compatible with Python 3.8+ ecosystem

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality

The library should implement a text editor core with the following functionality:

1. A focus system that:
   - Identifies and isolates current paragraph or sentence context
   - Maintains edit capabilities while in focus mode
   - Provides smooth transitions between different focus points
   - Preserves document structure while focusing

2. A statistics tracking system that:
   - Calculates and monitors word count, sentence structure, and reading level
   - Tracks writing pace and productivity over time
   - Analyzes linguistic patterns and vocabulary usage
   - Generates reports on writing trends and goal progress

3. A narrative element tracking system that:
   - Identifies and indexes character names and key terms
   - Maintains cross-references of elements across document sections
   - Detects potential continuity issues or inconsistencies
   - Provides element lookup and reference capabilities

4. A non-linear navigation system that:
   - Organizes document by narrative elements rather than just linear text
   - Enables quick movement between related sections regardless of position
   - Maintains multiple organizational views of the same content
   - Preserves document integrity while enabling non-linear access

5. A revision management system that:
   - Maintains multiple drafts of the same document
   - Provides detailed comparison between different versions
   - Enables selective merging of changes from different drafts
   - Tracks the history and evolution of content over time

## Testing Requirements

### Key Functionalities to Verify
- Focus mode correctly isolates the current paragraph or sentence
- Statistics calculations accurately reflect writing metrics
- Character and plot element tracking correctly identifies narrative elements
- Non-linear navigation properly organizes and accesses document by narrative structure
- Revision marking successfully manages multiple drafts and enables comparison

### Critical User Scenarios
- Writing a new scene with focus on the current paragraph
- Analyzing writing statistics for a completed chapter
- Tracking a character's appearances and descriptions across a novel
- Navigating between related scenes in different chapters
- Comparing two drafts of the same scene and selectively merging changes

### Performance Benchmarks
- Focus mode transitions should occur in under 50ms
- Statistics calculations should process at least 10,000 words per second
- Character indexing should identify at least 95% of character names without explicit tagging
- Navigation structure should handle documents with at least 100 scenes/chapters
- Revision comparison should complete in under 3 seconds for 10,000-word documents

### Edge Cases and Error Conditions
- Handling extremely long paragraphs or sentences in focus mode
- Managing statistics for unusual writing styles or multilingual content
- Dealing with ambiguous character names or references
- Navigating complex non-linear structures with circular references
- Managing revision history for documents with frequent and extensive changes

### Required Test Coverage Metrics
- Minimum 90% code coverage across all core modules
- 100% coverage of text processing functions
- Complete coverage of all public API methods
- All statistical metrics must have verification tests
- All draft comparison operations must have test coverage

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

1. Focus mode effectively isolates current writing context without losing surrounding document awareness
2. Writing statistics provide accurate and useful metrics on writing style and productivity
3. Character and plot tracking successfully identifies and maintains consistency of narrative elements
4. Non-linear navigation enables intuitive movement through document based on narrative structure
5. Revision marking and comparison effectively manages the evolution of document drafts

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