"""Income management system for freelancers."""

import calendar
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import time

import numpy as np
import pandas as pd
from pydantic import BaseModel

# Import from common library
from common import (
    BaseManager,
    CRUDManager,
    ManagerResult,
    ValidationResult,
    cached,
    BatchProcessor,
    Money,
    sum_money,
    average_money,
)

from personal_finance_tracker.models.common import Invoice, Transaction, TransactionType
from personal_finance_tracker.income.models import (
    SmoothingConfig,
    SmoothingMethod,
    SmoothedIncome,
    RevenueForecast,
)


class IncomeManager(BaseManager[Transaction]):
    """Income management system for normalizing variable freelance income using common patterns."""

    def __init__(self, smoothing_config: Optional[SmoothingConfig] = None):
        """Initialize with optional configuration."""
        super().__init__("IncomeManager")
        self.config = smoothing_config or SmoothingConfig()
        self._income_cache = {}
    
    def validate(self, transaction: Transaction) -> ValidationResult:
        """Validate an income transaction."""
        result = ValidationResult(True)
        
        if transaction.transaction_type != TransactionType.INCOME:
            result.add_error("Transaction must be of type INCOME")
        
        if transaction.amount.is_zero():
            result.add_error("Transaction amount cannot be zero")
        
        if transaction.amount.is_negative():
            result.add_error("Income amount cannot be negative")
        
        return result

    def record_income(
        self, transactions: List[Transaction], force_recalculation: bool = False
    ) -> ManagerResult:
        """
        Record income transactions and update income calculations.

        Args:
            transactions: List of income transactions to record
            force_recalculation: Whether to force recalculation of smoothed income
            
        Returns:
            ManagerResult with recording status
        """
        with self.operation_context("record_income", force_recalculation=force_recalculation):
            # Clear cache if forced
            if force_recalculation:
                self._income_cache = {}

            # Only process income transactions and validate them
            income_transactions = []
            validation_errors = []
            
            for transaction in transactions:
                if transaction.transaction_type == TransactionType.INCOME:
                    validation_result = self.validate(transaction)
                    if validation_result.is_valid:
                        income_transactions.append(transaction)
                    else:
                        validation_errors.extend(validation_result.errors)
            
            if validation_errors:
                return ManagerResult.error_result(validation_errors)

            if not income_transactions:
                return ManagerResult.success_result(
                    data={"processed_count": 0},
                    metadata={"operation": "record_income"}
                )
            
            return ManagerResult.success_result(
                data={"processed_count": len(income_transactions), "transactions": income_transactions},
                metadata={"operation": "record_income"}
            )

    def calculate_monthly_income(
        self, transactions: List[Transaction], start_date: datetime, end_date: datetime
    ) -> Dict[str, Money]:
        """
        Calculate monthly income from transactions within date range using Money arithmetic.

        Args:
            transactions: List of income transactions
            start_date: Start date for calculation
            end_date: End date for calculation

        Returns:
            Dictionary mapping month (YYYY-MM format) to Money amount
        """
        # Filter transactions to income within date range
        income_transactions = [
            t
            for t in transactions
            if (
                t.transaction_type == TransactionType.INCOME
                and start_date <= t.date <= end_date
            )
        ]

        # Group by month and sum using Money arithmetic
        monthly_income = {}
        for transaction in income_transactions:
            month_key = transaction.date.strftime("%Y-%m")
            if month_key not in monthly_income:
                monthly_income[month_key] = Money.zero()
            monthly_income[month_key] = monthly_income[month_key] + transaction.amount

        return monthly_income

    def smooth_income(
        self,
        transactions: List[Transaction],
        method: Optional[SmoothingMethod] = None,
        config: Optional[SmoothingConfig] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[SmoothedIncome]:
        """
        Apply income smoothing algorithm to normalize variable income.

        Args:
            transactions: List of income transactions
            method: Smoothing method to use (defaults to config method)
            config: Smoothing configuration (defaults to instance config)
            start_date: Start date for calculation (defaults to earliest transaction)
            end_date: End date for calculation (defaults to latest transaction)

        Returns:
            List of SmoothedIncome objects with monthly smoothed income values
        """
        # Performance measurement
        start_time = time.time()

        # Use provided or default config
        smoothing_config = config or self.config
        smoothing_method = method or smoothing_config.method

        # Filter to income transactions
        income_transactions = [
            t for t in transactions if t.transaction_type == TransactionType.INCOME
        ]

        if not income_transactions:
            return []

        # Determine date range if not provided
        if not start_date:
            start_date = min(t.date for t in income_transactions)
        if not end_date:
            end_date = max(t.date for t in income_transactions)

        # Ensure start_date is beginning of month and end_date is end of month
        start_date = datetime(start_date.year, start_date.month, 1)
        last_day = calendar.monthrange(end_date.year, end_date.month)[1]
        end_date = datetime(end_date.year, end_date.month, last_day)

        # Create DataFrame with monthly income using Money
        monthly_income = self.calculate_monthly_income(
            income_transactions, start_date, end_date
        )

        # Convert to pandas Series for time series operations (convert Money to float for pandas)
        date_range = pd.date_range(start=start_date, end=end_date, freq="MS")
        income_series = pd.Series(
            [float(monthly_income.get(d.strftime("%Y-%m"), Money.zero()).amount) for d in date_range],
            index=date_range,
        )

        # Apply appropriate smoothing algorithm
        if smoothing_method == SmoothingMethod.MOVING_AVERAGE:
            smoothed_values = self._moving_average_smoothing(
                income_series, smoothing_config.window_size
            )
        elif smoothing_method == SmoothingMethod.EXPONENTIAL_SMOOTHING:
            smoothed_values = self._exponential_smoothing(
                income_series, smoothing_config.alpha
            )
        elif smoothing_method == SmoothingMethod.SEASONAL_ADJUSTMENT:
            smoothed_values = self._seasonal_adjustment_smoothing(
                income_series, smoothing_config.seasonal_periods
            )
        elif smoothing_method == SmoothingMethod.PERCENTILE_BASED:
            smoothed_values = self._percentile_based_smoothing(
                income_series, smoothing_config.percentile
            )
        elif smoothing_method == SmoothingMethod.ROLLING_MEDIAN:
            smoothed_values = self._rolling_median_smoothing(
                income_series, smoothing_config.window_size
            )
        else:
            raise ValueError(f"Unsupported smoothing method: {smoothing_method}")

        # If target income is provided, use it instead
        if smoothing_config.target_monthly_income is not None:
            smoothed_values = pd.Series(
                [float(smoothing_config.target_monthly_income.amount)] * len(income_series),
                index=income_series.index,
            )

        # Create smoothed income results
        results = []
        for i, date in enumerate(income_series.index):
            # Calculate month end date
            month_end = pd.Timestamp(
                datetime(
                    date.year, date.month, calendar.monthrange(date.year, date.month)[1]
                )
            )

            actual_money = Money.from_float(income_series[date])
            smoothed_money = Money.from_float(smoothed_values[date])

            # Calculate surplus/deficit using Money arithmetic
            if smoothed_money > actual_money:
                deficit = smoothed_money - actual_money
                surplus = Money.zero()
            else:
                deficit = Money.zero()
                surplus = actual_money - smoothed_money

            result = SmoothedIncome(
                period_start=date.to_pydatetime(),
                period_end=month_end.to_pydatetime(),
                actual_income=actual_money,
                smoothed_income=smoothed_money,
                method=smoothing_method,
                configuration=smoothing_config,
                income_deficit=deficit,
                income_surplus=surplus,
            )
            results.append(result)

        # Verify performance requirement
        elapsed_time = time.time() - start_time
        if elapsed_time > 3.0:
            print(
                f"Warning: Income smoothing took {elapsed_time:.2f} seconds, which exceeds the 3 second requirement"
            )

        return results

    def _moving_average_smoothing(
        self, income_series: pd.Series, window_size: int
    ) -> pd.Series:
        """Apply moving average smoothing."""
        # Calculate rolling mean
        smoothed = income_series.rolling(
            window=window_size, min_periods=1, center=False
        ).mean()

        # For initial periods with insufficient history, use mean of available data
        for i in range(min(window_size, len(income_series))):
            if pd.isna(smoothed.iloc[i]):
                smoothed.iloc[i] = income_series.iloc[: i + 1].mean()

        return smoothed

    def _exponential_smoothing(
        self, income_series: pd.Series, alpha: float
    ) -> pd.Series:
        """Apply exponential smoothing."""
        # Use pandas ewm (exponentially weighted mean)
        smoothed = income_series.ewm(alpha=alpha, adjust=False).mean()
        return smoothed

    def _seasonal_adjustment_smoothing(
        self, income_series: pd.Series, seasonal_periods: int
    ) -> pd.Series:
        """Apply seasonal adjustment smoothing."""
        if len(income_series) < seasonal_periods:
            # Not enough data for seasonal adjustment
            return income_series.rolling(window=3, min_periods=1).mean()

        # Calculate seasonal indices
        seasonal_means = [
            income_series.iloc[i::seasonal_periods].mean()
            for i in range(seasonal_periods)
        ]
        overall_mean = income_series.mean()

        # Avoid division by zero
        if overall_mean == 0:
            seasonal_indices = [1.0] * seasonal_periods
        else:
            seasonal_indices = [s / overall_mean for s in seasonal_means]

        # Apply seasonal adjustment
        smoothed = pd.Series(index=income_series.index, dtype=float)
        for i, date in enumerate(income_series.index):
            month_index = date.month - 1  # 0-based index
            seasonal_factor = seasonal_indices[month_index]

            # Avoid division by zero
            if seasonal_factor == 0:
                seasonal_factor = 1.0

            smoothed.iloc[i] = income_series.iloc[i] / seasonal_factor

        # Apply additional smoothing
        smoothed = smoothed.rolling(window=3, min_periods=1).mean()

        return smoothed

    def _percentile_based_smoothing(
        self, income_series: pd.Series, percentile: float
    ) -> pd.Series:
        """
        Apply percentile-based smoothing.

        This method sets a baseline income at a specified percentile of historical income,
        providing a conservative estimate that can be sustained in lean months.
        """
        if len(income_series) < 3:
            # Not enough data for percentile calculation
            return income_series

        # Calculate percentile of all non-zero income months
        non_zero_income = income_series[income_series > 0]
        if len(non_zero_income) == 0:
            return income_series

        baseline = np.percentile(non_zero_income, percentile)

        # Create series with baseline value
        smoothed = pd.Series([baseline] * len(income_series), index=income_series.index)

        return smoothed

    def _rolling_median_smoothing(
        self, income_series: pd.Series, window_size: int
    ) -> pd.Series:
        """
        Apply rolling median smoothing.

        This method is more robust to outliers than moving average.
        """
        # Calculate rolling median
        smoothed = income_series.rolling(
            window=window_size, min_periods=1, center=False
        ).median()

        # For initial periods with insufficient history, use median of available data
        for i in range(min(window_size, len(income_series))):
            if pd.isna(smoothed.iloc[i]):
                smoothed.iloc[i] = income_series.iloc[: i + 1].median()

        return smoothed

    def forecast_revenue(
        self,
        transactions: List[Transaction],
        invoices: List[Invoice],
        forecast_months: int = 6,
        confidence_interval: Optional[float] = None,
    ) -> List[RevenueForecast]:
        """
        Forecast future revenue based on historical patterns and pending invoices.

        Args:
            transactions: Historical income transactions
            invoices: Pending invoices (issued but not paid)
            forecast_months: Number of months to forecast
            confidence_interval: Confidence interval for prediction (0-1)

        Returns:
            List of monthly revenue forecasts
        """
        # Use configured or provided confidence interval
        ci = confidence_interval or self.config.confidence_interval

        # Filter to income transactions
        income_transactions = [
            t for t in transactions if t.transaction_type == TransactionType.INCOME
        ]

        if not income_transactions:
            # No historical data, can't make forecast
            return []

        # Get latest transaction date and create forecast start date
        latest_date = max(t.date for t in income_transactions)
        forecast_start = datetime(latest_date.year, latest_date.month, 1) + timedelta(
            days=32
        )
        forecast_start = datetime(forecast_start.year, forecast_start.month, 1)

        # Calculate monthly historical income using Money
        end_date = latest_date
        start_date = end_date - timedelta(days=365 * 2)  # 2 years of history
        monthly_income = self.calculate_monthly_income(
            income_transactions, start_date, end_date
        )

        # Convert to Series for analysis (convert Money to float for pandas)
        dates = pd.date_range(start=start_date, end=end_date, freq="MS")
        historical = pd.Series(
            [float(monthly_income.get(d.strftime("%Y-%m"), Money.zero()).amount) for d in dates], index=dates
        )

        # Calculate basic statistics for forecast
        mean_income = historical.mean()
        std_income = historical.std() if len(historical) > 1 else mean_income * 0.2

        # Calculate bounds based on confidence interval
        from scipy import stats

        z_score = stats.norm.ppf((1 + ci) / 2)

        # Process pending invoices using Money arithmetic
        pending_by_month = {}
        for invoice in invoices:
            if invoice.status in ["draft", "sent", "overdue"]:
                # For unpaid invoices, use due date for estimation
                month_key = invoice.due_date.strftime("%Y-%m")
                if month_key not in pending_by_month:
                    pending_by_month[month_key] = Money.zero()
                pending_by_month[month_key] = pending_by_month[month_key] + invoice.amount

        # Create forecasts
        forecasts = []
        for i in range(forecast_months):
            # Calculate forecast month
            forecast_date = forecast_start + timedelta(days=32 * i)
            forecast_date = datetime(forecast_date.year, forecast_date.month, 1)

            # Base forecast on historical average (convert to Money)
            expected_income_money = Money.from_float(mean_income)

            # Add pending invoice amounts if available
            month_key = forecast_date.strftime("%Y-%m")
            if month_key in pending_by_month:
                expected_income_money = expected_income_money + pending_by_month[month_key]

            # Calculate bounds (using float for statistical calculations, then convert back)
            expected_income_float = float(expected_income_money.amount)
            lower_bound_float = max(0, expected_income_float - z_score * std_income)
            upper_bound_float = expected_income_float + z_score * std_income
            
            lower_bound_money = Money.from_float(lower_bound_float)
            upper_bound_money = Money.from_float(upper_bound_float)

            # Create forecast entry using Money
            forecast = RevenueForecast(
                month=forecast_date,
                expected_income=expected_income_money,
                lower_bound=lower_bound_money,
                upper_bound=upper_bound_money,
                confidence_interval=ci,
                sources={
                    "historical": Money.from_float(mean_income),
                    "pending": pending_by_month.get(month_key, Money.zero()),
                },
            )
            forecasts.append(forecast)

        return forecasts

    def track_invoice(self, invoice: Invoice, update_existing: bool = True) -> Invoice:
        """
        Track a new invoice or update an existing one.

        Args:
            invoice: The invoice to track
            update_existing: Whether to update an existing invoice with the same ID

        Returns:
            The tracked invoice
        """
        # In a real implementation, this would store the invoice in a database
        # For this example, we just return the invoice
        return invoice

    def get_invoice_status(self, invoice_id: str) -> Optional[str]:
        """Get the status of an invoice by ID."""
        # In a real implementation, this would look up the invoice in a database
        return None

    def update_invoice_status(
        self, invoice_id: str, new_status: str, payment_date: Optional[datetime] = None
    ) -> bool:
        """
        Update the status of an invoice.

        Args:
            invoice_id: ID of the invoice to update
            new_status: New status value
            payment_date: Date of payment if status is 'paid'

        Returns:
            True if the update was successful
        """
        # In a real implementation, this would update the invoice in a database
        return True
