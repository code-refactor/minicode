"""
Pytest configuration for the vectordb tests.
"""

import pytest
import random
import os

def pytest_configure(config):
    """
    Configure pytest.

    This function sets up the test environment.
    """
    # Set a fixed random seed for deterministic test results
    random.seed(42)


def pytest_addoption(parser):
    """
    Add command-line options to pytest.
    """
    parser.addoption(
        "--run-benchmark",
        action="store_true",
        default=False,
        help="Run benchmark tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify the collected test items.
    
    This function skips benchmark tests unless explicitly requested.
    """
    if not config.getoption("--run-benchmark"):
        skip_benchmark = pytest.mark.skip(reason="Need --run-benchmark option to run")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_benchmark)


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """
    Set up the test environment.
    
    This fixture runs once per session and ensures the test environment is properly set up.
    """
    # Create any necessary directories or files for testing
    os.makedirs("./test_data", exist_ok=True)
    
    yield
    
    # Clean up after tests
    if os.path.exists("./test_data"):
        # In a real application, we would clean up temp files here
        pass