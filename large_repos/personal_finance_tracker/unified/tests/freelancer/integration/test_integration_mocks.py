"""Integration tests using mock implementations for cross-module functionality."""

import random
from datetime import datetime, timedelta
import uuid

import pytest

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
)


class TestIntegrationWithMocks:
    """Tests demonstrating integration between different system components using mocks."""

    def test_expense_categorization_impacts_tax_liability(self):
        """Test how business expense categorization impacts tax liability."""
        # Mock transactions
        transactions = [
            # Income
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 10),
                amount=10000.0,
                description="Client payment",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            ),
            # Business expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 15),
                amount=2000.0,
                description="Office equipment",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.EQUIPMENT,
                business_use_percentage=100.0,
            ),
            # Personal expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 20),
                amount=1000.0,
                description="Groceries",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,
                business_use_percentage=0.0,
            ),
            # Mixed use expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 25),
                amount=1500.0,
                description="Computer upgrade",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.EQUIPMENT,
                business_use_percentage=50.0,
            ),
        ]

        # Calculate taxable income with proper classification
        income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.INCOME)
        business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        
        taxable_income = income - business_expenses
        
        # Now recalculate with the mixed use expense categorized as personal
        misclassified_transactions = transactions.copy()
        for t in misclassified_transactions:
            if t.description == "Computer upgrade":
                t.category = ExpenseCategory.PERSONAL
                t.business_use_percentage = 0.0
        
        misclassified_business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in misclassified_transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        
        misclassified_taxable_income = income - misclassified_business_expenses
        
        # Misclassification should result in higher taxable income
        assert misclassified_taxable_income > taxable_income
        assert misclassified_taxable_income - taxable_income == 750.0  # 50% of $1500
    
    def test_categorization_correction_tax_impact(self):
        """Test the tax impact of correcting expense categorization."""
        # Mock initial transactions with a miscategorized personal expense
        transactions = [
            # Income
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 10),
                amount=8000.0,
                description="Client payment",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            ),
            # Correctly categorized business expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 15),
                amount=1000.0,
                description="Software subscription",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.SOFTWARE,
                business_use_percentage=100.0,
            ),
            # Miscategorized expense (business expense categorized as personal)
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 20),
                amount=2000.0,
                description="Professional development course",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,  # Incorrectly categorized
                business_use_percentage=0.0,  # Should be 100%
            ),
        ]
        
        # Calculate initial tax (with miscategorization)
        income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.INCOME)
        initial_business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        
        initial_taxable_income = income - initial_business_expenses
        
        # Apply correction
        corrected_transactions = transactions.copy()
        for t in corrected_transactions:
            if t.description == "Professional development course":
                t.category = ExpenseCategory.PROFESSIONAL_DEVELOPMENT
                t.business_use_percentage = 100.0
        
        # Calculate corrected tax
        corrected_business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in corrected_transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        
        corrected_taxable_income = income - corrected_business_expenses
        
        # Correction should result in lower taxable income
        assert corrected_taxable_income < initial_taxable_income
        assert initial_taxable_income - corrected_taxable_income == 2000.0  # Full amount of the course
        
    def test_quarterly_tax_estimation(self):
        """Test quarterly tax estimation based on income and expenses."""
        # Create income and expenses for each quarter
        transactions = []
        
        # Q1: January-March
        q1_income = 20000.0
        q1_expenses = 5000.0
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 2, 15),
            amount=q1_income,
            description="Q1 Client payments",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 3, 1),
            amount=q1_expenses,
            description="Q1 Business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # Q2: April-June
        q2_income = 25000.0
        q2_expenses = 6000.0
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 15),
            amount=q2_income,
            description="Q2 Client payments",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 6, 1),
            amount=q2_expenses,
            description="Q2 Business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # Q3: July-September
        q3_income = 30000.0
        q3_expenses = 7500.0
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 8, 15),
            amount=q3_income,
            description="Q3 Client payments",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 9, 1),
            amount=q3_expenses,
            description="Q3 Business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # Q4: October-December
        q4_income = 35000.0
        q4_expenses = 9000.0
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 11, 15),
            amount=q4_income,
            description="Q4 Client payments",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 12, 1),
            amount=q4_expenses,
            description="Q4 Business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # Calculate tax payments for each quarter (simplified calculation)
        # Assume effective tax rate of 25%
        def calculate_quarterly_payment(quarter_transactions, effective_tax_rate=0.25):
            income = sum(t.amount for t in quarter_transactions if t.transaction_type == TransactionType.INCOME)
            expenses = sum(
                t.amount * (t.business_use_percentage / 100.0)
                for t in quarter_transactions 
                if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
            )
            taxable_income = income - expenses
            return taxable_income * effective_tax_rate
        
        # Filter transactions by quarter
        q1_transactions = [t for t in transactions if t.date.month <= 3]
        q2_transactions = [t for t in transactions if 4 <= t.date.month <= 6]
        q3_transactions = [t for t in transactions if 7 <= t.date.month <= 9]
        q4_transactions = [t for t in transactions if t.date.month >= 10]
        
        # Calculate quarterly payments
        q1_payment = calculate_quarterly_payment(q1_transactions)
        q2_payment = calculate_quarterly_payment(q2_transactions)
        q3_payment = calculate_quarterly_payment(q3_transactions)
        q4_payment = calculate_quarterly_payment(q4_transactions)
        
        # Calculate annual income, expenses, and tax
        total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.INCOME)
        total_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        total_taxable_income = total_income - total_expenses
        total_tax = total_taxable_income * 0.25  # Assumed 25% effective tax rate
        
        # Verify total payments are close to the full year tax liability
        total_payments = q1_payment + q2_payment + q3_payment + q4_payment
        
        # Total payments should match annual tax liability
        # In real tax system there would be small differences due to quarterly estimations
        assert abs(total_payments - total_tax) < 0.01
        
    def test_multi_year_project_profitability(self):
        """Test profitability analysis for a project spanning multiple tax years."""
        # Create a project spanning 2022-2023
        project_id = "multi-year-project-123"
        
        # 2022 project transactions (Year 1)
        year1_transactions = [
            # Income from project in year 1
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 6, 15),
                amount=20000.0,
                description="Project milestone payment 1",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
                project_id=project_id,
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 11, 1),
                amount=30000.0,
                description="Project milestone payment 2",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
                project_id=project_id,
            ),
            # Expenses for project in year 1
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 5, 1),
                amount=5000.0,
                description="Project equipment",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.EQUIPMENT,
                business_use_percentage=100.0,
                project_id=project_id,
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 7, 15),
                amount=10000.0,
                description="Project software licenses",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.SOFTWARE,
                business_use_percentage=100.0,
                project_id=project_id,
            ),
        ]
        
        # 2023 project transactions (Year 2)
        year2_transactions = [
            # Income from project in year 2
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, 3, 1),
                amount=25000.0,
                description="Project milestone payment 3",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
                project_id=project_id,
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, 6, 30),
                amount=40000.0,
                description="Project final payment",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
                project_id=project_id,
            ),
            # Expenses for project in year 2
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, 2, 15),
                amount=8000.0,
                description="Project consulting",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PROFESSIONAL_SERVICES,
                business_use_percentage=100.0,
                project_id=project_id,
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, 5, 1),
                amount=7000.0,
                description="Project travel expenses",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.TRAVEL,
                business_use_percentage=100.0,
                project_id=project_id,
            ),
        ]
        
        # Calculate project profitability by year
        all_transactions = year1_transactions + year2_transactions
        
        # Calculate year 1 profitability
        year1_income = sum(t.amount for t in year1_transactions if t.transaction_type == TransactionType.INCOME)
        year1_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in year1_transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        year1_profit = year1_income - year1_expenses
        
        # Calculate year 2 profitability
        year2_income = sum(t.amount for t in year2_transactions if t.transaction_type == TransactionType.INCOME)
        year2_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0)
            for t in year2_transactions 
            if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
        )
        year2_profit = year2_income - year2_expenses
        
        # Calculate overall project profitability
        total_income = year1_income + year2_income
        total_expenses = year1_expenses + year2_expenses
        total_profit = total_income - total_expenses
        
        # Calculate profit margins
        year1_margin = year1_profit / year1_income * 100
        year2_margin = year2_profit / year2_income * 100
        total_margin = total_profit / total_income * 100
        
        # Verify profit analysis
        assert year1_profit == 35000.0
        assert year2_profit == 50000.0
        assert total_profit == 85000.0
        
        # Profitability should be higher in year 2 than year 1
        assert year2_margin > year1_margin
        
        # The overall margin should be between year 1 and year 2 margins
        assert year1_margin < total_margin < year2_margin