"""
Financial calculation utilities for common financial operations.

This module provides functions for calculating percentages, changes,
returns, and other financial metrics used across both persona implementations.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional, List, Tuple
import math

# Type alias for numeric types
Numeric = Union[int, float, Decimal]


def to_decimal(value: Numeric) -> Decimal:
    """
    Convert a numeric value to Decimal for precise calculations.
    
    Args:
        value: Numeric value to convert
        
    Returns:
        Decimal representation
        
    Raises:
        ValueError: If value cannot be converted
    """
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def percentage_change(old_value: Numeric, new_value: Numeric) -> Decimal:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change as decimal (0.15 = 15%)
        
    Raises:
        ValueError: If old_value is zero
    """
    old_decimal = to_decimal(old_value)
    new_decimal = to_decimal(new_value)
    
    if old_decimal == 0:
        if new_decimal == 0:
            return Decimal('0')
        raise ValueError("Cannot calculate percentage change when old value is zero")
    
    change = (new_decimal - old_decimal) / old_decimal
    return change.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def absolute_change(old_value: Numeric, new_value: Numeric) -> Decimal:
    """
    Calculate absolute change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Absolute change
    """
    old_decimal = to_decimal(old_value)
    new_decimal = to_decimal(new_value)
    
    return new_decimal - old_decimal


def percentage_of_total(part: Numeric, total: Numeric) -> Decimal:
    """
    Calculate what percentage a part is of the total.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage as decimal (0.25 = 25%)
        
    Raises:
        ValueError: If total is zero
    """
    part_decimal = to_decimal(part)
    total_decimal = to_decimal(total)
    
    if total_decimal == 0:
        if part_decimal == 0:
            return Decimal('0')
        raise ValueError("Cannot calculate percentage when total is zero")
    
    percentage = part_decimal / total_decimal
    return percentage.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def apply_percentage(base_value: Numeric, percentage: Numeric) -> Decimal:
    """
    Apply a percentage to a base value.
    
    Args:
        base_value: Base value to apply percentage to
        percentage: Percentage as decimal (0.15 = 15%)
        
    Returns:
        Result of applying percentage
    """
    base_decimal = to_decimal(base_value)
    percentage_decimal = to_decimal(percentage)
    
    result = base_decimal * percentage_decimal
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def compound_growth_rate(
    initial_value: Numeric,
    final_value: Numeric,
    periods: int
) -> Decimal:
    """
    Calculate compound annual growth rate (CAGR).
    
    Args:
        initial_value: Starting value
        final_value: Ending value
        periods: Number of periods
        
    Returns:
        Growth rate as decimal (0.08 = 8%)
        
    Raises:
        ValueError: If initial_value is zero or negative, or periods is zero
    """
    initial_decimal = to_decimal(initial_value)
    final_decimal = to_decimal(final_value)
    
    if initial_decimal <= 0:
        raise ValueError("Initial value must be positive")
    
    if periods == 0:
        raise ValueError("Number of periods cannot be zero")
    
    if periods < 0:
        raise ValueError("Number of periods must be positive")
    
    # CAGR = (Final/Initial)^(1/periods) - 1
    ratio = float(final_decimal / initial_decimal)
    if ratio <= 0:
        raise ValueError("Cannot calculate growth rate with negative or zero final value")
    
    growth_rate = Decimal(str(ratio ** (1.0 / periods) - 1))
    return growth_rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def simple_interest(
    principal: Numeric,
    rate: Numeric,
    time_periods: Numeric
) -> Decimal:
    """
    Calculate simple interest.
    
    Args:
        principal: Principal amount
        rate: Interest rate per period as decimal (0.05 = 5%)
        time_periods: Number of time periods
        
    Returns:
        Interest amount
    """
    principal_decimal = to_decimal(principal)
    rate_decimal = to_decimal(rate)
    time_decimal = to_decimal(time_periods)
    
    interest = principal_decimal * rate_decimal * time_decimal
    return interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def compound_interest(
    principal: Numeric,
    rate: Numeric,
    time_periods: Numeric,
    compounding_frequency: int = 1
) -> Decimal:
    """
    Calculate compound interest.
    
    Args:
        principal: Principal amount
        rate: Annual interest rate as decimal (0.05 = 5%)
        time_periods: Number of years
        compounding_frequency: Times compounded per year (default 1)
        
    Returns:
        Final amount (principal + interest)
    """
    principal_decimal = to_decimal(principal)
    rate_decimal = to_decimal(rate)
    time_decimal = to_decimal(time_periods)
    frequency_decimal = to_decimal(compounding_frequency)
    
    # A = P(1 + r/n)^(nt)
    rate_per_period = rate_decimal / frequency_decimal
    total_periods = frequency_decimal * time_decimal
    
    # Use float for exponentiation, then convert back to Decimal
    base = float(1 + rate_per_period)
    exponent = float(total_periods)
    
    final_amount = principal_decimal * Decimal(str(base ** exponent))
    return final_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def present_value(
    future_value: Numeric,
    rate: Numeric,
    periods: int
) -> Decimal:
    """
    Calculate present value of a future amount.
    
    Args:
        future_value: Future value
        rate: Discount rate per period as decimal
        periods: Number of periods
        
    Returns:
        Present value
    """
    future_decimal = to_decimal(future_value)
    rate_decimal = to_decimal(rate)
    
    if periods == 0:
        return future_decimal
    
    # PV = FV / (1 + r)^n
    discount_factor = Decimal(str((1 + float(rate_decimal)) ** (-periods)))
    present_val = future_decimal * discount_factor
    
    return present_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def future_value(
    present_value: Numeric,
    rate: Numeric,
    periods: int
) -> Decimal:
    """
    Calculate future value of a present amount.
    
    Args:
        present_value: Present value
        rate: Growth rate per period as decimal
        periods: Number of periods
        
    Returns:
        Future value
    """
    present_decimal = to_decimal(present_value)
    rate_decimal = to_decimal(rate)
    
    if periods == 0:
        return present_decimal
    
    # FV = PV * (1 + r)^n
    growth_factor = Decimal(str((1 + float(rate_decimal)) ** periods))
    future_val = present_decimal * growth_factor
    
    return future_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def net_present_value(
    cash_flows: List[Numeric],
    discount_rate: Numeric
) -> Decimal:
    """
    Calculate net present value of cash flows.
    
    Args:
        cash_flows: List of cash flows (negative for outflows, positive for inflows)
        discount_rate: Discount rate as decimal
        
    Returns:
        Net present value
    """
    if not cash_flows:
        return Decimal('0')
    
    rate_decimal = to_decimal(discount_rate)
    npv = Decimal('0')
    
    for period, cash_flow in enumerate(cash_flows):
        cash_flow_decimal = to_decimal(cash_flow)
        pv = present_value(cash_flow_decimal, rate_decimal, period)
        npv += pv
    
    return npv.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def internal_rate_of_return(
    cash_flows: List[Numeric],
    guess: Numeric = 0.1,
    tolerance: Numeric = 1e-6,
    max_iterations: int = 100
) -> Optional[Decimal]:
    """
    Calculate internal rate of return using Newton-Raphson method.
    
    Args:
        cash_flows: List of cash flows (first should be negative)
        guess: Initial guess for IRR
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations
        
    Returns:
        IRR as decimal or None if not found
    """
    if not cash_flows or len(cash_flows) < 2:
        return None
    
    # Convert to Decimal
    cf_decimals = [to_decimal(cf) for cf in cash_flows]
    guess_decimal = to_decimal(guess)
    tolerance_decimal = to_decimal(tolerance)
    
    current_guess = guess_decimal
    
    for _ in range(max_iterations):
        # Calculate NPV and its derivative
        npv = Decimal('0')
        npv_derivative = Decimal('0')
        
        for period, cash_flow in enumerate(cf_decimals):
            if current_guess == -1:
                # Avoid division by zero
                current_guess += tolerance_decimal
            
            discount_factor = (1 + current_guess) ** (-period)
            npv += cash_flow * Decimal(str(discount_factor))
            
            if period > 0:
                derivative_term = -period * cash_flow * Decimal(str(discount_factor)) / (1 + current_guess)
                npv_derivative += derivative_term
        
        if abs(npv) < tolerance_decimal:
            return current_guess.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        
        if npv_derivative == 0:
            return None  # Cannot continue
        
        # Newton-Raphson iteration
        current_guess = current_guess - npv / npv_derivative
    
    return None  # Did not converge


def break_even_point(
    fixed_costs: Numeric,
    price_per_unit: Numeric,
    variable_cost_per_unit: Numeric
) -> Decimal:
    """
    Calculate break-even point in units.
    
    Args:
        fixed_costs: Fixed costs
        price_per_unit: Selling price per unit
        variable_cost_per_unit: Variable cost per unit
        
    Returns:
        Break-even quantity in units
        
    Raises:
        ValueError: If contribution margin is zero or negative
    """
    fixed_decimal = to_decimal(fixed_costs)
    price_decimal = to_decimal(price_per_unit)
    variable_decimal = to_decimal(variable_cost_per_unit)
    
    contribution_margin = price_decimal - variable_decimal
    
    if contribution_margin <= 0:
        raise ValueError("Contribution margin must be positive (price > variable cost)")
    
    break_even_units = fixed_decimal / contribution_margin
    return break_even_units.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def return_on_investment(
    gain: Numeric,
    cost: Numeric
) -> Decimal:
    """
    Calculate return on investment (ROI).
    
    Args:
        gain: Gain from investment
        cost: Cost of investment
        
    Returns:
        ROI as decimal (0.25 = 25%)
        
    Raises:
        ValueError: If cost is zero
    """
    gain_decimal = to_decimal(gain)
    cost_decimal = to_decimal(cost)
    
    if cost_decimal == 0:
        raise ValueError("Cost cannot be zero for ROI calculation")
    
    roi = gain_decimal / cost_decimal
    return roi.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def weighted_average(
    values: List[Numeric],
    weights: List[Numeric]
) -> Decimal:
    """
    Calculate weighted average.
    
    Args:
        values: List of values
        weights: List of corresponding weights
        
    Returns:
        Weighted average
        
    Raises:
        ValueError: If lists have different lengths or sum of weights is zero
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights lists must have the same length")
    
    if not values:
        return Decimal('0')
    
    value_decimals = [to_decimal(v) for v in values]
    weight_decimals = [to_decimal(w) for w in weights]
    
    total_weight = sum(weight_decimals)
    if total_weight == 0:
        raise ValueError("Sum of weights cannot be zero")
    
    weighted_sum = sum(v * w for v, w in zip(value_decimals, weight_decimals))
    weighted_avg = weighted_sum / total_weight
    
    return weighted_avg.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def annualized_return(
    total_return: Numeric,
    holding_period_days: int
) -> Decimal:
    """
    Calculate annualized return from total return and holding period.
    
    Args:
        total_return: Total return as decimal (0.25 = 25%)
        holding_period_days: Holding period in days
        
    Returns:
        Annualized return as decimal
        
    Raises:
        ValueError: If holding period is zero or negative
    """
    if holding_period_days <= 0:
        raise ValueError("Holding period must be positive")
    
    total_return_decimal = to_decimal(total_return)
    days_per_year = Decimal('365.25')  # Account for leap years
    
    # Annualized return = (1 + total_return)^(365.25/days) - 1
    holding_years = holding_period_days / days_per_year
    annualized = Decimal(str((1 + float(total_return_decimal)) ** (1 / float(holding_years)) - 1))
    
    return annualized.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def tax_adjusted_return(
    gross_return: Numeric,
    tax_rate: Numeric
) -> Decimal:
    """
    Calculate after-tax return.
    
    Args:
        gross_return: Gross return as decimal
        tax_rate: Tax rate as decimal (0.25 = 25%)
        
    Returns:
        After-tax return as decimal
    """
    gross_decimal = to_decimal(gross_return)
    tax_rate_decimal = to_decimal(tax_rate)
    
    after_tax_return = gross_decimal * (1 - tax_rate_decimal)
    return after_tax_return.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def inflation_adjusted_value(
    nominal_value: Numeric,
    inflation_rate: Numeric,
    periods: int
) -> Decimal:
    """
    Calculate inflation-adjusted (real) value.
    
    Args:
        nominal_value: Nominal value
        inflation_rate: Inflation rate per period as decimal
        periods: Number of periods
        
    Returns:
        Real value adjusted for inflation
    """
    nominal_decimal = to_decimal(nominal_value)
    inflation_decimal = to_decimal(inflation_rate)
    
    # Real value = Nominal / (1 + inflation)^periods
    inflation_factor = Decimal(str((1 + float(inflation_decimal)) ** periods))
    real_value = nominal_decimal / inflation_factor
    
    return real_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)