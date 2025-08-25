"""
Time-based aggregation utilities for financial data.

This module provides functions for aggregating financial data across
different time periods and creating summaries for analysis.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

# Import from our models
from ..models.time_period import Period, PeriodType
from ..models.money import Money

# Type aliases
Numeric = Union[int, float, Decimal]
DateLike = Union[date, datetime]


class AggregationType(Enum):
    """Types of aggregation operations."""
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    MIN = "minimum"
    MAX = "maximum"
    MEDIAN = "median"
    FIRST = "first"
    LAST = "last"


@dataclass
class TimeSeriesDataPoint:
    """
    A single data point in a time series.
    """
    date: date
    value: Union[Decimal, Money]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Convert date if datetime
        if isinstance(self.date, datetime):
            self.date = self.date.date()
        
        # Convert value to Decimal if numeric
        if isinstance(self.value, (int, float)) and not isinstance(self.value, Money):
            self.value = Decimal(str(self.value))


@dataclass
class AggregationResult:
    """
    Result of an aggregation operation.
    """
    period: Period
    aggregation_type: AggregationType
    value: Union[Decimal, Money, int]
    count: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TimeSeriesAggregator:
    """
    Aggregates time series data across different time periods.
    
    Provides methods to aggregate financial data by various time periods
    such as daily, weekly, monthly, quarterly, and yearly.
    """
    
    def __init__(self, data_points: List[TimeSeriesDataPoint]):
        """
        Initialize aggregator with time series data.
        
        Args:
            data_points: List of time series data points
        """
        self.data_points = sorted(data_points, key=lambda x: x.date)
        self._validate_data()
    
    def _validate_data(self) -> None:
        """Validate that all data points have consistent value types."""
        if not self.data_points:
            return
        
        # Check that all values are the same type (all Decimal, all Money, etc.)
        first_type = type(self.data_points[0].value)
        
        # Special handling for Money - all must have same currency
        if first_type == Money:
            first_currency = self.data_points[0].value.currency
            for point in self.data_points[1:]:
                if not isinstance(point.value, Money):
                    raise ValueError("Mixed value types: all values must be Money objects")
                if point.value.currency != first_currency:
                    raise ValueError(f"Mixed currencies: {point.value.currency} != {first_currency}")
        else:
            for point in self.data_points[1:]:
                if type(point.value) != first_type:
                    raise ValueError(f"Mixed value types: {type(point.value)} != {first_type}")
    
    def aggregate_by_period_type(
        self,
        period_type: PeriodType,
        aggregation_type: AggregationType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AggregationResult]:
        """
        Aggregate data by period type.
        
        Args:
            period_type: Type of period for aggregation
            aggregation_type: Type of aggregation operation
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of aggregation results for each period
        """
        if not self.data_points:
            return []
        
        # Filter data by date range if provided
        filtered_data = self._filter_by_date_range(start_date, end_date)
        if not filtered_data:
            return []
        
        # Generate periods based on period type
        periods = self._generate_periods(period_type, filtered_data)
        
        # Aggregate data for each period
        results = []
        for period in periods:
            period_data = self._get_data_in_period(filtered_data, period)
            if period_data:  # Only create result if there's data in the period
                result = self._aggregate_period_data(period_data, period, aggregation_type)
                results.append(result)
        
        return results
    
    def aggregate_by_custom_periods(
        self,
        periods: List[Period],
        aggregation_type: AggregationType
    ) -> List[AggregationResult]:
        """
        Aggregate data by custom periods.
        
        Args:
            periods: List of custom periods
            aggregation_type: Type of aggregation operation
            
        Returns:
            List of aggregation results for each period
        """
        results = []
        for period in periods:
            period_data = self._get_data_in_period(self.data_points, period)
            if period_data:
                result = self._aggregate_period_data(period_data, period, aggregation_type)
                results.append(result)
        
        return results
    
    def rolling_aggregation(
        self,
        window_days: int,
        aggregation_type: AggregationType,
        step_days: int = 1
    ) -> List[AggregationResult]:
        """
        Perform rolling window aggregation.
        
        Args:
            window_days: Size of rolling window in days
            aggregation_type: Type of aggregation operation
            step_days: Step size for rolling window
            
        Returns:
            List of rolling aggregation results
        """
        if not self.data_points or window_days <= 0:
            return []
        
        results = []
        start_date = self.data_points[0].date
        end_date = self.data_points[-1].date
        
        current_date = start_date
        while current_date <= end_date:
            window_end = current_date + timedelta(days=window_days - 1)
            period = Period(current_date, min(window_end, end_date))
            
            period_data = self._get_data_in_period(self.data_points, period)
            if period_data:
                result = self._aggregate_period_data(period_data, period, aggregation_type)
                results.append(result)
            
            current_date += timedelta(days=step_days)
        
        return results
    
    def _filter_by_date_range(
        self,
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> List[TimeSeriesDataPoint]:
        """Filter data points by date range."""
        filtered = self.data_points
        
        if start_date:
            filtered = [p for p in filtered if p.date >= start_date]
        
        if end_date:
            filtered = [p for p in filtered if p.date <= end_date]
        
        return filtered
    
    def _generate_periods(
        self,
        period_type: PeriodType,
        data_points: List[TimeSeriesDataPoint]
    ) -> List[Period]:
        """Generate periods based on period type and data range."""
        if not data_points:
            return []
        
        start_date = data_points[0].date
        end_date = data_points[-1].date
        periods = []
        
        if period_type == PeriodType.DAILY:
            current_date = start_date
            while current_date <= end_date:
                periods.append(Period.single_day(current_date))
                current_date += timedelta(days=1)
        
        elif period_type == PeriodType.WEEKLY:
            # Start from Monday of the first week
            current_date = start_date
            # Find Monday of this week
            days_since_monday = current_date.weekday()
            week_start = current_date - timedelta(days=days_since_monday)
            
            while week_start <= end_date:
                week_end = min(week_start + timedelta(days=6), end_date)
                periods.append(Period(week_start, week_end))
                week_start += timedelta(days=7)
        
        elif period_type == PeriodType.MONTHLY:
            # Generate monthly periods
            current_date = start_date.replace(day=1)  # First day of month
            
            while current_date <= end_date:
                # Last day of current month
                if current_date.month == 12:
                    next_month = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    next_month = current_date.replace(month=current_date.month + 1)
                
                month_end = min(next_month - timedelta(days=1), end_date)
                periods.append(Period(current_date, month_end))
                current_date = next_month
        
        elif period_type == PeriodType.QUARTERLY:
            # Generate quarterly periods
            year = start_date.year
            quarter = (start_date.month - 1) // 3 + 1
            
            while True:
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_start = date(year, quarter_start_month, 1)
                
                if quarter == 4:
                    quarter_end = date(year, 12, 31)
                else:
                    next_quarter_start = date(year, quarter_start_month + 3, 1)
                    quarter_end = next_quarter_start - timedelta(days=1)
                
                # Adjust for data range
                period_start = max(quarter_start, start_date)
                period_end = min(quarter_end, end_date)
                
                if period_start <= end_date:
                    periods.append(Period(period_start, period_end))
                
                if quarter_end >= end_date:
                    break
                
                # Move to next quarter
                quarter += 1
                if quarter > 4:
                    quarter = 1
                    year += 1
        
        elif period_type == PeriodType.ANNUALLY:
            # Generate yearly periods
            current_year = start_date.year
            
            while True:
                year_start = max(date(current_year, 1, 1), start_date)
                year_end = min(date(current_year, 12, 31), end_date)
                
                if year_start <= end_date:
                    periods.append(Period(year_start, year_end))
                
                if year_end >= end_date:
                    break
                
                current_year += 1
        
        return periods
    
    def _get_data_in_period(
        self,
        data_points: List[TimeSeriesDataPoint],
        period: Period
    ) -> List[TimeSeriesDataPoint]:
        """Get data points that fall within the specified period."""
        return [p for p in data_points if period.contains_date(p.date)]
    
    def _aggregate_period_data(
        self,
        data_points: List[TimeSeriesDataPoint],
        period: Period,
        aggregation_type: AggregationType
    ) -> AggregationResult:
        """Aggregate data points for a single period."""
        if not data_points:
            raise ValueError("Cannot aggregate empty data")
        
        values = [p.value for p in data_points]
        
        if aggregation_type == AggregationType.SUM:
            if isinstance(values[0], Money):
                result_value = sum(values[1:], values[0])  # Start with first value
            else:
                result_value = sum(values)
        
        elif aggregation_type == AggregationType.AVERAGE:
            if isinstance(values[0], Money):
                total = sum(values[1:], values[0])
                result_value = total / len(values)
            else:
                result_value = sum(values) / len(values)
        
        elif aggregation_type == AggregationType.COUNT:
            result_value = len(values)
        
        elif aggregation_type == AggregationType.MIN:
            result_value = min(values)
        
        elif aggregation_type == AggregationType.MAX:
            result_value = max(values)
        
        elif aggregation_type == AggregationType.MEDIAN:
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                if isinstance(values[0], Money):
                    mid1, mid2 = sorted_values[n//2 - 1], sorted_values[n//2]
                    result_value = (mid1 + mid2) / 2
                else:
                    result_value = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                result_value = sorted_values[n // 2]
        
        elif aggregation_type == AggregationType.FIRST:
            result_value = data_points[0].value  # Already sorted by date
        
        elif aggregation_type == AggregationType.LAST:
            result_value = data_points[-1].value  # Already sorted by date
        
        else:
            raise ValueError(f"Unsupported aggregation type: {aggregation_type}")
        
        # Round Decimal results
        if isinstance(result_value, Decimal):
            result_value = result_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return AggregationResult(
            period=period,
            aggregation_type=aggregation_type,
            value=result_value,
            count=len(data_points),
            metadata={
                "first_date": data_points[0].date,
                "last_date": data_points[-1].date
            }
        )


def group_by_category(
    data_points: List[TimeSeriesDataPoint],
    category_func: Callable[[TimeSeriesDataPoint], str]
) -> Dict[str, List[TimeSeriesDataPoint]]:
    """
    Group data points by category.
    
    Args:
        data_points: List of time series data points
        category_func: Function to extract category from data point
        
    Returns:
        Dictionary mapping categories to data points
    """
    groups = defaultdict(list)
    for point in data_points:
        category = category_func(point)
        groups[category].append(point)
    
    return dict(groups)


def create_summary_by_period(
    data_points: List[TimeSeriesDataPoint],
    period_type: PeriodType,
    categories: Optional[List[str]] = None,
    category_func: Optional[Callable[[TimeSeriesDataPoint], str]] = None
) -> Dict[str, List[AggregationResult]]:
    """
    Create comprehensive summary by period and category.
    
    Args:
        data_points: List of time series data points
        period_type: Type of period for aggregation
        categories: Optional list of categories to include
        category_func: Function to extract category from data point
        
    Returns:
        Dictionary mapping categories to their aggregation results
    """
    if not data_points:
        return {}
    
    # Group by category if category function provided
    if category_func:
        category_groups = group_by_category(data_points, category_func)
    else:
        category_groups = {"all": data_points}
    
    # Filter categories if specified
    if categories:
        category_groups = {k: v for k, v in category_groups.items() if k in categories}
    
    results = {}
    
    for category, points in category_groups.items():
        if not points:
            continue
        
        aggregator = TimeSeriesAggregator(points)
        
        # Calculate multiple aggregation types
        sum_results = aggregator.aggregate_by_period_type(period_type, AggregationType.SUM)
        avg_results = aggregator.aggregate_by_period_type(period_type, AggregationType.AVERAGE)
        count_results = aggregator.aggregate_by_period_type(period_type, AggregationType.COUNT)
        
        # Combine results
        category_results = []
        
        # Create a comprehensive result for each period
        for i in range(len(sum_results)):
            period = sum_results[i].period
            
            # Create a combined result
            combined_result = AggregationResult(
                period=period,
                aggregation_type=AggregationType.SUM,  # Primary aggregation
                value=sum_results[i].value,
                count=sum_results[i].count,
                metadata={
                    "sum": sum_results[i].value,
                    "average": avg_results[i].value if i < len(avg_results) else None,
                    "count": count_results[i].value if i < len(count_results) else None,
                    "category": category
                }
            )
            category_results.append(combined_result)
        
        results[category] = category_results
    
    return results


def calculate_period_over_period_change(
    current_results: List[AggregationResult],
    previous_results: List[AggregationResult]
) -> List[Dict[str, Any]]:
    """
    Calculate period-over-period changes.
    
    Args:
        current_results: Current period aggregation results
        previous_results: Previous period aggregation results
        
    Returns:
        List of change calculations
    """
    changes = []
    
    # Create mapping of periods to values for easier comparison
    prev_map = {str(r.period): r.value for r in previous_results}
    
    for current in current_results:
        period_key = str(current.period)
        
        change_data = {
            "period": current.period,
            "current_value": current.value,
            "previous_value": None,
            "absolute_change": None,
            "percentage_change": None
        }
        
        # Find corresponding previous period (this is simplified - in practice,
        # you might need more sophisticated period matching)
        if period_key in prev_map:
            prev_value = prev_map[period_key]
            change_data["previous_value"] = prev_value
            
            # Calculate changes
            if isinstance(current.value, Money) and isinstance(prev_value, Money):
                change_data["absolute_change"] = current.value - prev_value
                if not prev_value.is_zero():
                    change_data["percentage_change"] = (
                        (current.value - prev_value) / prev_value
                    ).amount
            elif isinstance(current.value, (int, float, Decimal)) and isinstance(prev_value, (int, float, Decimal)):
                change_data["absolute_change"] = current.value - prev_value
                if prev_value != 0:
                    change_data["percentage_change"] = (current.value - prev_value) / prev_value
        
        changes.append(change_data)
    
    return changes


def create_time_series_from_dict(
    data: Dict[DateLike, Numeric],
    metadata_func: Optional[Callable[[DateLike, Numeric], Dict[str, Any]]] = None
) -> List[TimeSeriesDataPoint]:
    """
    Create time series data points from dictionary.
    
    Args:
        data: Dictionary mapping dates to values
        metadata_func: Optional function to generate metadata for each point
        
    Returns:
        List of time series data points
    """
    points = []
    
    for date_key, value in data.items():
        # Convert date if needed
        if isinstance(date_key, datetime):
            point_date = date_key.date()
        else:
            point_date = date_key
        
        # Generate metadata if function provided
        metadata = metadata_func(date_key, value) if metadata_func else {}
        
        point = TimeSeriesDataPoint(
            date=point_date,
            value=value,
            metadata=metadata
        )
        points.append(point)
    
    return points