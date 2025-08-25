"""
A/B testing implementation for ML model experimentation.

This module provides functionality for consistent assignment of entities to
experimental groups, with support for traffic allocation, outcome tracking,
and statistical analysis.
"""

import hashlib
import json
import time
import random
import math
import threading
from typing import Dict, List, Set, Tuple, Optional, Any, Union, Callable
from collections import defaultdict
import statistics


class ExperimentGroup:
    """
    Represents an experimental group in an A/B test.
    
    This class manages a group in an experiment, tracking assignments,
    outcomes, and metadata for the group.
    """
    
    def __init__(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        allocation: float = 0.0,  # Percentage of traffic allocated to this group
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an experiment group.
        
        Args:
            group_id: Unique identifier for this group
            name: Optional display name for this group
            description: Optional description of this group
            allocation: Traffic allocation percentage (0.0 to 1.0)
            metadata: Optional additional metadata
        """
        self._group_id = group_id
        self._name = name or group_id
        self._description = description
        self._allocation = max(0.0, min(1.0, allocation))  # Clamp to [0, 1]
        self._metadata = metadata or {}
        
        # Track assignments and outcomes
        self._entities: Set[str] = set()
        self._outcomes: Dict[str, Dict[str, Any]] = {}
        
        # Track creation and modification times
        self._created_at = time.time()
        self._last_modified = self._created_at
    
    @property
    def group_id(self) -> str:
        """Get the group ID."""
        return self._group_id
    
    @property
    def name(self) -> str:
        """Get the group name."""
        return self._name
    
    @property
    def description(self) -> Optional[str]:
        """Get the group description."""
        return self._description
    
    @property
    def allocation(self) -> float:
        """Get the traffic allocation percentage."""
        return self._allocation
    
    @allocation.setter
    def allocation(self, value: float) -> None:
        """Set the traffic allocation percentage."""
        self._allocation = max(0.0, min(1.0, value))
        self._last_modified = time.time()
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the group metadata."""
        return self._metadata.copy()
    
    @property
    def created_at(self) -> float:
        """Get the creation timestamp."""
        return self._created_at
    
    @property
    def last_modified(self) -> float:
        """Get the last modification timestamp."""
        return self._last_modified
    
    @property
    def entity_count(self) -> int:
        """Get the number of entities assigned to this group."""
        return len(self._entities)
    
    @property
    def outcome_count(self) -> int:
        """Get the number of entities with outcomes in this group."""
        return len(self._outcomes)
    
    def has_entity(self, entity_id: str) -> bool:
        """
        Check if an entity is assigned to this group.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            True if the entity is in this group, False otherwise
        """
        return entity_id in self._entities
    
    def add_entity(self, entity_id: str) -> None:
        """
        Add an entity to this group.
        
        Args:
            entity_id: ID of the entity to add
        """
        self._entities.add(entity_id)
        self._last_modified = time.time()
    
    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove an entity from this group.
        
        Args:
            entity_id: ID of the entity to remove
            
        Returns:
            True if the entity was removed, False if it wasn't in this group
        """
        if entity_id in self._entities:
            self._entities.remove(entity_id)
            
            # Also remove any outcomes for this entity
            if entity_id in self._outcomes:
                del self._outcomes[entity_id]
                
            self._last_modified = time.time()
            return True
        return False
    
    def get_entities(self) -> List[str]:
        """
        Get all entities assigned to this group.
        
        Returns:
            List of entity IDs
        """
        return list(self._entities)
    
    def record_outcome(
        self,
        entity_id: str,
        outcome_value: Any,
        outcome_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Record an outcome for an entity in this group.
        
        Args:
            entity_id: ID of the entity
            outcome_value: The outcome value
            outcome_type: Optional type of outcome
            metadata: Optional additional metadata
            timestamp: Optional timestamp (default: current time)
            
        Returns:
            True if the outcome was recorded, False if the entity is not in this group
        """
        if entity_id not in self._entities:
            return False
        
        self._outcomes[entity_id] = {
            "value": outcome_value,
            "type": outcome_type,
            "timestamp": timestamp or time.time(),
            "metadata": metadata or {}
        }
        
        self._last_modified = time.time()
        return True
    
    def get_outcome(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the outcome for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Outcome dictionary if found, None otherwise
        """
        return self._outcomes.get(entity_id)
    
    def get_outcomes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all outcomes for this group.
        
        Returns:
            Dictionary mapping entity ID to outcome data
        """
        return self._outcomes.copy()
    
    def get_outcome_values(self, outcome_type: Optional[str] = None) -> List[Any]:
        """
        Get all outcome values for this group, optionally filtered by type.
        
        Args:
            outcome_type: Optional type to filter by
            
        Returns:
            List of outcome values
        """
        values = []
        for entity_id, outcome in self._outcomes.items():
            if outcome_type is None or outcome.get("type") == outcome_type:
                values.append(outcome["value"])
        return values
    
    def calculate_statistics(self, outcome_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate statistics for the outcomes in this group.
        
        Args:
            outcome_type: Optional type to filter by
            
        Returns:
            Dictionary of statistics
        """
        values = self.get_outcome_values(outcome_type)
        
        # Check if values are numeric
        if not values:
            return {"count": 0}
        
        numeric_values = []
        for v in values:
            if isinstance(v, (int, float)):
                numeric_values.append(v)
        
        if not numeric_values:
            return {"count": len(values)}
        
        # Calculate statistics for numeric values
        stats = {
            "count": len(numeric_values),
            "mean": statistics.mean(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values)
        }
        
        # Calculate additional statistics if we have enough values
        if len(numeric_values) > 1:
            stats["median"] = statistics.median(numeric_values)
            stats["stdev"] = statistics.stdev(numeric_values)
            stats["variance"] = statistics.variance(numeric_values)
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this group to a dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "group_id": self._group_id,
            "name": self._name,
            "description": self._description,
            "allocation": self._allocation,
            "metadata": self._metadata,
            "entities": list(self._entities),
            "outcomes": self._outcomes,
            "created_at": self._created_at,
            "last_modified": self._last_modified
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentGroup':
        """
        Create a group from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            A new ExperimentGroup instance
        """
        group = cls(
            group_id=data["group_id"],
            name=data.get("name"),
            description=data.get("description"),
            allocation=data.get("allocation", 0.0),
            metadata=data.get("metadata", {})
        )
        
        # Restore entities
        for entity_id in data.get("entities", []):
            group.add_entity(entity_id)
        
        # Restore outcomes
        group._outcomes = data.get("outcomes", {})
        
        # Restore timestamps
        group._created_at = data.get("created_at", time.time())
        group._last_modified = data.get("last_modified", time.time())
        
        return group


class ABTester:
    """
    A/B testing system for experimental group assignment and analysis.
    
    This class provides functionality for consistent assignment of entities
    to experimental groups, with support for traffic allocation, outcome tracking,
    and statistical analysis.
    """
    
    def __init__(
        self,
        experiment_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        groups: Optional[Dict[str, ExperimentGroup]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        salt: Optional[str] = None
    ):
        """
        Initialize an A/B tester.
        
        Args:
            experiment_id: Unique identifier for this experiment
            name: Optional display name for this experiment
            description: Optional description of this experiment
            groups: Optional mapping of group IDs to ExperimentGroup instances
            metadata: Optional additional metadata
            salt: Optional salt for hashing (default: experiment_id)
        """
        self._experiment_id = experiment_id
        self._name = name or experiment_id
        self._description = description
        self._metadata = metadata or {}
        self._salt = salt or experiment_id
        
        # Initialize groups
        self._groups: Dict[str, ExperimentGroup] = {}
        if groups:
            self._groups.update(groups)
        
        # Track creation and modification times
        self._created_at = time.time()
        self._last_modified = self._created_at
        
        # For thread safety
        self._lock = threading.RLock()
    
    @property
    def experiment_id(self) -> str:
        """Get the experiment ID."""
        return self._experiment_id
    
    @property
    def name(self) -> str:
        """Get the experiment name."""
        return self._name
    
    @property
    def description(self) -> Optional[str]:
        """Get the experiment description."""
        return self._description
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get the experiment metadata."""
        return self._metadata.copy()
    
    @property
    def salt(self) -> str:
        """Get the salt used for hashing."""
        return self._salt
    
    @property
    def created_at(self) -> float:
        """Get the creation timestamp."""
        return self._created_at
    
    @property
    def last_modified(self) -> float:
        """Get the last modification timestamp."""
        return self._last_modified
    
    def add_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        allocation: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExperimentGroup:
        """
        Add a new group to the experiment.
        
        Args:
            group_id: Unique identifier for the group
            name: Optional display name for the group
            description: Optional description of the group
            allocation: Traffic allocation percentage (0.0 to 1.0)
            metadata: Optional additional metadata
            
        Returns:
            The created ExperimentGroup
            
        Raises:
            ValueError: If a group with the same ID already exists
        """
        with self._lock:
            if group_id in self._groups:
                raise ValueError(f"Group with ID '{group_id}' already exists")
            
            group = ExperimentGroup(
                group_id=group_id,
                name=name,
                description=description,
                allocation=allocation,
                metadata=metadata
            )
            
            self._groups[group_id] = group
            self._last_modified = time.time()
            
            return group
    
    def get_group(self, group_id: str) -> Optional[ExperimentGroup]:
        """
        Get a group by its ID.
        
        Args:
            group_id: ID of the group
            
        Returns:
            The ExperimentGroup if found, None otherwise
        """
        with self._lock:
            return self._groups.get(group_id)
    
    def remove_group(self, group_id: str) -> bool:
        """
        Remove a group from the experiment.
        
        Args:
            group_id: ID of the group to remove
            
        Returns:
            True if the group was removed, False if it wasn't found
        """
        with self._lock:
            if group_id in self._groups:
                del self._groups[group_id]
                self._last_modified = time.time()
                return True
            return False
    
    def get_groups(self) -> Dict[str, ExperimentGroup]:
        """
        Get all groups in the experiment.
        
        Returns:
            Dictionary mapping group IDs to ExperimentGroup instances
        """
        with self._lock:
            return self._groups.copy()
    
    def set_allocations(self, allocations: Dict[str, float]) -> None:
        """
        Set traffic allocations for multiple groups.
        
        Args:
            allocations: Mapping of group ID to allocation percentage (0.0 to 1.0)
            
        Raises:
            ValueError: If the total allocation exceeds 1.0
        """
        with self._lock:
            # Check that total allocation doesn't exceed 100%
            total = sum(allocations.values())
            if total > 1.0:
                raise ValueError(f"Total allocation ({total}) exceeds 1.0")
            
            # Update allocations for existing groups
            for group_id, allocation in allocations.items():
                if group_id in self._groups:
                    self._groups[group_id].allocation = allocation
            
            self._last_modified = time.time()
    
    def assign_entity(self, entity_id: str, force_group: Optional[str] = None) -> Optional[str]:
        """
        Assign an entity to an experiment group.
        
        Args:
            entity_id: ID of the entity to assign
            force_group: Optional group ID to force assignment to
            
        Returns:
            The ID of the assigned group, or None if no assignment was made
            
        Note:
            If force_group is provided, the entity will be assigned to that group
            regardless of the hash value or allocation percentage.
        """
        with self._lock:
            # If no groups, no assignment
            if not self._groups:
                return None
            
            # If forcing a specific group
            if force_group is not None:
                if force_group in self._groups:
                    self._groups[force_group].add_entity(entity_id)
                    return force_group
                return None
            
            # Get group assignments and allocations
            assignments = []
            total_allocation = 0.0
            
            for group_id, group in self._groups.items():
                allocation = group.allocation
                total_allocation += allocation
                assignments.append((group_id, allocation))
            
            # Normalize allocations if needed
            if total_allocation > 0:
                assignments = [(gid, alloc / total_allocation) for gid, alloc in assignments]
            else:
                # If no allocation, assign randomly
                group_id = random.choice(list(self._groups.keys()))
                self._groups[group_id].add_entity(entity_id)
                return group_id
            
            # Generate a deterministic hash value for this entity
            hash_input = f"{self._salt}:{entity_id}"
            hash_bytes = hashlib.md5(hash_input.encode('utf-8')).digest()
            hash_value = int.from_bytes(hash_bytes, byteorder='big') / (2 ** 128)  # Value between 0 and 1
            
            # Find the assigned group based on the hash value
            cumulative = 0.0
            for group_id, allocation in assignments:
                cumulative += allocation
                if hash_value < cumulative:
                    # Assign to this group
                    self._groups[group_id].add_entity(entity_id)
                    return group_id
            
            # If we reach here, assign to the last group
            if assignments:
                last_group_id = assignments[-1][0]
                self._groups[last_group_id].add_entity(entity_id)
                return last_group_id
            
            return None
    
    def assign_entities(self, entity_ids: List[str]) -> Dict[str, Optional[str]]:
        """
        Assign multiple entities to experiment groups.
        
        Args:
            entity_ids: List of entity IDs to assign
            
        Returns:
            Dictionary mapping entity IDs to assigned group IDs
        """
        with self._lock:
            result = {}
            for entity_id in entity_ids:
                result[entity_id] = self.assign_entity(entity_id)
            return result
    
    def get_entity_group(self, entity_id: str) -> Optional[str]:
        """
        Get the group ID for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            The ID of the assigned group, or None if not assigned
        """
        with self._lock:
            for group_id, group in self._groups.items():
                if group.has_entity(entity_id):
                    return group_id
            return None
    
    def record_outcome(
        self,
        entity_id: str,
        outcome_value: Any,
        outcome_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Record an outcome for an entity.
        
        Args:
            entity_id: ID of the entity
            outcome_value: The outcome value
            outcome_type: Optional type of outcome
            metadata: Optional additional metadata
            timestamp: Optional timestamp (default: current time)
            
        Returns:
            True if the outcome was recorded, False if the entity is not assigned to a group
        """
        with self._lock:
            # Find the group for this entity
            group_id = self.get_entity_group(entity_id)
            if group_id is None:
                return False
            
            # Record the outcome in the group
            return self._groups[group_id].record_outcome(
                entity_id=entity_id,
                outcome_value=outcome_value,
                outcome_type=outcome_type,
                metadata=metadata,
                timestamp=timestamp
            )
    
    def get_outcome(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the outcome for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Outcome dictionary if found, None otherwise
        """
        with self._lock:
            group_id = self.get_entity_group(entity_id)
            if group_id is None:
                return None
            
            return self._groups[group_id].get_outcome(entity_id)
    
    def get_outcomes_by_group(self, outcome_type: Optional[str] = None) -> Dict[str, List[Any]]:
        """
        Get outcomes grouped by experiment group.
        
        Args:
            outcome_type: Optional type to filter by
            
        Returns:
            Dictionary mapping group IDs to lists of outcome values
        """
        with self._lock:
            result = {}
            for group_id, group in self._groups.items():
                result[group_id] = group.get_outcome_values(outcome_type)
            return result
    
    def calculate_statistics(
        self,
        outcome_type: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate statistics for outcomes by group.
        
        Args:
            outcome_type: Optional type to filter by
            
        Returns:
            Dictionary mapping group IDs to statistics dictionaries
        """
        with self._lock:
            result = {}
            for group_id, group in self._groups.items():
                result[group_id] = group.calculate_statistics(outcome_type)
            return result
    
    def calculate_lift(
        self,
        control_group_id: str,
        test_group_id: str,
        outcome_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate lift between a test group and a control group.
        
        Args:
            control_group_id: ID of the control group
            test_group_id: ID of the test group
            outcome_type: Optional type to filter by
            
        Returns:
            Dictionary with lift metrics
            
        Raises:
            ValueError: If either group doesn't exist
        """
        with self._lock:
            if control_group_id not in self._groups:
                raise ValueError(f"Control group '{control_group_id}' not found")
            if test_group_id not in self._groups:
                raise ValueError(f"Test group '{test_group_id}' not found")
            
            control_stats = self._groups[control_group_id].calculate_statistics(outcome_type)
            test_stats = self._groups[test_group_id].calculate_statistics(outcome_type)
            
            # If either group has no outcomes, we can't calculate lift
            if control_stats.get("count", 0) == 0 or test_stats.get("count", 0) == 0:
                return {"error": "One or both groups have no outcomes"}
            
            # Calculate relative lift
            control_mean = control_stats.get("mean")
            test_mean = test_stats.get("mean")
            
            if control_mean is None or test_mean is None:
                return {"error": "Cannot calculate lift for non-numeric outcomes"}
            
            if math.isclose(control_mean, 0):
                relative_lift = float('inf') if test_mean > 0 else float('-inf')
            else:
                relative_lift = (test_mean - control_mean) / control_mean
            
            absolute_lift = test_mean - control_mean
            
            # Calculate confidence interval if we have standard deviations
            confidence_interval = None
            if "stdev" in control_stats and "stdev" in test_stats:
                control_stdev = control_stats["stdev"]
                test_stdev = test_stats["stdev"]
                control_count = control_stats["count"]
                test_count = test_stats["count"]
                
                # Standard error of the difference in means
                se_diff = math.sqrt((control_stdev ** 2 / control_count) + (test_stdev ** 2 / test_count))
                
                # 95% confidence interval (1.96 standard errors)
                margin = 1.96 * se_diff
                confidence_interval = (absolute_lift - margin, absolute_lift + margin)
            
            return {
                "control_mean": control_mean,
                "test_mean": test_mean,
                "absolute_lift": absolute_lift,
                "relative_lift": relative_lift,
                "confidence_interval": confidence_interval,
                "control_count": control_stats.get("count", 0),
                "test_count": test_stats.get("count", 0)
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this A/B tester to a dictionary.
        
        Returns:
            Dictionary representation
        """
        with self._lock:
            return {
                "experiment_id": self._experiment_id,
                "name": self._name,
                "description": self._description,
                "metadata": self._metadata,
                "salt": self._salt,
                "created_at": self._created_at,
                "last_modified": self._last_modified,
                "groups": {
                    group_id: group.to_dict()
                    for group_id, group in self._groups.items()
                }
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ABTester':
        """
        Create an A/B tester from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            A new ABTester instance
        """
        tester = cls(
            experiment_id=data["experiment_id"],
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
            salt=data.get("salt")
        )
        
        # Restore timestamps
        tester._created_at = data.get("created_at", time.time())
        tester._last_modified = data.get("last_modified", time.time())
        
        # Restore groups
        for group_id, group_data in data.get("groups", {}).items():
            tester._groups[group_id] = ExperimentGroup.from_dict(group_data)
        
        return tester
    
    def to_json(self) -> str:
        """
        Convert this A/B tester to a JSON string.
        
        Returns:
            JSON string representation
        """
        with self._lock:
            return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ABTester':
        """
        Create an A/B tester from a JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            A new ABTester instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)