"""
Feedback Analysis module for GameVault.

This module provides analysis capabilities for feedback data.
"""

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.feedback_system.database import FeedbackDatabase
from gamevault.models import FeedbackEntry, ProjectVersion


class FeedbackAnalysis:
    """
    Analysis tools for feedback data.
    
    This class provides methods for analyzing feedback data to extract
    insights and patterns.
    """
    
    def __init__(self, feedback_db: FeedbackDatabase):
        """
        Initialize the feedback analysis.
        
        Args:
            feedback_db: Feedback database instance
        """
        self.feedback_db = feedback_db
    
    def get_common_terms(
        self,
        feedback_entries: List[FeedbackEntry],
        min_length: int = 4,
        max_terms: int = 20,
        stop_words: Optional[Set[str]] = None
    ) -> List[Tuple[str, int]]:
        """
        Extract common terms from feedback content.
        
        Args:
            feedback_entries: List of feedback entries to analyze
            min_length: Minimum length of terms to consider
            max_terms: Maximum number of terms to return
            stop_words: Set of stop words to exclude
            
        Returns:
            List[Tuple[str, int]]: List of (term, count) tuples
        """
        if not stop_words:
            stop_words = {
                "the", "and", "that", "this", "with", "for", "was", "have", "game",
                "are", "not", "but", "from", "there", "when", "would", "could", "they",
                "been", "were", "then", "than", "also", "will", "more", "just", "very",
                "like", "should", "been", "only", "some", "much", "what", "which", "their"
            }
        
        # Extract all words from feedback content
        words = []
        for feedback in feedback_entries:
            # Convert to lowercase and split by non-alphanumeric characters
            content_words = re.findall(r'\b[a-z0-9]+\b', feedback.content.lower())
            words.extend(content_words)
        
        # Filter words
        filtered_words = [word for word in words if len(word) >= min_length and word not in stop_words]
        
        # Count occurrences
        word_counts = Counter(filtered_words)
        
        # Get most common terms
        return word_counts.most_common(max_terms)
    
    def get_feedback_over_time(
        self,
        version_history: List[ProjectVersion],
        category: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> Dict[str, Dict[str, int]]:
        """
        Track feedback patterns over time across versions.
        
        Args:
            version_history: List of versions in chronological order
            category: Filter by category
            resolved: Filter by resolved status
            
        Returns:
            Dict[str, Dict[str, int]]: Dictionary mapping version IDs to category counts
        """
        result = {}
        
        for version in version_history:
            feedback = self.feedback_db.list_feedback(
                version_id=version.id,
                category=category,
                resolved=resolved
            )
            
            # Count by category
            category_counts = Counter(f.category for f in feedback)
            
            result[version.id] = {
                'name': version.name,
                'timestamp': version.timestamp,
                'counts': dict(category_counts),
                'total': len(feedback)
            }
        
        return result
    
    def identify_recurring_issues(
        self,
        version_history: List[ProjectVersion],
        threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Identify recurring issues across multiple versions.
        
        Args:
            version_history: List of versions in chronological order
            threshold: Minimum number of versions where the issue appears
            
        Returns:
            List[Dict[str, Any]]: List of recurring issues
        """
        # Get all bug feedback for each version
        feedback_by_version = {}
        for version in version_history:
            feedback_by_version[version.id] = self.feedback_db.list_feedback(
                version_id=version.id,
                category='bug'
            )
        
        # Extract common terms from each version's feedback
        terms_by_version = {}
        for version_id, feedback in feedback_by_version.items():
            terms_by_version[version_id] = set(term for term, _ in self.get_common_terms(feedback))
        
        # Find terms that appear in multiple versions
        term_versions = defaultdict(list)
        for version_id, terms in terms_by_version.items():
            for term in terms:
                term_versions[term].append(version_id)
        
        # Filter by threshold
        recurring_terms = {term: versions for term, versions in term_versions.items() if len(versions) >= threshold}
        
        # Format results
        results = []
        for term, versions in recurring_terms.items():
            # Get example feedback entries containing this term
            examples = []
            for version_id in versions:
                for feedback in feedback_by_version[version_id]:
                    if term.lower() in feedback.content.lower():
                        examples.append({
                            'id': feedback.id,
                            'version_id': version_id,
                            'content': feedback.content[:100] + ('...' if len(feedback.content) > 100 else '')
                        })
                        break  # One example per version is enough
            
            results.append({
                'term': term,
                'version_count': len(versions),
                'versions': versions,
                'examples': examples
            })
        
        # Sort by version count (most recurring first)
        results.sort(key=lambda x: x['version_count'], reverse=True)
        
        return results
    
    def get_sentiment_distribution(
        self,
        feedback_entries: List[FeedbackEntry]
    ) -> Dict[str, int]:
        """
        Simple sentiment analysis of feedback entries.
        
        This is a very basic implementation. For a real project, you might
        want to use a proper NLP library.
        
        Args:
            feedback_entries: List of feedback entries to analyze
            
        Returns:
            Dict[str, int]: Distribution of sentiments
        """
        # Simple keyword-based sentiment analysis
        positive_keywords = {
            "like", "love", "great", "good", "excellent", "awesome", "amazing",
            "cool", "fantastic", "wonderful", "enjoy", "nice", "fun", "best"
        }
        negative_keywords = {
            "bug", "issue", "problem", "crash", "error", "glitch", "hate", "bad",
            "terrible", "awful", "broken", "poor", "worst", "annoying", "frustrating"
        }
        
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        
        for feedback in feedback_entries:
            content = feedback.content.lower()
            pos_count = sum(1 for word in positive_keywords if word in content)
            neg_count = sum(1 for word in negative_keywords if word in content)
            
            if pos_count > neg_count:
                sentiments["positive"] += 1
            elif neg_count > pos_count:
                sentiments["negative"] += 1
            else:
                sentiments["neutral"] += 1
        
        return sentiments
    
    def analyze_feature_feedback(
        self,
        feature_tag: str,
        version_history: List[ProjectVersion]
    ) -> Dict[str, Any]:
        """
        Analyze feedback related to a specific feature across versions.
        
        Args:
            feature_tag: Tag identifying the feature
            version_history: List of versions in chronological order
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Get all feedback with the feature tag for each version
        feedback_by_version = {}
        for version in version_history:
            feedback_by_version[version.id] = self.feedback_db.list_feedback(
                version_id=version.id,
                tag=feature_tag
            )
        
        # Prepare analysis results
        results = {
            "feature_tag": feature_tag,
            "total_feedback": sum(len(feedback) for feedback in feedback_by_version.values()),
            "by_version": {},
            "common_terms": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }
        
        # Combine all feedback for feature-wide analysis
        all_feature_feedback = []
        for feedback_list in feedback_by_version.values():
            all_feature_feedback.extend(feedback_list)
        
        # Get common terms across all versions
        if all_feature_feedback:
            results["common_terms"] = self.get_common_terms(all_feature_feedback)
            results["sentiment"] = self.get_sentiment_distribution(all_feature_feedback)
        
        # Per-version analysis
        for version in version_history:
            feedback_list = feedback_by_version[version.id]
            
            if not feedback_list:
                continue
            
            version_sentiment = self.get_sentiment_distribution(feedback_list)
            version_terms = self.get_common_terms(feedback_list, max_terms=5)
            
            # Count by category
            category_counts = Counter(f.category for f in feedback_list)
            
            results["by_version"][version.id] = {
                "name": version.name,
                "timestamp": version.timestamp,
                "feedback_count": len(feedback_list),
                "sentiment": version_sentiment,
                "common_terms": version_terms,
                "category_counts": dict(category_counts)
            }
        
        return results
    
    def get_player_engagement(
        self,
        player_id: str,
        version_history: List[ProjectVersion]
    ) -> Dict[str, Any]:
        """
        Analyze a specific player's engagement across versions.
        
        Args:
            player_id: ID of the player
            version_history: List of versions in chronological order
            
        Returns:
            Dict[str, Any]: Player engagement metrics
        """
        # Get all feedback from this player
        all_player_feedback = self.feedback_db.list_feedback(player_id=player_id)
        
        if not all_player_feedback:
            return {"player_id": player_id, "feedback_count": 0}
        
        # Group feedback by version
        feedback_by_version = defaultdict(list)
        for feedback in all_player_feedback:
            feedback_by_version[feedback.version_id].append(feedback)
        
        # Get version names for referenced versions
        version_names = {}
        for version in version_history:
            version_names[version.id] = version.name
        
        # Analyze player engagement
        results = {
            "player_id": player_id,
            "feedback_count": len(all_player_feedback),
            "first_feedback": min(all_player_feedback, key=lambda f: f.timestamp).timestamp,
            "latest_feedback": max(all_player_feedback, key=lambda f: f.timestamp).timestamp,
            "versions_with_feedback": len(feedback_by_version),
            "by_version": {},
            "by_category": dict(Counter(f.category for f in all_player_feedback)),
            "common_terms": self.get_common_terms(all_player_feedback, max_terms=10),
            "sentiment": self.get_sentiment_distribution(all_player_feedback)
        }
        
        # Per-version breakdown
        for version_id, feedback_list in feedback_by_version.items():
            results["by_version"][version_id] = {
                "name": version_names.get(version_id, "Unknown"),
                "feedback_count": len(feedback_list),
                "categories": dict(Counter(f.category for f in feedback_list)),
                "sentiment": self.get_sentiment_distribution(feedback_list)
            }
        
        return results