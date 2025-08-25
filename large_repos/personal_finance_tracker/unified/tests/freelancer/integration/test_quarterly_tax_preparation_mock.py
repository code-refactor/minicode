"""Mock-based integration tests for end-to-end quarterly tax preparation."""

from datetime import datetime, timedelta
import uuid
from decimal import Decimal

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
from personal_finance_tracker.tax.models import (
    FilingStatus,
    TaxJurisdiction,
    QuarterInfo,
    EstimatedPayment,
)
from personal_finance_tracker.tax.tax_manager import TaxManager


class TestQuarterlyTaxPreparationMock:
    """Mock-based integration tests for quarterly tax preparation process."""
    
    def test_comprehensive_quarterly_tax_preparation(self):
        """Test a comprehensive end-to-end quarterly tax preparation process with mock data."""
        # Set up components
        expense_categorizer = ExpenseCategorizer()
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Define test data
        tax_year = 2022
        quarter_number = 2
        
        # Calculate quarter dates
        quarters = tax_manager.calculate_tax_quarters(tax_year)
        current_quarter = next(q for q in quarters if q.quarter == quarter_number)
        
        # Create mock transactions
        business_expenses = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 4, 15),
                amount=1200.0,
                description="Office supplies purchase",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 5, 10),
                amount=500.0,
                description="Software subscription",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
        ]
        
        income_tx = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 4, 5),
            amount=8000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        # Add expense categorization rules
        rules = [
            CategorizationRule(
                name="Software Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software", "subscription"],
                business_use_percentage=100.0,
                priority=10,
            ),
            CategorizationRule(
                name="Office Supplies Rule",
                category=ExpenseCategory.BUSINESS_SUPPLIES,
                keyword_patterns=["supplies", "office"],
                business_use_percentage=100.0,
                priority=5,
            ),
        ]
        
        for rule in rules:
            expense_categorizer.add_categorization_rule(rule)
        
        # Categorize expenses
        categorization_results = expense_categorizer.categorize_transactions(business_expenses)
        
        # Apply categorizations
        categorized_expenses = []
        for tx in business_expenses:
            for result in categorization_results:
                if result.transaction_id == tx.id:
                    categorized_tx = expense_categorizer.apply_categorization(tx, result)
                    categorized_expenses.append(categorized_tx)
                    break
        
        # Calculate taxable income
        total_income = income_tx.amount
        business_expense_amount = sum(
            tx.amount * (tx.business_use_percentage / 100.0)
            for tx in categorized_expenses
            if tx.business_use_percentage is not None
        )
        
        taxable_income = total_income - business_expense_amount
        
        # Calculate quarterly tax payment
        quarterly_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=taxable_income,
            ytd_taxable_income=taxable_income,  # Assuming this is the only income YTD
            tax_year=tax_year,
            quarter=quarter_number
        )
        
        # Calculate control (no deductions)
        control_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=total_income,  # No business expense deduction
            ytd_taxable_income=total_income,
            tax_year=tax_year,
            quarter=quarter_number
        )
        
        # Create tax payment transaction
        tax_payment_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 6, 15),  # Q2 due date
            amount=quarterly_tax.payment_amount,
            description=f"Q{quarter_number} {tax_year} Estimated Tax Payment",
            transaction_type=TransactionType.TAX_PAYMENT,
            account_id="checking123",
        )
        
        # Verify tax calculation
        assert quarterly_tax.tax_year == tax_year
        assert quarterly_tax.quarter == quarter_number
        assert quarterly_tax.payment_amount > 0
        assert quarterly_tax.jurisdiction == TaxJurisdiction.FEDERAL
        
        # Verify business expenses reduce tax liability
        assert quarterly_tax.payment_amount < control_tax.payment_amount