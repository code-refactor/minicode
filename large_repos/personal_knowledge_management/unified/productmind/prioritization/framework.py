"""
Strategic Prioritization Framework - Methodology for feature evaluation.

This module provides capabilities for:
- Multi-criteria scoring models for feature assessment
- Strategic alignment mapping between features and business objectives
- ROI estimation tools with customizable parameters
- Dependency management for feature relationships
- Resource constraint modeling for realistic roadmap planning
"""
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
import json
import os
import math
from uuid import UUID

import numpy as np

from common.core import EntityStorage
from productmind.models import (
    Feature,
    Priority,
    StrategicGoal
)


class ScoringModel(str, Enum):
    """Types of scoring models for feature prioritization."""
    WEIGHTED = "weighted"  # Weighted scoring based on multiple criteria
    VALUE_EFFORT = "value_effort"  # Simple value/effort matrix
    RICE = "rice"  # Reach, Impact, Confidence, Effort
    KANO = "kano"  # Kano model (must-have, performance, delighter)
    WSJF = "wsjf"  # Weighted Shortest Job First


class PrioritizationFramework:
    """
    Framework for prioritizing features based on strategic objectives.
    
    This class provides methods to:
    - Score and prioritize features using various methodologies
    - Map features to strategic objectives
    - Estimate ROI and business value
    - Manage feature dependencies
    - Model resource constraints for roadmap planning
    """
    
    def __init__(
        self,
        storage_dir: str = "./data",
        default_scoring_model: ScoringModel = ScoringModel.WEIGHTED
    ):
        """
        Initialize the prioritization framework.
        
        Args:
            storage_dir: Directory to store data
            default_scoring_model: Default scoring model for prioritization
        """
        self.storage_dir = storage_dir
        self.default_scoring_model = default_scoring_model
        self.feature_storage = EntityStorage[Feature](storage_dir, Feature)
        self.goal_storage = EntityStorage[StrategicGoal](storage_dir, StrategicGoal)
        
        # Create required directories for backward compatibility
        for subdir in ["features", "strategic_goals"]:
            os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)
        
        # Backward compatibility: expose EntityStorage caches
        self._features_cache = self.feature_storage._cache
        self._goals_cache = self.goal_storage._cache
    
    def add_feature(self, feature: Union[Feature, List[Feature]]) -> List[str]:
        """
        Add a new feature or list of features to the system.
        
        Args:
            feature: Feature or list of features to add
            
        Returns:
            List of feature IDs
        """
        if isinstance(feature, Feature):
            feature = [feature]
        
        # Use batch save for multiple features, but also create JSON files for compatibility
        if len(feature) > 1:
            self.feature_storage.save_batch(feature)
            # Create JSON files for backward compatibility
            for item in feature:
                self._create_feature_json_file(item)
        else:
            self.feature_storage.save(feature[0])
            # Create JSON file for backward compatibility
            self._create_feature_json_file(feature[0])
        
        return [str(item.id) for item in feature]
    
    def _create_feature_json_file(self, feature: Feature) -> None:
        """
        Create a JSON file for feature backward compatibility.
        
        Args:
            feature: Feature to create JSON file for
        """
        features_dir = os.path.join(self.storage_dir, "features")
        json_file_path = os.path.join(features_dir, f"{feature.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(feature.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # If JSON creation fails, don't break the main functionality
            pass
    
    def _create_goal_json_file(self, goal: StrategicGoal) -> None:
        """
        Create a JSON file for strategic goal backward compatibility.
        
        Args:
            goal: Strategic goal to create JSON file for
        """
        goals_dir = os.path.join(self.storage_dir, "strategic_goals")
        json_file_path = os.path.join(goals_dir, f"{goal.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(goal.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # If JSON creation fails, don't break the main functionality
            pass
    
    def _store_feature(self, feature: Feature) -> None:
        """
        Store a feature using the EntityStorage system.
        
        Args:
            feature: Feature to store
        """
        self.feature_storage.save(feature)
        
        # Backward compatibility: create JSON file
        self._create_feature_json_file(feature)
    
    def add_strategic_goal(self, goal: Union[StrategicGoal, List[StrategicGoal]]) -> List[str]:
        """
        Add a new strategic goal or list of goals to the system.
        
        Args:
            goal: Strategic goal or list of goals to add
            
        Returns:
            List of goal IDs
        """
        if isinstance(goal, StrategicGoal):
            goal = [goal]
        
        # Use batch save for multiple goals, but also create JSON files for compatibility
        if len(goal) > 1:
            self.goal_storage.save_batch(goal)
            # Create JSON files for backward compatibility
            for item in goal:
                self._create_goal_json_file(item)
        else:
            self.goal_storage.save(goal[0])
            # Create JSON file for backward compatibility
            self._create_goal_json_file(goal[0])
        
        return [str(item.id) for item in goal]
    
    def _store_strategic_goal(self, goal: StrategicGoal) -> None:
        """
        Store a strategic goal using the EntityStorage system.
        
        Args:
            goal: Strategic goal to store
        """
        self.goal_storage.save(goal)
        
        # Backward compatibility: create JSON file
        self._create_goal_json_file(goal)
    
    def get_feature(self, feature_id: Union[str, UUID]) -> Optional[Feature]:
        """
        Retrieve a feature by ID.
        
        Args:
            feature_id: ID of the feature to retrieve (string or UUID)
            
        Returns:
            Feature if found, None otherwise
        """
        if isinstance(feature_id, str):
            try:
                feature_id = UUID(feature_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.feature_storage.get(feature_id)
    
    def get_strategic_goal(self, goal_id: Union[str, UUID]) -> Optional[StrategicGoal]:
        """
        Retrieve a strategic goal by ID.
        
        Args:
            goal_id: ID of the goal to retrieve (string or UUID)
            
        Returns:
            Strategic goal if found, None otherwise
        """
        if isinstance(goal_id, str):
            try:
                goal_id = UUID(goal_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.goal_storage.get(goal_id)
    
    def get_all_features(self) -> List[Feature]:
        """
        Retrieve all features.
        
        Returns:
            List of all features
        """
        return self.feature_storage.list_all()
    
    def get_all_strategic_goals(self) -> List[StrategicGoal]:
        """
        Retrieve all strategic goals.
        
        Returns:
            List of all strategic goals
        """
        return self.goal_storage.list_all()
    
    def map_strategic_alignment(
        self, 
        feature_id: Union[str, UUID], 
        alignments: Dict[Union[str, UUID], float]
    ) -> Feature:
        """
        Map a feature's alignment to strategic goals.
        
        Args:
            feature_id: ID of the feature
            alignments: Dictionary mapping goal IDs to alignment scores (0-10)
            
        Returns:
            Updated feature with alignments
        """
        feature = self.get_feature(feature_id)
        if not feature:
            raise ValueError(f"Feature with ID {feature_id} not found")
        
        # Validate goals exist
        for goal_id in alignments:
            goal = self.get_strategic_goal(goal_id)
            if not goal:
                raise ValueError(f"Strategic goal with ID {goal_id} not found")
        
        # Convert alignment keys to UUIDs for validation, but keep as strings for storage
        string_alignments = {}
        for goal_id, score in alignments.items():
            if isinstance(goal_id, str):
                try:
                    UUID(goal_id)  # Validate it's a proper UUID
                    string_alignments[goal_id] = score
                except ValueError:
                    raise ValueError(f"Invalid UUID format for goal ID: {goal_id}")
            else:
                # Convert UUID to string
                string_alignments[str(goal_id)] = score
        
        # Update alignments - store as strings for compatibility
        feature.strategic_alignment = string_alignments
        feature.update()
        
        # Save feature
        self._store_feature(feature)
        
        return feature
    
    def calculate_strategic_score(self, feature_id: str) -> float:
        """
        Calculate a feature's overall strategic alignment score.

        Args:
            feature_id: ID of the feature

        Returns:
            Strategic alignment score (0-10)
        """
        feature = self.get_feature(feature_id)
        if not feature:
            raise ValueError(f"Feature with ID {feature_id} not found")

        # Return 0.0 when feature has no strategic_alignment or it's empty
        if not feature.strategic_alignment or len(feature.strategic_alignment) == 0:
            return 0.0

        # Get all goals
        all_goals = self.get_all_strategic_goals()

        # Create goal priority weights
        priority_weights = {
            Priority.CRITICAL: 4.0,
            Priority.HIGH: 3.0,
            Priority.MEDIUM: 2.0,
            Priority.LOW: 1.0
        }

        total_score = 0.0
        total_weight = 0.0

        for goal_id, alignment_score in feature.strategic_alignment.items():
            # Convert goal_id to UUID if it's a string
            if isinstance(goal_id, str):
                try:
                    goal_uuid = UUID(goal_id)
                except ValueError:
                    continue  # Skip invalid UUID strings
            else:
                goal_uuid = goal_id
            
            goal = self.get_strategic_goal(goal_uuid)
            if goal:
                weight = priority_weights.get(goal.priority, 1.0)
                total_score += alignment_score * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(total_score / total_weight, 2)
    
    def prioritize_features(
        self,
        feature_ids: Optional[List[str]] = None,
        scoring_model: Optional[ScoringModel] = None,
        criteria_weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Prioritize features based on the selected scoring model.
        
        Args:
            feature_ids: List of feature IDs to prioritize (if None, use all features)
            scoring_model: Scoring model to use
            criteria_weights: Custom weights for criteria (only for WEIGHTED model)
            
        Returns:
            List of features with scores, sorted by priority
        """
        if scoring_model is None:
            scoring_model = self.default_scoring_model
        
        # Get all features if feature_ids not provided
        if feature_ids is None:
            all_features = self.get_all_features()
            feature_ids = [str(f.id) for f in all_features]
        
        # Get features by IDs
        features = []
        for fid in feature_ids:
            feature = self.get_feature(fid)
            if feature:
                features.append(feature)
        
        if not features:
            return []
        
        # Default weights for weighted scoring
        default_weights = {
            "strategic_alignment": 2.0,
            "value": 1.0,
            "effort": -0.5,
            "risk": -0.3
        }
        
        # Use provided weights or defaults
        weights = default_weights
        if criteria_weights:
            weights.update(criteria_weights)
        
        # Calculate scores based on the selected model
        result = []
        
        for feature in features:
            strategic_score = self.calculate_strategic_score(str(feature.id))
            
            # Default values if not set
            value = feature.value_estimate if feature.value_estimate is not None else 5.0
            effort = feature.effort_estimate if feature.effort_estimate is not None else 5.0
            risk = feature.risk_level if feature.risk_level is not None else 5.0
            
            if scoring_model == ScoringModel.WEIGHTED:
                # Weighted scoring based on multiple criteria
                score = (
                    strategic_score * weights["strategic_alignment"] +
                    value * weights["value"] +
                    effort * weights["effort"] +
                    risk * weights["risk"]
                )
                
            elif scoring_model == ScoringModel.VALUE_EFFORT:
                # Simple value/effort ratio
                score = value / max(1.0, effort)
                
            elif scoring_model == ScoringModel.RICE:
                # RICE: Reach, Impact, Confidence, Effort
                # Simplified version where:
                # - Reach is proportional to value
                # - Impact is proportional to strategic score
                # - Confidence is inverse of risk
                # - Effort is effort
                reach = value
                impact = strategic_score
                confidence = (10 - risk) / 10
                
                score = (reach * impact * confidence) / max(1.0, effort)
                
            elif scoring_model == ScoringModel.KANO:
                # Kano model score (simplified)
                # High strategic score and low effort are "must-haves"
                # High value and medium effort are "performance"
                # High value and high effort are "delighters"
                if strategic_score > 7 and effort < 4:
                    kano_class = "must-have"
                    base_score = 10
                elif value > 7 and effort < 7:
                    kano_class = "performance"
                    base_score = 7
                elif value > 8:
                    kano_class = "delighter"
                    base_score = 5
                else:
                    kano_class = "indifferent"
                    base_score = 3
                
                # Adjust score by risk
                score = base_score * (1 - (risk / 20))
                
            elif scoring_model == ScoringModel.WSJF:
                # Weighted Shortest Job First
                # WSJF = (User Value + Time Value + Risk Reduction) / Job Size
                user_value = value
                time_value = strategic_score * 0.8  # Time criticality approximated by strategic alignment
                risk_reduction = (10 - risk) * 0.5
                job_size = effort
                
                score = (user_value + time_value + risk_reduction) / max(1.0, job_size)
            
            else:
                score = strategic_score  # Default to strategic score if model not recognized
            
            # Assign priority based on score
            if score >= 6.5:
                priority = Priority.CRITICAL
            elif score >= 5:
                priority = Priority.HIGH
            elif score >= 3:
                priority = Priority.MEDIUM
            else:
                priority = Priority.LOW
            
            # Update feature with calculated priority
            feature.priority = priority
            feature.update()
            self._store_feature(feature)
            
            result.append({
                "feature_id": str(feature.id),
                "name": feature.name,
                "score": round(score, 2),
                "priority": priority,
                "strategic_score": strategic_score,
                "value": value,
                "effort": effort,
                "risk": risk
            })
        
        # Sort by score (descending)
        result.sort(key=lambda x: x["score"], reverse=True)
        
        return result
    
    def analyze_dependencies(self, feature_ids: Optional[List[str]] = None) -> Dict:
        """
        Analyze dependencies between features.
        
        Args:
            feature_ids: List of feature IDs to analyze (if None, use all features)
            
        Returns:
            Dictionary with dependency analysis
        """
        # Get all features if feature_ids not provided
        if feature_ids is None:
            all_features = self.get_all_features()
            feature_ids = [str(f.id) for f in all_features]
        
        # Get features by IDs
        features = []
        for fid in feature_ids:
            feature = self.get_feature(fid)
            if feature:
                features.append(feature)
        
        if not features:
            return {"features": [], "dependency_graph": {}, "critical_path": []}
        
        # Build dependency graph
        dependency_graph = {}
        for feature in features:
            fid = str(feature.id)
            dependency_graph[fid] = {
                "name": feature.name,
                "dependencies": [str(dep) for dep in feature.dependencies],
                "dependents": []
            }
        
        # Add dependents
        for fid, data in dependency_graph.items():
            for dep_id in data["dependencies"]:
                if dep_id in dependency_graph:
                    dependency_graph[dep_id]["dependents"].append(fid)
        
        # Find root features (no dependencies)
        roots = [fid for fid, data in dependency_graph.items() if not data["dependencies"]]
        
        # Find leaf features (no dependents)
        leaves = [fid for fid, data in dependency_graph.items() if not data["dependents"]]
        
        # Find critical path (longest path from any root to any leaf)
        critical_path = []
        longest_path_length = 0
        
        for root in roots:
            for leaf in leaves:
                # Find all paths from root to leaf
                paths = self._find_all_paths(dependency_graph, root, leaf)
                for path in paths:
                    if len(path) > longest_path_length:
                        longest_path_length = len(path)
                        critical_path = path
        
        # Get feature details for return
        feature_details = []
        for feature in features:
            fid = str(feature.id)
            feature_details.append({
                "id": fid,
                "name": feature.name,
                "dependencies": [str(dep) for dep in feature.dependencies],
                "dependents": dependency_graph[fid]["dependents"] if fid in dependency_graph else [],
                "is_root": fid in roots,
                "is_leaf": fid in leaves,
                "is_on_critical_path": fid in critical_path
            })
        
        return {
            "features": feature_details,
            "dependency_graph": dependency_graph,
            "critical_path": critical_path,
            "roots": roots,
            "leaves": leaves
        }
    
    def _find_all_paths(self, graph, start, end, path=None):
        """
        Helper method to find all paths between two nodes in a graph.
        
        Args:
            graph: Dependency graph
            start: Starting node
            end: End node
            path: Current path (used for recursion)
            
        Returns:
            List of all paths from start to end
        """
        if path is None:
            path = []
        
        path = path + [start]
        
        if start == end:
            return [path]
        
        if start not in graph:
            return []
        
        paths = []
        for node in graph[start]["dependents"]:
            if node not in path:  # Avoid cycles
                new_paths = self._find_all_paths(graph, node, end, path)
                for new_path in new_paths:
                    paths.append(new_path)
        
        return paths
    
    def generate_roadmap(
        self,
        feature_ids: Optional[List[str]] = None,
        time_units: int = 12,
        resources_per_unit: float = 10.0
    ) -> Dict:
        """
        Generate a feature roadmap with resource constraints.
        
        Args:
            feature_ids: List of feature IDs to include (if None, use all features)
            time_units: Number of time units for planning (e.g., months, sprints)
            resources_per_unit: Amount of resource units available per time unit
            
        Returns:
            Dictionary with roadmap plan
        """
        # Get all features if feature_ids not provided
        if feature_ids is None:
            all_features = self.get_all_features()
            feature_ids = [str(f.id) for f in all_features]
        
        # Get features by IDs
        features = []
        for fid in feature_ids:
            feature = self.get_feature(fid)
            if feature:
                features.append(feature)
        
        if not features:
            return {"timeline": [], "unscheduled": []}
        
        # Prioritize features
        prioritized = self.prioritize_features(feature_ids)
        
        # Analyze dependencies
        dependency_analysis = self.analyze_dependencies(feature_ids)
        
        # Create a mapping of feature IDs to their priority order
        priority_order = {item["feature_id"]: idx for idx, item in enumerate(prioritized)}
        
        # Get dependency graph
        dep_graph = dependency_analysis["dependency_graph"]
        
        # Create a list of features with their dependencies and efforts
        feature_nodes = []
        for feature in features:
            fid = str(feature.id)
            effort = feature.effort_estimate if feature.effort_estimate is not None else 5.0
            
            # Get dependent features that are in our feature list
            dependencies = [dep for dep in feature.dependencies if str(dep) in feature_ids]
            
            feature_nodes.append({
                "id": fid,
                "name": feature.name,
                "effort": effort,
                "dependencies": [str(dep) for dep in dependencies],
                "priority_index": priority_order.get(fid, 999)
            })
        
        # Sort by priority (higher priority features are scheduled first)
        feature_nodes.sort(key=lambda x: x["priority_index"])
        
        # Schedule features considering dependencies and resource constraints
        timeline = [[] for _ in range(time_units)]
        scheduled_features = set()
        unscheduled = []
        
        # First, build a map of the earliest possible time unit for each feature
        earliest_time_unit = {}
        
        # Initialize with features that have no dependencies
        for feature in feature_nodes:
            if not feature["dependencies"]:
                earliest_time_unit[feature["id"]] = 0
        
        # Iteratively determine earliest time unit based on dependencies
        while len(earliest_time_unit) < len(feature_nodes):
            made_progress = False
            
            for feature in feature_nodes:
                fid = feature["id"]
                if fid in earliest_time_unit:
                    continue
                
                # Check if all dependencies have been assigned a time unit
                if all(dep in earliest_time_unit for dep in feature["dependencies"]):
                    # Earliest time unit is the max of all dependencies' time units + 1
                    max_dep_time = max(
                        earliest_time_unit.get(dep, 0) for dep in feature["dependencies"]
                    )
                    earliest_time_unit[fid] = max_dep_time + 1
                    made_progress = True
            
            if not made_progress:
                # There are circular dependencies or unreachable features
                # Assign remaining features to the last time unit
                for feature in feature_nodes:
                    if feature["id"] not in earliest_time_unit:
                        earliest_time_unit[feature["id"]] = 0
        
        # Now schedule features respecting resource constraints
        remaining_resources = [resources_per_unit for _ in range(time_units)]
        
        for feature in feature_nodes:
            fid = feature["id"]
            earliest_unit = earliest_time_unit.get(fid, 0)
            effort = feature["effort"]
            
            # Find the first time unit that can accommodate this feature
            scheduled = False
            
            for t in range(earliest_unit, time_units):
                if remaining_resources[t] >= effort:
                    # Schedule the feature
                    timeline[t].append({
                        "id": fid,
                        "name": feature["name"],
                        "effort": effort
                    })
                    remaining_resources[t] -= effort
                    scheduled_features.add(fid)
                    scheduled = True
                    break
            
            if not scheduled:
                # Could not schedule the feature
                unscheduled.append({
                    "id": fid,
                    "name": feature["name"],
                    "effort": effort,
                    "earliest_time_unit": earliest_unit
                })
        
        return {
            "timeline": [
                {
                    "time_unit": t,
                    "features": timeline[t],
                    "total_effort": sum(f["effort"] for f in timeline[t]),
                    "remaining_resources": remaining_resources[t]
                }
                for t in range(time_units)
            ],
            "unscheduled": unscheduled
        }
    
    def estimate_roi(
        self,
        feature_id: Union[str, UUID],
        value_factors: Optional[Dict[str, float]] = None,
        cost_factors: Optional[Dict[str, float]] = None,
        time_horizon: int = 12
    ) -> Dict:
        """
        Estimate ROI for a feature.
        
        Args:
            feature_id: ID of the feature
            value_factors: Custom value factors
            cost_factors: Custom cost factors
            time_horizon: Time horizon for ROI calculation (months)
            
        Returns:
            Dictionary with ROI estimate
        """
        feature = self.get_feature(feature_id)
        if not feature:
            raise ValueError(f"Feature with ID {feature_id} not found")
        
        # Default value factors
        default_value_factors = {
            "revenue_increase": 1.0,
            "cost_savings": 1.0,
            "user_satisfaction": 0.5,
            "strategic_alignment": 0.8
        }
        
        # Default cost factors
        default_cost_factors = {
            "development": 1.0,
            "maintenance": 0.2,
            "training": 0.1,
            "operational": 0.2
        }
        
        # Use provided factors or defaults
        v_factors = default_value_factors
        if value_factors:
            v_factors.update(value_factors)
        
        c_factors = default_cost_factors
        if cost_factors:
            c_factors.update(cost_factors)
        
        # Get feature attributes
        value = feature.value_estimate if feature.value_estimate is not None else 5.0
        effort = feature.effort_estimate if feature.effort_estimate is not None else 5.0
        strategic_score = self.calculate_strategic_score(feature_id)
        
        # Calculate baseline value and cost
        base_value = value * 10000  # Arbitrary base value
        base_cost = effort * 5000   # Arbitrary base cost
        
        # Calculate value components
        value_components = {
            "revenue_increase": base_value * v_factors["revenue_increase"] * (value / 10),
            "cost_savings": base_value * v_factors["cost_savings"] * (value / 10),
            "user_satisfaction": base_value * v_factors["user_satisfaction"] * (value / 10),
            "strategic_alignment": base_value * v_factors["strategic_alignment"] * (strategic_score / 10)
        }
        
        total_value = sum(value_components.values())
        
        # Calculate cost components
        cost_components = {
            "development": base_cost * c_factors["development"] * (effort / 10),
            "maintenance": base_cost * c_factors["maintenance"] * (effort / 10) * time_horizon / 12,
            "training": base_cost * c_factors["training"],
            "operational": base_cost * c_factors["operational"] * time_horizon / 12
        }
        
        total_cost = sum(cost_components.values())
        
        # Calculate ROI
        if total_cost == 0:
            roi_percent = 0
        else:
            roi_percent = ((total_value - total_cost) / total_cost) * 100
        
        # Calculate payback period (months)
        if total_value == 0:
            payback_period = float('inf')
        else:
            monthly_value = total_value / time_horizon
            initial_cost = cost_components["development"] + cost_components["training"]
            monthly_cost = (cost_components["maintenance"] + cost_components["operational"]) / time_horizon
            
            if monthly_value <= monthly_cost:
                payback_period = float('inf')
            else:
                payback_period = initial_cost / (monthly_value - monthly_cost)
        
        return {
            "feature_id": feature_id,
            "feature_name": feature.name,
            "time_horizon_months": time_horizon,
            "value_components": value_components,
            "total_value": total_value,
            "cost_components": cost_components,
            "total_cost": total_cost,
            "net_value": total_value - total_cost,
            "roi_percent": roi_percent,
            "payback_period_months": payback_period if payback_period != float('inf') else None
        }