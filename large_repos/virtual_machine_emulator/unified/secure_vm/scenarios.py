"""
Predefined security scenarios for demonstration and education.

This module provides ready-to-use scenarios demonstrating different vulnerability
classes and exploitation techniques.
"""

from __future__ import annotations
import struct
from typing import Dict, List, Optional, Tuple, Union, Any

from secure_vm.emulator import VirtualMachine
from secure_vm.memory import MemoryProtection, MemoryProtectionLevel, MemoryPermission
from secure_vm.attacks import (
    Attack, BufferOverflow, ReturnOrientedProgramming, 
    FormatStringVulnerability, CodeInjection, PrivilegeEscalation,
    create_shellcode, find_rop_gadgets, AttackResult
)


class SecurityScenario:
    """Base class for security demonstration scenarios."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def setup(self, vm: VirtualMachine) -> None:
        """Set up the scenario in the provided VM."""
        raise NotImplementedError("Subclasses must implement setup()")
    
    def get_attacks(self) -> List[Attack]:
        """Get the attacks that can be used with this scenario."""
        raise NotImplementedError("Subclasses must implement get_attacks()")
    
    def evaluate_result(self, attack_result: AttackResult) -> Dict[str, Any]:
        """Evaluate the result of an attack against this scenario."""
        raise NotImplementedError("Subclasses must implement evaluate_result()")


class BufferOverflowScenario(SecurityScenario):
    """
    Classic buffer overflow vulnerability scenario.
    
    This scenario demonstrates a stack buffer overflow vulnerability that
    allows overwriting a return address to redirect execution.
    """
    
    def __init__(self, protection_level: MemoryProtectionLevel = MemoryProtectionLevel.MINIMAL):
        super().__init__(
            name="Classic Buffer Overflow",
            description=(
                "Demonstrates a classic stack-based buffer overflow vulnerability "
                "that allows overwriting a return address to redirect execution. "
                "This scenario shows how memory corruption can lead to arbitrary "
                "code execution."
            )
        )
        self.protection_level = protection_level
        self.buffer_address = 0
        self.return_address_location = 0
        self.target_function_address = 0
        self.overflow_size = 0
    
    def setup(self, vm: VirtualMachine) -> None:
        """Set up the buffer overflow scenario."""
        # Reset the VM first
        vm.reset()
        
        # Create a vulnerable program
        program = self._create_program()
        
        # Load the program into the VM
        vm.load_program(program)
        
        # Record important addresses for attacks
        self.buffer_address = vm.data_segment.base_address + 100
        self.return_address_location = self.buffer_address + 64
        self.target_function_address = vm.code_segment.base_address + 64
        self.overflow_size = 80  # Enough to overflow past the buffer to the return address
    
    def _create_program(self) -> List[int]:
        """Create a program with a buffer overflow vulnerability."""
        # This is a simplified program that simulates a buffer overflow vulnerability
        # The key elements are:
        # 1. A function that creates a buffer on the stack
        # 2. A function that unsafely copies data into that buffer
        # 3. A "sensitive" function that should not be called directly
        
        program = []
        
        # Main function: sets up the environment and calls the vulnerable function
        # Starting at offset 0
        main = [
            0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,  # MOV R0, 0 (to be used as counter)
            0x10, 0x01, 0x02, 0x10, 0x00, 0x00, 0x00,  # MOV R1, 0x10 (loop limit)
            
            # Loop start (offset 14)
            0x01, 0x00, 0x00,  # ADD R0, R0 (increment counter)
            0x02, 0x01, 0x00,  # SUB R1, R0 (decrement remaining)
            
            # Call the vulnerable function (offset 20)
            0x10, 0x02, 0x03, 0x40, 0x00, 0x00, 0x00,  # MOV R2, 0x40 (vulnerable function)
            0x23, 0x02,  # CALL R2
            
            # Check if we need to loop again (offset 29)
            0x22, 0x02,  # JNZ R2 (jump to loop start if not zero)
            
            # Exit program (offset 31)
            0xF1,  # HALT
        ]
        program.extend(main)
        
        # Pad to offset 64 where our "vulnerable" function starts
        program.extend([0xF0] * (64 - len(program)))  # NOP padding
        
        # Vulnerable function at offset 64
        # This function simulates a vulnerability by allowing a buffer overflow
        vuln_func = [
            # Function prologue
            0x13, 0x05,  # PUSH R5 (save caller's R5)
            0x10, 0x05, 0x06, 0x40, 0x00, 0x00, 0x00,  # MOV R5, 64 (buffer size)
            
            # Create a buffer on the stack (allocate by decrementing SP)
            0x10, 0x00, 0x01, 0x40, 0x00, 0x00, 0x00,  # MOV R0, 64 (buffer size)
            0x02, 0x07, 0x00,  # SUB SP, R0 (allocate buffer on stack)
            
            # Store buffer address in R1
            0x10, 0x01, 0x07,  # MOV R1, SP
            
            # Call function to fill buffer (potentially with overflow)
            0x10, 0x00, 0x02, 0x88, 0x00, 0x00, 0x00,  # MOV R0, 0x88 (fill buffer function)
            0x23, 0x00,  # CALL R0
            
            # Function epilogue: cleanup and return
            0x01, 0x07, 0x05,  # ADD SP, R5 (deallocate buffer)
            0x14, 0x05,  # POP R5 (restore caller's R5)
            0x24,  # RET
        ]
        program.extend(vuln_func)
        
        # Pad to offset 128 where our "sensitive" function starts
        program.extend([0xF0] * (128 - len(program)))  # NOP padding
        
        # Sensitive function that should not be called directly
        # This represents the target of our buffer overflow attack
        sensitive_func = [
            # Do something "sensitive" (change privilege level)
            0x32, 0x02,  # ELEVATE 2 (kernel privilege)
            0x10, 0x00, 0x01, 0xAA, 0xAA, 0xAA, 0xAA,  # MOV R0, 0xAAAAAAAA (sensitive value)
            0x10, 0x01, 0x02, 0x30, 0x00, 0x00, 0x00,  # MOV R1, 0x3000 (address to store)
            0x12, 0x01, 0x00,  # STORE R1, R0 (store sensitive value)
            0x33, 0x00,  # LOWER 0 (back to user privilege)
            0x24,  # RET
        ]
        program.extend(sensitive_func)
        
        # Pad to offset 192 where our "fill buffer" function starts
        program.extend([0xF0] * (192 - len(program)))  # NOP padding
        
        # Fill buffer function - with vulnerability
        # This function has a buffer overflow vulnerability because it doesn't check bounds
        fill_func = [
            # R1 contains buffer address from caller
            # Fill buffer with a pattern that could include malicious content
            0x10, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00,  # MOV R2, 0 (offset)
            
            # Loop to fill buffer
            # This loop will fill more than the buffer size if not careful
            0x10, 0x03, 0x04, 0x80, 0x00, 0x00, 0x00,  # MOV R3, 128 (will overflow!)
            
            # Loop start
            0x10, 0x04, 0x05, 0x41, 0x41, 0x41, 0x41,  # MOV R4, 0x41414141 ('AAAA')
            0x01, 0x00, 0x02,  # ADD R0, R2 (R0 = buffer + offset)
            0x12, 0x00, 0x04,  # STORE R0, R4 (store 'AAAA' at current position)
            
            # Increment and check
            0x10, 0x04, 0x05, 0x04, 0x00, 0x00, 0x00,  # MOV R4, 4 (word size)
            0x01, 0x02, 0x04,  # ADD R2, R4 (increment offset)
            0x02, 0x03, 0x04,  # SUB R3, R4 (decrement remaining)
            
            # Check if done
            0x22, 0x00,  # JNZ R0 (jump back to loop start if not zero)
            
            0x24,  # RET
        ]
        program.extend(fill_func)
        
        return program
    
    def get_attacks(self) -> List[Attack]:
        """Get available attacks for this scenario."""
        attacks = []
        
        # Basic buffer overflow targeting the sensitive function
        attacks.append(BufferOverflow(
            buffer_address=self.buffer_address,
            overflow_size=self.overflow_size,
            target_address=self.target_function_address,
        ))
        
        return attacks
    
    def evaluate_result(self, attack_result: AttackResult) -> Dict[str, Any]:
        """Evaluate the result of an attack against this scenario."""
        evaluation = {
            "success": attack_result.success,
            "attack_type": attack_result.attack_type,
            "details": {},
        }
        
        # Check for control flow hijacking
        for event in attack_result.detection_events:
            if event.get("type") == "control_flow_hijack":
                evaluation["details"]["control_flow_hijacked"] = True
                evaluation["details"]["hijack_target"] = event["to"]
                break
        
        # Check for privilege escalation (specific to this scenario)
        trace = attack_result.execution_trace
        final_state = trace.get("final_state", {})
        registers = final_state.get("cpu_registers", {})
        
        if registers.get("PRIV", 0) > 0:
            evaluation["details"]["privilege_escalated"] = True
            evaluation["details"]["privilege_level"] = registers["PRIV"]
        
        return evaluation


class ReturnOrientedProgrammingScenario(SecurityScenario):
    """
    Return-Oriented Programming (ROP) demonstration scenario.
    
    This scenario showcases how an attacker can chain together existing code
    fragments ending in return instructions to bypass DEP protections.
    """
    
    def __init__(self, dep_enabled: bool = True):
        super().__init__(
            name="Return-Oriented Programming",
            description=(
                "Demonstrates a Return-Oriented Programming (ROP) attack that "
                "chains together existing code fragments (gadgets) to perform "
                "arbitrary operations without injecting new code, bypassing "
                "Data Execution Prevention (DEP) protections."
            )
        )
        self.dep_enabled = dep_enabled
        self.buffer_address = 0
        self.overflow_size = 0
        self.gadgets = []
    
    def setup(self, vm: VirtualMachine) -> None:
        """Set up the ROP scenario."""
        # Reset the VM first
        vm.reset()
        
        # Create a program with useful ROP gadgets
        program = self._create_program_with_gadgets()
        
        # Load the program into the VM
        vm.load_program(program)
        
        # Find ROP gadgets in the loaded program
        raw_gadgets = find_rop_gadgets(vm)
        self.gadgets = [(addr, desc) for addr, _, desc in raw_gadgets]
        
        # Record important addresses for attacks
        self.buffer_address = vm.data_segment.base_address + 100
        self.overflow_size = 80
    
    def _create_program_with_gadgets(self) -> List[int]:
        """Create a program with deliberate ROP gadgets."""
        program = []
        
        # Main function: sets up the environment and calls the vulnerable function
        main = [
            0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,  # MOV R0, 0
            0x10, 0x01, 0x02, 0x40, 0x00, 0x00, 0x00,  # MOV R1, 0x40 (vulnerable function)
            0x23, 0x01,  # CALL R1
            0xF1,  # HALT
        ]
        program.extend(main)
        
        # Pad to offset 64 where our "vulnerable" function starts
        program.extend([0xF0] * (64 - len(program)))  # NOP padding
        
        # Vulnerable function
        vuln_func = [
            # Function prologue
            0x13, 0x05,  # PUSH R5
            0x10, 0x05, 0x06, 0x40, 0x00, 0x00, 0x00,  # MOV R5, 64
            
            # Create a buffer on the stack
            0x10, 0x00, 0x01, 0x40, 0x00, 0x00, 0x00,  # MOV R0, 64
            0x02, 0x07, 0x00,  # SUB SP, R0
            
            # Store buffer address in R1
            0x10, 0x01, 0x07,  # MOV R1, SP
            
            # Call function to fill buffer
            0x10, 0x00, 0x02, 0x88, 0x00, 0x00, 0x00,  # MOV R0, 0x88
            0x23, 0x00,  # CALL R0
            
            # Function epilogue
            0x01, 0x07, 0x05,  # ADD SP, R5
            0x14, 0x05,  # POP R5
            0x24,  # RET
        ]
        program.extend(vuln_func)
        
        # Add intentional ROP gadgets
        # These are small code sequences that end with RET
        
        # Gadget 1: Load a value into R0
        gadget1 = [
            0x10, 0x00, 0x01, 0xAA, 0xBB, 0xCC, 0xDD,  # MOV R0, 0xAABBCCDD
            0x24,  # RET
        ]
        program.extend(gadget1)
        
        # Gadget 2: Load a value into R1
        gadget2 = [
            0x10, 0x01, 0x02, 0x11, 0x22, 0x33, 0x44,  # MOV R1, 0x11223344
            0x24,  # RET
        ]
        program.extend(gadget2)
        
        # Gadget 3: Store R0 to address in R1
        gadget3 = [
            0x12, 0x01, 0x00,  # STORE R1, R0
            0x24,  # RET
        ]
        program.extend(gadget3)
        
        # Gadget 4: Pop multiple registers
        gadget4 = [
            0x14, 0x00,  # POP R0
            0x14, 0x01,  # POP R1
            0x24,  # RET
        ]
        program.extend(gadget4)
        
        # Gadget 5: Elevate privilege
        gadget5 = [
            0x32, 0x02,  # ELEVATE 2
            0x24,  # RET
        ]
        program.extend(gadget5)
        
        # Gadget 6: Add registers
        gadget6 = [
            0x01, 0x00, 0x01,  # ADD R0, R1
            0x24,  # RET
        ]
        program.extend(gadget6)
        
        # Fill buffer function with vulnerability
        fill_func = [
            # R1 contains buffer address from caller
            # Fill with pattern
            0x10, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00,  # MOV R2, 0 (offset)
            
            # Loop to fill buffer
            0x10, 0x03, 0x04, 0x80, 0x00, 0x00, 0x00,  # MOV R3, 128 (will overflow!)
            
            # Loop start
            0x10, 0x04, 0x05, 0x41, 0x41, 0x41, 0x41,  # MOV R4, 0x41414141 ('AAAA')
            0x01, 0x00, 0x02,  # ADD R0, R2
            0x12, 0x00, 0x04,  # STORE R0, R4
            
            # Increment and check
            0x10, 0x04, 0x05, 0x04, 0x00, 0x00, 0x00,  # MOV R4, 4
            0x01, 0x02, 0x04,  # ADD R2, R4
            0x02, 0x03, 0x04,  # SUB R3, R4
            
            # Check if done
            0x22, 0x00,  # JNZ R0
            
            0x24,  # RET
        ]
        program.extend(fill_func)
        
        return program
    
    def get_attacks(self) -> List[Attack]:
        """Get available attacks for this scenario."""
        attacks = []
        
        # Only create ROP attack if we found gadgets
        if len(self.gadgets) >= 3:
            # Use the first 3 gadgets for a simple chain
            rop_chain = self.gadgets[:3]
            attacks.append(ReturnOrientedProgramming(
                buffer_address=self.buffer_address,
                overflow_size=self.overflow_size,
                gadgets=rop_chain,
            ))
        
        return attacks
    
    def evaluate_result(self, attack_result: AttackResult) -> Dict[str, Any]:
        """Evaluate the result of an ROP attack against this scenario."""
        evaluation = {
            "success": attack_result.success,
            "attack_type": attack_result.attack_type,
            "details": {},
        }
        
        # Check how many gadgets were executed
        trace = attack_result.execution_trace
        evaluation["details"]["gadgets_executed"] = trace.get("rop_gadgets_executed", 0)
        evaluation["details"]["total_gadgets"] = trace.get("total_rop_gadgets", 0)
        
        # Check if DEP was bypassed
        dep_bypassed = False
        dep_violations = 0
        
        for event in attack_result.detection_events:
            if event.get("access_type") == "execute" and event.get("required_permission") == "EXECUTE":
                dep_violations += 1
        
        dep_bypassed = evaluation["details"]["gadgets_executed"] > 0 and dep_violations == 0
        evaluation["details"]["dep_bypassed"] = dep_bypassed
        evaluation["details"]["dep_violations"] = dep_violations
        
        return evaluation


class FormatStringScenario(SecurityScenario):
    """
    Format string vulnerability demonstration scenario.
    
    This scenario demonstrates how format string vulnerabilities can be
    exploited to read or write arbitrary memory locations.
    """
    
    def __init__(self):
        super().__init__(
            name="Format String Vulnerability",
            description=(
                "Demonstrates a format string vulnerability that allows an attacker "
                "to read or write to arbitrary memory locations by exploiting "
                "string formatting functions."
            )
        )
        self.format_string_address = 0
        self.target_address = 0
        self.original_value = 0
    
    def setup(self, vm: VirtualMachine) -> None:
        """Set up the format string scenario."""
        # Reset the VM first
        vm.reset()
        
        # Create a program with a format string vulnerability
        program = self._create_program()
        
        # Load the program into the VM
        vm.load_program(program)
        
        # Set up target locations
        self.format_string_address = vm.data_segment.base_address + 200
        self.target_address = vm.data_segment.base_address + 400
        
        # Initialize the target memory location with a value
        vm.memory.write_word(self.target_address, 0x12345678)
        self.original_value = 0x12345678
    
    def _create_program(self) -> List[int]:
        """Create a program with a format string vulnerability."""
        program = []
        
        # Main function that processes a format string
        main = [
            # Set up registers
            0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,  # MOV R0, 0
            
            # Call the format processor function
            0x10, 0x01, 0x02, 0x40, 0x00, 0x00, 0x00,  # MOV R1, 0x40 (format processor)
            0x23, 0x01,  # CALL R1
            
            # Check result and exit
            0xF1,  # HALT
        ]
        program.extend(main)
        
        # Pad to offset 64 where our format processor function starts
        program.extend([0xF0] * (64 - len(program)))  # NOP padding
        
        # Format processor function (vulnerable to format string attacks)
        format_func = [
            # Function prologue
            0x13, 0x05,  # PUSH R5
            
            # Get format string address
            0x10, 0x01, 0x02, 0x00, 0x00, 0x02, 0x00,  # MOV R1, data_segment+200 (format string)
            
            # Process the format string (vulnerable - no validation)
            # This simulates a function like printf that interprets format specifiers
            
            # Read the format string to look for specifiers
            0x11, 0x02, 0x01,  # LOAD R2, R1
            
            # Check if it contains specifiers (simplified)
            0x10, 0x03, 0x04, 0x25, 0x00, 0x00, 0x00,  # MOV R3, 0x25 ('%' character)
            0x02, 0x02, 0x03,  # SUB R2, R3
            
            # If it contains a '%n' specifier, it could write to memory
            0x10, 0x00, 0x04, 0x6E, 0x00, 0x00, 0x00,  # MOV R0, 0x6E ('n' character)
            0x11, 0x02, 0x01,  # LOAD R2, R1 (load next character)
            0x02, 0x02, 0x00,  # SUB R2, R0 (compare with 'n')
            
            # If we found '%n', perform a write (vulnerable!)
            0x21, 0x02,  # JZ R2 (skip if not '%n')
            
            # Vulnerable: writing a value to memory based on format string
            # This simulates how %n writes the number of characters processed
            0x10, 0x03, 0x04, 0x10, 0x00, 0x00, 0x00,  # MOV R3, 16 (characters processed)
            0x11, 0x02, 0x01,  # LOAD R2, R1 (load address to write to from format string)
            0x12, 0x02, 0x03,  # STORE R2, R3 (write to the address)
            
            # Function epilogue
            0x14, 0x05,  # POP R5
            0x24,  # RET
        ]
        program.extend(format_func)
        
        return program
    
    def get_attacks(self) -> List[Attack]:
        """Get available attacks for this scenario."""
        attacks = []
        
        # Read attack
        attacks.append(FormatStringVulnerability(
            format_string_address=self.format_string_address,
            read_only=True,
        ))
        
        # Write attack
        attacks.append(FormatStringVulnerability(
            format_string_address=self.format_string_address,
            target_address=self.target_address,
            target_value=0xDEADBEEF,
            read_only=False,
        ))
        
        return attacks
    
    def evaluate_result(self, attack_result: AttackResult) -> Dict[str, Any]:
        """Evaluate the result of a format string attack."""
        evaluation = {
            "success": attack_result.success,
            "attack_type": attack_result.attack_type,
            "details": {},
        }
        
        # For write attacks, check if the target value was modified
        trace = attack_result.execution_trace
        initial_state = trace.get("initial_state", {})
        final_state = trace.get("final_state", {})
        
        if "target_address_value" in initial_state and "target_address_value" in final_state:
            initial_value = initial_state["target_address_value"]
            final_value = final_state["target_address_value"]
            
            evaluation["details"]["initial_value"] = initial_value
            evaluation["details"]["final_value"] = final_value
            evaluation["details"]["value_changed"] = initial_value != final_value
        
        if attack_result.attack_type == "format_string" and not attack_result.success:
            evaluation["details"]["protection_events"] = len(attack_result.detection_events)
        
        return evaluation


class PrivilegeEscalationScenario(SecurityScenario):
    """
    Privilege escalation demonstration scenario.
    
    This scenario demonstrates how an attacker can exploit vulnerabilities to
    gain higher privilege levels than intended.
    """
    
    def __init__(self):
        super().__init__(
            name="Privilege Escalation",
            description=(
                "Demonstrates how attackers can exploit vulnerabilities to "
                "elevate their privileges from unprivileged user code to "
                "higher privilege levels with more system access."
            )
        )
        self.buffer_address = 0
        self.overflow_size = 0
        self.privilege_elevate_function = 0
    
    def setup(self, vm: VirtualMachine) -> None:
        """Set up the privilege escalation scenario."""
        # Reset the VM first
        vm.reset()
        
        # Create a program with a privilege boundary
        program = self._create_program()
        
        # Load the program into the VM
        vm.load_program(program)
        
        # Set up attack parameters
        self.buffer_address = vm.data_segment.base_address + 100
        self.overflow_size = 80
        self.privilege_elevate_function = vm.code_segment.base_address + 160
    
    def _create_program(self) -> List[int]:
        """Create a program with a privilege boundary."""
        program = []
        
        # Main function - unprivileged
        main = [
            # Start in user mode (unprivileged)
            0x10, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,  # MOV R0, 0 (user level)
            
            # Call a regular function
            0x10, 0x01, 0x02, 0x40, 0x00, 0x00, 0x00,  # MOV R1, 0x40 (regular function)
            0x23, 0x01,  # CALL R1
            
            # Try to access privileged memory (will fail without escalation)
            0x10, 0x01, 0x02, 0x70, 0x00, 0x00, 0x00,  # MOV R1, 0x70 (privileged data)
            0x11, 0x00, 0x01,  # LOAD R0, R1 (attempt to read privileged data)
            
            # Exit
            0xF1,  # HALT
        ]
        program.extend(main)
        
        # Pad to offset 64 where our regular function starts
        program.extend([0xF0] * (64 - len(program)))  # NOP padding
        
        # Regular function - has a buffer overflow vulnerability
        regular_func = [
            # Function prologue
            0x13, 0x05,  # PUSH R5
            
            # Create a buffer on the stack
            0x10, 0x00, 0x01, 0x40, 0x00, 0x00, 0x00,  # MOV R0, 64 (buffer size)
            0x02, 0x07, 0x00,  # SUB SP, R0 (allocate buffer)
            
            # Store buffer address in R1
            0x10, 0x01, 0x07,  # MOV R1, SP
            
            # Do something with the buffer (vulnerable)
            0x10, 0x02, 0x03, 0x50, 0x00, 0x00, 0x00,  # MOV R2, 0x50 (buffer filler)
            0x23, 0x02,  # CALL R2
            
            # Function epilogue
            0x01, 0x07, 0x00,  # ADD SP, R0 (deallocate buffer)
            0x14, 0x05,  # POP R5
            0x24,  # RET
        ]
        program.extend(regular_func)
        
        # Pad to offset 128 where the buffer filler function starts
        program.extend([0xF0] * (128 - len(program)))  # NOP padding
        
        # Buffer filler function - vulnerable to overflow
        buffer_fill = [
            # R1 contains buffer address
            0x10, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00,  # MOV R2, 0 (offset)
            
            # Loop to fill buffer
            0x10, 0x03, 0x04, 0x80, 0x00, 0x00, 0x00,  # MOV R3, 128 (will overflow!)
            
            # Loop start
            0x10, 0x04, 0x05, 0x41, 0x41, 0x41, 0x41,  # MOV R4, 0x41414141 ('AAAA')
            0x01, 0x00, 0x02,  # ADD R0, R2
            0x12, 0x00, 0x04,  # STORE R0, R4
            
            # Increment and check
            0x10, 0x04, 0x05, 0x04, 0x00, 0x00, 0x00,  # MOV R4, 4
            0x01, 0x02, 0x04,  # ADD R2, R4
            0x02, 0x03, 0x04,  # SUB R3, R4
            
            # Check if done
            0x22, 0x00,  # JNZ R0
            
            0x24,  # RET
        ]
        program.extend(buffer_fill)
        
        # Pad to offset 160 where the privileged function starts
        program.extend([0xF0] * (160 - len(program)))  # NOP padding
        
        # Privileged function - should only be callable by privileged code
        privileged_func = [
            # Direct privilege elevation
            0x32, 0x02,  # ELEVATE 2 (kernel level)
            
            # Do something privileged
            0x10, 0x00, 0x01, 0xBB, 0xBB, 0xBB, 0xBB,  # MOV R0, 0xBBBBBBBB (kernel data)
            0x10, 0x01, 0x02, 0x70, 0x00, 0x00, 0x00,  # MOV R1, 0x70 (privileged memory)
            0x12, 0x01, 0x00,  # STORE R1, R0 (write kernel data)
            
            # Return still elevated for demonstration
            0x24,  # RET
        ]
        program.extend(privileged_func)
        
        return program
    
    def get_attacks(self) -> List[Attack]:
        """Get available attacks for this scenario."""
        attacks = []
        
        # Buffer overflow to call the privileged function
        attacks.append(BufferOverflow(
            buffer_address=self.buffer_address,
            overflow_size=self.overflow_size,
            target_address=self.privilege_elevate_function,
        ))
        
        # Specific privilege escalation attack
        attacks.append(PrivilegeEscalation(
            buffer_address=self.buffer_address,
            overflow_size=self.overflow_size,
            target_privilege_level=2,  # Kernel level
            escalation_gadget_address=self.privilege_elevate_function,
        ))
        
        return attacks
    
    def evaluate_result(self, attack_result: AttackResult) -> Dict[str, Any]:
        """Evaluate the result of a privilege escalation attack."""
        evaluation = {
            "success": attack_result.success,
            "attack_type": attack_result.attack_type,
            "details": {},
        }
        
        # Check if privilege was escalated
        trace = attack_result.execution_trace
        initial_state = trace.get("initial_state", {})
        final_state = trace.get("final_state", {})
        
        initial_priv = initial_state.get("initial_privilege", "USER")
        final_priv = final_state.get("final_privilege", "USER")
        
        evaluation["details"]["initial_privilege"] = initial_priv
        evaluation["details"]["final_privilege"] = final_priv
        evaluation["details"]["privilege_escalated"] = initial_priv != final_priv
        
        # Look for privilege change events
        privilege_changes = []
        for event in attack_result.detection_events:
            if event.get("type") == "privilege-change":
                privilege_changes.append(event)
        
        evaluation["details"]["privilege_change_events"] = len(privilege_changes)
        
        return evaluation


def get_all_scenarios() -> List[SecurityScenario]:
    """Get all available security demonstration scenarios."""
    scenarios = [
        BufferOverflowScenario(),
        ReturnOrientedProgrammingScenario(),
        FormatStringScenario(),
        PrivilegeEscalationScenario(),
    ]
    return scenarios


def compare_protection_strategies(
    scenario: SecurityScenario,
    attack: Attack,
    protection_strategies: List[MemoryProtection],
) -> Dict[str, Any]:
    """
    Compare different protection strategies against the same attack scenario.
    
    This is useful for educational purposes to demonstrate how different
    protection mechanisms affect exploitability.
    """
    results = []
    
    for protection in protection_strategies:
        # Create a new VM with this protection strategy
        vm = VirtualMachine(protection=protection)
        
        # Set up the scenario
        scenario.setup(vm)
        
        # Execute the attack
        attack_result = attack.execute(vm)
        
        # Evaluate the result
        evaluation = scenario.evaluate_result(attack_result)
        
        # Record the result
        results.append({
            "protection": protection.get_protection_description(),
            "attack_successful": attack_result.success,
            "protection_events": len(attack_result.detection_events),
            "evaluation": evaluation,
        })
    
    return {
        "scenario": scenario.name,
        "attack_type": attack.attack_type,
        "results": results,
    }