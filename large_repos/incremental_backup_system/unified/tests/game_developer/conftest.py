"""
Pytest configuration file for GameVault tests.
"""

import pytest


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests (can be slow)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify the test collection based on command-line options."""
    if not config.getoption("--run-performance"):
        skip_performance = pytest.mark.skip(reason="Need --run-performance option to run")
        for item in items:
            if "performance" in item.fspath.strpath:
                item.add_marker(skip_performance)