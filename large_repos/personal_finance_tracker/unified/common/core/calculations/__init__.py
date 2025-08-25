"""
Financial calculation utilities for common operations.

This package provides calculation functions for financial analysis,
statistics, aggregation, and scoring that both persona implementations
can use for their specific needs.
"""

# Financial calculations
from .financial import (
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
)

# Statistical calculations
from .statistics import (
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
)

# Aggregation utilities
from .aggregation import (
    AggregationType,
    TimeSeriesDataPoint,
    AggregationResult,
    TimeSeriesAggregator,
    group_by_category,
    create_summary_by_period,
    calculate_period_over_period_change,
    create_time_series_from_dict,
)

# Scoring and normalization
from .scoring import (
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

__all__ = [
    # Financial calculations
    "percentage_change",
    "absolute_change",
    "percentage_of_total",
    "apply_percentage",
    "compound_growth_rate",
    "simple_interest",
    "compound_interest",
    "present_value",
    "future_value",
    "net_present_value",
    "internal_rate_of_return",
    "break_even_point",
    "return_on_investment",
    "weighted_average",
    "annualized_return",
    "tax_adjusted_return",
    "inflation_adjusted_value",
    
    # Statistical calculations
    "mean",
    "median",
    "mode",
    "variance",
    "standard_deviation",
    "coefficient_of_variation",
    "percentile",
    "quartiles",
    "interquartile_range",
    "outliers",
    "correlation_coefficient",
    "linear_regression",
    "moving_average",
    "exponential_moving_average",
    "summary_statistics",
    "volatility",
    "sharpe_ratio",
    
    # Aggregation utilities
    "AggregationType",
    "TimeSeriesDataPoint",
    "AggregationResult",
    "TimeSeriesAggregator",
    "group_by_category",
    "create_summary_by_period",
    "calculate_period_over_period_change",
    "create_time_series_from_dict",
    
    # Scoring and normalization
    "ScoreDirection",
    "NormalizationMethod",
    "ScoreConfig",
    "ScoreResult",
    "normalize_min_max",
    "normalize_z_score",
    "normalize_percentile",
    "normalize_sigmoid",
    "score_metric",
    "calculate_composite_score",
    "rank_values",
    "create_score_card",
    "calculate_financial_health_score",
]