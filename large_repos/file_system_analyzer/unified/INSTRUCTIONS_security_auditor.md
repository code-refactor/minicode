# Compliance Data Discovery Analyzer

A specialized file system analyzer focused on identifying sensitive information and ensuring regulatory compliance.

## Overview

The Compliance Data Discovery Analyzer is a Python library designed to help information security specialists conduct thorough audits for regulatory compliance. It provides tools for pattern-based scanning to detect sensitive information, comprehensive audit logging, customizable compliance reporting, differential scanning to identify changes, and chain-of-custody tracking to ensure the integrity of findings.

## Persona Description

Priya works as an information security specialist conducting regular audits for regulatory compliance. She needs to identify potentially sensitive files stored in unauthorized locations and verify that data retention policies are being properly enforced.

## Key Requirements

1. **Pattern-Based Scanning for Sensitive Data**:
   Algorithms to detect personally identifiable information (PII) and other sensitive data based on content signatures. This is critical for Priya because unauthorized storage of sensitive information creates regulatory and security risks. The system must identify various types of sensitive data including personal identifiers, financial information, health records, and proprietary business data across diverse file formats.

2. **Comprehensive Audit Logging**:
   Implementation of immutable, detailed logging of all scan operations for compliance evidence. This feature is essential because audits must be defensible and verifiable. Priya needs to document exactly what was scanned, when, by whom, and what was found to create an indisputable record that can be presented during formal compliance reviews.

3. **Customizable Compliance Report Templates**:
   Reporting tools mapped to specific regulatory frameworks (GDPR, HIPAA, SOX, etc.). This capability is crucial for providing evidence in the right format for different compliance requirements. Priya needs to generate reports that directly address the specific requirements of various regulations, with appropriate categorization and context for findings.

4. **Differential Scanning for New Content**:
   Mechanisms to highlight newly added sensitive content since previous audit. This is vital for efficient ongoing compliance monitoring. Priya needs to quickly identify new compliance violations without reviewing previously addressed issues, allowing for targeted remediation and continuous improvement of data governance.

5. **Chain-of-Custody Tracking**:
   Cryptographic verification systems for exported reports to maintain evidence integrity. This feature is essential for establishing the validity of findings. Priya needs to ensure that compliance evidence cannot be altered once collected, with cryptographic proof that reports haven't been modified since their creation.

## Technical Requirements

### Testability Requirements
- All components must have well-defined interfaces that can be tested independently
- Pattern detection algorithms must be testable against sample data with known sensitive content
- Audit logging must be verifiable for completeness and immutability
- Report generation must be testable for accuracy and compliance with regulatory formats
- Chain-of-custody mechanisms must be cryptographically verifiable

### Performance Expectations
- Content scanning should process at least 100GB of data per hour
- Pattern matching should handle complex regular expressions with minimal false positives
- Differential analysis should complete 50% faster than full scans
- Report generation should handle findings from millions of files
- System should operate with minimal performance impact on scanned systems

### Integration Points
- Standard filesystem access interfaces across operating systems
- Encryption libraries for secure logging and verification
- Regulatory compliance definition libraries
- Export formats for compliance documentation (PDF, HTML, XLSX)
- Optional integration with governance, risk, and compliance (GRC) platforms

### Key Constraints
- All operations must be non-destructive and read-only
- Sensitive data found during scans must never be extracted or copied
- Implementation must handle diverse file formats including documents, databases, and archives
- System must operate within data privacy regulations
- Solution must be deployable in air-gapped environments if needed

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality

The Compliance Data Discovery Analyzer must provide the following core functionality:

1. **Sensitive Data Detection Engine**:
   - Pattern matching using regular expressions and other techniques
   - Pre-defined rules for common sensitive data types
   - Custom rule definition capabilities
   - Multi-format content extraction (text, documents, structured data)
   - Context-aware detection to minimize false positives

2. **Audit Integrity Framework**:
   - Tamper-evident logging architecture
   - Detailed operation recording with timestamps
   - User attribution for all actions
   - Cryptographic hashing for log validation
   - Secure storage of audit records

3. **Regulatory Compliance Reporting System**:
   - Framework-specific report templates (GDPR, HIPAA, SOX, etc.)
   - Finding categorization by compliance requirement
   - Risk level assessment for identified issues
   - Remediation recommendation generation
   - Evidence packaging for formal audits

4. **Differential Analysis Engine**:
   - Baseline storage and comparison
   - Change detection algorithms
   - New content identification
   - Modified content tracking
   - Removed sensitive data verification

5. **Evidence Chain-of-Custody System**:
   - Cryptographic signing of reports and findings
   - Tamper detection mechanisms
   - Timestamping and validation
   - Access logging for exported evidence
   - Verification tools for authenticity checking

## Testing Requirements

### Key Functionalities to Verify
- Accuracy of sensitive data detection across file types
- Integrity and immutability of audit logging
- Correctness of regulatory compliance report generation
- Precision of differential scanning results
- Reliability of chain-of-custody mechanisms

### Critical User Scenarios
- Complete compliance scan of an enterprise environment
- Generation of regulatory-specific reports for formal audit
- Differential scan to identify new compliance issues
- Verification of evidence package integrity
- Documentation of data retention policy enforcement

### Performance Benchmarks
- Complete scan of 1TB of diverse data in under 10 hours
- False positive rate below 0.1% for sensitive data detection
- Differential analysis 50% faster than full scan for 10% changed content
- Report generation in under 5 minutes for 10,000+ findings
- Verification of chain-of-custody in under 10 seconds

### Edge Cases and Error Conditions
- Handling of encrypted or password-protected content
- Graceful operation with corrupted or malformed files
- Recovery from interrupted scans
- Appropriate handling of very large individual files
- Proper response to access permission restrictions

### Required Test Coverage Metrics
- Minimum 95% code coverage for all security-critical modules
- 90% code coverage for all other modules
- Comprehensive tests for all supported sensitive data patterns
- Performance tests for all resource-intensive operations
- Security tests for all chain-of-custody mechanisms

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

The Compliance Data Discovery Analyzer implementation will be considered successful when:

1. Sensitive data detection accurately identifies PII and other regulated information
2. Audit logging provides immutable, comprehensive evidence of scan operations
3. Compliance reports correctly map findings to specific regulatory requirements
4. Differential scanning efficiently identifies newly added sensitive content
5. Chain-of-custody mechanisms provide cryptographically verifiable evidence
6. All performance benchmarks are met or exceeded
7. Code is well-structured, maintainable, and follows Python best practices
8. The system meets the needs of formal compliance auditing processes

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

NOTE: To set up your development environment, use `uv venv` to create a virtual environment. From within the project directory, activate the environment with `source .venv/bin/activate`. Install the project with `uv pip install -e .`.

CRITICAL: Running tests with pytest-json-report and providing the pytest_results.json file is MANDATORY for project completion. Use the following commands:
```
pip install pytest-json-report
pytest --json-report --json-report-file=pytest_results.json
```