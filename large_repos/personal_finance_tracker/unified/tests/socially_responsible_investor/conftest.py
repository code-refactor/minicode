"""Common test fixtures for ethical finance package."""

import pytest
import pandas as pd
import random
from typing import Dict, List, Any

@pytest.fixture
def sample_investments() -> List[Dict[str, Any]]:
    """Sample investment data for testing."""
    return [
        {
            "id": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 2500000000000,
            "price": 175.50,
            "esg_ratings": {
                "environmental": 72,
                "social": 68,
                "governance": 82,
                "overall": 74
            },
            "carbon_footprint": 22600000,  # tons CO2
            "renewable_energy_use": 0.85,  # percentage
            "diversity_score": 0.72,
            "board_independence": 0.80,  # percentage of independent directors
            "controversies": ["labor_practices", "tax_avoidance"],
            "positive_practices": ["renewable_energy_investment", "supply_chain_monitoring"]
        },
        {
            "id": "XOM",
            "name": "Exxon Mobil Corp",
            "sector": "Energy",
            "industry": "Oil & Gas",
            "market_cap": 450000000000,
            "price": 104.25,
            "esg_ratings": {
                "environmental": 28,
                "social": 45,
                "governance": 62,
                "overall": 41
            },
            "carbon_footprint": 112000000,  # tons CO2
            "renewable_energy_use": 0.05,  # percentage
            "diversity_score": 0.58,
            "board_independence": 0.75,
            "controversies": ["climate_impact", "oil_spills", "political_lobbying"],
            "positive_practices": ["community_investment"]
        },
        {
            "id": "TSLA",
            "name": "Tesla Inc.",
            "sector": "Consumer Cyclical",
            "industry": "Auto Manufacturers",
            "market_cap": 650000000000,
            "price": 215.75,
            "esg_ratings": {
                "environmental": 88,
                "social": 48,
                "governance": 55,
                "overall": 65
            },
            "carbon_footprint": 5600000,  # tons CO2
            "renewable_energy_use": 0.93,  # percentage
            "diversity_score": 0.61,
            "board_independence": 0.62,
            "controversies": ["labor_practices", "governance_issues"],
            "positive_practices": ["clean_energy_products", "battery_recycling"]
        },
        {
            "id": "COST",
            "name": "Costco Wholesale Corp",
            "sector": "Consumer Defensive",
            "industry": "Discount Stores",
            "market_cap": 220000000000,
            "price": 492.30,
            "esg_ratings": {
                "environmental": 65,
                "social": 78,
                "governance": 73,
                "overall": 72
            },
            "carbon_footprint": 3800000,  # tons CO2
            "renewable_energy_use": 0.52,  # percentage
            "diversity_score": 0.81,
            "board_independence": 0.90,
            "controversies": ["plastic_usage"],
            "positive_practices": ["fair_wages", "ethical_sourcing", "waste_reduction"]
        },
        {
            "id": "PG",
            "name": "Procter & Gamble Co",
            "sector": "Consumer Defensive",
            "industry": "Household Products",
            "market_cap": 350000000000,
            "price": 145.80,
            "esg_ratings": {
                "environmental": 61,
                "social": 75,
                "governance": 80,
                "overall": 70
            },
            "carbon_footprint": 5200000,  # tons CO2
            "renewable_energy_use": 0.62,  # percentage
            "diversity_score": 0.79,
            "board_independence": 0.85,
            "controversies": ["animal_testing", "deforestation"],
            "positive_practices": ["packaging_reduction", "water_conservation"]
        }
    ]

@pytest.fixture
def sample_shareholder_resolutions() -> List[Dict[str, Any]]:
    """Sample shareholder resolution data for testing."""
    return [
        {
            "company_id": "AAPL",
            "resolution_id": "AAPL-2023-01",
            "year": 2023,
            "title": "Report on Forced Labor in Supply Chain",
            "category": "social",
            "subcategory": "human_rights",
            "proposed_by": "shareholder_group",
            "status": "voted",
            "votes_for": 0.65,
            "votes_against": 0.32,
            "abstentions": 0.03,
            "company_recommendation": "against",
            "outcome": "passed"
        },
        {
            "company_id": "AAPL",
            "resolution_id": "AAPL-2023-02",
            "year": 2023,
            "title": "Report on Gender and Racial Pay Gap",
            "category": "social",
            "subcategory": "diversity",
            "proposed_by": "institutional_investor",
            "status": "voted",
            "votes_for": 0.42,
            "votes_against": 0.55,
            "abstentions": 0.03,
            "company_recommendation": "against",
            "outcome": "failed"
        },
        {
            "company_id": "XOM",
            "resolution_id": "XOM-2023-01",
            "year": 2023,
            "title": "Adopt GHG Reduction Targets",
            "category": "environmental",
            "subcategory": "climate",
            "proposed_by": "institutional_investor",
            "status": "voted",
            "votes_for": 0.38,
            "votes_against": 0.61,
            "abstentions": 0.01,
            "company_recommendation": "against",
            "outcome": "failed"
        },
        {
            "company_id": "XOM",
            "resolution_id": "XOM-2023-02",
            "year": 2023,
            "title": "Report on Lobbying Activities and Climate Policy",
            "category": "governance",
            "subcategory": "lobbying",
            "proposed_by": "shareholder_group",
            "status": "voted",
            "votes_for": 0.52,
            "votes_against": 0.47,
            "abstentions": 0.01,
            "company_recommendation": "against",
            "outcome": "passed"
        },
        {
            "company_id": "TSLA",
            "resolution_id": "TSLA-2023-01",
            "year": 2023,
            "title": "Adopt Policy on Freedom of Association",
            "category": "social",
            "subcategory": "labor_rights",
            "proposed_by": "union_pension_fund",
            "status": "voted",
            "votes_for": 0.32,
            "votes_against": 0.68,
            "abstentions": 0.00,
            "company_recommendation": "against",
            "outcome": "failed"
        }
    ]

@pytest.fixture
def sample_personal_transactions() -> List[Dict[str, Any]]:
    """Sample personal transaction data for testing."""
    return [
        {
            "id": "tx1",
            "date": "2023-05-10",
            "amount": 85.50,
            "vendor": "Whole Foods Market",
            "category": "Groceries",
            "description": "Weekly grocery shopping",
            "tags": ["food", "organic"]
        },
        {
            "id": "tx2",
            "date": "2023-05-12",
            "amount": 42.00,
            "vendor": "Local Farmers Market",
            "category": "Groceries",
            "description": "Fresh vegetables and fruits",
            "tags": ["food", "local", "sustainable"]
        },
        {
            "id": "tx3",
            "date": "2023-05-15",
            "amount": 120.75,
            "vendor": "REI",
            "category": "Clothing",
            "description": "Outdoor clothing",
            "tags": ["apparel", "sustainable_brand"]
        },
        {
            "id": "tx4",
            "date": "2023-05-18",
            "amount": 45.00,
            "vendor": "Shell Gas Station",
            "category": "Transportation",
            "description": "Gas for car",
            "tags": ["fossil_fuel", "transportation"]
        },
        {
            "id": "tx5",
            "date": "2023-05-22",
            "amount": 10.50,
            "vendor": "Starbucks",
            "category": "Dining",
            "description": "Coffee and snack",
            "tags": ["food", "chain_business"]
        },
        {
            "id": "tx6",
            "date": "2023-05-25",
            "amount": 250.00,
            "vendor": "Local Charity",
            "category": "Donations",
            "description": "Monthly donation",
            "tags": ["philanthropy", "community_support"]
        },
        {
            "id": "tx7",
            "date": "2023-05-28",
            "amount": 35.99,
            "vendor": "Amazon",
            "category": "Shopping",
            "description": "Household items",
            "tags": ["online_shopping", "large_corporation"]
        }
    ]

@pytest.fixture
def sample_portfolio() -> Dict[str, Any]:
    """Sample portfolio data for testing."""
    return {
        "portfolio_id": "test-portfolio",
        "name": "Test Ethical Portfolio",
        "holdings": [
            {
                "investment_id": "AAPL",
                "shares": 50,
                "purchase_price": 165.75,
                "purchase_date": "2022-06-15",
                "current_price": 175.50,
                "current_value": 8775.00
            },
            {
                "investment_id": "TSLA",
                "shares": 20,
                "purchase_price": 190.50,
                "purchase_date": "2022-07-20",
                "current_price": 215.75,
                "current_value": 4315.00
            },
            {
                "investment_id": "COST",
                "shares": 15,
                "purchase_price": 475.25,
                "purchase_date": "2022-08-10",
                "current_price": 492.30,
                "current_value": 7384.50
            },
            {
                "investment_id": "PG",
                "shares": 30,
                "purchase_price": 140.50,
                "purchase_date": "2022-09-05",
                "current_price": 145.80,
                "current_value": 4374.00
            }
        ],
        "total_value": 24848.50,
        "cash_balance": 5000.00,
        "creation_date": "2022-05-01",
        "last_updated": "2023-05-30"
    }

@pytest.fixture
def sample_impact_data() -> Dict[str, List[Dict[str, Any]]]:
    """Sample impact data for investments over time."""
    companies = ["AAPL", "TSLA", "COST", "PG", "XOM"]
    years = [2019, 2020, 2021, 2022, 2023]
    impact_data = {}
    
    for company in companies:
        impact_data[company] = []
        base_carbon = random.randint(3000000, 10000000)
        base_renewable = random.uniform(0.3, 0.7)
        base_water = random.randint(500000, 2000000)
        base_waste = random.randint(100000, 500000)
        
        for year in years:
            # Simulate improvement over time (except for some companies)
            if company != "XOM":
                carbon_reduction = (year - 2019) * 0.05
                renewable_increase = (year - 2019) * 0.03
            else:
                carbon_reduction = (year - 2019) * 0.01
                renewable_increase = (year - 2019) * 0.005
                
            entry = {
                "year": year,
                "carbon_emissions": int(base_carbon * (1 - carbon_reduction)),
                "renewable_energy_percentage": min(0.95, base_renewable + renewable_increase),
                "water_usage": int(base_water * (1 - (year - 2019) * 0.04)),
                "waste_generated": int(base_waste * (1 - (year - 2019) * 0.03)),
                "community_investment": int(10000000 * (1 + (year - 2019) * 0.1)),
                "jobs_created": int(1000 * (1 + (year - 2019) * 0.05))
            }
            impact_data[company].append(entry)
    
    return impact_data

@pytest.fixture
def sample_ethical_criteria() -> Dict[str, Any]:
    """Sample ethical criteria for screening investments."""
    return {
        "criteria_id": "test-criteria",
        "name": "Default Ethical Criteria",
        "environmental": {
            "min_environmental_score": 60,
            "max_carbon_footprint": 50000000,
            "min_renewable_energy_use": 0.5,
            "exclude_fossil_fuel_production": True,
            "weight": 0.4
        },
        "social": {
            "min_social_score": 65,
            "min_diversity_score": 0.6,
            "exclude_human_rights_violations": True,
            "exclude_weapons_manufacturing": True,
            "weight": 0.3
        },
        "governance": {
            "min_governance_score": 70,
            "min_board_independence": 0.7,
            "exclude_excessive_executive_compensation": True,
            "weight": 0.3
        },
        "exclusions": [
            "tobacco",
            "gambling",
            "adult_entertainment",
            "military_contracting"
        ],
        "inclusions": [
            "renewable_energy",
            "sustainable_agriculture",
            "education",
            "healthcare"
        ],
        "min_overall_score": 65
    }