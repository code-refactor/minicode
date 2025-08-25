"""Shared data models for the unified backup system."""

from .file_info import FileInfo
from .snapshot import Snapshot, SnapshotDiff
from .version import Version

__all__ = ['FileInfo', 'Snapshot', 'SnapshotDiff', 'Version']