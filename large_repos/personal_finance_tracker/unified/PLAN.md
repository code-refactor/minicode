# Unified Library Architecture Plan

## Executive Summary

This document outlines the architecture and migration plan for creating a unified library that serves both the Personal Finance Tracker (freelancer) and Ethical Finance (socially responsible investor) implementations. The goal is to extract common functionality while preserving persona-specific business logic.

## Analysis Summary

### Common Patterns Identified

1. **Financial Transactions**: Both systems process transactions with dates, amounts, and categories
2. **Time-Based Aggregation**: Monthly, quarterly, and yearly calculations
3. **Scoring Systems**: Confidence scores, alignment scores, ESG ratings
4. **Batch Processing**: Efficient handling of large transaction sets
5. **Configuration Management**: Settings and rules-based systems
6. **Performance Monitoring**: Processing time tracking and optimization

### Key Differences to Preserve

- **Personal Finance Tracker**: Tax calculations, project profitability, business expense tracking
- **Ethical Finance**: ESG screening, impact measurement, shareholder advocacy

## Common Library Architecture

### Core Components

#### 1. Base Models (`common.core.models`)

```python
# base.py
class BaseTransaction:
    - id: str
    - date: datetime
    - amount: float
    - description: str
    - metadata: Dict[str, Any]
    
class BasePortfolio:
    - id: str
    - name: str
    - holdings: List[BaseHolding]
    - created_at: datetime
    - updated_at: datetime

class BaseConfiguration:
    - validate(): bool
    - to_dict(): Dict
    - from_dict(data: Dict): BaseConfiguration

# money.py
class Money:
    - amount: Decimal
    - currency: str
    - operations: +, -, *, /, comparison
    - formatting methods

# time_period.py
class Period:
    - start: datetime
    - end: datetime
    - type: PeriodType (MONTH, QUARTER, YEAR)
    - contains(date): bool
    - overlaps(other): bool
```

#### 2. Financial Calculations (`common.core.calculations`)

```python
# financial.py
- calculate_percentage(part, whole) -> float
- calculate_change(old, new) -> float
- compound_interest(principal, rate, time) -> float
- present_value(future_value, rate, time) -> float

# statistics.py
- mean(values) -> float
- median(values) -> float
- variance(values) -> float
- standard_deviation(values) -> float
- percentile(values, p) -> float
- weighted_average(values, weights) -> float

# aggregation.py
- aggregate_by_period(transactions, period_type) -> Dict
- group_by_category(transactions) -> Dict
- rolling_average(values, window) -> List
- cumulative_sum(values) -> List

# scoring.py
- normalize_score(value, min_val, max_val) -> float
- weighted_score(scores, weights) -> float
- confidence_interval(values, confidence) -> Tuple
- rank_scores(scores) -> List[int]
```

#### 3. Data Validation (`common.core.validation`)

```python
# validators.py
- validate_percentage(value, min=0, max=100) -> float
- validate_date_range(start, end) -> bool
- validate_positive(value) -> float
- validate_currency_amount(value) -> Decimal

# constraints.py
- check_required_fields(obj, fields) -> bool
- check_range(value, min_val, max_val) -> bool
- check_enum(value, allowed_values) -> bool
```

#### 4. Processing Utilities (`common.core.processing`)

```python
# batch.py
class BatchProcessor:
    - process_in_chunks(items, chunk_size, processor)
    - parallel_process(items, processor, max_workers)
    - progress_tracking(items, processor)

# caching.py
class CacheManager:
    - get(key) -> Optional[Any]
    - set(key, value, ttl)
    - invalidate(key)
    - clear()

# performance.py
class PerformanceMonitor:
    - start_timer(operation)
    - end_timer(operation)
    - get_metrics() -> Dict
    - check_threshold(operation, threshold)
```

#### 5. Formatting Utilities (`common.core.formatting`)

```python
# currency.py
- format_currency(amount, currency='USD') -> str
- parse_currency(text) -> Decimal

# dates.py
- format_date(date, format='YYYY-MM-DD') -> str
- parse_date(text) -> datetime
- format_period(period) -> str

# data.py
- to_dict(obj) -> Dict
- from_dict(data, cls) -> object
- to_json(obj) -> str
- from_json(text, cls) -> object
```

### Pattern Libraries (`common.patterns`)

```python
# managers.py
class BaseManager:
    - __init__(config: BaseConfiguration)
    - process(items) -> ProcessingResult
    - validate_input(items) -> bool
    - get_metrics() -> Dict

# results.py
class ProcessingResult:
    - success: bool
    - data: Any
    - errors: List[str]
    - warnings: List[str]
    - metadata: Dict
    - processing_time: float

# config.py
class ConfigurationManager:
    - load_config(path) -> BaseConfiguration
    - save_config(config, path)
    - validate_config(config) -> bool
    - merge_configs(base, override) -> BaseConfiguration
```

## Migration Strategy

### Phase 1: Common Library Implementation

1. **Create base models and utilities**
   - Implement Money class with proper decimal handling
   - Create Period and time handling utilities
   - Build base Transaction and Portfolio classes

2. **Implement calculation modules**
   - Financial calculations (percentages, changes, etc.)
   - Statistical functions
   - Aggregation utilities
   - Scoring systems

3. **Add validation and processing utilities**
   - Input validators
   - Constraint checkers
   - Batch processing
   - Caching system
   - Performance monitoring

4. **Create formatting utilities**
   - Currency formatting
   - Date formatting
   - Data serialization

### Phase 2: Personal Finance Tracker Migration

1. **Update models to extend base classes**
   ```python
   from common.core.models import BaseTransaction
   
   class Expense(BaseTransaction):
       category: ExpenseCategory
       is_business: bool
       project_id: Optional[str]
   ```

2. **Replace calculation functions**
   - Use common.core.calculations for percentages
   - Use common.core.statistics for averages
   - Use common.core.aggregation for monthly summaries

3. **Update managers to use common patterns**
   ```python
   from common.patterns import BaseManager, ProcessingResult
   
   class ExpenseCategorizer(BaseManager):
       # Inherit common processing patterns
   ```

4. **Preserve domain-specific logic**
   - Keep tax calculations
   - Keep project profitability analysis
   - Keep invoice and client management

### Phase 3: Ethical Finance Migration

1. **Update models to extend base classes**
   ```python
   from common.core.models import BaseTransaction, BasePortfolio
   
   class EthicalTransaction(BaseTransaction):
       esg_score: float
       impact_category: str
   
   class EthicalPortfolio(BasePortfolio):
       ethical_criteria: EthicalCriteria
   ```

2. **Use common calculation utilities**
   - Replace custom percentage calculations
   - Use common scoring utilities
   - Use common aggregation functions

3. **Adopt common patterns**
   - Use BaseManager for service classes
   - Use ProcessingResult for return values
   - Use common validation utilities

4. **Maintain specialized functionality**
   - Keep ESG screening algorithms
   - Keep impact measurement
   - Keep shareholder advocacy features

## Implementation Order

1. **Week 1: Core Infrastructure**
   - [ ] common/core/models/base.py
   - [ ] common/core/models/money.py
   - [ ] common/core/models/time_period.py
   - [ ] common/core/calculations/financial.py
   - [ ] common/core/calculations/statistics.py

2. **Week 2: Utilities and Patterns**
   - [ ] common/core/validation/validators.py
   - [ ] common/core/processing/batch.py
   - [ ] common/core/formatting/currency.py
   - [ ] common/patterns/managers.py
   - [ ] common/patterns/results.py

3. **Week 3: Personal Finance Tracker Migration**
   - [ ] Update expense models
   - [ ] Update income models
   - [ ] Refactor categorizer
   - [ ] Refactor tax manager
   - [ ] Update project analyzer

4. **Week 4: Ethical Finance Migration**
   - [ ] Update transaction models
   - [ ] Update portfolio models
   - [ ] Refactor screening system
   - [ ] Refactor analysis system
   - [ ] Update budgeting system

## Success Metrics

1. **Code Reduction**: Target 30-40% reduction in duplicated code
2. **Test Coverage**: Maintain 100% test pass rate
3. **Performance**: No degradation in processing times
4. **Maintainability**: Clear separation of concerns
5. **Extensibility**: Easy to add new personas

## Risk Mitigation

1. **Backward Compatibility**: All existing tests must pass
2. **Performance**: Monitor and benchmark critical paths
3. **Complexity**: Keep interfaces simple and intuitive
4. **Documentation**: Comprehensive docstrings and examples

## Testing Strategy

1. **Unit Tests**: Test each common component independently
2. **Integration Tests**: Verify persona implementations work with common library
3. **Performance Tests**: Ensure no performance regression
4. **Regression Tests**: Run all existing tests continuously

## Deliverables

1. Fully implemented common library
2. Migrated personal_finance_tracker using common
3. Migrated ethical_finance using common
4. All tests passing with report.json
5. Updated README documentation