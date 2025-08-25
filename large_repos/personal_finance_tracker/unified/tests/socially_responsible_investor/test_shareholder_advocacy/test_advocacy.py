"""Tests for the shareholder advocacy tracker."""

import pytest
from unittest.mock import patch, MagicMock
import time
from datetime import date
from typing import Dict, List, Any

from ethical_finance.models import ShareholderResolution, Portfolio
from ethical_finance.shareholder_advocacy.advocacy import (
    ShareholderAdvocacyTracker,
    VotingAnalysisResult,
    VotingRecommendation
)


class TestShareholderAdvocacy:
    """Test class for the shareholder advocacy tracker."""
    
    def test_initialize_tracker(self):
        """Test initializing the shareholder advocacy tracker."""
        # Initialize with default value priorities
        tracker = ShareholderAdvocacyTracker()
        
        assert hasattr(tracker, "value_priorities")
        assert isinstance(tracker.value_priorities, dict)
        assert "environmental" in tracker.value_priorities
        assert "social" in tracker.value_priorities
        assert "governance" in tracker.value_priorities
        
        # Initialize with custom value priorities
        custom_priorities = {
            "environmental": 0.6,
            "social": 0.2,
            "governance": 0.2,
            "climate": 0.8
        }
        tracker = ShareholderAdvocacyTracker(custom_priorities)
        
        assert tracker.value_priorities == custom_priorities
    
    def test_analyze_company_voting_record_with_resolutions(self, sample_shareholder_resolutions):
        """Test analyzing voting patterns for a company with resolutions."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
        
        # Choose a company that has resolutions
        company_id = "AAPL"  # Apple Inc.
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Analyze voting record
        result = tracker.analyze_company_voting_record(company_id, resolutions)
        
        # Verify result
        assert isinstance(result, VotingAnalysisResult)
        assert result.entity_id == company_id
        assert result.entity_type == "company"
        assert isinstance(result.analysis_date, date)
        assert result.total_resolutions > 0
        assert len(result.category_breakdown) > 0
        assert isinstance(result.passing_rate, float)
        assert isinstance(result.management_support_rate, float)
        assert len(result.key_findings) > 0
        assert "resolutions" in result.supporting_data
        assert result.processing_time_ms > 0
    
    def test_analyze_company_voting_record_no_resolutions(self, sample_shareholder_resolutions):
        """Test analyzing voting patterns for a company with no resolutions."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
        
        # Choose a company that has no resolutions
        company_id = "NONEXISTENT"
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Analyze voting record
        result = tracker.analyze_company_voting_record(company_id, resolutions)
        
        # Verify result handles no resolutions
        assert isinstance(result, VotingAnalysisResult)
        assert result.entity_id == company_id
        assert result.total_resolutions == 0
        assert result.passing_rate == 0.0
        assert result.management_support_rate == 0.0
        assert len(result.key_findings) == 1
        assert "No resolutions found" in result.key_findings[0]
    
    def test_analyze_issue_voting_patterns(self, sample_shareholder_resolutions):
        """Test analyzing voting patterns for a specific ESG issue category."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
        
        # Choose a category that has resolutions
        issue_category = "environmental"
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Analyze issue voting patterns
        result = tracker.analyze_issue_voting_patterns(issue_category, resolutions)
        
        # Verify result
        assert isinstance(result, VotingAnalysisResult)
        assert result.entity_id == issue_category
        assert result.entity_type == "resolution_category"
        assert result.total_resolutions > 0
        assert len(result.key_findings) > 0
        assert "company_breakdown" in result.supporting_data
        assert result.processing_time_ms > 0
    
    def test_analyze_issue_voting_patterns_no_resolutions(self, sample_shareholder_resolutions):
        """Test analyzing voting patterns for an issue with no resolutions."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
        
        # Choose a category that has no resolutions
        issue_category = "nonexistent_category"
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Analyze issue voting patterns
        result = tracker.analyze_issue_voting_patterns(issue_category, resolutions)
        
        # Verify result handles no resolutions
        assert isinstance(result, VotingAnalysisResult)
        assert result.entity_id == issue_category
        assert result.total_resolutions == 0
        assert result.passing_rate == 0.0
        assert len(result.key_findings) == 1
        assert "No resolutions found" in result.key_findings[0]
    
    def test_generate_voting_recommendations(self, sample_shareholder_resolutions):
        """Test generating voting recommendations for upcoming shareholder resolutions."""
        # Convert sample data to ShareholderResolution models
        past_resolutions = []
        
        # Use only completed resolutions for past data
        for res_data in sample_shareholder_resolutions:
            if res_data["status"] == "voted":
                past_resolutions.append(ShareholderResolution(
                    company_id=res_data["company_id"],
                    resolution_id=res_data["resolution_id"],
                    year=res_data["year"],
                    title=res_data["title"],
                    category=res_data["category"],
                    subcategory=res_data["subcategory"],
                    proposed_by=res_data["proposed_by"],
                    status=res_data["status"],
                    votes_for=res_data["votes_for"],
                    votes_against=res_data["votes_against"],
                    abstentions=res_data["abstentions"],
                    company_recommendation=res_data["company_recommendation"],
                    outcome=res_data["outcome"]
                ))
        
        # Create upcoming resolutions based on past ones but with new IDs and status
        upcoming_resolutions = []
        for i, past in enumerate(past_resolutions[:2]):  # Use first 2 as templates
            upcoming = ShareholderResolution(
                company_id=past.company_id,
                resolution_id=f"UPCOMING-{i+1}",
                year=date.today().year,
                title=f"Upcoming {past.title}",
                category=past.category,
                subcategory=past.subcategory,
                proposed_by=past.proposed_by,
                status="pending",
                votes_for=None,
                votes_against=None,
                abstentions=None,
                company_recommendation=None,
                outcome=None
            )
            upcoming_resolutions.append(upcoming)
        
        # Initialize tracker with strong environmental priority
        value_priorities = {
            "environmental": 0.6,
            "social": 0.2,
            "governance": 0.2,
            "climate": 0.8
        }
        tracker = ShareholderAdvocacyTracker(value_priorities)
        
        # Generate recommendations
        recommendations = tracker.generate_voting_recommendations(upcoming_resolutions, past_resolutions)
        
        # Verify recommendations
        assert isinstance(recommendations, dict)
        assert len(recommendations) == len(upcoming_resolutions)
        
        for res_id, rec in recommendations.items():
            assert isinstance(rec, VotingRecommendation)
            assert rec.resolution_id == res_id
            assert rec.recommendation in ["for", "against", "abstain"]
            assert 0.0 <= rec.confidence <= 1.0
            assert isinstance(rec.rationale, str)
            assert -1.0 <= rec.alignment_score <= 1.0
    
    def test_identify_engagement_opportunities(self, sample_portfolio, sample_shareholder_resolutions):
        """Test identifying opportunities for shareholder engagement."""
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
        
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            # Make sure we have resolutions for companies in our portfolio
            if res_data["company_id"] in [h.investment_id for h in portfolio.holdings]:
                resolutions.append(ShareholderResolution(
                    company_id=res_data["company_id"],
                    resolution_id=res_data["resolution_id"],
                    year=res_data["year"],
                    title=res_data["title"],
                    category=res_data["category"],
                    subcategory=res_data["subcategory"],
                    proposed_by=res_data["proposed_by"],
                    status=res_data["status"],
                    votes_for=res_data["votes_for"],
                    votes_against=res_data["votes_against"],
                    abstentions=res_data["abstentions"],
                    company_recommendation=res_data["company_recommendation"],
                    outcome=res_data["outcome"]
                ))
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Identify engagement opportunities
        opportunities = tracker.identify_engagement_opportunities(portfolio, resolutions)
        
        # Verify opportunities
        assert isinstance(opportunities, list)
        
        # Test might not find opportunities if there aren't enough resolutions
        # or they don't match our criteria, so we just check the format if any exist
        for opportunity in opportunities:
            assert "company_id" in opportunity
            assert "category" in opportunity
            assert "alignment_score" in opportunity
            assert "opportunity_type" in opportunity
            assert "priority" in opportunity
    
    def test_calculate_value_alignment(self, sample_shareholder_resolutions):
        """Test calculating value alignment for a resolution."""
        # Convert a sample resolution to ShareholderResolution model
        res_data = sample_shareholder_resolutions[0]  # Use first resolution
        resolution = ShareholderResolution(
            company_id=res_data["company_id"],
            resolution_id=res_data["resolution_id"],
            year=res_data["year"],
            title=res_data["title"],
            category=res_data["category"],
            subcategory=res_data["subcategory"],
            proposed_by=res_data["proposed_by"],
            status=res_data["status"],
            votes_for=res_data["votes_for"],
            votes_against=res_data["votes_against"],
            abstentions=res_data["abstentions"],
            company_recommendation=res_data["company_recommendation"],
            outcome=res_data["outcome"]
        )
        
        # Create tracker with custom priorities that emphasize the resolution's category
        value_priorities = {
            resolution.category: 0.8,
            "other_category": 0.2
        }
        tracker = ShareholderAdvocacyTracker(value_priorities)
        
        # Calculate alignment
        alignment = tracker._calculate_value_alignment(resolution)
        
        # Verify alignment
        assert isinstance(alignment, float)
        assert -1.0 <= alignment <= 1.0
        
        # Should have high alignment since we prioritized this category
        assert alignment > 0.3
        
        # Create another tracker with opposite priorities
        opposite_priorities = {
            resolution.category: 0.1,
            "other_category": 0.9
        }
        opposite_tracker = ShareholderAdvocacyTracker(opposite_priorities)
        
        # Calculate alignment with opposite priorities
        opposite_alignment = opposite_tracker._calculate_value_alignment(resolution)
        
        # Alignment should be lower with opposite priorities
        assert opposite_alignment < alignment
    
    def test_find_similar_resolutions(self, sample_shareholder_resolutions):
        """Test finding similar past resolutions."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        for res_data in sample_shareholder_resolutions:
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
        
        # Choose a resolution to find similar ones for
        target_resolution = resolutions[0]
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Find similar resolutions
        similar = tracker._find_similar_resolutions(target_resolution, resolutions)
        
        # Verify results
        assert isinstance(similar, list)
        # At least the target resolution itself should be similar (if it has outcome)
        if target_resolution.outcome in ["passed", "failed"]:
            assert len(similar) >= 1
        
        # All similar resolutions should match company and category
        for res in similar:
            assert res.company_id == target_resolution.company_id
            assert res.category == target_resolution.category
            assert res.outcome in ["passed", "failed"]  # Should have a valid outcome
    
    def test_analyze_trends(self, sample_shareholder_resolutions):
        """Test analyzing trends in resolutions over time."""
        # Convert sample data to ShareholderResolution models
        resolutions = []
        
        # Modify sample data to have multiple years for trend analysis
        for res_data in sample_shareholder_resolutions:
            # Create original resolution
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=res_data["resolution_id"],
                year=res_data["year"],
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status=res_data["status"],
                votes_for=res_data["votes_for"],
                votes_against=res_data["votes_against"],
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome=res_data["outcome"]
            ))
            
            # Create a version from the previous year with slightly different voting
            resolutions.append(ShareholderResolution(
                company_id=res_data["company_id"],
                resolution_id=f"{res_data['resolution_id']}-prev",
                year=res_data["year"] - 1,
                title=res_data["title"],
                category=res_data["category"],
                subcategory=res_data["subcategory"],
                proposed_by=res_data["proposed_by"],
                status="voted",
                votes_for=max(0, min(1, res_data["votes_for"] - 0.1)),  # Lower support in previous year
                votes_against=min(1, max(0, res_data["votes_against"] + 0.1)),
                abstentions=res_data["abstentions"],
                company_recommendation=res_data["company_recommendation"],
                outcome="passed" if res_data["votes_for"] - 0.1 > 0.5 else "failed",
            ))
        
        # Initialize tracker
        tracker = ShareholderAdvocacyTracker()
        
        # Analyze trends for a subset of resolutions (e.g., for one company)
        company_id = "AAPL"
        company_resolutions = [r for r in resolutions if r.company_id == company_id]
        
        # Should have at least some resolutions for the company
        assert len(company_resolutions) >= 2
        
        # Analyze trends
        trends = tracker._analyze_trends(company_resolutions)
        
        # Verify results
        assert isinstance(trends, dict)
        assert "trend" in trends
        assert trends["trend"] in ["increasing_support", "decreasing_support", "stable_support", "insufficient_data"]
        
        if trends["trend"] != "insufficient_data":
            assert "passing_rates_by_year" in trends
            assert "resolutions_by_year" in trends
            assert len(trends["passing_rates_by_year"]) >= 2  # At least two years