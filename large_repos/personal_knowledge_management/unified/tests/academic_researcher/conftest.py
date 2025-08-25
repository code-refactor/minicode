"""Pytest configuration file."""

import os
import tempfile
from pathlib import Path

import pytest


def pytest_addoption(parser):
    """Add custom command line options to pytest."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests which are skipped by default",
    )


def pytest_configure(config):
    """Configure pytest environment."""
    # Register custom markers
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    
    # Set environment variable if --run-performance is used
    if config.getoption("--run-performance"):
        os.environ["RUN_LARGE_PERFORMANCE_TESTS"] = "1"


def pytest_collection_modifyitems(config, items):
    """Modify collected tests based on options."""
    # We want to run all tests, so don't skip performance tests
    pass