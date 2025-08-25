"""
Competitive Analysis System - Framework for market intelligence.

This module provides capabilities for:
- Competitor profile management with feature inventories
- Comparative analysis across multiple product dimensions
- Gap identification between product offerings
- Timeline tracking of competitive feature releases
- Market positioning visualization using text-based matrices
"""
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union
import json
import os
from uuid import UUID

import numpy as np

from common.core import EntityStorage
from productmind.models import (
    Competitor,
    CompetitiveFeature,
    MarketGap
)


class CompetitiveAnalysisSystem:
    """
    System for analyzing competitive landscape and market positioning.
    
    This class provides methods to:
    - Manage competitor profiles and feature inventories
    - Perform comparative analysis across product dimensions
    - Identify gaps and opportunities in the market
    - Track competitive feature releases over time
    - Visualize market positioning using text-based matrices
    """
    
    def __init__(self, storage_dir: str = "./data"):
        """
        Initialize the competitive analysis system.
        
        Args:
            storage_dir: Directory to store data
        """
        self.storage_dir = storage_dir
        self.competitor_storage = EntityStorage[Competitor](storage_dir, Competitor)
        self.feature_storage = EntityStorage[CompetitiveFeature](storage_dir, CompetitiveFeature)
        self.gap_storage = EntityStorage[MarketGap](storage_dir, MarketGap)
        
        # Create required directories for backward compatibility
        for subdir in ["competitors", "competitive_features", "market_gaps"]:
            os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)
        
        # Backward compatibility: expose EntityStorage caches
        self._competitors_cache = self.competitor_storage._cache
        self._features_cache = self.feature_storage._cache
        self._gaps_cache = self.gap_storage._cache
    
    def add_competitor(self, competitor: Union[Competitor, List[Competitor]]) -> List[str]:
        """
        Add a new competitor or list of competitors to the system.
        
        Args:
            competitor: Competitor or list of competitors to add
            
        Returns:
            List of competitor IDs
        """
        if isinstance(competitor, Competitor):
            competitor = [competitor]
        
        # Use batch save for multiple competitors, but also create JSON files for compatibility
        if len(competitor) > 1:
            self.competitor_storage.save_batch(competitor)
            for item in competitor:
                self._create_competitor_json_file(item)
        else:
            self.competitor_storage.save(competitor[0])
            self._create_competitor_json_file(competitor[0])
        
        return [str(item.id) for item in competitor]
    
    def _create_competitor_json_file(self, competitor) -> None:
        """
        Create a JSON file for competitor backward compatibility.
        """
        competitors_dir = os.path.join(self.storage_dir, "competitors")
        json_file_path = os.path.join(competitors_dir, f"{competitor.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(competitor.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass
    
    def _create_competitive_feature_json_file(self, feature) -> None:
        """
        Create a JSON file for competitive feature backward compatibility.
        """
        features_dir = os.path.join(self.storage_dir, "competitive_features")
        json_file_path = os.path.join(features_dir, f"{feature.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(feature.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass
    
    def _create_market_gap_json_file(self, gap) -> None:
        """
        Create a JSON file for market gap backward compatibility.
        """
        gaps_dir = os.path.join(self.storage_dir, "market_gaps")
        json_file_path = os.path.join(gaps_dir, f"{gap.id}.json")
        
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(gap.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass
    
    def _store_competitor(self, competitor: Competitor) -> None:
        """
        Store a competitor using the EntityStorage system.
        
        Args:
            competitor: Competitor to store
        """
        self.competitor_storage.save(competitor)
        
        # Backward compatibility: create JSON file
        self._create_competitor_json_file(competitor)
    
    def add_competitive_feature(
        self, 
        feature: Union[CompetitiveFeature, List[CompetitiveFeature]]
    ) -> List[str]:
        """
        Add a new competitive feature or list of features to the system.
        
        Args:
            feature: Competitive feature or list of features to add
            
        Returns:
            List of feature IDs
        """
        if isinstance(feature, CompetitiveFeature):
            feature = [feature]
        
        # Use batch save for multiple features, but also create JSON files for compatibility
        if len(feature) > 1:
            self.feature_storage.save_batch(feature)
            for item in feature:
                self._create_competitive_feature_json_file(item)
        else:
            self.feature_storage.save(feature[0])
            self._create_competitive_feature_json_file(feature[0])
        
        return [str(item.id) for item in feature]
    
    def _store_competitive_feature(self, feature: CompetitiveFeature) -> None:
        """
        Store a competitive feature using the EntityStorage system.
        
        Args:
            feature: Competitive feature to store
        """
        self.feature_storage.save(feature)
        
        # Backward compatibility: create JSON file
        self._create_competitive_feature_json_file(feature)
    
    def add_market_gap(self, gap: Union[MarketGap, List[MarketGap]]) -> List[str]:
        """
        Add a new market gap or list of gaps to the system.
        
        Args:
            gap: Market gap or list of gaps to add
            
        Returns:
            List of gap IDs
        """
        if isinstance(gap, MarketGap):
            gap = [gap]
        
        # Use batch save for multiple gaps, but also create JSON files for compatibility
        if len(gap) > 1:
            self.gap_storage.save_batch(gap)
            for item in gap:
                self._create_market_gap_json_file(item)
        else:
            self.gap_storage.save(gap[0])
            self._create_market_gap_json_file(gap[0])
        
        return [str(item.id) for item in gap]
    
    def _store_market_gap(self, gap: MarketGap) -> None:
        """
        Store a market gap using the EntityStorage system.
        
        Args:
            gap: Market gap to store
        """
        self.gap_storage.save(gap)
        
        # Backward compatibility: create JSON file
        self._create_market_gap_json_file(gap)
    
    def get_competitor(self, competitor_id: Union[str, UUID]) -> Optional[Competitor]:
        """
        Retrieve a competitor by ID.
        
        Args:
            competitor_id: ID of the competitor to retrieve (string or UUID)
            
        Returns:
            Competitor if found, None otherwise
        """
        if isinstance(competitor_id, str):
            try:
                competitor_id = UUID(competitor_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.competitor_storage.get(competitor_id)
    
    def get_competitive_feature(self, feature_id: Union[str, UUID]) -> Optional[CompetitiveFeature]:
        """
        Retrieve a competitive feature by ID.
        
        Args:
            feature_id: ID of the feature to retrieve (string or UUID)
            
        Returns:
            Competitive feature if found, None otherwise
        """
        if isinstance(feature_id, str):
            try:
                feature_id = UUID(feature_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.feature_storage.get(feature_id)
    
    def get_market_gap(self, gap_id: Union[str, UUID]) -> Optional[MarketGap]:
        """
        Retrieve a market gap by ID.
        
        Args:
            gap_id: ID of the gap to retrieve (string or UUID)
            
        Returns:
            Market gap if found, None otherwise
        """
        if isinstance(gap_id, str):
            try:
                gap_id = UUID(gap_id)
            except ValueError:
                return None  # Invalid UUID string
        
        return self.gap_storage.get(gap_id)
    
    def get_all_competitors(self) -> List[Competitor]:
        """
        Retrieve all competitors.
        
        Returns:
            List of all competitors
        """
        return self.competitor_storage.list_all()
    
    def get_all_competitive_features(self) -> List[CompetitiveFeature]:
        """
        Retrieve all competitive features.
        
        Returns:
            List of all competitive features
        """
        return self.feature_storage.list_all()
    
    def get_all_market_gaps(self) -> List[MarketGap]:
        """
        Retrieve all market gaps.
        
        Returns:
            List of all market gaps
        """
        return self.gap_storage.list_all()
    
    def update_competitor_feature(
        self, 
        competitor_id: Union[str, UUID], 
        feature_name: str, 
        has_feature: bool
    ) -> Competitor:
        """
        Update a competitor's feature inventory.
        
        Args:
            competitor_id: ID of the competitor
            feature_name: Name of the feature
            has_feature: Whether the competitor has this feature
            
        Returns:
            Updated competitor
        """
        competitor = self.get_competitor(competitor_id)
        if not competitor:
            raise ValueError(f"Competitor with ID {competitor_id} not found")
        
        # Update feature_comparison dictionary
        competitor.feature_comparison[feature_name] = has_feature
        competitor.update()
        
        # Save competitor
        self._store_competitor(competitor)
        
        return competitor
    
    def update_feature_implementation(
        self,
        feature_id: Union[str, UUID],
        competitor_id: Union[str, UUID],
        implementation: Optional[str] = None,
        rating: Optional[float] = None
    ) -> CompetitiveFeature:
        """
        Update a competitive feature's implementation details for a competitor.
        
        Args:
            feature_id: ID of the competitive feature
            competitor_id: ID of the competitor
            implementation: Description of the competitor's implementation
            rating: Rating of the implementation (0-10)
            
        Returns:
            Updated competitive feature
        """
        feature = self.get_competitive_feature(feature_id)
        if not feature:
            raise ValueError(f"Competitive feature with ID {feature_id} not found")
        
        competitor = self.get_competitor(competitor_id)
        if not competitor:
            raise ValueError(f"Competitor with ID {competitor_id} not found")
        
        # Update implementation and rating
        if implementation is not None:
            feature.competitor_implementations[competitor_id] = implementation
        
        if rating is not None:
            feature.competitor_ratings[competitor_id] = rating
        
        feature.update()
        
        # Save feature
        self._store_competitive_feature(feature)
        
        return feature
    
    def compare_features(
        self, 
        competitor_ids: Optional[List[str]] = None,
        feature_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Compare features across competitors.
        
        Args:
            competitor_ids: List of competitor IDs to compare (if None, use all)
            feature_ids: List of feature IDs to compare (if None, use all)
            
        Returns:
            Dictionary with comparison results
        """
        # Get all competitors if competitor_ids not provided
        if competitor_ids is None:
            all_competitors = self.get_all_competitors()
            competitor_ids = [str(c.id) for c in all_competitors]
        
        # Get all features if feature_ids not provided
        if feature_ids is None:
            all_features = self.get_all_competitive_features()
            feature_ids = [str(f.id) for f in all_features]
        
        # Get competitors by IDs
        competitors = []
        for cid in competitor_ids:
            competitor = self.get_competitor(cid)
            if competitor:
                competitors.append(competitor)
        
        # Get features by IDs
        features = []
        for fid in feature_ids:
            feature = self.get_competitive_feature(fid)
            if feature:
                features.append(feature)
        
        if not competitors or not features:
            return {"features": [], "competitors": [], "comparison": []}
        
        # Build comparison matrix
        comparison = []
        
        for feature in features:
            feature_row = {
                "feature_id": str(feature.id),
                "name": feature.name,
                "category": feature.category,
                "importance": feature.importance,
                "our_implementation": feature.our_implementation,
                "our_rating": feature.our_rating,
                "competitor_ratings": {}
            }
            
            for competitor in competitors:
                cid = str(competitor.id)
                feature_row["competitor_ratings"][cid] = feature.competitor_ratings.get(cid)
            
            comparison.append(feature_row)
        
        # Group features by category
        categories = defaultdict(list)
        for row in comparison:
            categories[row["category"]].append(row)
        
        category_comparison = []
        for category, items in categories.items():
            category_row = {
                "category": category,
                "features": items,
                "our_average_rating": np.mean([
                    item["our_rating"] for item in items if item["our_rating"] is not None
                ]) if any(item["our_rating"] is not None for item in items) else None,
                "competitor_average_ratings": {}
            }
            
            # Calculate average rating for each competitor
            for competitor in competitors:
                cid = str(competitor.id)
                ratings = [
                    item["competitor_ratings"].get(cid) 
                    for item in items 
                    if item["competitor_ratings"].get(cid) is not None
                ]
                
                if ratings:
                    category_row["competitor_average_ratings"][cid] = np.mean(ratings)
                else:
                    category_row["competitor_average_ratings"][cid] = None
            
            category_comparison.append(category_row)
        
        return {
            "features": [
                {"id": str(f.id), "name": f.name, "category": f.category}
                for f in features
            ],
            "competitors": [
                {"id": str(c.id), "name": c.name}
                for c in competitors
            ],
            "comparison": comparison,
            "category_comparison": category_comparison
        }
    
    def identify_gaps(self) -> List[Dict]:
        """
        Identify gaps in the market based on competitive feature analysis.
        
        Returns:
            List of potential market gaps
        """
        features = self.get_all_competitive_features()
        competitors = self.get_all_competitors()
        
        if not features or not competitors:
            return []
        
        # Look for features where:
        # 1. We don't have the feature (our_implementation is None)
        # 2. Few competitors have the feature
        # 3. The feature has high importance
        
        potential_gaps = []
        
        for feature in features:
            # Skip if we have this feature
            if feature.our_implementation:
                continue
            
            # Count competitors with this feature
            implementations = 0
            for cid in feature.competitor_implementations:
                if cid in [str(c.id) for c in competitors]:
                    implementations += 1
            
            # Calculate percentage of competitors with this feature
            competitor_percentage = implementations / len(competitors) if competitors else 0
            
            # Calculate opportunity score
            # Higher when feature is important and few competitors have it
            opportunity_score = feature.importance * (1 - competitor_percentage) * 10
            
            if opportunity_score >= 5:  # Threshold for potential gaps
                potential_gaps.append({
                    "feature_id": str(feature.id),
                    "feature_name": feature.name,
                    "category": feature.category,
                    "importance": feature.importance,
                    "competitor_coverage": competitor_percentage * 100,
                    "opportunity_score": opportunity_score,
                    "competitors_with_feature": [
                        cid for cid in feature.competitor_implementations
                        if cid in [str(c.id) for c in competitors]
                    ]
                })
        
        # Sort by opportunity score (descending)
        potential_gaps.sort(key=lambda x: x["opportunity_score"], reverse=True)
        
        return potential_gaps
    
    def create_market_gap_from_analysis(self, feature_id: str) -> MarketGap:
        """
        Create a market gap entry from a competitive feature analysis.
        
        Args:
            feature_id: ID of the feature to base the gap on
            
        Returns:
            Created market gap
        """
        feature = self.get_competitive_feature(feature_id)
        if not feature:
            raise ValueError(f"Competitive feature with ID {feature_id} not found")
        
        # Calculate opportunity score
        competitors = self.get_all_competitors()
        if not competitors:
            opportunity_score = feature.importance * 10
        else:
            # Count competitors with this feature
            implementations = 0
            competing_solutions = []
            
            for cid in feature.competitor_implementations:
                if cid in [str(c.id) for c in competitors]:
                    implementations += 1
                    competing_solutions.append(cid)
            
            # Calculate percentage of competitors with this feature
            competitor_percentage = implementations / len(competitors)
            
            # Calculate opportunity score
            # Make sure there's some minimum opportunity score even when all competitors have the feature
            competitor_factor = max(0.1, 1 - competitor_percentage)
            opportunity_score = feature.importance * competitor_factor * 10
        
        # Create market gap
        gap = MarketGap(
            name=f"Gap in {feature.name}",
            description=f"Market opportunity in {feature.category} category for {feature.name}",
            opportunity_score=opportunity_score,
            competing_solutions=competing_solutions
        )
        
        # Save gap
        self._store_market_gap(gap)
        
        return gap
    
    def generate_competitive_matrix(
        self,
        dimensions: List[str] = ["price", "features"],
        competitor_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a competitive positioning matrix.
        
        Args:
            dimensions: List of dimensions to plot (2 dimensions)
            competitor_ids: List of competitor IDs to include (if None, use all)
            
        Returns:
            Dictionary with matrix data
        """
        if len(dimensions) != 2:
            raise ValueError("Exactly 2 dimensions must be provided")
        
        # Get all competitors if competitor_ids not provided
        if competitor_ids is None:
            all_competitors = self.get_all_competitors()
            competitor_ids = [str(c.id) for c in all_competitors]
        
        # Get competitors by IDs
        competitors = []
        for cid in competitor_ids:
            competitor = self.get_competitor(cid)
            if competitor:
                competitors.append(competitor)
        
        if not competitors:
            return {"dimensions": dimensions, "positions": []}
        
        # Calculate position for each competitor on each dimension
        positions = []
        
        for competitor in competitors:
            position = {
                "competitor_id": str(competitor.id),
                "name": competitor.name,
                "coordinates": {}
            }
            
            # Calculate position on each dimension
            for dimension in dimensions:
                if dimension == "price":
                    # Use average price point if available
                    if competitor.price_points:
                        position["coordinates"][dimension] = np.mean(list(competitor.price_points.values()))
                    else:
                        position["coordinates"][dimension] = 5.0  # Default mid-range
                
                elif dimension == "features":
                    # Count features
                    feature_count = sum(1 for v in competitor.feature_comparison.values() if v)
                    # Normalize to 0-10 scale
                    max_features = max(1, max(
                        sum(1 for v in c.feature_comparison.values() if v)
                        for c in competitors
                    ))
                    position["coordinates"][dimension] = (feature_count / max_features) * 10
                
                elif dimension == "market_share":
                    position["coordinates"][dimension] = competitor.market_share or 5.0
                
                else:
                    # Default to mid-point for unknown dimensions
                    position["coordinates"][dimension] = 5.0
            
            positions.append(position)
        
        # Normalize coordinates to 0-10 scale for each dimension
        for dimension in dimensions:
            values = [p["coordinates"][dimension] for p in positions]
            if values and max(values) != min(values):
                for position in positions:
                    normalized = (position["coordinates"][dimension] - min(values)) / (max(values) - min(values)) * 10
                    position["coordinates"][dimension] = normalized
        
        return {
            "dimensions": dimensions,
            "positions": positions
        }
    
    def track_competitive_timeline(
        self,
        feature_category: Optional[str] = None
    ) -> Dict:
        """
        Track competitive feature releases over time.
        
        Args:
            feature_category: Category to filter by (if None, show all)
            
        Returns:
            Dictionary with timeline data
        """
        features = self.get_all_competitive_features()
        competitors = self.get_all_competitors()
        
        if not features or not competitors:
            return {"timeline": []}
        
        # Filter features by category if provided
        if feature_category:
            features = [f for f in features if f.category == feature_category]
        
        # Create a timeline of feature implementations
        # Note: In a real implementation, we would track when competitors
        # added features. Here we're using creation timestamp as a proxy.
        
        timeline_items = []
        
        for feature in features:
            for competitor_id, implementation in feature.competitor_implementations.items():
                competitor = self.get_competitor(competitor_id)
                if competitor:
                    timeline_items.append({
                        "date": feature.created_at,
                        "competitor_id": competitor_id,
                        "competitor_name": competitor.name,
                        "feature_id": str(feature.id),
                        "feature_name": feature.name,
                        "category": feature.category,
                        "implementation": implementation
                    })
        
        # Sort by date
        timeline_items.sort(key=lambda x: x["date"])
        
        return {"timeline": timeline_items}
    
    def generate_feature_parity_report(
        self,
        competitor_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a feature parity report comparing our product to competitors.
        
        Args:
            competitor_ids: List of competitor IDs to include (if None, use all)
            
        Returns:
            Dictionary with parity report
        """
        # Get all competitors if competitor_ids not provided
        if competitor_ids is None:
            all_competitors = self.get_all_competitors()
            competitor_ids = [str(c.id) for c in all_competitors]
        
        # Get competitors by IDs
        competitors = []
        for cid in competitor_ids:
            competitor = self.get_competitor(cid)
            if competitor:
                competitors.append(competitor)
        
        if not competitors:
            return {"parity_summary": {}, "feature_details": []}
        
        features = self.get_all_competitive_features()
        
        # Create feature comparison
        feature_details = []
        for feature in features:
            feature_item = {
                "feature_id": str(feature.id),
                "name": feature.name,
                "category": feature.category,
                "importance": feature.importance,
                "we_have_it": feature.our_implementation is not None,
                "our_rating": feature.our_rating,
                "competitors_with_feature": 0,
                "competitors_without_feature": 0,
                "competitor_details": {}
            }
            
            for competitor in competitors:
                cid = str(competitor.id)
                has_feature = cid in feature.competitor_implementations
                feature_item["competitor_details"][cid] = {
                    "has_feature": has_feature,
                    "rating": feature.competitor_ratings.get(cid)
                }
                
                if has_feature:
                    feature_item["competitors_with_feature"] += 1
                else:
                    feature_item["competitors_without_feature"] += 1
            
            feature_details.append(feature_item)
        
        # Calculate parity statistics
        total_features = len(features)
        features_we_have = sum(1 for f in feature_details if f["we_have_it"])
        features_we_lack = total_features - features_we_have
        
        # Calculate parity by competitor
        competitor_parity = {}
        for competitor in competitors:
            cid = str(competitor.id)
            features_they_have = sum(1 for f in feature_details if f["competitor_details"].get(cid, {}).get("has_feature", False))
            
            features_both_have = sum(1 for f in feature_details 
                                    if f["we_have_it"] and f["competitor_details"].get(cid, {}).get("has_feature", False))
            
            features_only_we_have = sum(1 for f in feature_details 
                                      if f["we_have_it"] and not f["competitor_details"].get(cid, {}).get("has_feature", False))
            
            features_only_they_have = sum(1 for f in feature_details 
                                        if not f["we_have_it"] and f["competitor_details"].get(cid, {}).get("has_feature", False))
            
            parity_percentage = (features_both_have / total_features * 100) if total_features > 0 else 0
            
            competitor_parity[cid] = {
                "competitor_name": competitor.name,
                "features_they_have": features_they_have,
                "features_both_have": features_both_have,
                "features_only_we_have": features_only_we_have,
                "features_only_they_have": features_only_they_have,
                "parity_percentage": parity_percentage
            }
        
        # Calculate parity by category
        category_parity = {}
        categories = set(f.category for f in features)
        
        for category in categories:
            category_features = [f for f in feature_details if f["category"] == category]
            total_in_category = len(category_features)
            
            we_have_in_category = sum(1 for f in category_features if f["we_have_it"])
            we_lack_in_category = total_in_category - we_have_in_category
            
            category_parity[category] = {
                "total_features": total_in_category,
                "features_we_have": we_have_in_category,
                "features_we_lack": we_lack_in_category,
                "coverage_percentage": (we_have_in_category / total_in_category * 100) if total_in_category > 0 else 0
            }
        
        return {
            "parity_summary": {
                "total_features": total_features,
                "features_we_have": features_we_have,
                "features_we_lack": features_we_lack,
                "coverage_percentage": (features_we_have / total_features * 100) if total_features > 0 else 0,
                "competitor_parity": competitor_parity,
                "category_parity": category_parity
            },
            "feature_details": feature_details
        }