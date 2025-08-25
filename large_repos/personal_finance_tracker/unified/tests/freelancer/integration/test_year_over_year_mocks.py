"""Integration tests for year-over-year financial comparisons using mocks."""

import random
from datetime import datetime, timedelta
import uuid

import pytest

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
)


class TestYearOverYearComparison:
    """Integration tests for year-over-year financial comparisons."""

    def test_income_growth_analysis(self):
        """Test analyzing income growth across multiple years."""
        # Create income transactions for 3 years
        income_2021 = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2021, month, 15),
                amount=5000.0 + random.uniform(-500, 500),  # Randomize income a bit
                description=f"2021 - Month {month} income",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            )
            for month in range(1, 13)
        ]
        
        income_2022 = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, month, 15),
                amount=6000.0 + random.uniform(-500, 500),  # Income increased in 2022
                description=f"2022 - Month {month} income",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            )
            for month in range(1, 13)
        ]
        
        income_2023 = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, month, 15),
                amount=7500.0 + random.uniform(-500, 500),  # Income increased in 2023
                description=f"2023 - Month {month} income",
                transaction_type=TransactionType.INCOME,
                account_id="checking123",
            )
            for month in range(1, 13)
        ]
        
        # Calculate total income by year
        total_2021 = sum(t.amount for t in income_2021)
        total_2022 = sum(t.amount for t in income_2022)
        total_2023 = sum(t.amount for t in income_2023)
        
        # Calculate year-over-year growth
        growth_2021_2022 = (total_2022 - total_2021) / total_2021 * 100
        growth_2022_2023 = (total_2023 - total_2022) / total_2022 * 100
        
        # Calculate income stability (standard deviation as percentage of mean)
        def income_stability(transactions):
            amounts = [t.amount for t in transactions]
            mean = sum(amounts) / len(amounts)
            variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
            std_dev = variance ** 0.5
            return (std_dev / mean) * 100  # Lower is more stable
        
        stability_2021 = income_stability(income_2021)
        stability_2022 = income_stability(income_2022)
        stability_2023 = income_stability(income_2023)
        
        # Verify income growth
        assert total_2022 > total_2021
        assert total_2023 > total_2022
        
        # Verify growth percentages (should be about 20% and 25%)
        assert 15 < growth_2021_2022 < 30
        assert 20 < growth_2022_2023 < 35
        
        # Income stability should remain similar (test resilience)
        assert abs(stability_2021 - stability_2022) < 5  # Within 5% of each other
        assert abs(stability_2022 - stability_2023) < 5  # Within 5% of each other
    
    def test_expense_category_trends(self):
        """Test analyzing expense category trends across multiple years."""
        # Create expense categories with increasing business ratio over years
        
        # 2021 expenses - 60% business, 40% personal
        expenses_2021 = []
        
        # Business expenses 2021
        for i in range(10):
            expenses_2021.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2021, random.randint(1, 12), random.randint(1, 28)),
                amount=2000.0 + random.uniform(-500, 500),
                description=f"2021 Business expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=random.choice([
                    ExpenseCategory.BUSINESS_SUPPLIES,
                    ExpenseCategory.SOFTWARE,
                    ExpenseCategory.EQUIPMENT
                ]),
                business_use_percentage=100.0,
            ))
        
        # Personal expenses 2021
        for i in range(7):
            expenses_2021.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2021, random.randint(1, 12), random.randint(1, 28)),
                amount=1500.0 + random.uniform(-300, 300),
                description=f"2021 Personal expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,
                business_use_percentage=0.0,
            ))
        
        # 2022 expenses - 70% business, 30% personal
        expenses_2022 = []
        
        # Business expenses 2022
        for i in range(14):
            expenses_2022.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, random.randint(1, 12), random.randint(1, 28)),
                amount=2200.0 + random.uniform(-500, 500),
                description=f"2022 Business expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=random.choice([
                    ExpenseCategory.BUSINESS_SUPPLIES,
                    ExpenseCategory.SOFTWARE,
                    ExpenseCategory.EQUIPMENT,
                    ExpenseCategory.MARKETING
                ]),
                business_use_percentage=100.0,
            ))
        
        # Personal expenses 2022
        for i in range(6):
            expenses_2022.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, random.randint(1, 12), random.randint(1, 28)),
                amount=1600.0 + random.uniform(-300, 300),
                description=f"2022 Personal expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,
                business_use_percentage=0.0,
            ))
        
        # 2023 expenses - 80% business, 20% personal
        expenses_2023 = []
        
        # Business expenses 2023
        for i in range(16):
            expenses_2023.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, random.randint(1, 12), random.randint(1, 28)),
                amount=2500.0 + random.uniform(-500, 500),
                description=f"2023 Business expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=random.choice([
                    ExpenseCategory.BUSINESS_SUPPLIES,
                    ExpenseCategory.SOFTWARE,
                    ExpenseCategory.EQUIPMENT,
                    ExpenseCategory.MARKETING,
                    ExpenseCategory.PROFESSIONAL_DEVELOPMENT
                ]),
                business_use_percentage=100.0,
            ))
        
        # Personal expenses 2023
        for i in range(4):
            expenses_2023.append(Transaction(
                id=uuid.uuid4(),
                date=datetime(2023, random.randint(1, 12), random.randint(1, 28)),
                amount=1700.0 + random.uniform(-300, 300),
                description=f"2023 Personal expense {i+1}",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,
                business_use_percentage=0.0,
            ))
        
        # Calculate business vs personal ratio for each year
        def calculate_ratio(transactions):
            business_expenses = sum(
                t.amount * (t.business_use_percentage / 100.0)
                for t in transactions 
                if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
            )
            
            total_expenses = sum(
                t.amount
                for t in transactions 
                if t.transaction_type == TransactionType.EXPENSE
            )
            
            return (business_expenses / total_expenses) * 100 if total_expenses > 0 else 0
        
        ratio_2021 = calculate_ratio(expenses_2021)
        ratio_2022 = calculate_ratio(expenses_2022)
        ratio_2023 = calculate_ratio(expenses_2023)
        
        # Verify business expense ratio is increasing
        assert 50 < ratio_2021 < 70  # Around 60%
        assert 60 < ratio_2022 < 80  # Around 70%
        assert 70 < ratio_2023 < 90  # Around 80%
        
        # Due to random nature, we can't guarantee exact ordering but should trend up
        # Each year should have a similar or higher ratio than the previous
        assert ratio_2022 >= ratio_2021 - 5  # Allow small variations due to randomness
        assert ratio_2023 >= ratio_2022 - 5  # Allow small variations due to randomness
    
    def test_tax_liability_comparison(self):
        """Test comparing tax liabilities across multiple years."""
        # Create income and expenses for multiple years with increasing income
        all_transactions = []
        
        # 2021 - Base income
        income_2021 = 60000.0
        expenses_2021 = 15000.0
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2021, 6, 30),
            amount=income_2021,
            description="2021 income",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2021, 6, 30),
            amount=expenses_2021,
            description="2021 business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # 2022 - 20% income increase
        income_2022 = income_2021 * 1.2
        expenses_2022 = expenses_2021 * 1.15  # 15% expense increase
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 6, 30),
            amount=income_2022,
            description="2022 income",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 6, 30),
            amount=expenses_2022,
            description="2022 business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # 2023 - Another 20% income increase
        income_2023 = income_2022 * 1.2
        expenses_2023 = expenses_2022 * 1.15  # 15% expense increase
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2023, 6, 30),
            amount=income_2023,
            description="2023 income",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        ))
        
        all_transactions.append(Transaction(
            id=uuid.uuid4(),
            date=datetime(2023, 6, 30),
            amount=expenses_2023,
            description="2023 business expenses",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            business_use_percentage=100.0,
        ))
        
        # Calculate tax liabilities (simplified for mock test)
        def calculate_tax(year_transactions, year):
            income = sum(
                t.amount 
                for t in year_transactions 
                if t.transaction_type == TransactionType.INCOME and t.date.year == year
            )
            
            expenses = sum(
                t.amount * (t.business_use_percentage / 100.0)
                for t in year_transactions 
                if t.transaction_type == TransactionType.EXPENSE 
                and t.date.year == year
                and t.business_use_percentage is not None
            )
            
            taxable_income = income - expenses
            
            # Simplified progressive tax brackets
            if taxable_income <= 20000:
                return taxable_income * 0.10
            elif taxable_income <= 50000:
                return 2000 + (taxable_income - 20000) * 0.15
            elif taxable_income <= 100000:
                return 2000 + 4500 + (taxable_income - 50000) * 0.25
            else:
                return 2000 + 4500 + 12500 + (taxable_income - 100000) * 0.35
        
        tax_2021 = calculate_tax(all_transactions, 2021)
        tax_2022 = calculate_tax(all_transactions, 2022)
        tax_2023 = calculate_tax(all_transactions, 2023)
        
        # Calculate effective tax rates
        taxable_2021 = income_2021 - expenses_2021
        taxable_2022 = income_2022 - expenses_2022
        taxable_2023 = income_2023 - expenses_2023
        
        rate_2021 = tax_2021 / taxable_2021 * 100 if taxable_2021 > 0 else 0
        rate_2022 = tax_2022 / taxable_2022 * 100 if taxable_2022 > 0 else 0
        rate_2023 = tax_2023 / taxable_2023 * 100 if taxable_2023 > 0 else 0
        
        # Verify tax liability increases with income
        assert tax_2022 > tax_2021
        assert tax_2023 > tax_2022
        
        # Due to progressive taxation, effective rate should increase
        assert rate_2022 > rate_2021
        assert rate_2023 > rate_2022
    
    def test_project_profitability_trends(self):
        """Test analyzing project profitability trends across multiple years."""
        # Create projects across multiple years with improving profitability
        
        # 2021 Projects (baseline profitability)
        projects_2021 = [
            # Project 1: 65% profit margin
            {
                "id": "project-2021-1",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2021, 3, 15),
                        amount=10000.0,
                        description="Project 2021-1 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2021-1",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2021, 2, 10),
                        amount=3500.0,
                        description="Project 2021-1 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2021-1",
                    ),
                ]
            },
            # Project 2: 60% profit margin
            {
                "id": "project-2021-2",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2021, 8, 20),
                        amount=15000.0,
                        description="Project 2021-2 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2021-2",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2021, 7, 15),
                        amount=6000.0,
                        description="Project 2021-2 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2021-2",
                    ),
                ]
            },
        ]
        
        # 2022 Projects (improved profitability)
        projects_2022 = [
            # Project 1: 70% profit margin
            {
                "id": "project-2022-1",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2022, 4, 10),
                        amount=12000.0,
                        description="Project 2022-1 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2022-1",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2022, 3, 5),
                        amount=3600.0,
                        description="Project 2022-1 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2022-1",
                    ),
                ]
            },
            # Project 2: 72% profit margin
            {
                "id": "project-2022-2",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2022, 9, 15),
                        amount=18000.0,
                        description="Project 2022-2 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2022-2",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2022, 8, 10),
                        amount=5000.0,
                        description="Project 2022-2 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2022-2",
                    ),
                ]
            },
        ]
        
        # 2023 Projects (further improved profitability)
        projects_2023 = [
            # Project 1: 75% profit margin
            {
                "id": "project-2023-1",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2023, 2, 20),
                        amount=14000.0,
                        description="Project 2023-1 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2023-1",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2023, 1, 15),
                        amount=3500.0,
                        description="Project 2023-1 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2023-1",
                    ),
                ]
            },
            # Project 2: 78% profit margin
            {
                "id": "project-2023-2",
                "transactions": [
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2023, 7, 10),
                        amount=20000.0,
                        description="Project 2023-2 income",
                        transaction_type=TransactionType.INCOME,
                        account_id="checking123",
                        project_id="project-2023-2",
                    ),
                    Transaction(
                        id=uuid.uuid4(),
                        date=datetime(2023, 6, 5),
                        amount=4400.0,
                        description="Project 2023-2 expenses",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        category=ExpenseCategory.BUSINESS_SUPPLIES,
                        business_use_percentage=100.0,
                        project_id="project-2023-2",
                    ),
                ]
            },
        ]
        
        # Calculate profit margins by year
        def calculate_profit_margin(projects):
            all_transactions = []
            for project in projects:
                all_transactions.extend(project["transactions"])
                
            income = sum(
                t.amount 
                for t in all_transactions 
                if t.transaction_type == TransactionType.INCOME
            )
            
            expenses = sum(
                t.amount * (t.business_use_percentage / 100.0)
                for t in all_transactions 
                if t.transaction_type == TransactionType.EXPENSE and t.business_use_percentage is not None
            )
            
            profit = income - expenses
            margin = (profit / income) * 100 if income > 0 else 0
            
            return margin
        
        margin_2021 = calculate_profit_margin(projects_2021)
        margin_2022 = calculate_profit_margin(projects_2022)
        margin_2023 = calculate_profit_margin(projects_2023)
        
        # Verify profit margins improve year over year
        assert 60 < margin_2021 < 65
        assert 70 < margin_2022 < 75
        assert 75 < margin_2023 < 80
        
        # Each year should show improvement
        assert margin_2022 > margin_2021
        assert margin_2023 > margin_2022