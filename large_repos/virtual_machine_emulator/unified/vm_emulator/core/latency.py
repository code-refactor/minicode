"""Configurable communication latency for the VM."""

import random
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Any, Union


class LatencyType(Enum):
    """Types of communication latency."""
    MEMORY_READ = auto()        # Memory read latency
    MEMORY_WRITE = auto()       # Memory write latency
    CACHE_COHERENCE = auto()    # Cache coherence protocol latency
    LOCK_ACQUIRE = auto()       # Lock acquisition latency
    LOCK_RELEASE = auto()       # Lock release latency
    BARRIER_WAIT = auto()       # Barrier wait latency
    THREAD_CREATION = auto()    # Thread creation latency
    THREAD_SCHEDULING = auto()  # Thread scheduling latency
    CONTEXT_SWITCH = auto()     # Context switch latency
    INTERRUPT = auto()          # Interrupt handling latency


class LatencyModel(Enum):
    """Types of latency models."""
    FIXED = auto()            # Fixed latency value
    UNIFORM = auto()          # Uniform random distribution
    NORMAL = auto()           # Normal (Gaussian) distribution
    EXPONENTIAL = auto()      # Exponential distribution
    NETWORK = auto()          # Network topology-based model
    NUMA = auto()             # NUMA architecture model
    CUSTOM = auto()           # Custom latency function


class LatencyConfiguration:
    """
    Configures and manages communication latencies in the VM.
    
    Allows setting different latency models for various types of
    communication, such as memory access, thread scheduling,
    and synchronization operations.
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize the latency configuration.
        
        Args:
            random_seed: Seed for deterministic latency generation
        """
        self.random_seed = random_seed
        
        if random_seed is not None:
            random.seed(random_seed)
        
        # Default latency configurations
        self.latency_configs: Dict[LatencyType, Dict[str, Any]] = {}
        
        # Set default configurations
        self._set_defaults()
        
        # Network topology for NETWORK model
        self.network_topology: Dict[Tuple[int, int], int] = {}
        
        # NUMA configuration for NUMA model
        self.numa_nodes: Dict[int, int] = {}  # processor_id -> node_id
        self.numa_distances: Dict[Tuple[int, int], int] = {}  # (node1, node2) -> distance
        
        # Custom latency functions
        self.custom_functions: Dict[LatencyType, callable] = {}
    
    def _set_defaults(self) -> None:
        """Set default latency configurations."""
        # Memory read latency: fixed 2 cycles
        self.latency_configs[LatencyType.MEMORY_READ] = {
            "model": LatencyModel.FIXED,
            "value": 2,
        }
        
        # Memory write latency: fixed 2 cycles
        self.latency_configs[LatencyType.MEMORY_WRITE] = {
            "model": LatencyModel.FIXED,
            "value": 2,
        }
        
        # Cache coherence latency: fixed 5 cycles
        self.latency_configs[LatencyType.CACHE_COHERENCE] = {
            "model": LatencyModel.FIXED,
            "value": 5,
        }
        
        # Lock acquisition latency: fixed 1 cycle
        self.latency_configs[LatencyType.LOCK_ACQUIRE] = {
            "model": LatencyModel.FIXED,
            "value": 1,
        }
        
        # Lock release latency: fixed 1 cycle
        self.latency_configs[LatencyType.LOCK_RELEASE] = {
            "model": LatencyModel.FIXED,
            "value": 1,
        }
        
        # Barrier wait latency: fixed 5 cycles
        self.latency_configs[LatencyType.BARRIER_WAIT] = {
            "model": LatencyModel.FIXED,
            "value": 5,
        }
        
        # Thread creation latency: fixed 10 cycles
        self.latency_configs[LatencyType.THREAD_CREATION] = {
            "model": LatencyModel.FIXED,
            "value": 10,
        }
        
        # Thread scheduling latency: fixed 5 cycles
        self.latency_configs[LatencyType.THREAD_SCHEDULING] = {
            "model": LatencyModel.FIXED,
            "value": 5,
        }
        
        # Context switch latency: fixed 3 cycles
        self.latency_configs[LatencyType.CONTEXT_SWITCH] = {
            "model": LatencyModel.FIXED,
            "value": 3,
        }
        
        # Interrupt latency: fixed 2 cycles
        self.latency_configs[LatencyType.INTERRUPT] = {
            "model": LatencyModel.FIXED,
            "value": 2,
        }
    
    def set_fixed_latency(self, latency_type: LatencyType, value: int) -> None:
        """
        Set a fixed latency value.
        
        Args:
            latency_type: Type of latency
            value: Fixed latency value in cycles
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.FIXED,
            "value": value,
        }
    
    def set_uniform_latency(
        self, latency_type: LatencyType, min_value: int, max_value: int
    ) -> None:
        """
        Set a uniform random latency distribution.
        
        Args:
            latency_type: Type of latency
            min_value: Minimum latency value in cycles
            max_value: Maximum latency value in cycles
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.UNIFORM,
            "min_value": min_value,
            "max_value": max_value,
        }
    
    def set_normal_latency(
        self, latency_type: LatencyType, mean: float, std_dev: float
    ) -> None:
        """
        Set a normal (Gaussian) latency distribution.
        
        Args:
            latency_type: Type of latency
            mean: Mean latency value in cycles
            std_dev: Standard deviation of latency
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.NORMAL,
            "mean": mean,
            "std_dev": std_dev,
        }
    
    def set_exponential_latency(
        self, latency_type: LatencyType, mean: float
    ) -> None:
        """
        Set an exponential latency distribution.
        
        Args:
            latency_type: Type of latency
            mean: Mean latency value in cycles
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.EXPONENTIAL,
            "mean": mean,
        }
    
    def set_network_topology(
        self, processor_distances: Dict[Tuple[int, int], int]
    ) -> None:
        """
        Set network topology for the NETWORK latency model.
        
        Args:
            processor_distances: Dictionary of (processor1, processor2) -> distance
        """
        self.network_topology = processor_distances.copy()
    
    def set_network_latency(
        self, latency_type: LatencyType, base_latency: int, distance_factor: float
    ) -> None:
        """
        Set network topology-based latency model.
        
        Args:
            latency_type: Type of latency
            base_latency: Base latency value in cycles
            distance_factor: Factor to multiply distance by
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.NETWORK,
            "base_latency": base_latency,
            "distance_factor": distance_factor,
        }
    
    def set_numa_configuration(
        self, processor_nodes: Dict[int, int], node_distances: Dict[Tuple[int, int], int]
    ) -> None:
        """
        Set NUMA configuration for the NUMA latency model.
        
        Args:
            processor_nodes: Dictionary of processor_id -> node_id
            node_distances: Dictionary of (node1, node2) -> distance
        """
        self.numa_nodes = processor_nodes.copy()
        self.numa_distances = node_distances.copy()
    
    def set_numa_latency(
        self, latency_type: LatencyType, base_latency: int, distance_factor: float
    ) -> None:
        """
        Set NUMA architecture-based latency model.
        
        Args:
            latency_type: Type of latency
            base_latency: Base latency value in cycles
            distance_factor: Factor to multiply NUMA distance by
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.NUMA,
            "base_latency": base_latency,
            "distance_factor": distance_factor,
        }
    
    def set_custom_latency(
        self, latency_type: LatencyType, latency_function: callable
    ) -> None:
        """
        Set a custom latency function.
        
        Args:
            latency_type: Type of latency
            latency_function: Function taking (src, dst, **kwargs) and returning latency
        """
        self.latency_configs[latency_type] = {
            "model": LatencyModel.CUSTOM,
        }
        self.custom_functions[latency_type] = latency_function
    
    def get_latency(
        self,
        latency_type: LatencyType,
        src: Optional[int] = None,
        dst: Optional[int] = None,
        **kwargs,
    ) -> int:
        """
        Get latency for a specific operation.
        
        Args:
            latency_type: Type of latency
            src: Source processor ID
            dst: Destination processor ID
            **kwargs: Additional parameters for custom latency functions
            
        Returns:
            Latency in cycles
        """
        if latency_type not in self.latency_configs:
            # Use default if not configured
            return 1
        
        config = self.latency_configs[latency_type]
        model = config["model"]
        
        if model == LatencyModel.FIXED:
            return config["value"]
        
        elif model == LatencyModel.UNIFORM:
            return random.randint(config["min_value"], config["max_value"])
        
        elif model == LatencyModel.NORMAL:
            # Ensure non-negative latency
            latency = max(1, int(random.normalvariate(config["mean"], config["std_dev"])))
            return latency
        
        elif model == LatencyModel.EXPONENTIAL:
            # Ensure non-negative latency
            latency = max(1, int(random.expovariate(1 / config["mean"])))
            return latency
        
        elif model == LatencyModel.NETWORK:
            if src is None or dst is None:
                return config["base_latency"]
            
            # Get distance from network topology
            distance = self.network_topology.get((src, dst), 1)
            
            # Calculate latency based on distance
            latency = config["base_latency"] + int(distance * config["distance_factor"])
            return latency
        
        elif model == LatencyModel.NUMA:
            if src is None or dst is None:
                return config["base_latency"]
            
            # Get NUMA nodes
            src_node = self.numa_nodes.get(src, 0)
            dst_node = self.numa_nodes.get(dst, 0)
            
            # Get NUMA distance
            distance = self.numa_distances.get((src_node, dst_node), 1)
            
            # Calculate latency based on NUMA distance
            latency = config["base_latency"] + int(distance * config["distance_factor"])
            return latency
        
        elif model == LatencyModel.CUSTOM:
            if latency_type in self.custom_functions:
                return self.custom_functions[latency_type](src, dst, **kwargs)
            return 1
        
        # Default
        return 1
    
    def get_memory_latency(
        self,
        is_write: bool,
        processor_id: Optional[int] = None,
        address: Optional[int] = None,
        **kwargs,
    ) -> int:
        """
        Get memory access latency.
        
        Args:
            is_write: Whether it's a write operation
            processor_id: Processor performing the access
            address: Memory address being accessed
            **kwargs: Additional parameters
            
        Returns:
            Latency in cycles
        """
        latency_type = LatencyType.MEMORY_WRITE if is_write else LatencyType.MEMORY_READ
        return self.get_latency(latency_type, processor_id, None, address=address, **kwargs)
    
    def get_coherence_latency(
        self,
        operation: str,
        src_processor: int,
        dst_processor: int,
        **kwargs,
    ) -> int:
        """
        Get cache coherence protocol latency.
        
        Args:
            operation: Type of coherence operation
            src_processor: Source processor ID
            dst_processor: Destination processor ID
            **kwargs: Additional parameters
            
        Returns:
            Latency in cycles
        """
        return self.get_latency(
            LatencyType.CACHE_COHERENCE, src_processor, dst_processor,
            operation=operation, **kwargs
        )
    
    def get_sync_latency(
        self,
        sync_type: str,
        operation: str,
        processor_id: Optional[int] = None,
        **kwargs,
    ) -> int:
        """
        Get synchronization operation latency.
        
        Args:
            sync_type: Type of synchronization primitive
            operation: Type of operation
            processor_id: Processor performing the operation
            **kwargs: Additional parameters
            
        Returns:
            Latency in cycles
        """
        if sync_type == "lock" and operation == "acquire":
            latency_type = LatencyType.LOCK_ACQUIRE
        elif sync_type == "lock" and operation == "release":
            latency_type = LatencyType.LOCK_RELEASE
        elif sync_type == "barrier":
            latency_type = LatencyType.BARRIER_WAIT
        else:
            # Default to lock acquire for other sync types
            latency_type = LatencyType.LOCK_ACQUIRE
        
        return self.get_latency(
            latency_type, processor_id, None,
            sync_type=sync_type, operation=operation, **kwargs
        )
    
    def get_thread_latency(
        self,
        operation: str,
        processor_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        **kwargs,
    ) -> int:
        """
        Get thread operation latency.
        
        Args:
            operation: Type of thread operation
            processor_id: Processor performing the operation
            thread_id: Thread being operated on
            **kwargs: Additional parameters
            
        Returns:
            Latency in cycles
        """
        if operation == "create":
            latency_type = LatencyType.THREAD_CREATION
        elif operation == "schedule":
            latency_type = LatencyType.THREAD_SCHEDULING
        elif operation == "context_switch":
            latency_type = LatencyType.CONTEXT_SWITCH
        else:
            # Default to thread creation for other operations
            latency_type = LatencyType.THREAD_CREATION
        
        return self.get_latency(
            latency_type, processor_id, None,
            operation=operation, thread_id=thread_id, **kwargs
        )
    
    def get_latency_configuration(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the current latency configuration.
        
        Returns:
            Dictionary of latency configurations
        """
        result = {}
        
        for latency_type, config in self.latency_configs.items():
            result[latency_type.name] = {
                "model": config["model"].name,
                **{k: v for k, v in config.items() if k != "model"},
            }
        
        return result
    
    def reset(self) -> None:
        """Reset to default latency configuration."""
        self.latency_configs = {}
        self.network_topology = {}
        self.numa_nodes = {}
        self.numa_distances = {}
        self.custom_functions = {}
        
        self._set_defaults()


class LatencyProfiler:
    """
    Profiles and analyzes communication latencies.
    
    Records and analyzes actual latencies observed during execution,
    and can recommend latency configuration adjustments.
    """
    
    def __init__(self, latency_config: LatencyConfiguration):
        """
        Initialize the latency profiler.
        
        Args:
            latency_config: Latency configuration to profile
        """
        self.latency_config = latency_config
        
        # Latency records
        self.latency_records: Dict[LatencyType, List[Dict[str, Any]]] = {}
        
        # Initialize latency records for each type
        for latency_type in LatencyType:
            self.latency_records[latency_type] = []
        
        # Analysis results
        self.analysis_results: Dict[str, Any] = {}
        
        # Whether analysis is up to date
        self.is_analyzed = False
    
    def record_latency(
        self,
        latency_type: LatencyType,
        cycles: int,
        src: Optional[int] = None,
        dst: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Record an observed latency.
        
        Args:
            latency_type: Type of latency
            cycles: Observed latency in cycles
            src: Source processor ID
            dst: Destination processor ID
            **kwargs: Additional parameters
        """
        record = {
            "type": latency_type,
            "cycles": cycles,
            "src": src,
            "dst": dst,
            **kwargs,
        }
        
        self.latency_records[latency_type].append(record)
        
        # Mark analysis as out of date
        self.is_analyzed = False
    
    def analyze(self) -> None:
        """Analyze recorded latencies."""
        if self.is_analyzed:
            return
        
        results = {}
        
        # Analyze each latency type
        for latency_type, records in self.latency_records.items():
            if not records:
                results[latency_type.name] = {
                    "count": 0,
                    "insufficient_data": True,
                }
                continue
            
            # Calculate statistics
            latencies = [record["cycles"] for record in records]
            
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            # Calculate variance and standard deviation
            variance = sum((l - avg_latency) ** 2 for l in latencies) / len(latencies)
            std_dev = variance ** 0.5
            
            # Check if current configuration matches observed latencies
            config = self.latency_config.latency_configs.get(latency_type)
            
            config_matches = False
            recommendation = None
            
            if config:
                model = config["model"]
                
                if model == LatencyModel.FIXED:
                    # Check if fixed value matches average
                    config_matches = abs(config["value"] - avg_latency) <= 1
                    
                    if not config_matches:
                        recommendation = {
                            "model": LatencyModel.FIXED.name,
                            "value": int(avg_latency),
                        }
                
                elif model == LatencyModel.UNIFORM:
                    # Check if min/max match
                    config_matches = (
                        abs(config["min_value"] - min_latency) <= 1 and
                        abs(config["max_value"] - max_latency) <= 1
                    )
                    
                    if not config_matches:
                        recommendation = {
                            "model": LatencyModel.UNIFORM.name,
                            "min_value": int(min_latency),
                            "max_value": int(max_latency),
                        }
                
                elif model == LatencyModel.NORMAL:
                    # Check if mean and std_dev match
                    config_matches = (
                        abs(config["mean"] - avg_latency) <= 1 and
                        abs(config["std_dev"] - std_dev) <= 1
                    )
                    
                    if not config_matches:
                        recommendation = {
                            "model": LatencyModel.NORMAL.name,
                            "mean": avg_latency,
                            "std_dev": std_dev,
                        }
                
                # Other models have similar checks
            
            # If no configuration or doesn't match, recommend one
            if not config or not config_matches:
                if not recommendation:
                    # Default recommendation based on variance
                    if std_dev < 0.5:
                        recommendation = {
                            "model": LatencyModel.FIXED.name,
                            "value": int(avg_latency),
                        }
                    elif min_latency == max_latency:
                        recommendation = {
                            "model": LatencyModel.FIXED.name,
                            "value": int(min_latency),
                        }
                    else:
                        recommendation = {
                            "model": LatencyModel.UNIFORM.name,
                            "min_value": int(min_latency),
                            "max_value": int(max_latency),
                        }
            
            # Record results
            results[latency_type.name] = {
                "count": len(records),
                "min": min_latency,
                "max": max_latency,
                "avg": avg_latency,
                "std_dev": std_dev,
                "config_matches": config_matches,
                "recommendation": recommendation,
            }
        
        # Store analysis results
        self.analysis_results = results
        self.is_analyzed = True
    
    def get_latency_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for recorded latencies.
        
        Returns:
            Dictionary of latency statistics
        """
        self.analyze()
        return self.analysis_results
    
    def get_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get latency configuration recommendations.
        
        Returns:
            Dictionary of recommendations
        """
        self.analyze()
        
        recommendations = {}
        
        for latency_type_name, results in self.analysis_results.items():
            if "recommendation" in results and results["recommendation"]:
                recommendations[latency_type_name] = results["recommendation"]
        
        return recommendations
    
    def apply_recommendations(self) -> None:
        """Apply recommendations to the latency configuration."""
        recommendations = self.get_recommendations()
        
        for latency_type_name, recommendation in recommendations.items():
            latency_type = getattr(LatencyType, latency_type_name)
            
            model_name = recommendation["model"]
            model = getattr(LatencyModel, model_name)
            
            if model == LatencyModel.FIXED:
                self.latency_config.set_fixed_latency(
                    latency_type, recommendation["value"]
                )
            
            elif model == LatencyModel.UNIFORM:
                self.latency_config.set_uniform_latency(
                    latency_type,
                    recommendation["min_value"],
                    recommendation["max_value"]
                )
            
            elif model == LatencyModel.NORMAL:
                self.latency_config.set_normal_latency(
                    latency_type,
                    recommendation["mean"],
                    recommendation["std_dev"]
                )
            
            # Other models follow similar patterns
    
    def reset(self) -> None:
        """Reset the profiler."""
        for latency_type in LatencyType:
            self.latency_records[latency_type] = []
        
        self.analysis_results = {}
        self.is_analyzed = False