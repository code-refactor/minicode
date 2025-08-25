# Research Knowledge Hub

A comprehensive personal knowledge management system tailored for academic researchers working with complex scientific literature and research projects.

## Overview

Research Knowledge Hub is a specialized adaptation of the BrainCache personal knowledge management system designed specifically for academic researchers. It focuses on organizing and connecting scientific literature, experimental data, theoretical frameworks, and collaborative inputs while supporting academic writing workflows such as grant proposals and publications.

## Persona Description

Dr. Elaine Chen is a neuroscience professor juggling multiple research projects, collaborations, and teaching responsibilities. She needs to organize complex scientific literature, experimental notes, and theoretical connections while preparing publications and grant proposals.

## Key Requirements

1. **Citation-aware note linking**: Automatically connect notes to referenced academic papers, linking knowledge elements to their bibliographic sources. This is critical for Dr. Chen to maintain scientific rigor in her work, ensuring all insights are properly attributed and can be traced back to original literature.

2. **Research question tracking**: Map hypotheses to supporting evidence and contradictions, allowing structured organization of scientific inquiry. This feature is essential for Dr. Chen to maintain clarity across multiple research streams, identify gaps in evidence, and prioritize experiments that address specific questions.

3. **Grant proposal workspaces**: Organize specific subsets of knowledge for funding applications, creating focused collections of relevant information. This capability is vital for efficiently preparing competitive grant proposals by quickly assembling supporting literature, preliminary data, and methodology notes relevant to specific funding opportunities.

4. **Experiment logging templates**: Provide structured metadata frameworks for scientific reproducibility, ensuring comprehensive documentation of experimental procedures. As a researcher managing multiple experiments simultaneously, Dr. Chen needs standardized approaches to record methodologies, conditions, and results to maintain scientific integrity and facilitate publication.

5. **Collaborative annotation importing**: Incorporate colleague comments while maintaining personal knowledge structure, integrating input from research team members. This functionality is crucial for Dr. Chen's collaborative research environment, allowing her to benefit from team insights while preserving her own organizational system.

## Technical Requirements

### Testability Requirements
- All functions must have comprehensive unit tests with at least 90% code coverage
- Mock external dependencies (file system, citation APIs) for deterministic testing
- Test data should include realistic academic paper metadata and citation formats
- Performance tests should verify response times under varying knowledge base sizes

### Performance Expectations
- Citation linking should complete in under 1 second for standard academic papers
- Search operations should return results in under 2 seconds with knowledge bases of up to 10,000 notes
- Knowledge graph operations should scale efficiently with increasing node counts
- Background indexing should not impact interactive system performance

### Integration Points
- Support for BibTeX and other citation format imports
- JSON export capabilities for data interchange with other research tools
- Plain text storage format for version control system integration
- API endpoints for programmatic access to knowledge structures

### Key Constraints
- All data must remain local without cloud dependencies for privacy and control
- Plain text file storage (markdown) for longevity and portability
- Low memory footprint to handle large collections of research literature
- Cross-platform compatibility for collaborative research environments

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality

The Research Knowledge Hub must implement the following core functionality:

1. **Knowledge Base Management**
   - Create, update, and organize markdown-based research notes
   - Establish bidirectional links between related notes
   - Apply tagging system for multi-dimensional categorization
   - Structure notes hierarchically while maintaining network relationships

2. **Academic Citation Integration**
   - Parse and extract citation data from academic papers
   - Link notes to specific sections or quotes from referenced papers
   - Track citation relationships across the knowledge base
   - Generate properly formatted citations for academic writing

3. **Research Question Framework**
   - Create and manage structured research questions
   - Link evidence notes to research questions as supporting or contradicting
   - Calculate evidence strength metrics for research questions
   - Identify knowledge gaps requiring additional investigation

4. **Grant Proposal Management**
   - Create workspaces for specific funding opportunities
   - Filter and organize knowledge relevant to proposal sections
   - Track proposal requirements and corresponding evidence
   - Archive proposal versions with associated knowledge subsets

5. **Experimental Data Integration**
   - Define and use templates for experimental documentation
   - Link raw data references to experiment notes
   - Track experimental parameters and variations
   - Connect experimental results to research questions

6. **Collaborative Knowledge Integration**
   - Import annotations and notes from collaborators
   - Maintain provenance of externally sourced information
   - Resolve conflicts in overlapping knowledge areas
   - Selectively share knowledge subsets with collaborators

7. **Knowledge Retrieval and Analysis**
   - Perform full-text search with boolean operators
   - Filter search by tags, citation information, or note relationships
   - Generate visualizations of knowledge networks
   - Calculate similarity metrics between notes

## Testing Requirements

### Key Functionalities to Verify
- Creation and management of notes with proper metadata
- Establishment and traversal of bidirectional links
- Citation parsing and relationship mapping
- Research question tracking with evidence strength metrics
- Grant proposal workspace organization and filtering
- Experimental template application and data linking
- Collaborative annotation integration
- Search functionality with various filter combinations

### Critical User Scenarios
- Managing literature for a new research project
- Organizing evidence for competing hypotheses
- Preparing materials for a specific grant proposal
- Documenting a series of related experiments
- Integrating feedback from research team members
- Finding all information related to a specific research concept
- Identifying contradictions in collected evidence

### Performance Benchmarks
- Note creation and linking should complete in under 500ms
- Complex searches should return results in under 2 seconds
- Citation processing should handle at least 50 papers per minute
- Knowledge graph operations should scale to handle at least 20,000 notes

### Edge Cases and Error Conditions
- Handling malformed citation data
- Managing conflicting bidirectional links
- Dealing with duplicate research questions or evidence
- Recovering from corrupted note files
- Handling very large individual notes (>100KB)
- Managing notes with unusually high numbers of connections
- Processing incorrectly formatted experimental data

### Required Test Coverage Metrics
- Minimum 90% line coverage for all modules
- 100% coverage for critical data model and linking functionality
- All public APIs must have integration tests
- All error handling paths must be explicitly tested

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

The implementation will be considered successful if it meets the following criteria:

1. **Functional Completeness**
   - All five key requirements are fully implemented
   - Core functionality operates as specified
   - APIs are well-documented and provide access to all features

2. **Technical Quality**
   - Code is well-structured, modular, and follows Python best practices
   - Documentation is comprehensive and clear
   - Error handling is robust and user-friendly
   - Performance meets or exceeds benchmark requirements

3. **Research Workflow Support**
   - System effectively supports academic literature organization
   - Research question tracking provides meaningful insight into evidence relationships
   - Grant proposal workflows enhance productivity
   - Experimental data is properly structured and linked
   - Collaborative features preserve information integrity

4. **Testing Verification**
   - All tests pass successfully
   - Code coverage meets or exceeds required thresholds
   - Edge cases are properly handled
   - Performance benchmarks are satisfied

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Development Setup

To set up the development environment:

1. Create a virtual environment using uv:
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

4. Run tests with pytest-json-report (MANDATORY):
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

CRITICAL REMINDER: Generating and providing pytest_results.json is mandatory for project completion. This file serves as proof that all functionality has been implemented correctly and meets the requirements.