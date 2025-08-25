"""Scenario evaluation system for scientific promise assessment."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from concurrent_task_scheduler.models import (
    Result,
    Scenario,
    ScenarioEvaluationResult,
    ScientificMetric,
)

logger = logging.getLogger(__name__)


class EvaluationCriteria(str, Enum):
    """Criteria for evaluating scenarios."""

    ACCURACY = "accuracy"  # Accuracy of results
    CONVERGENCE = "convergence"  # Convergence of simulation
    STABILITY = "stability"  # Stability of results
    EFFICIENCY = "efficiency"  # Computational efficiency
    NOVELTY = "novelty"  # Novelty of results
    SIGNIFICANCE = "significance"  # Scientific significance
    ROBUSTNESS = "robustness"  # Robustness to parameter changes
    EXPLAINABILITY = "explainability"  # Ability to explain results
    CONSISTENCY = "consistency"  # Consistency with known results


class EvaluationMethod(str, Enum):
    """Methods for evaluating scenarios."""

    MANUAL = "manual"  # Manual evaluation by experts
    AUTOMATED = "automated"  # Automated evaluation
    HYBRID = "hybrid"  # Combination of manual and automated
    COMPARATIVE = "comparative"  # Comparison with other scenarios
    OBJECTIVE = "objective"  # Evaluation against objective criteria
    ENSEMBLE = "ensemble"  # Ensemble of evaluation methods


class ScenarioEvaluator:
    """Evaluator for assessing scientific promise of scenarios."""

    def __init__(self):
        self.evaluation_history: Dict[str, List[ScenarioEvaluationResult]] = {}
        self.evaluation_methods: Dict[EvaluationCriteria, EvaluationMethod] = {
            EvaluationCriteria.ACCURACY: EvaluationMethod.OBJECTIVE,
            EvaluationCriteria.CONVERGENCE: EvaluationMethod.AUTOMATED,
            EvaluationCriteria.STABILITY: EvaluationMethod.AUTOMATED,
            EvaluationCriteria.EFFICIENCY: EvaluationMethod.OBJECTIVE,
            EvaluationCriteria.NOVELTY: EvaluationMethod.HYBRID,
            EvaluationCriteria.SIGNIFICANCE: EvaluationMethod.MANUAL,
            EvaluationCriteria.ROBUSTNESS: EvaluationMethod.AUTOMATED,
            EvaluationCriteria.EXPLAINABILITY: EvaluationMethod.MANUAL,
            EvaluationCriteria.CONSISTENCY: EvaluationMethod.COMPARATIVE,
        }
        self.criteria_weights: Dict[EvaluationCriteria, float] = {
            EvaluationCriteria.ACCURACY: 0.20,
            EvaluationCriteria.CONVERGENCE: 0.15,
            EvaluationCriteria.STABILITY: 0.10,
            EvaluationCriteria.EFFICIENCY: 0.05,
            EvaluationCriteria.NOVELTY: 0.15,
            EvaluationCriteria.SIGNIFICANCE: 0.20,
            EvaluationCriteria.ROBUSTNESS: 0.10,
            EvaluationCriteria.EXPLAINABILITY: 0.025,
            EvaluationCriteria.CONSISTENCY: 0.025,
        }
        self.evaluation_functions = {
            EvaluationCriteria.ACCURACY: self._evaluate_accuracy,
            EvaluationCriteria.CONVERGENCE: self._evaluate_convergence,
            EvaluationCriteria.STABILITY: self._evaluate_stability,
            EvaluationCriteria.EFFICIENCY: self._evaluate_efficiency,
            EvaluationCriteria.NOVELTY: self._evaluate_novelty,
            EvaluationCriteria.SIGNIFICANCE: self._evaluate_significance,
            EvaluationCriteria.ROBUSTNESS: self._evaluate_robustness,
            EvaluationCriteria.EXPLAINABILITY: self._evaluate_explainability,
            EvaluationCriteria.CONSISTENCY: self._evaluate_consistency,
        }
        self.manual_ratings: Dict[str, Dict[EvaluationCriteria, float]] = {}
    
    def evaluate_scenario(
        self,
        scenario: Scenario,
        evaluation_methods: Optional[Dict[EvaluationCriteria, EvaluationMethod]] = None,
        criteria_weights: Optional[Dict[EvaluationCriteria, float]] = None,
    ) -> Result[ScenarioEvaluationResult]:
        """Evaluate the scientific promise of a scenario."""
        # Use provided methods and weights or defaults
        methods = evaluation_methods or self.evaluation_methods
        weights = criteria_weights or self.criteria_weights
        
        # Normalize weights to sum to 1
        weight_sum = sum(weights.values())
        if weight_sum != 1.0:
            weights = {k: v / weight_sum for k, v in weights.items()}
        
        # Evaluate each criterion
        metric_scores = {}
        reasons = []
        confidence = 0.0
        
        for criterion, method in methods.items():
            if criterion not in self.evaluation_functions:
                continue
            
            # Get the evaluation function
            eval_function = self.evaluation_functions[criterion]
            
            # Evaluate the criterion
            score, reason, method_confidence = eval_function(scenario, method)
            
            # Store results
            criterion_key = criterion.value
            metric_scores[criterion_key] = score
            reasons.append(f"{criterion.value.capitalize()}: {reason}")
            
            # Weighted confidence
            criterion_weight = weights.get(criterion, 0.0)
            confidence += method_confidence * criterion_weight
        
        # Calculate overall score
        overall_score = 0.0
        for criterion, score in metric_scores.items():
            criterion_enum = EvaluationCriteria(criterion)
            weight = weights.get(criterion_enum, 0.0)
            overall_score += score * weight
        
        # Determine recommendation based on score
        if overall_score >= 0.8:
            recommendation = "continue"
            suggested_priority = min(1.0, scenario.priority_score + 0.2)
        elif overall_score >= 0.5:
            recommendation = "continue"
            suggested_priority = scenario.priority_score
        elif overall_score >= 0.3:
            recommendation = "adjust"
            suggested_priority = max(0.0, scenario.priority_score - 0.1)
        else:
            recommendation = "deprioritize"
            suggested_priority = max(0.0, scenario.priority_score - 0.3)
        
        # Create evaluation result
        result = ScenarioEvaluationResult(
            scenario_id=scenario.id,
            evaluation_time=datetime.now(),
            overall_score=overall_score,
            metric_scores=metric_scores,
            confidence=confidence,
            recommendation=recommendation,
            suggested_priority=suggested_priority,
            reasons=reasons,
        )
        
        # Store in history
        if scenario.id not in self.evaluation_history:
            self.evaluation_history[scenario.id] = []
        
        self.evaluation_history[scenario.id].append(result)
        
        return Result.ok(result)
    
    def add_manual_rating(
        self,
        scenario_id: str,
        criterion: EvaluationCriteria,
        rating: float,
    ) -> None:
        """Add a manual rating for a scenario criterion."""
        if scenario_id not in self.manual_ratings:
            self.manual_ratings[scenario_id] = {}
        
        self.manual_ratings[scenario_id][criterion] = max(0.0, min(1.0, rating))
    
    def _evaluate_accuracy(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the accuracy of a scenario."""
        # Check if there's a metric for accuracy
        accuracy_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "accuracy" in name.lower() or "error" in name.lower()
        ]
        
        if accuracy_metrics:
            # Use existing metrics
            scores = []
            for metric in accuracy_metrics:
                if metric.is_higher_better:
                    scores.append(metric.value)
                else:
                    # Invert for error metrics (lower is better)
                    scores.append(1.0 - metric.value)
            
            avg_score = sum(scores) / len(scores)
            confidence = 0.9  # High confidence using actual metrics
            
            if avg_score > 0.8:
                reason = "High accuracy based on explicit metrics."
            elif avg_score > 0.5:
                reason = "Moderate accuracy based on explicit metrics."
            else:
                reason = "Low accuracy based on explicit metrics."
        
        else:
            # Simulate accuracy evaluation
            if "accuracy" in scenario.metadata:
                # Use pre-defined accuracy
                avg_score = float(scenario.metadata["accuracy"])
                confidence = 0.8
            else:
                # Generate mock accuracy score
                # Use progress as a factor - higher progress usually means more reliable evaluation
                progress = scenario.total_progress()
                base_score = 0.5 + (random.random() * 0.5)  # 0.5 to 1.0
                variance = max(0.1, 0.5 - (progress * 0.5))  # More variance when less progress
                avg_score = max(0.0, min(1.0, base_score + (random.random() * variance * 2 - variance)))
                confidence = 0.6 + (progress * 0.3)  # 0.6 to 0.9
            
            if avg_score > 0.8:
                reason = "Results appear to have high accuracy based on preliminary analysis."
            elif avg_score > 0.5:
                reason = "Results show moderate accuracy in preliminary tests."
            else:
                reason = "Initial results suggest concerns with accuracy."
        
        return avg_score, reason, confidence
    
    def _evaluate_convergence(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the convergence of a scenario."""
        convergence_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "convergence" in name.lower() or "residual" in name.lower()
        ]
        
        if convergence_metrics:
            # Use existing metrics
            scores = []
            for metric in convergence_metrics:
                if metric.is_higher_better:
                    scores.append(metric.value)
                else:
                    # Invert for residual metrics (lower is better)
                    scores.append(1.0 - metric.value)
            
            avg_score = sum(scores) / len(scores)
            confidence = 0.9
            
            if avg_score > 0.8:
                reason = "Excellent convergence behavior observed."
            elif avg_score > 0.5:
                reason = "Acceptable convergence rate in simulations."
            else:
                reason = "Poor convergence detected in simulations."
        
        else:
            # Simulate convergence evaluation
            # Generate mock convergence data
            progress = scenario.total_progress()
            
            # Use simulation progress as a factor in convergence
            if progress > 0.8:
                # Almost complete - more likely to have converged
                base_score = 0.7 + (random.random() * 0.3)  # 0.7 to 1.0
                confidence = 0.8
            elif progress > 0.5:
                # Halfway through - moderate convergence
                base_score = 0.5 + (random.random() * 0.4)  # 0.5 to 0.9
                confidence = 0.6
            else:
                # Early stages - less likely to have converged
                base_score = 0.2 + (random.random() * 0.5)  # 0.2 to 0.7
                confidence = 0.4
            
            avg_score = base_score
            
            if avg_score > 0.8:
                reason = "Simulation shows strong convergence patterns."
            elif avg_score > 0.5:
                reason = "Moderate convergence observed, with some oscillation."
            else:
                reason = "Weak convergence or divergence in simulation results."
        
        return avg_score, reason, confidence
    
    def _evaluate_stability(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the stability of a scenario."""
        stability_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "stability" in name.lower() or "variation" in name.lower()
        ]
        
        if stability_metrics:
            # Use existing metrics
            scores = []
            for metric in stability_metrics:
                if metric.is_higher_better:
                    scores.append(metric.value)
                else:
                    # Invert for variation metrics (lower is better)
                    scores.append(1.0 - metric.value)
            
            avg_score = sum(scores) / len(scores)
            confidence = 0.9
            
            if avg_score > 0.8:
                reason = "Results show high stability across runs."
            elif avg_score > 0.5:
                reason = "Moderate stability with some variance in results."
            else:
                reason = "Low stability with significant variance between runs."
        
        else:
            # Simulate stability evaluation
            # For a research scenario, we can tie stability to how consistent progress has been
            progress = scenario.total_progress()
            
            # Generate mock stability score
            if "stability" in scenario.metadata:
                # Use pre-defined stability
                avg_score = float(scenario.metadata["stability"])
                confidence = 0.8
            else:
                base_score = 0.6 + (random.random() * 0.4)  # 0.6 to 1.0
                
                # Adjust based on progress fluctuations (mocking this)
                progress_penalty = random.random() * 0.3  # 0 to 0.3
                avg_score = max(0.0, min(1.0, base_score - progress_penalty))
                confidence = 0.7
            
            if avg_score > 0.8:
                reason = "Results are highly stable with minimal variation across test runs."
            elif avg_score > 0.5:
                reason = "Moderate stability observed with acceptable variation in results."
            else:
                reason = "Significant instability detected, with high variance between runs."
        
        return avg_score, reason, confidence
    
    def _evaluate_efficiency(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the computational efficiency of a scenario."""
        efficiency_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "efficiency" in name.lower() or "performance" in name.lower() or "speed" in name.lower()
        ]
        
        if efficiency_metrics:
            # Use existing metrics
            scores = []
            for metric in efficiency_metrics:
                if metric.is_higher_better:
                    scores.append(metric.value)
                else:
                    # Invert for time metrics (lower is better)
                    scores.append(1.0 - metric.value)
            
            avg_score = sum(scores) / len(scores)
            confidence = 0.9
            
            if avg_score > 0.8:
                reason = "Highly efficient use of computational resources."
            elif avg_score > 0.5:
                reason = "Reasonable computational efficiency for the problem domain."
            else:
                reason = "Poor computational efficiency compared to expectations."
        
        else:
            # Simulate efficiency evaluation
            if "efficiency" in scenario.metadata:
                # Use pre-defined efficiency
                avg_score = float(scenario.metadata["efficiency"])
                confidence = 0.7
            else:
                # Generate mock efficiency score
                # Base efficiency score
                base_score = 0.5 + (random.random() * 0.5)  # 0.5 to 1.0
                
                # Efficiency tends to be inversely related to complexity/accuracy
                # Assume complex scenarios (more simulations) are less efficient
                complexity_factor = len(scenario.simulations) / 10  # Normalize
                complexity_penalty = min(0.4, complexity_factor * 0.1)
                
                avg_score = max(0.0, min(1.0, base_score - complexity_penalty))
                confidence = 0.6
            
            if avg_score > 0.8:
                reason = "Excellent computational efficiency with optimal resource utilization."
            elif avg_score > 0.5:
                reason = "Acceptable computational efficiency for the problem complexity."
            else:
                reason = "Resource-intensive with suboptimal computational efficiency."
        
        return avg_score, reason, confidence
    
    def _evaluate_novelty(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the novelty of a scenario."""
        # Novelty is typically assessed manually, but we can check for manual ratings
        if scenario.id in self.manual_ratings and EvaluationCriteria.NOVELTY in self.manual_ratings[scenario.id]:
            novelty_score = self.manual_ratings[scenario.id][EvaluationCriteria.NOVELTY]
            confidence = 0.9  # High confidence for manual ratings
            
            if novelty_score > 0.8:
                reason = "Highly novel approach with significant potential for new insights."
            elif novelty_score > 0.5:
                reason = "Moderately novel with some unique aspects worth exploring."
            else:
                reason = "Limited novelty compared to existing approaches."
            
            return novelty_score, reason, confidence
        
        # If no manual rating, use tag-based or metadata-based assessment
        novelty_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "novelty" in name.lower() or "original" in name.lower()
        ]
        
        if novelty_metrics:
            # Use existing metrics
            scores = [metric.value for metric in novelty_metrics]
            avg_score = sum(scores) / len(scores)
            confidence = 0.7
            
            if avg_score > 0.8:
                reason = "Highly novel approach based on preliminary analysis."
            elif avg_score > 0.5:
                reason = "Some novel elements worth exploring further."
            else:
                reason = "Limited novelty detected in current approach."
        
        else:
            # Simulate novelty evaluation
            if "novelty" in scenario.metadata:
                avg_score = float(scenario.metadata["novelty"])
                confidence = 0.6
            else:
                # Generate mock novelty score
                # Use the number of unique tags as a proxy for novelty
                tag_factor = len(set(scenario.tags)) / 10  # Normalize
                avg_score = 0.3 + (tag_factor * 0.4) + (random.random() * 0.3)
                confidence = 0.4  # Low confidence for automated novelty assessment
            
            if avg_score > 0.8:
                reason = "Appears to introduce novel concepts and approaches."
            elif avg_score > 0.5:
                reason = "Contains some novel elements among standard approaches."
            else:
                reason = "Primarily uses well-established methods with limited novelty."
        
        return avg_score, reason, confidence
    
    def _evaluate_significance(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the scientific significance of a scenario."""
        # Significance typically requires expert evaluation
        if scenario.id in self.manual_ratings and EvaluationCriteria.SIGNIFICANCE in self.manual_ratings[scenario.id]:
            significance_score = self.manual_ratings[scenario.id][EvaluationCriteria.SIGNIFICANCE]
            confidence = 0.95  # Very high confidence for manual ratings
            
            if significance_score > 0.8:
                reason = "Highly significant work with potential for substantial impact."
            elif significance_score > 0.5:
                reason = "Moderate significance with contributions to the field."
            else:
                reason = "Limited scientific significance relative to current research."
            
            return significance_score, reason, confidence
        
        # If no manual rating, use metrics or estimate
        significance_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "significance" in name.lower() or "impact" in name.lower()
        ]
        
        if significance_metrics:
            # Use existing metrics
            scores = [metric.value for metric in significance_metrics]
            avg_score = sum(scores) / len(scores)
            confidence = 0.7
            
            if avg_score > 0.8:
                reason = "Early results indicate high scientific significance."
            elif avg_score > 0.5:
                reason = "Moderate scientific significance based on preliminary assessment."
            else:
                reason = "Limited scientific significance in current results."
        
        else:
            # Simulate significance evaluation
            if "significance" in scenario.metadata:
                avg_score = float(scenario.metadata["significance"])
                confidence = 0.6
            else:
                # Generate mock significance score
                # Combine novelty and accuracy as components of significance
                base_score = random.random() * 0.6 + 0.3  # 0.3 to 0.9
                confidence = 0.4  # Low confidence for automated significance assessment
                avg_score = base_score
            
            if avg_score > 0.8:
                reason = "Preliminary analysis suggests high scientific significance."
            elif avg_score > 0.5:
                reason = "Potential for moderate scientific contribution, pending more results."
            else:
                reason = "Limited scientific significance apparent at this stage."
        
        return avg_score, reason, confidence
    
    def _evaluate_robustness(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the robustness of a scenario to parameter changes."""
        robustness_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "robustness" in name.lower() or "sensitivity" in name.lower()
        ]
        
        if robustness_metrics:
            # Use existing metrics
            scores = []
            for metric in robustness_metrics:
                if "sensitivity" in metric.name.lower() and not metric.is_higher_better:
                    # Lower sensitivity means higher robustness
                    scores.append(1.0 - metric.value)
                else:
                    scores.append(metric.value)
            
            avg_score = sum(scores) / len(scores)
            confidence = 0.85
            
            if avg_score > 0.8:
                reason = "Results show high robustness to parameter variations."
            elif avg_score > 0.5:
                reason = "Moderate robustness with some sensitivity to key parameters."
            else:
                reason = "Low robustness with high sensitivity to parameter changes."
        
        else:
            # Simulate robustness evaluation
            if "robustness" in scenario.metadata:
                avg_score = float(scenario.metadata["robustness"])
                confidence = 0.7
            else:
                # Generate mock robustness score
                # Use number of simulations as a proxy - more simulations might indicate more parameter testing
                sim_count = len(scenario.simulations)
                sim_factor = min(1.0, sim_count / 5)  # More simulations suggest more testing
                
                base_score = 0.4 + (sim_factor * 0.4) + (random.random() * 0.2)
                avg_score = base_score
                confidence = 0.5 + (sim_factor * 0.3)  # More confidence with more simulations
            
            if avg_score > 0.8:
                reason = "Results remain consistent across parameter variations."
            elif avg_score > 0.5:
                reason = "Results show acceptable stability with some parameter sensitivity."
            else:
                reason = "Results highly sensitive to parameter variations."
        
        return avg_score, reason, confidence
    
    def _evaluate_explainability(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the explainability of a scenario."""
        # Explainability often requires human judgment
        if scenario.id in self.manual_ratings and EvaluationCriteria.EXPLAINABILITY in self.manual_ratings[scenario.id]:
            explainability_score = self.manual_ratings[scenario.id][EvaluationCriteria.EXPLAINABILITY]
            confidence = 0.9
            
            if explainability_score > 0.8:
                reason = "Results are highly interpretable and theoretically grounded."
            elif explainability_score > 0.5:
                reason = "Results can be reasonably interpreted within theoretical framework."
            else:
                reason = "Results are difficult to interpret or explain."
            
            return explainability_score, reason, confidence
        
        # If no manual rating, use metrics or estimate
        explainability_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "explain" in name.lower() or "interpret" in name.lower()
        ]
        
        if explainability_metrics:
            # Use existing metrics
            scores = [metric.value for metric in explainability_metrics]
            avg_score = sum(scores) / len(scores)
            confidence = 0.8
            
            if avg_score > 0.8:
                reason = "Results have clear physical/theoretical interpretation."
            elif avg_score > 0.5:
                reason = "Results are partially explainable within theoretical framework."
            else:
                reason = "Results are difficult to interpret within current theory."
        
        else:
            # Simulate explainability evaluation
            if "explainability" in scenario.metadata:
                avg_score = float(scenario.metadata["explainability"])
                confidence = 0.6
            else:
                # Generate mock explainability score
                # More complex scenarios are often less explainable
                complexity = random.random()
                explainability_base = 0.9 - (complexity * 0.6)  # 0.3 to 0.9
                
                avg_score = explainability_base
                confidence = 0.5  # Low confidence for automated explainability assessment
            
            if avg_score > 0.8:
                reason = "Clear theoretical explanation for observed results."
            elif avg_score > 0.5:
                reason = "Partial theoretical explanation for some results."
            else:
                reason = "Limited ability to explain results within current framework."
        
        return avg_score, reason, confidence
    
    def _evaluate_consistency(
        self,
        scenario: Scenario,
        method: EvaluationMethod,
    ) -> Tuple[float, str, float]:
        """Evaluate the consistency of a scenario with known results."""
        consistency_metrics = [
            metric for name, metric in scenario.scientific_metrics.items()
            if "consistency" in name.lower() or "agreement" in name.lower()
        ]
        
        if consistency_metrics:
            # Use existing metrics
            scores = [metric.value for metric in consistency_metrics]
            avg_score = sum(scores) / len(scores)
            confidence = 0.9
            
            if avg_score > 0.8:
                reason = "High consistency with established results and theory."
            elif avg_score > 0.5:
                reason = "Moderate consistency with some deviations from expected results."
            else:
                reason = "Significant inconsistencies with established results."
        
        else:
            # Simulate consistency evaluation
            if "consistency" in scenario.metadata:
                avg_score = float(scenario.metadata["consistency"])
                confidence = 0.7
            else:
                # Generate mock consistency score
                # More progress generally means more opportunity to validate consistency
                progress = scenario.total_progress()
                
                if progress < 0.3:
                    # Early stage - hard to assess
                    base_score = 0.4 + (random.random() * 0.2)  # 0.4 to 0.6
                    confidence = 0.4
                else:
                    # More progress - better assessment
                    base_score = 0.5 + (random.random() * 0.5)  # 0.5 to 1.0
                    confidence = 0.5 + (progress * 0.3)  # 0.5 to 0.8
                
                avg_score = base_score
            
            if avg_score > 0.8:
                reason = "Results align well with established scientific understanding."
            elif avg_score > 0.5:
                reason = "Results generally consistent with known findings, with some novel variations."
            else:
                reason = "Results show significant deviations from established understanding."
        
        return avg_score, reason, confidence
    
    def get_evaluation_history(
        self,
        scenario_id: str,
    ) -> List[ScenarioEvaluationResult]:
        """Get the evaluation history for a scenario."""
        return self.evaluation_history.get(scenario_id, [])
    
    def get_latest_evaluation(
        self,
        scenario_id: str,
    ) -> Optional[ScenarioEvaluationResult]:
        """Get the latest evaluation for a scenario."""
        history = self.evaluation_history.get(scenario_id, [])
        if not history:
            return None
        
        # Sort by evaluation time, newest first
        sorted_history = sorted(
            history,
            key=lambda eval_result: eval_result.evaluation_time,
            reverse=True
        )
        
        return sorted_history[0]
    
    def compare_evaluations(
        self,
        scenario_id: str,
        evaluation_index1: int,
        evaluation_index2: int,
    ) -> Result[Dict[str, float]]:
        """Compare two evaluations of the same scenario."""
        history = self.evaluation_history.get(scenario_id, [])
        if not history:
            return Result.err(f"No evaluation history for scenario {scenario_id}")
        
        if evaluation_index1 < 0 or evaluation_index1 >= len(history):
            return Result.err(f"Invalid evaluation index: {evaluation_index1}")
        
        if evaluation_index2 < 0 or evaluation_index2 >= len(history):
            return Result.err(f"Invalid evaluation index: {evaluation_index2}")
        
        eval1 = history[evaluation_index1]
        eval2 = history[evaluation_index2]
        
        # Compare each metric
        differences = {}
        
        # Common metrics
        common_metrics = set(eval1.metric_scores.keys()).intersection(set(eval2.metric_scores.keys()))
        
        for metric in common_metrics:
            score1 = eval1.metric_scores[metric]
            score2 = eval2.metric_scores[metric]
            differences[metric] = score2 - score1  # Positive means improvement
        
        # Overall difference
        differences["overall_score"] = eval2.overall_score - eval1.overall_score
        
        return Result.ok(differences)