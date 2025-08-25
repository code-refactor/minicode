"""Simplified tests for the financial projection system."""

from datetime import datetime
import uuid

import pytest
import numpy as np

from personal_finance_tracker.models.common import ExpenseCategory

from personal_finance_tracker.projection.models import (
    SpendingLevel,
    ProjectionScenario,
    RevenueSource,
    ExpenseItem,
    ScenarioParameter,
)

from personal_finance_tracker.projection.financial_projector import FinancialProjector


class TestFinancialProjectorSimple:
    """Simplified test suite for the FinancialProjector class."""

    def test_init(self):
        """Test initialization of the financial projector."""
        projector = FinancialProjector()
        assert projector._projection_cache == {}

    def test_project_cash_flow_basic(self):
        """Test basic cash flow projection."""
        projector = FinancialProjector()

        # Set up basic parameters
        starting_balance = 5000.0
        current_date = datetime(2022, 1, 1)
        months_ahead = 3

        # Simple revenue and expenses
        revenue_sources = [
            RevenueSource(
                name="Monthly Income",
                amount=3000.0,
                probability=100.0,
                recurring=True,
                recurrence_frequency="monthly",
            )
        ]

        expense_items = [
            ExpenseItem(
                name="Monthly Expenses",
                amount=2000.0,
                category=ExpenseCategory.OTHER,
                recurring=True,
                recurrence_frequency="monthly",
            )
        ]

        # Generate projection
        projection = projector.project_cash_flow(
            starting_balance=starting_balance,
            current_date=current_date,
            months_ahead=months_ahead,
            revenue_sources=revenue_sources,
            expense_items=expense_items,
        )

        # Basic verification
        assert projection.starting_balance == starting_balance
        assert len(projection.monthly_breakdown) == months_ahead
        assert projection.total_income == 3000.0 * months_ahead
        assert projection.total_expenses == 2000.0 * months_ahead
        assert (
            projection.net_cash_flow
            == projection.total_income - projection.total_expenses
        )
        assert projection.ending_balance == starting_balance + projection.net_cash_flow

    def test_create_scenario(self):
        """Test creating a what-if scenario."""
        projector = FinancialProjector()

        # Create scenario
        parameters = [
            ScenarioParameter(
                name="hourly_rate",
                description="Hourly billing rate",
                current_value=75.0,
                min_value=50.0,
                max_value=150.0,
                step_size=5.0,
                unit="$",
            )
        ]

        scenario = projector.create_what_if_scenario(
            name="Test Scenario",
            base_scenario=ProjectionScenario.EXPECTED,
            parameters=parameters,
        )

        # Verify scenario
        assert scenario.name == "Test Scenario"
        assert scenario.base_scenario == ProjectionScenario.EXPECTED
        assert len(scenario.parameters) == 1
        assert scenario.parameters[0].name == "hourly_rate"
