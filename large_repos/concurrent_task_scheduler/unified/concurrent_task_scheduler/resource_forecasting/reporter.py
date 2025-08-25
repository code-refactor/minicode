"""Reporting module for resource usage and forecasts."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd

from concurrent_task_scheduler.models import (
    ForecastPeriod,
    ResourceForecast,
    ResourceProjection,
    ResourceType,
    Result,
    Simulation,
)
from concurrent_task_scheduler.resource_forecasting.data_collector import (
    AggregationMethod,
    AggregationPeriod,
    ResourceDataCollector,
    ResourceUsageAnalyzer,
)
from concurrent_task_scheduler.resource_forecasting.forecaster import ResourceForecaster
from concurrent_task_scheduler.resource_forecasting.optimizer import (
    CapacityPlanningRecommendation,
    OptimizationGoal,
    OptimizationTimeframe,
    ResourceAllocationRecommendation,
    ResourceOptimizer,
)

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of resource reports."""

    UTILIZATION = "utilization"  # Resource utilization
    FORECAST = "forecast"  # Resource forecast
    EFFICIENCY = "efficiency"  # Resource efficiency
    COMPARISON = "comparison"  # Simulation comparison
    GRANT = "grant"  # Grant report
    CAPACITY = "capacity"  # Capacity planning
    RECOMMENDATION = "recommendation"  # Recommendations


class ReportFormat(str, Enum):
    """Output formats for reports."""

    JSON = "json"
    CSV = "csv"
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"


class ResourceReporter:
    """Reporter for generating resource reports."""

    def __init__(
        self,
        data_collector=None,
        forecaster=None,
        optimizer=None,
    ):
        self.data_collector = data_collector
        self.forecaster = forecaster
        self.optimizer = optimizer
        if data_collector is not None:
            self.analyzer = ResourceUsageAnalyzer(data_collector)
        else:
            self.analyzer = None
        self.generated_reports: Dict[str, Dict] = {}
    
    def generate_utilization_report(
        self,
        simulation_id: Optional[str] = None,
        node_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resource_types: Optional[List[ResourceType]] = None,
        format: ReportFormat = ReportFormat.JSON,
    ) -> Result[str]:
        """Generate a resource utilization report."""
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        if resource_types is None:
            resource_types = list(ResourceType)
        
        report_data = {
            "report_type": ReportType.UTILIZATION.value,
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "scope": {
                "simulation_id": simulation_id,
                "node_id": node_id,
                "resource_types": [rt.value for rt in resource_types],
            },
            "metrics": {},
            "data": {},
        }
        
        # Gather utilization data for each resource type
        for resource_type in resource_types:
            # Get utilization metrics
            metrics_result = self.analyzer.calculate_utilization_metrics(
                resource_type=resource_type,
                start_date=start_date,
                end_date=end_date,
                simulation_id=simulation_id,
                node_id=node_id,
            )
            
            if metrics_result.success:
                report_data["metrics"][resource_type.value] = metrics_result.value
            
            # Get utilization history
            history_result = self.data_collector.get_resource_history(
                resource_type=resource_type,
                start_date=start_date,
                end_date=end_date,
                simulation_id=simulation_id,
                node_id=node_id,
                aggregation_method=AggregationMethod.MEAN,
                aggregation_period=AggregationPeriod.DAY,
            )
            
            if history_result.success:
                history = history_result.value
                
                # Convert to time series data
                timestamps, values = history.get_time_series_data()
                
                # Format for report
                time_series = {}
                for i, ts in enumerate(timestamps):
                    time_series[ts.isoformat()] = values[i]
                
                report_data["data"][resource_type.value] = {
                    "time_series": time_series,
                    "unit": "utilization",
                }
        
        # Add summary statistics
        summary = {}
        
        for resource_type in resource_types:
            if resource_type.value in report_data["metrics"]:
                metrics = report_data["metrics"][resource_type.value]
                summary[resource_type.value] = {
                    "average_utilization": metrics.get("mean_utilization", 0),
                    "peak_utilization": metrics.get("max_utilization", 0),
                    "utilization_rate": metrics.get("mean_utilization_rate", 0),
                }
        
        report_data["summary"] = summary
        
        # Store report
        report_id = f"utilization_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.generated_reports[report_id] = report_data
        
        # Format the report
        if format == ReportFormat.JSON:
            return Result.ok(json.dumps(report_data, indent=2))
        
        elif format == ReportFormat.CSV:
            # Convert to CSV format
            csv_lines = ["timestamp"]
            for rt in resource_types:
                csv_lines[0] += f",{rt.value}"
            
            # Collect all timestamps across all resource types
            all_timestamps = set()
            for rt in resource_types:
                if rt.value in report_data["data"]:
                    all_timestamps.update(report_data["data"][rt.value]["time_series"].keys())
            
            # Sort timestamps
            sorted_timestamps = sorted(all_timestamps)
            
            # Add data rows
            for ts in sorted_timestamps:
                line = ts
                for rt in resource_types:
                    if (rt.value in report_data["data"] and 
                        ts in report_data["data"][rt.value]["time_series"]):
                        line += f",{report_data['data'][rt.value]['time_series'][ts]}"
                    else:
                        line += ","
                csv_lines.append(line)
            
            return Result.ok("\n".join(csv_lines))
        
        elif format == ReportFormat.MARKDOWN:
            # Generate markdown report
            md_lines = [
                f"# Resource Utilization Report",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                f"",
            ]
            
            if simulation_id:
                md_lines.append(f"Simulation: {simulation_id}")
            if node_id:
                md_lines.append(f"Node: {node_id}")
            
            md_lines.extend([
                f"",
                f"## Summary",
                f"",
                f"| Resource | Average Utilization | Peak Utilization | Utilization Rate |",
                f"|----------|---------------------|------------------|------------------|",
            ])
            
            for rt in resource_types:
                if rt.value in summary:
                    stats = summary[rt.value]
                    md_lines.append(
                        f"| {rt.value} | "
                        f"{stats['average_utilization']:.2f} | "
                        f"{stats['peak_utilization']:.2f} | "
                        f"{stats['utilization_rate']:.2f} |"
                    )
            
            return Result.ok("\n".join(md_lines))
        
        elif format == ReportFormat.TEXT:
            # Generate text report
            text_lines = [
                f"Resource Utilization Report",
                f"=========================",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                f"",
            ]
            
            if simulation_id:
                text_lines.append(f"Simulation: {simulation_id}")
            if node_id:
                text_lines.append(f"Node: {node_id}")
            
            text_lines.append(f"")
            text_lines.append(f"Summary:")
            text_lines.append(f"--------")
            
            for rt in resource_types:
                if rt.value in summary:
                    stats = summary[rt.value]
                    text_lines.extend([
                        f"{rt.value}:",
                        f"  Average Utilization: {stats['average_utilization']:.2f}",
                        f"  Peak Utilization: {stats['peak_utilization']:.2f}",
                        f"  Utilization Rate: {stats['utilization_rate']:.2f}",
                        f"",
                    ])
            
            return Result.ok("\n".join(text_lines))
        
        else:
            return Result.err(f"Unsupported report format: {format}")
    
    def generate_forecast_report(
        self,
        simulation_id: Optional[str] = None,
        node_id: Optional[str] = None,
        resource_types: Optional[List[ResourceType]] = None,
        forecast_days: int = 30,
        format: ReportFormat = ReportFormat.JSON,
    ) -> Result[str]:
        """Generate a resource forecast report."""
        if resource_types is None:
            resource_types = list(ResourceType)
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=forecast_days)
        
        report_data = {
            "report_type": ReportType.FORECAST.value,
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "forecast_days": forecast_days,
            },
            "scope": {
                "simulation_id": simulation_id,
                "node_id": node_id,
                "resource_types": [rt.value for rt in resource_types],
            },
            "forecasts": {},
        }
        
        # Generate forecasts for each resource type
        for resource_type in resource_types:
            forecast_result = self.forecaster.forecast_resource_usage(
                resource_type=resource_type,
                start_date=start_date,
                end_date=end_date,
                simulation_id=simulation_id,
                node_id=node_id,
                period=ForecastPeriod.DAILY,
            )
            
            if forecast_result.success:
                forecast = forecast_result.value
                
                # Convert to serializable format
                forecast_data = {
                    "values": forecast.forecasted_values,
                    "confidence_intervals": {
                        date: {"lower": lower, "upper": upper}
                        for date, (lower, upper) in forecast.confidence_intervals.items()
                    },
                    "peak_forecast": forecast.get_max_forecast(),
                    "total_forecast": forecast.get_total_forecast(),
                }
                
                if forecast.accuracy:
                    forecast_data["accuracy"] = {
                        "mean_absolute_error": forecast.accuracy.mean_absolute_error,
                        "mean_percentage_error": forecast.accuracy.mean_percentage_error,
                        "root_mean_squared_error": forecast.accuracy.root_mean_squared_error,
                        "confidence_interval": {
                            "lower": forecast.accuracy.confidence_interval[0],
                            "upper": forecast.accuracy.confidence_interval[1],
                        },
                    }
                
                report_data["forecasts"][resource_type.value] = forecast_data
        
        # Add recommendations based on forecasts
        if simulation_id:
            recommendations = []
            
            for resource_type in resource_types:
                if resource_type.value in report_data["forecasts"]:
                    forecast_data = report_data["forecasts"][resource_type.value]
                    peak_forecast = forecast_data["peak_forecast"]
                    
                    # Get current allocation (mock)
                    current_allocation = 0
                    if resource_type == ResourceType.CPU:
                        current_allocation = 32
                    elif resource_type == ResourceType.MEMORY:
                        current_allocation = 128
                    elif resource_type == ResourceType.STORAGE:
                        current_allocation = 1024
                    elif resource_type == ResourceType.NETWORK:
                        current_allocation = 10
                    
                    # Check if adjustment is needed
                    utilization_target = 0.8  # 80% target utilization
                    recommended_allocation = peak_forecast / utilization_target
                    
                    if abs(recommended_allocation - current_allocation) / current_allocation > 0.1:
                        change_direction = "increase" if recommended_allocation > current_allocation else "decrease"
                        change_percent = abs(recommended_allocation - current_allocation) / current_allocation * 100
                        
                        recommendations.append({
                            "resource_type": resource_type.value,
                            "current_allocation": current_allocation,
                            "recommended_allocation": recommended_allocation,
                            "change_direction": change_direction,
                            "change_percent": change_percent,
                            "justification": f"Based on peak forecast of {peak_forecast}",
                        })
            
            report_data["recommendations"] = recommendations
        
        # Store report
        report_id = f"forecast_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.generated_reports[report_id] = report_data
        
        # Format the report
        if format == ReportFormat.JSON:
            return Result.ok(json.dumps(report_data, indent=2))
        
        elif format == ReportFormat.CSV:
            # Convert to CSV format
            csv_lines = ["date"]
            for rt in resource_types:
                if rt.value in report_data["forecasts"]:
                    csv_lines[0] += f",{rt.value}_forecast,{rt.value}_lower,{rt.value}_upper"
            
            # Collect all dates across all forecasts
            all_dates = set()
            for rt in resource_types:
                if rt.value in report_data["forecasts"]:
                    all_dates.update(report_data["forecasts"][rt.value]["values"].keys())
            
            # Sort dates
            sorted_dates = sorted(all_dates)
            
            # Add data rows
            for date in sorted_dates:
                line = date
                for rt in resource_types:
                    if rt.value in report_data["forecasts"]:
                        forecast_data = report_data["forecasts"][rt.value]
                        forecast_value = forecast_data["values"].get(date, "")
                        
                        if date in forecast_data["confidence_intervals"]:
                            lower = forecast_data["confidence_intervals"][date]["lower"]
                            upper = forecast_data["confidence_intervals"][date]["upper"]
                            line += f",{forecast_value},{lower},{upper}"
                        else:
                            line += f",{forecast_value},,"
                    else:
                        line += ",,,"
                csv_lines.append(line)
            
            return Result.ok("\n".join(csv_lines))
        
        elif format == ReportFormat.MARKDOWN:
            # Generate markdown report
            md_lines = [
                f"# Resource Forecast Report",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"Forecast Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({forecast_days} days)",
                f"",
            ]
            
            if simulation_id:
                md_lines.append(f"Simulation: {simulation_id}")
            if node_id:
                md_lines.append(f"Node: {node_id}")
            
            md_lines.extend([
                f"",
                f"## Summary",
                f"",
                f"| Resource | Peak Forecast | Total Forecast | Forecast Accuracy |",
                f"|----------|---------------|----------------|-------------------|",
            ])
            
            for rt in resource_types:
                if rt.value in report_data["forecasts"]:
                    forecast_data = report_data["forecasts"][rt.value]
                    accuracy = forecast_data.get("accuracy", {}).get("mean_percentage_error", "N/A")
                    accuracy_str = f"{accuracy:.1%}" if isinstance(accuracy, (int, float)) else accuracy
                    
                    md_lines.append(
                        f"| {rt.value} | "
                        f"{forecast_data['peak_forecast']:.2f} | "
                        f"{forecast_data['total_forecast']:.2f} | "
                        f"{accuracy_str} |"
                    )
            
            if "recommendations" in report_data and report_data["recommendations"]:
                md_lines.extend([
                    f"",
                    f"## Recommendations",
                    f"",
                    f"| Resource | Current | Recommended | Change |",
                    f"|----------|---------|-------------|--------|",
                ])
                
                for rec in report_data["recommendations"]:
                    md_lines.append(
                        f"| {rec['resource_type']} | "
                        f"{rec['current_allocation']:.2f} | "
                        f"{rec['recommended_allocation']:.2f} | "
                        f"{rec['change_direction']} by {rec['change_percent']:.1f}% |"
                    )
            
            return Result.ok("\n".join(md_lines))
        
        elif format == ReportFormat.TEXT:
            # Generate text report
            text_lines = [
                f"Resource Forecast Report",
                f"========================",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Forecast Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({forecast_days} days)",
                f"",
            ]
            
            if simulation_id:
                text_lines.append(f"Simulation: {simulation_id}")
            if node_id:
                text_lines.append(f"Node: {node_id}")
            
            text_lines.append(f"")
            text_lines.append(f"Summary:")
            text_lines.append(f"--------")
            
            for rt in resource_types:
                if rt.value in report_data["forecasts"]:
                    forecast_data = report_data["forecasts"][rt.value]
                    accuracy = forecast_data.get("accuracy", {}).get("mean_percentage_error", "N/A")
                    accuracy_str = f"{accuracy:.1%}" if isinstance(accuracy, (int, float)) else accuracy
                    
                    text_lines.extend([
                        f"{rt.value}:",
                        f"  Peak Forecast: {forecast_data['peak_forecast']:.2f}",
                        f"  Total Forecast: {forecast_data['total_forecast']:.2f}",
                        f"  Forecast Accuracy: {accuracy_str}",
                        f"",
                    ])
            
            if "recommendations" in report_data and report_data["recommendations"]:
                text_lines.append(f"Recommendations:")
                text_lines.append(f"----------------")
                
                for rec in report_data["recommendations"]:
                    text_lines.extend([
                        f"{rec['resource_type']}:",
                        f"  Current Allocation: {rec['current_allocation']:.2f}",
                        f"  Recommended Allocation: {rec['recommended_allocation']:.2f}",
                        f"  Change: {rec['change_direction']} by {rec['change_percent']:.1f}%",
                        f"  Justification: {rec['justification']}",
                        f"",
                    ])
            
            return Result.ok("\n".join(text_lines))
        
        else:
            return Result.err(f"Unsupported report format: {format}")
    
    def generate_grant_report(
        self,
        project_id: str,
        project_name: str,
        start_date: datetime,
        end_date: datetime,
        simulation_ids: List[str],
        format: ReportFormat = ReportFormat.JSON,
    ) -> Result[str]:
        """Generate a grant report with resource projections."""
        # Create resource projection
        projection_result = self.forecaster.create_resource_projection(
            project_id=project_id,
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            simulation_ids=simulation_ids,
        )
        
        if not projection_result.success:
            return Result.err(f"Failed to create resource projection: {projection_result.error}")
        
        projection = projection_result.value
        
        # Create report data
        report_data = {
            "report_type": ReportType.GRANT.value,
            "generated_at": datetime.now().isoformat(),
            "project": {
                "id": project_id,
                "name": project_name,
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days,
            },
            "simulations": simulation_ids,
            "resource_projections": {},
            "cost_estimate": {
                "total": projection.total_cost_estimate,
                "breakdown": projection.cost_breakdown,
            },
        }
        
        # Format resource projections
        for resource_type, forecast in projection.resource_projections.items():
            report_data["resource_projections"][resource_type.value] = {
                "values": forecast.forecasted_values,
                "peak_forecast": forecast.get_max_forecast(),
                "total_forecast": forecast.get_total_forecast(),
            }
        
        # Generate capacity recommendations
        capacity_result = self.optimizer.generate_capacity_plan(
            resource_projection=projection,
            timeframe=OptimizationTimeframe.MEDIUM_TERM,
        )
        
        if capacity_result.success:
            report_data["capacity_recommendations"] = [
                rec.to_dict() for rec in capacity_result.value
            ]
        
        # Store report
        report_id = f"grant_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.generated_reports[report_id] = report_data
        
        # Format the report
        if format == ReportFormat.JSON:
            return Result.ok(json.dumps(report_data, indent=2))
        
        elif format == ReportFormat.MARKDOWN:
            # Generate markdown report
            md_lines = [
                f"# Resource Projection for Grant Report",
                f"",
                f"## Project: {project_name} ({project_id})",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({(end_date - start_date).days} days)",
                f"",
                f"## Cost Estimate",
                f"",
                f"**Total Cost: ${projection.total_cost_estimate:.2f}**",
                f"",
                f"### Cost Breakdown",
                f"",
                f"| Resource | Cost |",
                f"|----------|------|",
            ]
            
            for resource, cost in projection.cost_breakdown.items():
                md_lines.append(f"| {resource} | ${cost:.2f} |")
            
            md_lines.extend([
                f"",
                f"## Resource Projections",
                f"",
                f"| Resource | Peak Usage | Total Usage |",
                f"|----------|------------|-------------|",
            ])
            
            for resource_type, forecast in projection.resource_projections.items():
                md_lines.append(
                    f"| {resource_type.value} | "
                    f"{forecast.get_max_forecast():.2f} | "
                    f"{forecast.get_total_forecast():.2f} |"
                )
            
            if "capacity_recommendations" in report_data:
                md_lines.extend([
                    f"",
                    f"## Capacity Recommendations",
                    f"",
                    f"| Resource | Current | Recommended | Cost Impact |",
                    f"|----------|---------|-------------|-------------|",
                ])
                
                for rec in report_data["capacity_recommendations"]:
                    md_lines.append(
                        f"| {rec['resource_type']} | "
                        f"{rec['current_capacity']:.2f} | "
                        f"{rec['recommended_capacity']:.2f} | "
                        f"${rec['cost_impact']:.2f} |"
                    )
            
            return Result.ok("\n".join(md_lines))
        
        elif format == ReportFormat.TEXT:
            # Generate text report
            text_lines = [
                f"Resource Projection for Grant Report",
                f"=====================================",
                f"",
                f"Project: {project_name} ({project_id})",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({(end_date - start_date).days} days)",
                f"",
                f"Cost Estimate",
                f"-------------",
                f"Total Cost: ${projection.total_cost_estimate:.2f}",
                f"",
                f"Cost Breakdown:",
            ]
            
            for resource, cost in projection.cost_breakdown.items():
                text_lines.append(f"  {resource}: ${cost:.2f}")
            
            text_lines.append(f"")
            text_lines.append(f"Resource Projections")
            text_lines.append(f"-------------------")
            
            for resource_type, forecast in projection.resource_projections.items():
                text_lines.extend([
                    f"{resource_type.value}:",
                    f"  Peak Usage: {forecast.get_max_forecast():.2f}",
                    f"  Total Usage: {forecast.get_total_forecast():.2f}",
                    f"",
                ])
            
            if "capacity_recommendations" in report_data:
                text_lines.append(f"Capacity Recommendations")
                text_lines.append(f"-----------------------")
                
                for rec in report_data["capacity_recommendations"]:
                    text_lines.extend([
                        f"{rec['resource_type']}:",
                        f"  Current Capacity: {rec['current_capacity']:.2f}",
                        f"  Recommended Capacity: {rec['recommended_capacity']:.2f}",
                        f"  Cost Impact: ${rec['cost_impact']:.2f}",
                        f"  Justification: {rec['justification']}",
                        f"",
                    ])
            
            return Result.ok("\n".join(text_lines))
        
        else:
            return Result.err(f"Unsupported report format: {format}")
    
    def generate_recommendation_report(
        self,
        simulation_id: Optional[str] = None,
        goal: OptimizationGoal = OptimizationGoal.BALANCE,
        timeframe: OptimizationTimeframe = OptimizationTimeframe.SHORT_TERM,
        format: ReportFormat = ReportFormat.JSON,
        simulation: Optional[Simulation] = None,
    ) -> Result[str]:
        """Generate a recommendation report."""
        if not simulation and not simulation_id:
            return Result.err("Either simulation or simulation_id must be provided")
        
        if not simulation:
            # In a real implementation, this would fetch the simulation
            simulation = Simulation(
                id=simulation_id,
                name=f"Simulation {simulation_id}",
                stages={},
                owner="user1",
                project="project1",
            )
        
        # Get optimization recommendations
        rec_result = self.optimizer.optimize_simulation_resources(
            simulation=simulation,
            goal=goal,
            timeframe=timeframe,
        )
        
        if not rec_result.success:
            return Result.err(f"Failed to generate recommendations: {rec_result.error}")
        
        recommendations = rec_result.value
        
        # Create report data
        report_data = {
            "report_type": ReportType.RECOMMENDATION.value,
            "generated_at": datetime.now().isoformat(),
            "simulation": {
                "id": simulation.id,
                "name": simulation.name,
            },
            "optimization": {
                "goal": goal.value,
                "timeframe": timeframe.value,
            },
            "recommendations": [rec.to_dict() for rec in recommendations],
            "summary": {
                "recommendation_count": len(recommendations),
                "resource_types": list(set(rec.resource_type.value for rec in recommendations)),
                "average_confidence": sum(rec.confidence for rec in recommendations) / len(recommendations) if recommendations else 0,
            },
        }
        
        # Store report
        report_id = f"recommendations_{simulation.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.generated_reports[report_id] = report_data
        
        # Format the report
        if format == ReportFormat.JSON:
            return Result.ok(json.dumps(report_data, indent=2))
        
        elif format == ReportFormat.MARKDOWN:
            # Generate markdown report
            md_lines = [
                f"# Resource Optimization Recommendations",
                f"",
                f"## Simulation: {simulation.name} ({simulation.id})",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"Optimization Goal: {goal.value}",
                f"Timeframe: {timeframe.value}",
                f"",
                f"## Recommendations",
                f"",
            ]
            
            if not recommendations:
                md_lines.append(f"*No recommendations at this time.*")
            else:
                md_lines.extend([
                    f"| Resource | Current | Recommended | Change | Confidence |",
                    f"|----------|---------|-------------|--------|------------|",
                ])
                
                for rec in recommendations:
                    percent_change = (rec.recommended_allocation - rec.current_allocation) / rec.current_allocation * 100
                    direction = "increase" if percent_change > 0 else "decrease"
                    
                    md_lines.append(
                        f"| {rec.resource_type.value} | "
                        f"{rec.current_allocation:.2f} | "
                        f"{rec.recommended_allocation:.2f} | "
                        f"{direction} by {abs(percent_change):.1f}% | "
                        f"{rec.confidence:.0%} |"
                    )
                
                md_lines.extend([
                    f"",
                    f"## Justifications",
                    f"",
                ])
                
                for i, rec in enumerate(recommendations):
                    md_lines.extend([
                        f"### {i+1}. {rec.resource_type.value}",
                        f"",
                        f"{rec.justification}",
                        f"",
                        f"**Expected Impact**: {rec.impact_estimate}",
                        f"",
                    ])
            
            return Result.ok("\n".join(md_lines))
        
        elif format == ReportFormat.TEXT:
            # Generate text report
            text_lines = [
                f"Resource Optimization Recommendations",
                f"=====================================",
                f"",
                f"Simulation: {simulation.name} ({simulation.id})",
                f"",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"Optimization Goal: {goal.value}",
                f"Timeframe: {timeframe.value}",
                f"",
                f"Recommendations",
                f"---------------",
                f"",
            ]
            
            if not recommendations:
                text_lines.append(f"No recommendations at this time.")
            else:
                for i, rec in enumerate(recommendations):
                    percent_change = (rec.recommended_allocation - rec.current_allocation) / rec.current_allocation * 100
                    direction = "increase" if percent_change > 0 else "decrease"
                    
                    text_lines.extend([
                        f"{i+1}. {rec.resource_type.value}:",
                        f"   Current: {rec.current_allocation:.2f}",
                        f"   Recommended: {rec.recommended_allocation:.2f}",
                        f"   Change: {direction} by {abs(percent_change):.1f}%",
                        f"   Confidence: {rec.confidence:.0%}",
                        f"",
                        f"   Justification: {rec.justification}",
                        f"",
                        f"   Expected Impact: {rec.impact_estimate}",
                        f"",
                    ])
            
            return Result.ok("\n".join(text_lines))
        
        else:
            return Result.err(f"Unsupported report format: {format}")
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """Get a previously generated report."""
        return self.generated_reports.get(report_id)