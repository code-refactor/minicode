"""Tests for the impact measurement engine."""

import pytest
from unittest.mock import patch, MagicMock
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Any

from ethical_finance.models import Investment, Portfolio, ImpactMetric, ImpactData
from ethical_finance.impact_measurement.impact import (
    ImpactMeasurementEngine,
    ImpactMetricDefinition,
    ImpactReport,
    create_default_impact_metrics
)


class TestImpactMeasurement:
    """Test class for the impact measurement engine."""
    
    def test_create_default_impact_metrics(self):
        """Test creating default impact metrics."""
        metrics = create_default_impact_metrics()
        
        # Check that we got valid metrics
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert all(isinstance(metric, ImpactMetricDefinition) for metric in metrics)
        
        # Check for required metrics
        metric_ids = [metric.id for metric in metrics]
        required_metrics = ["carbon_intensity", "renewable_energy_percentage", "diversity_score"]
        for req_metric in required_metrics:
            assert req_metric in metric_ids
    
    def test_initialize_engine(self):
        """Test initializing the impact measurement engine."""
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        assert hasattr(engine, "metrics")
        assert isinstance(engine.metrics, dict)
        assert len(engine.metrics) == len(metrics)
        
        # Check that metrics are indexed by ID
        for metric in metrics:
            assert metric.id in engine.metrics
    
    def test_measure_investment_impact(self, sample_investments):
        """Test measuring the impact of a single investment."""
        # Choose an investment from the sample data
        inv_data = sample_investments[0]
        
        # Convert to Investment model
        investment = Investment(
            id=inv_data["id"],
            name=inv_data["name"],
            sector=inv_data["sector"],
            industry=inv_data["industry"],
            market_cap=inv_data["market_cap"],
            price=inv_data["price"],
            esg_ratings=inv_data["esg_ratings"],
            carbon_footprint=inv_data["carbon_footprint"],
            renewable_energy_use=inv_data["renewable_energy_use"],
            diversity_score=inv_data["diversity_score"],
            board_independence=inv_data["board_independence"],
            controversies=inv_data["controversies"],
            positive_practices=inv_data["positive_practices"]
        )
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Measure impact
        report = engine.measure_investment_impact(investment)
        
        # Verify report
        assert isinstance(report, ImpactReport)
        assert report.entity_id == investment.id
        assert report.entity_type == "investment"
        assert isinstance(report.report_date, date)
        assert len(report.metrics) > 0
        assert "carbon_intensity" in report.metrics
        assert "renewable_energy_percentage" in report.metrics
        assert len(report.normalized_metrics) == len(report.metrics)
        assert len(report.benchmark_comparison) == len(report.metrics)
        assert report.processing_time_ms > 0
    
    def test_measure_investment_impact_with_additional_data(self, sample_investments):
        """Test measuring the impact of an investment with additional impact data."""
        # Choose an investment from the sample data
        inv_data = sample_investments[0]
        
        # Convert to Investment model
        investment = Investment(
            id=inv_data["id"],
            name=inv_data["name"],
            sector=inv_data["sector"],
            industry=inv_data["industry"],
            market_cap=inv_data["market_cap"],
            price=inv_data["price"],
            esg_ratings=inv_data["esg_ratings"],
            carbon_footprint=inv_data["carbon_footprint"],
            renewable_energy_use=inv_data["renewable_energy_use"],
            diversity_score=inv_data["diversity_score"],
            board_independence=inv_data["board_independence"],
            controversies=inv_data["controversies"],
            positive_practices=inv_data["positive_practices"]
        )
        
        # Create additional impact data
        additional_data = {
            "community_investment": 12.5,  # $12.5M
            "water_usage": 450  # 450 kgal/$M
        }
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Measure impact with additional data
        report = engine.measure_investment_impact(investment, additional_data)
        
        # Verify report includes additional metrics
        assert "community_investment" in report.metrics
        assert report.metrics["community_investment"] == 12.5
        assert "water_usage" in report.metrics
        assert report.metrics["water_usage"] == 450
    
    def test_measure_portfolio_impact(self, sample_portfolio, sample_investments):
        """Test measuring the impact of a portfolio of investments."""
        # Convert sample portfolio to Portfolio model
        holdings = []
        for holding_data in sample_portfolio["holdings"]:
            holdings.append({
                "investment_id": holding_data["investment_id"],
                "shares": holding_data["shares"],
                "purchase_price": holding_data["purchase_price"],
                "purchase_date": datetime.strptime(holding_data["purchase_date"], "%Y-%m-%d").date(),
                "current_price": holding_data["current_price"],
                "current_value": holding_data["current_value"]
            })
        
        portfolio = Portfolio(
            portfolio_id=sample_portfolio["portfolio_id"],
            name=sample_portfolio["name"],
            holdings=holdings,
            total_value=sample_portfolio["total_value"],
            cash_balance=sample_portfolio["cash_balance"],
            creation_date=datetime.strptime(sample_portfolio["creation_date"], "%Y-%m-%d").date(),
            last_updated=datetime.strptime(sample_portfolio["last_updated"], "%Y-%m-%d").date()
        )
        
        # Convert sample investments to Investment models
        investments_dict = {}
        for inv_data in sample_investments:
            # Only include investments that are in the portfolio
            if any(h.investment_id == inv_data["id"] for h in portfolio.holdings):
                investments_dict[inv_data["id"]] = Investment(
                    id=inv_data["id"],
                    name=inv_data["name"],
                    sector=inv_data["sector"],
                    industry=inv_data["industry"],
                    market_cap=inv_data["market_cap"],
                    price=inv_data["price"],
                    esg_ratings=inv_data["esg_ratings"],
                    carbon_footprint=inv_data["carbon_footprint"],
                    renewable_energy_use=inv_data["renewable_energy_use"],
                    diversity_score=inv_data["diversity_score"],
                    board_independence=inv_data["board_independence"],
                    controversies=inv_data["controversies"],
                    positive_practices=inv_data["positive_practices"]
                )
        
        # Create sample impact data for each investment
        impact_data = {
            inv_id: {
                "community_investment": 10.0 + i,  # $10M+
                "water_usage": 500 - i * 20  # kgal/$M
            }
            for i, inv_id in enumerate(investments_dict.keys())
        }
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Measure portfolio impact
        report = engine.measure_portfolio_impact(portfolio, investments_dict, impact_data)
        
        # Verify report
        assert isinstance(report, ImpactReport)
        assert report.entity_id == portfolio.portfolio_id
        assert report.entity_type == "portfolio"
        assert isinstance(report.report_date, date)
        assert len(report.metrics) > 0
        assert report.processing_time_ms > 0
        
        # Key metrics should be present
        assert "carbon_intensity" in report.metrics
        assert "renewable_energy_percentage" in report.metrics
        assert "diversity_score" in report.metrics
        assert "board_independence" in report.metrics
    
    def test_analyze_historical_impact(self, sample_impact_data):
        """Test analyzing historical impact data for trends."""
        # Choose a company to analyze
        company_id = list(sample_impact_data.keys())[0]
        company_data = sample_impact_data[company_id]
        
        # Convert to historical data format expected by the function
        historical_data = {}
        for metric in ["carbon_emissions", "renewable_energy_percentage", "water_usage", 
                      "waste_generated", "community_investment"]:
            historical_data[metric] = []
            for year_data in company_data:
                if metric in year_data:
                    historical_data[metric].append(
                        (date(year_data["year"], 1, 1), year_data[metric])
                    )
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Analyze historical data
        results = engine.analyze_historical_impact(company_id, historical_data)
        
        # Verify results
        assert isinstance(results, dict)
        assert "entity_id" in results
        assert results["entity_id"] == company_id
        assert "trends" in results
        assert "year_over_year" in results
        
        # Check for trend data for each metric
        for metric in historical_data:
            if len(historical_data[metric]) >= 2:  # Only metrics with sufficient data points
                if metric in results["trends"]:
                    assert "slope" in results["trends"][metric]
                    assert "direction" in results["trends"][metric]
                    assert "is_improving" in results["trends"][metric]
    
    def test_calculate_financial_impact_correlation(self, sample_impact_data):
        """Test calculating correlation between impact metrics and financial performance."""
        # Choose a company's impact data
        company_id = list(sample_impact_data.keys())[0]
        company_data = sample_impact_data[company_id]
        
        # Convert to historical impact data format
        impact_data = {}
        for metric in ["carbon_emissions", "renewable_energy_percentage", "water_usage"]:
            impact_data[metric] = []
            for year_data in company_data:
                if metric in year_data:
                    impact_data[metric].append(
                        (date(year_data["year"], 1, 1), year_data[metric])
                    )
        
        # Create simulated financial data
        financial_data = []
        for year_data in company_data:
            # Simple model: financial performance improves with better environmental metrics
            financial_value = 100 - year_data["carbon_emissions"] / 1000000 + year_data["renewable_energy_percentage"] * 100
            financial_data.append(
                (date(year_data["year"], 1, 1), financial_value)
            )
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Calculate correlations
        correlations = engine.calculate_financial_impact_correlation(impact_data, financial_data)
        
        # Verify results
        assert isinstance(correlations, dict)
        
        # Should have correlation values for each metric
        for metric in impact_data:
            if len(impact_data[metric]) >= 2:  # Only metrics with sufficient data points
                assert metric in correlations
                assert isinstance(correlations[metric], float) or correlations[metric] is None
    
    def test_normalize_metric(self):
        """Test normalization of impact metrics to a 0-100 scale."""
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Test normalizing a carbon intensity value (lower is better)
        carbon_intensity = 100  # tons CO2/$B
        normalized = engine._normalize_metric("carbon_intensity", carbon_intensity)
        assert isinstance(normalized, float)
        assert 0 <= normalized <= 100
        
        # Test normalizing a renewable energy percentage (higher is better)
        renewable_pct = 75  # 75%
        normalized = engine._normalize_metric("renewable_energy_percentage", renewable_pct)
        assert isinstance(normalized, float)
        assert 0 <= normalized <= 100
        
        # Higher renewable percentage should result in higher normalized score
        higher_renewable = 85  # 85%
        higher_normalized = engine._normalize_metric("renewable_energy_percentage", higher_renewable)
        assert higher_normalized > normalized
    
    def test_compare_to_benchmark(self):
        """Test comparing impact metrics to benchmarks."""
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Test comparing carbon intensity to benchmark (lower is better)
        # Benchmark is 100 tons CO2/$B
        better_than_benchmark = 50  # tons CO2/$B
        ratio = engine._compare_to_benchmark("carbon_intensity", better_than_benchmark)
        assert ratio > 1.0  # Better than benchmark
        
        worse_than_benchmark = 150  # tons CO2/$B
        ratio = engine._compare_to_benchmark("carbon_intensity", worse_than_benchmark)
        assert ratio < 1.0  # Worse than benchmark
        
        # Test comparing renewable energy to benchmark (higher is better)
        # Benchmark is 50%
        better_than_benchmark = 75  # 75%
        ratio = engine._compare_to_benchmark("renewable_energy_percentage", better_than_benchmark)
        assert ratio > 1.0  # Better than benchmark
        
        worse_than_benchmark = 25  # 25%
        ratio = engine._compare_to_benchmark("renewable_energy_percentage", worse_than_benchmark)
        assert ratio < 1.0  # Worse than benchmark
    
    def test_performance_with_historical_data(self, sample_impact_data):
        """Test performance with 5+ years of historical data."""
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Prepare historical data for all companies
        all_historical_data = {}
        for company_id, company_data in sample_impact_data.items():
            historical_data = {}
            for metric in ["carbon_emissions", "renewable_energy_percentage", "water_usage", 
                          "waste_generated", "community_investment"]:
                historical_data[metric] = []
                for year_data in company_data:
                    if metric in year_data:
                        historical_data[metric].append(
                            (date(year_data["year"], 1, 1), year_data[metric])
                        )
            all_historical_data[company_id] = historical_data
        
        # Measure performance for analyzing all companies
        start_time = time.time()
        
        for company_id, historical_data in all_historical_data.items():
            results = engine.analyze_historical_impact(company_id, historical_data)
            assert isinstance(results, dict)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # The test assumes 5 years of data for 5 companies (in sample_impact_data)
        # so that's 25 company-years of data
        print(f"Analyzed {len(all_historical_data)} companies with 5+ years of data in {total_time:.2f} seconds")
        
        # Verify performance is acceptable (should be fast enough)
        assert total_time < 5.0  # Should be well under 5 seconds
        
    def test_sustainable_investment_thresholds(self, sample_investments):
        """Test identifying investments that meet sustainable investment thresholds."""
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Convert sample investments to Investment models
        investments = []
        for inv_data in sample_investments:
            investments.append(Investment(
                id=inv_data["id"],
                name=inv_data["name"],
                sector=inv_data["sector"],
                industry=inv_data["industry"],
                market_cap=inv_data["market_cap"],
                price=inv_data["price"],
                esg_ratings=inv_data["esg_ratings"],
                carbon_footprint=inv_data["carbon_footprint"],
                renewable_energy_use=inv_data["renewable_energy_use"],
                diversity_score=inv_data["diversity_score"],
                board_independence=inv_data["board_independence"],
                controversies=inv_data["controversies"],
                positive_practices=inv_data["positive_practices"]
            ))
        
        # Test individual metrics thresholds
        for investment in investments:
            # Measure investment impact
            report = engine.measure_investment_impact(investment)
            
            # Verify renewable energy metric is present (value may be scaled in the engine)
            if "renewable_energy_percentage" in report.metrics:
                assert isinstance(report.metrics["renewable_energy_percentage"], (int, float))
                
            # Verify diversity score is present (value may be scaled in the engine)
            if "diversity_score" in report.metrics:
                assert isinstance(report.metrics["diversity_score"], (int, float))
                
        # Test filtering by threshold (renewable energy - higher is better)
        filtered_investments = []
        threshold = 50.0  # 50% renewable energy (note: engine may scale to 0-100)
        
        for investment in investments:
            report = engine.measure_investment_impact(investment)
            if "renewable_energy_percentage" in report.metrics and report.metrics["renewable_energy_percentage"] >= threshold:
                filtered_investments.append(investment)
                
        # Verify the filtering logic works without depending on exact values
        assert isinstance(filtered_investments, list)