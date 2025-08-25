"""Resource forecasting models for simulation resource requirements."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

from concurrent_task_scheduler.models.simulation import ResourceType


class ResourceUsagePattern(str, Enum):
    """Patterns of resource usage over time."""
    
    CONSTANT = "constant"  # Consistent usage
    INCREASING = "increasing"  # Gradually increasing usage
    DECREASING = "decreasing"  # Gradually decreasing usage
    SPIKY = "spiky"  # Usage with periodic spikes
    CYCLICAL = "cyclical"  # Predictable cycles of usage
    WAVE = "wave"  # Smooth sine-wave-like pattern
    BURST = "burst"  # Low baseline with occasional bursts
    RANDOM = "random"  # Unpredictable usage patterns


class ForecastPeriod(str, Enum):
    """Time periods for resource forecasts."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ForecastAccuracy(BaseModel):
    """Accuracy metrics for a resource forecast."""

    mean_absolute_error: float
    mean_percentage_error: float
    root_mean_squared_error: float
    confidence_interval: Tuple[float, float]  # (lower, upper) bounds as percentages


class ResourceForecast(BaseModel):
    """Forecast of resource usage for a specific period."""

    start_date: datetime
    end_date: datetime
    period: ForecastPeriod
    resource_type: ResourceType
    forecasted_values: Dict[str, float]  # Date string to forecasted value
    actual_values: Dict[str, float] = Field(default_factory=dict)  # Date string to actual value
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    accuracy: Optional[ForecastAccuracy] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    
    # Fields for backward compatibility with tests
    scenario_id: Optional[str] = None
    forecast_method: Optional[str] = None
    data_points: List[Any] = Field(default_factory=list)
    forecast_created: Optional[datetime] = None
    resource_forecasts: List[Any] = Field(default_factory=list)
    
    def calculate_accuracy(self) -> ForecastAccuracy:
        """Calculate accuracy metrics based on actual vs. forecasted values."""
        if not self.actual_values:
            return ForecastAccuracy(
                mean_absolute_error=0.0,
                mean_percentage_error=0.0,
                root_mean_squared_error=0.0,
                confidence_interval=(0.0, 0.0)
            )
        
        errors = []
        percentage_errors = []
        
        for date_str, actual in self.actual_values.items():
            if date_str in self.forecasted_values:
                forecast = self.forecasted_values[date_str]
                error = abs(forecast - actual)
                errors.append(error)
                
                if actual != 0:
                    percentage_error = error / actual
                    percentage_errors.append(percentage_error)
        
        if not errors:
            return ForecastAccuracy(
                mean_absolute_error=0.0,
                mean_percentage_error=0.0,
                root_mean_squared_error=0.0,
                confidence_interval=(0.0, 0.0)
            )
        
        mae = np.mean(errors)
        mpe = np.mean(percentage_errors) if percentage_errors else 0.0
        rmse = np.sqrt(np.mean([e**2 for e in errors]))
        
        # Use 95% confidence interval
        if len(percentage_errors) > 1:
            std_dev = np.std(percentage_errors)
            confidence_interval = (max(0.0, mpe - 1.96 * std_dev), mpe + 1.96 * std_dev)
        else:
            confidence_interval = (0.0, 0.0)
        
        return ForecastAccuracy(
            mean_absolute_error=float(mae),
            mean_percentage_error=float(mpe),
            root_mean_squared_error=float(rmse),
            confidence_interval=confidence_interval
        )
    
    def get_max_forecast(self) -> float:
        """Get the maximum forecasted value."""
        if not self.forecasted_values:
            return 0.0
        return max(self.forecasted_values.values())
    
    def get_total_forecast(self) -> float:
        """Get the total forecasted usage over the period."""
        return sum(self.forecasted_values.values())
    
    def is_within_accuracy_threshold(self, threshold_percent: float = 15.0) -> bool:
        """Check if forecast is within the specified accuracy threshold."""
        if not self.accuracy:
            self.accuracy = self.calculate_accuracy()
        
        return self.accuracy.mean_percentage_error * 100 <= threshold_percent


class UtilizationDataPoint(BaseModel):
    """A single data point for resource utilization."""

    timestamp: datetime
    resource_type: ResourceType
    utilization: float  # Actual utilization value
    capacity: float  # Total available capacity
    simulation_id: Optional[str] = None  # If associated with a specific simulation
    node_id: Optional[str] = None  # If associated with a specific node


class ResourceUtilizationHistory(BaseModel):
    """Historical resource utilization data for forecasting."""

    resource_type: ResourceType
    start_date: datetime
    end_date: datetime
    data_points: List[UtilizationDataPoint] = Field(default_factory=list)
    aggregation_period: str = "hourly"  # hourly, daily, weekly, etc.
    
    def add_data_point(self, data_point: UtilizationDataPoint) -> None:
        """Add a new data point to the history."""
        self.data_points.append(data_point)
        
        # Update date range if needed
        if data_point.timestamp < self.start_date:
            self.start_date = data_point.timestamp
        if data_point.timestamp > self.end_date:
            self.end_date = data_point.timestamp
    
    def get_utilization_rate(self) -> float:
        """Calculate the average utilization rate."""
        if not self.data_points:
            return 0.0
        
        total_utilization = sum(dp.utilization / dp.capacity for dp in self.data_points)
        return total_utilization / len(self.data_points)
    
    def get_peak_utilization(self) -> float:
        """Get the peak utilization value."""
        if not self.data_points:
            return 0.0
        
        return max(dp.utilization for dp in self.data_points)
    
    def get_time_series_data(self) -> Tuple[List[datetime], List[float]]:
        """Get time series data for forecasting algorithms."""
        if not self.data_points:
            return [], []
        
        # Sort by timestamp
        sorted_points = sorted(self.data_points, key=lambda dp: dp.timestamp)
        
        timestamps = [dp.timestamp for dp in sorted_points]
        values = [dp.utilization for dp in sorted_points]
        
        return timestamps, values


class ResourceProjection(BaseModel):
    """Projection of future resource needs for grant reporting and planning."""

    project_id: str
    project_name: str
    start_date: datetime
    end_date: datetime
    resource_projections: Dict[ResourceType, ResourceForecast]
    confidence_level: float = 0.95  # 95% confidence level by default
    total_cost_estimate: Optional[float] = None
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)
    narrative: Optional[str] = None  # Human-readable explanation
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def get_projection_duration(self) -> timedelta:
        """Get the total duration of the projection."""
        return self.end_date - self.start_date
    
    def get_accuracy_metrics(self) -> Dict[ResourceType, ForecastAccuracy]:
        """Get accuracy metrics for all resource types."""
        result = {}
        for resource_type, forecast in self.resource_projections.items():
            if not forecast.accuracy:
                forecast.accuracy = forecast.calculate_accuracy()
            result[resource_type] = forecast.accuracy
        return result
    
    def is_within_grant_budget(self, budget: float) -> bool:
        """Check if the projection is within the grant budget."""
        if self.total_cost_estimate is None:
            return True
        return self.total_cost_estimate <= budget