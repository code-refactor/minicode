"""Common exception types for VM implementations."""


class VMException(Exception):
    """Base exception for VM errors."""
    pass


class ExecutionException(VMException):
    """Exception during instruction execution."""
    pass


class MemoryException(VMException):
    """Memory-related exception."""
    pass


class MemoryAccessViolation(MemoryException):
    """Memory access violation."""
    
    def __init__(self, address: int, access_type: str, message: str = ""):
        """Initialize with address and access type."""
        self.address = address
        self.access_type = access_type
        super().__init__(message or f"Memory {access_type} violation at 0x{address:x}")


class SegmentationFault(MemoryAccessViolation):
    """Segmentation fault exception."""
    
    def __init__(self, address: int):
        """Initialize with address."""
        super().__init__(address, "segmentation", f"Segmentation fault at 0x{address:x}")


class PermissionDenied(MemoryAccessViolation):
    """Permission denied for memory access."""
    
    def __init__(self, address: int, required_permission: str):
        """Initialize with address and required permission."""
        self.required_permission = required_permission
        super().__init__(
            address,
            "permission",
            f"Permission denied for {required_permission} at 0x{address:x}"
        )


class InvalidInstruction(ExecutionException):
    """Invalid instruction exception."""
    
    def __init__(self, opcode: str, address: int = 0):
        """Initialize with opcode."""
        self.opcode = opcode
        self.address = address
        super().__init__(f"Invalid instruction '{opcode}' at 0x{address:x}")


class PrivilegeViolation(ExecutionException):
    """Privilege violation exception."""
    
    def __init__(self, required_level: int, current_level: int):
        """Initialize with privilege levels."""
        self.required_level = required_level
        self.current_level = current_level
        super().__init__(
            f"Privilege violation: required={required_level}, current={current_level}"
        )


class StackOverflow(MemoryException):
    """Stack overflow exception."""
    
    def __init__(self, stack_pointer: int, stack_limit: int):
        """Initialize with stack information."""
        self.stack_pointer = stack_pointer
        self.stack_limit = stack_limit
        super().__init__(
            f"Stack overflow: SP=0x{stack_pointer:x}, limit=0x{stack_limit:x}"
        )


class DivisionByZero(ExecutionException):
    """Division by zero exception."""
    
    def __init__(self, address: int = 0):
        """Initialize with address."""
        self.address = address
        super().__init__(f"Division by zero at 0x{address:x}")


class Breakpoint(ExecutionException):
    """Breakpoint exception."""
    
    def __init__(self, address: int):
        """Initialize with address."""
        self.address = address
        super().__init__(f"Breakpoint at 0x{address:x}")


class HaltException(ExecutionException):
    """Halt instruction encountered."""
    
    def __init__(self, exit_code: int = 0):
        """Initialize with exit code."""
        self.exit_code = exit_code
        super().__init__(f"HALT with exit code {exit_code}")


class ThreadException(VMException):
    """Thread-related exception."""
    pass


class DeadlockDetected(ThreadException):
    """Deadlock detected exception."""
    
    def __init__(self, threads: list):
        """Initialize with involved threads."""
        self.threads = threads
        super().__init__(f"Deadlock detected involving threads: {threads}")


class SynchronizationException(ThreadException):
    """Synchronization primitive exception."""
    pass


class TimeoutException(VMException):
    """Operation timeout exception."""
    
    def __init__(self, operation: str, timeout: int):
        """Initialize with operation and timeout."""
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation '{operation}' timed out after {timeout} cycles")