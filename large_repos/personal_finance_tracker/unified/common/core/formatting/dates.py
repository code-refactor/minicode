"""
Date and time formatting utilities for financial applications.

This module provides functions for formatting dates, times, and periods
in various styles suitable for financial reports and user interfaces.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Union, List, Dict, Any
from enum import Enum
import calendar

# Import from our models
from ..models.time_period import Period, PeriodType

# Type alias
DateLike = Union[date, datetime, str]


class DateFormat(Enum):
    """Standard date formatting styles."""
    ISO = "iso"                    # 2023-12-25
    US = "us"                      # 12/25/2023
    EUROPEAN = "european"          # 25/12/2023
    LONG = "long"                  # December 25, 2023
    SHORT = "short"                # Dec 25, 2023
    COMPACT = "compact"            # 25Dec23
    RELATIVE = "relative"          # 3 days ago
    FINANCIAL = "financial"        # 25-Dec-2023


class TimeFormat(Enum):
    """Time formatting styles."""
    HOUR_24 = "24h"               # 14:30:00
    HOUR_12 = "12h"               # 2:30:00 PM
    COMPACT = "compact"           # 1430
    ISO = "iso"                   # 14:30:00.000Z


def format_date(
    date_value: DateLike,
    format_style: DateFormat = DateFormat.ISO,
    include_weekday: bool = False,
    timezone_aware: bool = False
) -> str:
    """
    Format a date according to the specified style.
    
    Args:
        date_value: Date to format
        format_style: Formatting style
        include_weekday: Whether to include weekday name
        timezone_aware: Whether to include timezone info
        
    Returns:
        Formatted date string
        
    Raises:
        ValueError: If date cannot be parsed
    """
    # Convert to date object
    if isinstance(date_value, str):
        try:
            if 'T' in date_value or ' ' in date_value:
                # Parse datetime string
                parsed_dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                date_obj = parsed_dt.date()
            else:
                # Parse date string
                date_obj = datetime.fromisoformat(date_value).date()
        except ValueError:
            # Try common formats
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d'):
                try:
                    date_obj = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Cannot parse date string: {date_value}")
    elif isinstance(date_value, datetime):
        date_obj = date_value.date()
    else:
        date_obj = date_value
    
    # Format according to style
    if format_style == DateFormat.ISO:
        formatted = date_obj.strftime('%Y-%m-%d')
    
    elif format_style == DateFormat.US:
        formatted = date_obj.strftime('%m/%d/%Y')
    
    elif format_style == DateFormat.EUROPEAN:
        formatted = date_obj.strftime('%d/%m/%Y')
    
    elif format_style == DateFormat.LONG:
        formatted = date_obj.strftime('%B %d, %Y')
    
    elif format_style == DateFormat.SHORT:
        formatted = date_obj.strftime('%b %d, %Y')
    
    elif format_style == DateFormat.COMPACT:
        formatted = date_obj.strftime('%d%b%y')
    
    elif format_style == DateFormat.FINANCIAL:
        formatted = date_obj.strftime('%d-%b-%Y')
    
    elif format_style == DateFormat.RELATIVE:
        formatted = format_relative_date(date_obj)
    
    else:
        formatted = date_obj.strftime('%Y-%m-%d')
    
    # Add weekday if requested
    if include_weekday and format_style != DateFormat.RELATIVE:
        weekday = date_obj.strftime('%A')
        formatted = f"{weekday}, {formatted}"
    
    return formatted


def format_datetime(
    datetime_value: Union[datetime, str],
    date_format: DateFormat = DateFormat.ISO,
    time_format: TimeFormat = TimeFormat.HOUR_24,
    include_seconds: bool = True,
    include_microseconds: bool = False,
    separator: str = " "
) -> str:
    """
    Format a datetime with custom date and time formats.
    
    Args:
        datetime_value: Datetime to format
        date_format: Date formatting style
        time_format: Time formatting style
        include_seconds: Whether to include seconds
        include_microseconds: Whether to include microseconds
        separator: Separator between date and time
        
    Returns:
        Formatted datetime string
    """
    # Convert to datetime object
    if isinstance(datetime_value, str):
        dt_obj = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
    else:
        dt_obj = datetime_value
    
    # Format date part
    date_part = format_date(dt_obj.date(), date_format)
    
    # Format time part
    if time_format == TimeFormat.HOUR_24:
        if include_microseconds:
            time_part = dt_obj.strftime('%H:%M:%S.%f')
        elif include_seconds:
            time_part = dt_obj.strftime('%H:%M:%S')
        else:
            time_part = dt_obj.strftime('%H:%M')
    
    elif time_format == TimeFormat.HOUR_12:
        if include_microseconds:
            time_part = dt_obj.strftime('%I:%M:%S.%f %p')
        elif include_seconds:
            time_part = dt_obj.strftime('%I:%M:%S %p')
        else:
            time_part = dt_obj.strftime('%I:%M %p')
    
    elif time_format == TimeFormat.COMPACT:
        if include_seconds:
            time_part = dt_obj.strftime('%H%M%S')
        else:
            time_part = dt_obj.strftime('%H%M')
    
    elif time_format == TimeFormat.ISO:
        if include_microseconds:
            time_part = dt_obj.strftime('%H:%M:%S.%fZ')
        elif include_seconds:
            time_part = dt_obj.strftime('%H:%M:%SZ')
        else:
            time_part = dt_obj.strftime('%H:%MZ')
    
    else:
        time_part = dt_obj.strftime('%H:%M:%S')
    
    return f"{date_part}{separator}{time_part}"


def format_relative_date(date_value: DateLike, reference_date: Optional[date] = None) -> str:
    """
    Format date as relative to reference date (e.g., "3 days ago").
    
    Args:
        date_value: Date to format
        reference_date: Reference date (defaults to today)
        
    Returns:
        Relative date string
    """
    # Convert to date
    if isinstance(date_value, str):
        date_obj = datetime.fromisoformat(date_value).date()
    elif isinstance(date_value, datetime):
        date_obj = date_value.date()
    else:
        date_obj = date_value
    
    if reference_date is None:
        reference_date = date.today()
    
    diff = (reference_date - date_obj).days
    
    if diff == 0:
        return "today"
    elif diff == 1:
        return "yesterday"
    elif diff == -1:
        return "tomorrow"
    elif diff > 1:
        if diff < 7:
            return f"{diff} days ago"
        elif diff < 30:
            weeks = diff // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif diff < 365:
            months = diff // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = diff // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    else:  # diff < -1 (future dates)
        abs_diff = abs(diff)
        if abs_diff < 7:
            return f"in {abs_diff} days"
        elif abs_diff < 30:
            weeks = abs_diff // 7
            return f"in {weeks} week{'s' if weeks > 1 else ''}"
        elif abs_diff < 365:
            months = abs_diff // 30
            return f"in {months} month{'s' if months > 1 else ''}"
        else:
            years = abs_diff // 365
            return f"in {years} year{'s' if years > 1 else ''}"


def format_period(
    period: Period,
    format_style: DateFormat = DateFormat.SHORT,
    separator: str = " to ",
    compact_same_month: bool = True
) -> str:
    """
    Format a time period for display.
    
    Args:
        period: Period to format
        format_style: Date formatting style
        separator: Separator between start and end dates
        compact_same_month: Use compact format for same-month periods
        
    Returns:
        Formatted period string
    """
    start_formatted = format_date(period.start_date, format_style)
    end_formatted = format_date(period.end_date, format_style)
    
    # Single day period
    if period.start_date == period.end_date:
        return start_formatted
    
    # Same month optimization
    if compact_same_month and period.start_date.month == period.end_date.month and period.start_date.year == period.end_date.year:
        if format_style in [DateFormat.LONG, DateFormat.SHORT]:
            # Format as "Dec 1-15, 2023"
            start_day = period.start_date.day
            end_formatted = format_date(period.end_date, format_style)
            month_name = period.start_date.strftime('%b' if format_style == DateFormat.SHORT else '%B')
            return f"{month_name} {start_day}-{period.end_date.day}, {period.end_date.year}"
    
    return f"{start_formatted}{separator}{end_formatted}"


def format_duration(
    duration: Union[timedelta, int, float],
    style: str = "verbose",  # "verbose", "compact", "short"
    max_units: int = 2
) -> str:
    """
    Format a duration for display.
    
    Args:
        duration: Duration as timedelta or seconds
        style: Formatting style
        max_units: Maximum number of time units to show
        
    Returns:
        Formatted duration string
    """
    # Convert to timedelta if needed
    if isinstance(duration, (int, float)):
        td = timedelta(seconds=duration)
    else:
        td = duration
    
    total_seconds = int(td.total_seconds())
    
    if total_seconds == 0:
        return "0 seconds" if style == "verbose" else "0s"
    
    # Calculate components
    years = total_seconds // (365 * 24 * 3600)
    remaining = total_seconds % (365 * 24 * 3600)
    
    months = remaining // (30 * 24 * 3600)
    remaining = remaining % (30 * 24 * 3600)
    
    days = remaining // (24 * 3600)
    remaining = remaining % (24 * 3600)
    
    hours = remaining // 3600
    remaining = remaining % 3600
    
    minutes = remaining // 60
    seconds = remaining % 60
    
    # Build components list
    components = []
    
    if years > 0:
        if style == "verbose":
            components.append(f"{years} year{'s' if years > 1 else ''}")
        elif style == "compact":
            components.append(f"{years}y")
        else:
            components.append(f"{years}yr")
    
    if months > 0:
        if style == "verbose":
            components.append(f"{months} month{'s' if months > 1 else ''}")
        elif style == "compact":
            components.append(f"{months}mo")
        else:
            components.append(f"{months}m")
    
    if days > 0:
        if style == "verbose":
            components.append(f"{days} day{'s' if days > 1 else ''}")
        elif style == "compact":
            components.append(f"{days}d")
        else:
            components.append(f"{days}d")
    
    if hours > 0:
        if style == "verbose":
            components.append(f"{hours} hour{'s' if hours > 1 else ''}")
        elif style == "compact":
            components.append(f"{hours}h")
        else:
            components.append(f"{hours}h")
    
    if minutes > 0:
        if style == "verbose":
            components.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        elif style == "compact":
            components.append(f"{minutes}m")
        else:
            components.append(f"{minutes}min")
    
    if seconds > 0:
        if style == "verbose":
            components.append(f"{seconds} second{'s' if seconds > 1 else ''}")
        elif style == "compact":
            components.append(f"{seconds}s")
        else:
            components.append(f"{seconds}s")
    
    # Limit to max_units
    components = components[:max_units]
    
    if not components:
        return "0 seconds" if style == "verbose" else "0s"
    
    # Join components
    if style == "verbose":
        if len(components) == 1:
            return components[0]
        elif len(components) == 2:
            return f"{components[0]} and {components[1]}"
        else:
            return ", ".join(components[:-1]) + f", and {components[-1]}"
    else:
        return " ".join(components)


def format_period_type_name(period_type: PeriodType, plural: bool = False) -> str:
    """
    Format a period type as a human-readable name.
    
    Args:
        period_type: Period type to format
        plural: Whether to return plural form
        
    Returns:
        Human-readable period type name
    """
    names = {
        PeriodType.DAILY: ("day", "days"),
        PeriodType.WEEKLY: ("week", "weeks"),
        PeriodType.BIWEEKLY: ("biweek", "biweeks"),
        PeriodType.MONTHLY: ("month", "months"),
        PeriodType.QUARTERLY: ("quarter", "quarters"),
        PeriodType.SEMIANNUALLY: ("semiannual", "semiannuals"),
        PeriodType.ANNUALLY: ("year", "years"),
        PeriodType.CUSTOM: ("custom period", "custom periods"),
    }
    
    singular, plural_form = names.get(period_type, (period_type.value, f"{period_type.value}s"))
    return plural_form if plural else singular


def format_business_date_range(
    start_date: DateLike,
    end_date: DateLike,
    exclude_weekends: bool = True
) -> str:
    """
    Format a business date range with business day count.
    
    Args:
        start_date: Start date
        end_date: End date
        exclude_weekends: Whether to exclude weekends from count
        
    Returns:
        Formatted business date range with day count
    """
    # Convert to date objects
    if isinstance(start_date, str):
        start_obj = datetime.fromisoformat(start_date).date()
    elif isinstance(start_date, datetime):
        start_obj = start_date.date()
    else:
        start_obj = start_date
    
    if isinstance(end_date, str):
        end_obj = datetime.fromisoformat(end_date).date()
    elif isinstance(end_date, datetime):
        end_obj = end_date.date()
    else:
        end_obj = end_date
    
    # Format the period
    period_str = format_period(Period(start_obj, end_obj), DateFormat.SHORT)
    
    # Count business days
    if exclude_weekends:
        business_days = 0
        current = start_obj
        while current <= end_obj:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            current += timedelta(days=1)
        
        if business_days == 1:
            return f"{period_str} (1 business day)"
        else:
            return f"{period_str} ({business_days} business days)"
    else:
        total_days = (end_obj - start_obj).days + 1
        if total_days == 1:
            return f"{period_str} (1 day)"
        else:
            return f"{period_str} ({total_days} days)"


def format_fiscal_period(
    period: Period,
    fiscal_year_start_month: int = 1,
    format_style: DateFormat = DateFormat.SHORT
) -> str:
    """
    Format a period with fiscal context.
    
    Args:
        period: Period to format
        fiscal_year_start_month: Starting month of fiscal year (1-12)
        format_style: Date formatting style
        
    Returns:
        Formatted fiscal period string
    """
    # Determine fiscal year
    start_date = period.start_date
    
    if fiscal_year_start_month == 1:
        # Calendar year = fiscal year
        fiscal_year = start_date.year
        fy_suffix = ""
    else:
        # Fiscal year spans calendar years
        if start_date.month >= fiscal_year_start_month:
            fiscal_year = start_date.year + 1
        else:
            fiscal_year = start_date.year
        fy_suffix = f" (FY{fiscal_year})"
    
    period_str = format_period(period, format_style)
    
    return f"{period_str}{fy_suffix}"


def get_quarter_name(date_value: DateLike, fiscal_year_start_month: int = 1) -> str:
    """
    Get quarter name for a date.
    
    Args:
        date_value: Date to get quarter for
        fiscal_year_start_month: Starting month of fiscal year
        
    Returns:
        Quarter name (e.g., "Q1 2023")
    """
    # Convert to date
    if isinstance(date_value, str):
        date_obj = datetime.fromisoformat(date_value).date()
    elif isinstance(date_value, datetime):
        date_obj = date_value.date()
    else:
        date_obj = date_value
    
    # Calculate quarter
    if fiscal_year_start_month == 1:
        # Calendar quarters
        quarter = (date_obj.month - 1) // 3 + 1
        year = date_obj.year
    else:
        # Fiscal quarters
        months_from_fy_start = (date_obj.month - fiscal_year_start_month) % 12
        quarter = months_from_fy_start // 3 + 1
        
        if date_obj.month >= fiscal_year_start_month:
            year = date_obj.year + 1
        else:
            year = date_obj.year
    
    return f"Q{quarter} {year}"


def format_date_list(
    dates: List[DateLike],
    format_style: DateFormat = DateFormat.SHORT,
    max_items: int = 5,
    conjunction: str = "and"
) -> str:
    """
    Format a list of dates as a readable string.
    
    Args:
        dates: List of dates to format
        format_style: Date formatting style
        max_items: Maximum items to show before truncating
        conjunction: Conjunction word for final item
        
    Returns:
        Formatted date list string
    """
    if not dates:
        return ""
    
    # Format dates
    formatted_dates = [format_date(d, format_style) for d in dates]
    
    # Truncate if needed
    if len(formatted_dates) > max_items:
        shown_dates = formatted_dates[:max_items]
        remaining = len(formatted_dates) - max_items
        if len(shown_dates) == 1:
            return f"{shown_dates[0]} and {remaining} other{'s' if remaining > 1 else ''}"
        else:
            return f"{', '.join(shown_dates[:-1])}, {shown_dates[-1]}, and {remaining} other{'s' if remaining > 1 else ''}"
    
    # Format list
    if len(formatted_dates) == 1:
        return formatted_dates[0]
    elif len(formatted_dates) == 2:
        return f"{formatted_dates[0]} {conjunction} {formatted_dates[1]}"
    else:
        return f"{', '.join(formatted_dates[:-1])}, {conjunction} {formatted_dates[-1]}"