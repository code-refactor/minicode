"""
Pytest configuration and shared fixtures.
"""
import pytest

# Import fixtures from test_data.py
from tests.product_manager.fixtures.test_data import (
    temp_data_dir,
    feedback_samples,
    theme_samples,
    cluster_samples,
    strategic_goal_samples,
    feature_samples,
    competitor_samples,
    competitive_feature_samples,
    market_gap_samples,
    decision_samples,
    stakeholder_samples,
    perspective_samples,
    stakeholder_relationship_samples
)