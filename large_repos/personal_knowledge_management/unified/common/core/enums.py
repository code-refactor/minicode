"""Common enumerations used across the unified library."""

from enum import Enum


class Priority(str, Enum):
    """Priority levels for tasks, features, and other entities."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    def __lt__(self, other):
        """Compare priorities for sorting."""
        if not isinstance(other, Priority):
            return NotImplemented
        priority_order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        return priority_order.index(self) < priority_order.index(other)


class EntityStatus(str, Enum):
    """Generic status for entities."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ExportFormat(str, Enum):
    """Supported export formats."""
    
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    BIBTEX = "bibtex"
    RIS = "ris"
    XML = "xml"


class Sentiment(str, Enum):
    """Sentiment classification."""
    
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class Visibility(str, Enum):
    """Visibility levels for entities."""
    
    PUBLIC = "public"
    PRIVATE = "private"
    TEAM = "team"
    RESTRICTED = "restricted"


class ImportanceLevel(str, Enum):
    """Importance levels for various entities."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class ConfidenceLevel(str, Enum):
    """Confidence levels for assessments and evaluations."""
    
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    RELATED = "related"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    DUPLICATES = "duplicates"
    SUPERSEDES = "supersedes"
    IMPLEMENTS = "implements"
    VALIDATES = "validates"