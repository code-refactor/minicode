"""
VectorDB: Vector-Optimized In-Memory Database for ML Applications.

A specialized in-memory database optimized for machine learning feature
storage and retrieval with vector operations, feature versioning,
batch prediction support, transformations, and A/B testing.
"""

from vectordb.core import Vector
from vectordb.indexing import VectorIndex
from vectordb.feature_store import FeatureStore
from vectordb.batch import BatchProcessor
from vectordb.transform import TransformationPipeline
from vectordb.experiment import ABTester

__all__ = [
    "Vector",
    "VectorIndex",
    "FeatureStore",
    "BatchProcessor",
    "TransformationPipeline",
    "ABTester",
]