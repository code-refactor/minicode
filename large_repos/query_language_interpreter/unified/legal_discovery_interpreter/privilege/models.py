"""Models for privilege detection in legal discovery."""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class PrivilegeType(str, Enum):
    """Types of legal privilege."""
    
    ATTORNEY_CLIENT = "attorney_client"
    WORK_PRODUCT = "work_product"
    ATTORNEY_WORK_PRODUCT = "attorney_work_product"
    COMMON_INTEREST = "common_interest"
    JOINT_DEFENSE = "joint_defense"
    SETTLEMENT_NEGOTIATION = "settlement_negotiation"
    SELF_CRITICAL_ANALYSIS = "self_critical_analysis"
    TRADE_SECRET = "trade_secret"
    EXECUTIVE = "executive"
    OTHER = "other"


class PrivilegeIndicatorCategory(str, Enum):
    """Categories of privilege indicators."""
    
    HEADER = "header"
    FOOTER = "footer"
    SUBJECT_LINE = "subject_line"
    DOCUMENT_TYPE = "document_type"
    PARTICIPANT = "participant"
    CONTENT = "content"
    METADATA = "metadata"
    FORMATTING = "formatting"
    CONTEXTUAL = "contextual"


class PrivilegeStatus(str, Enum):
    """Status of privilege for a document."""
    
    PRIVILEGED = "privileged"
    POTENTIALLY_PRIVILEGED = "potentially_privileged"
    NOT_PRIVILEGED = "not_privileged"
    UNKNOWN = "unknown"


class PrivilegeIndicator(BaseModel):
    """Model for an indicator of privilege."""
    
    indicator_id: str = Field(..., description="Unique identifier for the indicator")
    name: str = Field(..., description="Name of the indicator")
    description: Optional[str] = Field(None, description="Description of the indicator")
    indicator_type: PrivilegeType = Field(..., description="Type of privilege the indicator suggests")
    category: PrivilegeIndicatorCategory = Field(..., description="Category of the indicator")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Weight of the indicator")
    pattern: Optional[str] = Field(None, description="Regex pattern to match the indicator")
    case_sensitive: bool = Field(default=False, description="Whether the pattern is case sensitive")
    exact_match: bool = Field(default=False, description="Whether the pattern requires an exact match")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class Attorney(BaseModel):
    """Model for an attorney in privilege detection."""
    
    attorney_id: str = Field(..., description="Unique identifier for the attorney")
    name: str = Field(..., description="Name of the attorney")
    email: Optional[str] = Field(None, description="Email of the attorney")
    organization: Optional[str] = Field(None, description="Organization of the attorney")
    bar_number: Optional[str] = Field(None, description="Bar number of the attorney")
    role: Optional[str] = Field(None, description="Role of the attorney")
    practice_areas: Optional[List[str]] = Field(None, description="Practice areas of the attorney")
    is_internal: bool = Field(default=False, description="Whether the attorney is internal to the organization")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class PrivilegeDetectionResult(BaseModel):
    """Result of privilege detection on a document."""
    
    document_id: str = Field(..., description="ID of the document")
    status: PrivilegeStatus = Field(..., description="Privilege status of the document")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the privilege determination")
    privilege_types: List[PrivilegeType] = Field(default_factory=list, 
                                              description="Types of privilege detected")
    detected_indicators: Dict[str, float] = Field(default_factory=dict, 
                                               description="Detected indicators and their scores")
    attorneys_involved: List[str] = Field(default_factory=list, 
                                       description="Attorneys involved in the document")
    notes: Optional[str] = Field(None, description="Notes about the privilege determination")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class PrivilegeLog(BaseModel):
    """Log of privilege determinations."""
    
    entries: Dict[str, PrivilegeDetectionResult] = Field(default_factory=dict, 
                                                      description="Privilege detection entries")
    
    def add_entry(self, result: PrivilegeDetectionResult) -> None:
        """Add an entry to the privilege log.
        
        Args:
            result: Privilege detection result to add
        """
        self.entries[result.document_id] = result
    
    def get_entry(self, document_id: str) -> Optional[PrivilegeDetectionResult]:
        """Get an entry from the privilege log.
        
        Args:
            document_id: ID of the document to get entry for
            
        Returns:
            The privilege detection result, or None if not found
        """
        return self.entries.get(document_id)
    
    def get_privileged_documents(self) -> List[str]:
        """Get IDs of privileged documents.
        
        Returns:
            List of privileged document IDs
        """
        return [
            doc_id for doc_id, result in self.entries.items()
            if result.status == PrivilegeStatus.PRIVILEGED
        ]
    
    def get_potentially_privileged_documents(self) -> List[str]:
        """Get IDs of potentially privileged documents.
        
        Returns:
            List of potentially privileged document IDs
        """
        return [
            doc_id for doc_id, result in self.entries.items()
            if result.status == PrivilegeStatus.POTENTIALLY_PRIVILEGED
        ]
    
    def count_entries(self) -> Dict[str, int]:
        """Count entries by privilege status.
        
        Returns:
            Dictionary mapping status to count
        """
        counts = {status.value: 0 for status in PrivilegeStatus}
        
        for result in self.entries.values():
            counts[result.status] += 1
        
        counts['total'] = len(self.entries)
        
        return counts