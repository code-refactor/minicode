"""Tests for the ethical screening framework."""

import pytest
from unittest.mock import patch, MagicMock
import time
from typing import Dict, List, Any

from ethical_finance.models import Investment, EthicalCriteria
from ethical_finance.ethical_screening.screening import (
    EthicalScreener, ScreeningResult, create_default_criteria
)


class TestEthicalScreening:
    """Test class for the ethical screening framework."""
    
    def test_create_default_criteria(self):
        """Test creating default ethical criteria."""
        criteria = create_default_criteria()
        
        # Check that we got valid criteria
        assert isinstance(criteria, EthicalCriteria)
        assert criteria.criteria_id == "default"
        assert criteria.name == "Default Ethical Criteria"
        
        # Check that the weights sum to 1.0
        env_weight = criteria.environmental["weight"]
        social_weight = criteria.social["weight"]
        gov_weight = criteria.governance["weight"]
        
        assert env_weight + social_weight + gov_weight == pytest.approx(1.0)
        
        # Check required fields
        assert "min_environmental_score" in criteria.environmental
        assert "min_social_score" in criteria.social
        assert "min_governance_score" in criteria.governance
        assert isinstance(criteria.exclusions, list)
        assert isinstance(criteria.inclusions, list)
        assert criteria.min_overall_score > 0
    
    def test_initialize_screener(self, sample_ethical_criteria):
        """Test initializing the ethical screener."""
        screener = EthicalScreener(sample_ethical_criteria)
        
        assert screener.criteria == sample_ethical_criteria
    
    def test_screen_investment_passing(self, sample_investments, sample_ethical_criteria):
        """Test screening an investment that passes criteria."""
        # Get a high-scoring investment from the sample data
        high_scoring_investment = None
        for investment in sample_investments:
            if (investment["esg_ratings"]["overall"] >= sample_ethical_criteria["min_overall_score"] and
                "fossil_fuel_production" not in investment["controversies"]):
                high_scoring_investment = investment
                break
        
        assert high_scoring_investment is not None, "No suitable investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=high_scoring_investment["id"],
            name=high_scoring_investment["name"],
            sector=high_scoring_investment["sector"],
            industry=high_scoring_investment["industry"],
            market_cap=high_scoring_investment["market_cap"],
            price=high_scoring_investment["price"],
            esg_ratings=high_scoring_investment["esg_ratings"],
            carbon_footprint=high_scoring_investment["carbon_footprint"],
            renewable_energy_use=high_scoring_investment["renewable_energy_use"],
            diversity_score=high_scoring_investment["diversity_score"],
            board_independence=high_scoring_investment["board_independence"],
            controversies=high_scoring_investment["controversies"],
            positive_practices=high_scoring_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Screen the investment
        result = screener.screen_investment(investment)
        
        # Verify result
        assert isinstance(result, ScreeningResult)
        assert result.investment_id == investment.id
        assert result.passed is True
        assert result.overall_score >= criteria.min_overall_score
        assert len(result.exclusion_flags) == 0
        assert result.details["processing_time_ms"] > 0
    
    def test_screen_investment_failing(self, sample_investments, sample_ethical_criteria):
        """Test screening an investment that fails criteria."""
        # Modify criteria to be more stringent
        strict_criteria = dict(sample_ethical_criteria)
        strict_criteria["min_overall_score"] = 85  # Very high threshold
        
        # Find a lower-scoring investment
        low_scoring_investment = None
        for investment in sample_investments:
            if investment["esg_ratings"]["overall"] < 85:
                low_scoring_investment = investment
                break
        
        assert low_scoring_investment is not None, "No suitable investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=low_scoring_investment["id"],
            name=low_scoring_investment["name"],
            sector=low_scoring_investment["sector"],
            industry=low_scoring_investment["industry"],
            market_cap=low_scoring_investment["market_cap"],
            price=low_scoring_investment["price"],
            esg_ratings=low_scoring_investment["esg_ratings"],
            carbon_footprint=low_scoring_investment["carbon_footprint"],
            renewable_energy_use=low_scoring_investment["renewable_energy_use"],
            diversity_score=low_scoring_investment["diversity_score"],
            board_independence=low_scoring_investment["board_independence"],
            controversies=low_scoring_investment["controversies"],
            positive_practices=low_scoring_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**strict_criteria)
        screener = EthicalScreener(criteria)
        
        # Screen the investment
        result = screener.screen_investment(investment)
        
        # Verify result
        assert isinstance(result, ScreeningResult)
        assert result.investment_id == investment.id
        assert result.passed is False
        assert result.overall_score < criteria.min_overall_score
    
    def test_screen_investment_with_exclusions(self, sample_investments, sample_ethical_criteria):
        """Test screening an investment that matches exclusion criteria."""
        # Get an energy sector investment (which should be excluded)
        energy_investment = None
        for investment in sample_investments:
            if investment["sector"] == "Energy":
                energy_investment = investment
                break
        
        assert energy_investment is not None, "No energy sector investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=energy_investment["id"],
            name=energy_investment["name"],
            sector=energy_investment["sector"],
            industry=energy_investment["industry"],
            market_cap=energy_investment["market_cap"],
            price=energy_investment["price"],
            esg_ratings=energy_investment["esg_ratings"],
            carbon_footprint=energy_investment["carbon_footprint"],
            renewable_energy_use=energy_investment["renewable_energy_use"],
            diversity_score=energy_investment["diversity_score"],
            board_independence=energy_investment["board_independence"],
            controversies=energy_investment["controversies"],
            positive_practices=energy_investment["positive_practices"]
        )
        
        # Add energy sector to exclusions
        modified_criteria = dict(sample_ethical_criteria)
        modified_criteria["exclusions"] = sample_ethical_criteria["exclusions"] + ["Energy"]
        
        criteria = EthicalCriteria(**modified_criteria)
        screener = EthicalScreener(criteria)
        
        # Screen the investment
        result = screener.screen_investment(investment)
        
        # Verify result
        assert isinstance(result, ScreeningResult)
        assert result.investment_id == investment.id
        assert result.passed is False
        assert len(result.exclusion_flags) > 0
        assert any("Energy" in flag for flag in result.exclusion_flags)
    
    def test_screen_investment_with_inclusions(self, sample_investments, sample_ethical_criteria):
        """Test screening an investment that matches inclusion criteria."""
        # Find an investment with a positive practice that's in our inclusions
        included_investment = None
        for investment in sample_investments:
            practices = [p.lower() for p in investment["positive_practices"]]
            if any(practice in [inc.lower() for inc in sample_ethical_criteria["inclusions"]] 
                   for practice in practices):
                included_investment = investment
                break
        
        if included_investment is None:
            # If none found, modify an investment to match
            included_investment = sample_investments[0].copy()
            included_investment["positive_practices"] = ["renewable_energy"] + included_investment["positive_practices"]
        
        # Convert to Investment model
        investment = Investment(
            id=included_investment["id"],
            name=included_investment["name"],
            sector=included_investment["sector"],
            industry=included_investment["industry"],
            market_cap=included_investment["market_cap"],
            price=included_investment["price"],
            esg_ratings=included_investment["esg_ratings"],
            carbon_footprint=included_investment["carbon_footprint"],
            renewable_energy_use=included_investment["renewable_energy_use"],
            diversity_score=included_investment["diversity_score"],
            board_independence=included_investment["board_independence"],
            controversies=included_investment["controversies"],
            positive_practices=included_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Screen the investment
        result = screener.screen_investment(investment)
        
        # Verify result
        assert isinstance(result, ScreeningResult)
        assert result.investment_id == investment.id
        assert len(result.inclusion_flags) > 0
    
    def test_screen_investments_batch(self, sample_investments, sample_ethical_criteria):
        """Test screening multiple investments in batch."""
        # Convert sample data to Investment models
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
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Screen all investments
        results = screener.screen_investments(investments)
        
        # Verify results
        assert isinstance(results, dict)
        assert len(results) == len(investments)
        
        # Check that all investments were screened
        for investment in investments:
            assert investment.id in results
            assert isinstance(results[investment.id], ScreeningResult)
    
    def test_evaluate_environmental_criteria(self, sample_investments, sample_ethical_criteria):
        """Test evaluating environmental criteria for an investment."""
        # Get an investment with good environmental metrics
        env_investment = None
        for investment in sample_investments:
            if (investment["esg_ratings"]["environmental"] >= 70 and
                investment["renewable_energy_use"] >= 0.7):
                env_investment = investment
                break
        
        assert env_investment is not None, "No suitable investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=env_investment["id"],
            name=env_investment["name"],
            sector=env_investment["sector"],
            industry=env_investment["industry"],
            market_cap=env_investment["market_cap"],
            price=env_investment["price"],
            esg_ratings=env_investment["esg_ratings"],
            carbon_footprint=env_investment["carbon_footprint"],
            renewable_energy_use=env_investment["renewable_energy_use"],
            diversity_score=env_investment["diversity_score"],
            board_independence=env_investment["board_independence"],
            controversies=env_investment["controversies"],
            positive_practices=env_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Directly test the environmental criteria evaluation
        env_score, env_details = screener._evaluate_environmental_criteria(investment)
        
        # Verify results
        assert isinstance(env_score, float)
        assert env_score >= criteria.environmental["min_environmental_score"]
        assert "base_score" in env_details
        assert "final_score" in env_details
        assert env_details["final_score"] == env_score
    
    def test_evaluate_social_criteria(self, sample_investments, sample_ethical_criteria):
        """Test evaluating social criteria for an investment."""
        # Get an investment with good social metrics
        social_investment = None
        for investment in sample_investments:
            if (investment["esg_ratings"]["social"] >= 70 and
                investment["diversity_score"] >= 0.7):
                social_investment = investment
                break
        
        assert social_investment is not None, "No suitable investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=social_investment["id"],
            name=social_investment["name"],
            sector=social_investment["sector"],
            industry=social_investment["industry"],
            market_cap=social_investment["market_cap"],
            price=social_investment["price"],
            esg_ratings=social_investment["esg_ratings"],
            carbon_footprint=social_investment["carbon_footprint"],
            renewable_energy_use=social_investment["renewable_energy_use"],
            diversity_score=social_investment["diversity_score"],
            board_independence=social_investment["board_independence"],
            controversies=social_investment["controversies"],
            positive_practices=social_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Directly test the social criteria evaluation
        social_score, social_details = screener._evaluate_social_criteria(investment)
        
        # Verify results
        assert isinstance(social_score, float)
        assert social_score >= criteria.social["min_social_score"]
        assert "base_score" in social_details
        assert "final_score" in social_details
        assert social_details["final_score"] == social_score
    
    def test_evaluate_governance_criteria(self, sample_investments, sample_ethical_criteria):
        """Test evaluating governance criteria for an investment."""
        # Get an investment with good governance metrics
        gov_investment = None
        for investment in sample_investments:
            if (investment["esg_ratings"]["governance"] >= 70 and
                investment["board_independence"] >= 0.7):
                gov_investment = investment
                break
        
        assert gov_investment is not None, "No suitable investment found in test data"
        
        # Convert to Investment model
        investment = Investment(
            id=gov_investment["id"],
            name=gov_investment["name"],
            sector=gov_investment["sector"],
            industry=gov_investment["industry"],
            market_cap=gov_investment["market_cap"],
            price=gov_investment["price"],
            esg_ratings=gov_investment["esg_ratings"],
            carbon_footprint=gov_investment["carbon_footprint"],
            renewable_energy_use=gov_investment["renewable_energy_use"],
            diversity_score=gov_investment["diversity_score"],
            board_independence=gov_investment["board_independence"],
            controversies=gov_investment["controversies"],
            positive_practices=gov_investment["positive_practices"]
        )
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Directly test the governance criteria evaluation
        gov_score, gov_details = screener._evaluate_governance_criteria(investment)
        
        # Verify results
        assert isinstance(gov_score, float)
        assert gov_score >= criteria.governance["min_governance_score"]
        assert "base_score" in gov_details
        assert "final_score" in gov_details
        assert gov_details["final_score"] == gov_score
    
    def test_performance_for_many_investments(self, sample_investments, sample_ethical_criteria):
        """Test screening performance for a large number of investments."""
        # Create many investments by duplicating sample investments
        num_investments = 200
        investments = []
        
        for i in range(num_investments):
            # Use modulo to cycle through sample investments
            sample_idx = i % len(sample_investments)
            sample_inv = sample_investments[sample_idx]
            
            # Create a new Investment with a unique ID
            investment = Investment(
                id=f"{sample_inv['id']}-{i}",
                name=sample_inv["name"],
                sector=sample_inv["sector"],
                industry=sample_inv["industry"],
                market_cap=sample_inv["market_cap"],
                price=sample_inv["price"],
                esg_ratings=sample_inv["esg_ratings"],
                carbon_footprint=sample_inv["carbon_footprint"],
                renewable_energy_use=sample_inv["renewable_energy_use"],
                diversity_score=sample_inv["diversity_score"],
                board_independence=sample_inv["board_independence"],
                controversies=sample_inv["controversies"],
                positive_practices=sample_inv["positive_practices"]
            )
            investments.append(investment)
        
        criteria = EthicalCriteria(**sample_ethical_criteria)
        screener = EthicalScreener(criteria)
        
        # Measure performance
        start_time = time.time()
        
        results = screener.screen_investments(investments)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance requirement: screen 1000+ investments in under 30 seconds
        # Scale the actual time to what it would take for 1000 investments
        scaled_time = total_time * (1000 / num_investments)
        
        print(f"Screened {num_investments} investments in {total_time:.2f} seconds")
        print(f"Estimated time for 1000 investments: {scaled_time:.2f} seconds")
        
        # Check that the performance meets requirements
        assert scaled_time < 30.0
        
        # Verify all investments were screened
        assert len(results) == num_investments