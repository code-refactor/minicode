"""Storage system for the unified backup system."""

from .backend import LocalStorageBackend
from .content_store import ContentAddressedStorage
from .deduplicator import Deduplicator

__all__ = ['LocalStorageBackend', 'ContentAddressedStorage', 'Deduplicator']