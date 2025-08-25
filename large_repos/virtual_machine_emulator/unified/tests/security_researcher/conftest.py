"""
Configuration for pytest.

This module sets up fixtures and configuration for testing the secure VM
emulator.
"""

import os
import pytest
from secure_vm.emulator import VirtualMachine
from secure_vm.memory import MemoryProtection, MemoryProtectionLevel


@pytest.fixture
def basic_vm():
    """Create a basic VM with default settings."""
    return VirtualMachine()


@pytest.fixture
def secure_vm():
    """Create a VM with enhanced security settings."""
    return VirtualMachine(
        protection=MemoryProtection(
            level=MemoryProtectionLevel.ENHANCED,
            dep_enabled=True,
            aslr_enabled=True,
            stack_canaries=True,
            shadow_memory=True
        ),
        detailed_logging=True
    )


@pytest.fixture
def vulnerable_vm():
    """Create a VM with minimal security for vulnerability demos."""
    return VirtualMachine(
        protection=MemoryProtection(
            level=MemoryProtectionLevel.MINIMAL,
            dep_enabled=False,
            aslr_enabled=False,
            stack_canaries=False,
            shadow_memory=False
        ),
        detailed_logging=True
    )


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    print("Starting test suite for Secure VM emulator...")


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    print(f"Test suite completed with status: {exitstatus}")


def pytest_configure(config):
    """
    Configure pytest.
    """
    # Add markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "security: marks tests related to security features"
    )
    config.addinivalue_line(
        "markers", "performance: marks performance benchmark tests"
    )


@pytest.fixture(scope="function")
def temp_program():
    """
    Create a simple test program.
    
    Returns:
        list: A list of instruction bytes for a simple program
        that moves a value to R0 and halts.
    """
    # MOV R0, 42; HALT
    return [0x10, 0x00, 0x01, 42, 0, 0, 0, 0xF1]