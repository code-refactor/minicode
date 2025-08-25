"""
Core model classes and utilities for the personal finance system.

This package provides foundational classes that both persona implementations
can inherit from and extend, including transaction handling, money operations,
and time period management.
"""

from .base import (
    BaseTransaction,
    BasePortfolio,
    BaseConfiguration,
    TransactionType,
    ValidationMixin,
    AuditMixin,
)
from .money import (
    Money,
    Currency,
    sum_money,
    average_money,
)
from .time_period import (
    Period,
    PeriodType,
    Weekday,
    RecurringSchedule,
    get_business_days_between,
    get_quarter_dates,
    get_fiscal_year_dates,
)

__all__ = [
    # Base classes
    "BaseTransaction",
    "BasePortfolio", 
    "BaseConfiguration",
    "TransactionType",
    "ValidationMixin",
    "AuditMixin",
    
    # Money classes
    "Money",
    "Currency",
    "sum_money",
    "average_money",
    
    # Time period classes
    "Period",
    "PeriodType",
    "Weekday",
    "RecurringSchedule",
    "get_business_days_between",
    "get_quarter_dates",
    "get_fiscal_year_dates",
]