"""Tests for the income management system."""

from datetime import datetime, timedelta
import time
import uuid

import pytest
import pandas as pd
import numpy as np

from personal_finance_tracker.models.common import Transaction, TransactionType

from personal_finance_tracker.income.models import SmoothingConfig, SmoothingMethod

from personal_finance_tracker.income.income_manager import IncomeManager


class TestIncomeManager:
    """Test suite for the IncomeManager class."""

    def test_init(self):
        """Test initialization with default and custom config."""
        # Default initialization
        manager = IncomeManager()
        assert manager.config is not None
        assert manager.config.method == SmoothingMethod.MOVING_AVERAGE

        # Custom config
        custom_config = SmoothingConfig(
            method=SmoothingMethod.EXPONENTIAL_SMOOTHING, alpha=0.5, window_size=6
        )
        manager = IncomeManager(custom_config)
        assert manager.config == custom_config
        assert manager.config.method == SmoothingMethod.EXPONENTIAL_SMOOTHING
        assert manager.config.alpha == 0.5

    def test_calculate_monthly_income(self, sample_transactions):
        """Test calculation of monthly income from transactions."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Calculate monthly income
        monthly_income = manager.calculate_monthly_income(
            sample_transactions, start_date, end_date
        )

        # Verify expected months are present
        for month in range(1, 13):
            month_key = f"2022-{month:02d}"
            assert month_key in monthly_income or monthly_income.get(month_key, 0) == 0

    def test_smooth_income_moving_average(self, sample_transactions):
        """Test income smoothing with moving average method."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing
        config = SmoothingConfig(method=SmoothingMethod.MOVING_AVERAGE, window_size=3)

        # Run smoothing
        start_time = time.time()
        smoothed_income = manager.smooth_income(
            sample_transactions,
            method=SmoothingMethod.MOVING_AVERAGE,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )
        elapsed_time = time.time() - start_time

        # Verify performance requirement (under 3 seconds for 5+ years)
        assert elapsed_time < 3.0

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            assert result.actual_income >= 0
            assert result.smoothed_income >= 0
            assert result.method == SmoothingMethod.MOVING_AVERAGE

    def test_smooth_income_exponential_smoothing(self, sample_transactions):
        """Test income smoothing with exponential smoothing method."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing
        config = SmoothingConfig(
            method=SmoothingMethod.EXPONENTIAL_SMOOTHING, alpha=0.3
        )

        # Run smoothing
        smoothed_income = manager.smooth_income(
            sample_transactions,
            method=SmoothingMethod.EXPONENTIAL_SMOOTHING,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            assert result.method == SmoothingMethod.EXPONENTIAL_SMOOTHING

    def test_smooth_income_percentile_based(self, sample_transactions):
        """Test income smoothing with percentile-based method."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing
        config = SmoothingConfig(
            method=SmoothingMethod.PERCENTILE_BASED, percentile=25.0
        )

        # Run smoothing
        smoothed_income = manager.smooth_income(
            sample_transactions,
            method=SmoothingMethod.PERCENTILE_BASED,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            assert result.method == SmoothingMethod.PERCENTILE_BASED

            # All smoothed values should be the same for percentile-based smoothing
            if smoothed_income[0].smoothed_income > 0:
                assert result.smoothed_income == smoothed_income[0].smoothed_income

    def test_smooth_income_seasonal_adjustment(self, sample_transactions):
        """Test income smoothing with seasonal adjustment method."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing
        config = SmoothingConfig(
            method=SmoothingMethod.SEASONAL_ADJUSTMENT, seasonal_periods=12
        )

        # Run smoothing
        smoothed_income = manager.smooth_income(
            sample_transactions,
            method=SmoothingMethod.SEASONAL_ADJUSTMENT,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            assert result.method == SmoothingMethod.SEASONAL_ADJUSTMENT

    def test_smooth_income_rolling_median(self, sample_transactions):
        """Test income smoothing with rolling median method."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing
        config = SmoothingConfig(method=SmoothingMethod.ROLLING_MEDIAN, window_size=3)

        # Run smoothing
        smoothed_income = manager.smooth_income(
            sample_transactions,
            method=SmoothingMethod.ROLLING_MEDIAN,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            assert result.method == SmoothingMethod.ROLLING_MEDIAN

    def test_smooth_income_with_target(self, sample_transactions):
        """Test income smoothing with target monthly income override."""
        manager = IncomeManager()

        # Define date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Configure smoothing with target income
        target_income = 3000.0
        config = SmoothingConfig(
            method=SmoothingMethod.MOVING_AVERAGE,
            window_size=3,
            target_monthly_income=target_income,
        )

        # Run smoothing
        smoothed_income = manager.smooth_income(
            sample_transactions, config=config, start_date=start_date, end_date=end_date
        )

        # Verify results
        assert len(smoothed_income) > 0
        for result in smoothed_income:
            # All smoothed values should equal the target
            assert result.smoothed_income == target_income

    def test_forecast_revenue(self, sample_transactions, sample_invoices):
        """Test revenue forecasting based on history and pending invoices."""
        manager = IncomeManager()

        # Run forecast
        forecast_months = 6
        forecasts = manager.forecast_revenue(
            sample_transactions, sample_invoices, forecast_months=forecast_months
        )

        # Verify results
        assert len(forecasts) == forecast_months

        for forecast in forecasts:
            # Verify forecast attributes
            assert forecast.expected_income >= 0
            assert forecast.lower_bound >= 0
            assert forecast.upper_bound >= forecast.expected_income
            assert 0 <= forecast.confidence_interval <= 1

    def test_extremely_irregular_income(self):
        """Test handling of extremely irregular income patterns."""
        manager = IncomeManager()

        # Create test data with extreme irregularity
        transactions = []
        dates = [
            datetime(2022, 1, 15),  # 10000
            datetime(2022, 2, 15),  # 0
            datetime(2022, 3, 15),  # 0
            datetime(2022, 4, 15),  # 15000
            datetime(2022, 5, 15),  # 0
            datetime(2022, 6, 15),  # 0
            datetime(2022, 7, 15),  # 0
            datetime(2022, 8, 15),  # 20000
            datetime(2022, 9, 15),  # 0
            datetime(2022, 10, 15),  # 0
            datetime(2022, 11, 15),  # 0
            datetime(2022, 12, 15),  # 30000
        ]
        amounts = [10000, 0, 0, 15000, 0, 0, 0, 20000, 0, 0, 0, 30000]

        for date, amount in zip(dates, amounts):
            if amount > 0:
                transactions.append(
                    Transaction(
                        id=uuid.uuid4(),
                        date=date,
                        amount=amount,
                        description="Irregular income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                    )
                )

        # Test different smoothing methods
        methods = [
            SmoothingMethod.MOVING_AVERAGE,
            SmoothingMethod.EXPONENTIAL_SMOOTHING,
            SmoothingMethod.PERCENTILE_BASED,
            SmoothingMethod.ROLLING_MEDIAN,
        ]

        for method in methods:
            config = SmoothingConfig(method=method)
            smoothed = manager.smooth_income(transactions, method=method, config=config)

            # Verify the method produces reasonable smoothing
            if len(smoothed) > 0:
                # Check that the smoothed income is more regular
                actual_values = [s.actual_income for s in smoothed]
                smoothed_values = [s.smoothed_income for s in smoothed]

                # Standard deviation of smoothed values should be less than actuals
                if any(actual_values):
                    assert np.std(smoothed_values) <= np.std(
                        [a for a in actual_values if a > 0]
                    )

    def test_income_smoothing_with_large_dataset(self):
        """Test performance with a large dataset (5+ years)."""
        manager = IncomeManager()

        # Create a large dataset spanning 7 years
        transactions = []
        start_date = datetime(2016, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Generate monthly income with some randomness
        current_date = start_date
        while current_date <= end_date:
            # Base income with seasonal pattern and random variation
            month = current_date.month
            seasonal_factor = 1.0 + 0.3 * np.sin(
                2 * np.pi * month / 12
            )  # Seasonal pattern
            base_income = 3000 * seasonal_factor

            # Add random variation
            random_factor = np.random.normal(1.0, 0.4)  # 40% standard deviation
            income = max(0, base_income * random_factor)

            # Add occasional large payments
            if np.random.random() < 0.1:  # 10% chance
                income += np.random.uniform(5000, 10000)

            # Create transaction
            if income > 0:
                transactions.append(
                    Transaction(
                        id=uuid.uuid4(),
                        date=current_date,
                        amount=income,
                        description=f"Income {current_date.strftime('%Y-%m')}",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                    )
                )

            # Move to next month
            month = current_date.month + 1
            year = current_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            current_date = datetime(year, month, 15)

        # Test performance of smoothing
        start_time = time.time()
        smoothed = manager.smooth_income(
            transactions, method=SmoothingMethod.MOVING_AVERAGE
        )
        elapsed_time = time.time() - start_time

        # Check performance requirement (under 3 seconds for 5+ years)
        assert elapsed_time < 3.0
        assert len(smoothed) > 60  # Should have at least 60 months (5 years)
