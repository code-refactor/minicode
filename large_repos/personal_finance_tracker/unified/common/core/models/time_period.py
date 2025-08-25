"""
Time period handling and date utilities for financial calculations.

This module provides classes and utilities for working with time periods,
date ranges, and recurring financial events.
"""

from datetime import datetime, date, timedelta
from typing import Iterator, Optional, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum
import calendar


class PeriodType(Enum):
    """Standard period types for financial calculations."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUALLY = "semiannually"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class Weekday(Enum):
    """Days of the week."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass(frozen=True)
class Period:
    """
    Immutable time period with start and end dates.
    
    Represents a specific time range for financial analysis
    with utilities for period operations and calculations.
    """
    
    start_date: date
    end_date: date
    
    def __post_init__(self):
        """Validate period after initialization."""
        if self.start_date > self.end_date:
            raise ValueError(f"Start date {self.start_date} cannot be after end date {self.end_date}")
    
    @classmethod
    def from_dates(cls, start: Union[date, datetime], end: Union[date, datetime]) -> 'Period':
        """
        Create period from date or datetime objects.
        
        Args:
            start: Start date/datetime
            end: End date/datetime
            
        Returns:
            Period instance
        """
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end
        return cls(start_date, end_date)
    
    @classmethod
    def single_day(cls, day: Union[date, datetime]) -> 'Period':
        """
        Create a single-day period.
        
        Args:
            day: The date for the period
            
        Returns:
            Period instance covering just that day
        """
        period_date = day.date() if isinstance(day, datetime) else day
        return cls(period_date, period_date)
    
    @classmethod
    def current_month(cls, reference_date: Optional[date] = None) -> 'Period':
        """
        Create period for current month.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Period covering the entire month
        """
        ref = reference_date or date.today()
        start_date = ref.replace(day=1)
        
        # Last day of month
        if ref.month == 12:
            next_month = ref.replace(year=ref.year + 1, month=1, day=1)
        else:
            next_month = ref.replace(month=ref.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
        
        return cls(start_date, end_date)
    
    @classmethod
    def current_quarter(cls, reference_date: Optional[date] = None) -> 'Period':
        """
        Create period for current quarter.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Period covering the entire quarter
        """
        ref = reference_date or date.today()
        
        # Determine quarter
        quarter = (ref.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        
        start_date = ref.replace(month=start_month, day=1)
        
        # End of quarter
        end_month = start_month + 2
        if end_month == 12:
            next_year_start = ref.replace(year=ref.year + 1, month=1, day=1)
        else:
            next_year_start = ref.replace(month=end_month + 1, day=1)
        end_date = next_year_start - timedelta(days=1)
        
        return cls(start_date, end_date)
    
    @classmethod
    def current_year(cls, reference_date: Optional[date] = None) -> 'Period':
        """
        Create period for current year.
        
        Args:
            reference_date: Reference date (defaults to today)
            
        Returns:
            Period covering the entire year
        """
        ref = reference_date or date.today()
        start_date = ref.replace(month=1, day=1)
        end_date = ref.replace(month=12, day=31)
        return cls(start_date, end_date)
    
    @classmethod
    def last_n_days(cls, n: int, reference_date: Optional[date] = None) -> 'Period':
        """
        Create period for last N days.
        
        Args:
            n: Number of days
            reference_date: Reference date (defaults to today)
            
        Returns:
            Period covering last n days
        """
        ref = reference_date or date.today()
        start_date = ref - timedelta(days=n - 1)
        return cls(start_date, ref)
    
    @classmethod
    def next_n_days(cls, n: int, reference_date: Optional[date] = None) -> 'Period':
        """
        Create period for next N days.
        
        Args:
            n: Number of days
            reference_date: Reference date (defaults to today)
            
        Returns:
            Period covering next n days
        """
        ref = reference_date or date.today()
        end_date = ref + timedelta(days=n - 1)
        return cls(ref, end_date)
    
    def duration_days(self) -> int:
        """Get duration in days (inclusive)."""
        return (self.end_date - self.start_date).days + 1
    
    def duration_weeks(self) -> float:
        """Get duration in weeks."""
        return self.duration_days() / 7.0
    
    def duration_months(self) -> float:
        """Get approximate duration in months."""
        return self.duration_days() / 30.44  # Average days per month
    
    def contains_date(self, check_date: Union[date, datetime]) -> bool:
        """
        Check if a date falls within this period.
        
        Args:
            check_date: Date to check
            
        Returns:
            True if date is within period (inclusive)
        """
        check = check_date.date() if isinstance(check_date, datetime) else check_date
        return self.start_date <= check <= self.end_date
    
    def overlaps_with(self, other: 'Period') -> bool:
        """
        Check if this period overlaps with another.
        
        Args:
            other: Other period to check
            
        Returns:
            True if periods overlap
        """
        return not (self.end_date < other.start_date or self.start_date > other.end_date)
    
    def intersection(self, other: 'Period') -> Optional['Period']:
        """
        Get intersection with another period.
        
        Args:
            other: Other period
            
        Returns:
            Intersection period or None if no overlap
        """
        if not self.overlaps_with(other):
            return None
        
        start = max(self.start_date, other.start_date)
        end = min(self.end_date, other.end_date)
        return Period(start, end)
    
    def union(self, other: 'Period') -> 'Period':
        """
        Get union with another period.
        
        Args:
            other: Other period
            
        Returns:
            Combined period covering both periods
        """
        start = min(self.start_date, other.start_date)
        end = max(self.end_date, other.end_date)
        return Period(start, end)
    
    def split_by_months(self) -> List['Period']:
        """
        Split period into monthly sub-periods.
        
        Returns:
            List of Period objects, one for each month
        """
        periods = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Start of current month period
            month_start = current_date
            
            # End of current month period
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            
            month_end = min(next_month - timedelta(days=1), self.end_date)
            
            periods.append(Period(month_start, month_end))
            current_date = next_month
        
        return periods
    
    def split_by_weeks(self) -> List['Period']:
        """
        Split period into weekly sub-periods.
        
        Returns:
            List of Period objects, one for each week
        """
        periods = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Calculate end of current week (Sunday)
            days_until_sunday = (6 - current_date.weekday()) % 7
            week_end = min(current_date + timedelta(days=days_until_sunday), self.end_date)
            
            periods.append(Period(current_date, week_end))
            current_date = week_end + timedelta(days=1)
        
        return periods
    
    def get_business_days(self) -> List[date]:
        """
        Get all business days (Monday-Friday) in the period.
        
        Returns:
            List of business day dates
        """
        business_days = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    def get_weekend_days(self) -> List[date]:
        """
        Get all weekend days (Saturday-Sunday) in the period.
        
        Returns:
            List of weekend day dates
        """
        weekend_days = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                weekend_days.append(current_date)
            current_date += timedelta(days=1)
        
        return weekend_days
    
    def iter_days(self) -> Iterator[date]:
        """
        Iterate over all days in the period.
        
        Yields:
            Each date in the period
        """
        current_date = self.start_date
        while current_date <= self.end_date:
            yield current_date
            current_date += timedelta(days=1)
    
    def __str__(self) -> str:
        """String representation of the period."""
        if self.start_date == self.end_date:
            return str(self.start_date)
        return f"{self.start_date} to {self.end_date}"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Period({self.start_date!r}, {self.end_date!r})"


class RecurringSchedule:
    """
    Generator for recurring dates based on various patterns.
    
    Useful for generating payment dates, billing cycles, and other
    recurring financial events.
    """
    
    def __init__(
        self,
        period_type: PeriodType,
        start_date: date,
        interval: int = 1,
        end_date: Optional[date] = None,
        max_occurrences: Optional[int] = None,
        custom_days: Optional[int] = None
    ):
        """
        Initialize recurring schedule.
        
        Args:
            period_type: Type of recurring period
            start_date: Start date for recurrence
            interval: Interval between occurrences (default 1)
            end_date: Optional end date for recurrence
            max_occurrences: Optional maximum number of occurrences
            custom_days: Number of days for CUSTOM period type
            
        Raises:
            ValueError: If parameters are invalid
        """
        self.period_type = period_type
        self.start_date = start_date
        self.interval = interval
        self.end_date = end_date
        self.max_occurrences = max_occurrences
        self.custom_days = custom_days
        
        if interval < 1:
            raise ValueError("Interval must be positive")
        
        if period_type == PeriodType.CUSTOM and custom_days is None:
            raise ValueError("custom_days required for CUSTOM period type")
        
        if end_date and end_date < start_date:
            raise ValueError("End date cannot be before start date")
    
    def generate_dates(self) -> Iterator[date]:
        """
        Generate recurring dates according to the schedule.
        
        Yields:
            Each occurrence date
        """
        current_date = self.start_date
        count = 0
        
        while True:
            # Check termination conditions
            if self.end_date and current_date > self.end_date:
                break
            if self.max_occurrences and count >= self.max_occurrences:
                break
            
            yield current_date
            count += 1
            
            # Calculate next occurrence
            if self.period_type == PeriodType.DAILY:
                current_date += timedelta(days=self.interval)
            elif self.period_type == PeriodType.WEEKLY:
                current_date += timedelta(weeks=self.interval)
            elif self.period_type == PeriodType.BIWEEKLY:
                current_date += timedelta(weeks=2 * self.interval)
            elif self.period_type == PeriodType.MONTHLY:
                current_date = self._add_months(current_date, self.interval)
            elif self.period_type == PeriodType.QUARTERLY:
                current_date = self._add_months(current_date, 3 * self.interval)
            elif self.period_type == PeriodType.SEMIANNUALLY:
                current_date = self._add_months(current_date, 6 * self.interval)
            elif self.period_type == PeriodType.ANNUALLY:
                current_date = self._add_months(current_date, 12 * self.interval)
            elif self.period_type == PeriodType.CUSTOM:
                current_date += timedelta(days=self.custom_days * self.interval)
    
    def get_next_n_dates(self, n: int) -> List[date]:
        """
        Get the next N occurrence dates.
        
        Args:
            n: Number of dates to return
            
        Returns:
            List of next n occurrence dates
        """
        dates = []
        generator = self.generate_dates()
        
        try:
            for _ in range(n):
                dates.append(next(generator))
        except StopIteration:
            pass  # Reached end of schedule
        
        return dates
    
    def get_dates_in_period(self, period: Period) -> List[date]:
        """
        Get all occurrence dates within a specific period.
        
        Args:
            period: Period to check for occurrences
            
        Returns:
            List of occurrence dates within the period
        """
        dates = []
        
        for occurrence_date in self.generate_dates():
            if period.contains_date(occurrence_date):
                dates.append(occurrence_date)
            elif occurrence_date > period.end_date:
                break  # Past the period, stop searching
        
        return dates
    
    @staticmethod
    def _add_months(start_date: date, months: int) -> date:
        """
        Add months to a date, handling edge cases.
        
        Args:
            start_date: Starting date
            months: Number of months to add
            
        Returns:
            New date with months added
        """
        # Calculate target year and month
        month = start_date.month - 1 + months
        year = start_date.year + month // 12
        month = month % 12 + 1
        
        # Handle day overflow (e.g., Jan 31 + 1 month should be Feb 28/29)
        day = start_date.day
        max_day = calendar.monthrange(year, month)[1]
        if day > max_day:
            day = max_day
        
        return start_date.replace(year=year, month=month, day=day)


def get_business_days_between(start_date: date, end_date: date) -> int:
    """
    Count business days between two dates (exclusive of end_date).
    
    Args:
        start_date: Start date
        end_date: End date (exclusive)
        
    Returns:
        Number of business days
    """
    if start_date >= end_date:
        return 0
    
    # Use numpy business day calculation if available, otherwise manual
    business_days = 0
    current_date = start_date
    
    while current_date < end_date:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def get_quarter_dates(year: int, quarter: int) -> Tuple[date, date]:
    """
    Get start and end dates for a specific quarter.
    
    Args:
        year: Year
        quarter: Quarter number (1-4)
        
    Returns:
        Tuple of (start_date, end_date)
        
    Raises:
        ValueError: If quarter is not 1-4
    """
    if quarter not in [1, 2, 3, 4]:
        raise ValueError("Quarter must be 1, 2, 3, or 4")
    
    start_month = (quarter - 1) * 3 + 1
    start_date = date(year, start_month, 1)
    
    # End of quarter
    end_month = start_month + 2
    if end_month == 12:
        end_date = date(year, 12, 31)
    else:
        next_quarter_start = date(year, end_month + 1, 1)
        end_date = next_quarter_start - timedelta(days=1)
    
    return start_date, end_date


def get_fiscal_year_dates(fiscal_year: int, fiscal_year_start_month: int = 1) -> Tuple[date, date]:
    """
    Get start and end dates for a fiscal year.
    
    Args:
        fiscal_year: The fiscal year
        fiscal_year_start_month: Month that fiscal year starts (1-12)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if fiscal_year_start_month == 1:
        # Calendar year
        return date(fiscal_year, 1, 1), date(fiscal_year, 12, 31)
    else:
        # Fiscal year spans two calendar years
        start_year = fiscal_year - 1 if fiscal_year_start_month > 1 else fiscal_year
        start_date = date(start_year, fiscal_year_start_month, 1)
        
        # End is last day of month before next fiscal year starts
        end_month = fiscal_year_start_month - 1
        if end_month == 0:
            end_month = 12
            end_year = fiscal_year
        else:
            end_year = fiscal_year
        
        # Last day of end month
        last_day = calendar.monthrange(end_year, end_month)[1]
        end_date = date(end_year, end_month, last_day)
        
        return start_date, end_date