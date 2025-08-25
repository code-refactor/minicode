"""
Feedback Analysis Engine - Core module for processing user feedback.

This module provides capabilities for:
- Natural language processing for theme extraction
- Clustering algorithms for grouping related feedback
- Sentiment analysis for emotional content classification
- Frequency and impact assessment for feedback weighting
- Trend detection for emerging user concerns
"""
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union
import json
import os
import re
from uuid import UUID


class UUIDCompatDict(dict):
    """A dictionary wrapper that allows access by both UUID objects and string keys."""
    
    def __init__(self, underlying_dict):
        super().__init__(underlying_dict)
        self._dict = underlying_dict
    
    def __contains__(self, key):
        if isinstance(key, UUID):
            return str(key) in self._dict
        return key in self._dict
    
    def __getitem__(self, key):
        if isinstance(key, UUID):
            return self._dict[str(key)]
        return self._dict[key]
    
    def __setitem__(self, key, value):
        if isinstance(key, UUID):
            self._dict[str(key)] = value
        else:
            self._dict[key] = value
    
    def get(self, key, default=None):
        if isinstance(key, UUID):
            return self._dict.get(str(key), default)
        return self._dict.get(key, default)
    
    def keys(self):
        return self._dict.keys()
    
    def values(self):
        return self._dict.values()
    
    def items(self):
        return self._dict.items()
    
    def __len__(self):
        return len(self._dict)
    
    def __iter__(self):
        return iter(self._dict)

import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from common.core import EntityStorage
from productmind.models import (
    Feedback, 
    FeedbackCluster, 
    Sentiment, 
    SourceType, 
    Theme
)


class FeedbackAnalysisEngine:
    """
    Engine for analyzing customer feedback through NLP, clustering, and sentiment analysis.
    
    This class provides methods to:
    - Process and analyze batches of feedback
    - Extract themes and topics from feedback
    - Cluster similar feedback items
    - Analyze sentiment of feedback
    - Detect trends in feedback over time
    """
    
    def __init__(
        self,
        storage_dir: str = "./data",
        vectorizer_max_features: int = 10000,
        min_cluster_size: int = 5,
        n_clusters: int = None,
        max_themes: int = 20
    ):
        """
        Initialize the feedback analysis engine.
        
        Args:
            storage_dir: Directory to store feedback data
            vectorizer_max_features: Maximum features for TF-IDF vectorizer
            min_cluster_size: Minimum samples per cluster for DBSCAN
            n_clusters: Number of clusters for KMeans (if None, auto-determined)
            max_themes: Maximum number of themes to extract
        """
        self.storage_dir = storage_dir
        self.feedback_storage = EntityStorage[Feedback](storage_dir, Feedback)
        self.cluster_storage = EntityStorage[FeedbackCluster](storage_dir, FeedbackCluster)
        self.theme_storage = EntityStorage[Theme](storage_dir, Theme)
        
        self.vectorizer = TfidfVectorizer(
            max_features=vectorizer_max_features,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2
        )
        self.min_cluster_size = min_cluster_size
        self.n_clusters = n_clusters
        self.max_themes = max_themes
        
        # Create required directories for backward compatibility
        for subdir in ["feedback", "clusters", "themes"]:
            os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)
        
        # Backward compatibility: expose EntityStorage caches with UUID compatibility
        self._feedback_cache = UUIDCompatDict(self.feedback_storage._cache)
        self._clusters = UUIDCompatDict(self.cluster_storage._cache)
        self._themes = UUIDCompatDict(self.theme_storage._cache)
    
    def add_feedback(self, feedback: Union[Feedback, List[Feedback]]) -> List[str]:
        """
        Add new feedback to the system.
        
        Args:
            feedback: Single feedback item or list of feedback items
            
        Returns:
            List of feedback IDs that were added
        """
        if isinstance(feedback, Feedback):
            feedback = [feedback]
        
        # Use batch save for multiple feedback, but also create JSON files for compatibility
        if len(feedback) > 1:
            self.feedback_storage.save_batch(feedback)
            # Create JSON files for backward compatibility
            for item in feedback:
                self._create_feedback_json_file(item)
        else:
            self.feedback_storage.save(feedback[0])
            # Create JSON file for backward compatibility
            self._create_feedback_json_file(feedback[0])
        
        return [str(item.id) for item in feedback]
    
    def _create_feedback_json_file(self, feedback: Feedback) -> None:
        """
        Create a JSON file for feedback backward compatibility.
        
        Args:
            feedback: Feedback item to create JSON file for
        """
        feedback_dir = os.path.join(self.storage_dir, "feedback")
        json_file_path = os.path.join(feedback_dir, f"{feedback.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(feedback.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # If JSON creation fails, don't break the main functionality
            pass
    
    def _create_cluster_json_file(self, cluster) -> None:
        """
        Create a JSON file for cluster backward compatibility.
        
        Args:
            cluster: Cluster item to create JSON file for
        """
        clusters_dir = os.path.join(self.storage_dir, "clusters")
        json_file_path = os.path.join(clusters_dir, f"{cluster.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(cluster.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # If JSON creation fails, don't break the main functionality
            pass
    
    def _create_theme_json_file(self, theme) -> None:
        """
        Create a JSON file for theme backward compatibility.
        
        Args:
            theme: Theme item to create JSON file for
        """
        themes_dir = os.path.join(self.storage_dir, "themes")
        json_file_path = os.path.join(themes_dir, f"{theme.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(theme.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # If JSON creation fails, don't break the main functionality
            pass
    
    def _store_feedback(self, feedback: Feedback) -> None:
        """
        Store feedback using the EntityStorage system.
        
        Args:
            feedback: Feedback item to store
        """
        self.feedback_storage.save(feedback)
        
        # Backward compatibility: create JSON file
        self._create_feedback_json_file(feedback)
    
    def get_feedback(self, feedback_id: Union[str, UUID]) -> Optional[Feedback]:
        """
        Retrieve feedback by ID.
        
        Args:
            feedback_id: ID of feedback to retrieve (string or UUID)
            
        Returns:
            Feedback item if found, None otherwise
        """
        if isinstance(feedback_id, str):
            try:
                feedback_id = UUID(feedback_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.feedback_storage.get(feedback_id)
    
    def get_all_feedback(self) -> List[Feedback]:
        """
        Retrieve all feedback.
        
        Returns:
            List of all feedback items
        """
        return self.feedback_storage.list_all()
    
    def analyze_sentiment(self, feedback: Union[Feedback, List[Feedback]]) -> Dict[str, Sentiment]:
        """
        Analyze sentiment of feedback.
        
        This is a simple rule-based sentiment analyzer. In a real implementation,
        this would use a more sophisticated NLP model.
        
        Args:
            feedback: Single feedback item or list of feedback items
            
        Returns:
            Dictionary mapping feedback ID to sentiment
        """
        if isinstance(feedback, Feedback):
            feedback = [feedback]
        
        results = {}
        
        positive_words = {
            "good", "great", "excellent", "amazing", "love", "like", "helpful",
            "awesome", "fantastic", "best", "perfect", "easy", "pleased", "happy"
        }

        negative_words = {
            "bad", "poor", "terrible", "awful", "hate", "dislike", "difficult",
            "confusing", "frustrating", "worst", "buggy", "slow", "issue", "problem",
            "broken", "can't", "cannot"
        }
        
        for item in feedback:
            text = item.content.lower()
            words = set(re.findall(r'\b\w+\b', text))
            
            positive_count = len(words.intersection(positive_words))
            negative_count = len(words.intersection(negative_words))
            
            if positive_count > negative_count * 2:
                sentiment = Sentiment.POSITIVE
            elif negative_count > positive_count * 2:
                sentiment = Sentiment.NEGATIVE
            elif positive_count > 0 and negative_count > 0:
                sentiment = Sentiment.MIXED
            else:
                sentiment = Sentiment.NEUTRAL
            
            # Update the feedback item with the sentiment
            item.sentiment = sentiment
            self._store_feedback(item)
            
            results[str(item.id)] = sentiment
        
        return results
    
    def cluster_feedback(
        self, 
        feedback_ids: Optional[List[str]] = None,
        algorithm: str = "kmeans",
        force_recompute: bool = False
    ) -> List[FeedbackCluster]:
        """
        Cluster feedback into groups of similar items.
        
        Args:
            feedback_ids: List of feedback IDs to cluster (if None, use all feedback)
            algorithm: Clustering algorithm to use ("kmeans" or "dbscan")
            force_recompute: Whether to force recomputation of existing clusters
            
        Returns:
            List of feedback clusters
        """
        # Get all feedback if feedback_ids not provided
        if feedback_ids is None:
            all_feedback = self.get_all_feedback()
            feedback_ids = [str(item.id) for item in all_feedback]
        
        # Get feedback items from IDs
        feedback_items = []
        for fid in feedback_ids:
            item = self.get_feedback(fid)
            if item:
                feedback_items.append(item)
        
        if not feedback_items:
            return []
        
        # Extract content for vectorization
        texts = [item.content for item in feedback_items]
        
        # Vectorize text
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        # Perform clustering
        if algorithm == "kmeans":
            # Determine number of clusters if not provided
            if self.n_clusters is None:
                n_clusters = min(max(3, len(feedback_items) // 10), 20)
            else:
                n_clusters = self.n_clusters
                
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            centroids = kmeans.cluster_centers_
            
        elif algorithm == "dbscan":
            # Compute similarity matrix
            similarity_matrix = cosine_similarity(tfidf_matrix)
            dbscan = DBSCAN(
                eps=0.3,
                min_samples=self.min_cluster_size,
                metric="precomputed"
            )
            # DBSCAN expects distances, not similarities
            # Ensure values are non-negative by using absolute values and clipping
            distances = np.clip(1 - similarity_matrix, 0, 2)
            cluster_labels = dbscan.fit_predict(distances)
            
            # Compute centroids for each cluster
            centroids = []
            for label in set(cluster_labels):
                if label == -1:  # Noise points in DBSCAN
                    centroids.append(np.zeros(tfidf_matrix.shape[1]))
                else:
                    mask = cluster_labels == label
                    centroid = tfidf_matrix[mask].toarray().mean(axis=0)
                    centroids.append(centroid)
            centroids = np.array(centroids)
        else:
            raise ValueError(f"Unsupported clustering algorithm: {algorithm}")
        
        # Create cluster objects
        clusters = []
        cluster_map = defaultdict(list)
        
        # Group feedback by cluster
        for i, label in enumerate(cluster_labels):
            if label != -1:  # Skip noise points from DBSCAN
                cluster_map[int(label)].append(feedback_items[i])
        
        # Create cluster objects
        for label, items in cluster_map.items():
            if len(items) < 1:
                continue
                
            # Get top terms for this cluster
            if label < len(centroids):
                centroid = centroids[label]
                feature_names = self.vectorizer.get_feature_names_out()
                
                # Get top terms from centroid
                if isinstance(centroid, np.ndarray):
                    top_indices = centroid.argsort()[-10:][::-1]
                    top_terms = [feature_names[i] for i in top_indices]
                else:
                    dense_centroid = centroid.toarray()[0]
                    top_indices = dense_centroid.argsort()[-10:][::-1]
                    top_terms = [feature_names[i] for i in top_indices]
            else:
                top_terms = []
            
            # Get sentiment distribution
            sentiment_counts = Counter(item.sentiment for item in items if item.sentiment)
            sentiment_dist = {
                sentiment: sentiment_counts.get(sentiment, 0) for sentiment in Sentiment
            }
            
            # Create cluster name from common terms
            cluster_name = " ".join(top_terms[:3])
            if not cluster_name:
                cluster_name = f"Cluster {label}"
            
            # Create cluster object
            cluster = FeedbackCluster(
                cluster_id=label,  # Use cluster_id instead of id
                name=cluster_name,
                description=f"Cluster containing {len(items)} feedback items",
                centroid=centroid.tolist() if isinstance(centroid, np.ndarray) else centroid.toarray()[0].tolist(),
                feedback_ids=[str(item.id) for item in items],  # Store as strings for compatibility
                themes=top_terms[:5],
                sentiment_distribution=sentiment_dist
            )
            
            # Store cluster
            self.cluster_storage.save(cluster)
            clusters.append(cluster)
            
            # Backward compatibility: create JSON file in clusters directory
            self._create_cluster_json_file(cluster)
            
            # Update feedback items with cluster ID (use cluster UUID for compatibility)
            for item in items:
                item.cluster_id = cluster.id
                self._store_feedback(item)
        
        return clusters
    
    def extract_themes(
        self, 
        feedback_ids: Optional[List[str]] = None,
        min_frequency: int = 3,
        force_recompute: bool = False
    ) -> List[Theme]:
        """
        Extract common themes from feedback.
        
        Args:
            feedback_ids: List of feedback IDs to analyze (if None, use all feedback)
            min_frequency: Minimum frequency for a theme to be considered
            force_recompute: Whether to force recomputation of existing themes
            
        Returns:
            List of extracted themes
        """
        # Get all feedback if feedback_ids not provided
        if feedback_ids is None:
            all_feedback = self.get_all_feedback()
            feedback_ids = [str(item.id) for item in all_feedback]
        
        # Get feedback items from IDs
        feedback_items = []
        for fid in feedback_ids:
            item = self.get_feedback(fid)
            if item:
                feedback_items.append(item)
        
        if not feedback_items:
            return []
        
        # Extract content for vectorization
        texts = [item.content for item in feedback_items]
        
        # Vectorize text
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Extract top terms across all documents
        tfidf_sums = tfidf_matrix.sum(axis=0).A1
        top_indices = tfidf_sums.argsort()[-50:][::-1]
        
        # Create theme objects
        themes = []
        theme_counter = 0
        
        for idx in top_indices:
            if theme_counter >= self.max_themes:
                break
                
            term = feature_names[idx]
            
            # Skip single character terms and very common words
            if len(term) <= 1:
                continue
                
            # Find related terms
            term_vector = np.zeros(len(feature_names))
            term_vector[idx] = 1
            
            # Get documents containing this term
            doc_indices = []
            for i, text in enumerate(texts):
                if term in text.lower():
                    doc_indices.append(i)
            
            if len(doc_indices) < min_frequency:
                continue
                
            # Calculate co-occurring terms
            co_terms = []
            if doc_indices:
                doc_vectors = tfidf_matrix[doc_indices].toarray()
                term_sums = doc_vectors.sum(axis=0)
                co_term_indices = term_sums.argsort()[-10:][::-1]
                co_terms = [feature_names[i] for i in co_term_indices]
            
            # Get sentiment distribution for this theme
            related_feedback = [feedback_items[i] for i in doc_indices]
            sentiment_counts = Counter(
                item.sentiment for item in related_feedback if item.sentiment
            )
            sentiment_dist = {
                sentiment: sentiment_counts.get(sentiment, 0) for sentiment in Sentiment
            }
            
            # Calculate impact score (based on frequency and sentiment)
            impact_score = (
                len(doc_indices) / len(feedback_items) * 10 +
                sentiment_counts.get(Sentiment.POSITIVE, 0) * 0.1 +
                sentiment_counts.get(Sentiment.NEGATIVE, 0) * 0.2
            )
            
            # Create theme object
            theme = Theme(
                name=term.title(),
                description=f"Theme related to {term} with {len(doc_indices)} mentions",
                keywords=co_terms,
                frequency=len(doc_indices),
                impact_score=impact_score,
                sentiment_distribution=sentiment_dist,
                feedback_ids=[str(feedback_items[i].id) for i in doc_indices]  # Store as strings for compatibility
            )
            
            # Store theme
            self.theme_storage.save(theme)
            themes.append(theme)
            
            # Backward compatibility: create JSON file in themes directory
            self._create_theme_json_file(theme)
            
            # Update feedback items with theme
            for i in doc_indices:
                feedback = feedback_items[i]
                if term.title() not in feedback.themes:
                    feedback.themes.append(term.title())
                    self._store_feedback(feedback)
            
            theme_counter += 1
        
        return themes
    
    def detect_trends(
        self,
        timeframe: str = "week",
        min_growth_rate: float = 1.5,
        limit: int = 10
    ) -> List[Dict]:
        """
        Detect emerging trends in feedback over time.
        
        Args:
            timeframe: Time period for trend analysis ("day", "week", "month")
            min_growth_rate: Minimum growth rate to consider a trend
            limit: Maximum number of trends to return
            
        Returns:
            List of trending themes with growth metrics
        """
        all_feedback = self.get_all_feedback()
        
        if not all_feedback:
            return []
            
        # Determine time periods based on timeframe
        now = datetime.now()
        
        if timeframe == "day":
            days_ago = lambda d: (now - d.created_at).total_seconds() / (24 * 3600)
            current_period = [f for f in all_feedback if days_ago(f) <= 1]
            previous_period = [f for f in all_feedback if 1 < days_ago(f) <= 2]
        elif timeframe == "week":
            weeks_ago = lambda d: (now - d.created_at).total_seconds() / (7 * 24 * 3600)
            current_period = [f for f in all_feedback if weeks_ago(f) <= 1]
            previous_period = [f for f in all_feedback if 1 < weeks_ago(f) <= 2]
        elif timeframe == "month":
            months_ago = lambda d: (now - d.created_at).days / 30
            current_period = [f for f in all_feedback if months_ago(f) <= 1]
            previous_period = [f for f in all_feedback if 1 < months_ago(f) <= 2]
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        # Count theme occurrences in each period
        current_themes = Counter()
        for feedback in current_period:
            for theme in feedback.themes:
                current_themes[theme] += 1
        
        previous_themes = Counter()
        for feedback in previous_period:
            for theme in feedback.themes:
                previous_themes[theme] += 1
        
        # Calculate growth rates
        trends = []
        
        for theme, current_count in current_themes.items():
            previous_count = previous_themes.get(theme, 0)
            
            # Avoid division by zero
            if previous_count == 0:
                if current_count >= 3:  # New theme with at least 3 mentions
                    growth_rate = float('inf')
                else:
                    continue
            else:
                growth_rate = current_count / previous_count
            
            if growth_rate >= min_growth_rate:
                trends.append({
                    "theme": theme,
                    "current_count": current_count,
                    "previous_count": previous_count,
                    "growth_rate": growth_rate if growth_rate != float('inf') else 999.99,
                    "is_new": previous_count == 0
                })
        
        # Sort trends by growth rate
        trends.sort(key=lambda x: x["growth_rate"], reverse=True)
        
        return trends[:limit]
    
    def get_cluster(self, cluster_id: Union[int, UUID]) -> Optional[FeedbackCluster]:
        """
        Get a cluster by ID.
        
        Args:
            cluster_id: ID of the cluster (int for legacy or UUID for new clusters)
            
        Returns:
            Cluster if found, None otherwise
        """
        # For integer cluster IDs, search by cluster_id field
        if isinstance(cluster_id, int):
            clusters = self.cluster_storage.query(cluster_id=cluster_id)
            return clusters[0] if clusters else None
        
        # For UUID cluster IDs, get directly
        return self.cluster_storage.get(cluster_id)
    
    def get_theme(self, theme_id: Union[str, UUID]) -> Optional[Theme]:
        """
        Get a theme by ID.
        
        Args:
            theme_id: ID of the theme (string or UUID)
            
        Returns:
            Theme if found, None otherwise
        """
        if isinstance(theme_id, str):
            try:
                theme_id = UUID(theme_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.theme_storage.get(theme_id)
    
    def get_all_clusters(self) -> List[FeedbackCluster]:
        """
        Get all clusters.
        
        Returns:
            List of all clusters
        """
        return self.cluster_storage.list_all()
    
    def get_all_themes(self) -> List[Theme]:
        """
        Get all themes.
        
        Returns:
            List of all themes
        """
        return self.theme_storage.list_all()
    
    def search_feedback(self, query: str, limit: int = 100) -> List[Feedback]:
        """
        Search for feedback items matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching feedback items
        """
        results = self.feedback_storage.search_text(query, ['content'])
        return results[:limit]
    
    def get_feedback_by_theme(self, theme_name: str) -> List[Feedback]:
        """
        Get all feedback items associated with a theme.
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            List of feedback items with the theme
        """
        return self.feedback_storage.query(themes=lambda themes: theme_name in themes)
    
    def get_feedback_by_cluster(self, cluster_id: Union[int, str, UUID]) -> List[Feedback]:
        """
        Get all feedback items in a cluster.
        
        Args:
            cluster_id: ID of the cluster (int, string, or UUID)
            
        Returns:
            List of feedback items in the cluster
        """
        # Handle different types of cluster_id
        if isinstance(cluster_id, UUID):
            # Direct UUID lookup
            return self.feedback_storage.query(cluster_id=cluster_id)
        elif isinstance(cluster_id, str):
            try:
                # Try converting to int first for backward compatibility
                int_id = int(cluster_id)
                return self.feedback_storage.query(cluster_id=int_id)
            except ValueError:
                # If not an int, try as UUID string
                try:
                    uuid_id = UUID(cluster_id)
                    return self.feedback_storage.query(cluster_id=uuid_id)
                except ValueError:
                    return []  # Invalid cluster ID
        else:
            # Assume it's an int (legacy cluster label)
            return self.feedback_storage.query(cluster_id=cluster_id)