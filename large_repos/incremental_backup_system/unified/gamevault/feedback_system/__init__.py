"""
Feedback Correlation System for GameVault.

This package provides tools for correlating player feedback with game versions,
enabling game developers to connect player comments with specific builds.
"""

from gamevault.feedback_system.analysis import FeedbackAnalysis
from gamevault.feedback_system.database import FeedbackDatabase
from gamevault.feedback_system.manager import FeedbackManager

__all__ = [
    'FeedbackAnalysis',
    'FeedbackDatabase',
    'FeedbackManager',
]