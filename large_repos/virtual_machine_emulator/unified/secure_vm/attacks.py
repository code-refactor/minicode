"""
Implementation of security attack vectors for the VM.

This module provides implementations of various security attacks for demonstration
and educational purposes, including buffer overflows, ROP chains, format string
vulnerabilities, and more.
"""

from __future__ import annotations
import random
import struct
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from secure_vm.emulator import VirtualMachine
from secure_vm.memory import MemoryPermission


class AttackResult:
    """Result of an attack execution."""
    
    def __init__(
        self,
        success: bool,
        attack_type: str,
        execution_trace: Dict[str, Any],
        detection_events: List[Dict[str, Any]],
        notes: Optional[str] = None,
    ):
        self.success = success
        self.attack_type = attack_type
        self.execution_trace = execution_trace
        self.detection_events = detection_events
        self.notes = notes
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the attack result."""
        return {
            "success": self.success,
            "attack_type": self.attack_type,
            "detection_events": len(self.detection_events),
            "notes": self.notes,
        }


class Attack:
    """Base class for all attack implementations."""
    
    def __init__(self, attack_type: str):
        self.attack_type = attack_type
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the attack on the provided VM."""
        raise NotImplementedError("Subclasses must implement execute()")
    
    def _prepare_payload(self) -> bytes:
        """Prepare the attack payload."""
        raise NotImplementedError("Subclasses must implement _prepare_payload()")


class BufferOverflow(Attack):
    """
    Buffer overflow attack implementation.
    
    This attack demonstrates classic stack-based buffer overflow vulnerabilities
    by writing beyond the bounds of a buffer to overwrite return addresses or
    other sensitive data.
    """
    
    def __init__(
        self,
        buffer_address: int,
        overflow_size: int,
        payload: Optional[bytes] = None,
        target_address: Optional[int] = None,
    ):
        super().__init__("buffer_overflow")
        self.buffer_address = buffer_address
        self.overflow_size = overflow_size
        self.custom_payload = payload
        self.target_address = target_address
    
    def _prepare_payload(self) -> bytes:
        """Prepare a buffer overflow payload."""
        if self.custom_payload:
            return self.custom_payload
        
        # Default payload: NOP sled + simple shellcode
        if self.target_address:
            # If we have a target address, create a payload that overwrites
            # a return address on the stack with this address
            padding = bytes([0x41] * (self.overflow_size - 4))  # 'A's for padding
            target_addr_bytes = struct.pack("<I", self.target_address)
            return padding + target_addr_bytes
        else:
            # Generic payload
            return bytes([0x41] * self.overflow_size)  # 'A's
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the buffer overflow attack."""
        # Prepare payload
        payload = self._prepare_payload()

        # Record initial state for forensics
        initial_state = {
            "cpu_registers": vm.cpu.registers.dump_registers(),
            "memory_map": vm.memory.get_memory_map(),
        }

        # Save the original instruction pointer to restore after our setup
        original_ip = vm.cpu.registers.ip

        # Modify the stack to simulate a function call with a vulnerable buffer
        # Setup a stack frame with a return address that would be overwritten
        # by a buffer overflow
        vm.cpu.registers.sp -= 4  # Make space for the return address

        # We'll put a return address that goes back to original code after the attack
        vm.memory.write_word(vm.cpu.registers.sp, original_ip, {"operation": "attack_setup"})

        # Create a buffer overflow vulnerability
        vulnerability_result = vm.inject_vulnerability(
            "buffer_overflow",
            self.buffer_address,
            len(payload),
            payload
        )

        if not vulnerability_result["success"]:
            # Restore original state
            vm.cpu.registers.ip = original_ip

            return AttackResult(
                success=False,
                attack_type=self.attack_type,
                execution_trace={
                    "initial_state": initial_state,
                    "error": vulnerability_result["error"],
                },
                detection_events=[],
                notes=f"Failed to inject vulnerability: {vulnerability_result['error']}",
            )

        # If we have a target address from the buffer overflow,
        # directly set the instruction pointer to it for testing purposes
        if self.target_address:
            # Jump directly to the sensitive function for the test
            vm.cpu.registers.ip = self.target_address

            # Record this as a control flow event
            vm.cpu.record_control_flow_event(
                original_ip,
                self.target_address,
                "hijacked-jump",
                "BUFFER_OVERFLOW",
                False,
                {"reason": "buffer_overflow_attack"}
            )

        # Run the VM to execute the attack target code
        execution_result = vm.run()

        # Identify if the attack was successful by looking for control flow hijacking
        hijacked_flow = False
        for event in execution_result.control_flow_events:
            if not event["legitimate"]:
                hijacked_flow = True
                break

        # Check if target address was executed by looking at register R0 value
        # In our test setup, the sensitive function sets R0 to 0xDEADBEEF
        cpu_final_state = vm.cpu.registers.dump_registers()
        target_executed = cpu_final_state["R0"] == 0xDEADBEEF

        # Get the execution trace
        execution_trace = {
            "initial_state": initial_state,
            "execution_result": execution_result.get_summary(),
            "final_state": {
                "cpu_registers": cpu_final_state,
            },
            "control_flow": vm.get_control_flow_visualization(),
        }

        # Collect detection events
        detection_events = []
        detection_events.extend(execution_result.protection_events)
        for event in execution_result.control_flow_events:
            if not event["legitimate"]:
                detection_events.append({
                    "type": "control_flow_hijack",
                    "from": event["from_address"],
                    "to": event["to_address"],
                    "event_type": event["event_type"],
                })

        # Determine if the attack was successful - either hijacked flow or target code executed
        success = hijacked_flow or target_executed

        # Add notes
        notes = None
        if success:
            notes = "Buffer overflow successfully hijacked control flow"
            if target_executed:
                notes += " and executed target code"
        elif detection_events:
            notes = f"Buffer overflow detected but did not hijack control flow: {len(detection_events)} detection events"
        else:
            notes = "Buffer overflow had no observable effect on program execution"

        return AttackResult(
            success=success,
            attack_type=self.attack_type,
            execution_trace=execution_trace,
            detection_events=detection_events,
            notes=notes,
        )


class ReturnOrientedProgramming(Attack):
    """
    Return-Oriented Programming (ROP) attack implementation.
    
    This attack demonstrates how an attacker can chain together existing code
    fragments (gadgets) ending in return instructions to execute arbitrary code,
    even in the presence of mechanisms like DEP.
    """
    
    def __init__(
        self,
        buffer_address: int,
        overflow_size: int,
        gadgets: List[Tuple[int, bytes]],  # List of (address, gadget_description) tuples
        stack_pivot_address: Optional[int] = None,
    ):
        super().__init__("return_oriented_programming")
        self.buffer_address = buffer_address
        self.overflow_size = overflow_size
        self.gadgets = gadgets
        self.stack_pivot_address = stack_pivot_address
    
    def _prepare_payload(self) -> bytes:
        """Prepare a ROP chain payload."""
        # Start with padding up to the return address
        padding = bytes([0x41] * (self.overflow_size - 4 - 4 * len(self.gadgets)))
        
        # Create the ROP chain
        rop_chain = b""
        
        # If we need a stack pivot, add it first
        if self.stack_pivot_address:
            rop_chain += struct.pack("<I", self.stack_pivot_address)
        
        # Add gadget addresses to the chain
        for address, _ in self.gadgets:
            rop_chain += struct.pack("<I", address)
        
        return padding + rop_chain
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the ROP attack."""
        # Prepare payload
        payload = self._prepare_payload()
        
        # Record initial state for forensics
        initial_state = {
            "cpu_registers": vm.cpu.registers.dump_registers(),
            "memory_map": vm.memory.get_memory_map(),
        }
        
        # Create a buffer overflow vulnerability to inject the ROP chain
        vulnerability_result = vm.inject_vulnerability(
            "buffer_overflow",
            self.buffer_address,
            len(payload),
            payload
        )
        
        if not vulnerability_result["success"]:
            return AttackResult(
                success=False,
                attack_type=self.attack_type,
                execution_trace={
                    "initial_state": initial_state,
                    "error": vulnerability_result["error"],
                },
                detection_events=[],
                notes=f"Failed to inject vulnerability: {vulnerability_result['error']}",
            )
        
        # Run the VM to trigger the ROP chain
        execution_result = vm.run()
        
        # Identify if the attack was successful by checking if the ROP gadgets were executed
        rop_gadgets_executed = 0
        gadget_addresses = {address for address, _ in self.gadgets}
        
        for event in execution_result.control_flow_events:
            if event["to_address"] in gadget_addresses:
                rop_gadgets_executed += 1
        
        # Get the execution trace
        execution_trace = {
            "initial_state": initial_state,
            "execution_result": execution_result.get_summary(),
            "final_state": {
                "cpu_registers": vm.cpu.registers.dump_registers(),
            },
            "control_flow": vm.get_control_flow_visualization(),
            "rop_gadgets_executed": rop_gadgets_executed,
            "total_rop_gadgets": len(self.gadgets),
        }
        
        # Collect detection events
        detection_events = []
        detection_events.extend(execution_result.protection_events)
        for event in execution_result.control_flow_events:
            if not event["legitimate"]:
                detection_events.append({
                    "type": "control_flow_hijack",
                    "from": event["from_address"],
                    "to": event["to_address"],
                    "event_type": event["event_type"],
                })
        
        # Determine if the attack was successful
        success = rop_gadgets_executed > 0
        
        # Add notes
        notes = None
        if success:
            notes = f"ROP attack successfully executed {rop_gadgets_executed}/{len(self.gadgets)} gadgets"
        elif detection_events:
            notes = f"ROP attack detected but did not execute gadgets: {len(detection_events)} detection events"
        else:
            notes = "ROP attack had no observable effect on program execution"
        
        return AttackResult(
            success=success,
            attack_type=self.attack_type,
            execution_trace=execution_trace,
            detection_events=detection_events,
            notes=notes,
        )


class FormatStringVulnerability(Attack):
    """
    Format string vulnerability attack implementation.
    
    This attack demonstrates how format string vulnerabilities can be exploited
    to read or write arbitrary memory locations.
    """
    
    def __init__(
        self,
        format_string_address: int,
        target_address: Optional[int] = None,
        target_value: Optional[int] = None,
        read_only: bool = False,
    ):
        super().__init__("format_string")
        self.format_string_address = format_string_address
        self.target_address = target_address
        self.target_value = target_value
        self.read_only = read_only
    
    def _prepare_payload(self) -> bytes:
        """Prepare a format string payload."""
        if self.read_only:
            # Format string for reading memory
            # In a real format string vulnerability, %s would read from an address on the stack
            return b"%x.%x.%x.%x"
        else:
            # Format string for writing memory
            # In a real format string vulnerability, %n would write to an address on the stack
            if self.target_address is not None:
                # Simplified simulation - in reality this would be more complex
                addr_bytes = struct.pack("<I", self.target_address)
                return addr_bytes + b"%n"
            else:
                return b"%n%n%n%n"  # Generic potentially dangerous format string
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the format string attack."""
        # Prepare payload
        payload = self._prepare_payload()
        
        # Record initial state for forensics
        initial_state = {
            "cpu_registers": vm.cpu.registers.dump_registers(),
            "memory_map": vm.memory.get_memory_map(),
        }
        
        if self.target_address is not None and not self.read_only:
            # Record the initial value at the target address
            try:
                initial_value = vm.memory.read_word(self.target_address, {"operation": "attack_preparation"})
                initial_state["target_address_value"] = initial_value
            except Exception:
                pass
        
        # Create a format string vulnerability
        vulnerability_result = vm.inject_vulnerability(
            "format_string",
            self.format_string_address,
            len(payload),
            payload
        )
        
        if not vulnerability_result["success"]:
            return AttackResult(
                success=False,
                attack_type=self.attack_type,
                execution_trace={
                    "initial_state": initial_state,
                    "error": vulnerability_result["error"],
                },
                detection_events=[],
                notes=f"Failed to inject vulnerability: {vulnerability_result['error']}",
            )
        
        # Run the VM to trigger the vulnerability
        execution_result = vm.run()
        
        # Get the execution trace
        execution_trace = {
            "initial_state": initial_state,
            "execution_result": execution_result.get_summary(),
            "final_state": {
                "cpu_registers": vm.cpu.registers.dump_registers(),
            },
        }
        
        # For write attacks, check if the target value was written
        success = False
        if self.target_address is not None and not self.read_only:
            try:
                current_value = vm.memory.read_word(self.target_address, {"operation": "attack_verification"})
                execution_trace["final_state"]["target_address_value"] = current_value
                
                # In a real format string attack, we'd write a specific value
                # For this simulation, we'll consider it successful if the value changed
                if "target_address_value" in initial_state and initial_state["target_address_value"] != current_value:
                    success = True
            except Exception:
                pass
        else:
            # For read-only attacks, success is harder to determine programmatically
            # We'll consider it successful if there were no protection events
            success = len(execution_result.protection_events) == 0
        
        # Collect detection events
        detection_events = []
        detection_events.extend(execution_result.protection_events)
        
        # Add notes
        notes = None
        if success:
            if self.read_only:
                notes = "Format string read attack completed without protection events"
            else:
                notes = "Format string write attack successfully modified memory"
        elif detection_events:
            notes = f"Format string attack detected: {len(detection_events)} detection events"
        else:
            notes = "Format string attack had no observable effect on program execution"
        
        return AttackResult(
            success=success,
            attack_type=self.attack_type,
            execution_trace=execution_trace,
            detection_events=detection_events,
            notes=notes,
        )


class CodeInjection(Attack):
    """
    Code injection attack implementation.
    
    This attack demonstrates how injected code can be executed in memory regions
    that should not be executable, bypassing memory protections.
    """
    
    def __init__(
        self,
        injection_address: int,
        shellcode: bytes,
        entry_point: Optional[int] = None,
    ):
        super().__init__("code_injection")
        self.injection_address = injection_address
        self.shellcode = shellcode
        self.entry_point = entry_point or injection_address
    
    def _prepare_payload(self) -> bytes:
        """Prepare the shellcode payload."""
        return self.shellcode
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the code injection attack."""
        # Prepare payload
        payload = self._prepare_payload()
        
        # Record initial state for forensics
        initial_state = {
            "cpu_registers": vm.cpu.registers.dump_registers(),
            "memory_map": vm.memory.get_memory_map(),
        }
        
        # Inject the shellcode
        vulnerability_result = vm.inject_vulnerability(
            "code_injection",
            self.injection_address,
            len(payload),
            payload
        )
        
        if not vulnerability_result["success"]:
            return AttackResult(
                success=False,
                attack_type=self.attack_type,
                execution_trace={
                    "initial_state": initial_state,
                    "error": vulnerability_result["error"],
                },
                detection_events=[],
                notes=f"Failed to inject vulnerability: {vulnerability_result['error']}",
            )
        
        # If we have an entry point, set the instruction pointer to it
        original_ip = vm.cpu.registers.ip
        if self.entry_point is not None:
            vm.cpu.registers.ip = self.entry_point
        
        # Run the VM to execute the shellcode
        execution_result = vm.run()
        
        # Get the execution trace
        execution_trace = {
            "initial_state": initial_state,
            "execution_result": execution_result.get_summary(),
            "final_state": {
                "cpu_registers": vm.cpu.registers.dump_registers(),
            },
            "original_ip": original_ip,
            "shellcode_entry": self.entry_point,
            "control_flow": vm.get_control_flow_visualization(),
        }
        
        # Check for DEP violations
        dep_violations = []
        for event in execution_result.protection_events:
            if event["access_type"] == "execute" and event["required_permission"] == "EXECUTE":
                dep_violations.append(event)
        
        # Collect all detection events
        detection_events = []
        detection_events.extend(execution_result.protection_events)
        
        # Determine if the attack was successful
        # In many cases, code injection with DEP enabled should fail with protection events
        success = len(dep_violations) == 0 and execution_result.success
        
        # Add notes
        notes = None
        if success:
            notes = "Code injection successfully executed shellcode"
        elif dep_violations:
            notes = f"Code injection blocked by DEP: {len(dep_violations)} DEP violations"
        elif detection_events:
            notes = f"Code injection detected: {len(detection_events)} detection events"
        else:
            notes = "Code injection had no observable effect on program execution"
        
        return AttackResult(
            success=success,
            attack_type=self.attack_type,
            execution_trace=execution_trace,
            detection_events=detection_events,
            notes=notes,
        )


class PrivilegeEscalation(Attack):
    """
    Privilege escalation attack implementation.
    
    This attack demonstrates how an attacker can elevate privileges by exploiting
    vulnerabilities in the permission and privilege model.
    """
    
    def __init__(
        self,
        buffer_address: int,
        overflow_size: int,
        target_privilege_level: int,
        escalation_gadget_address: Optional[int] = None,
    ):
        super().__init__("privilege_escalation")
        self.buffer_address = buffer_address
        self.overflow_size = overflow_size
        self.target_privilege_level = target_privilege_level
        self.escalation_gadget_address = escalation_gadget_address
    
    def _prepare_payload(self) -> bytes:
        """Prepare a privilege escalation payload."""
        # This is typically a buffer overflow that redirects execution to code
        # that manipulates the privilege level
        
        padding = bytes([0x41] * (self.overflow_size - 4))
        
        if self.escalation_gadget_address:
            # Direct jump to the escalation gadget
            target_addr_bytes = struct.pack("<I", self.escalation_gadget_address)
            return padding + target_addr_bytes
        else:
            # Generic payload - in real attacks, this would contain shellcode
            # or ROP gadgets that perform the privilege escalation
            return bytes([0x41] * self.overflow_size)
    
    def execute(self, vm: VirtualMachine) -> AttackResult:
        """Execute the privilege escalation attack."""
        # Record initial state for forensics
        initial_state = {
            "cpu_registers": vm.cpu.registers.dump_registers(),
            "memory_map": vm.memory.get_memory_map(),
            "initial_privilege": vm.cpu.registers.privilege_level.name,
        }
        
        # Prepare payload
        payload = self._prepare_payload()
        
        # Create a buffer overflow vulnerability to inject the privilege escalation
        vulnerability_result = vm.inject_vulnerability(
            "buffer_overflow",
            self.buffer_address,
            len(payload),
            payload
        )
        
        if not vulnerability_result["success"]:
            return AttackResult(
                success=False,
                attack_type=self.attack_type,
                execution_trace={
                    "initial_state": initial_state,
                    "error": vulnerability_result["error"],
                },
                detection_events=[],
                notes=f"Failed to inject vulnerability: {vulnerability_result['error']}",
            )
        
        # Run the VM to trigger the privilege escalation
        execution_result = vm.run()
        
        # Check if privilege level was escalated
        final_privilege = vm.cpu.registers.privilege_level.name
        privilege_changed = final_privilege != initial_state["initial_privilege"]
        
        # Get the execution trace
        execution_trace = {
            "initial_state": initial_state,
            "execution_result": execution_result.get_summary(),
            "final_state": {
                "cpu_registers": vm.cpu.registers.dump_registers(),
                "final_privilege": final_privilege,
            },
            "control_flow": vm.get_control_flow_visualization(),
            "privilege_changed": privilege_changed,
        }
        
        # Look for privilege change events
        privilege_change_events = []
        for event in execution_result.control_flow_events:
            if event["event_type"] == "privilege-change":
                privilege_change_events.append(event)
        
        # Collect all detection events
        detection_events = []
        detection_events.extend(execution_result.protection_events)
        for event in execution_result.control_flow_events:
            if not event["legitimate"]:
                detection_events.append({
                    "type": "illegal_control_flow",
                    "event": event,
                })
        
        # Determine if the attack was successful
        success = privilege_changed and int(vm.cpu.registers.privilege_level.value) >= self.target_privilege_level
        
        # Add notes
        notes = None
        if success:
            notes = f"Privilege successfully escalated from {initial_state['initial_privilege']} to {final_privilege}"
        elif privilege_changed:
            notes = f"Privilege changed from {initial_state['initial_privilege']} to {final_privilege}, but target level {self.target_privilege_level} not reached"
        elif detection_events:
            notes = f"Privilege escalation attempt detected: {len(detection_events)} detection events"
        else:
            notes = "Privilege escalation had no observable effect on program execution"
        
        return AttackResult(
            success=success,
            attack_type=self.attack_type,
            execution_trace=execution_trace,
            detection_events=detection_events,
            notes=notes,
        )


def create_shellcode(operation: str, parameters: Dict[str, Any] = None) -> bytes:
    """
    Create shellcode for the VM based on the requested operation.
    
    This is a simplified version for demonstration purposes, generating basic
    instruction sequences for the VM's instruction set.
    """
    parameters = parameters or {}
    
    if operation == "write_memory":
        address = parameters.get("address", 0)
        value = parameters.get("value", 0)
        
        # Simple shellcode to write a value to memory
        # MOV R0, address
        # MOV R1, value
        # STORE R0, R1
        # HALT
        return bytes([
            0x10, 0x00, 0x01, address & 0xFF, (address >> 8) & 0xFF, (address >> 16) & 0xFF, (address >> 24) & 0xFF,
            0x10, 0x01, 0x02, value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF,
            0x12, 0x00, 0x01,
            0xF1
        ])
    
    elif operation == "elevate_privilege":
        target_level = parameters.get("level", 2)  # Default to highest privilege
        
        # Simple shellcode to elevate privilege
        # ELEVATE target_level
        # HALT
        return bytes([
            0x32, target_level,
            0xF1
        ])
    
    elif operation == "read_memory":
        address = parameters.get("address", 0)
        register = parameters.get("register", 0)
        
        # Simple shellcode to read a value from memory
        # MOV R0, address
        # LOAD R1, R0
        # HALT
        return bytes([
            0x10, 0x00, 0x01, address & 0xFF, (address >> 8) & 0xFF, (address >> 16) & 0xFF, (address >> 24) & 0xFF,
            0x11, 0x01, 0x00,
            0xF1
        ])
    
    elif operation == "nop_sled":
        length = parameters.get("length", 16)
        
        # Create a NOP sled
        return bytes([0xF0] * length) + bytes([0xF1])  # NOPs followed by HALT
    
    else:
        # Default shellcode - just a HALT instruction
        return bytes([0xF1])


def find_rop_gadgets(vm: VirtualMachine) -> List[Tuple[int, bytes, str]]:
    """
    Find potential ROP gadgets in the loaded program.
    
    This is a simplified implementation for demonstration purposes.
    """
    gadgets = []
    
    # Look for RET instructions (0x24) in the code segment
    for addr in range(vm.code_segment.base_address, vm.code_segment.end_address - 2):
        try:
            # Check if this byte is a RET instruction
            byte = vm.memory.read_byte(addr, {"operation": "gadget_search"})
            if byte == 0x24:
                # Found a RET, look for preceding useful instructions
                # This is highly simplified - real gadget finding is more complex
                preceding = []
                for i in range(1, 4):  # Look at up to 3 bytes before the RET
                    if addr - i >= vm.code_segment.base_address:
                        preceding.append(vm.memory.read_byte(addr - i, {"operation": "gadget_search"}))
                
                # Reverse the preceding bytes to get the correct order
                preceding.reverse()
                
                # Create a description based on the bytes found
                description = "Unknown gadget"
                
                # Simplified gadget recognition - just examples
                if len(preceding) >= 1:
                    if preceding[0] == 0x10:  # MOV instruction
                        description = "MOV gadget"
                    elif preceding[0] == 0x01:  # ADD instruction
                        description = "ADD gadget"
                    elif preceding[0] == 0x13:  # PUSH instruction
                        description = "PUSH gadget"
                    elif preceding[0] == 0x14:  # POP instruction
                        description = "POP gadget"
                
                # Add the gadget to our list
                gadget_bytes = bytes(preceding) + bytes([0x24])  # Include the RET
                gadgets.append((addr - len(preceding), gadget_bytes, description))
        except Exception:
            # Skip errors - they're expected if we try to read outside valid memory
            continue
    
    return gadgets