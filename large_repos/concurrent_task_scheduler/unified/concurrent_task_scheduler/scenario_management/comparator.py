"""Scenario comparison system for scientific research optimization."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from concurrent_task_scheduler.models import (
    ComparisonResult,
    Result,
    Scenario,
    ScenarioEvaluationResult,
    ScientificMetric,
)
from concurrent_task_scheduler.scenario_management.evaluator import (
    EvaluationCriteria,
    ScenarioEvaluator,
)

logger = logging.getLogger(__name__)


class ComparisonMethod(str, Enum):
    """Methods for comparing scenarios."""

    DIRECT = "direct"  # Direct comparison of metrics
    RELATIVE = "relative"  # Relative comparison (percent difference)
    WEIGHTED = "weighted"  # Weighted comparison based on importance
    RANK_BASED = "rank_based"  # Comparison based on ranking of scenarios
    ENSEMBLE = "ensemble"  # Ensemble of comparison methods


class ScenarioComparator:
    """Comparator for assessing relative merits of scenarios."""

    def __init__(self, evaluator: Optional[ScenarioEvaluator] = None):
        self.evaluator = evaluator or ScenarioEvaluator()
        self.comparison_history: Dict[str, List[ComparisonResult]] = {}
        self.comparison_weights: Dict[str, float] = {
            "accuracy": 0.20,
            "convergence": 0.15,
            "efficiency": 0.10,
            "novelty": 0.20,
            "significance": 0.20,
            "robustness": 0.15,
        }
    
    def compare_scenarios(
        self,
        scenario_a: Scenario,
        scenario_b: Scenario,
        method: ComparisonMethod = ComparisonMethod.WEIGHTED,
        comparison_weights: Optional[Dict[str, float]] = None,
    ) -> Result[ComparisonResult]:
        """Compare two scenarios to determine which has more promise."""
        # Use provided weights or defaults
        weights = comparison_weights or self.comparison_weights
        
        # Normalize weights to sum to 1
        weight_sum = sum(weights.values())
        if weight_sum != 1.0:
            weights = {k: v / weight_sum for k, v in weights.items()}
        
        # First, get the latest evaluations for each scenario
        eval_a = self.evaluator.get_latest_evaluation(scenario_a.id)
        eval_b = self.evaluator.get_latest_evaluation(scenario_b.id)
        
        # If evaluations don't exist, create them
        if not eval_a:
            eval_result_a = self.evaluator.evaluate_scenario(scenario_a)
            if not eval_result_a.success:
                return Result.err(f"Failed to evaluate scenario A: {eval_result_a.error}")
            eval_a = eval_result_a.value
        
        if not eval_b:
            eval_result_b = self.evaluator.evaluate_scenario(scenario_b)
            if not eval_result_b.success:
                return Result.err(f"Failed to evaluate scenario B: {eval_result_b.error}")
            eval_b = eval_result_b.value
        
        # Compare based on method
        if method == ComparisonMethod.DIRECT:
            comparison = self._direct_comparison(eval_a, eval_b, weights)
        elif method == ComparisonMethod.RELATIVE:
            comparison = self._relative_comparison(eval_a, eval_b, weights)
        elif method == ComparisonMethod.RANK_BASED:
            comparison = self._rank_based_comparison(eval_a, eval_b, weights)
        else:  # Default to WEIGHTED
            comparison = self._weighted_comparison(eval_a, eval_b, weights)
        
        # Calculate overall difference and confidence
        overall_difference = comparison.get("overall", 0.0)
        
        # Confidence based on evaluation confidences
        confidence = (eval_a.confidence + eval_b.confidence) / 2
        
        # Generate recommendation
        if overall_difference > 0.15:
            recommendation = f"Scenario {scenario_a.id} shows significantly more promise and should be prioritized."
        elif overall_difference > 0.05:
            recommendation = f"Scenario {scenario_a.id} shows somewhat more promise and should receive more resources."
        elif overall_difference > -0.05:
            recommendation = f"Both scenarios show similar promise and should be continued in parallel."
        elif overall_difference > -0.15:
            recommendation = f"Scenario {scenario_b.id} shows somewhat more promise and should receive more resources."
        else:
            recommendation = f"Scenario {scenario_b.id} shows significantly more promise and should be prioritized."
        
        # Create comparison result
        result = ComparisonResult(
            scenario_id_a=scenario_a.id,
            scenario_id_b=scenario_b.id,
            metrics_comparison={"direct": comparison},
            overall_difference=overall_difference,
            confidence=confidence,
            recommendation=recommendation,
        )
        
        # Store in history
        comparison_key = f"{scenario_a.id}_{scenario_b.id}"
        if comparison_key not in self.comparison_history:
            self.comparison_history[comparison_key] = []
        
        self.comparison_history[comparison_key].append(result)
        
        return Result.ok(result)
    
    def _direct_comparison(
        self,
        eval_a: ScenarioEvaluationResult,
        eval_b: ScenarioEvaluationResult,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """Perform direct comparison of metrics."""
        comparison = {}
        
        # Compare common metrics
        common_metrics = set(eval_a.metric_scores.keys()).intersection(set(eval_b.metric_scores.keys()))
        
        for metric in common_metrics:
            score_a = eval_a.metric_scores[metric]
            score_b = eval_b.metric_scores[metric]
            comparison[metric] = score_a - score_b  # Positive means A is better
        
        # Overall comparison (weighted)
        overall = 0.0
        total_weight = 0.0
        
        for metric, diff in comparison.items():
            if metric in weights:
                weight = weights[metric]
                overall += diff * weight
                total_weight += weight
        
        if total_weight > 0:
            comparison["overall"] = overall / total_weight
        else:
            comparison["overall"] = 0.0
        
        return comparison
    
    def _relative_comparison(
        self,
        eval_a: ScenarioEvaluationResult,
        eval_b: ScenarioEvaluationResult,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """Perform relative comparison (percent difference)."""
        comparison = {}
        
        # Compare common metrics
        common_metrics = set(eval_a.metric_scores.keys()).intersection(set(eval_b.metric_scores.keys()))
        
        for metric in common_metrics:
            score_a = eval_a.metric_scores[metric]
            score_b = eval_b.metric_scores[metric]
            
            # Calculate relative difference (as percentage)
            if score_b != 0:
                relative_diff = (score_a - score_b) / score_b
            elif score_a != 0:
                relative_diff = 1.0  # A is infinitely better than zero
            else:
                relative_diff = 0.0  # Both zero
            
            # Cap extreme values
            relative_diff = max(-1.0, min(1.0, relative_diff))
            
            comparison[metric] = relative_diff
        
        # Overall comparison (weighted)
        overall = 0.0
        total_weight = 0.0
        
        for metric, diff in comparison.items():
            if metric in weights:
                weight = weights[metric]
                overall += diff * weight
                total_weight += weight
        
        if total_weight > 0:
            comparison["overall"] = overall / total_weight
        else:
            comparison["overall"] = 0.0
        
        return comparison
    
    def _weighted_comparison(
        self,
        eval_a: ScenarioEvaluationResult,
        eval_b: ScenarioEvaluationResult,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """Perform weighted comparison based on importance."""
        comparison = {}
        
        # Calculate weighted scores for each scenario
        weighted_score_a = 0.0
        weighted_score_b = 0.0
        total_weight = 0.0
        
        # Common metrics
        common_metrics = set(eval_a.metric_scores.keys()).intersection(set(eval_b.metric_scores.keys()))
        
        for metric in common_metrics:
            if metric in weights:
                score_a = eval_a.metric_scores[metric]
                score_b = eval_b.metric_scores[metric]
                weight = weights[metric]
                
                weighted_score_a += score_a * weight
                weighted_score_b += score_b * weight
                total_weight += weight
                
                # Store individual metric comparison
                comparison[metric] = score_a - score_b
        
        # Calculate overall difference
        if total_weight > 0:
            # Normalize by total weight
            weighted_score_a /= total_weight
            weighted_score_b /= total_weight
            
            comparison["overall"] = weighted_score_a - weighted_score_b
        else:
            comparison["overall"] = 0.0
        
        return comparison
    
    def _rank_based_comparison(
        self,
        eval_a: ScenarioEvaluationResult,
        eval_b: ScenarioEvaluationResult,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """Perform rank-based comparison."""
        comparison = {}
        
        # Common metrics
        common_metrics = set(eval_a.metric_scores.keys()).intersection(set(eval_b.metric_scores.keys()))
        
        for metric in common_metrics:
            score_a = eval_a.metric_scores[metric]
            score_b = eval_b.metric_scores[metric]
            
            # For rank-based, we just care about which is higher
            if score_a > score_b:
                comparison[metric] = 1.0  # A ranks higher
            elif score_a < score_b:
                comparison[metric] = -1.0  # B ranks higher
            else:
                comparison[metric] = 0.0  # Tied
        
        # Overall comparison (weighted)
        overall = 0.0
        total_weight = 0.0
        
        for metric, diff in comparison.items():
            if metric in weights:
                weight = weights[metric]
                overall += diff * weight
                total_weight += weight
        
        if total_weight > 0:
            comparison["overall"] = overall / total_weight
        else:
            comparison["overall"] = 0.0
        
        return comparison
    
    def get_comparison_history(
        self,
        scenario_id_a: str,
        scenario_id_b: str,
    ) -> List[ComparisonResult]:
        """Get comparison history between two scenarios."""
        key_direct = f"{scenario_id_a}_{scenario_id_b}"
        key_reverse = f"{scenario_id_b}_{scenario_id_a}"
        
        direct_history = self.comparison_history.get(key_direct, [])
        reverse_history = self.comparison_history.get(key_reverse, [])
        
        # For reverse comparisons, invert the difference
        adjusted_reverse = []
        for comparison in reverse_history:
            # Create a copy with inverted difference
            inverted = ComparisonResult(
                scenario_id_a=comparison.scenario_id_b,  # Swap IDs
                scenario_id_b=comparison.scenario_id_a,
                metrics_comparison=comparison.metrics_comparison,  # Keep metrics as is for now
                overall_difference=-comparison.overall_difference,  # Invert
                confidence=comparison.confidence,
                comparison_time=comparison.comparison_time,
                recommendation=f"Inverted: {comparison.recommendation}",
            )
            adjusted_reverse.append(inverted)
        
        # Combine both directions
        all_comparisons = direct_history + adjusted_reverse
        
        # Sort by comparison time
        return sorted(all_comparisons, key=lambda c: c.comparison_time)
    
    def compare_multiple_scenarios(
        self,
        scenarios: List[Scenario],
        method: ComparisonMethod = ComparisonMethod.WEIGHTED,
        comparison_weights: Optional[Dict[str, float]] = None,
    ) -> Result:
        """Compare multiple scenarios and rank them by promise."""
        if len(scenarios) < 2:
            return Result.err("At least two scenarios are required for comparison")
        
        # Use provided weights or defaults
        weights = comparison_weights or self.comparison_weights
        
        # Evaluate all scenarios first
        for scenario in scenarios:
            if not self.evaluator.get_latest_evaluation(scenario.id):
                self.evaluator.evaluate_scenario(scenario)
        
        # Compare all pairs
        comparisons = {}
        
        for i, scenario_a in enumerate(scenarios):
            for j, scenario_b in enumerate(scenarios):
                if i >= j:  # Skip self-comparison and duplicates
                    continue
                
                result = self.compare_scenarios(scenario_a, scenario_b, method, weights)
                if result.success:
                    key = f"{scenario_a.id}_{scenario_b.id}"
                    comparisons[key] = result.value
        
        # Calculate overall scores (PageRank-like approach)
        scores = {scenario.id: 1.0 / len(scenarios) for scenario in scenarios}
        damping = 0.85
        iterations = 5
        
        for _ in range(iterations):
            new_scores = {sid: (1 - damping) / len(scenarios) for sid in scores}
            
            for key, comparison in comparisons.items():
                id_a, id_b = key.split("_")
                diff = comparison.overall_difference
                
                # Normalize difference to [0, 1] range
                norm_diff = (diff + 1) / 2  # -1..1 -> 0..1
                
                # Distribute score
                if norm_diff > 0.5:  # A is better
                    new_scores[id_a] += damping * scores[id_b] * (norm_diff - 0.5) * 2
                else:  # B is better
                    new_scores[id_b] += damping * scores[id_a] * (0.5 - norm_diff) * 2
            
            # Normalize
            total = sum(new_scores.values())
            scores = {sid: score / total for sid, score in new_scores.items()}
        
        # Identify complementary scenarios for the comparison
        complementary_result = self.identify_complementary_scenarios(scenarios)
        complementary_pairs = [] if not complementary_result.success else complementary_result.value
        
        # Create a mock result object that has the needed attributes
        result = Result.ok(scores)
        
        # Add ranked_scenarios and complementary_pairs attributes
        result.ranked_scenarios = scores
        result.value = scores  # Maintain value attribute for backward compatibility
        result.complementary_pairs = complementary_pairs
        result.method = method
        result.comparison_time = datetime.now()
        
        return result
    
    def group_scenarios_by_similarity(
        self,
        scenarios: List[Scenario],
        similarity_threshold: float = 0.2,
    ) -> Result[List[List[str]]]:
        """Group scenarios by their similarity."""
        if len(scenarios) < 2:
            return Result.err("At least two scenarios are required for grouping")
        
        # Calculate similarity matrix
        n = len(scenarios)
        similarity = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                # Calculate similarity based on metrics
                sim_score = self._calculate_similarity(scenarios[i], scenarios[j])
                similarity[i, j] = sim_score
                similarity[j, i] = sim_score
        
        # Group scenarios using a simple clustering approach
        groups = []
        unassigned = set(range(n))
        
        while unassigned:
            # Start a new group with the first unassigned scenario
            current = min(unassigned)
            current_group = [current]
            unassigned.remove(current)
            
            # Find all similar scenarios
            to_check = [current]
            while to_check:
                idx = to_check.pop(0)
                for j in list(unassigned):
                    if similarity[idx, j] >= similarity_threshold:
                        current_group.append(j)
                        to_check.append(j)
                        unassigned.remove(j)
            
            # Add the group
            scenario_ids = [scenarios[i].id for i in current_group]
            groups.append(scenario_ids)
        
        return Result.ok(groups)
    
    def _calculate_similarity(self, scenario_a: Scenario, scenario_b: Scenario) -> float:
        """Calculate similarity between two scenarios."""
        # Check for common tags
        a_tags = set(scenario_a.tags)
        b_tags = set(scenario_b.tags)
        
        if a_tags and b_tags:
            tag_similarity = len(a_tags.intersection(b_tags)) / len(a_tags.union(b_tags))
        else:
            tag_similarity = 0.0
        
        # Check for common objectives
        a_objectives = set(scenario_a.research_objectives)
        b_objectives = set(scenario_b.research_objectives)
        
        if a_objectives and b_objectives:
            objective_similarity = len(a_objectives.intersection(b_objectives)) / len(a_objectives.union(b_objectives))
        else:
            objective_similarity = 0.0
        
        # Check for similar simulations
        # In a real implementation, this would involve deeper analysis
        simulation_similarity = 0.0
        
        # Check for metric similarity
        metric_similarity = 0.0
        common_metrics = set(scenario_a.scientific_metrics.keys()).intersection(set(scenario_b.scientific_metrics.keys()))
        
        if common_metrics:
            metric_diffs = []
            for metric_name in common_metrics:
                a_metric = scenario_a.scientific_metrics[metric_name]
                b_metric = scenario_b.scientific_metrics[metric_name]
                
                # Normalize difference by converting to similarity (1 - diff)
                diff = abs(a_metric.value - b_metric.value)
                metric_diffs.append(1.0 - diff)
            
            if metric_diffs:
                metric_similarity = sum(metric_diffs) / len(metric_diffs)
        
        # Weighted combination
        weights = {
            "tag": 0.3,
            "objective": 0.3,
            "simulation": 0.1,
            "metric": 0.3,
        }
        
        similarity = (
            tag_similarity * weights["tag"] +
            objective_similarity * weights["objective"] +
            simulation_similarity * weights["simulation"] +
            metric_similarity * weights["metric"]
        )
        
        return similarity
    
    def identify_complementary_scenarios(
        self,
        scenarios: List[Scenario],
    ) -> Result[List[Tuple[str, str, float]]]:
        """Identify pairs of scenarios that complement each other."""
        if len(scenarios) < 2:
            return Result.err("At least two scenarios are required")
        
        complementary_pairs = []
        
        for i, scenario_a in enumerate(scenarios):
            for j, scenario_b in enumerate(scenarios):
                if i >= j:  # Skip self-pairs and duplicates
                    continue
                
                complementarity = self._calculate_complementarity(scenario_a, scenario_b)
                
                # Only include highly complementary pairs
                if complementarity > 0.6:
                    complementary_pairs.append((scenario_a.id, scenario_b.id, complementarity))
        
        # Sort by complementarity score (descending)
        complementary_pairs.sort(key=lambda pair: pair[2], reverse=True)
        
        return Result.ok(complementary_pairs)
    
    def _calculate_complementarity(self, scenario_a: Scenario, scenario_b: Scenario) -> float:
        """Calculate how complementary two scenarios are."""
        # Check for different strengths/weaknesses
        # First, get evaluations
        eval_a = self.evaluator.get_latest_evaluation(scenario_a.id)
        eval_b = self.evaluator.get_latest_evaluation(scenario_b.id)
        
        if not eval_a or not eval_b:
            # If evaluations don't exist, estimate from metrics
            return self._estimate_complementarity_from_metrics(scenario_a, scenario_b)
        
        # Calculate complementarity based on evaluations
        common_metrics = set(eval_a.metric_scores.keys()).intersection(set(eval_b.metric_scores.keys()))
        
        if not common_metrics:
            return 0.0
        
        # Check where each scenario excels over the other
        a_strengths = []
        b_strengths = []
        
        for metric in common_metrics:
            score_a = eval_a.metric_scores[metric]
            score_b = eval_b.metric_scores[metric]
            
            if score_a > score_b + 0.2:  # A is significantly better
                a_strengths.append(metric)
            elif score_b > score_a + 0.2:  # B is significantly better
                b_strengths.append(metric)
        
        # Scenarios are complementary if each has different strengths
        if a_strengths and b_strengths:
            # Calculate overlap of strengths (less overlap = more complementary)
            overlap = set(a_strengths).intersection(set(b_strengths))
            strength_complementarity = 1.0 - (len(overlap) / max(len(a_strengths) + len(b_strengths), 1))
            
            # Calculate diversity of approaches
            tag_a = set(scenario_a.tags)
            tag_b = set(scenario_b.tags)
            tag_similarity = len(tag_a.intersection(tag_b)) / max(len(tag_a.union(tag_b)), 1)
            
            # Diversity of approaches is complementary
            approach_complementarity = 1.0 - tag_similarity
            
            # Weighted combination
            complementarity = 0.7 * strength_complementarity + 0.3 * approach_complementarity
            
            return complementarity
        
        return 0.0
    
    def _estimate_complementarity_from_metrics(self, scenario_a: Scenario, scenario_b: Scenario) -> float:
        """Estimate complementarity from scientific metrics."""
        # Find common metric categories
        a_metrics = scenario_a.scientific_metrics
        b_metrics = scenario_b.scientific_metrics
        
        a_categories = set(name.split('_')[0] if '_' in name else name for name in a_metrics.keys())
        b_categories = set(name.split('_')[0] if '_' in name else name for name in b_metrics.keys())
        
        common_categories = a_categories.intersection(b_categories)
        
        if not common_categories:
            return 0.0
        
        # Check for different strengths in common categories
        complementary_categories = 0
        
        for category in common_categories:
            # Find metrics in this category
            a_category_metrics = {name: metric for name, metric in a_metrics.items() 
                                if name.startswith(f"{category}_") or name == category}
            b_category_metrics = {name: metric for name, metric in b_metrics.items() 
                                if name.startswith(f"{category}_") or name == category}
            
            # Calculate average values for this category
            if a_category_metrics and b_category_metrics:
                a_avg = sum(m.value for m in a_category_metrics.values()) / len(a_category_metrics)
                b_avg = sum(m.value for m in b_category_metrics.values()) / len(b_category_metrics)
                
                # Check if there's a significant difference
                if abs(a_avg - b_avg) > 0.2:
                    complementary_categories += 1
        
        if complementary_categories > 0:
            # Calculate complementarity score
            return complementary_categories / len(common_categories)
        
        return 0.0