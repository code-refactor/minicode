"""Impact measurement engine for tracking and quantifying investment impact."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import date
import time
import pandas as pd
import numpy as np
from dataclasses import dataclass

from ethical_finance.models import Investment, Portfolio, ImpactMetric, ImpactData


@dataclass
class ImpactMetricDefinition:
    """Definition of an impact metric used for measurement."""
    
    id: str
    name: str
    category: str
    unit: str
    description: str
    higher_is_better: bool
    data_source: str
    normalization_factor: Optional[str] = None
    benchmark: Optional[float] = None


@dataclass
class ImpactReport:
    """Report containing impact metrics for a portfolio or investment."""
    
    entity_id: str
    entity_type: str  # "portfolio" or "investment"
    report_date: date
    metrics: Dict[str, float]
    normalized_metrics: Dict[str, float]
    benchmark_comparison: Dict[str, float]
    historical_data: Optional[Dict[str, List[Tuple[date, float]]]] = None
    processing_time_ms: float = 0


class ImpactMeasurementEngine:
    """Engine for measuring and quantifying the impact of investments."""
    
    def __init__(self, metrics: List[ImpactMetricDefinition]):
        """Initialize with the specified impact metrics.
        
        Args:
            metrics: List of impact metrics to track
        """
        self.metrics = {metric.id: metric for metric in metrics}
    
    def measure_investment_impact(
        self, 
        investment: Investment, 
        impact_data: Optional[Dict[str, Any]] = None
    ) -> ImpactReport:
        """Measure the impact of a single investment.
        
        Args:
            investment: The investment to measure
            impact_data: Optional additional impact data not in the investment model
            
        Returns:
            An ImpactReport containing the calculated metrics
        """
        start_time = time.time()
        
        metrics = {}
        normalized_metrics = {}
        benchmark_comparison = {}
        
        # Process environmental metrics
        metrics["carbon_intensity"] = investment.carbon_footprint / investment.market_cap * 1e9  # tons CO2 per $B
        normalized_metrics["carbon_intensity"] = self._normalize_metric("carbon_intensity", metrics["carbon_intensity"])
        benchmark_comparison["carbon_intensity"] = self._compare_to_benchmark("carbon_intensity", metrics["carbon_intensity"])
        
        metrics["renewable_energy_percentage"] = investment.renewable_energy_use * 100  # Convert to percentage
        normalized_metrics["renewable_energy_percentage"] = self._normalize_metric("renewable_energy_percentage", metrics["renewable_energy_percentage"])
        benchmark_comparison["renewable_energy_percentage"] = self._compare_to_benchmark("renewable_energy_percentage", metrics["renewable_energy_percentage"])
        
        # Process social metrics
        metrics["diversity_score"] = investment.diversity_score * 100  # Convert to percentage
        normalized_metrics["diversity_score"] = self._normalize_metric("diversity_score", metrics["diversity_score"])
        benchmark_comparison["diversity_score"] = self._compare_to_benchmark("diversity_score", metrics["diversity_score"])
        
        # Process governance metrics
        metrics["board_independence"] = investment.board_independence * 100  # Convert to percentage
        normalized_metrics["board_independence"] = self._normalize_metric("board_independence", metrics["board_independence"])
        benchmark_comparison["board_independence"] = self._compare_to_benchmark("board_independence", metrics["board_independence"])
        
        # Include additional impact data if provided
        if impact_data:
            for metric_id, value in impact_data.items():
                if metric_id in self.metrics:
                    metrics[metric_id] = value
                    normalized_metrics[metric_id] = self._normalize_metric(metric_id, value)
                    benchmark_comparison[metric_id] = self._compare_to_benchmark(metric_id, value)
        
        processing_time = (time.time() - start_time) * 1000
        
        return ImpactReport(
            entity_id=investment.id,
            entity_type="investment",
            report_date=date.today(),
            metrics=metrics,
            normalized_metrics=normalized_metrics,
            benchmark_comparison=benchmark_comparison,
            processing_time_ms=processing_time
        )
    
    def measure_portfolio_impact(
        self, 
        portfolio: Portfolio, 
        investments: Dict[str, Investment],
        impact_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> ImpactReport:
        """Measure the aggregate impact of a portfolio of investments.
        
        Args:
            portfolio: The portfolio to measure
            investments: Dict mapping investment IDs to Investment objects
            impact_data: Optional dict mapping investment IDs to additional impact data
            
        Returns:
            An ImpactReport containing the calculated metrics for the portfolio
        """
        start_time = time.time()
        
        # Calculate the weight of each investment in the portfolio
        total_value = portfolio.total_value
        weights = {
            holding.investment_id: holding.current_value / total_value
            for holding in portfolio.holdings
        }
        
        # Collect individual investment impacts
        investment_impacts = {}
        for holding in portfolio.holdings:
            investment_id = holding.investment_id
            if investment_id in investments:
                investment_data = impact_data.get(investment_id, {}) if impact_data else {}
                investment_impacts[investment_id] = self.measure_investment_impact(
                    investments[investment_id], investment_data
                )
        
        # Aggregate impacts across the portfolio
        portfolio_metrics = {}
        portfolio_normalized = {}
        portfolio_benchmark = {}
        
        for metric_id in self.metrics:
            # Use weighted average for most metrics
            if metric_id in ["renewable_energy_percentage", "diversity_score", "board_independence"]:
                portfolio_metrics[metric_id] = sum(
                    impact.metrics.get(metric_id, 0) * weights[impact.entity_id]
                    for impact in investment_impacts.values()
                    if impact.entity_id in weights
                )
            # For carbon intensity, weighted sum is appropriate
            elif metric_id == "carbon_intensity":
                portfolio_metrics[metric_id] = sum(
                    impact.metrics.get(metric_id, 0) * weights[impact.entity_id]
                    for impact in investment_impacts.values()
                    if impact.entity_id in weights
                )
            
            # Normalize and benchmark the aggregated metrics
            if metric_id in portfolio_metrics:
                portfolio_normalized[metric_id] = self._normalize_metric(metric_id, portfolio_metrics[metric_id])
                portfolio_benchmark[metric_id] = self._compare_to_benchmark(metric_id, portfolio_metrics[metric_id])
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        return ImpactReport(
            entity_id=portfolio.portfolio_id,
            entity_type="portfolio",
            report_date=date.today(),
            metrics=portfolio_metrics,
            normalized_metrics=portfolio_normalized,
            benchmark_comparison=portfolio_benchmark,
            processing_time_ms=processing_time
        )
    
    def analyze_historical_impact(
        self,
        entity_id: str,
        historical_data: Dict[str, List[Tuple[date, float]]],
        entity_type: str = "investment"
    ) -> Dict[str, Any]:
        """Analyze historical impact data to identify trends.
        
        Args:
            entity_id: ID of the investment or portfolio
            historical_data: Dict mapping metric IDs to lists of (date, value) tuples
            entity_type: Type of entity ("investment" or "portfolio")
            
        Returns:
            Dict containing trend analysis results
        """
        results = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "trends": {},
            "year_over_year": {},
            "improvement_metrics": []
        }
        
        for metric_id, data_points in historical_data.items():
            if metric_id not in self.metrics:
                continue
                
            metric = self.metrics[metric_id]
            
            # Sort data by date
            sorted_data = sorted(data_points, key=lambda x: x[0])
            dates = [d[0] for d in sorted_data]
            values = [d[1] for d in sorted_data]
            
            # Skip metrics with too few data points
            if len(values) < 2:
                continue
            
            # Create a pandas Series for analysis
            series = pd.Series(values, index=dates)
            
            # Calculate trend (slope of linear regression)
            x = np.arange(len(series))
            slope, intercept = np.polyfit(x, series.values, 1)
            
            # Determine if trend is positive based on higher_is_better
            trend_direction = "improving" if (slope > 0) == metric.higher_is_better else "worsening"
            
            # Calculate year-over-year change if we have at least 2 years
            if len(series) >= 2:
                yoy_change = series.iloc[-1] - series.iloc[0]
                yoy_percent = (yoy_change / series.iloc[0]) * 100 if series.iloc[0] != 0 else float('inf')
            else:
                yoy_change = 0
                yoy_percent = 0
            
            # Track metrics showing improvement
            is_improving = (yoy_change > 0) == metric.higher_is_better
            if is_improving:
                results["improvement_metrics"].append(metric_id)
            
            # Store results
            results["trends"][metric_id] = {
                "slope": slope,
                "direction": trend_direction,
                "is_improving": is_improving
            }
            
            results["year_over_year"][metric_id] = {
                "absolute_change": yoy_change,
                "percent_change": yoy_percent
            }
        
        return results
    
    def calculate_financial_impact_correlation(
        self,
        impact_data: Dict[str, List[Tuple[date, float]]],
        financial_data: List[Tuple[date, float]]
    ) -> Dict[str, float]:
        """Calculate correlation between impact metrics and financial performance.
        
        Args:
            impact_data: Dict mapping metric IDs to lists of (date, value) tuples
            financial_data: List of (date, value) tuples for financial performance
            
        Returns:
            Dict mapping metric IDs to correlation coefficients (-1 to 1)
        """
        # Convert financial data to pandas Series
        financial_series = pd.Series(
            [d[1] for d in financial_data],
            index=[d[0] for d in financial_data]
        )
        
        correlations = {}
        
        for metric_id, data_points in impact_data.items():
            # Convert impact data to pandas Series
            impact_series = pd.Series(
                [d[1] for d in data_points],
                index=[d[0] for d in data_points]
            )
            
            # Align the series on the same dates
            aligned_data = pd.concat([impact_series, financial_series], axis=1).dropna()
            
            # Skip if not enough aligned data points
            if len(aligned_data) < 2:
                correlations[metric_id] = None
                continue
            
            # Calculate correlation
            corr = aligned_data.corr().iloc[0, 1]
            correlations[metric_id] = corr
        
        return correlations
    
    def _normalize_metric(self, metric_id: str, value: float) -> float:
        """Normalize a metric value to a 0-100 scale.
        
        Args:
            metric_id: ID of the metric
            value: Raw metric value
            
        Returns:
            Normalized value (0-100)
        """
        if metric_id not in self.metrics:
            return 0
            
        metric = self.metrics[metric_id]
        
        # Define min/max ranges for each metric
        ranges = {
            "carbon_intensity": (0, 200),  # tons CO2 per $B
            "renewable_energy_percentage": (0, 100),  # percentage
            "diversity_score": (0, 100),  # percentage
            "board_independence": (0, 100),  # percentage
        }
        
        if metric_id in ranges:
            min_val, max_val = ranges[metric_id]
            
            # Normalize to 0-100 scale
            normalized = (value - min_val) / (max_val - min_val) * 100
            
            # Invert if lower is better
            if not metric.higher_is_better:
                normalized = 100 - normalized
                
            # Clamp to 0-100
            return max(0, min(100, normalized))
        
        return 50  # Default neutral value for unknown metrics
    
    def _compare_to_benchmark(self, metric_id: str, value: float) -> float:
        """Compare a metric value to its benchmark.
        
        Args:
            metric_id: ID of the metric
            value: Raw metric value
            
        Returns:
            Percentage relative to benchmark (>1 means better than benchmark)
        """
        if metric_id not in self.metrics:
            return 1.0
            
        metric = self.metrics[metric_id]
        
        # Define benchmarks for each metric
        benchmarks = {
            "carbon_intensity": 100,  # tons CO2 per $B (lower is better)
            "renewable_energy_percentage": 50,  # percentage (higher is better)
            "diversity_score": 60,  # percentage (higher is better)
            "board_independence": 70,  # percentage (higher is better)
        }
        
        if metric_id in benchmarks:
            benchmark = benchmarks[metric_id]
            
            # Calculate ratio to benchmark
            if metric.higher_is_better:
                return value / benchmark
            else:
                return benchmark / value if value > 0 else float('inf')
        
        return 1.0  # Default neutral value for unknown metrics
        
    def analyze_sdg_alignment(
        self, 
        investment: Investment, 
        sdg_data: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze investment alignment with UN Sustainable Development Goals (SDGs).
        
        Args:
            investment: The investment to analyze
            sdg_data: Dictionary containing SDG-related metrics for the investment
                (e.g., {"sdg7_clean_energy_contribution": 0.85})
                
        Returns:
            Dictionary with SDG alignment analysis results
        """
        # SDG definitions for reference
        sdg_definitions = {
            "sdg1": "No Poverty",
            "sdg2": "Zero Hunger",
            "sdg3": "Good Health and Well-being",
            "sdg4": "Quality Education",
            "sdg5": "Gender Equality",
            "sdg6": "Clean Water and Sanitation",
            "sdg7": "Affordable and Clean Energy",
            "sdg8": "Decent Work and Economic Growth",
            "sdg9": "Industry, Innovation and Infrastructure",
            "sdg10": "Reduced Inequality",
            "sdg11": "Sustainable Cities and Communities",
            "sdg12": "Responsible Consumption and Production",
            "sdg13": "Climate Action",
            "sdg14": "Life Below Water",
            "sdg15": "Life on Land",
            "sdg16": "Peace, Justice and Strong Institutions",
            "sdg17": "Partnerships for the Goals"
        }
        
        # Extract SDG alignment scores from provided data
        sdg_alignment_scores = {}
        for key, value in sdg_data.items():
            # Extract SDG number from key
            if key.startswith("sdg") and "_" in key:
                sdg_number = key.split("_")[0]
                if sdg_number in sdg_definitions:
                    sdg_alignment_scores[sdg_number] = value
        
        # Default scores for SDGs based on ESG ratings and company attributes
        if "sdg13" not in sdg_alignment_scores:  # Climate Action
            sdg_alignment_scores["sdg13"] = max(0, min(1.0, 1.0 - (investment.carbon_footprint / 100000000)))
            
        if "sdg7" not in sdg_alignment_scores:  # Affordable and Clean Energy
            sdg_alignment_scores["sdg7"] = investment.renewable_energy_use
            
        if "sdg5" not in sdg_alignment_scores:  # Gender Equality
            sdg_alignment_scores["sdg5"] = investment.diversity_score
            
        if "sdg16" not in sdg_alignment_scores:  # Peace, Justice and Strong Institutions
            sdg_alignment_scores["sdg16"] = investment.board_independence
        
        # Determine primary and secondary SDGs
        sorted_sdgs = sorted(
            sdg_alignment_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        primary_sdgs = [sdg for sdg, score in sorted_sdgs[:3] if score >= 0.7]
        secondary_sdgs = [sdg for sdg, score in sorted_sdgs[3:6] if score >= 0.4]
        
        # Calculate overall SDG alignment score (weighted average)
        overall_sdg_alignment = sum(sdg_alignment_scores.values()) / len(sdg_alignment_scores) if sdg_alignment_scores else 0
        
        # Combine results
        result = {
            "investment_id": investment.id,
            "investment_name": investment.name,
            "sdg_alignment_scores": sdg_alignment_scores,
            "primary_sdgs": primary_sdgs,
            "secondary_sdgs": secondary_sdgs,
            "overall_sdg_alignment": overall_sdg_alignment
        }
        
        return result
        
    def calculate_impact_per_dollar(
        self,
        portfolio: Portfolio,
        investments: Dict[str, Investment],
        impact_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate impact metrics per dollar invested in the portfolio.
        
        Args:
            portfolio: The portfolio to analyze
            investments: Dict mapping investment IDs to Investment objects
            impact_data: Dict mapping investment IDs to impact data
                
        Returns:
            Dictionary with impact per dollar metrics
        """
        # Calculate portfolio value and weights
        total_portfolio_value = portfolio.total_value
        investment_weights = {}
        impact_per_investment = {}
        
        # Collect and aggregate impact data per investment
        aggregate_impact = {
            "renewable_energy_generated_kwh": 0,
            "co2_emissions_avoided_tons": 0,
            "water_saved_gallons": 0,
            "jobs_created": 0
        }
        
        # Process each holding in the portfolio
        for holding in portfolio.holdings:
            investment_id = holding.investment_id
            
            # Skip if investment data is not available
            if investment_id not in investments or investment_id not in impact_data:
                continue
                
            # Calculate weight of this investment in the portfolio
            weight = holding.current_value / total_portfolio_value
            investment_weights[investment_id] = weight
            
            # Get investment impact data
            inv_impact = impact_data[investment_id]
            
            # Calculate attribution percentage (how much of the company's impact is attributable to the portfolio)
            investment = investments[investment_id]
            company_value = investment.market_cap
            attribution_percentage = (holding.current_value / company_value) * 100 if company_value > 0 else 0
            
            # Calculate absolute impact contribution to the portfolio
            investment_impact = {}
            for metric, value in inv_impact.items():
                if metric in aggregate_impact:
                    attributed_value = value * (attribution_percentage / 100)
                    investment_impact[metric] = attributed_value
                    aggregate_impact[metric] += attributed_value
            
            # Store results for this investment
            impact_per_investment[investment_id] = {
                "weight": weight,
                "attribution_percentage": attribution_percentage,
                "impact_metrics": investment_impact
            }
        
        # Calculate impact per dollar invested
        impact_per_dollar = {}
        for metric, total_value in aggregate_impact.items():
            impact_per_dollar[metric] = total_value / total_portfolio_value if total_portfolio_value > 0 else 0
        
        # Compile the final result
        result = {
            "total_portfolio_value": total_portfolio_value,
            "impact_per_dollar": impact_per_dollar,
            "impact_per_investment": impact_per_investment,
            "total_impact": aggregate_impact
        }
        
        return result
        
    def compare_to_industry_benchmark(
        self,
        investment: Investment,
        company_data: Dict[str, Any],
        industry_benchmark: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare investment impact metrics against industry benchmarks.
        
        Args:
            investment: The investment to analyze
            company_data: Company-specific impact data
            industry_benchmark: Benchmark data for the investment's industry
                
        Returns:
            Dictionary with comparative analysis results
        """
        # Initialize results
        metrics_comparison = {}
        
        # Compare metrics where there's both company data and benchmark data
        for metric, benchmark_value in industry_benchmark.items():
            # Get company value for this metric
            company_value = None
            
            # Check in company_data first
            if metric in company_data:
                company_value = company_data[metric]
            # Check in investment basic data
            elif metric == "carbon_emissions":
                company_value = investment.carbon_footprint
            elif metric == "renewable_energy_percentage":
                company_value = investment.renewable_energy_use * 100  # Convert to percentage
            
            # Skip if we don't have company data for this metric
            if company_value is None:
                continue
                
            # Determine if higher or lower is better for this metric
            higher_is_better = True
            if metric in ["carbon_emissions", "water_usage"]:
                higher_is_better = False
                
            # Calculate percentage difference from benchmark
            percent_diff = ((company_value - benchmark_value) / benchmark_value) * 100
            
            # Determine if better than benchmark
            better_than_benchmark = (
                (percent_diff > 0 and higher_is_better) or
                (percent_diff < 0 and not higher_is_better)
            )
            
            # Compile comparison for this metric
            metrics_comparison[metric] = {
                "investment_value": company_value,
                "benchmark_value": benchmark_value,
                "percentage_difference": percent_diff,
                "better_than_benchmark": better_than_benchmark
            }
        
        # Calculate overall comparison score (-100 to 100, where positive is better than benchmark)
        overall_comparison = 0
        if metrics_comparison:
            score_sum = 0
            for metric, comparison in metrics_comparison.items():
                # Normalize percentage difference to -1 to 1 range
                norm_diff = comparison["percentage_difference"] / 100
                
                # Invert if lower is better
                if metric in ["carbon_emissions", "water_usage"]:
                    norm_diff = -norm_diff
                    
                score_sum += norm_diff
                
            # Average across all metrics and scale to -100 to 100
            overall_comparison = (score_sum / len(metrics_comparison)) * 100
        
        # Estimate percentile in industry (simplified calculation)
        # A positive overall comparison above 20 is considered upper quartile
        if overall_comparison > 20:
            percentile = 75 + (overall_comparison - 20) / 80 * 25  # 75th to 100th percentile
        elif overall_comparison > 0:
            percentile = 50 + overall_comparison / 20 * 25  # 50th to 75th percentile
        elif overall_comparison > -20:
            percentile = 25 + (overall_comparison + 20) / 20 * 25  # 25th to 50th percentile
        else:
            percentile = max(1, 25 + (overall_comparison + 20) / 80 * 24)  # 1st to 25th percentile
            
        # Cap percentile between 1 and 100
        percentile = max(1, min(100, percentile))
        
        # Compile final result
        result = {
            "investment_id": investment.id,
            "investment_name": investment.name,
            "sector": investment.sector,
            "industry": investment.industry,
            "metrics_comparison": metrics_comparison,
            "overall_comparison": overall_comparison,
            "percentile_in_industry": percentile
        }
        
        return result


def create_default_impact_metrics() -> List[ImpactMetricDefinition]:
    """Create a default set of impact metrics.
    
    Returns:
        List of default ImpactMetricDefinition objects
    """
    return [
        ImpactMetricDefinition(
            id="carbon_intensity",
            name="Carbon Intensity",
            category="environmental",
            unit="tons CO2/$B",
            description="Carbon emissions per billion dollars of market cap",
            higher_is_better=False,
            data_source="company_reports",
            benchmark=100
        ),
        ImpactMetricDefinition(
            id="renewable_energy_percentage",
            name="Renewable Energy Use",
            category="environmental",
            unit="%",
            description="Percentage of energy from renewable sources",
            higher_is_better=True,
            data_source="company_reports",
            benchmark=50
        ),
        ImpactMetricDefinition(
            id="diversity_score",
            name="Workforce Diversity",
            category="social",
            unit="%",
            description="Score representing workforce diversity",
            higher_is_better=True,
            data_source="company_reports",
            benchmark=60
        ),
        ImpactMetricDefinition(
            id="board_independence",
            name="Board Independence",
            category="governance",
            unit="%",
            description="Percentage of independent board members",
            higher_is_better=True,
            data_source="company_reports",
            benchmark=70
        ),
        ImpactMetricDefinition(
            id="community_investment",
            name="Community Investment",
            category="social",
            unit="$M",
            description="Millions of dollars invested in community projects",
            higher_is_better=True,
            data_source="company_reports",
            benchmark=5
        ),
        ImpactMetricDefinition(
            id="water_usage",
            name="Water Usage",
            category="environmental",
            unit="kgal/$M",
            description="Thousands of gallons used per million dollars of revenue",
            higher_is_better=False,
            data_source="company_reports",
            benchmark=500
        )
    ]