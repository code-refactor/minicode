# Freelancer Financial Management System

## Overview
A specialized financial management system designed for freelancers and independent contractors who experience irregular income patterns and project-based earnings. The system helps manage cash flow during lean periods, track business expenses, forecast tax obligations, and ensure financial stability despite unpredictable revenue streams.

## Persona Description
Jamal works as a freelance designer with irregular income patterns and project-based earnings. He needs to manage cash flow during lean periods, track business expenses for tax purposes, and ensure financial stability despite unpredictable revenue.

## Key Requirements
1. **Income smoothing calculations that normalize variable earnings for consistent budgeting**  
   Jamal's income varies significantly month-to-month, making conventional budget approaches ineffective. He needs sophisticated income smoothing algorithms that can normalize his irregular earnings into predictable budget allocations, creating artificial "paychecks" that allow for consistent bill payment and expense management despite the actual timing of client payments.

2. **Project profitability analysis comparing time invested against revenue generated**  
   As a freelancer, Jamal needs to understand which projects and clients provide the best return on his time investment. The system must track hours worked on each project, associated expenses, and resulting income to calculate effective hourly rates, project profitability, and client value over time, allowing for data-driven decisions on which opportunities to pursue.

3. **Tax obligation forecasting with quarterly estimated payment scheduling**  
   Without employer tax withholding, Jamal must manage his own tax obligations. The system needs to continuously calculate estimated tax liabilities based on current earnings, track previously made payments, forecast upcoming quarterly payment amounts, and alert him to payment deadlines to prevent tax-related penalties and surprises.

4. **Business versus personal expense separation maintaining clear boundaries for deductions**  
   Jamal requires clear separation between business and personal finances while using the same physical accounts. The system needs sophisticated categorization rules to properly tag expenses, calculate appropriate business use percentages for mixed-use items, and maintain audit-ready records of business deductions with attached documentation.

5. **Cash runway visualization showing how long current funds will last at different spending levels**  
   During periods between projects, Jamal needs to understand how long his current funds will sustain him. The system must provide cash runway projections based on current balances, expected incoming payments, and different spending scenarios, helping him make informed decisions about taking on new projects or reducing expenses.

## Technical Requirements
- **Testability Requirements:**
  - Income smoothing algorithms must be tested with various income patterns
  - Tax calculation functions must be validated against real tax rules
  - Time tracking and profitability calculations must be accurate to the minute
  - Cash runway projections must be tested against historical data

- **Performance Expectations:**
  - System must recalculate tax obligations in under 1 second when new transactions are added
  - Income smoothing calculations must process 5+ years of transaction history in under 3 seconds
  - Project profitability analysis must handle at least 100 concurrent projects
  - Category tagging and expense classification must achieve 95% accuracy

- **Integration Points:**
  - Import functionality for invoicing software data
  - Export capabilities for tax preparation
  - Time tracking data integration
  - Receipt scanning and storage

- **Key Constraints:**
  - Tax rules must be configurable for different jurisdictions
  - All calculations must be traceable and explainable
  - System must be usable offline during travel periods
  - Data model must allow for both cash and accrual accounting views

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The system must implement these core components:

1. **Income Management System:**
   - Variable income recording with client and project attribution
   - Income smoothing algorithms with configurable parameters
   - Revenue forecasting based on historical patterns and confirmed projects
   - Invoice tracking from creation to payment

2. **Project Profitability Analyzer:**
   - Time tracking integration and management
   - Expense allocation to specific projects
   - Multi-dimensional profitability metrics (hourly, project, client)
   - Trend analysis across project types and timelines

3. **Tax Management Engine:**
   - Progressive tax bracket calculations
   - Self-employment tax handling
   - Quarterly estimated payment scheduling
   - Deduction and credit optimization
   - Year-over-year tax comparison

4. **Expense Categorization System:**
   - Rule-based transaction categorization
   - Business use percentage calculations
   - Receipt and documentation management
   - Category-based reporting and analysis
   - Audit trail maintenance

5. **Financial Projection Models:**
   - Cash flow forecasting with multiple scenarios
   - Runway calculations with confidence intervals
   - "What-if" analysis for spending decisions
   - Emergency fund adequacy assessment

## Testing Requirements
- **Key Functionalities to Verify:**
  - Income smoothing correctly normalizes variable income streams
  - Project profitability calculations accurately reflect time and expense inputs
  - Tax obligation forecasts align with actual tax liabilities
  - Business and personal expenses are correctly categorized
  - Cash runway projections accurately predict sustainable time periods

- **Critical User Scenarios:**
  - Processing a new client payment and its impact on income smoothing
  - Completing a project and analyzing its final profitability
  - Preparing for quarterly tax payments
  - Categorizing mixed-use expenses with appropriate business percentages
  - Making spending decisions during a period with no active projects

- **Performance Benchmarks:**
  - System must maintain performance with 7+ years of transaction history
  - Tax calculations must complete in under 2 seconds including all deductions
  - Income smoothing must be recalculated in under 1 second when new data is added
  - Project profitability reports must generate in under 3 seconds for all historical projects

- **Edge Cases and Error Conditions:**
  - Handling of extremely irregular income patterns
  - Managing projects that span multiple tax years
  - Adapting to mid-year tax rule changes
  - Recovering from categorization errors discovered months later
  - Handling negative cash flow periods

- **Required Test Coverage Metrics:**
  - Income smoothing algorithms: minimum 95% coverage
  - Tax calculation functions: minimum 95% coverage
  - Project profitability analysis: minimum 90% coverage
  - Cash flow projection models: minimum 90% coverage

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
- The system effectively smooths irregular income into predictable budget allocations
- Project profitability analysis accurately reflects the return on time invested
- Tax obligations are correctly calculated and forecasted for quarterly payments
- Business and personal expenses are clearly separated with proper documentation
- Cash runway visualizations provide accurate projections for financial planning
- All calculations maintain accuracy across different income scenarios
- System performance meets or exceeds the specified benchmarks
- All tests pass without manual intervention

REQUIRED FOR SUCCESS:
- All tests must pass when run with pytest
- A valid pytest_results.json file must be generated showing all tests passing
- The implementation must satisfy all key requirements specified for this persona

## Development Environment Setup
1. Set up a virtual environment using `uv venv`
2. Activate the environment with `source .venv/bin/activate`
3. Install the project with `uv pip install -e .`
4. Run tests with:
   ```
   pip install pytest-json-report
   pytest --json-report --json-report-file=pytest_results.json
   ```

REMINDER: Generating and providing the pytest_results.json file is a critical requirement for project completion.