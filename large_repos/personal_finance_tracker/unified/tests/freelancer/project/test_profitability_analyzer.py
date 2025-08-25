"""Tests for the project profitability analyzer."""

from datetime import datetime, timedelta
import time
import uuid

import pytest
import pandas as pd
import numpy as np

from personal_finance_tracker.models.common import (
    Project,
    TimeEntry,
    Transaction,
    TransactionType,
)

from personal_finance_tracker.project.models import ProjectMetricType

from personal_finance_tracker.project.profitability_analyzer import ProjectProfiler


class TestProjectProfiler:
    """Test suite for the ProjectProfiler class."""

    def test_init(self):
        """Test initialization of the project profiler."""
        profiler = ProjectProfiler()
        assert profiler._profitability_cache == {}

    def test_analyze_project_profitability(
        self, sample_projects, sample_time_entries, sample_transactions, sample_invoices
    ):
        """Test project profitability analysis for a single project."""
        profiler = ProjectProfiler()

        # Test each project
        for project in sample_projects:
            # Run analysis
            analysis = profiler.analyze_project_profitability(
                project, sample_time_entries, sample_transactions, sample_invoices
            )

            # Verify analysis results
            assert analysis.project_id == project.id
            assert analysis.project_name == project.name
            assert analysis.client_id == project.client_id
            assert analysis.start_date == project.start_date
            assert analysis.end_date == project.end_date
            assert analysis.total_hours >= 0
            assert analysis.total_revenue >= 0
            assert isinstance(analysis.effective_hourly_rate, float)
            assert isinstance(analysis.profit_margin, float)
            assert isinstance(analysis.roi, float)

            # Verify metrics
            assert len(analysis.metrics) > 0
            metric_types = [m.metric_type for m in analysis.metrics]
            assert ProjectMetricType.HOURLY_RATE in metric_types
            assert ProjectMetricType.TOTAL_PROFIT in metric_types
            assert ProjectMetricType.PROFIT_MARGIN in metric_types
            assert ProjectMetricType.ROI in metric_types

    def test_analyze_client_profitability(
        self,
        sample_clients,
        sample_projects,
        sample_time_entries,
        sample_transactions,
        sample_invoices,
    ):
        """Test client profitability analysis across multiple projects."""
        profiler = ProjectProfiler()

        # Test each client
        for client in sample_clients:
            # Run analysis
            analysis = profiler.analyze_client_profitability(
                client,
                sample_projects,
                sample_time_entries,
                sample_transactions,
                sample_invoices,
            )

            # Verify analysis results
            assert analysis.client_id == client.id
            assert analysis.client_name == client.name

            # Check that client-level metrics are calculated correctly
            client_projects = [p for p in sample_projects if p.client_id == client.id]
            assert analysis.number_of_projects == len(client_projects)

            if len(client_projects) > 0:
                assert len(analysis.projects) == len(client_projects)
                assert analysis.total_hours >= 0
                assert analysis.total_revenue >= 0
                assert analysis.average_hourly_rate >= 0
                assert -100 <= analysis.average_profit_margin <= 100

    def test_analyze_all_projects(
        self, sample_projects, sample_time_entries, sample_transactions, sample_invoices
    ):
        """Test analysis of all projects at once."""
        profiler = ProjectProfiler()

        # Run analysis for all projects
        start_time = time.time()
        all_projects = profiler.analyze_all_projects(
            sample_projects, sample_time_entries, sample_transactions, sample_invoices
        )
        elapsed_time = time.time() - start_time

        # Verify results
        assert len(all_projects) == len(sample_projects)

        # Verify projects are sorted by profitability (highest first)
        for i in range(len(all_projects) - 1):
            assert all_projects[i].total_profit >= all_projects[i + 1].total_profit

    def test_generate_trend_analysis(
        self, sample_projects, sample_time_entries, sample_transactions, sample_invoices
    ):
        """Test trend analysis for project metrics over time."""
        profiler = ProjectProfiler()

        # Set up test parameters
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)
        metric_type = ProjectMetricType.HOURLY_RATE
        period = "monthly"

        # Test project-specific trend
        project_id = sample_projects[0].id
        project_trend = profiler.generate_trend_analysis(
            metric_type=metric_type,
            start_date=start_date,
            end_date=end_date,
            period=period,
            project_id=project_id,
            projects=sample_projects,
            time_entries=sample_time_entries,
            transactions=sample_transactions,
            invoices=sample_invoices,
        )

        # Verify trend results
        assert project_trend.metric_type == metric_type
        assert project_trend.project_id == project_id
        assert project_trend.period == period
        assert project_trend.start_date == start_date
        assert project_trend.end_date == end_date

        # Test client-specific trend
        client_id = sample_projects[0].client_id
        client_trend = profiler.generate_trend_analysis(
            metric_type=metric_type,
            start_date=start_date,
            end_date=end_date,
            period=period,
            client_id=client_id,
            projects=sample_projects,
            time_entries=sample_time_entries,
            transactions=sample_transactions,
            invoices=sample_invoices,
        )

        # Verify trend results
        assert client_trend.metric_type == metric_type
        assert client_trend.client_id == client_id

    def test_record_time_entry(self):
        """Test recording a new time entry."""
        profiler = ProjectProfiler()

        # Create a time entry
        time_entry = TimeEntry(
            project_id="project1",
            start_time=datetime(2022, 5, 1, 9, 0),
            end_time=datetime(2022, 5, 1, 13, 0),
            description="Test time entry",
        )

        # Record the entry
        recorded_entry = profiler.record_time_entry(time_entry)

        # Verify the entry is recorded correctly
        assert recorded_entry.id == time_entry.id
        assert recorded_entry.project_id == time_entry.project_id
        assert recorded_entry.duration_minutes == 4 * 60  # 4 hours = 240 minutes

    def test_allocate_expense(self):
        """Test allocating an expense to a project."""
        profiler = ProjectProfiler()

        # Create an expense transaction
        transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 15),
            amount=100.0,
            description="Test expense",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        # Allocate to project
        project_id = "project1"
        updated_transaction = profiler.allocate_expense(transaction, project_id)

        # Verify the allocation
        assert updated_transaction.id == transaction.id
        assert updated_transaction.project_id == project_id
        assert updated_transaction.amount == transaction.amount

    def test_analyze_large_project_set(self):
        """Test performance with a large set of projects (100+)."""
        profiler = ProjectProfiler()

        # Generate a large set of projects
        num_projects = 105  # Slightly over the 100 requirement
        projects = []
        time_entries = []
        transactions = []
        invoices = []

        # Base date for test data
        base_date = datetime(2022, 1, 1)

        for i in range(num_projects):
            # Create project
            project_id = f"large_project_{i}"
            client_id = f"client_{i % 10}"  # 10 clients

            start_date = base_date + timedelta(days=i % 30)
            end_date = start_date + timedelta(days=30) if i % 3 == 0 else None
            status = "completed" if end_date else "active"

            project = Project(
                id=project_id,
                name=f"Project {i}",
                client_id=client_id,
                start_date=start_date,
                end_date=end_date,
                status=status,
                hourly_rate=75.0 + (i % 5) * 10,  # Vary hourly rates
                estimated_hours=20.0 + (i % 8) * 5,  # Vary estimated hours
            )
            projects.append(project)

            # Add some time entries
            hours = 15 + (i % 10) * 2  # Different hours per project
            for j in range(int(hours)):
                entry_date = start_date + timedelta(days=j)
                time_entries.append(
                    TimeEntry(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        start_time=datetime.combine(entry_date, datetime.min.time())
                        + timedelta(hours=9),
                        end_time=datetime.combine(entry_date, datetime.min.time())
                        + timedelta(hours=10),
                        description=f"Work on project {i}",
                    )
                )

            # Add some expenses
            expense_count = 1 + i % 3
            for j in range(expense_count):
                transactions.append(
                    Transaction(
                        id=uuid.uuid4(),
                        date=start_date + timedelta(days=j * 5),
                        amount=50.0 + j * 20,
                        description=f"Expense for project {i}",
                        transaction_type=TransactionType.EXPENSE,
                        account_id="checking123",
                        project_id=project_id,
                    )
                )

            # Add an invoice
            invoice_amount = project.hourly_rate * hours
            invoice_date = start_date + timedelta(days=15)

            from personal_finance_tracker.models.common import Invoice

            invoices.append(
                Invoice(
                    id=f"inv_{project_id}",
                    client_id=client_id,
                    project_id=project_id,
                    issue_date=invoice_date,
                    due_date=invoice_date + timedelta(days=15),
                    amount=invoice_amount,
                    status="paid" if i % 4 != 0 else "sent",
                    payment_date=(invoice_date + timedelta(days=10))
                    if i % 4 != 0
                    else None,
                    description=f"Invoice for Project {i}",
                    line_items=[
                        {
                            "description": f"Work on Project {i}",
                            "amount": invoice_amount,
                        }
                    ],
                )
            )

        # Test performance
        start_time = time.time()
        results = profiler.analyze_all_projects(
            projects, time_entries, transactions, invoices
        )
        elapsed_time = time.time() - start_time

        # Verify performance (should be under 3 seconds for 100+ projects)
        assert elapsed_time < 3.0
        assert len(results) == num_projects
