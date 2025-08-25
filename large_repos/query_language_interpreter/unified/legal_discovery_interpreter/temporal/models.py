"""Models for temporal management in legal discovery."""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
from enum import Enum
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field


class TimeUnit(str, Enum):
    """Units for time periods."""
    
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class TimePeriod(BaseModel):
    """Model for a time period."""
    
    amount: int = Field(..., description="Amount of time")
    unit: TimeUnit = Field(..., description="Unit of time")
    
    def to_timedelta(self) -> timedelta:
        """Convert the time period to a timedelta.
        
        Returns:
            Timedelta representation of the time period
        """
        if self.unit == TimeUnit.DAYS:
            return timedelta(days=self.amount)
        elif self.unit == TimeUnit.WEEKS:
            return timedelta(weeks=self.amount)
        elif self.unit == TimeUnit.MONTHS:
            # Approximate - months don't have a fixed number of days
            return timedelta(days=self.amount * 30)
        elif self.unit == TimeUnit.YEARS:
            # Approximate - years don't have a fixed number of days
            return timedelta(days=self.amount * 365)
        else:
            raise ValueError(f"Unknown time unit: {self.unit}")


class TimeframeType(str, Enum):
    """Types of legal timeframes."""
    
    STATUTE_OF_LIMITATIONS = "statute_of_limitations"
    REGULATORY_DEADLINE = "regulatory_deadline"
    DISCOVERY_PERIOD = "discovery_period"
    LITIGATION_HOLD = "litigation_hold"
    CORPORATE_EVENT = "corporate_event"
    COMPLIANCE_PERIOD = "compliance_period"
    CONTRACTUAL_PERIOD = "contractual_period"
    CUSTOM = "custom"


class LegalTimeframe(BaseModel):
    """Model for a legal timeframe."""
    
    timeframe_id: str = Field(..., description="Unique identifier for the timeframe")
    name: str = Field(..., description="Name of the timeframe")
    description: Optional[str] = Field(None, description="Description of the timeframe")
    timeframe_type: TimeframeType = Field(..., description="Type of timeframe")
    period: Optional[TimePeriod] = Field(None, description="Period of the timeframe")
    start_date: Optional[Union[datetime, date]] = Field(None, description="Start date of the timeframe")
    end_date: Optional[Union[datetime, date]] = Field(None, description="End date of the timeframe")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction of the timeframe")
    legal_reference: Optional[str] = Field(None, description="Legal reference for the timeframe")
    notes: Optional[str] = Field(None, description="Additional notes about the timeframe")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"
    
    def calculate_dates(self, reference_date: Optional[Union[datetime, date]] = None) -> Dict[str, Union[datetime, date]]:
        """Calculate the start and end dates of the timeframe.
        
        Args:
            reference_date: Reference date for calculating relative timeframes
            
        Returns:
            Dictionary with start and end dates
        """
        result = {}
        
        # Use specified dates if available
        if self.start_date:
            result['start'] = self.start_date
        
        if self.end_date:
            result['end'] = self.end_date
        
        # Calculate dates based on period if necessary
        if self.period and reference_date:
            # If no start date is specified, use the reference date
            if 'start' not in result:
                result['start'] = reference_date
            
            # If no end date is specified, calculate it from the start date and period
            if 'end' not in result:
                delta = self.period.to_timedelta()
                result['end'] = result['start'] + delta
        
        return result


class TimeframeCatalog(BaseModel):
    """Catalog of legal timeframes."""
    
    timeframes: Dict[str, LegalTimeframe] = Field(
        default_factory=dict, description="Timeframes in the catalog"
    )
    
    def add_timeframe(self, timeframe: LegalTimeframe) -> None:
        """Add a timeframe to the catalog.
        
        Args:
            timeframe: Timeframe to add
        """
        self.timeframes[timeframe.timeframe_id] = timeframe
    
    def get_timeframe(self, timeframe_id: str) -> Optional[LegalTimeframe]:
        """Get a timeframe from the catalog.
        
        Args:
            timeframe_id: ID of the timeframe to get
            
        Returns:
            The timeframe, or None if not found
        """
        return self.timeframes.get(timeframe_id)
    
    def get_timeframes_by_type(self, timeframe_type: TimeframeType) -> List[LegalTimeframe]:
        """Get timeframes of a specific type.
        
        Args:
            timeframe_type: Type of timeframes to get
            
        Returns:
            List of matching timeframes
        """
        return [
            timeframe for timeframe in self.timeframes.values()
            if timeframe.timeframe_type == timeframe_type
        ]
    
    def get_timeframes_by_jurisdiction(self, jurisdiction: str) -> List[LegalTimeframe]:
        """Get timeframes for a specific jurisdiction.
        
        Args:
            jurisdiction: Jurisdiction to filter by
            
        Returns:
            List of matching timeframes
        """
        return [
            timeframe for timeframe in self.timeframes.values()
            if timeframe.jurisdiction and timeframe.jurisdiction.lower() == jurisdiction.lower()
        ]
    
    def count_timeframes(self) -> int:
        """Count the number of timeframes in the catalog.
        
        Returns:
            Number of timeframes
        """
        return len(self.timeframes)


class DateNormalizationFormat(BaseModel):
    """Format for date normalization."""
    
    name: str = Field(..., description="Name of the format")
    regex_pattern: str = Field(..., description="Regex pattern for matching dates")
    strptime_format: str = Field(..., description="Strptime format for parsing dates")
    description: Optional[str] = Field(None, description="Description of the format")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"