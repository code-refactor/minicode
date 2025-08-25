"""
Scoring and normalization utilities for financial analysis.

This module provides functions for scoring financial metrics,
normalizing values, and creating composite scores for analysis.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import math

# Type aliases
Numeric = Union[int, float, Decimal]


class ScoreDirection(Enum):
    """Direction for scoring - higher or lower values are better."""
    HIGHER_IS_BETTER = "higher_better"
    LOWER_IS_BETTER = "lower_better"


class NormalizationMethod(Enum):
    """Methods for normalizing values."""
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"
    PERCENTILE = "percentile"
    SIGMOID = "sigmoid"
    LINEAR_SCALE = "linear_scale"


@dataclass
class ScoreConfig:
    """Configuration for scoring a metric."""
    name: str
    direction: ScoreDirection
    weight: Decimal = Decimal('1.0')
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    target_value: Optional[Decimal] = None
    normalization: NormalizationMethod = NormalizationMethod.MIN_MAX


@dataclass
class ScoreResult:
    """Result of a scoring calculation."""
    metric_name: str
    raw_value: Decimal
    normalized_value: Decimal
    weighted_score: Decimal
    percentile_rank: Optional[Decimal] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def to_decimal(value: Numeric) -> Decimal:
    """Convert numeric value to Decimal for precise calculations."""
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {value} to Decimal: {e}")


def normalize_min_max(
    values: List[Numeric],
    target_min: Decimal = Decimal('0'),
    target_max: Decimal = Decimal('1')
) -> List[Decimal]:
    """
    Normalize values using min-max scaling.
    
    Args:
        values: List of values to normalize
        target_min: Target minimum value
        target_max: Target maximum value
        
    Returns:
        List of normalized values
        
    Raises:
        ValueError: If all values are the same
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    min_val = min(decimals)
    max_val = max(decimals)
    
    if min_val == max_val:
        # All values are the same - return middle of target range
        middle = (target_min + target_max) / 2
        return [middle for _ in decimals]
    
    range_val = max_val - min_val
    target_range = target_max - target_min
    
    normalized = []
    for value in decimals:
        # Scale to 0-1 first
        scaled = (value - min_val) / range_val
        # Then scale to target range
        result = target_min + scaled * target_range
        normalized.append(result.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return normalized


def normalize_z_score(values: List[Numeric]) -> List[Decimal]:
    """
    Normalize values using z-score standardization.
    
    Args:
        values: List of values to normalize
        
    Returns:
        List of z-scores
        
    Raises:
        ValueError: If standard deviation is zero
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    
    # Calculate mean
    mean_val = sum(decimals) / len(decimals)
    
    # Calculate standard deviation
    variance = sum((v - mean_val) ** 2 for v in decimals) / len(decimals)
    std_dev = Decimal(str(math.sqrt(float(variance))))
    
    if std_dev == 0:
        # All values are the same - return zeros
        return [Decimal('0') for _ in decimals]
    
    # Calculate z-scores
    z_scores = []
    for value in decimals:
        z_score = (value - mean_val) / std_dev
        z_scores.append(z_score.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return z_scores


def normalize_percentile(values: List[Numeric]) -> List[Decimal]:
    """
    Normalize values to percentile ranks (0-1).
    
    Args:
        values: List of values to normalize
        
    Returns:
        List of percentile ranks
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    sorted_values = sorted(decimals)
    n = len(sorted_values)
    
    percentiles = []
    for value in decimals:
        # Count values less than current value
        rank = sum(1 for v in sorted_values if v < value)
        # Add 0.5 for ties (average rank)
        rank += sum(0.5 for v in sorted_values if v == value)
        
        percentile = Decimal(str(rank)) / Decimal(str(n))
        percentiles.append(percentile.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return percentiles


def normalize_sigmoid(
    values: List[Numeric],
    center: Optional[Numeric] = None,
    scale: Numeric = 1.0
) -> List[Decimal]:
    """
    Normalize values using sigmoid function.
    
    Args:
        values: List of values to normalize
        center: Center point for sigmoid (defaults to median)
        scale: Scale parameter for sigmoid
        
    Returns:
        List of sigmoid-normalized values (0-1)
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    scale_decimal = to_decimal(scale)
    
    if center is None:
        # Use median as center
        sorted_values = sorted(decimals)
        n = len(sorted_values)
        if n % 2 == 0:
            center_decimal = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            center_decimal = sorted_values[n // 2]
    else:
        center_decimal = to_decimal(center)
    
    normalized = []
    for value in decimals:
        # Sigmoid: 1 / (1 + exp(-(x - center) / scale))
        exponent = -(value - center_decimal) / scale_decimal
        sigmoid_value = Decimal('1') / (Decimal('1') + Decimal(str(math.exp(float(exponent)))))
        normalized.append(sigmoid_value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return normalized


def score_metric(
    values: List[Numeric],
    config: ScoreConfig
) -> List[ScoreResult]:
    """
    Score a metric according to configuration.
    
    Args:
        values: List of raw metric values
        config: Scoring configuration
        
    Returns:
        List of score results
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    
    # Normalize values
    if config.normalization == NormalizationMethod.MIN_MAX:
        if config.min_value is not None and config.max_value is not None:
            # Use specified bounds
            normalized = []
            range_val = config.max_value - config.min_value
            if range_val == 0:
                normalized = [Decimal('0.5') for _ in decimals]
            else:
                for value in decimals:
                    # Clamp to bounds
                    clamped = max(config.min_value, min(config.max_value, value))
                    norm_val = (clamped - config.min_value) / range_val
                    normalized.append(norm_val)
        else:
            normalized = normalize_min_max(decimals)
    
    elif config.normalization == NormalizationMethod.Z_SCORE:
        z_scores = normalize_z_score(decimals)
        # Convert z-scores to 0-1 range using sigmoid
        normalized = [Decimal('1') / (Decimal('1') + Decimal(str(math.exp(-float(z))))) for z in z_scores]
    
    elif config.normalization == NormalizationMethod.PERCENTILE:
        normalized = normalize_percentile(decimals)
    
    elif config.normalization == NormalizationMethod.SIGMOID:
        center = config.target_value if config.target_value is not None else None
        normalized = normalize_sigmoid(decimals, center)
    
    else:
        # Default to min-max
        normalized = normalize_min_max(decimals)
    
    # Reverse if lower is better
    if config.direction == ScoreDirection.LOWER_IS_BETTER:
        normalized = [Decimal('1') - n for n in normalized]
    
    # Calculate percentile ranks
    percentiles = normalize_percentile(decimals)
    if config.direction == ScoreDirection.LOWER_IS_BETTER:
        percentiles = [Decimal('1') - p for p in percentiles]
    
    # Create results
    results = []
    for i, (raw_val, norm_val, percentile) in enumerate(zip(decimals, normalized, percentiles)):
        weighted_score = norm_val * config.weight
        
        result = ScoreResult(
            metric_name=config.name,
            raw_value=raw_val,
            normalized_value=norm_val.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            weighted_score=weighted_score.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
            percentile_rank=percentile,
            metadata={
                "direction": config.direction.value,
                "weight": float(config.weight),
                "normalization": config.normalization.value
            }
        )
        results.append(result)
    
    return results


def calculate_composite_score(
    score_results: List[List[ScoreResult]],
    aggregation_method: str = "weighted_average"
) -> List[Decimal]:
    """
    Calculate composite scores from multiple metrics.
    
    Args:
        score_results: List of score results for each metric
        aggregation_method: Method to aggregate scores ("weighted_average", "geometric_mean")
        
    Returns:
        List of composite scores
        
    Raises:
        ValueError: If score result lists have different lengths
    """
    if not score_results:
        return []
    
    # Check that all metric results have the same length
    first_length = len(score_results[0])
    if not all(len(metric_results) == first_length for metric_results in score_results):
        raise ValueError("All metric result lists must have the same length")
    
    composite_scores = []
    
    for i in range(first_length):
        # Get all scores for this item
        item_scores = []
        total_weight = Decimal('0')
        
        for metric_results in score_results:
            score_result = metric_results[i]
            item_scores.append(score_result.weighted_score)
            total_weight += score_result.weighted_score / score_result.normalized_value if score_result.normalized_value != 0 else Decimal('0')
        
        if aggregation_method == "weighted_average":
            if total_weight > 0:
                composite = sum(item_scores) / total_weight * len(item_scores)
            else:
                composite = Decimal('0')
        
        elif aggregation_method == "geometric_mean":
            if all(score > 0 for score in item_scores):
                # Geometric mean of the scores
                product = Decimal('1')
                for score in item_scores:
                    product *= score
                composite = product ** (Decimal('1') / len(item_scores))
            else:
                composite = Decimal('0')  # Any zero score makes geometric mean zero
        
        else:
            # Default to simple average
            composite = sum(item_scores) / len(item_scores)
        
        composite_scores.append(composite.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    
    return composite_scores


def rank_values(
    values: List[Numeric],
    descending: bool = True
) -> List[Tuple[int, Decimal, int]]:
    """
    Rank values and return rankings.
    
    Args:
        values: List of values to rank
        descending: If True, higher values get better (lower) ranks
        
    Returns:
        List of tuples (original_index, value, rank)
    """
    if not values:
        return []
    
    decimals = [to_decimal(v) for v in values]
    
    # Create list of (index, value) pairs
    indexed_values = list(enumerate(decimals))
    
    # Sort by value
    sorted_pairs = sorted(indexed_values, key=lambda x: x[1], reverse=descending)
    
    # Assign ranks (handling ties)
    rankings = []
    current_rank = 1
    
    for i, (original_index, value) in enumerate(sorted_pairs):
        # Check for ties
        if i > 0 and sorted_pairs[i-1][1] == value:
            # Same rank as previous
            rank = rankings[-1][2]
        else:
            rank = current_rank
        
        rankings.append((original_index, value, rank))
        current_rank = i + 2  # Next unique rank
    
    # Sort back to original order
    rankings.sort(key=lambda x: x[0])
    
    return rankings


def create_score_card(
    metric_scores: Dict[str, List[ScoreResult]],
    item_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Create a comprehensive score card for multiple items and metrics.
    
    Args:
        metric_scores: Dictionary mapping metric names to score results
        item_names: Optional names for items being scored
        
    Returns:
        List of score cards, one per item
    """
    if not metric_scores:
        return []
    
    # Get the number of items
    first_metric_results = next(iter(metric_scores.values()))
    num_items = len(first_metric_results)
    
    # Validate all metrics have same number of items
    for metric_name, results in metric_scores.items():
        if len(results) != num_items:
            raise ValueError(f"Metric {metric_name} has {len(results)} results, expected {num_items}")
    
    # Calculate composite scores
    all_score_results = list(metric_scores.values())
    composite_scores = calculate_composite_score(all_score_results)
    
    # Rank items by composite score
    composite_rankings = rank_values(composite_scores, descending=True)
    
    # Create score cards
    score_cards = []
    
    for i in range(num_items):
        item_name = item_names[i] if item_names and i < len(item_names) else f"Item {i+1}"
        
        # Get composite score and rank
        composite_score = composite_scores[i]
        composite_rank = composite_rankings[i][2]
        
        # Get individual metric scores
        metric_details = {}
        for metric_name, results in metric_scores.items():
            result = results[i]
            metric_details[metric_name] = {
                "raw_value": float(result.raw_value),
                "normalized_score": float(result.normalized_value),
                "weighted_score": float(result.weighted_score),
                "percentile_rank": float(result.percentile_rank) if result.percentile_rank else None,
                "metadata": result.metadata
            }
        
        score_card = {
            "item_name": item_name,
            "composite_score": float(composite_score),
            "composite_rank": composite_rank,
            "metric_scores": metric_details,
            "strengths": [],
            "weaknesses": []
        }
        
        # Identify strengths and weaknesses
        for metric_name, details in metric_details.items():
            percentile = details["percentile_rank"]
            if percentile is not None:
                if percentile >= 0.75:  # Top quartile
                    score_card["strengths"].append({
                        "metric": metric_name,
                        "percentile": percentile,
                        "score": details["normalized_score"]
                    })
                elif percentile <= 0.25:  # Bottom quartile
                    score_card["weaknesses"].append({
                        "metric": metric_name,
                        "percentile": percentile,
                        "score": details["normalized_score"]
                    })
        
        score_cards.append(score_card)
    
    return score_cards


def calculate_financial_health_score(
    liquidity_ratio: Numeric,
    debt_to_income: Numeric,
    savings_rate: Numeric,
    emergency_fund_months: Numeric,
    investment_diversity_score: Numeric
) -> Dict[str, Any]:
    """
    Calculate a comprehensive financial health score.
    
    Args:
        liquidity_ratio: Current assets / current liabilities
        debt_to_income: Total debt / gross income
        savings_rate: Savings / income
        emergency_fund_months: Months of expenses in emergency fund
        investment_diversity_score: Portfolio diversification score (0-1)
        
    Returns:
        Financial health score and breakdown
    """
    # Define scoring configurations
    configs = [
        ScoreConfig("liquidity_ratio", ScoreDirection.HIGHER_IS_BETTER, Decimal('0.2'), 
                   min_value=Decimal('0'), max_value=Decimal('3'), target_value=Decimal('1.5')),
        ScoreConfig("debt_to_income", ScoreDirection.LOWER_IS_BETTER, Decimal('0.25'),
                   min_value=Decimal('0'), max_value=Decimal('0.6'), target_value=Decimal('0.2')),
        ScoreConfig("savings_rate", ScoreDirection.HIGHER_IS_BETTER, Decimal('0.2'),
                   min_value=Decimal('0'), max_value=Decimal('0.5'), target_value=Decimal('0.2')),
        ScoreConfig("emergency_fund", ScoreDirection.HIGHER_IS_BETTER, Decimal('0.2'),
                   min_value=Decimal('0'), max_value=Decimal('12'), target_value=Decimal('6')),
        ScoreConfig("investment_diversity", ScoreDirection.HIGHER_IS_BETTER, Decimal('0.15'),
                   min_value=Decimal('0'), max_value=Decimal('1'), target_value=Decimal('0.8'))
    ]
    
    # Input values
    values = [
        [liquidity_ratio],
        [debt_to_income],
        [savings_rate],
        [emergency_fund_months],
        [investment_diversity_score]
    ]
    
    # Score each metric
    metric_scores = {}
    all_results = []
    
    for config, metric_values in zip(configs, values):
        results = score_metric(metric_values, config)
        metric_scores[config.name] = results
        all_results.append(results)
    
    # Calculate composite score
    composite_scores = calculate_composite_score(all_results)
    final_score = composite_scores[0] if composite_scores else Decimal('0')
    
    # Create score card
    score_cards = create_score_card(metric_scores, ["Financial Health"])
    score_card = score_cards[0] if score_cards else {}
    
    # Add interpretation
    score_float = float(final_score)
    if score_float >= 0.8:
        health_level = "Excellent"
        recommendation = "Your financial health is excellent. Continue your current practices."
    elif score_float >= 0.6:
        health_level = "Good"
        recommendation = "Your financial health is good. Consider improving weaker areas."
    elif score_float >= 0.4:
        health_level = "Fair"
        recommendation = "Your financial health needs improvement. Focus on key weaknesses."
    else:
        health_level = "Poor"
        recommendation = "Your financial health needs significant improvement. Seek financial advice."
    
    return {
        "overall_score": score_float,
        "health_level": health_level,
        "recommendation": recommendation,
        "score_card": score_card,
        "breakdown": {
            "liquidity": float(metric_scores["liquidity_ratio"][0].normalized_value),
            "debt_management": float(metric_scores["debt_to_income"][0].normalized_value),
            "savings_discipline": float(metric_scores["savings_rate"][0].normalized_value),
            "emergency_preparedness": float(metric_scores["emergency_fund"][0].normalized_value),
            "investment_strategy": float(metric_scores["investment_diversity"][0].normalized_value)
        }
    }