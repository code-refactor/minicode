"""Shared fixtures for testing."""

from datetime import datetime, timedelta
from typing import Dict, List
import uuid

import pytest

from personal_finance_tracker.models.common import (
    AccountType,
    Client,
    ExpenseCategory,
    Invoice,
    Project,
    TimeEntry,
    Transaction,
    TransactionType,
)


@pytest.fixture
def sample_date():
    """Base date for test data."""
    return datetime(2022, 1, 1)


@pytest.fixture
def sample_transactions(sample_date):
    """Sample transactions for testing."""
    transactions = []

    # Income transactions - variable pattern typical for freelancer
    income_amounts = [2500, 0, 4500, 1500, 3000, 500, 5000, 0, 2000, 3500, 1000, 4000]

    for i, amount in enumerate(income_amounts):
        month = i + 1  # 1-12
        year = 2022

        if month > 12:
            month -= 12
            year += 1

        date = datetime(year, month, 15)

        if amount > 0:
            transactions.append(
                Transaction(
                    id=uuid.uuid4(),
                    date=date,
                    amount=amount,
                    description=f"Client payment for Project {i}",
                    transaction_type=TransactionType.INCOME,
                    account_id="checking123",
                    client_id=f"client{i % 3 + 1}",
                    project_id=f"project{i % 5 + 1}",
                )
            )

    # Expense transactions
    expense_categories = [
        (ExpenseCategory.BUSINESS_SUPPLIES, 100, 100),
        (ExpenseCategory.SOFTWARE, 50, 100),
        (ExpenseCategory.MARKETING, 200, 100),
        (ExpenseCategory.UTILITIES, 150, 30),
        (ExpenseCategory.MEALS, 80, 50),
        (ExpenseCategory.EQUIPMENT, 500, 80),
        (ExpenseCategory.PHONE, 100, 70),
        (ExpenseCategory.INTERNET, 80, 80),
        (ExpenseCategory.CAR, 200, 60),
        (ExpenseCategory.HOME_OFFICE, 300, 40),
        (ExpenseCategory.PERSONAL, 1000, 0),
    ]

    for month in range(1, 13):
        year = 2022

        if month > 12:
            month -= 12
            year += 1

        date = datetime(year, month, 20)

        for category, amount, business_pct in expense_categories:
            transactions.append(
                Transaction(
                    id=uuid.uuid4(),
                    date=date,
                    amount=amount,
                    description=f"{category.value} expense",
                    transaction_type=TransactionType.EXPENSE,
                    account_id="checking123",
                    category=category,
                    business_use_percentage=business_pct,
                )
            )

    # Tax payment transactions
    for quarter in range(1, 5):
        # Determine payment date
        if quarter == 1:
            date = datetime(2022, 4, 15)
        elif quarter == 2:
            date = datetime(2022, 6, 15)
        elif quarter == 3:
            date = datetime(2022, 9, 15)
        else:
            date = datetime(2023, 1, 15)

        transactions.append(
            Transaction(
                id=uuid.uuid4(),
                date=date,
                amount=2000,
                description=f"Q{quarter} 2022 Estimated Tax Payment",
                transaction_type=TransactionType.TAX_PAYMENT,
                account_id="checking123",
            )
        )

    return transactions


@pytest.fixture
def sample_clients():
    """Sample clients for testing."""
    return [
        Client(
            id="client1",
            name="TechCorp Inc.",
            contact_email="contact@techcorp.com",
            active=True,
        ),
        Client(
            id="client2",
            name="Design Masters LLC",
            contact_email="projects@designmasters.com",
            active=True,
        ),
        Client(
            id="client3",
            name="Marketing Solutions",
            contact_email="info@marketsolutions.com",
            active=True,
        ),
    ]


@pytest.fixture
def sample_projects(sample_date):
    """Sample projects for testing."""
    return [
        Project(
            id="project1",
            name="Website Redesign",
            client_id="client1",
            start_date=sample_date,
            end_date=sample_date + timedelta(days=45),
            status="completed",
            hourly_rate=85.0,
            estimated_hours=40.0,
        ),
        Project(
            id="project2",
            name="Mobile App Development",
            client_id="client1",
            start_date=sample_date + timedelta(days=30),
            status="active",
            hourly_rate=95.0,
            estimated_hours=100.0,
        ),
        Project(
            id="project3",
            name="Brand Identity Package",
            client_id="client2",
            start_date=sample_date + timedelta(days=15),
            end_date=sample_date + timedelta(days=60),
            status="completed",
            fixed_price=3500.0,
            estimated_hours=35.0,
        ),
        Project(
            id="project4",
            name="Marketing Campaign",
            client_id="client3",
            start_date=sample_date + timedelta(days=75),
            status="active",
            hourly_rate=75.0,
            estimated_hours=50.0,
        ),
        Project(
            id="project5",
            name="Logo Design",
            client_id="client2",
            start_date=sample_date + timedelta(days=90),
            end_date=sample_date + timedelta(days=110),
            status="completed",
            fixed_price=1000.0,
            estimated_hours=10.0,
        ),
    ]


@pytest.fixture
def sample_time_entries(sample_projects):
    """Sample time entries for testing."""
    time_entries = []

    # Project 1
    start_date = sample_projects[0].start_date
    for day in range(30):
        if day % 3 == 0:  # Work every 3 days
            start_time = datetime.combine(
                (start_date + timedelta(days=day)).date(), datetime.min.time()
            ) + timedelta(hours=9)  # 9 AM

            end_time = start_time + timedelta(hours=4)  # 4 hour session

            time_entries.append(
                TimeEntry(
                    id=uuid.uuid4(),
                    project_id="project1",
                    start_time=start_time,
                    end_time=end_time,
                    description="Website design work",
                    billable=True,
                )
            )

    # Project 2
    start_date = sample_projects[1].start_date
    for day in range(45):
        if day % 2 == 0:  # Work every 2 days
            start_time = datetime.combine(
                (start_date + timedelta(days=day)).date(), datetime.min.time()
            ) + timedelta(hours=13)  # 1 PM

            end_time = start_time + timedelta(hours=5)  # 5 hour session

            time_entries.append(
                TimeEntry(
                    id=uuid.uuid4(),
                    project_id="project2",
                    start_time=start_time,
                    end_time=end_time,
                    description="App development",
                    billable=True,
                )
            )

    # Other projects with less detailed entries
    for project in sample_projects[2:]:
        total_hours = project.estimated_hours or 20
        days_span = (
            (project.end_date - project.start_date).days if project.end_date else 30
        )
        hours_per_day = total_hours / max(
            days_span / 3, 1
        )  # Work every 3 days on average

        for day in range(0, days_span, 3):
            start_time = datetime.combine(
                (project.start_date + timedelta(days=day)).date(), datetime.min.time()
            ) + timedelta(hours=10)  # 10 AM

            end_time = start_time + timedelta(hours=hours_per_day)

            time_entries.append(
                TimeEntry(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    start_time=start_time,
                    end_time=end_time,
                    description=f"Work on {project.name}",
                    billable=True,
                )
            )

    return time_entries


@pytest.fixture
def sample_invoices(sample_projects):
    """Sample invoices for testing."""
    invoices = []

    for i, project in enumerate(sample_projects):
        # Create 1-2 invoices per project
        invoice_count = 2 if i % 2 == 0 else 1

        for j in range(invoice_count):
            # Determine invoice details
            if project.fixed_price:
                amount = project.fixed_price / invoice_count
                description = (
                    f"Fixed price payment {j + 1}/{invoice_count} for {project.name}"
                )
            else:
                # For hourly projects, estimate based on hourly rate and estimated hours
                hours = (project.estimated_hours or 40) / invoice_count
                amount = hours * (project.hourly_rate or 75)
                description = f"Payment for {hours} hours on {project.name}"

            # Set dates
            if project.end_date:
                # For completed projects
                days_span = (project.end_date - project.start_date).days
                issue_date = project.start_date + timedelta(
                    days=days_span * (j + 1) / invoice_count
                )
                due_date = issue_date + timedelta(days=15)
                payment_date = due_date - timedelta(days=5) if i % 3 != 0 else None
                status = "paid" if payment_date else "sent"
            else:
                # For active projects
                issue_date = project.start_date + timedelta(days=30 * (j + 1))
                due_date = issue_date + timedelta(days=15)
                payment_date = due_date - timedelta(days=2) if j == 0 else None
                status = "paid" if payment_date else "sent"

            invoices.append(
                Invoice(
                    id=f"inv{project.id}-{j + 1}",
                    client_id=project.client_id,
                    project_id=project.id,
                    issue_date=issue_date,
                    due_date=due_date,
                    amount=amount,
                    status=status,
                    payment_date=payment_date,
                    description=description,
                    line_items=[{"description": description, "amount": amount}],
                )
            )

    return invoices


@pytest.fixture
def sample_account_balances(sample_date):
    """Sample account balances for testing."""
    return [
        AccountBalance(
            account_id="checking123",
            account_name="Business Checking",
            account_type=AccountType.CHECKING,
            balance=15000.0,
            as_of_date=sample_date + timedelta(days=180),
        ),
        AccountBalance(
            account_id="savings456",
            account_name="Emergency Fund",
            account_type=AccountType.SAVINGS,
            balance=10000.0,
            as_of_date=sample_date + timedelta(days=180),
        ),
        AccountBalance(
            account_id="creditcard789",
            account_name="Business Credit Card",
            account_type=AccountType.CREDIT_CARD,
            balance=-2500.0,
            as_of_date=sample_date + timedelta(days=180),
        ),
    ]
