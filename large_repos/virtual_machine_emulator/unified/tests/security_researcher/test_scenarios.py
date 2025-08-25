"""
Tests for security demonstration scenarios.

This module tests the predefined security scenarios that demonstrate
various vulnerability classes and exploitation techniques.
"""

import pytest
from secure_vm.emulator import VirtualMachine
from secure_vm.memory import MemoryProtection, MemoryProtectionLevel
from secure_vm.scenarios import (
    SecurityScenario, BufferOverflowScenario, ReturnOrientedProgrammingScenario,
    FormatStringScenario, PrivilegeEscalationScenario, get_all_scenarios,
    compare_protection_strategies
)


def test_security_scenario_base_class():
    """Test the base SecurityScenario class."""
    # Create a simple subclass for testing
    class TestScenario(SecurityScenario):
        def __init__(self):
            super().__init__("Test Scenario", "Test description")
            
        def setup(self, vm):
            pass
            
        def get_attacks(self):
            return []
            
        def evaluate_result(self, attack_result):
            return {"success": attack_result.success}
    
    # Create the scenario
    scenario = TestScenario()
    
    # Check properties
    assert scenario.name == "Test Scenario"
    assert scenario.description == "Test description"
    
    # Check methods
    assert callable(scenario.setup)
    assert callable(scenario.get_attacks)
    assert callable(scenario.evaluate_result)


def test_buffer_overflow_scenario():
    """Test the buffer overflow demonstration scenario."""
    # Create the scenario with minimal protection
    scenario = BufferOverflowScenario(
        protection_level=MemoryProtectionLevel.MINIMAL
    )
    
    # Check basic properties
    assert scenario.name == "Classic Buffer Overflow"
    assert "buffer overflow" in scenario.description.lower()
    
    # Create a VM and set up the scenario
    vm = VirtualMachine(
        protection=MemoryProtection(
            level=MemoryProtectionLevel.MINIMAL
        )
    )
    scenario.setup(vm)
    
    # Check that setup created the necessary state
    assert scenario.buffer_address > 0
    assert scenario.return_address_location > 0
    assert scenario.target_function_address > 0
    assert scenario.overflow_size > 0
    
    # Get available attacks
    attacks = scenario.get_attacks()
    
    # Should have at least one attack
    assert len(attacks) > 0
    assert attacks[0].attack_type == "buffer_overflow"
    
    # Execute the attack
    result = attacks[0].execute(vm)
    
    # Evaluate the result
    evaluation = scenario.evaluate_result(result)
    
    # Check evaluation
    assert "success" in evaluation
    assert "attack_type" in evaluation
    assert "details" in evaluation


def test_return_oriented_programming_scenario():
    """Test the Return-Oriented Programming demonstration scenario."""
    # Create the scenario with DEP enabled
    scenario = ReturnOrientedProgrammingScenario(dep_enabled=True)
    
    # Check basic properties
    assert scenario.name == "Return-Oriented Programming"
    assert "rop" in scenario.description.lower()
    
    # Create a VM and set up the scenario
    vm = VirtualMachine(
        protection=MemoryProtection(
            level=MemoryProtectionLevel.STANDARD,
            dep_enabled=True
        )
    )
    scenario.setup(vm)
    
    # Check that setup created the necessary state
    assert scenario.buffer_address > 0
    assert scenario.overflow_size > 0
    assert len(scenario.gadgets) > 0
    
    # Get available attacks
    attacks = scenario.get_attacks()
    
    # Should have at least one attack if gadgets were found
    if len(attacks) > 0:
        assert attacks[0].attack_type == "return_oriented_programming"
        
        # Execute the attack
        result = attacks[0].execute(vm)
        
        # Evaluate the result
        evaluation = scenario.evaluate_result(result)
        
        # Check evaluation
        assert "success" in evaluation
        assert "attack_type" in evaluation
        assert "details" in evaluation
        assert "gadgets_executed" in evaluation["details"]
        assert "dep_bypassed" in evaluation["details"]


def test_format_string_scenario():
    """Test the format string vulnerability demonstration scenario."""
    # Create the scenario
    scenario = FormatStringScenario()
    
    # Check basic properties
    assert scenario.name == "Format String Vulnerability"
    assert "format string" in scenario.description.lower()
    
    # Create a VM and set up the scenario
    vm = VirtualMachine()
    scenario.setup(vm)
    
    # Check that setup created the necessary state
    assert scenario.format_string_address > 0
    assert scenario.target_address > 0
    assert scenario.original_value > 0
    
    # Get available attacks
    attacks = scenario.get_attacks()
    
    # Should have at least one attack for reading and one for writing
    assert len(attacks) >= 2
    
    # Check attack types
    attack_types = [attack.attack_type for attack in attacks]
    assert all(attack_type == "format_string" for attack_type in attack_types)
    
    # Check read/write modes
    read_attack = None
    write_attack = None
    
    for attack in attacks:
        if attack.read_only:
            read_attack = attack
        else:
            write_attack = attack
    
    assert read_attack is not None
    assert write_attack is not None
    
    # Execute the write attack
    result = write_attack.execute(vm)
    
    # Evaluate the result
    evaluation = scenario.evaluate_result(result)
    
    # Check evaluation
    assert "success" in evaluation
    assert "attack_type" in evaluation
    assert "details" in evaluation


def test_privilege_escalation_scenario():
    """Test the privilege escalation demonstration scenario."""
    # Create the scenario
    scenario = PrivilegeEscalationScenario()
    
    # Check basic properties
    assert scenario.name == "Privilege Escalation"
    assert "privilege" in scenario.description.lower()
    
    # Create a VM and set up the scenario
    vm = VirtualMachine()
    scenario.setup(vm)
    
    # Check that setup created the necessary state
    assert scenario.buffer_address > 0
    assert scenario.overflow_size > 0
    assert scenario.privilege_elevate_function > 0
    
    # Get available attacks
    attacks = scenario.get_attacks()
    
    # Should have at least two attacks
    assert len(attacks) >= 2
    
    # Check attack types
    attack_types = [attack.attack_type for attack in attacks]
    assert "buffer_overflow" in attack_types
    assert "privilege_escalation" in attack_types
    
    # Find the privilege escalation attack
    priv_attack = next(attack for attack in attacks if attack.attack_type == "privilege_escalation")
    
    # Execute the attack
    result = priv_attack.execute(vm)
    
    # Evaluate the result
    evaluation = scenario.evaluate_result(result)
    
    # Check evaluation
    assert "success" in evaluation
    assert "attack_type" in evaluation
    assert "details" in evaluation
    assert "privilege_escalated" in evaluation["details"]


def test_get_all_scenarios():
    """Test getting all available security scenarios."""
    scenarios = get_all_scenarios()
    
    # Should have several scenarios
    assert len(scenarios) >= 4
    
    # Check scenario types
    scenario_names = [scenario.name for scenario in scenarios]
    assert "Classic Buffer Overflow" in scenario_names
    assert "Return-Oriented Programming" in scenario_names
    assert "Format String Vulnerability" in scenario_names
    assert "Privilege Escalation" in scenario_names


def test_compare_protection_strategies():
    """Test comparing different protection strategies."""
    # Create a scenario and an attack
    scenario = BufferOverflowScenario()
    
    # Create a VM and set up the scenario
    vm = VirtualMachine()
    scenario.setup(vm)
    
    # Get an attack to test with
    attacks = scenario.get_attacks()
    assert len(attacks) > 0
    attack = attacks[0]
    
    # Define protection strategies to compare
    protection_strategies = [
        MemoryProtection(
            level=MemoryProtectionLevel.MINIMAL,
            dep_enabled=False,
            aslr_enabled=False,
            stack_canaries=False
        ),
        MemoryProtection(
            level=MemoryProtectionLevel.STANDARD,
            dep_enabled=True,
            aslr_enabled=False,
            stack_canaries=False
        ),
        MemoryProtection(
            level=MemoryProtectionLevel.MAXIMUM,
            dep_enabled=True,
            aslr_enabled=True,
            stack_canaries=True
        )
    ]
    
    # Compare strategies
    results = compare_protection_strategies(
        scenario, attack, protection_strategies
    )
    
    # Check results structure
    assert "scenario" in results
    assert "attack_type" in results
    assert "results" in results
    
    # Check that we have results for each strategy
    assert len(results["results"]) == len(protection_strategies)
    
    # Check that results include protection details
    for result in results["results"]:
        assert "protection" in result
        assert "attack_successful" in result
        assert "protection_events" in result
        assert "evaluation" in result