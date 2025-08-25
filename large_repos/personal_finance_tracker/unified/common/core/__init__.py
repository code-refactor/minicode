"""
Core financial system functionality.

This package provides foundational components for financial applications
including models, calculations, validation, processing, and formatting
utilities that both persona implementations can use.
"""

# Models - Core data structures and base classes
from .models import (
    # Base classes
    BaseTransaction,
    BasePortfolio,
    BaseConfiguration,
    TransactionType,
    ValidationMixin,
    AuditMixin,
    
    # Money handling
    Money,
    Currency,
    sum_money,
    average_money,
    
    # Time periods
    Period,
    PeriodType,
    Weekday,
    RecurringSchedule,
    get_business_days_between,
    get_quarter_dates,
    get_fiscal_year_dates,
)

# Calculations - Financial and statistical computations
from .calculations import (
    # Financial calculations
    percentage_change,
    absolute_change,
    percentage_of_total,
    apply_percentage,
    compound_growth_rate,
    simple_interest,
    compound_interest,
    present_value,
    future_value,
    net_present_value,
    internal_rate_of_return,
    break_even_point,
    return_on_investment,
    weighted_average,
    annualized_return,
    tax_adjusted_return,
    inflation_adjusted_value,
    
    # Statistical calculations
    mean,
    median,
    mode,
    variance,
    standard_deviation,
    coefficient_of_variation,
    percentile,
    quartiles,
    interquartile_range,
    outliers,
    correlation_coefficient,
    linear_regression,
    moving_average,
    exponential_moving_average,
    summary_statistics,
    volatility,
    sharpe_ratio,
    
    # Aggregation utilities
    AggregationType,
    TimeSeriesDataPoint,
    AggregationResult,
    TimeSeriesAggregator,
    group_by_category,
    create_summary_by_period,
    calculate_period_over_period_change,
    create_time_series_from_dict,
    
    # Scoring and normalization
    ScoreDirection,
    NormalizationMethod,
    ScoreConfig,
    ScoreResult,
    normalize_min_max,
    normalize_z_score,
    normalize_percentile,
    normalize_sigmoid,
    score_metric,
    calculate_composite_score,
    rank_values,
    create_score_card,
    calculate_financial_health_score,
)

# Validation - Data integrity and business rules
from .validation import (
    # Validation functions and classes
    ValidationError,
    ValidationResult,
    validate_required,
    validate_type,
    validate_numeric,
    validate_positive_amount,
    validate_percentage,
    validate_date,
    validate_date_range,
    validate_email,
    validate_string_length,
    validate_regex_pattern,
    validate_choice,
    validate_list,
    validate_dict,
    validate_business_rules,
    
    # Constraint classes and utilities
    ConstraintSeverity,
    ConstraintViolation,
    Constraint,
    RangeConstraint,
    DateRangeConstraint,
    UniquenessConstraint,
    RegexConstraint,
    CustomConstraint,
    FinancialConstraints,
    ConstraintValidator,
    create_financial_validator,
)

# Processing - Batch processing, caching, and performance
from .processing import (
    # Batch processing
    BatchResult,
    BatchProcessor,
    TransactionBatchProcessor,
    ProgressTracker,
    create_transaction_validator,
    create_transaction_enrichment_functions,
    
    # Caching utilities
    CacheEntry,
    CacheStats,
    Cache,
    InMemoryCache,
    CacheManager,
    get_cache_manager,
    cached,
    cache_key_from_dict,
    MemoizedCalculation,
    memoized_calculation,
    setup_default_caches,
    
    # Performance monitoring
    PerformanceMetric,
    TimingResult,
    PerformanceTracker,
    SystemMonitor,
    PerformanceMonitor,
    timed,
    get_global_monitor,
    memory_profiling,
    time_financial_operation,
)

# Formatting - Display and serialization
from .formatting import (
    # Currency formatting
    CurrencyFormat,
    CurrencySymbols,
    format_currency,
    format_compact_currency,
    format_exchange_rate,
    format_percentage,
    parse_currency_string,
    format_currency_list,
    get_currency_formatting_info,
    
    # Date formatting
    DateFormat,
    TimeFormat,
    format_date,
    format_datetime,
    format_relative_date,
    format_period,
    format_duration,
    format_period_type_name,
    format_business_date_range,
    format_fiscal_period,
    get_quarter_name,
    format_date_list,
    
    # Data serialization and formatting
    SerializationFormat,
    DateTimeEncoder,
    datetime_decoder,
    serialize_to_json,
    deserialize_from_json,
    serialize_to_dict,
    flatten_dict,
    serialize_to_csv,
    deserialize_from_csv,
    format_table,
    create_financial_csv_formatter,
    export_data,
    import_data,
)
