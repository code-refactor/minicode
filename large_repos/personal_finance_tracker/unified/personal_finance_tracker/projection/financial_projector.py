"""Financial projection system for freelancers."""

import calendar
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union
import math

import numpy as np
import pandas as pd
from pydantic import BaseModel

from personal_finance_tracker.models.common import (
    AccountBalance,
    ExpenseCategory,
    Transaction,
    TransactionType,
)

from personal_finance_tracker.income.models import RevenueForecast, SmoothedIncome

from personal_finance_tracker.projection.models import (
    SpendingLevel,
    ProjectionScenario,
    RevenueSource,
    ExpenseItem,
    CashFlowProjection,
    RunwayProjection,
    ScenarioParameter,
    WhatIfScenario,
    EmergencyFundAssessment,
)


class FinancialProjector:
    """
    Financial projection model for freelancers.

    This class provides cash flow forecasting, runway calculations,
    what-if analysis, and emergency fund assessment.
    """

    def __init__(self):
        """Initialize the financial projector."""
        self._projection_cache = {}

    def project_cash_flow(
        self,
        starting_balance: float,
        current_date: datetime,
        months_ahead: int,
        revenue_sources: List[RevenueSource],
        expense_items: List[ExpenseItem],
        scenario: ProjectionScenario = ProjectionScenario.EXPECTED,
        historical_transactions: Optional[List[Transaction]] = None,
        confidence_interval: float = 0.8,
    ) -> CashFlowProjection:
        """
        Project cash flow for a specific timeframe.

        Args:
            starting_balance: Current cash balance
            current_date: Start date for projection
            months_ahead: Number of months to project
            revenue_sources: Expected revenue sources
            expense_items: Expected expenses
            scenario: Projection scenario
            historical_transactions: Optional historical transactions for trend analysis
            confidence_interval: Confidence interval for projections

        Returns:
            CashFlowProjection object with detailed cash flow projection
        """
        # Performance measurement
        start_time = time.time()

        # Calculate dates
        start_date = datetime(current_date.year, current_date.month, 1)
        end_month = current_date.month + months_ahead
        end_year = current_date.year + (end_month - 1) // 12
        end_month = ((end_month - 1) % 12) + 1
        end_date = datetime(
            end_year, end_month, calendar.monthrange(end_year, end_month)[1]
        )

        # Generate month strings for the projection period
        months = []
        current_month = start_date
        while current_month <= end_date:
            months.append(current_month.strftime("%Y-%m"))

            # Move to next month
            month = current_month.month + 1
            year = current_month.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            current_month = datetime(year, month, 1)

        # Initialize monthly breakdown
        monthly_breakdown = {
            month: {"income": 0.0, "expenses": 0.0, "balance": 0.0} for month in months
        }

        # Apply scenario adjustments
        income_multiplier = self._get_scenario_income_multiplier(scenario)
        expense_multiplier = self._get_scenario_expense_multiplier(scenario)

        # Process revenue sources
        for revenue in revenue_sources:
            if revenue.recurring:
                # Add recurring revenue to each month
                self._add_recurring_item(
                    monthly_breakdown,
                    revenue,
                    start_date,
                    end_date,
                    "income",
                    income_multiplier,
                )
            elif revenue.expected_date:
                # Add one-time revenue
                month_key = revenue.expected_date.strftime("%Y-%m")
                if month_key in monthly_breakdown:
                    # Apply probability and scenario adjustment
                    adjusted_amount = (
                        revenue.amount * (revenue.probability / 100) * income_multiplier
                    )
                    monthly_breakdown[month_key]["income"] += adjusted_amount

        # Process expenses
        for expense in expense_items:
            if expense.recurring:
                # Add recurring expense to each month
                self._add_recurring_item(
                    monthly_breakdown,
                    expense,
                    start_date,
                    end_date,
                    "expenses",
                    expense_multiplier,
                )
            elif expense.due_date:
                # Add one-time expense
                month_key = expense.due_date.strftime("%Y-%m")
                if month_key in monthly_breakdown:
                    # Apply scenario adjustment
                    adjusted_amount = expense.amount * expense_multiplier
                    monthly_breakdown[month_key]["expenses"] += adjusted_amount

        # Calculate balances for each month
        running_balance = starting_balance

        for month in months:
            income = monthly_breakdown[month]["income"]
            expenses = monthly_breakdown[month]["expenses"]
            net = income - expenses
            running_balance += net
            monthly_breakdown[month]["balance"] = running_balance

        # Calculate totals
        total_income = sum(monthly_breakdown[month]["income"] for month in months)
        total_expenses = sum(monthly_breakdown[month]["expenses"] for month in months)
        net_cash_flow = total_income - total_expenses
        ending_balance = starting_balance + net_cash_flow

        # Create projection
        projection = CashFlowProjection(
            start_date=start_date,
            end_date=end_date,
            scenario=scenario,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_income=total_income,
            total_expenses=total_expenses,
            net_cash_flow=net_cash_flow,
            monthly_breakdown=monthly_breakdown,
            confidence_interval=confidence_interval,
        )

        # Verify performance
        elapsed_time = time.time() - start_time

        return projection

    def _add_recurring_item(
        self,
        monthly_breakdown: Dict[str, Dict[str, float]],
        item: Union[RevenueSource, ExpenseItem],
        start_date: datetime,
        end_date: datetime,
        item_type: str,  # "income" or "expenses"
        multiplier: float = 1.0,
    ) -> None:
        """Add a recurring item to monthly breakdown."""
        # Handle different recurrence frequencies
        months_interval = 1  # Default to monthly

        if item.recurrence_frequency == "quarterly":
            months_interval = 3
        elif item.recurrence_frequency == "biannual":
            months_interval = 6
        elif item.recurrence_frequency == "annual":
            months_interval = 12
        elif item.recurrence_frequency == "biweekly":
            # Approximate biweekly as 2.17 payments per month
            months_interval = 1
            multiplier *= 2.17
        elif item.recurrence_frequency == "weekly":
            # Approximate weekly as 4.33 payments per month
            months_interval = 1
            multiplier *= 4.33

        # Determine start month (use expected_date if available)
        if hasattr(item, "expected_date") and item.expected_date:
            current_month = item.expected_date
        else:
            current_month = start_date

        # Add to each applicable month
        while current_month <= end_date:
            month_key = current_month.strftime("%Y-%m")

            if month_key in monthly_breakdown:
                # Apply probability adjustment for revenue
                if item_type == "income" and hasattr(item, "probability"):
                    adjusted_amount = (
                        item.amount * (item.probability / 100) * multiplier
                    )
                else:
                    adjusted_amount = item.amount * multiplier

                monthly_breakdown[month_key][item_type] += adjusted_amount

            # Move to next applicable month
            month = current_month.month + months_interval
            year = current_month.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            current_month = datetime(year, month, 1)

    def _get_scenario_income_multiplier(self, scenario: ProjectionScenario) -> float:
        """Get income multiplier based on scenario."""
        if scenario == ProjectionScenario.PESSIMISTIC:
            return 0.7  # 70% of expected income
        elif scenario == ProjectionScenario.CONSERVATIVE:
            return 0.85  # 85% of expected income
        elif scenario == ProjectionScenario.EXPECTED:
            return 1.0  # 100% of expected income
        elif scenario == ProjectionScenario.OPTIMISTIC:
            return 1.15  # 115% of expected income
        return 1.0

    def _get_scenario_expense_multiplier(self, scenario: ProjectionScenario) -> float:
        """Get expense multiplier based on scenario."""
        if scenario == ProjectionScenario.PESSIMISTIC:
            return 1.15  # 115% of expected expenses
        elif scenario == ProjectionScenario.CONSERVATIVE:
            return 1.05  # 105% of expected expenses
        elif scenario == ProjectionScenario.EXPECTED:
            return 1.0  # 100% of expected expenses
        elif scenario == ProjectionScenario.OPTIMISTIC:
            return 0.95  # 95% of expected expenses
        return 1.0

    def calculate_runway(
        self,
        current_balance: float,
        spending_level: SpendingLevel,
        monthly_expenses: Optional[float] = None,
        historical_transactions: Optional[List[Transaction]] = None,
        expected_revenue: Optional[Dict[str, float]] = None,
        confidence_level: float = 0.8,
    ) -> RunwayProjection:
        """
        Calculate how long current funds will last at different spending levels.

        Args:
            current_balance: Current cash balance
            spending_level: Level of spending to project
            monthly_expenses: Optional override for monthly expense rate
            historical_transactions: Optional historical transactions for expense analysis
            expected_revenue: Optional expected future revenue by month
            confidence_level: Confidence level for projection

        Returns:
            RunwayProjection with detailed runway information
        """
        # Performance measurement
        start_time = time.time()

        # Determine monthly expense rate
        monthly_expense_rate = 0.0

        if monthly_expenses is not None:
            # Use provided expense rate
            monthly_expense_rate = monthly_expenses
        elif historical_transactions:
            # Calculate from historical data (last 3 months)
            now = datetime.now()
            three_months_ago = datetime(now.year, now.month, 1) - timedelta(days=90)

            # Filter to expenses in the last 3 months
            recent_expenses = [
                t
                for t in historical_transactions
                if (
                    t.transaction_type == TransactionType.EXPENSE
                    and t.date >= three_months_ago
                )
            ]

            # Group by month and calculate average
            expenses_by_month = {}
            for expense in recent_expenses:
                month_key = expense.date.strftime("%Y-%m")
                if month_key not in expenses_by_month:
                    expenses_by_month[month_key] = 0
                expenses_by_month[month_key] += expense.amount

            if expenses_by_month:
                monthly_expense_rate = sum(expenses_by_month.values()) / len(
                    expenses_by_month
                )
            else:
                raise ValueError("No historical expense data available")
        else:
            raise ValueError(
                "Either monthly_expenses or historical_transactions must be provided"
            )

        # Apply spending level adjustment
        adjusted_expense_rate = self._adjust_for_spending_level(
            monthly_expense_rate, spending_level
        )

        # Calculate runway without expected revenue
        bare_runway_months = (
            current_balance / adjusted_expense_rate
            if adjusted_expense_rate > 0
            else float("inf")
        )

        # Include expected revenue if provided
        if expected_revenue:
            # Get expected revenue by month
            sorted_months = sorted(expected_revenue.keys())

            # Calculate runway with revenue
            balance = current_balance
            months = 0
            depletion_date = None

            while balance > 0 and months < 60:  # Cap at 5 years
                # Current month index
                current_month_idx = months % len(sorted_months)
                current_month = sorted_months[current_month_idx]

                # Subtract expenses and add revenue
                balance -= adjusted_expense_rate
                if current_month in expected_revenue:
                    balance += expected_revenue[current_month]

                months += 1

                # Calculate depletion date
                if balance <= 0:
                    now = datetime.now()
                    depletion_date = datetime(
                        now.year + (now.month + months - 1) // 12,
                        ((now.month + months - 1) % 12) + 1,
                        1,
                    )
                    break

            # If we reached the cap without depleting, set to infinity
            runway_months = months if months < 60 else float("inf")
        else:
            # Without expected revenue, use simple calculation
            runway_months = bare_runway_months

            # Calculate depletion date
            if runway_months < float("inf"):
                now = datetime.now()
                months_to_add = math.floor(runway_months)
                depletion_date = datetime(
                    now.year + (now.month + months_to_add - 1) // 12,
                    ((now.month + months_to_add - 1) % 12) + 1,
                    1,
                )
            else:
                depletion_date = None

        # Create result
        result = RunwayProjection(
            calculation_date=datetime.now(),
            starting_balance=current_balance,
            spending_level=spending_level,
            monthly_expense_rate=adjusted_expense_rate,
            expected_income=expected_revenue or {},
            runway_months=runway_months,
            depletion_date=depletion_date,
            confidence_level=confidence_level,
        )

        # Verify performance
        elapsed_time = time.time() - start_time

        return result

    def _adjust_for_spending_level(
        self, base_expense_rate: float, spending_level: SpendingLevel
    ) -> float:
        """Adjust expense rate based on spending level."""
        if spending_level == SpendingLevel.MINIMAL:
            return base_expense_rate * 0.6  # 60% of normal expenses
        elif spending_level == SpendingLevel.REDUCED:
            return base_expense_rate * 0.8  # 80% of normal expenses
        elif spending_level == SpendingLevel.NORMAL:
            return base_expense_rate  # 100% of normal expenses
        elif spending_level == SpendingLevel.INCREASED:
            return base_expense_rate * 1.2  # 120% of normal expenses
        return base_expense_rate

    def create_what_if_scenario(
        self,
        name: str,
        base_scenario: ProjectionScenario,
        parameters: List[ScenarioParameter],
        description: Optional[str] = None,
    ) -> WhatIfScenario:
        """
        Create a what-if scenario for financial planning.

        Args:
            name: Name for the scenario
            base_scenario: Base projection scenario
            parameters: Parameters for the scenario
            description: Optional description

        Returns:
            WhatIfScenario object
        """
        # Create the scenario
        scenario = WhatIfScenario(
            name=name,
            description=description,
            base_scenario=base_scenario,
            parameters=parameters,
            creation_date=datetime.now(),
        )

        return scenario

    def evaluate_what_if_scenario(
        self,
        scenario: WhatIfScenario,
        starting_balance: float,
        revenue_sources: List[RevenueSource],
        expense_items: List[ExpenseItem],
        months_ahead: int = 12,
    ) -> Tuple[WhatIfScenario, CashFlowProjection]:
        """
        Evaluate a what-if scenario and calculate its impact.

        Args:
            scenario: What-if scenario to evaluate
            starting_balance: Current cash balance
            revenue_sources: Expected revenue sources
            expense_items: Expected expenses
            months_ahead: Number of months to project

        Returns:
            Tuple of (updated scenario with results, cash flow projection)
        """
        # Apply parameter adjustments to revenue and expenses
        adjusted_revenue = list(revenue_sources)
        adjusted_expenses = list(expense_items)

        # Track adjustments made for each parameter
        adjustments = {}

        for param in scenario.parameters:
            # Store original value
            adjustments[param.name] = param.current_value

            # Apply parameter adjustments based on name patterns
            if "hourly_rate" in param.name.lower():
                # Adjust revenue based on hourly rate change
                for i, revenue in enumerate(adjusted_revenue):
                    if "hourly" in revenue.name.lower():
                        # Create a new object with updated amount
                        new_revenue = RevenueSource(
                            name=revenue.name,
                            amount=param.current_value,
                            probability=revenue.probability,
                            expected_date=revenue.expected_date,
                            recurring=revenue.recurring,
                            recurrence_frequency=revenue.recurrence_frequency,
                            notes=revenue.notes,
                        )
                        adjusted_revenue[i] = new_revenue

            elif "monthly_income" in param.name.lower():
                # Adjust monthly income
                for i, revenue in enumerate(adjusted_revenue):
                    if revenue.recurring and revenue.recurrence_frequency == "monthly":
                        # Create a new object with updated amount
                        new_revenue = RevenueSource(
                            name=revenue.name,
                            amount=param.current_value,
                            probability=revenue.probability,
                            expected_date=revenue.expected_date,
                            recurring=revenue.recurring,
                            recurrence_frequency=revenue.recurrence_frequency,
                            notes=revenue.notes,
                        )
                        adjusted_revenue[i] = new_revenue

            elif "expense_reduction" in param.name.lower():
                # Apply expense reduction percentage
                reduction_factor = 1.0 - (param.current_value / 100)
                for i, expense in enumerate(adjusted_expenses):
                    # Create a new object with updated amount
                    new_expense = ExpenseItem(
                        name=expense.name,
                        amount=expense.amount * reduction_factor,
                        category=expense.category,
                        due_date=expense.due_date,
                        recurring=expense.recurring,
                        recurrence_frequency=expense.recurrence_frequency,
                        essential=expense.essential,
                        notes=expense.notes,
                    )
                    adjusted_expenses[i] = new_expense

            # Add more parameter handling as needed

        # Run projection with adjusted values
        projection = self.project_cash_flow(
            starting_balance=starting_balance,
            current_date=datetime.now(),
            months_ahead=months_ahead,
            revenue_sources=adjusted_revenue,
            expense_items=adjusted_expenses,
            scenario=scenario.base_scenario,
        )

        # Calculate result metrics
        result_metrics = {
            "ending_balance": projection.ending_balance,
            "net_cash_flow": projection.net_cash_flow,
            "total_income": projection.total_income,
            "total_expenses": projection.total_expenses,
        }

        # Update scenario with results
        # Create a new scenario with updated result metrics
        updated_scenario = WhatIfScenario(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            base_scenario=scenario.base_scenario,
            parameters=scenario.parameters,
            result_metrics=result_metrics,
            creation_date=scenario.creation_date,
            notes=scenario.notes,
        )

        return updated_scenario, projection

    def assess_emergency_fund(
        self,
        current_fund_balance: float,
        monthly_expenses: Optional[float] = None,
        historical_transactions: Optional[List[Transaction]] = None,
        recommended_months: float = 6.0,
    ) -> EmergencyFundAssessment:
        """
        Assess the adequacy of an emergency fund.

        Args:
            current_fund_balance: Current emergency fund balance
            monthly_expenses: Optional override for monthly expenses
            historical_transactions: Optional historical transactions for expense analysis
            recommended_months: Recommended number of months coverage

        Returns:
            EmergencyFundAssessment with detailed assessment
        """
        # Determine monthly essential expenses
        monthly_essential = 0.0

        if monthly_expenses is not None:
            # Use provided expense amount
            monthly_essential = monthly_expenses
        elif historical_transactions:
            # Calculate from historical data (last 3 months)
            now = datetime.now()
            three_months_ago = datetime(now.year, now.month, 1) - timedelta(days=90)

            # Filter to essential expenses in the last 3 months
            essential_expenses = [
                t
                for t in historical_transactions
                if (
                    t.transaction_type == TransactionType.EXPENSE
                    and t.date >= three_months_ago
                    and t.category
                    in [
                        ExpenseCategory.UTILITIES,
                        ExpenseCategory.HEALTH_INSURANCE,
                        ExpenseCategory.OFFICE_RENT,
                        ExpenseCategory.INTERNET,
                        ExpenseCategory.PHONE,
                    ]
                )
            ]

            # Group by month and calculate average
            expenses_by_month = {}
            for expense in essential_expenses:
                month_key = expense.date.strftime("%Y-%m")
                if month_key not in expenses_by_month:
                    expenses_by_month[month_key] = 0
                expenses_by_month[month_key] += expense.amount

            if expenses_by_month:
                monthly_essential = sum(expenses_by_month.values()) / len(
                    expenses_by_month
                )
            else:
                raise ValueError("No historical essential expense data available")
        else:
            raise ValueError(
                "Either monthly_expenses or historical_transactions must be provided"
            )

        # Calculate recommended fund size
        recommended_fund_size = monthly_essential * recommended_months

        # Calculate current coverage
        current_coverage_months = (
            current_fund_balance / monthly_essential if monthly_essential > 0 else 0
        )

        # Determine adequacy level
        if current_coverage_months < 1:
            adequacy_level = "inadequate"
            funding_plan = (
                "Immediate action needed: Build to 1 month coverage as soon as possible"
            )
        elif current_coverage_months < 3:
            adequacy_level = "minimal"
            funding_plan = "Continue building: Aim for 3 months coverage"
        elif current_coverage_months < recommended_months:
            adequacy_level = "adequate"
            funding_plan = f"Good progress: Continue building toward {recommended_months} months coverage"
        else:
            adequacy_level = "excellent"
            funding_plan = (
                "Well funded: Maintain current level or consider other financial goals"
            )

        # Create assessment
        assessment = EmergencyFundAssessment(
            assessment_date=datetime.now(),
            current_fund_balance=current_fund_balance,
            monthly_essential_expenses=monthly_essential,
            recommended_months_coverage=recommended_months,
            recommended_fund_size=recommended_fund_size,
            current_coverage_months=current_coverage_months,
            adequacy_level=adequacy_level,
            funding_plan=funding_plan,
        )

        return assessment
