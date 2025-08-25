"""Tests for customizing ethical screening criteria based on personal values."""

import pytest
from typing import Dict, List, Any
import json

from ethical_finance.models import Investment, EthicalCriteria
from ethical_finance.ethical_screening.screening import (
    EthicalScreener, ScreeningResult, create_default_criteria
)


class TestEthicalCriteriaCustomization:
    """Test class for customizing ethical screening criteria based on personal values."""
    
    def test_create_prioritized_ethical_criteria(self):
        """Test creating criteria with personalized priority weights."""
        # Create a custom criteria with prioritized categories
        custom_criteria = EthicalCriteria(
            criteria_id="personal-values-focused",
            name="Personal Values Focused Criteria",
            environmental={
                "min_environmental_score": 65,
                "max_carbon_footprint": 40000000,
                "min_renewable_energy_use": 0.6,
                "exclude_fossil_fuel_production": True,
                "weight": 0.5  # Higher weight for environmental factors
            },
            social={
                "min_social_score": 60,
                "min_diversity_score": 0.65,
                "exclude_human_rights_violations": True,
                "exclude_weapons_manufacturing": True,
                "weight": 0.3
            },
            governance={
                "min_governance_score": 65,
                "min_board_independence": 0.7,
                "exclude_excessive_executive_compensation": True,
                "weight": 0.2
            },
            min_overall_score=65,
            exclusions=[
                "tobacco",
                "gambling",
                "adult_entertainment",
                "military_contracting"
            ],
            inclusions=[
                "renewable_energy",
                "sustainable_agriculture",
                "education",
                "healthcare"
            ]
        )
        
        # Verify criteria properties
        assert custom_criteria.criteria_id == "personal-values-focused"
        assert custom_criteria.name == "Personal Values Focused Criteria"
        
        # Verify custom weights
        assert custom_criteria.environmental["weight"] == 0.5
        assert custom_criteria.social["weight"] == 0.3
        assert custom_criteria.governance["weight"] == 0.2
        assert abs(custom_criteria.environmental["weight"] + 
                custom_criteria.social["weight"] + 
                custom_criteria.governance["weight"] - 1.0) < 0.001
        
        # Initialize screener with the custom criteria
        screener = EthicalScreener(custom_criteria)
        
        # Create test investments with different characteristics
        test_investments = [
            # Investment with high environmental but lower social scores
            Investment(
                id="renewable-energy-corp",
                name="Renewable Energy Corp",
                sector="Energy",
                industry="Renewable Energy",
                market_cap=15000000000,
                price=45.75,
                esg_ratings={
                    "environmental": 90,
                    "social": 60,
                    "governance": 70,
                    "overall": 75
                },
                carbon_footprint=5000000,
                renewable_energy_use=0.95,
                diversity_score=0.62,
                board_independence=0.75,
                controversies=["labor_practices"],
                positive_practices=["renewable_energy_investment", "carbon_neutrality"]
            ),
            # Investment with high social but lower environmental scores
            Investment(
                id="social-enterprise-inc",
                name="Social Enterprise Inc",
                sector="Consumer Defensive",
                industry="Personal Products",
                market_cap=8000000000,
                price=32.50,
                esg_ratings={
                    "environmental": 65,
                    "social": 88,
                    "governance": 72,
                    "overall": 75
                },
                carbon_footprint=35000000,
                renewable_energy_use=0.45,
                diversity_score=0.92,
                board_independence=0.80,
                controversies=[],
                positive_practices=["fair_trade", "community_investment", "diverse_leadership"]
            ),
            # Investment that's bad on governance
            Investment(
                id="poor-governance-corp",
                name="Poor Governance Corp",
                sector="Technology",
                industry="Software",
                market_cap=25000000000,
                price=125.30,
                esg_ratings={
                    "environmental": 75,
                    "social": 72,
                    "governance": 45,
                    "overall": 65
                },
                carbon_footprint=15000000,
                renewable_energy_use=0.70,
                diversity_score=0.71,
                board_independence=0.55,
                controversies=["executive_compensation", "governance_issues"],
                positive_practices=["sustainable_operations", "diversity_initiatives"]
            )
        ]
        
        # Screen all investments
        results = {}
        for investment in test_investments:
            results[investment.id] = screener.screen_investment(investment)
            
        # Verify results based on our priorities
        # The environmental-focused company should get a better score since we prioritized that
        assert results["renewable-energy-corp"].passed
        assert results["social-enterprise-inc"].passed  # Should pass but with lower score
        assert not results["poor-governance-corp"].passed  # Should fail governance
        
        # Check that scores reflect our custom weights
        # Environmental scores should have the most impact
        assert results["renewable-energy-corp"].overall_score > results["social-enterprise-inc"].overall_score
        
    def test_criteria_from_user_survey(self):
        """Test generating ethical criteria from user survey responses."""
        # Simulate user survey responses
        survey_responses = {
            "top_concerns": ["climate_change", "human_rights", "labor_practices"],
            "industries_to_avoid": ["fossil_fuels", "weapons", "tobacco"],
            "industries_to_support": ["renewable_energy", "education", "healthcare"],
            "relative_importance": {
                "environmental": 5,  # 1-5 scale
                "social": 4,
                "governance": 3
            },
            "environmental_priorities": ["carbon_reduction", "renewable_energy", "waste_reduction"],
            "social_priorities": ["diversity", "community_investment", "fair_labor"],
            "governance_priorities": ["board_diversity", "executive_compensation", "transparency"]
        }
        
        # Generate criteria from survey responses
        criteria = EthicalScreener.generate_criteria_from_survey(survey_responses)
        
        # Verify criteria reflects survey responses
        assert criteria.criteria_id == "user-personalized"
        
        # Check weights are properly calculated from relative importance
        total_importance = sum(survey_responses["relative_importance"].values())
        expected_env_weight = survey_responses["relative_importance"]["environmental"] / total_importance
        expected_social_weight = survey_responses["relative_importance"]["social"] / total_importance
        expected_gov_weight = survey_responses["relative_importance"]["governance"] / total_importance
        
        assert abs(criteria.environmental["weight"] - expected_env_weight) < 0.001
        assert abs(criteria.social["weight"] - expected_social_weight) < 0.001
        assert abs(criteria.governance["weight"] - expected_gov_weight) < 0.001
        
        # Check exclusions and inclusions
        for industry in survey_responses["industries_to_avoid"]:
            assert industry in criteria.exclusions
            
        for industry in survey_responses["industries_to_support"]:
            assert industry in criteria.inclusions
            
        # Check that environmental priorities are reflected
        if "carbon_reduction" in survey_responses["environmental_priorities"]:
            assert "max_carbon_footprint" in criteria.environmental
            
        if "renewable_energy" in survey_responses["environmental_priorities"]:
            assert "min_renewable_energy_use" in criteria.environmental
            
        # Create test investment that aligns with the user's priorities
        aligned_investment = Investment(
            id="aligned-investment",
            name="Aligned Investment Co",
            sector="Technology",
            industry="Clean Technology",
            market_cap=20000000000,
            price=85.25,
            esg_ratings={
                "environmental": 85,
                "social": 80,
                "governance": 75,
                "overall": 82
            },
            carbon_footprint=8000000,
            renewable_energy_use=0.85,
            diversity_score=0.80,
            board_independence=0.75,
            controversies=[],
            positive_practices=["renewable_energy_investment", "diversity_initiatives", "community_investment"]
        )
        
        # Create test investment that conflicts with the user's priorities
        misaligned_investment = Investment(
            id="misaligned-investment",
            name="Misaligned Investment Co",
            sector="Energy",
            industry="Oil & Gas",
            market_cap=35000000000,
            price=65.50,
            esg_ratings={
                "environmental": 45,
                "social": 60,
                "governance": 70,
                "overall": 55
            },
            carbon_footprint=75000000,
            renewable_energy_use=0.15,
            diversity_score=0.60,
            board_independence=0.72,
            controversies=["climate_impact", "human_rights"],
            positive_practices=["community_investment"]
        )
        
        # Initialize screener with the criteria
        screener = EthicalScreener(criteria)
        
        # Screen both investments
        aligned_result = screener.screen_investment(aligned_investment)
        misaligned_result = screener.screen_investment(misaligned_investment)
        
        # Verify the aligned investment passes and the misaligned one fails
        assert aligned_result.passed
        assert not misaligned_result.passed
        
        # Check that the reasons for failing match the user's priorities
        if "fossil_fuels" in survey_responses["industries_to_avoid"]:
            assert any("fossil" in flag.lower() for flag in misaligned_result.exclusion_flags)
            
        if "climate_change" in survey_responses["top_concerns"]:
            assert misaligned_result.environmental_score < criteria.environmental["min_environmental_score"]
            
        
    def test_serialize_and_load_criteria(self):
        """Test serializing and loading criteria for persistence."""
        # Create custom criteria
        custom_criteria = EthicalCriteria(
            criteria_id="serialization-test",
            name="Serialization Test Criteria",
            environmental={
                "min_environmental_score": 70,
                "max_carbon_footprint": 30000000,
                "min_renewable_energy_use": 0.7,
                "exclude_fossil_fuel_production": True,
                "weight": 0.4
            },
            social={
                "min_social_score": 65,
                "min_diversity_score": 0.7,
                "exclude_human_rights_violations": True,
                "exclude_weapons_manufacturing": True,
                "weight": 0.4
            },
            governance={
                "min_governance_score": 60,
                "min_board_independence": 0.65,
                "exclude_excessive_executive_compensation": True,
                "weight": 0.2
            },
            min_overall_score=65,
            exclusions=["tobacco", "gambling", "fossil_fuels"],
            inclusions=["renewable_energy", "education"]
        )
        
        # Serialize criteria to JSON
        criteria_json = self._serialize_criteria(custom_criteria)
        
        # Verify serialization
        assert isinstance(criteria_json, str)
        
        # Parse JSON
        criteria_dict = json.loads(criteria_json)
        assert criteria_dict["criteria_id"] == "serialization-test"
        assert criteria_dict["name"] == "Serialization Test Criteria"
        assert criteria_dict["environmental"]["weight"] == 0.4
        assert criteria_dict["social"]["weight"] == 0.4
        assert criteria_dict["governance"]["weight"] == 0.2
        
        # Load criteria from JSON
        loaded_criteria = self._load_criteria_from_json(criteria_json)
        
        # Verify loaded criteria matches original
        assert loaded_criteria.criteria_id == custom_criteria.criteria_id
        assert loaded_criteria.name == custom_criteria.name
        assert loaded_criteria.environmental["weight"] == custom_criteria.environmental["weight"]
        assert loaded_criteria.environmental["min_environmental_score"] == custom_criteria.environmental["min_environmental_score"]
        assert loaded_criteria.social["weight"] == custom_criteria.social["weight"]
        assert loaded_criteria.governance["weight"] == custom_criteria.governance["weight"]
        assert loaded_criteria.min_overall_score == custom_criteria.min_overall_score
        assert set(loaded_criteria.exclusions) == set(custom_criteria.exclusions)
        assert set(loaded_criteria.inclusions) == set(custom_criteria.inclusions)
        
        # Initialize screener with loaded criteria
        screener = EthicalScreener(loaded_criteria)
        
        # Create test investment
        test_investment = Investment(
            id="test-investment",
            name="Test Investment Co",
            sector="Technology",
            industry="Software",
            market_cap=50000000000,
            price=120.75,
            esg_ratings={
                "environmental": 75,
                "social": 68,
                "governance": 72,
                "overall": 72
            },
            carbon_footprint=25000000,
            renewable_energy_use=0.75,
            diversity_score=0.72,
            board_independence=0.75,
            controversies=[],
            positive_practices=["renewable_energy_investment", "diversity_initiatives"]
        )
        
        # Screen the investment to verify the loaded criteria works
        result = screener.screen_investment(test_investment)
        
        # Verify result
        assert result.passed
        assert result.overall_score > 70
        
    def _serialize_criteria(self, criteria: EthicalCriteria) -> str:
        """Serialize criteria to JSON."""
        criteria_dict = {
            "criteria_id": criteria.criteria_id,
            "name": criteria.name,
            "environmental": criteria.environmental,
            "social": criteria.social,
            "governance": criteria.governance,
            "min_overall_score": criteria.min_overall_score,
            "exclusions": criteria.exclusions,
            "inclusions": criteria.inclusions
        }
        return json.dumps(criteria_dict)
        
    def _load_criteria_from_json(self, criteria_json: str) -> EthicalCriteria:
        """Load criteria from JSON."""
        criteria_dict = json.loads(criteria_json)
        return EthicalCriteria(**criteria_dict)