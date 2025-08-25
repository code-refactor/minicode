# Privacy-Focused Query Language Interpreter

## Overview
This specialized Query Language Interpreter enables data privacy officers to identify and manage personal information across company systems without centralizing sensitive data. The interpreter includes built-in PII detection capabilities, data minimization filtering, comprehensive access logging, policy-based query restrictions, and automatic anonymization functions, allowing for effective compliance reviews while maintaining strict data protection standards.

## Persona Description
Raj ensures compliance with data protection regulations across company systems. He needs to query data repositories to identify personal information without centralizing sensitive data in additional systems.

## Key Requirements
1. **PII (Personally Identifiable Information) detection using pattern matching and validation**: Automatically identifies potential PII (names, addresses, phone numbers, SSNs, financial information, etc.) across diverse data sources using pre-configured and customizable pattern matching, validation rules, and contextual analysis, enabling comprehensive compliance scanning without prior knowledge of where sensitive data might reside.

2. **Data minimization filtering showing only essential fields for compliance reviews**: Implements configurable field filtering that automatically limits query results to only the specific data fields necessary for privacy compliance tasks, enforcing the data minimization principle required by regulations like GDPR and preventing unnecessary exposure of sensitive information during compliance activities.

3. **Access logging creating immutable records of all queries against sensitive data**: Maintains detailed, tamper-resistant logs of all query activities, including the user, timestamp, query parameters, data sources accessed, and the specific fields viewed, providing a complete audit trail for regulatory compliance and security reviews of privacy-related activities.

4. **Policy-based query restrictions preventing unauthorized data combinations**: Enforces configurable data access policies that prevent potentially harmful data combinations or analyses, such as joining anonymized datasets with identifying information or combining data in ways that could lead to re-identification of individuals, ensuring compliance with privacy regulations even during advanced analysis.

5. **Anonymization functions automatically masking sensitive fields in query results**: Provides built-in data anonymization capabilities (hashing, tokenization, redaction, generalization, etc.) that can be applied automatically to sensitive fields in query results, enabling privacy-preserving analysis while maintaining the utility of the data for legitimate business purposes.

## Technical Requirements
### Testability Requirements
- All PII detection patterns must be individually testable with sample data
- Data minimization rules must be verifiable with distinct test cases
- Access logging must be tested for completeness and tamper resistance
- Policy enforcement must be tested with both compliant and non-compliant queries
- Anonymization functions must be tested for effectiveness and consistency

### Performance Expectations
- PII scanning should process at least 1GB of structured data per hour
- Query execution should maintain reasonable performance despite policy enforcement
- Access logging should have minimal impact on query performance
- Anonymization operations should add no more than 200ms to query execution time
- The system should scale to handle enterprise datasets (100+ tables, billions of records)

### Integration Points
- Support for common data sources (databases, CSV files, JSON data, API endpoints)
- Configurable integration with existing enterprise identity and access management systems
- Export capabilities for compliance reports and audit logs
- Optional integration with data cataloging systems for metadata awareness
- Alert mechanism for potential policy violations or unusual access patterns

### Key Constraints
- Processing must occur where data resides to avoid centralizing sensitive information
- Implementation must be compliant with major privacy regulations (GDPR, CCPA, HIPAA)
- All operations must be auditable and transparent
- Access controls must be granular to field-level permissions
- System must operate securely in environments with highly sensitive data

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The core functionality of this Privacy-Focused Query Language Interpreter includes:

1. **Query Engine with Privacy Extensions**:
   - SQL-like language with privacy-specific functions and constraints
   - Execution planning that respects privacy policies and access restrictions
   - Support for distributed query execution without data centralization
   - Integration with existing data sources without modification

2. **PII Detection System**:
   - Pattern matching engine with pre-configured detectors for common PII types
   - Validation rules to confirm potential PII matches
   - Customizable detection rules for organization or industry-specific PII
   - Confidence scoring for potential PII matches

3. **Policy Enforcement Framework**:
   - Rule-based system for defining and enforcing data access policies
   - Prevention of unauthorized data combinations
   - Field-level access control integration
   - Policy violation detection and handling

4. **Access Audit System**:
   - Comprehensive logging of all query operations
   - Tamper-evident audit trail implementation
   - Detailed metadata capture for compliance reporting
   - Query history and analysis tools

5. **Data Protection Functions**:
   - Multiple anonymization techniques (hashing, tokenization, masking, etc.)
   - Pseudonymization with key management
   - Data generalization and aggregation methods
   - Differential privacy implementation for statistical queries

## Testing Requirements
### Key Functionalities to Verify
- Accuracy of PII detection across diverse data formats and types
- Correct application of data minimization filters based on purpose specification
- Complete and accurate logging of all access activities
- Proper enforcement of data access policies and combination restrictions
- Effectiveness of anonymization functions for different data types

### Critical User Scenarios
- Conducting a data protection impact assessment across multiple systems
- Responding to a data subject access request by locating all personal data
- Performing a compliance audit for regulatory requirements
- Investigating a potential data protection violation
- Generating privacy compliance reports for management or regulators

### Performance Benchmarks
- PII detection must achieve at least 95% accuracy on standard test datasets
- Query execution with privacy controls must complete within 2x the time of equivalent queries without controls
- Access logging must not increase query latency by more than 10%
- Policy enforcement engine must evaluate complex policies in under 100ms
- System must handle datasets with at least 10 million records while maintaining reasonable performance

### Edge Cases and Error Conditions
- Handling of encrypted or encoded data with potential PII
- Correct behavior when encountering malformed or unusual personal data formats
- Appropriate response to attempted policy violations or unauthorized queries
- Graceful handling of conflicting privacy rules or policies
- Proper management of edge cases in anonymization (e.g., unique values that can't be effectively anonymized)

### Required Test Coverage Metrics
- Minimum 95% code coverage across all modules
- 100% coverage for PII detection patterns and anonymization functions
- All policy enforcement rules must have dedicated test cases
- Access logging must be tested for all query types and scenarios
- All potential policy violation scenarios must be explicitly tested

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
A successful implementation will:

1. Accurately identify PII across various data sources using pattern matching and validation, verified by tests with diverse data samples containing known PII patterns
2. Properly apply data minimization filters based on purpose specification, demonstrated by tests showing only necessary fields are returned
3. Maintain comprehensive access logs for all queries and data access, validated through audit trail tests
4. Correctly enforce data access policies and prevent unauthorized data combinations, verified by tests with policy-violating queries
5. Effectively anonymize sensitive data fields while preserving analytical utility, confirmed through tests measuring both protection and utility

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Environment Setup

To set up your development environment:

```bash
# From within the project directory
uv venv
source .venv/bin/activate
uv pip install -e .
```

CRITICAL: Running tests with pytest-json-report and providing the pytest_results.json file is MANDATORY for project completion:
```bash
pip install pytest-json-report
pytest --json-report --json-report-file=pytest_results.json
```