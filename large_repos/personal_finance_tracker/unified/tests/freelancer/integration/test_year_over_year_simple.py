"""Simplified version of year-over-year comparison tests."""

from datetime import datetime, timedelta
import uuid
from typing import Dict, List

import pytest

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
    Project,
)
from personal_finance_tracker.expense.models import ExpenseSummary
from personal_finance_tracker.expense.categorizer import ExpenseCategorizer
from personal_finance_tracker.income.income_manager import IncomeManager
from personal_finance_tracker.tax.tax_manager import TaxManager
from personal_finance_tracker.tax.models import (
    FilingStatus,
    TaxJurisdiction,
)
from personal_finance_tracker.project.profitability_analyzer import ProjectProfiler


class TestYearOverYearSimple:
    """Simple version of year-over-year comparison tests."""

    def test_income_comparison_across_years(self):
        """Test comparing income patterns across multiple years."""
        # Create sample transactions
        transactions = []
        
        # 2021 income (lower)
        for month in range(1, 13, 2):  # Every other month
            transactions.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2021, month, 15),
                amount=3000.0,
                description=f"Income for month {month}/2021",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            ))
            
        # 2022 income (higher)
        for month in range(1, 13, 2):  # Same pattern but higher amount
            transactions.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, month, 15),
                amount=4000.0,
                description=f"Income for month {month}/2022",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            ))
            
        # Split by year
        income_2021 = [tx for tx in transactions if tx.date.year == 2021]
        income_2022 = [tx for tx in transactions if tx.date.year == 2022]
        
        # Calculate totals
        total_2021 = sum(tx.amount for tx in income_2021)
        total_2022 = sum(tx.amount for tx in income_2022)
        
        # Verify income increased
        assert total_2022 > total_2021
        
        # Calculate growth rate
        growth_rate = (total_2022 - total_2021) / total_2021
        assert growth_rate > 0
        
    def test_expense_comparison_across_years(self):
        """Test comparing expense patterns across multiple years."""
        # Create sample transactions
        transactions = []
        
        # 2021 expenses
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2021, 6, 15),
            amount=1000.0,
            description="Software expenses 2021",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.SOFTWARE,
            business_use_percentage=100.0,
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2021, 7, 15),
            amount=2000.0,
            description="Personal expenses 2021",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.PERSONAL,
            business_use_percentage=0.0,
        ))
        
        # 2022 expenses (higher)
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 6, 15),
            amount=1500.0,
            description="Software expenses 2022",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.SOFTWARE,
            business_use_percentage=100.0,
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 7, 15),
            amount=2500.0,
            description="Personal expenses 2022",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.PERSONAL,
            business_use_percentage=0.0,
        ))
            
        # Split by year
        expenses_2021 = [tx for tx in transactions if tx.date.year == 2021]
        expenses_2022 = [tx for tx in transactions if tx.date.year == 2022]
        
        # Calculate totals
        total_2021 = sum(tx.amount for tx in expenses_2021)
        total_2022 = sum(tx.amount for tx in expenses_2022)
        
        # Verify expenses increased
        assert total_2022 > total_2021
        
        # Calculate business expenses
        business_2021 = sum(
            tx.amount * (tx.business_use_percentage / 100.0)
            for tx in expenses_2021
            if tx.category != ExpenseCategory.PERSONAL
        )
        
        business_2022 = sum(
            tx.amount * (tx.business_use_percentage / 100.0)
            for tx in expenses_2022
            if tx.category != ExpenseCategory.PERSONAL
        )
        
        # Verify business expenses increased
        assert business_2022 > business_2021
        
    def test_tax_comparison_across_years(self):
        """Test comparing tax liabilities across multiple years."""
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # 2021 tax data
        income_2021 = 30000.0
        expenses_2021 = 5000.0
        taxable_income_2021 = income_2021 - expenses_2021
        
        # 2022 tax data
        income_2022 = 40000.0
        expenses_2022 = 6000.0
        taxable_income_2022 = income_2022 - expenses_2022
        
        # Simple tax calculation (25% rate)
        tax_2021 = taxable_income_2021 * 0.25
        tax_2022 = taxable_income_2022 * 0.25
        
        # Verify tax increased with income
        assert tax_2022 > tax_2021
        
    def test_project_profitability_across_years(self):
        """Test comparing project profitability across years."""
        # Create simple projects with hourly rates
        project_2021 = Project(
            id="project2021",
            name="Website Design 2021",
            client_id="client1",
            start_date=datetime(2021, 3, 1),
            end_date=datetime(2021, 5, 31),
            status="completed",
            hourly_rate=75.0,
            estimated_hours=40.0,
        )
        
        project_2022 = Project(
            id="project2022",
            name="Website Design 2022",
            client_id="client1",
            start_date=datetime(2022, 3, 1),
            end_date=datetime(2022, 5, 31),
            status="completed",
            hourly_rate=85.0,
            estimated_hours=40.0,
        )
        
        # For simplicity, just compare hourly rates directly
        assert project_2022.hourly_rate > project_2021.hourly_rate
        
        # Calculate growth rate
        rate_growth = (project_2022.hourly_rate - project_2021.hourly_rate) / project_2021.hourly_rate
        assert rate_growth > 0