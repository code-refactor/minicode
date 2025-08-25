"""Tests for the portfolio analysis system."""

import pytest
from unittest.mock import patch, MagicMock
import time
from datetime import date
from typing import Dict, List, Any

from ethical_finance.models import Investment, Portfolio, InvestmentHolding
from ethical_finance.ethical_screening.screening import EthicalScreener, ScreeningResult, create_default_criteria
from ethical_finance.portfolio_analysis.analysis import (
    PortfolioAnalysisSystem,
    PortfolioCompositionResult,
    DiversificationAssessment,
    PortfolioOptimizationResult
)


class TestPortfolioAnalysis:
    """Test class for the portfolio analysis system."""
    
    def test_initialize_analysis_system(self):
        """Test initializing the portfolio analysis system."""
        # Initialize without ethical screener
        analysis_system = PortfolioAnalysisSystem()
        assert analysis_system.ethical_screener is None
        
        # Initialize with ethical screener
        criteria = create_default_criteria()
        screener = EthicalScreener(criteria)
        analysis_system = PortfolioAnalysisSystem(screener)
        assert analysis_system.ethical_screener is screener
    
    def test_analyze_portfolio_composition(self, sample_portfolio, sample_investments):
        """Test analyzing portfolio composition."""
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
        
        # Analyze portfolio composition
        result = analysis_system.analyze_portfolio_composition(portfolio, investments_dict)
        
        # Verify result
        assert isinstance(result, PortfolioCompositionResult)
        assert result.portfolio_id == portfolio.portfolio_id
        assert isinstance(result.analysis_date, date)
        assert len(result.sector_breakdown) > 0
        assert len(result.industry_breakdown) > 0
        assert len(result.esg_theme_exposure) > 0
        assert len(result.concentration_metrics) > 0
        assert len(result.top_holdings) > 0
        assert isinstance(result.ethical_alignment, dict)
        assert result.processing_time_ms > 0
    
    def test_analyze_portfolio_composition_with_screening(self, sample_portfolio, sample_investments, sample_ethical_criteria):
        """Test analyzing portfolio composition with ethical screening results."""
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
        
        # Create screening results for the investments
        screening_results = {}
        for inv_id, investment in investments_dict.items():
            # Simple mock screening result
            passed = investment.esg_ratings.overall >= 65  # Simple threshold
            screening_results[inv_id] = ScreeningResult(
                investment_id=inv_id,
                passed=passed,
                overall_score=investment.esg_ratings.overall,
                environmental_score=investment.esg_ratings.environmental,
                social_score=investment.esg_ratings.social,
                governance_score=investment.esg_ratings.governance,
                exclusion_flags=[],
                inclusion_flags=[],
                details={}
            )
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Analyze portfolio composition with screening results
        result = analysis_system.analyze_portfolio_composition(
            portfolio, investments_dict, screening_results
        )
        
        # Verify result includes ethical alignment data
        assert isinstance(result, PortfolioCompositionResult)
        assert "holdings_passing_percentage" in result.ethical_alignment
        assert "value_passing_percentage" in result.ethical_alignment
        assert "weighted_environmental_score" in result.ethical_alignment
        assert "weighted_social_score" in result.ethical_alignment
        assert "weighted_governance_score" in result.ethical_alignment
        assert "weighted_overall_score" in result.ethical_alignment
    
    def test_assess_diversification(self, sample_portfolio, sample_investments):
        """Test assessing portfolio diversification."""
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
        
        # Assess diversification
        result = analysis_system.assess_diversification(portfolio, investments_dict)
        
        # Verify result
        assert isinstance(result, DiversificationAssessment)
        assert result.portfolio_id == portfolio.portfolio_id
        assert isinstance(result.assessment_date, date)
        assert isinstance(result.diversification_score, float)
        assert 0 <= result.diversification_score <= 100
        assert isinstance(result.sector_concentration_risk, dict)
        assert isinstance(result.industry_concentration_risk, dict)
        assert isinstance(result.esg_theme_concentration_risk, dict)
        assert isinstance(result.diversification_recommendations, list)
        assert isinstance(result.ethical_constraints_applied, list)
        assert result.processing_time_ms > 0
    
    def test_assess_diversification_with_constraints(self, sample_portfolio, sample_investments):
        """Test assessing portfolio diversification with ethical constraints."""
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
        
        # Define ethical constraints
        ethical_constraints = {
            "required_sectors": ["Technology", "Consumer Defensive"],
            "required_themes": ["renewable_energy", "social_impact"],
            "excluded_sectors": ["Energy", "Military"],
            "min_esg_score": 65
        }
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Assess diversification with constraints
        result = analysis_system.assess_diversification(
            portfolio, investments_dict, ethical_constraints
        )
        
        # Verify constraints were applied
        assert isinstance(result, DiversificationAssessment)
        assert len(result.ethical_constraints_applied) > 0
        for constraint in result.ethical_constraints_applied:
            assert constraint in ethical_constraints
    
    def test_optimize_portfolio(self, sample_portfolio, sample_investments):
        """Test optimizing a portfolio for returns and ethical alignment."""
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
        current_investments = {}
        candidate_investments = {}
        
        for inv_data in sample_investments:
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
            
            # Add to current investments if in portfolio
            if inv_data["id"] in [h.investment_id for h in portfolio.holdings]:
                current_investments[inv_data["id"]] = investment
            else:
                # Add to candidate investments if not in portfolio
                candidate_investments[inv_data["id"]] = investment
        
        # Define optimization goals and constraints
        optimization_goals = {
            "financial_return": 0.6,
            "ethical_alignment": 0.4
        }
        
        constraints = {
            "max_sector_weight": 0.3,
            "max_industry_weight": 0.2,
            "min_esg_score": 65,
            "min_return_for_concentration": 10,
            "excluded_sectors": ["Energy"],
            "excluded_industries": ["Oil & Gas"]
        }
        
        # Initialize analysis system
        analysis_system = PortfolioAnalysisSystem()
        
        # Optimize portfolio
        result = analysis_system.optimize_portfolio(
            portfolio, current_investments, candidate_investments,
            optimization_goals, constraints
        )
        
        # Verify result
        assert isinstance(result, PortfolioOptimizationResult)
        assert result.portfolio_id == portfolio.portfolio_id
        assert isinstance(result.optimization_date, date)
        assert isinstance(result.current_ethical_score, float)
        assert isinstance(result.current_risk_metrics, dict)
        assert isinstance(result.recommended_changes, list)
        assert isinstance(result.expected_improvement, dict)
        assert result.optimization_constraints == constraints
        assert result.processing_time_ms > 0
        
        # Check recommended changes
        for change in result.recommended_changes:
            assert "action" in change
            assert change["action"] in ["add", "reduce"]
            assert "investment_id" in change
            assert "current_weight" in change
            assert "target_weight" in change
            assert "reason" in change
    
    def test_map_practice_to_theme(self):
        """Test mapping a company's positive practice to an ESG theme."""
        analysis_system = PortfolioAnalysisSystem()
        
        # Test mapping known practices
        assert analysis_system._map_practice_to_theme("renewable_energy") == "renewable_energy"
        assert analysis_system._map_practice_to_theme("diversity_initiative") == "diversity_equity_inclusion"
        assert analysis_system._map_practice_to_theme("community_investment") == "community_development"
        
        # Test with case variations
        assert analysis_system._map_practice_to_theme("Renewable_Energy") == "renewable_energy"
        
        # Test unknown practice
        assert analysis_system._map_practice_to_theme("unknown_practice") == "other"
    
    def test_sector_conflicts_with_constraints(self):
        """Test checking if reducing a sector would conflict with ethical constraints."""
        analysis_system = PortfolioAnalysisSystem()
        
        # Define constraints
        constraints = {
            "required_sectors": ["Renewable Energy", "Healthcare"],
            "required_themes": ["renewable_energy", "social_impact"]
        }
        
        # Test required sector
        assert analysis_system._sector_conflicts_with_constraints("Renewable Energy", constraints) is True
        
        # Test sector that maps to required theme
        assert analysis_system._sector_conflicts_with_constraints("Clean Technology", constraints) is True
        
        # Test unrelated sector
        assert analysis_system._sector_conflicts_with_constraints("Technology", constraints) is False
    
    def test_calculate_diversification_benefit(self, sample_investments):
        """Test calculating the diversification benefit of adding an investment."""
        # Convert a sample investment to Investment model
        inv_data = sample_investments[0]
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
        
        analysis_system = PortfolioAnalysisSystem()
        
        # Test with empty current portfolio
        current_sector_breakdown = {}
        current_industry_breakdown = {}
        
        benefit = analysis_system._calculate_diversification_benefit(
            investment, current_sector_breakdown, current_industry_breakdown
        )
        
        # Should provide high benefit for empty portfolio
        assert benefit > 0.5
        
        # Test with portfolio that already has this sector/industry
        current_sector_breakdown = {investment.sector: 0.5}
        current_industry_breakdown = {investment.industry: 0.3}
        
        benefit = analysis_system._calculate_diversification_benefit(
            investment, current_sector_breakdown, current_industry_breakdown
        )
        
        # Should provide less benefit
        assert benefit < 0.5
    
    def test_performance_with_large_portfolio(self, sample_portfolio, sample_investments):
        """Test performance with a portfolio of 200+ holdings."""
        # Create a large portfolio by duplicating sample holdings
        large_holdings = []
        num_holdings = 200
        
        # Use sample holdings as templates
        for i in range(num_holdings):
            # Use modulo to cycle through sample holdings
            sample_idx = i % len(sample_portfolio["holdings"])
            holding_data = sample_portfolio["holdings"][sample_idx]
            
            # Create a new holding with a unique ID
            large_holdings.append({
                "investment_id": f"{holding_data['investment_id']}-{i}",
                "shares": holding_data["shares"],
                "purchase_price": holding_data["purchase_price"],
                "purchase_date": date.fromisoformat(holding_data["purchase_date"]),
                "current_price": holding_data["current_price"],
                "current_value": holding_data["current_value"]
            })
        
        # Calculate total value
        total_value = sum(h["current_value"] for h in large_holdings)
        
        # Create large portfolio
        large_portfolio = Portfolio(
            portfolio_id="large-test-portfolio",
            name="Large Test Portfolio",
            holdings=large_holdings,
            total_value=total_value,
            cash_balance=sample_portfolio["cash_balance"],
            creation_date=date.fromisoformat(sample_portfolio["creation_date"]),
            last_updated=date.fromisoformat(sample_portfolio["last_updated"])
        )
        
        # Create investments dictionary
        large_investments = {}
        for i in range(num_holdings):
            # Use modulo to cycle through sample investments
            sample_idx = i % len(sample_investments)
            inv_data = sample_investments[sample_idx]
            
            # Create a new investment with a unique ID
            investment_id = f"{inv_data['id']}-{i}"
            large_investments[investment_id] = Investment(
                id=investment_id,
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
        
        # Measure performance
        start_time = time.time()
        
        result = analysis_system.analyze_portfolio_composition(large_portfolio, large_investments)
        
        end_time = time.time()
        composition_time = end_time - start_time
        
        # Verify result
        assert isinstance(result, PortfolioCompositionResult)
        assert len(result.sector_breakdown) > 0
        assert len(result.industry_breakdown) > 0
        
        # Performance requirement: process 200+ holdings in reasonable time
        print(f"Analyzed portfolio with {num_holdings} holdings in {composition_time:.2f} seconds")
        
        # Should be fast enough for interactive use
        assert composition_time < 5.0