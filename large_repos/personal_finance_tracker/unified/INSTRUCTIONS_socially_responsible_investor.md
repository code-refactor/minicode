# Values-Aligned Financial Management System

## Overview
A specialized financial management system designed for socially responsible investors who want to track both the financial performance and social impact of their investments. The system helps align investments with ethical values, measure impact beyond financial returns, evaluate corporate behavior, analyze sector exposure, and ensure spending patterns match personal principles.

## Persona Description
Miguel aligns his investments with his ethical values and wants to track both financial performance and social impact. He needs to evaluate investments against environmental, social, and governance (ESG) criteria while optimizing his portfolio returns.

## Key Requirements
1. **Ethical investment screening using customizable value-based criteria**  
   Miguel needs to evaluate potential investments against his personal ethical standards. The system must provide a framework for defining customizable screening criteria based on environmental, social, governance (ESG), and other ethical factors. It should support both positive screening (seeking out companies with desired attributes) and negative screening (excluding companies involved in specific activities), with the ability to weight different criteria according to personal priorities.

2. **Impact metric tracking beyond pure financial returns (carbon avoided, community investment)**  
   Beyond financial performance, Miguel wants to measure the positive impact of his investment choices. The system must track and visualize non-financial impact metrics such as carbon emissions avoided, community development projects funded, sustainable practices supported, and other quantifiable social and environmental outcomes, providing a comprehensive view of his portfolio's total return (financial + impact).

3. **Shareholder voting record assessment for companies in portfolio**  
   Miguel wants to be an engaged shareholder who understands how the companies he invests in vote on important ESG issues. The system needs to track shareholder resolutions across his holdings, analyze voting patterns on key issues (climate change, diversity, executive compensation, etc.), and provide insights into corporate governance practices to inform future investment decisions.

4. **Industry and sector exposure analysis highlighting concentration in specific areas**  
   To ensure proper diversification while maintaining ethical alignment, Miguel needs detailed portfolio composition analysis. The system must break down holdings by industry, sector, geography, and ESG themes, identify concentrations and potential vulnerabilities, and provide recommendations for addressing gaps while maintaining alignment with defined ethical criteria.

5. **Values-aligned budget categories showing spending alignment with personal principles**  
   Miguel wants his personal spending to reflect the same values as his investments. The system requires enhanced budgeting functionality that tags expenses according to values-based categories, identifies spending patterns that may conflict with stated ethical priorities, and suggests alternatives that better align with personal principles.

## Technical Requirements
- **Testability Requirements:**
  - ESG screening algorithms must be tested against established frameworks
  - Impact calculations must be verifiable against public data sources
  - Portfolio analysis must be validated with diverse investment mixes
  - Values-based expense categorization must achieve high accuracy

- **Performance Expectations:**
  - System must handle portfolios with 100+ individual holdings
  - Screening of potential investments must complete in under 3 seconds
  - Portfolio impact analysis must update within 5 seconds when holdings change
  - Expense categorization must process 1,000+ transactions per second

- **Integration Points:**
  - Support for importing investment data from brokerage accounts
  - Access to ESG rating data from multiple providers
  - Integration with shareholder voting records
  - Connection to sustainable spending guides and resources

- **Key Constraints:**
  - ESG criteria must be fully customizable to individual values
  - Impact metrics must be quantifiable and comparable over time
  - System must adapt to evolving ethical standards and frameworks
  - All calculations must be transparent and explainable

IMPORTANT: The implementation should have NO UI/UX components. All functionality must be implemented as testable Python modules and classes that can be thoroughly tested using pytest. Focus on creating well-defined APIs and interfaces rather than user interfaces.

## Core Functionality
The system must implement these core components:

1. **Ethical Screening Framework:**
   - Customizable screening criteria definition
   - Multi-factor scoring system for investments
   - Positive and negative screening capabilities
   - Threshold-based investment inclusion/exclusion
   - Periodic rescreening of existing holdings

2. **Impact Measurement Engine:**
   - Quantifiable impact metric definitions
   - Impact data collection and validation
   - Portfolio-level impact aggregation
   - Financial/impact correlation analysis
   - Impact reporting and visualization

3. **Shareholder Advocacy Tracker:**
   - Shareholder resolution database
   - Voting record analysis by company and issue
   - Proxy voting recommendation system
   - Corporate engagement opportunity identification
   - Governance practice assessment

4. **Portfolio Analysis System:**
   - Multi-dimensional portfolio composition analysis
   - ESG theme exposure calculation
   - Diversification assessment with ethical constraints
   - Risk analysis with values alignment
   - Portfolio optimization recommendations

5. **Values-Aligned Budgeting:**
   - Ethical spending category framework
   - Transaction classification with values tagging
   - Spending pattern analysis against stated values
   - Alternative vendor and product suggestions
   - Values-consistency scoring

## Testing Requirements
- **Key Functionalities to Verify:**
  - Accurate screening of investments against customizable ethical criteria
  - Proper calculation of impact metrics from investment data
  - Correct analysis of shareholder voting patterns on ESG issues
  - Accurate portfolio composition analysis by industry, sector, and ESG themes
  - Proper categorization of expenses according to values-based criteria

- **Critical User Scenarios:**
  - Defining a new set of ethical screening criteria and evaluating a portfolio
  - Tracking the impact metrics of a newly added sustainable investment
  - Analyzing a company's voting record on climate-related shareholder resolutions
  - Identifying overexposure to a particular industry and finding ethical alternatives
  - Categorizing personal expenses and identifying values-aligned spending patterns

- **Performance Benchmarks:**
  - Ethical screening must evaluate 1,000+ potential investments in under 30 seconds
  - Impact calculations must handle 5+ years of historical data for trend analysis
  - Portfolio analysis must process at least 200 holdings with multiple ESG attributes
  - Values-based expense categorization must achieve at least 85% accuracy

- **Edge Cases and Error Conditions:**
  - Handling investments with limited or conflicting ESG data
  - Managing competing ethical priorities in screening criteria
  - Processing companies that change practices over time
  - Adapting to new impact metrics and measurement methodologies
  - Categorizing ambiguous expenses with multiple potential ethical implications

- **Required Test Coverage Metrics:**
  - Ethical screening algorithms: minimum 90% coverage
  - Impact calculation functions: minimum 90% coverage
  - Portfolio analysis components: minimum 85% coverage
  - Values-based categorization system: minimum 85% coverage

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
- The system accurately screens investments according to customizable ethical criteria
- Impact metrics are properly calculated and tracked alongside financial returns
- Shareholder voting patterns are correctly analyzed for ESG-related issues
- Portfolio composition analysis provides clear insight into sector and industry exposure
- Personal spending is appropriately categorized according to values-based criteria
- All calculations are transparent and can be explained to the user
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