"""
Virtual Machine emulator for security research.

This module implements the main virtual machine emulator that integrates
the memory, CPU, and security components.
"""

from __future__ import annotations
import random
import time
from typing import Dict, List, Optional, Set, Tuple, Union, Any, BinaryIO

# Import common library components
from common.core.vm_base import VMBase
from common.core.program import Program as CommonProgram
from common.core.instruction import Instruction as CommonInstruction
from common.core.state import VMState, ExecutionStats
from common.execution.context import ExecutionContext
from common.utils.exceptions import VMException, HaltException

# Import secure VM specific components
from secure_vm.memory import (
    Memory, MemorySegment, MemoryPermission, MemoryProtectionLevel, MemoryProtection
)
from secure_vm.cpu import CPU, PrivilegeLevel, CPUException


class ExecutionResult:
    """Result of executing a program in the VM."""
    
    def __init__(
        self,
        success: bool,
        cycles: int,
        execution_time: float,
        cpu_state: Dict[str, Any],
        control_flow_events: List[Dict[str, Any]],
        protection_events: List[Dict[str, Any]],
    ):
        self.success = success
        self.cycles = cycles
        self.execution_time = execution_time
        self.cpu_state = cpu_state
        self.control_flow_events = control_flow_events
        self.protection_events = protection_events
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution result."""
        return {
            "success": self.success,
            "cycles": self.cycles,
            "execution_time": self.execution_time,
            "control_flow_events": len(self.control_flow_events),
            "protection_events": len(self.protection_events),
            "instructions_per_second": self.cycles / max(self.execution_time, 0.001),
        }


class ForensicLog:
    """Forensic logging system for the VM."""
    
    def __init__(self, enabled: bool = True, detailed: bool = False):
        self.enabled = enabled
        self.detailed = detailed
        self.logs: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event if logging is enabled."""
        if not self.enabled:
            return
        
        entry = {
            "timestamp": time.time() - self.start_time,
            "event_type": event_type,
            "data": data,
        }
        self.logs.append(entry)
    
    def log_memory_access(
        self,
        address: int,
        access_type: str,
        size: int,
        value: Optional[int] = None,
        context: Dict[str, Any] = None,
    ) -> None:
        """Log a memory access event."""
        if not self.enabled or not self.detailed:
            return
        
        data = {
            "address": address,
            "access_type": access_type,
            "size": size,
        }
        if value is not None:
            data["value"] = value
        if context:
            data["context"] = context
        
        self.log_event("memory_access", data)
    
    def log_control_flow(self, event: Dict[str, Any]) -> None:
        """Log a control flow event."""
        if not self.enabled:
            return
        
        self.log_event("control_flow", event)
    
    def log_protection_violation(self, event: Dict[str, Any]) -> None:
        """Log a protection violation event."""
        if not self.enabled:
            return
        
        self.log_event("protection_violation", event)
    
    def log_system_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log a system-level event."""
        if not self.enabled:
            return
        
        data = {"system_event": event_type, **details}
        self.log_event("system", data)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.logs
    
    def export_logs(self, format_type: str = "dict") -> Union[List[Dict[str, Any]], str]:
        """Export logs in the specified format."""
        if format_type == "dict":
            return self.logs
        elif format_type == "json":
            import json
            return json.dumps(self.logs, indent=2)
        elif format_type == "text":
            text_logs = []
            for log in self.logs:
                timestamp = log["timestamp"]
                event_type = log["event_type"]
                data_str = ", ".join(f"{k}={v}" for k, v in log["data"].items())
                text_logs.append(f"[{timestamp:.6f}] {event_type}: {data_str}")
            return "\n".join(text_logs)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


class VirtualMachine(VMBase):
    """Virtual machine emulator for security research."""
    
    def __init__(
        self,
        memory_size: int = 65536,
        protection: Optional[MemoryProtection] = None,
        enable_forensics: bool = True,
        detailed_logging: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Initialize execution state
        self.execution_stats = ExecutionStats()
        self.state = VMState.IDLE
        # Default memory protection if none provided
        if protection is None:
            protection = MemoryProtection(
                level=MemoryProtectionLevel.STANDARD,
                dep_enabled=True,
                aslr_enabled=False,
                stack_canaries=False,
                shadow_memory=False,
            )
        
        # Initialize memory with protection settings
        self.memory = Memory(
            size=memory_size,
            protection_level=protection.level,
            enable_dep=protection.dep_enabled,
            enable_aslr=protection.aslr_enabled,
            enable_logging=detailed_logging,
        )
        
        # Initialize CPU
        self.cpu = CPU(self.memory)
        
        # Initialize forensic logging
        self.forensic_log = ForensicLog(
            enabled=enable_forensics,
            detailed=detailed_logging,
        )
        
        # Track loaded programs (use common Program)
        self.current_program: Optional[CommonProgram] = None
        self.program_loaded = False
        self.program_name = ""
        self.program_entry_point = 0
        
        # Standard memory layout with configurable size
        self._setup_memory_layout(memory_size)
        
        # Apply additional memory protections
        self.protection = protection
        self._apply_memory_protections()
    
    def _setup_memory_layout(self, memory_size: int) -> None:
        """Set up the standard memory layout for the VM."""
        # Calculate segment sizes
        code_size = memory_size // 4
        data_size = memory_size // 4
        heap_size = memory_size // 4
        stack_size = memory_size - code_size - data_size - heap_size
        
        # Create memory segments
        self.code_segment = self.memory.add_segment(
            MemorySegment(
                base_address=0x10000,
                size=code_size,
                permission=MemoryPermission.READ_EXECUTE,
                name="code"
            )
        )
        
        self.data_segment = self.memory.add_segment(
            MemorySegment(
                base_address=0x20000,
                size=data_size,
                permission=MemoryPermission.READ_WRITE,
                name="data"
            )
        )
        
        self.heap_segment = self.memory.add_segment(
            MemorySegment(
                base_address=0x30000,
                size=heap_size,
                permission=MemoryPermission.READ_WRITE,
                name="heap"
            )
        )
        
        self.stack_segment = self.memory.add_segment(
            MemorySegment(
                base_address=0x70000,
                size=stack_size,
                permission=MemoryPermission.READ_WRITE,
                name="stack"
            )
        )
        
        # Initialize stack pointer to top of stack
        self.cpu.registers.sp = self.stack_segment.base_address + self.stack_segment.size - 4
        self.cpu.registers.bp = self.cpu.registers.sp
    
    def _apply_memory_protections(self) -> None:
        """Apply configured memory protections."""
        self.protection.apply_to_memory(self.memory)
        
        # Apply segment-specific protections
        self.protection.apply_to_segment(self.stack_segment, self.memory)
        
        # Log the memory protection configuration
        self.forensic_log.log_system_event(
            "memory_protection_config",
            self.protection.get_protection_description()
        )
        
        # Log the memory map
        self.forensic_log.log_system_event(
            "memory_map",
            {"segments": self.memory.get_memory_map()}
        )
    
    def load_program_bytes(self, program: List[int], entry_point: Optional[int] = None) -> None:
        """Load a program (instruction bytes) into the code segment."""
        if len(program) > self.code_segment.size:
            raise ValueError(f"Program size {len(program)} exceeds code segment size {self.code_segment.size}")

        # Temporarily modify code segment permissions to allow writing
        original_permission = self.code_segment.permission
        self.code_segment.permission = MemoryPermission.READ_WRITE_EXECUTE

        # Write program bytes to code segment
        for i, byte in enumerate(program):
            self.memory.write_byte(
                self.code_segment.base_address + i,
                byte,
                {"operation": "program_load"}
            )

        # Restore original permissions
        self.code_segment.permission = original_permission

        # Set default entry point
        if entry_point is None:
            entry_point = self.code_segment.base_address

        self.program_entry_point = entry_point
        self.program_loaded = True

        # Set instruction pointer to entry point
        self.cpu.registers.ip = entry_point

        # Log program load
        self.forensic_log.log_system_event(
            "program_load",
            {
                "size": len(program),
                "entry_point": entry_point,
            }
        )
    
    def load_program(self, program) -> None:
        """Load a program (either CommonProgram or list of bytes)."""
        if isinstance(program, list):
            # Legacy: list of bytes - use None to get default entry point
            self.load_program_bytes(program, None)
        elif hasattr(program, 'instructions'):
            # CommonProgram object
            self.current_program = program
            self.program_entry_point = program.entry_point
            self.program_loaded = True
            
            # Convert program instructions to bytes for legacy loading
            program_bytes = []
            for instruction in program.instructions:
                # Simple encoding - this would need to be more sophisticated in practice
                encoded = instruction.encode() if hasattr(instruction, 'encode') else 0
                program_bytes.extend([
                    encoded & 0xFF,
                    (encoded >> 8) & 0xFF,
                    (encoded >> 16) & 0xFF,
                    (encoded >> 24) & 0xFF
                ])
            
            self.load_program_bytes(program_bytes, program.entry_point)
            
            # Load data segment if present
            if hasattr(program, 'data'):
                for address, value in program.data.items():
                    self.memory.write_word(address, value)
        else:
            # Unknown type
            raise ValueError(f"Unknown program type: {type(program)}")
        
        # Set program name if available
        if not isinstance(program, list):
            self.program_name = getattr(program, 'name', 'unknown')
        else:
            self.program_name = 'legacy_program'
    
    def load_program_from_file(self, filename: str, entry_point: Optional[int] = None) -> None:
        """Load a program from a binary file."""
        with open(filename, "rb") as f:
            program = list(f.read())
        
        self.program_name = filename
        self.load_program_bytes(program, entry_point)
    
    def load_data(self, data: List[int], data_address: Optional[int] = None) -> int:
        """Load data into the data segment and return the address where it was loaded."""
        if data_address is None:
            data_address = self.data_segment.base_address
        
        if not self.data_segment.contains_address(data_address) or not self.data_segment.contains_address(data_address + len(data) - 1):
            raise ValueError(f"Data doesn't fit in data segment at address 0x{data_address:08x}")
        
        # Write data bytes
        for i, byte in enumerate(data):
            self.memory.write_byte(
                data_address + i,
                byte,
                {"operation": "data_load"}
            )
        
        # Log data load
        self.forensic_log.log_system_event(
            "data_load",
            {
                "address": data_address,
                "size": len(data),
            }
        )
        
        return data_address
    
    def run(self, max_instructions: int = 10000) -> ExecutionResult:
        """Run the virtual machine."""
        return self.execute(max_instructions)
    
    def execute(self, max_instructions: int = 10000) -> ExecutionResult:
        """Run the loaded program for up to max_instructions."""
        if not self.program_loaded:
            raise VMException("No program loaded")
        
        self.state = VMState.RUNNING
        
        # Log execution start
        self.forensic_log.log_system_event(
            "execution_start",
            {
                "entry_point": self.cpu.registers.ip,
                "max_instructions": max_instructions,
            }
        )
        
        # Run the CPU
        try:
            instructions_executed = self.cpu.run(max_instructions)
            success = True
            self.state = VMState.FINISHED
        except HaltException:
            instructions_executed = self.cpu.cycle_count
            success = True
            self.state = VMState.FINISHED
        except Exception as e:
            instructions_executed = self.cpu.cycle_count
            success = False
            self.state = VMState.ERROR
            # Log the exception
            self.forensic_log.log_system_event(
                "execution_exception",
                {
                    "exception_type": type(e).__name__,
                    "message": str(e),
                    "instruction_pointer": self.cpu.registers.ip,
                }
            )
        
        # Update execution statistics
        self.execution_stats.cycles += self.cpu.cycle_count
        self.execution_stats.instructions_executed += instructions_executed
        
        # Log execution end
        self.forensic_log.log_system_event(
            "execution_end",
            {
                "cycles": self.cpu.cycle_count,
                "success": success,
                "halted": self.cpu.halted,
            }
        )
        
        # Process control flow records for forensic log
        control_flow_events = []
        for record in self.cpu.control_flow_records:
            event = {
                "from_address": record.from_address,
                "to_address": record.to_address,
                "event_type": record.event_type,
                "instruction": record.instruction,
                "legitimate": record.legitimate,
                "timestamp": record.timestamp,
            }
            if record.context:
                event["context"] = record.context
            
            control_flow_events.append(event)
            self.forensic_log.log_control_flow(event)
        
        # Process protection events
        protection_events = []
        for event in self.memory.protection_events:
            protection_event = {
                "address": event.address,
                "access_type": event.access_type,
                "current_permission": event.current_permission.name,
                "required_permission": event.required_permission.name,
                "instruction_pointer": event.instruction_pointer,
            }
            if event.context:
                protection_event["context"] = event.context
            
            protection_events.append(protection_event)
            self.forensic_log.log_protection_violation(protection_event)
        
        # Create execution result
        result = ExecutionResult(
            success=success,
            cycles=self.cpu.cycle_count,
            execution_time=self.cpu.execution_time,
            cpu_state=self.cpu.registers.dump_registers(),
            control_flow_events=control_flow_events,
            protection_events=protection_events,
        )
        
        return result
    
    def get_memory_snapshot(self, segment_name: str = None) -> Dict[str, Any]:
        """Get a snapshot of memory contents, optionally filtered by segment name."""
        segments = []
        
        for segment in self.memory.segments:
            if segment_name is None or segment.name == segment_name:
                # Create a snapshot of this segment
                snapshot = {
                    "name": segment.name,
                    "base_address": segment.base_address,
                    "size": segment.size,
                    "permission": segment.permission.name,
                    "data": bytes(segment.data),  # Convert to bytes for easier handling
                }
                segments.append(snapshot)
        
        return {"segments": segments}
    
    def inject_vulnerability(
        self,
        vuln_type: str,
        address: int,
        size: int,
        payload: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Inject a vulnerability into memory for demonstration purposes.
        
        This is useful for creating controlled security vulnerabilities
        that can be exploited through different attack vectors.
        """
        self.forensic_log.log_system_event(
            "vulnerability_injection",
            {
                "type": vuln_type,
                "address": address,
                "size": size,
                "has_payload": payload is not None,
            }
        )
        
        result = {"success": False, "error": None}
        
        try:
            if vuln_type == "buffer_overflow":
                # Create a buffer overflow condition
                segment = self.memory.find_segment(address)
                if segment is None:
                    result["error"] = f"Address 0x{address:08x} not in any memory segment"
                    return result
                
                # Write beyond intended buffer size
                data = payload or bytes([0x41] * size)  # Default to 'A's if no payload
                self.memory.write_bytes(address, data, {"vulnerability": "buffer_overflow"})
                result["success"] = True
                
            elif vuln_type == "use_after_free":
                # Simulate a use-after-free by marking memory as "freed" but still accessible
                segment = self.memory.find_segment(address)
                if segment is None:
                    result["error"] = f"Address 0x{address:08x} not in any memory segment"
                    return result
                
                # In a real scenario, we'd actually free this memory, but for demonstration,
                # we'll just modify it to show it was "freed" but still accessible
                data = payload or bytes([0xDD] * size)  # Default to a "freed memory" pattern
                self.memory.write_bytes(address, data, {"vulnerability": "use_after_free"})
                result["success"] = True
                
            elif vuln_type == "format_string":
                # Simulate a format string vulnerability
                segment = self.memory.find_segment(address)
                if segment is None:
                    result["error"] = f"Address 0x{address:08x} not in any memory segment"
                    return result
                
                # Create a "format string" in memory
                format_string = payload or b"%x%x%x%n"
                self.memory.write_bytes(address, format_string, {"vulnerability": "format_string"})
                result["success"] = True
                
            elif vuln_type == "code_injection":
                # Inject executable code into a writeable memory segment
                segment = self.memory.find_segment(address)
                if segment is None:
                    result["error"] = f"Address 0x{address:08x} not in any memory segment"
                    return result
                
                # This would normally be caught by DEP, but we allow it for demonstration
                shellcode = payload or bytes([0x90] * (size - 2) + [0x90, 0xC3])  # NOP sled + RET
                self.memory.write_bytes(address, shellcode, {"vulnerability": "code_injection"})
                result["success"] = True
                
            else:
                result["error"] = f"Unknown vulnerability type: {vuln_type}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_forensic_logs(self, format_type: str = "dict") -> Union[List[Dict[str, Any]], str]:
        """Get forensic logs in the specified format."""
        return self.forensic_log.export_logs(format_type)
    
    def reset(self) -> None:
        """Reset the VM state while preserving configuration."""
        # Reset CPU
        self.cpu.reset()
        
        # Reset memory segments (clear data but preserve structure)
        for segment in self.memory.segments:
            segment.data = bytearray(segment.size)
        
        # Reset memory protection events
        self.memory.protection_events = []
        
        # Reset program state
        self.program_loaded = False
        self.program_name = ""
        self.program_entry_point = 0
        
        # Reset stack pointer
        self.cpu.registers.sp = self.stack_segment.base_address + self.stack_segment.size - 4
        self.cpu.registers.bp = self.cpu.registers.sp
        
        # Reset VM state
        self.state = VMState.IDLE
        self.execution_stats = ExecutionStats()
        
        # Log reset
        self.forensic_log.log_system_event("reset", {})
    
    def get_control_flow_visualization(self, format_type: str = "dict") -> Union[Dict[str, Any], str]:
        """
        Generate a visualization of the control flow.
        
        This is useful for understanding how attacks manipulate program flow.
        """
        # Extract control flow records
        records = self.cpu.control_flow_records
        
        # Build a graph representation
        nodes = set()
        edges = []
        
        for record in records:
            nodes.add(record.from_address)
            nodes.add(record.to_address)
            
            edge = {
                "source": record.from_address,
                "target": record.to_address,
                "type": record.event_type,
                "legitimate": record.legitimate,
                "instruction": record.instruction,
            }
            edges.append(edge)
        
        nodes_list = [{"address": addr} for addr in sorted(nodes)]
        
        visualization = {
            "nodes": nodes_list,
            "edges": edges,
        }
        
        if format_type == "dict":
            return visualization
        elif format_type == "json":
            import json
            return json.dumps(visualization, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def get_memory_access_pattern(self) -> Dict[str, Dict[int, int]]:
        """
        Analyze memory access patterns from the forensic logs.
        
        Useful for identifying suspicious memory behavior.
        """
        if not self.forensic_log.detailed:
            return {"error": "Detailed logging must be enabled for memory access patterns"}
        
        patterns = {
            "read": {},
            "write": {},
            "execute": {},
        }
        
        for log in self.forensic_log.logs:
            if log["event_type"] == "memory_access":
                access_type = log["data"]["access_type"]
                address = log["data"]["address"]
                
                if access_type in patterns:
                    patterns[access_type][address] = patterns[access_type].get(address, 0) + 1
        
        return patterns
    
    def compare_protection_strategies(
        self,
        strategies: List[MemoryProtection],
        program: List[int],
        attack: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Compare different memory protection strategies against the same attack.
        
        This is useful for educational purposes to show how different protections
        affect exploitability.
        """
        results = []
        
        for strategy in strategies:
            # Reset VM and apply new protection strategy
            self.reset()
            self.protection = strategy
            self._apply_memory_protections()
            
            # Load the program
            self.load_program(program)
            
            # Set up the attack
            if attack["type"] == "buffer_overflow":
                self.inject_vulnerability(
                    "buffer_overflow",
                    attack["address"],
                    attack["size"],
                    attack.get("payload")
                )
            elif attack["type"] == "code_injection":
                self.inject_vulnerability(
                    "code_injection",
                    attack["address"],
                    attack["size"],
                    attack.get("payload")
                )
            # Add other attack types as needed
            
            # Run the program
            execution_result = self.run()
            
            # Collect results
            results.append({
                "protection": strategy.get_protection_description(),
                "attack_successful": not execution_result.success,
                "protection_events": len(execution_result.protection_events),
                "execution_result": execution_result.get_summary(),
            })
        
        return results
    
    def get_state(self) -> VMState:
        """Get current VM state."""
        return self.state
    
    def get_execution_stats(self) -> ExecutionStats:
        """Get execution statistics."""
        return self.execution_stats
    
    def step(self) -> bool:
        """Execute a single instruction."""
        if not self.program_loaded:
            return False
        
        if self.state != VMState.RUNNING:
            self.state = VMState.RUNNING
        
        try:
            opcode = self.cpu.fetch()
            result = self.cpu.execute_instruction_by_opcode(opcode)
            self.execution_stats.instructions_executed += 1
            self.execution_stats.cycles += 1
            return result
        except Exception:
            self.state = VMState.ERROR
            return False
    
    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get execution trace from control flow records."""
        trace = []
        for record in self.cpu.control_flow_records:
            trace.append({
                "from_address": record.from_address,
                "to_address": record.to_address,
                "event_type": record.event_type,
                "instruction": record.instruction,
                "legitimate": record.legitimate,
                "timestamp": record.timestamp,
                "context": record.context
            })
        return trace