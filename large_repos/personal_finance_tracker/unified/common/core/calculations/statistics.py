"""
Statistical calculation utilities for financial data analysis.

This module provides functions for calculating statistical measures,
distributions, and risk metrics commonly used in financial analysis.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Union, Optional, Tuple, Dict, Any
import math
from collections import Counter

# Type alias for numeric types
Numeric = Union[int, float, Decimal]


def to_decimal(value: Numeric) -> Decimal:
    """Convert numeric value to Decimal for precise calculations."""
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def mean(values: List[Numeric]) -> Decimal:
    """
    Calculate arithmetic mean (average).
    
    Args:
        values: List of numeric values
        
    Returns:
        Mean value
        
    Raises:
        ValueError: If list is empty
    """
    if not values:
        raise ValueError("Cannot calculate mean of empty list")
    
    decimals = [to_decimal(v) for v in values]
    total = sum(decimals)
    avg = total / len(decimals)
    
    return avg.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def median(values: List[Numeric]) -> Decimal:
    """
    Calculate median value.
    
    Args:
        values: List of numeric values
        
    Returns:
        Median value
        
    Raises:
        ValueError: If list is empty
    """
    if not values:
        raise ValueError("Cannot calculate median of empty list")
    
    decimals = [to_decimal(v) for v in values]
    sorted_values = sorted(decimals)
    n = len(sorted_values)
    
    if n % 2 == 0:
        # Even number of values - average of middle two
        middle_right = n // 2
        middle_left = middle_right - 1
        median_value = (sorted_values[middle_left] + sorted_values[middle_right]) / 2
    else:
        # Odd number of values - middle value
        middle = n // 2
        median_value = sorted_values[middle]
    
    return median_value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def mode(values: List[Numeric]) -> List[Decimal]:
    """
    Calculate mode (most frequent values).
    
    Args:
        values: List of numeric values
        
    Returns:
        List of mode values (can be multiple)
        
    Raises:
        ValueError: If list is empty
    """
    if not values:
        raise ValueError("Cannot calculate mode of empty list")
    
    decimals = [to_decimal(v) for v in values]
    counter = Counter(decimals)
    max_count = max(counter.values())
    
    modes = [value for value, count in counter.items() if count == max_count]
    return sorted(modes)


def variance(values: List[Numeric], population: bool = False) -> Decimal:
    """
    Calculate variance.
    
    Args:
        values: List of numeric values
        population: If True, calculate population variance; if False, sample variance
        
    Returns:
        Variance
        
    Raises:
        ValueError: If list is empty or has only one value (for sample variance)
    """
    if not values:
        raise ValueError("Cannot calculate variance of empty list")
    
    if not population and len(values) == 1:
        raise ValueError("Cannot calculate sample variance with only one value")
    
    decimals = [to_decimal(v) for v in values]
    avg = mean(values)
    
    squared_deviations = [(x - avg) ** 2 for x in decimals]
    sum_squared_deviations = sum(squared_deviations)
    
    # Population variance divides by n, sample variance divides by n-1
    divisor = len(decimals) if population else len(decimals) - 1
    var = sum_squared_deviations / divisor
    
    return var.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def standard_deviation(values: List[Numeric], population: bool = False) -> Decimal:
    """
    Calculate standard deviation.
    
    Args:
        values: List of numeric values
        population: If True, calculate population std dev; if False, sample std dev
        
    Returns:
        Standard deviation
    """
    var = variance(values, population)
    std_dev = Decimal(str(math.sqrt(float(var))))
    
    return std_dev.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def coefficient_of_variation(values: List[Numeric]) -> Decimal:
    """
    Calculate coefficient of variation (relative standard deviation).
    
    Args:
        values: List of numeric values
        
    Returns:
        Coefficient of variation as decimal
        
    Raises:
        ValueError: If mean is zero
    """
    avg = mean(values)
    if avg == 0:
        raise ValueError("Cannot calculate coefficient of variation when mean is zero")
    
    std_dev = standard_deviation(values)
    cv = std_dev / abs(avg)
    
    return cv.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def percentile(values: List[Numeric], percentile_rank: Numeric) -> Decimal:
    """
    Calculate percentile value.
    
    Args:
        values: List of numeric values
        percentile_rank: Percentile rank (0-100)
        
    Returns:
        Value at the specified percentile
        
    Raises:
        ValueError: If list is empty or percentile rank is invalid
    """
    if not values:
        raise ValueError("Cannot calculate percentile of empty list")
    
    rank = to_decimal(percentile_rank)
    if rank < 0 or rank > 100:
        raise ValueError("Percentile rank must be between 0 and 100")
    
    decimals = [to_decimal(v) for v in values]
    sorted_values = sorted(decimals)
    
    if rank == 0:
        return sorted_values[0]
    if rank == 100:
        return sorted_values[-1]
    
    # Calculate position
    position = (rank / 100) * (len(sorted_values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    
    if lower_index == upper_index:
        return sorted_values[lower_index]
    
    # Linear interpolation
    weight = position - lower_index
    interpolated = (sorted_values[lower_index] * (1 - Decimal(str(weight))) + 
                   sorted_values[upper_index] * Decimal(str(weight)))
    
    return interpolated.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def quartiles(values: List[Numeric]) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate first, second (median), and third quartiles.
    
    Args:
        values: List of numeric values
        
    Returns:
        Tuple of (Q1, Q2, Q3)
    """
    q1 = percentile(values, 25)
    q2 = percentile(values, 50)  # median
    q3 = percentile(values, 75)
    
    return q1, q2, q3


def interquartile_range(values: List[Numeric]) -> Decimal:
    """
    Calculate interquartile range (Q3 - Q1).
    
    Args:
        values: List of numeric values
        
    Returns:
        Interquartile range
    """
    q1, _, q3 = quartiles(values)
    return q3 - q1


def outliers(values: List[Numeric], method: str = "iqr", threshold: Numeric = 1.5) -> List[Decimal]:
    """
    Identify outliers in the data.
    
    Args:
        values: List of numeric values
        method: Method to use ("iqr" or "zscore")
        threshold: Threshold for outlier detection
        
    Returns:
        List of outlier values
        
    Raises:
        ValueError: If method is invalid
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    threshold_decimal = to_decimal(threshold)
    outliers_list = []
    
    if method == "iqr":
        q1, _, q3 = quartiles(values)
        iqr = q3 - q1
        lower_bound = q1 - threshold_decimal * iqr
        upper_bound = q3 + threshold_decimal * iqr
        
        outliers_list = [v for v in decimals if v < lower_bound or v > upper_bound]
        
    elif method == "zscore":
        avg = mean(values)
        std_dev = standard_deviation(values)
        
        if std_dev == 0:
            return []  # No outliers if no variation
        
        z_scores = [abs(v - avg) / std_dev for v in decimals]
        outliers_list = [decimals[i] for i, z in enumerate(z_scores) if z > threshold_decimal]
        
    else:
        raise ValueError("Method must be 'iqr' or 'zscore'")
    
    return sorted(list(set(outliers_list)))


def correlation_coefficient(x_values: List[Numeric], y_values: List[Numeric]) -> Decimal:
    """
    Calculate Pearson correlation coefficient.
    
    Args:
        x_values: First variable values
        y_values: Second variable values
        
    Returns:
        Correlation coefficient (-1 to 1)
        
    Raises:
        ValueError: If lists have different lengths or insufficient data
    """
    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length")
    
    if len(x_values) < 2:
        raise ValueError("Need at least 2 data points for correlation")
    
    x_decimals = [to_decimal(v) for v in x_values]
    y_decimals = [to_decimal(v) for v in y_values]
    
    x_mean = mean(x_values)
    y_mean = mean(y_values)
    
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_decimals, y_decimals))
    
    x_variance = sum((x - x_mean) ** 2 for x in x_decimals)
    y_variance = sum((y - y_mean) ** 2 for y in y_decimals)
    
    if x_variance == 0 or y_variance == 0:
        return Decimal('0')  # Perfect correlation undefined when no variance
    
    denominator = Decimal(str(math.sqrt(float(x_variance * y_variance))))
    correlation = numerator / denominator
    
    return correlation.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def linear_regression(x_values: List[Numeric], y_values: List[Numeric]) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate linear regression parameters.
    
    Args:
        x_values: Independent variable values
        y_values: Dependent variable values
        
    Returns:
        Tuple of (slope, intercept, r_squared)
        
    Raises:
        ValueError: If lists have different lengths or insufficient data
    """
    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have the same length")
    
    if len(x_values) < 2:
        raise ValueError("Need at least 2 data points for regression")
    
    x_decimals = [to_decimal(v) for v in x_values]
    y_decimals = [to_decimal(v) for v in y_values]
    
    x_mean = mean(x_values)
    y_mean = mean(y_values)
    
    # Calculate slope
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_decimals, y_decimals))
    denominator = sum((x - x_mean) ** 2 for x in x_decimals)
    
    if denominator == 0:
        raise ValueError("Cannot calculate regression with no variance in x")
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Calculate R-squared
    y_predicted = [slope * x + intercept for x in x_decimals]
    ss_total = sum((y - y_mean) ** 2 for y in y_decimals)
    ss_residual = sum((y - y_pred) ** 2 for y, y_pred in zip(y_decimals, y_predicted))
    
    if ss_total == 0:
        r_squared = Decimal('1')  # Perfect fit when no variance in y
    else:
        r_squared = 1 - (ss_residual / ss_total)
    
    return (
        slope.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
        intercept.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP),
        r_squared.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    )


def moving_average(values: List[Numeric], window_size: int) -> List[Decimal]:
    """
    Calculate simple moving average.
    
    Args:
        values: List of numeric values
        window_size: Size of moving window
        
    Returns:
        List of moving averages
        
    Raises:
        ValueError: If window size is invalid
    """
    if window_size <= 0:
        raise ValueError("Window size must be positive")
    
    if window_size > len(values):
        raise ValueError("Window size cannot be larger than data size")
    
    decimals = [to_decimal(v) for v in values]
    moving_averages = []
    
    for i in range(len(decimals) - window_size + 1):
        window_values = decimals[i:i + window_size]
        avg = sum(window_values) / len(window_values)
        moving_averages.append(avg.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return moving_averages


def exponential_moving_average(
    values: List[Numeric],
    alpha: Numeric,
    initial_value: Optional[Numeric] = None
) -> List[Decimal]:
    """
    Calculate exponential moving average.
    
    Args:
        values: List of numeric values
        alpha: Smoothing factor (0 < alpha <= 1)
        initial_value: Initial EMA value (defaults to first value)
        
    Returns:
        List of exponential moving averages
        
    Raises:
        ValueError: If alpha is not in valid range
    """
    if not values:
        return []
    
    alpha_decimal = to_decimal(alpha)
    if alpha_decimal <= 0 or alpha_decimal > 1:
        raise ValueError("Alpha must be in range (0, 1]")
    
    decimals = [to_decimal(v) for v in values]
    ema_values = []
    
    # Initialize with first value or provided initial value
    if initial_value is not None:
        ema = to_decimal(initial_value)
    else:
        ema = decimals[0]
    
    for value in decimals:
        ema = alpha_decimal * value + (1 - alpha_decimal) * ema
        ema_values.append(ema.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return ema_values


def summary_statistics(values: List[Numeric]) -> Dict[str, Any]:
    """
    Calculate comprehensive summary statistics.
    
    Args:
        values: List of numeric values
        
    Returns:
        Dictionary of statistical measures
    """
    if not values:
        return {"error": "Empty dataset"}
    
    try:
        stats = {
            "count": len(values),
            "mean": float(mean(values)),
            "median": float(median(values)),
            "mode": [float(m) for m in mode(values)],
            "std_dev": float(standard_deviation(values)),
            "variance": float(variance(values)),
            "min": float(min(to_decimal(v) for v in values)),
            "max": float(max(to_decimal(v) for v in values)),
            "range": float(max(to_decimal(v) for v in values) - min(to_decimal(v) for v in values)),
        }
        
        # Add quartiles
        q1, q2, q3 = quartiles(values)
        stats.update({
            "q1": float(q1),
            "q2": float(q2),
            "q3": float(q3),
            "iqr": float(q3 - q1)
        })
        
        # Add coefficient of variation if mean is not zero
        if stats["mean"] != 0:
            stats["cv"] = float(coefficient_of_variation(values))
        
        return stats
        
    except Exception as e:
        return {"error": f"Error calculating statistics: {e}"}


def volatility(returns: List[Numeric], annualize: bool = True, trading_days: int = 252) -> Decimal:
    """
    Calculate volatility (standard deviation of returns).
    
    Args:
        returns: List of return values
        annualize: Whether to annualize the volatility
        trading_days: Trading days per year for annualization
        
    Returns:
        Volatility measure
    """
    if not returns:
        raise ValueError("Cannot calculate volatility of empty returns list")
    
    std_dev = standard_deviation(returns)
    
    if annualize:
        # Annualize by multiplying by square root of trading periods
        annual_volatility = std_dev * Decimal(str(math.sqrt(trading_days)))
        return annual_volatility.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    return std_dev


def sharpe_ratio(
    returns: List[Numeric],
    risk_free_rate: Numeric = 0,
    annualize: bool = True
) -> Decimal:
    """
    Calculate Sharpe ratio (risk-adjusted return).
    
    Args:
        returns: List of return values
        risk_free_rate: Risk-free rate for comparison
        annualize: Whether returns and risk-free rate are annualized
        
    Returns:
        Sharpe ratio
        
    Raises:
        ValueError: If standard deviation is zero
    """
    if not returns:
        raise ValueError("Cannot calculate Sharpe ratio with empty returns")
    
    excess_returns = [to_decimal(r) - to_decimal(risk_free_rate) for r in returns]
    
    excess_mean = mean(excess_returns)
    excess_std = standard_deviation(excess_returns)
    
    if excess_std == 0:
        if excess_mean > 0:
            return Decimal('inf')
        elif excess_mean < 0:
            return Decimal('-inf')
        else:
            return Decimal('0')  # No excess return, no risk
    
    sharpe = excess_mean / excess_std
    
    # Annualize if not already annualized
    if not annualize:
        sharpe = sharpe * Decimal(str(math.sqrt(252)))  # Assume 252 trading days
    
    return sharpe.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)