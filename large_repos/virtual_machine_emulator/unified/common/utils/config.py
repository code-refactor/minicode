"""Configuration management utilities."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json


@dataclass
class VMConfig:
    """Base VM configuration."""
    
    # Core settings
    memory_size: int = 65536
    max_cycles: int = 1000000
    debug: bool = False
    
    # Processor settings
    num_processors: int = 1
    processor_frequency: int = 1000  # MHz
    
    # Memory settings
    enable_memory_protection: bool = False
    enable_caching: bool = False
    cache_size: int = 4096
    
    # Execution settings
    enable_tracing: bool = True
    max_trace_events: int = 10000
    enable_statistics: bool = True
    
    # Thread settings (for parallel VMs)
    max_threads: int = 32
    default_stack_size: int = 4096
    scheduler_quantum: int = 100
    
    # Security settings (for secure VMs)
    enable_dep: bool = False  # Data Execution Prevention
    enable_aslr: bool = False  # Address Space Layout Randomization
    enable_stack_canaries: bool = False
    default_privilege_level: int = 0
    
    # Additional settings
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'memory_size': self.memory_size,
            'max_cycles': self.max_cycles,
            'debug': self.debug,
            'num_processors': self.num_processors,
            'processor_frequency': self.processor_frequency,
            'enable_memory_protection': self.enable_memory_protection,
            'enable_caching': self.enable_caching,
            'cache_size': self.cache_size,
            'enable_tracing': self.enable_tracing,
            'max_trace_events': self.max_trace_events,
            'enable_statistics': self.enable_statistics,
            'max_threads': self.max_threads,
            'default_stack_size': self.default_stack_size,
            'scheduler_quantum': self.scheduler_quantum,
            'enable_dep': self.enable_dep,
            'enable_aslr': self.enable_aslr,
            'enable_stack_canaries': self.enable_stack_canaries,
            'default_privilege_level': self.default_privilege_level,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VMConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def save(self, filename: str) -> None:
        """Save configuration to file."""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filename: str) -> 'VMConfig':
        """Load configuration from file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def update(self, **kwargs) -> None:
        """Update configuration with keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.metadata[key] = value


@dataclass
class ParallelVMConfig(VMConfig):
    """Configuration for parallel computing VMs."""
    
    num_processors: int = 4
    enable_race_detection: bool = True
    enable_deadlock_detection: bool = True
    scheduler_type: str = "round_robin"
    enable_cache_coherence: bool = True
    coherence_protocol: str = "MESI"
    
    # Synchronization settings
    max_locks: int = 100
    max_semaphores: int = 50
    max_barriers: int = 20
    
    # Thread affinity
    enable_affinity: bool = False
    affinity_policy: str = "balanced"


@dataclass
class SecureVMConfig(VMConfig):
    """Configuration for security-focused VMs."""
    
    enable_memory_protection: bool = True
    enable_dep: bool = True
    enable_aslr: bool = True
    enable_stack_canaries: bool = True
    
    # Security levels
    max_privilege_level: int = 3
    enforce_privilege_separation: bool = True
    
    # Memory segmentation
    code_segment_size: int = 16384
    data_segment_size: int = 16384
    stack_segment_size: int = 8192
    heap_segment_size: int = 24576
    
    # Attack mitigation
    enable_control_flow_integrity: bool = True
    enable_shadow_stack: bool = True
    enable_forensic_logging: bool = True
    
    # Sandbox settings
    enable_sandboxing: bool = False
    sandbox_memory_limit: int = 32768
    allowed_syscalls: list = field(default_factory=list)


class ConfigManager:
    """Manage multiple configurations."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.configs: Dict[str, VMConfig] = {}
        self.active_config: Optional[str] = None
        
    def add_config(self, name: str, config: VMConfig) -> None:
        """Add a configuration."""
        self.configs[name] = config
        
        if self.active_config is None:
            self.active_config = name
    
    def get_config(self, name: Optional[str] = None) -> Optional[VMConfig]:
        """Get a configuration."""
        if name is None:
            name = self.active_config
        
        return self.configs.get(name) if name else None
    
    def set_active(self, name: str) -> bool:
        """Set active configuration."""
        if name in self.configs:
            self.active_config = name
            return True
        return False
    
    def create_default_configs(self) -> None:
        """Create default configurations."""
        # Basic VM config
        self.add_config("basic", VMConfig())
        
        # Parallel VM config
        self.add_config("parallel", ParallelVMConfig())
        
        # Secure VM config
        self.add_config("secure", SecureVMConfig())
        
        # Debug config
        debug_config = VMConfig(debug=True, enable_tracing=True)
        self.add_config("debug", debug_config)
        
        # Performance config
        perf_config = VMConfig(
            enable_tracing=False,
            enable_statistics=True,
            max_cycles=10000000
        )
        self.add_config("performance", perf_config)