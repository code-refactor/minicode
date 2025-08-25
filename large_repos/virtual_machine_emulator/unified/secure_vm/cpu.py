"""
CPU implementation for the secure VM.

This module implements a simplified CPU architecture with registers, instructions,
and support for different privilege levels and security isolation.
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
import struct
import time

# Import common library components
from common.core.processor_base import ProcessorBase, Flags
from common.core.instruction import Instruction as CommonInstruction, InstructionType
from common.core.state import ProcessorState
from common.utils.exceptions import (
    ExecutionException, MemoryException, InvalidInstruction as CommonInvalidInstruction,
    PrivilegeViolation as CommonPrivilegeViolation
)
from secure_vm.memory import Memory, MemoryPermission


class PrivilegeLevel(Enum):
    """CPU privilege levels, from least to most privileged."""
    USER = 0       # Unprivileged user code
    SUPERVISOR = 1 # Limited system operations
    KERNEL = 2     # Full system access


# Use common exceptions but extend for security-specific needs
class CPUException(ExecutionException):
    """Base class for CPU execution exceptions."""
    pass


class SegmentationFault(MemoryException):
    """Raised when memory access violates segmentation rules."""
    pass


class ProtectionFault(MemoryException):
    """Raised when memory access violates protection rules."""
    pass


# Use common PrivilegeViolation and InvalidInstruction
PrivilegeViolation = CommonPrivilegeViolation
InvalidInstruction = CommonInvalidInstruction


# Use common InstructionType directly
# CONTROL is now InstructionType.BRANCH for compatibility


class SecurityInstruction(CommonInstruction):
    """Security-enhanced instruction with privilege requirements."""
    
    def __init__(
        self,
        opcode: Union[int, str],
        name: str = None,
        instr_type: InstructionType = InstructionType.NOP,
        operand_count: int = 0,
        required_privilege: PrivilegeLevel = PrivilegeLevel.USER,
        handler: Optional[Callable] = None,
        **kwargs
    ):
        # Use name as opcode if name not provided separately
        if name is None:
            name = str(opcode)
        
        super().__init__(
            opcode=name,
            instruction_type=instr_type,
            **kwargs
        )
        
        self.name = name
        self.operand_count = operand_count
        self.required_privilege = required_privilege
        self.handler = handler
        
        # Store original opcode if it was numeric
        if isinstance(opcode, int):
            self.numeric_opcode = opcode
        else:
            self.numeric_opcode = None
    
    def __str__(self) -> str:
        if self.numeric_opcode is not None:
            return f"{self.name} (0x{self.numeric_opcode:02x})"
        return f"{self.name}"


class SecurityRegisters:
    """Security-specific register extensions."""
    
    def __init__(self, base_registers):
        self.base = base_registers
        # Protection and privilege registers
        self.privilege_level = PrivilegeLevel.USER
        self.protection_key = 0
    
    def get_register(self, reg_spec: Union[int, str]) -> int:
        """Get register value by number or name."""
        if isinstance(reg_spec, int):
            # Numeric register
            if 0 <= reg_spec < 16:
                return self.base.get_register(f"R{reg_spec}")
            raise ValueError(f"Invalid register number: {reg_spec}")
        else:
            # Named register
            return self.base.get_register(reg_spec)
    
    def set_register(self, reg_spec: Union[int, str], value: int) -> None:
        """Set register value by number or name."""
        if isinstance(reg_spec, int):
            # Numeric register
            if 0 <= reg_spec < 16:
                self.base.set_register(f"R{reg_spec}", value)
            else:
                raise ValueError(f"Invalid register number: {reg_spec}")
        else:
            # Named register
            self.base.set_register(reg_spec, value)
    
    def dump_registers(self) -> Dict[str, int]:
        """Get a snapshot of all register values."""
        result = self.base.get_all_registers()
        result.update({
            "IP": self.ip,  # Alias for PC
            "SP": self.base.stack_pointer,
            "BP": self.base.frame_pointer, # Alias for FP
            "PRIV": self.privilege_level.value,
            "PKEY": self.protection_key,
        })
        return result
    
    @property
    def ip(self) -> int:
        """Instruction pointer (alias for program counter)."""
        return self.base.program_counter
    
    @ip.setter
    def ip(self, value: int) -> None:
        """Set instruction pointer."""
        self.base.program_counter = value
    
    @property
    def sp(self) -> int:
        """Stack pointer."""
        return self.base.stack_pointer
    
    @sp.setter
    def sp(self, value: int) -> None:
        """Set stack pointer."""
        self.base.stack_pointer = value
    
    @property
    def bp(self) -> int:
        """Base pointer (frame pointer)."""
        return self.base.frame_pointer
    
    @bp.setter
    def bp(self, value: int) -> None:
        """Set base pointer."""
        self.base.frame_pointer = value
    
    @property
    def flags(self) -> int:
        """Flags register."""
        return self.base.flags
    
    @flags.setter
    def flags(self, value: int) -> None:
        """Set flags register."""
        self.base.flags = value


class ControlFlowRecord:
    """Records a control flow event for integrity monitoring."""
    
    def __init__(
        self,
        from_address: int,
        to_address: int,
        event_type: str,
        instruction: str,
        legitimate: bool = True,
        context: Dict[str, Any] = None,
    ):
        self.from_address = from_address
        self.to_address = to_address
        self.event_type = event_type
        self.instruction = instruction
        self.legitimate = legitimate
        self.context = context or {}
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        return (
            f"Control flow: {self.event_type} from 0x{self.from_address:x} "
            f"to 0x{self.to_address:x} via {self.instruction} "
            f"{'(legitimate)' if self.legitimate else '(HIJACKED)'}"
        )


class CPU(ProcessorBase):
    """Security-enhanced CPU implementation with privilege levels and execution support."""
    
    # Security-enhanced instruction set definition
    INSTRUCTIONS = {
        # Arithmetic instructions
        0x01: SecurityInstruction(0x01, "ADD", InstructionType.ARITHMETIC, 2),
        0x02: SecurityInstruction(0x02, "SUB", InstructionType.ARITHMETIC, 2),
        0x03: SecurityInstruction(0x03, "MUL", InstructionType.ARITHMETIC, 2),
        0x04: SecurityInstruction(0x04, "DIV", InstructionType.ARITHMETIC, 2),
        
        # Memory instructions
        0x10: SecurityInstruction(0x10, "MOV", InstructionType.MEMORY, 2),
        0x11: SecurityInstruction(0x11, "LOAD", InstructionType.MEMORY, 2),
        0x12: SecurityInstruction(0x12, "STORE", InstructionType.MEMORY, 2),
        0x13: SecurityInstruction(0x13, "PUSH", InstructionType.MEMORY, 1),
        0x14: SecurityInstruction(0x14, "POP", InstructionType.MEMORY, 1),
        
        # Control flow instructions
        0x20: SecurityInstruction(0x20, "JMP", InstructionType.BRANCH, 1),
        0x21: SecurityInstruction(0x21, "JZ", InstructionType.BRANCH, 1),
        0x22: SecurityInstruction(0x22, "JNZ", InstructionType.BRANCH, 1),
        0x23: SecurityInstruction(0x23, "CALL", InstructionType.BRANCH, 1),
        0x24: SecurityInstruction(0x24, "RET", InstructionType.BRANCH, 0),
        
        # System instructions (privileged)
        0x30: SecurityInstruction(0x30, "SYSCALL", InstructionType.SYSTEM, 1),
        0x31: SecurityInstruction(0x31, "SYSRET", InstructionType.SYSTEM, 0),
        0x32: SecurityInstruction(0x32, "ELEVATE", InstructionType.SYSTEM, 1, PrivilegeLevel.KERNEL),
        0x33: SecurityInstruction(0x33, "LOWER", InstructionType.SYSTEM, 1),
        
        # Special instructions
        0xF0: SecurityInstruction(0xF0, "NOP", InstructionType.NOP, 0),
        0xF1: SecurityInstruction(0xF1, "HALT", InstructionType.SYSTEM, 0),
        0xF2: SecurityInstruction(0xF2, "INT", InstructionType.SYSTEM, 1),
    }
    
    def __init__(self, memory: Memory):
        super().__init__()
        
        # Security-specific register extensions
        self.sec_registers = SecurityRegisters(self.registers)
        self.memory = memory
        self.running = False
        self.halted = False
        self.control_flow_records: List[ControlFlowRecord] = []
        
        # Security and protection state
        self.protection_keys: Dict[int, Set[MemoryPermission]] = {}
        self.shadow_stack: List[int] = []  # For control flow integrity
        self.syscall_table: Dict[int, Callable] = {}
        
        # Performance tracking
        self.execution_start_time = 0
        self.execution_time = 0
    
    def reset(self) -> None:
        """Reset the CPU state."""
        super().reset()
        self.sec_registers = SecurityRegisters(self.registers)
        self.running = False
        self.halted = False
        self.control_flow_records = []
        self.shadow_stack = []
        self.execution_start_time = 0
        self.execution_time = 0
    
    def fetch(self) -> int:
        """Fetch the next instruction byte from memory."""
        try:
            # We use execute here to enforce DEP
            instr_byte = self.memory.execute(
                self.sec_registers.ip,
                {"instruction_pointer": self.sec_registers.ip}
            )
            self.sec_registers.ip += 1
            return instr_byte
        except MemoryError as e:
            # Check if this is due to a non-executable segment
            segment = self.memory.find_segment(self.sec_registers.ip)
            if segment and not segment.check_permission(self.sec_registers.ip, MemoryPermission.EXECUTE):
                raise SegmentationFault(f"Cannot execute code from non-executable memory at 0x{self.sec_registers.ip:x}")
            else:
                raise SegmentationFault(f"Failed to fetch instruction: {str(e)}")
    
    def fetch_word(self) -> int:
        """Fetch a 32-bit word from memory at the instruction pointer."""
        try:
            # For operands we use read_word since they don't need to be executable
            word = self.memory.read_word(
                self.sec_registers.ip,
                {"instruction_pointer": self.sec_registers.ip}
            )
            self.sec_registers.ip += 4
            return word
        except MemoryError as e:
            raise SegmentationFault(f"Failed to fetch word: {str(e)}")
    
    def push(self, value: int) -> None:
        """Push a value onto the stack."""
        self.sec_registers.sp -= 4
        try:
            self.memory.write_word(
                self.sec_registers.sp,
                value,
                {"instruction_pointer": self.sec_registers.ip}
            )
        except MemoryError as e:
            # Restore SP if push failed
            self.sec_registers.sp += 4
            raise SegmentationFault(f"Failed to push value: {str(e)}")
    
    def pop(self) -> int:
        """Pop a value from the stack."""
        try:
            value = self.memory.read_word(
                self.sec_registers.sp,
                {"instruction_pointer": self.sec_registers.ip}
            )
            self.sec_registers.sp += 4
            return value
        except MemoryError as e:
            raise SegmentationFault(f"Failed to pop value: {str(e)}")
    
    def execute_instruction(self, instruction: CommonInstruction) -> bool:
        """Execute a common instruction (ProcessorBase interface)."""
        # Convert common instruction to security instruction if needed
        if not isinstance(instruction, SecurityInstruction):
            # Try to find matching security instruction
            for sec_inst in self.INSTRUCTIONS.values():
                if sec_inst.name == instruction.opcode:
                    return self.execute_instruction_by_opcode(sec_inst.numeric_opcode or 0)
            
            # If not found, create a basic security instruction
            sec_inst = SecurityInstruction(
                instruction.opcode,
                instruction.opcode,
                instruction.instruction_type,
                len(instruction.operands)
            )
            return self._execute_generic_instruction(sec_inst)
        
        return self.execute_instruction_by_opcode(instruction.numeric_opcode or 0)
    
    def _execute_generic_instruction(self, instruction: SecurityInstruction) -> bool:
        """Execute a generic instruction that doesn't have specific opcode mapping."""
        # This is a simplified execution for compatibility
        if instruction.instruction_type == InstructionType.NOP:
            pass
        elif instruction.instruction_type == InstructionType.SYSTEM:
            if instruction.name == "HALT":
                self.halted = True
                self.running = False
                return False
        
        self.cycle_count += 1
        return True

    def execute_instruction_by_opcode(self, opcode: int) -> bool:
        """Execute a single instruction with the given opcode."""
        if opcode not in self.INSTRUCTIONS:
            raise InvalidInstruction(f"0x{opcode:02x}", self.sec_registers.ip)
        
        instruction = self.INSTRUCTIONS[opcode]
        
        # Check privilege level for security instructions
        if hasattr(instruction, 'required_privilege'):
            if self.sec_registers.privilege_level.value < instruction.required_privilege.value:
                self.record_control_flow_event(
                    self.sec_registers.ip - 1,  # Previous IP value where opcode was fetched
                    self.sec_registers.ip,      # Current IP value
                    "privilege-violation",
                    instruction.name,
                    False
                )
                raise PrivilegeViolation(
                    instruction.required_privilege.value,
                    self.sec_registers.privilege_level.value
                )
        
        # Decode and execute the instruction based on type
        if instruction.instruction_type == InstructionType.ARITHMETIC:
            self._execute_arithmetic(instruction)
        elif instruction.instruction_type == InstructionType.MEMORY:
            self._execute_memory(instruction)
        elif instruction.instruction_type == InstructionType.BRANCH:
            self._execute_control(instruction)
        elif instruction.instruction_type == InstructionType.SYSTEM:
            return self._execute_system(instruction)
        elif instruction.instruction_type == InstructionType.NOP:
            return self._execute_special(instruction)
        
        self.cycle_count += 1
        return True  # Continue execution unless HALT or similar
    
    def _execute_arithmetic(self, instruction: SecurityInstruction) -> None:
        """Execute an arithmetic instruction."""
        if instruction.operand_count == 2:
            # For simplicity, we'll assume reg-reg operations
            dest_reg = self.fetch()
            src_reg = self.fetch()
            dest_val = self.sec_registers.get_register(dest_reg)
            src_val = self.sec_registers.get_register(src_reg)
            
            result = 0
            if instruction.name == "ADD":
                result = (dest_val + src_val) & 0xFFFFFFFF
            elif instruction.name == "SUB":
                result = (dest_val - src_val) & 0xFFFFFFFF
            elif instruction.name == "MUL":
                result = (dest_val * src_val) & 0xFFFFFFFF
            elif instruction.name == "DIV":
                if src_val == 0:
                    raise CPUException("Division by zero")
                result = (dest_val // src_val) & 0xFFFFFFFF
            
            self.sec_registers.set_register(dest_reg, result)
            
            # Update flags (zero flag example)
            if result == 0:
                self.set_flag(Flags.ZERO, True)
            else:
                self.set_flag(Flags.ZERO, False)
    
    def _execute_memory(self, instruction: SecurityInstruction) -> None:
        """Execute a memory instruction."""
        if instruction.name == "MOV":
            dest_reg = self.fetch()
            src_type = self.fetch()  # 0x01 for immediate, 0x02 for register

            if src_type == 0x01:  # Immediate value
                # Fetch a 32-bit immediate value
                value = self.fetch_word()
                self.sec_registers.set_register(dest_reg, value)
            elif src_type == 0x02:  # Register value
                src_reg = self.fetch()
                value = self.sec_registers.get_register(src_reg)
                self.sec_registers.set_register(dest_reg, value)
            else:
                src_reg = src_type  # Backward compatibility
                value = self.sec_registers.get_register(src_reg)
                self.sec_registers.set_register(dest_reg, value)

        elif instruction.name == "LOAD":
            dest_reg = self.fetch()
            addr_reg = self.fetch()
            addr = self.sec_registers.get_register(addr_reg)
            try:
                value = self.memory.read_word(
                    addr,
                    {"instruction_pointer": self.sec_registers.ip - 2}
                )
                self.sec_registers.set_register(dest_reg, value)
            except MemoryError as e:
                raise SegmentationFault(f"LOAD failed: {str(e)}")

        elif instruction.name == "STORE":
            addr_reg = self.fetch()
            src_reg = self.fetch()
            addr = self.sec_registers.get_register(addr_reg)
            value = self.sec_registers.get_register(src_reg)
            try:
                self.memory.write_word(
                    addr,
                    value,
                    {"instruction_pointer": self.sec_registers.ip - 2}
                )
            except MemoryError as e:
                raise SegmentationFault(f"STORE failed: {str(e)}")

        elif instruction.name == "PUSH":
            reg = self.fetch()
            value = self.sec_registers.get_register(reg)
            self.push(value)

        elif instruction.name == "POP":
            reg = self.fetch()
            value = self.pop()
            self.sec_registers.set_register(reg, value)
    
    def _execute_control(self, instruction: SecurityInstruction) -> None:
        """Execute a control flow instruction."""
        if instruction.name == "JMP":
            target_reg = self.fetch()
            target = self.sec_registers.get_register(target_reg)
            
            # Record the control flow event
            self.record_control_flow_event(
                self.sec_registers.ip - 1,  # Where opcode was fetched
                target,
                "jump",
                instruction.name,
                True  # Assumed legitimate for now - CFI would validate this
            )
            
            self.sec_registers.ip = target
        
        elif instruction.name == "JZ":
            target_reg = self.fetch()
            target = self.sec_registers.get_register(target_reg)
            
            # Only jump if zero flag is set
            if self.get_flag(Flags.ZERO):
                # Record the control flow event
                self.record_control_flow_event(
                    self.sec_registers.ip - 1,
                    target,
                    "conditional-jump",
                    instruction.name,
                    True
                )
                self.sec_registers.ip = target
        
        elif instruction.name == "JNZ":
            target_reg = self.fetch()
            target = self.sec_registers.get_register(target_reg)
            
            # Only jump if zero flag is not set
            if not self.get_flag(Flags.ZERO):
                # Record the control flow event
                self.record_control_flow_event(
                    self.sec_registers.ip - 1,
                    target,
                    "conditional-jump",
                    instruction.name,
                    True
                )
                self.sec_registers.ip = target
        
        elif instruction.name == "CALL":
            target_reg = self.fetch()
            target = self.sec_registers.get_register(target_reg)
            return_addr = self.sec_registers.ip
            
            # Record return address in shadow stack for control flow integrity
            self.shadow_stack.append(return_addr)
            
            # Push return address onto the stack
            self.push(return_addr)
            
            # Record the control flow event
            self.record_control_flow_event(
                self.sec_registers.ip - 1,
                target,
                "call",
                instruction.name,
                True
            )
            
            self.sec_registers.ip = target
        
        elif instruction.name == "RET":
            # Pop return address from stack
            return_addr = self.pop()
            
            # Control flow integrity check using shadow stack
            shadow_valid = True
            if self.shadow_stack:
                expected_return = self.shadow_stack.pop()
                if expected_return != return_addr:
                    shadow_valid = False
                    # We record this but don't stop execution to allow exploits
                    self.record_control_flow_event(
                        self.sec_registers.ip - 1,
                        return_addr,
                        "return",
                        instruction.name,
                        False
                    )
            else:
                shadow_valid = False
                self.record_control_flow_event(
                    self.sec_registers.ip - 1,
                    return_addr,
                    "return",
                    instruction.name,
                    False
                )
            
            if shadow_valid:
                self.record_control_flow_event(
                    self.sec_registers.ip - 1,
                    return_addr,
                    "return",
                    instruction.name,
                    True
                )
            
            self.sec_registers.ip = return_addr
    
    def _execute_system(self, instruction: SecurityInstruction) -> None:
        """Execute a system instruction."""
        if instruction.name == "SYSCALL":
            syscall_num = self.fetch()
            
            # Record system call for forensic purposes
            context = {"registers": self.sec_registers.dump_registers()}
            self.record_control_flow_event(
                self.sec_registers.ip - 1,
                self.sec_registers.ip,
                "syscall",
                f"{instruction.name} {syscall_num}",
                True,
                context
            )
            
            # Execute the system call if registered
            if syscall_num in self.syscall_table:
                self.syscall_table[syscall_num](self)
        
        elif instruction.name == "SYSRET":
            # Return from system call - typically adjusts privilege
            prev_privilege = self.sec_registers.privilege_level
            
            # Only lower privilege on return, never elevate
            if prev_privilege != PrivilegeLevel.USER:
                self.sec_registers.privilege_level = PrivilegeLevel.USER
            
            self.record_control_flow_event(
                self.sec_registers.ip - 1,
                self.sec_registers.ip,
                "sysret",
                instruction.name,
                True,
                {"previous_privilege": prev_privilege.name}
            )
        
        elif instruction.name == "ELEVATE":
            # Elevate privilege level (requires KERNEL privilege to use)
            target_level = self.fetch()
            
            # Must be called from kernel mode for security
            # This is checked at the beginning of execute_instruction
            
            if 0 <= target_level <= 2:
                self.sec_registers.privilege_level = PrivilegeLevel(target_level)
                self.record_control_flow_event(
                    self.sec_registers.ip - 2,
                    self.sec_registers.ip,
                    "privilege-change",
                    instruction.name,
                    True,
                    {"new_level": self.sec_registers.privilege_level.name}
                )
            else:
                raise CPUException(f"Invalid privilege level: {target_level}")
        
        elif instruction.name == "LOWER":
            # Voluntarily lower privilege level
            target_level = self.fetch()
            current_level = self.sec_registers.privilege_level.value
            
            # Can only lower privilege, not elevate
            if 0 <= target_level < current_level:
                self.sec_registers.privilege_level = PrivilegeLevel(target_level)
                self.record_control_flow_event(
                    self.sec_registers.ip - 2,
                    self.sec_registers.ip,
                    "privilege-change",
                    instruction.name,
                    True,
                    {"new_level": self.sec_registers.privilege_level.name}
                )
            else:
                raise PrivilegeViolation(
                    f"Cannot elevate privilege from {current_level} to {target_level}"
                )
    
    def _execute_special(self, instruction: SecurityInstruction) -> bool:
        """Execute a special instruction. Returns False if execution should stop."""
        if instruction.name == "NOP":
            # No operation, just proceed
            pass
        
        elif instruction.name == "HALT":
            # Stop execution
            self.halted = True
            self.running = False
            return False
        
        elif instruction.name == "INT":
            # Software interrupt
            interrupt_num = self.fetch()
            
            # Record for forensic purposes
            self.record_control_flow_event(
                self.sec_registers.ip - 2,
                self.sec_registers.ip,
                "interrupt",
                f"{instruction.name} {interrupt_num}",
                True
            )
            
            # Handle the interrupt based on number
            # This would call an interrupt handler if implemented
            pass
        
        return True  # Continue execution
    
    def register_syscall(self, syscall_num: int, handler: Callable) -> None:
        """Register a system call handler."""
        self.syscall_table[syscall_num] = handler
    
    def record_control_flow_event(
        self,
        from_address: int,
        to_address: int,
        event_type: str,
        instruction: str,
        legitimate: bool = True,
        context: Dict[str, Any] = None,
    ) -> None:
        """Record a control flow event for integrity monitoring."""
        record = ControlFlowRecord(
            from_address=from_address,
            to_address=to_address,
            event_type=event_type,
            instruction=instruction,
            legitimate=legitimate,
            context=context,
        )
        self.control_flow_records.append(record)
    
    def run(self, max_instructions: int = 10000) -> int:
        """Run the CPU for up to max_instructions instructions."""
        if self.halted:
            return 0
        
        self.running = True
        self.execution_start_time = time.time()
        instructions_executed = 0
        
        try:
            while self.running and instructions_executed < max_instructions:
                # Fetch instruction
                opcode = self.fetch()
                
                # Execute instruction
                continue_execution = self.execute_instruction_by_opcode(opcode)
                if not continue_execution:
                    break
                
                instructions_executed += 1
        
        except (CPUException, SegmentationFault, ProtectionFault, ExecutionException) as e:
            self.running = False
            # Record the exception but don't re-raise it to allow exploit demonstration
            self.record_control_flow_event(
                self.sec_registers.ip,
                0,
                "exception",
                str(e),
                False
            )
        
        finally:
            self.execution_time += time.time() - self.execution_start_time
        
        return instructions_executed
    
    def get_control_flow_trace(self) -> List[ControlFlowRecord]:
        """Get the control flow trace for visualization."""
        return self.control_flow_records
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the CPU."""
        return {
            "cycles": self.cycle_count,
            "execution_time": self.execution_time,
            "instructions_per_second": self.cycle_count / max(self.execution_time, 0.001),
            "control_flow_events": len(self.control_flow_records),
        }