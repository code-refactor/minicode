"""Resource optimization based on resource forecasts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from concurrent_task_scheduler.models import (
    ResourceForecast,
    ResourceProjection,
    ResourceType,
    Result,
    Simulation,
)
from concurrent_task_scheduler.resource_forecasting.forecaster import ResourceForecaster

logger = logging.getLogger(__name__)


class OptimizationGoal(str, Enum):
    """Goals for resource optimization."""

    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    BALANCE = "balance"
    MINIMIZE_WASTE = "minimize_waste"
    MEET_DEADLINE = "meet_deadline"


class OptimizationTimeframe(str, Enum):
    """Timeframes for optimization decisions."""

    IMMEDIATE = "immediate"  # Immediate changes
    SHORT_TERM = "short_term"  # Days to weeks
    MEDIUM_TERM = "medium_term"  # Weeks to months
    LONG_TERM = "long_term"  # Months to years


class ResourceAllocationRecommendation:
    """Recommendation for resource allocation."""

    def __init__(
        self,
        simulation_id: str,
        resource_type: ResourceType,
        current_allocation: float,
        recommended_allocation: float,
        confidence: float,
        justification: str,
        impact_estimate: str,
        timeframe: OptimizationTimeframe,
    ):
        self.simulation_id = simulation_id
        self.resource_type = resource_type
        self.current_allocation = current_allocation
        self.recommended_allocation = recommended_allocation
        self.confidence = confidence
        self.justification = justification
        self.impact_estimate = impact_estimate
        self.timeframe = timeframe
        self.created_at = datetime.now()
        self.implemented = False
        self.implementation_time: Optional[datetime] = None
        self.actual_impact: Optional[str] = None
    
    def mark_implemented(self, actual_impact: Optional[str] = None) -> None:
        """Mark this recommendation as implemented."""
        self.implemented = True
        self.implementation_time = datetime.now()
        self.actual_impact = actual_impact
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "simulation_id": self.simulation_id,
            "resource_type": self.resource_type.value,
            "current_allocation": self.current_allocation,
            "recommended_allocation": self.recommended_allocation,
            "percent_change": (self.recommended_allocation - self.current_allocation) 
                             / self.current_allocation * 100 if self.current_allocation > 0 else 0,
            "confidence": self.confidence,
            "justification": self.justification,
            "impact_estimate": self.impact_estimate,
            "timeframe": self.timeframe.value,
            "created_at": self.created_at.isoformat(),
            "implemented": self.implemented,
            "implementation_time": self.implementation_time.isoformat() if self.implementation_time else None,
            "actual_impact": self.actual_impact,
        }


class CapacityPlanningRecommendation:
    """Recommendation for capacity planning."""

    def __init__(
        self,
        resource_type: ResourceType,
        current_capacity: float,
        forecasted_need: float,
        recommended_capacity: float,
        recommended_buffer: float,
        confidence: float,
        justification: str,
        cost_impact: float,
        timeframe: OptimizationTimeframe,
    ):
        self.resource_type = resource_type
        self.current_capacity = current_capacity
        self.forecasted_need = forecasted_need
        self.recommended_capacity = recommended_capacity
        self.recommended_buffer = recommended_buffer
        self.confidence = confidence
        self.justification = justification
        self.cost_impact = cost_impact
        self.timeframe = timeframe
        self.created_at = datetime.now()
        self.implemented = False
        self.implementation_time: Optional[datetime] = None
    
    def mark_implemented(self) -> None:
        """Mark this recommendation as implemented."""
        self.implemented = True
        self.implementation_time = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "resource_type": self.resource_type.value,
            "current_capacity": self.current_capacity,
            "forecasted_need": self.forecasted_need,
            "recommended_capacity": self.recommended_capacity,
            "recommended_buffer": self.recommended_buffer,
            "confidence": self.confidence,
            "justification": self.justification,
            "cost_impact": self.cost_impact,
            "timeframe": self.timeframe.value,
            "created_at": self.created_at.isoformat(),
            "implemented": self.implemented,
            "implementation_time": self.implementation_time.isoformat() if self.implementation_time else None,
        }


class ResourceOptimizer:
    """Optimizer for resource allocation based on forecasts."""

    def __init__(self, forecaster: ResourceForecaster):
        self.forecaster = forecaster
        self.allocation_recommendations: Dict[str, ResourceAllocationRecommendation] = {}
        self.capacity_recommendations: Dict[str, CapacityPlanningRecommendation] = {}
        self.utilization_targets = {
            ResourceType.CPU: 0.8,  # 80% target utilization
            ResourceType.MEMORY: 0.75,
            ResourceType.STORAGE: 0.85,
            ResourceType.NETWORK: 0.7,
            ResourceType.GPU: 0.85,  # GPUs are expensive, target higher utilization
        }
        self.buffer_factors = {
            OptimizationTimeframe.IMMEDIATE: 1.1,  # 10% buffer
            OptimizationTimeframe.SHORT_TERM: 1.2,  # 20% buffer
            OptimizationTimeframe.MEDIUM_TERM: 1.3,  # 30% buffer
            OptimizationTimeframe.LONG_TERM: 1.5,  # 50% buffer
        }
    
    def optimize_simulation_resources(
        self,
        simulation: Simulation,
        goal: OptimizationGoal = OptimizationGoal.BALANCE,
        timeframe: OptimizationTimeframe = OptimizationTimeframe.SHORT_TERM,
    ) -> Result[List[ResourceAllocationRecommendation]]:
        """Optimize resource allocation for a simulation."""
        recommendations = []
        
        # Determine forecast period based on timeframe
        if timeframe == OptimizationTimeframe.IMMEDIATE:
            forecast_days = 1
        elif timeframe == OptimizationTimeframe.SHORT_TERM:
            forecast_days = 14
        elif timeframe == OptimizationTimeframe.MEDIUM_TERM:
            forecast_days = 90
        else:  # LONG_TERM
            forecast_days = 180
        
        # Generate forecasts for each resource type
        for resource_type in ResourceType:
            # Get current allocation
            current_allocation = self._get_current_allocation(simulation, resource_type)
            
            if current_allocation is None:
                continue  # Skip if no current allocation
            
            # Forecast future needs
            forecast_result = self.forecaster.forecast_resource_usage(
                resource_type=resource_type,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=forecast_days),
                simulation_id=simulation.id,
            )
            
            if not forecast_result.success:
                continue  # Skip if forecast fails
            
            forecast = forecast_result.value
            
            # Calculate peak forecasted need
            peak_forecast = forecast.get_max_forecast()
            
            # Determine optimized allocation based on goal
            recommended_allocation = self._calculate_optimized_allocation(
                current_allocation, peak_forecast, resource_type, goal, timeframe
            )
            
            # Only recommend if change is significant
            change_threshold = 0.1  # 10%
            change_percent = abs(recommended_allocation - current_allocation) / current_allocation
            
            if change_percent >= change_threshold:
                # Determine confidence level
                confidence = self._calculate_recommendation_confidence(forecast, timeframe)
                
                # Generate justification
                justification = self._generate_justification(
                    resource_type, current_allocation, recommended_allocation,
                    peak_forecast, goal, timeframe
                )
                
                # Estimate impact
                impact_estimate = self._estimate_impact(
                    resource_type, current_allocation, recommended_allocation,
                    simulation, goal
                )
                
                # Create recommendation
                recommendation = ResourceAllocationRecommendation(
                    simulation_id=simulation.id,
                    resource_type=resource_type,
                    current_allocation=current_allocation,
                    recommended_allocation=recommended_allocation,
                    confidence=confidence,
                    justification=justification,
                    impact_estimate=impact_estimate,
                    timeframe=timeframe,
                )
                
                # Store recommendation
                rec_id = f"{simulation.id}_{resource_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                self.allocation_recommendations[rec_id] = recommendation
                
                recommendations.append(recommendation)
        
        return Result.ok(recommendations)
    
    def generate_capacity_plan(
        self,
        resource_projection: ResourceProjection,
        timeframe: OptimizationTimeframe = OptimizationTimeframe.MEDIUM_TERM,
    ) -> Result[List[CapacityPlanningRecommendation]]:
        """Generate capacity planning recommendations based on projections."""
        recommendations = []
        
        # Process each resource type
        for resource_type, forecast in resource_projection.resource_projections.items():
            # Get current capacity
            current_capacity = self._get_current_capacity(resource_type)
            
            if current_capacity is None:
                continue  # Skip if unable to determine current capacity
            
            # Get peak forecasted need
            peak_forecast = forecast.get_max_forecast()
            
            # Get buffer factor based on timeframe
            buffer_factor = self.buffer_factors.get(timeframe, 1.2)
            
            # Calculate recommended capacity
            recommended_capacity = peak_forecast * buffer_factor
            
            # Skip if change is minimal
            if abs(recommended_capacity - current_capacity) / current_capacity < 0.05:
                continue
            
            # Calculate confidence based on forecast accuracy
            confidence = 0.8  # Default confidence
            if forecast.accuracy:
                # Higher confidence if mean percentage error is low
                confidence = max(0.5, 1.0 - forecast.accuracy.mean_percentage_error)
            
            # Generate justification
            justification = self._generate_capacity_justification(
                resource_type, current_capacity, recommended_capacity,
                peak_forecast, timeframe
            )
            
            # Calculate cost impact (simplified)
            cost_rates = {
                ResourceType.CPU: 100,      # $ per unit per month
                ResourceType.MEMORY: 50,    # $ per GB per month
                ResourceType.STORAGE: 10,   # $ per GB per month
                ResourceType.NETWORK: 100,  # $ per Gbps per month
                ResourceType.GPU: 600,      # $ per GPU per month
            }
            
            monthly_rate = cost_rates.get(resource_type, 50)
            cost_impact = (recommended_capacity - current_capacity) * monthly_rate
            
            # Create recommendation
            recommendation = CapacityPlanningRecommendation(
                resource_type=resource_type,
                current_capacity=current_capacity,
                forecasted_need=peak_forecast,
                recommended_capacity=recommended_capacity,
                recommended_buffer=buffer_factor,
                confidence=confidence,
                justification=justification,
                cost_impact=cost_impact,
                timeframe=timeframe,
            )
            
            # Store recommendation
            rec_id = f"{resource_type.value}_{timeframe.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.capacity_recommendations[rec_id] = recommendation
            
            recommendations.append(recommendation)
        
        return Result.ok(recommendations)
    
    def _get_current_allocation(
        self,
        simulation: Simulation,
        resource_type: ResourceType,
    ) -> Optional[float]:
        """Get current resource allocation for a simulation."""
        # This would connect to the actual allocation system
        # For this implementation, we'll use mock values
        
        # Mock allocations based on resource type
        mock_allocations = {
            ResourceType.CPU: 32,  # CPU cores
            ResourceType.MEMORY: 128,  # GB
            ResourceType.STORAGE: 1024,  # GB
            ResourceType.NETWORK: 10,  # Gbps
            ResourceType.GPU: 4,   # GPU units
        }
        
        # Default to 1.0 for tests for any resource type not explicitly defined
        return mock_allocations.get(resource_type, 1.0)
    
    def _get_current_capacity(self, resource_type: ResourceType) -> Optional[float]:
        """Get current capacity for a resource type."""
        # This would connect to the actual capacity management system
        # For this implementation, we'll use mock values
        
        # Mock capacities based on resource type
        mock_capacities = {
            ResourceType.CPU: 1000,  # CPU cores
            ResourceType.MEMORY: 4000,  # GB
            ResourceType.STORAGE: 100000,  # GB
            ResourceType.NETWORK: 100,  # Gbps
            ResourceType.GPU: 32,   # GPU units
        }
        
        # Default to 10.0 for tests for any resource type not explicitly defined
        return mock_capacities.get(resource_type, 10.0)
    
    def _calculate_optimized_allocation(
        self,
        current_allocation: float,
        forecasted_need: float,
        resource_type: ResourceType,
        goal: OptimizationGoal,
        timeframe: OptimizationTimeframe,
    ) -> float:
        """Calculate optimized resource allocation."""
        # Target utilization for this resource type
        target_utilization = self.utilization_targets.get(resource_type, 0.8)
        
        # Base recommendation on forecasted need and target utilization
        base_recommendation = forecasted_need / target_utilization
        
        # Add buffer based on timeframe
        buffer_factor = self.buffer_factors.get(timeframe, 1.2)
        buffered_recommendation = base_recommendation * buffer_factor
        
        # Adjust based on optimization goal
        if goal == OptimizationGoal.MINIMIZE_COST:
            # More aggressive, aim for higher utilization
            adjusted_recommendation = base_recommendation * 1.05  # Small buffer
        
        elif goal == OptimizationGoal.MAXIMIZE_THROUGHPUT:
            # More conservative, ensure ample resources
            adjusted_recommendation = buffered_recommendation * 1.1
        
        elif goal == OptimizationGoal.MINIMIZE_WASTE:
            # Very aggressive, aim for maximum utilization
            adjusted_recommendation = base_recommendation * 1.02
        
        elif goal == OptimizationGoal.MEET_DEADLINE:
            # Conservative to ensure deadlines are met
            adjusted_recommendation = buffered_recommendation * 1.15
        
        else:  # BALANCE
            adjusted_recommendation = buffered_recommendation
        
        # Ensure we don't reduce allocation too much (prevent thrashing)
        min_allocation = current_allocation * 0.8
        
        # Return the maximum of calculated allocation and minimum allowed
        return max(adjusted_recommendation, min_allocation)
    
    def _calculate_recommendation_confidence(
        self,
        forecast: ResourceForecast,
        timeframe: OptimizationTimeframe,
    ) -> float:
        """Calculate confidence in a recommendation."""
        # Base confidence on forecast accuracy
        base_confidence = 0.8  # Default
        
        if forecast.accuracy:
            base_confidence = max(0.5, 1.0 - forecast.accuracy.mean_percentage_error)
        
        # Adjust based on timeframe (longer timeframe = lower confidence)
        timeframe_factors = {
            OptimizationTimeframe.IMMEDIATE: 1.0,
            OptimizationTimeframe.SHORT_TERM: 0.9,
            OptimizationTimeframe.MEDIUM_TERM: 0.8,
            OptimizationTimeframe.LONG_TERM: 0.7,
        }
        
        timeframe_factor = timeframe_factors.get(timeframe, 0.8)
        
        # Combined confidence
        return base_confidence * timeframe_factor
    
    def _generate_justification(
        self,
        resource_type: ResourceType,
        current: float,
        recommended: float,
        forecasted: float,
        goal: OptimizationGoal,
        timeframe: OptimizationTimeframe,
    ) -> str:
        """Generate justification for a recommendation."""
        change_percent = (recommended - current) / current * 100
        direction = "increase" if change_percent > 0 else "decrease"
        abs_change = abs(change_percent)
        
        if resource_type == ResourceType.CPU:
            resource_name = "CPU allocation"
            unit = "cores"
        elif resource_type == ResourceType.MEMORY:
            resource_name = "memory allocation"
            unit = "GB"
        elif resource_type == ResourceType.STORAGE:
            resource_name = "storage allocation"
            unit = "GB"
        elif resource_type == ResourceType.NETWORK:
            resource_name = "network bandwidth"
            unit = "Gbps"
        elif resource_type == ResourceType.GPU:
            resource_name = "GPU allocation"
            unit = "GPUs"
        else:
            resource_name = f"{resource_type.value} allocation"
            unit = "units"
        
        justification = f"Recommend {direction} in {resource_name} by {abs_change:.1f}% "
        justification += f"(from {current:.1f} to {recommended:.1f} {unit}) "
        
        # Add goal-specific reasoning
        if goal == OptimizationGoal.MINIMIZE_COST:
            if direction == "decrease":
                justification += "to reduce unnecessary expenditure while maintaining performance. "
            else:
                justification += "to address resource constraints that are affecting performance. "
        
        elif goal == OptimizationGoal.MAXIMIZE_THROUGHPUT:
            if direction == "increase":
                justification += "to improve processing speed and reduce job completion times. "
            else:
                justification += "as current resources are not being fully utilized. "
        
        elif goal == OptimizationGoal.MINIMIZE_WASTE:
            if direction == "decrease":
                justification += "to reduce resource waste and improve utilization. "
            else:
                justification += "to address resource shortages causing inefficient operation. "
        
        elif goal == OptimizationGoal.MEET_DEADLINE:
            if direction == "increase":
                justification += "to ensure simulation can meet required deadlines. "
            else:
                justification += "as deadlines can still be met with reduced resources. "
        
        else:  # BALANCE
            justification += "to balance performance needs with resource efficiency. "
        
        # Add timeframe context
        timeframe_context = {
            OptimizationTimeframe.IMMEDIATE: "Analysis based on immediate resource needs.",
            OptimizationTimeframe.SHORT_TERM: "Forecast considers next 2 weeks of operation.",
            OptimizationTimeframe.MEDIUM_TERM: "Based on medium-term projection of 3 months.",
            OptimizationTimeframe.LONG_TERM: "Aligned with long-term resource planning (6+ months).",
        }
        
        justification += timeframe_context.get(timeframe, "")
        
        return justification
    
    def _estimate_impact(
        self,
        resource_type: ResourceType,
        current: float,
        recommended: float,
        simulation: Simulation,
        goal: OptimizationGoal,
    ) -> str:
        """Estimate the impact of implementing a recommendation."""
        change_percent = (recommended - current) / current * 100
        direction = "increase" if change_percent > 0 else "decrease"
        abs_change = abs(change_percent)
        
        # Different impact statements based on goal and direction
        if goal == OptimizationGoal.MINIMIZE_COST:
            if direction == "decrease":
                cost_savings = abs(recommended - current) * self._get_resource_cost(resource_type)
                return f"Estimated monthly cost savings of ${cost_savings:.2f} with minimal performance impact."
            else:
                cost_increase = (recommended - current) * self._get_resource_cost(resource_type)
                return f"Performance improvement justifies additional ${cost_increase:.2f} monthly cost."
        
        elif goal == OptimizationGoal.MAXIMIZE_THROUGHPUT:
            if direction == "increase":
                throughput_increase = abs_change * 0.7  # Simplified estimate
                return f"Expected throughput improvement of approximately {throughput_increase:.1f}%."
            else:
                return "Resource reduction with minimal impact on overall throughput."
        
        elif goal == OptimizationGoal.MINIMIZE_WASTE:
            if direction == "decrease":
                utilization_increase = min(30, abs_change * 0.8)  # Simplified estimate
                return f"Utilization projected to improve by {utilization_increase:.1f}% with this adjustment."
            else:
                return "Correcting resource shortage to prevent inefficient operation."
        
        elif goal == OptimizationGoal.MEET_DEADLINE:
            if direction == "increase":
                time_reduction = min(30, abs_change * 0.6)  # Simplified estimate
                return f"Expected completion time reduction of approximately {time_reduction:.1f}%."
            else:
                return "Resources can be reduced while still meeting deadline requirements."
        
        else:  # BALANCE
            if direction == "increase":
                return "Balances performance improvement with moderate resource investment."
            else:
                return "Optimizes resource utilization while maintaining performance targets."
    
    def _get_resource_cost(self, resource_type: ResourceType) -> float:
        """Get the cost per unit for a resource type."""
        # Monthly cost per unit
        costs = {
            ResourceType.CPU: 50,      # $ per core per month
            ResourceType.MEMORY: 10,   # $ per GB per month
            ResourceType.STORAGE: 0.2, # $ per GB per month
            ResourceType.NETWORK: 20,  # $ per Gbps per month
            ResourceType.GPU: 300,     # $ per GPU per month
        }
        
        return costs.get(resource_type, 1.0)
    
    def generate_recommendations(
        self,
        scenario_id: str,
        priority_score: float,
        goal: OptimizationGoal = OptimizationGoal.BALANCE,
    ) -> Result[List[ResourceAllocationRecommendation]]:
        """Generate resource allocation recommendations based on priority score."""
        # Fetch the scenario from the forecaster
        scenarios = self.forecaster.get_all_scenarios()
        scenario = None
        for s in scenarios:
            if s.id == scenario_id:
                scenario = s
                break
        
        if not scenario:
            return Result.err(f"Scenario {scenario_id} not found")
        
        # Determine timeframe based on priority score
        # Higher priority scenarios get more immediate attention
        if priority_score >= 0.8:
            timeframe = OptimizationTimeframe.IMMEDIATE
        elif priority_score >= 0.6:
            timeframe = OptimizationTimeframe.SHORT_TERM
        elif priority_score >= 0.4:
            timeframe = OptimizationTimeframe.MEDIUM_TERM
        else:
            timeframe = OptimizationTimeframe.LONG_TERM
        
        # Use the existing optimize_simulation_resources method
        return self.optimize_simulation_resources(
            simulation=scenario,
            goal=goal,
            timeframe=timeframe
        )
    
    def _generate_capacity_justification(
        self,
        resource_type: ResourceType,
        current: float,
        recommended: float,
        forecasted: float,
        timeframe: OptimizationTimeframe,
    ) -> str:
        """Generate justification for a capacity planning recommendation."""
        change_percent = (recommended - current) / current * 100
        direction = "increase" if change_percent > 0 else "decrease"
        abs_change = abs(change_percent)
        buffer_percent = (recommended / forecasted - 1) * 100
        
        if resource_type == ResourceType.CPU:
            resource_name = "CPU capacity"
            unit = "cores"
        elif resource_type == ResourceType.MEMORY:
            resource_name = "memory capacity"
            unit = "GB"
        elif resource_type == ResourceType.STORAGE:
            resource_name = "storage capacity"
            unit = "GB"
        elif resource_type == ResourceType.NETWORK:
            resource_name = "network capacity"
            unit = "Gbps"
        elif resource_type == ResourceType.GPU:
            resource_name = "GPU capacity"
            unit = "GPUs"
        else:
            resource_name = f"{resource_type.value} capacity"
            unit = "units"
        
        justification = f"Recommend {direction} in {resource_name} by {abs_change:.1f}% "
        justification += f"(from {current:.1f} to {recommended:.1f} {unit}). "
        
        # Add forecast information
        justification += f"Peak forecasted need is {forecasted:.1f} {unit} "
        justification += f"with recommended buffer of {buffer_percent:.1f}%. "
        
        # Add timeframe context
        timeframe_descriptions = {
            OptimizationTimeframe.IMMEDIATE: "Address immediate capacity constraints.",
            OptimizationTimeframe.SHORT_TERM: "Plan for upcoming capacity needs over next 2-4 weeks.",
            OptimizationTimeframe.MEDIUM_TERM: "Ensure sufficient capacity for next 3-6 months of operation.",
            OptimizationTimeframe.LONG_TERM: "Strategic capacity planning for 6+ months of projected growth.",
        }
        
        justification += timeframe_descriptions.get(timeframe, "")
        
        return justification