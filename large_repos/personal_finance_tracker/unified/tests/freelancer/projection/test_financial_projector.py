"""Tests for the financial projection system."""

from datetime import datetime, timedelta
import time
import uuid

import pytest
import pandas as pd
import numpy as np

from personal_finance_tracker.models.common import (
    Transaction,
    TransactionType,
    ExpenseCategory,
)
from personal_finance_tracker.projection.models import (
    SpendingLevel,
    ProjectionScenario,
    RevenueSource,
    ExpenseItem,
    ScenarioParameter,
    WhatIfScenario,
)

from personal_finance_tracker.projection.financial_projector import FinancialProjector


class TestFinancialProjector:
    """Test suite for the FinancialProjector class."""

    def test_init(self):
        """Test initialization of the financial projector."""
        projector = FinancialProjector()
        assert projector._projection_cache == {}

    def test_project_cash_flow(self):
        """Test cash flow projection for a specific timeframe."""
        projector = FinancialProjector()

        # Set up test parameters
        starting_balance = 10000.0
        current_date = datetime(2022, 6, 1)
        months_ahead = 6

        # Create revenue sources
        revenue_sources = [
            RevenueSource(
                name="Monthly Retainer",
                amount=3000.0,
                probability=100.0,
                recurring=True,
                recurrence_frequency="monthly",
            ),
            RevenueSource(
                name="Quarterly Project",
                amount=9000.0,
                probability=80.0,
                recurring=True,
                recurrence_frequency="quarterly",
            ),
            RevenueSource(
                name="One-time Payment",
                amount=5000.0,
                probability=90.0,
                expected_date=datetime(2022, 8, 15),
                recurring=False,
            ),
        ]

        # Create expense items
        expense_items = [
            ExpenseItem(
                name="Office Rent",
                amount=800.0,
                category="office_rent",
                recurring=True,
                recurrence_frequency="monthly",
                essential=True,
            ),
            ExpenseItem(
                name="Software Subscriptions",
                amount=200.0,
                category="software",
                recurring=True,
                recurrence_frequency="monthly",
                essential=True,
            ),
            ExpenseItem(
                name="New Equipment",
                amount=1200.0,
                category="equipment",
                due_date=datetime(2022, 7, 10),
                recurring=False,
                essential=False,
            ),
        ]

        # Generate projection
        projection = projector.project_cash_flow(
            starting_balance=starting_balance,
            current_date=current_date,
            months_ahead=months_ahead,
            revenue_sources=revenue_sources,
            expense_items=expense_items,
            scenario=ProjectionScenario.EXPECTED,
        )

        # Verify projection
        assert projection.starting_balance == starting_balance
        assert projection.scenario == ProjectionScenario.EXPECTED
        assert projection.start_date.month == current_date.month
        assert projection.start_date.year == current_date.year

        # End date should be months_ahead months after start
        expected_end_month = (current_date.month + months_ahead - 1) % 12 + 1
        expected_end_year = (
            current_date.year + (current_date.month + months_ahead - 1) // 12
        )
        assert projection.end_date.month == expected_end_month
        assert projection.end_date.year == expected_end_year

        # Verify monthly breakdown
        assert len(projection.monthly_breakdown) > 0

        # Check first month
        first_month_key = current_date.strftime("%Y-%m")
        assert first_month_key in projection.monthly_breakdown

        first_month = projection.monthly_breakdown[first_month_key]
        assert first_month["income"] > 0
        assert first_month["expenses"] > 0
        assert (
            first_month["balance"]
            == starting_balance + first_month["income"] - first_month["expenses"]
        )

        # Verify totals
        assert projection.total_income > 0
        assert projection.total_expenses > 0
        assert (
            projection.net_cash_flow
            == projection.total_income - projection.total_expenses
        )
        assert projection.ending_balance == starting_balance + projection.net_cash_flow

    def test_project_cash_flow_different_scenarios(self):
        """Test cash flow projections with different scenarios."""
        projector = FinancialProjector()

        # Common parameters
        starting_balance = 15000.0
        current_date = datetime(2022, 6, 1)
        months_ahead = 3

        # Revenue and expenses
        revenue_sources = [
            RevenueSource(
                name="Monthly Income",
                amount=5000.0,
                probability=100.0,
                recurring=True,
                recurrence_frequency="monthly",
            )
        ]

        expense_items = [
            ExpenseItem(
                name="Monthly Expenses",
                amount=3000.0,
                category=ExpenseCategory.OTHER,
                recurring=True,
                recurrence_frequency="monthly",
            )
        ]

        # Generate projections for each scenario
        scenarios = [
            ProjectionScenario.PESSIMISTIC,
            ProjectionScenario.CONSERVATIVE,
            ProjectionScenario.EXPECTED,
            ProjectionScenario.OPTIMISTIC,
        ]

        projections = {}
        for scenario in scenarios:
            projections[scenario] = projector.project_cash_flow(
                starting_balance=starting_balance,
                current_date=current_date,
                months_ahead=months_ahead,
                revenue_sources=revenue_sources,
                expense_items=expense_items,
                scenario=scenario,
            )

        # Verify scenario adjustments
        # Income should increase from pessimistic to optimistic
        income_values = [projections[s].total_income for s in scenarios]
        assert income_values[0] < income_values[1] < income_values[2] < income_values[3]

        # Expenses should decrease from pessimistic to optimistic
        expense_values = [projections[s].total_expenses for s in scenarios]
        assert (
            expense_values[0]
            > expense_values[1]
            > expense_values[2]
            > expense_values[3]
        )

        # Net cash flow should improve from pessimistic to optimistic
        cash_flow_values = [projections[s].net_cash_flow for s in scenarios]
        assert (
            cash_flow_values[0]
            < cash_flow_values[1]
            < cash_flow_values[2]
            < cash_flow_values[3]
        )

    def test_calculate_runway_simple(self):
        """Test simple cash runway calculation."""
        projector = FinancialProjector()

        # Test parameters
        current_balance = 12000.0
        monthly_expenses = 3000.0  # $3000/month burn rate

        # Calculate runway for normal spending
        runway = projector.calculate_runway(
            current_balance=current_balance,
            spending_level=SpendingLevel.NORMAL,
            monthly_expenses=monthly_expenses,
        )

        # Normal spending level should give runway of current_balance / monthly_expenses
        expected_normal_runway = current_balance / monthly_expenses
        assert abs(runway.runway_months - expected_normal_runway) < 0.01

    def test_create_what_if_scenario(self):
        """Test creating a what-if scenario."""
        projector = FinancialProjector()

        # Create scenario parameters
        parameters = [
            ScenarioParameter(
                name="hourly_rate",
                description="Hourly billing rate",
                current_value=75.0,
                min_value=50.0,
                max_value=150.0,
                step_size=5.0,
                unit="$",
            ),
            ScenarioParameter(
                name="expense_reduction",
                description="Expense reduction percentage",
                current_value=10.0,
                min_value=0.0,
                max_value=30.0,
                step_size=5.0,
                unit="%",
            ),
        ]

        # Create scenario
        scenario = projector.create_what_if_scenario(
            name="Rate Increase Scenario",
            base_scenario=ProjectionScenario.EXPECTED,
            parameters=parameters,
            description="Testing impact of rate increases and expense reductions",
        )

        # Verify scenario
        assert scenario.name == "Rate Increase Scenario"
        assert scenario.base_scenario == ProjectionScenario.EXPECTED
        assert len(scenario.parameters) == 2
        assert scenario.parameters[0].name == "hourly_rate"
        assert scenario.parameters[0].current_value == 75.0
        assert scenario.parameters[1].name == "expense_reduction"
        assert scenario.result_metrics == {}

    def test_create_what_if_scenario_with_evaluation(self):
        """Test creating and partially evaluating a what-if scenario."""
        projector = FinancialProjector()

        # Create scenario
        parameters = [
            ScenarioParameter(
                name="hourly_rate",
                description="Hourly billing rate",
                current_value=100.0,  # Increased from base 75.0
                min_value=50.0,
                max_value=150.0,
                step_size=5.0,
                unit="$",
            )
        ]

        scenario = projector.create_what_if_scenario(
            name="Rate Increase Scenario",
            base_scenario=ProjectionScenario.EXPECTED,
            parameters=parameters,
        )

        # Verify the scenario was created properly
        assert scenario.name == "Rate Increase Scenario"
        assert scenario.base_scenario == ProjectionScenario.EXPECTED
        assert len(scenario.parameters) == 1
        assert scenario.parameters[0].name == "hourly_rate"
        assert scenario.parameters[0].current_value == 100.0

    def test_assess_emergency_fund_simple(self):
        """Test simple emergency fund assessment."""
        projector = FinancialProjector()

        # Test parameters
        current_fund_balance = 15000.0
        monthly_expenses = 5000.0

        # Assess with direct monthly expenses
        assessment = projector.assess_emergency_fund(
            current_fund_balance=current_fund_balance, monthly_expenses=monthly_expenses
        )

        # Verify assessment
        assert assessment.current_fund_balance == current_fund_balance
        assert assessment.monthly_essential_expenses == monthly_expenses
        assert assessment.recommended_months_coverage == 6.0  # Default
        assert assessment.recommended_fund_size == monthly_expenses * 6.0
        assert (
            assessment.current_coverage_months
            == current_fund_balance / monthly_expenses
        )

    def test_negative_cash_flow(self):
        """Test handling of negative cash flow periods."""
        projector = FinancialProjector()

        # Set up test parameters
        starting_balance = 5000.0
        current_date = datetime(2022, 10, 1)
        months_ahead = 6

        # Create revenue sources (income starts in month 3)
        revenue_sources = [
            RevenueSource(
                name="Delayed Project",
                amount=8000.0,
                probability=100.0,
                expected_date=datetime(2022, 12, 15),  # December (month 3)
                recurring=False,
            ),
            RevenueSource(
                name="New Contract",
                amount=4000.0,
                probability=100.0,
                expected_date=datetime(2023, 1, 1),  # January (month 4)
                recurring=True,
                recurrence_frequency="monthly",
            ),
        ]

        # Create expense items (continuous expenses)
        expense_items = [
            ExpenseItem(
                name="Monthly Expenses",
                amount=2000.0,
                category=ExpenseCategory.OTHER,
                recurring=True,
                recurrence_frequency="monthly",
                essential=True,
            )
        ]

        # Generate projection
        projection = projector.project_cash_flow(
            starting_balance=starting_balance,
            current_date=current_date,
            months_ahead=months_ahead,
            revenue_sources=revenue_sources,
            expense_items=expense_items,
            scenario=ProjectionScenario.EXPECTED,
        )

        # Verify monthly breakdown
        month_keys = sorted(projection.monthly_breakdown.keys())

        # First two months should have negative cash flow
        assert projection.monthly_breakdown[month_keys[0]]["income"] == 0
        assert projection.monthly_breakdown[month_keys[1]]["income"] == 0
        assert projection.monthly_breakdown[month_keys[0]]["expenses"] > 0
        assert projection.monthly_breakdown[month_keys[1]]["expenses"] > 0

        # Month 3 (December) should have positive cash flow from the delayed project
        december_key = "2022-12"
        assert december_key in month_keys
        assert projection.monthly_breakdown[december_key]["income"] == 8000.0

        # Verify the balance calculation correctly handles negative months
        expected_balance = starting_balance
        for i, month in enumerate(month_keys):
            month_data = projection.monthly_breakdown[month]
            expected_balance += month_data["income"] - month_data["expenses"]
            assert abs(month_data["balance"] - expected_balance) < 0.01

        # Calculate runway
        runway = projector.calculate_runway(
            current_balance=starting_balance,
            spending_level=SpendingLevel.NORMAL,
            monthly_expenses=2000.0,
            expected_revenue={
                "2022-10": 0,
                "2022-11": 0,
                "2022-12": 8000.0,
                "2023-01": 4000.0,
                "2023-02": 4000.0,
                "2023-03": 4000.0,
            },
        )

        # Verify runway calculation
        # Without revenue, runway would be $5000/$2000 = 2.5 months
        # With revenue, it should be much longer
        assert runway.runway_months > 2.5
