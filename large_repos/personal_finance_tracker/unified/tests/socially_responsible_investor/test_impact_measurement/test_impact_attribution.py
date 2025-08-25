"""Tests for impact attribution and alignment with UN SDGs."""

import pytest
from datetime import date, datetime
from typing import Dict, List, Any

from ethical_finance.models import Investment, Portfolio, ImpactMetric, ImpactData
from ethical_finance.impact_measurement.impact import (
    ImpactMeasurementEngine,
    ImpactReport,
    create_default_impact_metrics
)


class TestImpactAttribution:
    """Test class for impact attribution and alignment with UN Sustainable Development Goals."""
    
    def test_sdg_alignment_analysis(self, sample_investments):
        """Test analyzing investment alignment with UN Sustainable Development Goals."""
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
        
        # Create additional impact data related to SDGs
        sdg_data = {
            "sdg7_clean_energy_contribution": 0.85,  # Contribution to SDG 7 (Affordable and Clean Energy)
            "sdg8_decent_work_score": 0.72,  # Contribution to SDG 8 (Decent Work and Economic Growth)
            "sdg12_responsible_consumption": 0.65,  # Contribution to SDG 12 (Responsible Consumption and Production)
            "sdg13_climate_action": 0.78  # Contribution to SDG 13 (Climate Action)
        }
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Analyze SDG alignment
        result = engine.analyze_sdg_alignment(investment, sdg_data)
        
        # Verify result
        assert isinstance(result, dict)
        assert "sdg_alignment_scores" in result
        assert "primary_sdgs" in result
        assert "secondary_sdgs" in result
        assert "overall_sdg_alignment" in result
        
        # Check SDG scores
        for sdg, score in result["sdg_alignment_scores"].items():
            assert isinstance(sdg, str)
            assert isinstance(score, float)
            assert 0 <= score <= 1.0
            
        # Check primary and secondary SDGs lists
        assert isinstance(result["primary_sdgs"], list)
        assert isinstance(result["secondary_sdgs"], list)
        assert len(result["primary_sdgs"]) <= 3  # Should identify top contributing SDGs
        
        # Check overall alignment score
        assert 0 <= result["overall_sdg_alignment"] <= 1.0
        
    def test_impact_attribution_by_dollar(self, sample_portfolio, sample_investments):
        """Test attributing impact metrics per dollar invested."""
        # Convert sample portfolio to Portfolio model
        holdings = []
        for holding_data in sample_portfolio["holdings"]:
            holdings.append({
                "investment_id": holding_data["investment_id"],
                "shares": holding_data["shares"],
                "purchase_price": holding_data["purchase_price"],
                "purchase_date": date.fromisoformat(holding_data["purchase_date"]),
                "current_price": holding_data["current_price"],
                "current_value": holding_data["current_value"]
            })
        
        portfolio = Portfolio(
            portfolio_id=sample_portfolio["portfolio_id"],
            name=sample_portfolio["name"],
            holdings=holdings,
            total_value=sample_portfolio["total_value"],
            cash_balance=sample_portfolio["cash_balance"],
            creation_date=date.fromisoformat(sample_portfolio["creation_date"]),
            last_updated=date.fromisoformat(sample_portfolio["last_updated"])
        )
        
        # Convert sample investments to Investment models
        investments_dict = {}
        for inv_data in sample_investments:
            # Only include investments that are in the portfolio
            if inv_data["id"] in [h.investment_id for h in portfolio.holdings]:
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
                "renewable_energy_generated_kwh": 1200000 + (i * 200000),  # kWh
                "co2_emissions_avoided_tons": 500 + (i * 100),  # tons
                "water_saved_gallons": 50000 + (i * 10000),  # gallons
                "jobs_created": 50 + (i * 10)  # count
            }
            for i, inv_id in enumerate(investments_dict.keys())
        }
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Calculate per-dollar impact attribution
        result = engine.calculate_impact_per_dollar(portfolio, investments_dict, impact_data)
        
        # Verify result
        assert isinstance(result, dict)
        assert "total_portfolio_value" in result
        assert "impact_per_dollar" in result
        assert "impact_per_investment" in result
        
        # Check impact per dollar metrics
        impact_per_dollar = result["impact_per_dollar"]
        assert "renewable_energy_generated_kwh" in impact_per_dollar
        assert "co2_emissions_avoided_tons" in impact_per_dollar
        assert "water_saved_gallons" in impact_per_dollar
        assert "jobs_created" in impact_per_dollar
        
        # Check impact per investment
        for inv_id, metrics in result["impact_per_investment"].items():
            assert inv_id in investments_dict
            assert "weight" in metrics
            assert "impact_metrics" in metrics
            assert "attribution_percentage" in metrics
            
            # Ensure weight is between 0 and 1
            assert 0 <= metrics["weight"] <= 1.0
            
            # Ensure attribution percentage is between 0 and 100
            assert 0 <= metrics["attribution_percentage"] <= 100.0
            
    def test_comparative_impact_analysis(self, sample_investments, sample_impact_data):
        """Test comparing investment impact against industry benchmarks."""
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
            
        # Define industry benchmarks for impact metrics
        industry_benchmarks = {
            "Technology": {
                "carbon_emissions": 5000000,  # tons
                "renewable_energy_percentage": 0.60,
                "water_usage": 500000,  # gallons
                "community_investment": 15000000  # dollars
            },
            "Energy": {
                "carbon_emissions": 80000000,  # tons
                "renewable_energy_percentage": 0.15,
                "water_usage": 2000000,  # gallons
                "community_investment": 20000000  # dollars
            },
            "Consumer Cyclical": {
                "carbon_emissions": 8000000,  # tons
                "renewable_energy_percentage": 0.40,
                "water_usage": 700000,  # gallons
                "community_investment": 10000000  # dollars
            },
            "Consumer Defensive": {
                "carbon_emissions": 4000000,  # tons
                "renewable_energy_percentage": 0.30,
                "water_usage": 900000,  # gallons
                "community_investment": 8000000  # dollars
            }
        }
        
        # Initialize engine with default metrics
        metrics = create_default_impact_metrics()
        engine = ImpactMeasurementEngine(metrics)
        
        # Compare investment impact against industry benchmarks
        results = {}
        for investment in investments:
            # Get company's impact data
            company_data = None
            if investment.id in sample_impact_data:
                company_data = sample_impact_data[investment.id]
                
            if company_data and investment.sector in industry_benchmarks:
                sector_benchmark = industry_benchmarks[investment.sector]
                
                # Calculate comparative impact
                result = engine.compare_to_industry_benchmark(
                    investment, company_data, sector_benchmark
                )
                
                results[investment.id] = result
                
        # Verify at least some results were calculated
        assert len(results) > 0
        
        # Check result structure
        for investment_id, result in results.items():
            assert "sector" in result
            assert "metrics_comparison" in result
            assert "overall_comparison" in result
            assert "percentile_in_industry" in result
            
            # Check metrics comparison
            metrics_comparison = result["metrics_comparison"]
            for metric, comparison in metrics_comparison.items():
                assert "investment_value" in comparison
                assert "benchmark_value" in comparison
                assert "percentage_difference" in comparison
                assert "better_than_benchmark" in comparison
                
            # Check overall comparison
            assert isinstance(result["overall_comparison"], float)
            
            # Check percentile
            assert 0 <= result["percentile_in_industry"] <= 100