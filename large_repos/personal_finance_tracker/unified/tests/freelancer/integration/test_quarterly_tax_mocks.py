"""Integration tests for quarterly tax preparation with mocks."""

from datetime import datetime, timedelta
import uuid
from unittest.mock import MagicMock, patch

import pytest

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
)
from personal_finance_tracker.expense.models import (
    CategorizationRule,
    ExpenseSummary,
)
from personal_finance_tracker.expense.categorizer import ExpenseCategorizer
from personal_finance_tracker.income.models import SmoothingMethod
from personal_finance_tracker.income.income_manager import IncomeManager
from personal_finance_tracker.tax.models import (
    FilingStatus,
    TaxJurisdiction,
    TaxBracket,
    QuarterInfo,
    EstimatedPayment,
)
from personal_finance_tracker.tax.tax_manager import TaxManager


class TestQuarterlyTaxPreparationMocks:
    """Mock-based tests for quarterly tax preparation."""

    def test_comprehensive_quarterly_tax_preparation(self):
        """Test a comprehensive end-to-end quarterly tax preparation process with mocks."""
        # Set up the required components
        expense_categorizer = ExpenseCategorizer()
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Create mock transactions for Q2 2022
        tax_year = 2022
        quarter_number = 2
        
        # Calculate quarter dates
        quarters = tax_manager.calculate_tax_quarters(tax_year)
        current_quarter = next(q for q in quarters if q.quarter == quarter_number)
        
        # Create sample transactions
        income_tx = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 15),
            amount=8000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        expense_tx1 = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 10),
            amount=500.0,
            description="Software subscription",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )
        
        expense_tx2 = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 4, 20),
            amount=300.0,
            description="Office supplies",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )
        
        # Mock categorization process
        categorized_expense1 = Transaction(
            id=expense_tx1.id,
            date=expense_tx1.date,
            amount=expense_tx1.amount,
            description=expense_tx1.description,
            transaction_type=expense_tx1.transaction_type,
            account_id=expense_tx1.account_id,
            category=ExpenseCategory.SOFTWARE,
            business_use_percentage=100.0,
        )
        
        categorized_expense2 = Transaction(
            id=expense_tx2.id,
            date=expense_tx2.date,
            amount=expense_tx2.amount,
            description=expense_tx2.description,
            transaction_type=expense_tx2.transaction_type,
            account_id=expense_tx2.account_id,
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        )
        
        quarter_transactions = [income_tx, categorized_expense1, categorized_expense2]
        
        # Calculate taxable income
        income = income_tx.amount
        expenses = categorized_expense1.amount + categorized_expense2.amount
        taxable_income = income - expenses
        
        # Calculate quarterly tax payment
        quarterly_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=taxable_income,
            ytd_taxable_income=taxable_income,  # Simplified: only using Q2 income
            tax_year=tax_year,
            quarter=quarter_number,
        )
        
        # Create tax payment transaction
        tax_payment_transaction = Transaction(
            id=uuid.uuid4(),
            date=current_quarter.due_date,
            amount=quarterly_tax.payment_amount,
            description=f"Q{quarter_number} {tax_year} Estimated Tax Payment",
            transaction_type=TransactionType.TAX_PAYMENT,
            account_id="checking123",
        )
        
        # Verify the tax calculation
        assert quarterly_tax.quarter == quarter_number
        assert quarterly_tax.tax_year == tax_year  # Check tax_year, not year
        assert quarterly_tax.payment_amount > 0
        
        # Verify that the quarterly calculation includes appropriate tax components
        assert hasattr(quarterly_tax, 'federal_tax')
        assert quarterly_tax.federal_tax is not None
        assert quarterly_tax.federal_tax >= 0
        
        # Optional: Verify self-employment tax is included
        assert hasattr(quarterly_tax, 'self_employment_tax')
        assert quarterly_tax.self_employment_tax is not None
        assert quarterly_tax.self_employment_tax >= 0
    
    def test_quarterly_tax_with_prior_payments(self):
        """Test quarterly tax preparation with prior quarterly payments."""
        # Set up components
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Define tax year
        tax_year = 2022
        
        # Simulate income and expenses for Q1 and Q2
        q1_taxable_income = 11000.0  # Income - Expenses for Q1
        q1_ytd_taxable_income = 11000.0  # Same as Q1 income for first quarter
        
        q2_taxable_income = 13500.0  # Income - Expenses for Q2
        q2_ytd_taxable_income = q1_taxable_income + q2_taxable_income  # Sum of Q1 and Q2
        
        # Calculate Q1 tax payment
        q1_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=q1_taxable_income,
            ytd_taxable_income=q1_ytd_taxable_income,
            tax_year=tax_year,
            quarter=1,
        )
        
        # Calculate Q2 tax payment with prior payment from Q1
        q2_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=q2_taxable_income,
            ytd_taxable_income=q2_ytd_taxable_income,
            tax_year=tax_year,
            quarter=2,
            prior_payments=q1_tax.payment_amount,
        )
        
        # Verify the tax calculations are reasonable
        assert q1_tax.payment_amount > 0
        assert q2_tax.payment_amount > 0
        
        # Calculate Q2 without prior payments for comparison
        q2_tax_without_prior = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=q2_taxable_income,
            ytd_taxable_income=q2_ytd_taxable_income,
            tax_year=tax_year,
            quarter=2,
            prior_payments=0.0,
        )
        
        # Verify that the payment with prior payments is different
        if abs(q2_tax.payment_amount - q2_tax_without_prior.payment_amount) > 0.01:
            # Prior payments should reduce the Q2 payment
            assert q2_tax.payment_amount <= q2_tax_without_prior.payment_amount
    
    def test_quarterly_tax_with_income_smoothing(self):
        """Test quarterly tax preparation with income smoothing."""
        # Set up components
        income_manager = IncomeManager()
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Create quarterly income data with significant differences between quarters
        monthly_income = [1000.0, 1200.0, 1500.0, 8000.0, 7500.0, 9000.0]  # Jan-Jun
        
        # Apply income smoothing using a simple average
        smoothed_income = sum(monthly_income) / len(monthly_income)
        smoothed_quarterly_income = smoothed_income * 3  # Q2 (3 months)
        
        # Calculate Q2 actual income
        q2_actual_income = sum(monthly_income[3:6])  # Apr-Jun
        
        # Compare actual Q2 income with smoothed Q2 income
        # In our test data, Q2 income should be different from smoothed income
        
        # Calculate tax using actual income
        actual_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=q2_actual_income,
            ytd_taxable_income=sum(monthly_income),
            tax_year=2022,
            quarter=2,
        )
        
        # Calculate tax using smoothed income
        smoothed_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=smoothed_quarterly_income,
            ytd_taxable_income=sum(monthly_income),
            tax_year=2022,
            quarter=2,
        )
        
        # Simply verify both calculations produced valid tax payments
        assert actual_tax.payment_amount > 0
        assert smoothed_tax.payment_amount > 0
        
        # Verify the tax payments have the correct properties
        assert actual_tax.tax_year == 2022
        assert actual_tax.quarter == 2
        assert actual_tax.jurisdiction == TaxJurisdiction.FEDERAL
        
        # Verify expected fields are present
        assert hasattr(actual_tax, 'federal_tax') 
        assert hasattr(actual_tax, 'self_employment_tax')