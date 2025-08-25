"""
Distance metrics for vector comparisons.

This module provides various distance and similarity measures
for comparing vectors, optimized for machine learning applications.
"""

import math
from typing import Callable, Union, List, Tuple
from vectordb.core.vector import Vector


def euclidean_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the Euclidean (L2) distance between two vectors.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The Euclidean distance between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1.values, v2.values)))


def squared_euclidean_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the squared Euclidean distance between two vectors.
    
    This is faster than euclidean_distance when only comparing distances
    (avoids the square root operation).
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The squared Euclidean distance between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    return sum((a - b) ** 2 for a, b in zip(v1.values, v2.values))


def manhattan_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the Manhattan (L1) distance between two vectors.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The Manhattan distance between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    return sum(abs(a - b) for a, b in zip(v1.values, v2.values))


def cosine_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the cosine distance between two vectors.
    
    The cosine distance is 1 minus the cosine similarity, resulting in a value
    between 0 (identical direction) and 2 (opposite direction).
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The cosine distance between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions or if either has zero magnitude
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    dot_product = v1.dot(v2)
    mag1 = v1.magnitude()
    mag2 = v2.magnitude()
    
    if math.isclose(mag1, 0) or math.isclose(mag2, 0):
        raise ValueError("Cannot calculate cosine distance for zero magnitude vectors")
    
    cosine_similarity = dot_product / (mag1 * mag2)
    
    # Ensure the value is in the valid range [-1, 1] due to potential floating point errors
    cosine_similarity = max(min(cosine_similarity, 1.0), -1.0)
    
    # Convert similarity to distance (0 is identical, 2 is opposite)
    return 1.0 - cosine_similarity


def cosine_similarity(v1: Vector, v2: Vector) -> float:
    """
    Calculate the cosine similarity between two vectors.
    
    The cosine similarity measures the cosine of the angle between two vectors,
    resulting in a value between -1 (opposite) and 1 (identical direction),
    with 0 indicating orthogonality.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The cosine similarity between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions or if either has zero magnitude
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate similarity between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    dot_product = v1.dot(v2)
    mag1 = v1.magnitude()
    mag2 = v2.magnitude()
    
    if math.isclose(mag1, 0) or math.isclose(mag2, 0):
        raise ValueError("Cannot calculate cosine similarity for zero magnitude vectors")
    
    similarity = dot_product / (mag1 * mag2)
    
    # Ensure the value is in the valid range [-1, 1] due to potential floating point errors
    return max(min(similarity, 1.0), -1.0)


def angular_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the angular distance between two vectors in radians.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The angular distance between the vectors in radians [0, π]
        
    Raises:
        ValueError: If the vectors have different dimensions or if either has zero magnitude
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    similarity = cosine_similarity(v1, v2)
    return math.acos(similarity)


def chebyshev_distance(v1: Vector, v2: Vector) -> float:
    """
    Calculate the Chebyshev (L∞) distance between two vectors.
    
    The Chebyshev distance is the maximum absolute difference between 
    any components of the vectors.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        The Chebyshev distance between the vectors
        
    Raises:
        ValueError: If the vectors have different dimensions
    """
    if v1.dimension != v2.dimension:
        raise ValueError(f"Cannot calculate distance between vectors with different dimensions: {v1.dimension} and {v2.dimension}")
    
    return max(abs(a - b) for a, b in zip(v1.values, v2.values))


# Mapping of distance metric names to functions
DISTANCE_METRICS = {
    "euclidean": euclidean_distance,
    "squared_euclidean": squared_euclidean_distance,
    "manhattan": manhattan_distance,
    "cosine": cosine_distance,
    "angular": angular_distance,
    "chebyshev": chebyshev_distance,
}


def get_distance_function(metric: str) -> Callable[[Vector, Vector], float]:
    """
    Get the distance function by name.
    
    Args:
        metric: Name of the distance metric
        
    Returns:
        The corresponding distance function
        
    Raises:
        ValueError: If the metric name is not recognized
    """
    if metric.lower() not in DISTANCE_METRICS:
        valid_metrics = ", ".join(DISTANCE_METRICS.keys())
        raise ValueError(f"Unknown distance metric: {metric}. Valid options are: {valid_metrics}")
    
    return DISTANCE_METRICS[metric.lower()]