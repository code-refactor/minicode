"""Tests for advanced portfolio analysis functionalities."""

import pytest
from datetime import date, datetime
from typing import Dict, List, Any

from ethical_finance.models import Investment, Portfolio
from ethical_finance.portfolio_analysis.analysis import (
    PortfolioAnalysisSystem,
    PortfolioCompositionResult,
    DiversificationAssessment
)
from ethical_finance.ethical_screening.screening import ScreeningResult


class TestAdvancedPortfolioAnalysis:
    """Test class for advanced portfolio analysis features."""
    
    def test_esg_theme_concentration_analysis(self, sample_portfolio, sample_investments):
        """Test analyzing ESG theme concentration in a portfolio."""
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
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Create a method to analyze ESG theme concentration
        result = analysis_system.analyze_esg_theme_concentration(portfolio, investments_dict)
        
        # Verify result includes theme concentration data
        assert isinstance(result, dict)
        assert "themes" in result
        assert "diversity" in result
        
        # Check theme data structure
        for theme, data in result["themes"].items():
            assert isinstance(theme, str)
            assert "weight" in data
            assert "holdings" in data
            assert isinstance(data["weight"], float)
            assert 0 <= data["weight"] <= 1.0
            assert isinstance(data["holdings"], list)
            
        # Check diversity metrics
        assert "theme_count" in result["diversity"]
        assert "concentration_index" in result["diversity"]
        assert result["diversity"]["theme_count"] > 0
        assert 0 <= result["diversity"]["concentration_index"] <= 1.0
        
    def test_compare_portfolios_esg_performance(self, sample_portfolio, sample_investments):
        """Test comparing ESG performance between portfolios."""
        # Create two portfolios with different holdings
        # Portfolio 1 - Original sample portfolio
        holdings1 = []
        for holding_data in sample_portfolio["holdings"]:
            holdings1.append({
                "investment_id": holding_data["investment_id"],
                "shares": holding_data["shares"],
                "purchase_price": holding_data["purchase_price"],
                "purchase_date": date.fromisoformat(holding_data["purchase_date"]),
                "current_price": holding_data["current_price"],
                "current_value": holding_data["current_value"]
            })
        
        portfolio1 = Portfolio(
            portfolio_id="esg-focused-portfolio",
            name="ESG Focused Portfolio",
            holdings=holdings1,
            total_value=sample_portfolio["total_value"],
            cash_balance=sample_portfolio["cash_balance"],
            creation_date=date.fromisoformat(sample_portfolio["creation_date"]),
            last_updated=date.fromisoformat(sample_portfolio["last_updated"])
        )
        
        # Portfolio 2 - Modified to include only tech companies
        tech_holdings = []
        for holding_data in sample_portfolio["holdings"]:
            if holding_data["investment_id"] in ["AAPL", "TSLA"]:  # Just tech companies
                tech_holdings.append({
                    "investment_id": holding_data["investment_id"],
                    "shares": holding_data["shares"] * 2,  # Double the shares
                    "purchase_price": holding_data["purchase_price"],
                    "purchase_date": date.fromisoformat(holding_data["purchase_date"]),
                    "current_price": holding_data["current_price"],
                    "current_value": holding_data["current_price"] * (holding_data["shares"] * 2)
                })
        
        tech_total_value = sum(h["current_value"] for h in tech_holdings)
        
        portfolio2 = Portfolio(
            portfolio_id="tech-focused-portfolio",
            name="Tech Focused Portfolio",
            holdings=tech_holdings,
            total_value=tech_total_value,
            cash_balance=5000.0,
            creation_date=date.fromisoformat(sample_portfolio["creation_date"]),
            last_updated=date.fromisoformat(sample_portfolio["last_updated"])
        )
        
        # Convert sample investments to Investment models
        investments_dict = {}
        for inv_data in sample_investments:
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
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Compare the portfolios
        comparison = analysis_system.compare_portfolio_esg_performance(
            portfolio1, portfolio2, investments_dict
        )
        
        # Verify comparison result
        assert isinstance(comparison, dict)
        assert "portfolio1" in comparison
        assert "portfolio2" in comparison
        assert "comparison" in comparison
        
        # Check portfolio data
        for portfolio_key in ["portfolio1", "portfolio2"]:
            assert "portfolio_id" in comparison[portfolio_key]
            assert "esg_metrics" in comparison[portfolio_key]
            assert "environmental_score" in comparison[portfolio_key]["esg_metrics"]
            assert "social_score" in comparison[portfolio_key]["esg_metrics"]
            assert "governance_score" in comparison[portfolio_key]["esg_metrics"]
            assert "overall_score" in comparison[portfolio_key]["esg_metrics"]
            
        # Check comparison data
        assert "environmental_difference" in comparison["comparison"]
        assert "social_difference" in comparison["comparison"]
        assert "governance_difference" in comparison["comparison"]
        assert "overall_difference" in comparison["comparison"]
        assert "better_portfolio" in comparison["comparison"]
        
    def test_risk_adjusted_esg_performance(self, sample_portfolio, sample_investments):
        """Test analyzing risk-adjusted ESG performance metrics."""
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
        
        # Create simulated volatility data
        volatility_data = {
            investment_id: 0.15 + (i * 0.05)  # Increasing volatility
            for i, investment_id in enumerate(investments_dict.keys())
        }
        
        # Create simulated return data
        return_data = {
            investment_id: 0.08 + (i * 0.02)  # Increasing returns
            for i, investment_id in enumerate(investments_dict.keys())
        }
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Calculate risk-adjusted ESG metrics
        result = analysis_system.calculate_risk_adjusted_esg_performance(
            portfolio, investments_dict, volatility_data, return_data
        )
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "overall" in result
        assert "by_investment" in result
        
        # Check overall metrics
        assert "esg_score" in result["overall"]
        assert "risk_adjusted_esg_score" in result["overall"]
        assert "sharpe_ratio" in result["overall"]
        assert "risk_return_esg_ratio" in result["overall"]
        
        # Check individual investment metrics
        for investment_id, metrics in result["by_investment"].items():
            assert investment_id in investments_dict
            assert "esg_score" in metrics
            assert "risk_adjusted_esg_score" in metrics
            assert "risk" in metrics
            assert "return" in metrics
            
            # Ensure risk-adjusted score accounts for volatility
            # Higher volatility should result in lower risk-adjusted scores
            assert metrics["risk_adjusted_esg_score"] <= metrics["esg_score"]