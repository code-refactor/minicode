"""Serializable execution state for reproducibility and testing."""

import json
import pickle
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Import common state definitions
from common.core.state import VMState, ProcessorState, ThreadState, ExecutionStats


class StateEncoder(json.JSONEncoder):
    """Custom JSON encoder for VM state objects."""
    
    def default(self, obj):
        """Encode objects that are not JSON serializable by default."""
        if isinstance(obj, Enum):
            return {"__enum__": True, "name": obj.__class__.__name__, "value": obj.name}
        
        if is_dataclass(obj):
            return {"__dataclass__": True, "name": obj.__class__.__name__, "data": asdict(obj)}
        
        if isinstance(obj, set):
            return {"__set__": True, "values": list(obj)}
        
        if hasattr(obj, "to_dict"):
            method = getattr(obj, "to_dict")
            if callable(method):
                return {"__custom__": True, "class": obj.__class__.__name__, "data": method()}
        
        return super().default(obj)


class StateDecoder(json.JSONDecoder):
    """Custom JSON decoder for VM state objects."""
    
    def __init__(self, *args, class_registry=None, **kwargs):
        """
        Initialize the decoder.
        
        Args:
            class_registry: Registry of available classes for reconstruction
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.class_registry = class_registry or {}
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
    
    def object_hook(self, obj):
        """Decode objects that were encoded with the custom encoder."""
        if "__enum__" in obj:
            enum_class = self.class_registry.get(obj["name"])
            if enum_class:
                return getattr(enum_class, obj["value"])
            return obj
        
        if "__dataclass__" in obj:
            dataclass_type = self.class_registry.get(obj["name"])
            if dataclass_type:
                return dataclass_type(**obj["data"])
            return obj
        
        if "__set__" in obj:
            return set(obj["values"])
        
        if "__custom__" in obj:
            class_type = self.class_registry.get(obj["class"])
            if class_type and hasattr(class_type, "from_dict"):
                method = getattr(class_type, "from_dict")
                if callable(method):
                    return method(obj["data"])
            return obj
        
        return obj


class ExecutionState:
    """
    Manages the serialization and deserialization of VM execution state.
    
    This class ensures that the entire state of the VM can be saved,
    restored, and transferred for reproducibility and testing.
    """
    
    def __init__(self, vm):
        """
        Initialize with reference to the VM.
        
        Args:
            vm: The virtual machine instance
        """
        self.vm = vm
        self.class_registry = {}
        
        # Register known classes
        self._register_classes()
    
    def _register_classes(self) -> None:
        """Register known classes for serialization/deserialization."""
        # Import here to avoid circular imports
        from common.core.state import InstructionType, ProcessorState, VMState
        from vm_emulator.memory.cache import MESIState, MOESIState, DragonState, CoherenceProtocol
        from vm_emulator.threading.thread import ThreadPriority
        from vm_emulator.scheduling.scheduler import SchedulingPolicy
        from vm_emulator.core.race import RaceType
        from vm_emulator.memory.patterns import AccessPattern, SharingPattern
        
        # Register enums
        self.class_registry.update({
            "InstructionType": InstructionType,
            "ProcessorState": ProcessorState,
            "VMState": VMState,
            "MESIState": MESIState,
            "MOESIState": MOESIState,
            "DragonState": DragonState,
            "CoherenceProtocol": CoherenceProtocol,
            "ThreadPriority": ThreadPriority,
            "SchedulingPolicy": SchedulingPolicy,
            "RaceType": RaceType,
            "AccessPattern": AccessPattern,
            "SharingPattern": SharingPattern,
        })
        
        # Register dataclasses and custom classes
        from vm_emulator.core.instruction import Instruction
        from vm_emulator.core.processor import Processor
        from vm_emulator.core.program import Program
        
        self.class_registry.update({
            "Instruction": Instruction,
            "Processor": Processor,
            "Program": Program,
        })
    
    def capture_state(self) -> Dict[str, Any]:
        """
        Capture the current execution state of the VM.
        
        Returns:
            Dictionary representing the VM state
        """
        state = {}
        
        # Capture VM core state
        state["vm"] = {
            "state": self.vm.state,
            "global_clock": self.vm.global_clock,
            "random_seed": self.vm.random_seed,
            "num_processors": self.vm.num_processors,
        }
        
        # Capture processor states
        state["processors"] = []
        for processor in self.vm.processors:
            processor_state = {
                "processor_id": processor.processor_id,
                "registers": processor.registers.copy(),
                "pc": processor.pc,
                "state": processor.state,
                "current_thread_id": processor.current_thread_id,
                "cycle_count": processor.cycle_count,
                "stall_cycles": processor.stall_cycles,
            }
            state["processors"].append(processor_state)
        
        # Capture thread states
        state["threads"] = {}
        for thread_id, thread in self.vm.threads.items():
            thread_state = {
                "thread_id": thread.thread_id,
                "program": thread.program.to_dict(),
                "pc": thread.pc,
                "registers": thread.registers.copy(),
                "stack": thread.stack.copy(),
                "state": thread.state,
                "processor_id": thread.processor_id,
                "parent_thread_id": thread.parent_thread_id,
                "creation_time": thread.creation_time,
                "execution_cycles": thread.execution_cycles,
            }
            state["threads"][thread_id] = thread_state
        
        # Capture memory state
        state["memory"] = {
            "memory": self.vm.main_memory.memory.copy(),
            "size": self.vm.main_memory.size,
        }
        
        # Capture loaded programs
        state["programs"] = {}
        for program_id, program in self.vm.loaded_programs.items():
            state["programs"][program_id] = program.to_dict()
        
        # Capture scheduler state
        if hasattr(self.vm, "scheduler"):
            state["scheduler"] = {
                "policy": self.vm.scheduler.__class__.__name__,
                "time_slice": self.vm.scheduler.time_slice,
                "random_seed": self.vm.scheduler.random_seed,
                "thread_run_times": self.vm.scheduler.thread_run_times.copy(),
                "thread_wait_cycles": self.vm.scheduler.thread_wait_cycles.copy(),
                "processor_assignments": self.vm.scheduler.processor_assignments.copy(),
                "thread_to_processor": self.vm.scheduler.thread_to_processor.copy(),
                "time_slice_remaining": self.vm.scheduler.time_slice_remaining.copy(),
            }
        
        # Capture synchronization state
        if hasattr(self.vm, "sync_manager"):
            state["sync"] = {
                "locks": {},
                "semaphores": {},
                "barriers": {},
                "latches": {},
                "thread_waits": {},
            }
            
            # Capture lock states
            for lock_id, lock in self.vm.sync_manager.locks.items():
                state["sync"]["locks"][lock_id] = {
                    "state": lock.state,
                    "owner": lock.owner,
                    "waiting_threads": lock.waiting_threads.copy(),
                }
            
            # Capture semaphore states
            for sem_id, sem in self.vm.sync_manager.semaphores.items():
                state["sync"]["semaphores"][sem_id] = {
                    "permits": sem.permits,
                    "waiting_threads": sem.waiting_threads.copy(),
                }
            
            # Capture barrier states
            for barrier_id, barrier in self.vm.sync_manager.barriers.items():
                state["sync"]["barriers"][barrier_id] = {
                    "parties": barrier.parties,
                    "waiting_threads": list(barrier.waiting_threads),
                    "generation": barrier.generation,
                    "state": barrier.state,
                }
            
            # Capture latch states
            for latch_id, latch in self.vm.sync_manager.latches.items():
                state["sync"]["latches"][latch_id] = {
                    "count": latch.count,
                    "initial_count": latch.initial_count,
                    "waiting_threads": list(latch.waiting_threads),
                }
            
            # Capture thread wait info
            state["sync"]["thread_waits"] = self.vm.sync_manager.thread_waits.copy()
        
        # Capture memory system state (if using coherent memory)
        if hasattr(self.vm, "memory_system"):
            state["memory_system"] = {
                "protocol": self.vm.memory_system.protocol.name,
                "cache_line_size": self.vm.memory_system.cache_line_size,
                "cache_size": self.vm.memory_system.cache_size,
                "cache_associativity": self.vm.memory_system.cache_associativity,
                "bus_latency": self.vm.memory_system.bus.latency,
            }
            
            # Capture cache states
            state["caches"] = {}
            for processor_id, cache in self.vm.memory_system.caches.items():
                cache_state = {
                    "cache_id": cache.cache_id,
                    "size": cache.size,
                    "line_size": cache.line_size,
                    "associativity": cache.associativity,
                    "num_sets": cache.num_sets,
                    "reads": cache.reads,
                    "writes": cache.writes,
                    "hits": cache.hits,
                    "misses": cache.misses,
                    "evictions": cache.evictions,
                }
                
                # Capture cache line states for MESI caches
                if hasattr(cache, "line_states"):
                    cache_state["line_states"] = {}
                    for (set_idx, line_idx), state in cache.line_states.items():
                        cache_state["line_states"][f"{set_idx},{line_idx}"] = state.name
                
                state["caches"][processor_id] = cache_state
        
        # Capture race detector state
        if hasattr(self.vm, "race_detector"):
            state["race_detector"] = {
                "race_conditions": self.vm.race_detector.race_conditions.copy(),
                "shared_addresses": list(self.vm.race_detector.shared_addresses),
                "last_writer": {str(addr): writer for addr, writer in self.vm.race_detector.last_writer.items()},
                "thread_locks": {tid: list(locks) for tid, locks in self.vm.race_detector.thread_locks.items()},
            }
        
        return state
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore the VM to a previously captured state.
        
        Args:
            state: Dictionary representing the VM state
        """
        # Restore VM core state
        vm_state = state["vm"]
        self.vm.state = vm_state["state"]
        self.vm.global_clock = vm_state["global_clock"]
        
        # Restore processors
        for i, processor_state in enumerate(state["processors"]):
            processor = self.vm.processors[i]
            processor.registers = processor_state["registers"].copy()
            processor.pc = processor_state["pc"]
            processor.state = processor_state["state"]
            processor.current_thread_id = processor_state["current_thread_id"]
            processor.cycle_count = processor_state["cycle_count"]
            processor.stall_cycles = processor_state["stall_cycles"]
        
        # Restore memory
        memory_state = state["memory"]
        self.vm.main_memory.memory = memory_state["memory"].copy()
        
        # Restore programs
        self.vm.loaded_programs = {}
        for program_id, program_dict in state["programs"].items():
            from vm_emulator.core.program import Program
            program = Program.from_dict(program_dict)
            self.vm.loaded_programs[program_id] = program
        
        # Restore threads
        self.vm.threads = {}
        for thread_id, thread_state in state["threads"].items():
            from vm_emulator.threading.thread import Thread
            program_id = thread_state["program"]["name"]
            program = self.vm.loaded_programs[program_id]
            
            thread = Thread(
                thread_id=thread_state["thread_id"],
                program=program,
                pc=thread_state["pc"],
                registers=thread_state["registers"].copy(),
                stack=thread_state["stack"].copy(),
                state=thread_state["state"],
                processor_id=thread_state["processor_id"],
                parent_thread_id=thread_state["parent_thread_id"],
                creation_time=thread_state["creation_time"],
                execution_cycles=thread_state["execution_cycles"],
            )
            
            self.vm.threads[thread_id] = thread
        
        # Restore scheduler state if available
        if "scheduler" in state and hasattr(self.vm, "scheduler"):
            scheduler_state = state["scheduler"]
            self.vm.scheduler.thread_run_times = scheduler_state["thread_run_times"].copy()
            self.vm.scheduler.thread_wait_cycles = scheduler_state["thread_wait_cycles"].copy()
            self.vm.scheduler.processor_assignments = scheduler_state["processor_assignments"].copy()
            self.vm.scheduler.thread_to_processor = scheduler_state["thread_to_processor"].copy()
            self.vm.scheduler.time_slice_remaining = scheduler_state["time_slice_remaining"].copy()
        
        # Restore synchronization state if available
        if "sync" in state and hasattr(self.vm, "sync_manager"):
            # Would need to reconstruct synchronization primitives
            # This is more complex and would require custom deserialization
            pass
        
        # Restore memory system state if available
        if "memory_system" in state and hasattr(self.vm, "memory_system"):
            # Would need to reconstruct caches and coherence state
            # This is more complex and would require custom deserialization
            pass
        
        # Restore race detector state if available
        if "race_detector" in state and hasattr(self.vm, "race_detector"):
            detector = self.vm.race_detector
            detector.race_conditions = state["race_detector"]["race_conditions"].copy()
            detector.shared_addresses = set(state["race_detector"]["shared_addresses"])
            detector.last_writer = {int(addr): writer for addr, writer in state["race_detector"]["last_writer"].items()}
            detector.thread_locks = {tid: set(locks) for tid, locks in state["race_detector"]["thread_locks"].items()}
    
    def serialize(self, state: Dict[str, Any], format: str = "json") -> Union[str, bytes]:
        """
        Serialize the state to a string or bytes.
        
        Args:
            state: Dictionary representing the VM state
            format: Serialization format ("json" or "pickle")
            
        Returns:
            Serialized state as string or bytes
        """
        if format == "json":
            return json.dumps(state, cls=StateEncoder, indent=2)
        
        elif format == "pickle":
            return pickle.dumps(state)
        
        raise ValueError(f"Unsupported serialization format: {format}")
    
    def deserialize(
        self, serialized_state: Union[str, bytes], format: str = "json"
    ) -> Dict[str, Any]:
        """
        Deserialize a state from a string or bytes.
        
        Args:
            serialized_state: Serialized state
            format: Serialization format ("json" or "pickle")
            
        Returns:
            Dictionary representing the VM state
        """
        if format == "json":
            return json.loads(
                serialized_state,
                cls=lambda *args, **kwargs: StateDecoder(*args, class_registry=self.class_registry, **kwargs),
            )
        
        elif format == "pickle":
            return pickle.loads(serialized_state)
        
        raise ValueError(f"Unsupported serialization format: {format}")
    
    def save_state(self, filename: str, format: str = "json") -> None:
        """
        Save the current VM state to a file.
        
        Args:
            filename: Output filename
            format: Serialization format ("json" or "pickle")
        """
        state = self.capture_state()
        serialized = self.serialize(state, format)
        
        mode = "w" if format == "json" else "wb"
        with open(filename, mode) as f:
            f.write(serialized)
    
    def load_state(self, filename: str, format: str = "json") -> None:
        """
        Load VM state from a file.
        
        Args:
            filename: Input filename
            format: Serialization format ("json" or "pickle")
        """
        mode = "r" if format == "json" else "rb"
        with open(filename, mode) as f:
            serialized = f.read()
        
        state = self.deserialize(serialized, format)
        self.restore_state(state)
    
    def clone_vm(self) -> Any:
        """
        Create a clone of the current VM.
        
        Returns:
            A new VM instance with the same state
        """
        # Get VM class
        vm_class = self.vm.__class__
        
        # Create a new VM instance
        new_vm = vm_class(
            num_processors=self.vm.num_processors,
            memory_size=self.vm.main_memory.size,
            random_seed=self.vm.random_seed,
        )
        
        # Capture current state
        state = self.capture_state()
        
        # Create an ExecutionState for the new VM
        new_state_manager = ExecutionState(new_vm)
        
        # Restore state to the new VM
        new_state_manager.restore_state(state)
        
        return new_vm