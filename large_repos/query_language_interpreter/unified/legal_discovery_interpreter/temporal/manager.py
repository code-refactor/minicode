"""Temporal management for legal discovery."""

import json
import re
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import logging
from dateutil import parser as date_parser

from .models import (
    TimeUnit,
    TimePeriod,
    TimeframeType,
    LegalTimeframe,
    TimeframeCatalog,
    DateNormalizationFormat
)


class TemporalManager:
    """Manager for temporal filtering and legal timeframes.
    
    This manager provides functionality for handling legal timeframes,
    normalizing dates, and filtering documents by date.
    """
    
    def __init__(self, logger=None):
        """Initialize the temporal manager.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.timeframe_catalog = TimeframeCatalog()
        
        # Common date formats for normalization
        self.date_formats = [
            DateNormalizationFormat(
                name="ISO",
                regex_pattern=r'\d{4}-\d{2}-\d{2}',
                strptime_format="%Y-%m-%d",
                description="ISO date format (YYYY-MM-DD)"
            ),
            DateNormalizationFormat(
                name="US",
                regex_pattern=r'\d{1,2}/\d{1,2}/\d{4}',
                strptime_format="%m/%d/%Y",
                description="US date format (MM/DD/YYYY)"
            ),
            DateNormalizationFormat(
                name="EU",
                regex_pattern=r'\d{1,2}/\d{1,2}/\d{4}',
                strptime_format="%d/%m/%Y",
                description="European date format (DD/MM/YYYY)"
            ),
            DateNormalizationFormat(
                name="Long",
                regex_pattern=r'[A-Za-z]+ \d{1,2}, \d{4}',
                strptime_format="%B %d, %Y",
                description="Long date format (Month DD, YYYY)"
            )
        ]
        
        # Map of common legal timeframes
        self._initialize_common_timeframes()
    
    def _initialize_common_timeframes(self) -> None:
        """Initialize common legal timeframes."""
        # Statutes of limitations
        sol_timeframes = [
            LegalTimeframe(
                timeframe_id="sol_contract_written_federal",
                name="Written Contract SOL (Federal)",
                description="Statute of limitations for written contracts under federal law",
                timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
                period=TimePeriod(amount=6, unit=TimeUnit.YEARS),
                jurisdiction="Federal",
                legal_reference="28 U.S.C. § 2415"
            ),
            LegalTimeframe(
                timeframe_id="sol_contract_written_ny",
                name="Written Contract SOL (NY)",
                description="Statute of limitations for written contracts under New York law",
                timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
                period=TimePeriod(amount=6, unit=TimeUnit.YEARS),
                jurisdiction="NY",
                legal_reference="N.Y. C.P.L.R. § 213"
            ),
            LegalTimeframe(
                timeframe_id="sol_contract_written_ca",
                name="Written Contract SOL (CA)",
                description="Statute of limitations for written contracts under California law",
                timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
                period=TimePeriod(amount=4, unit=TimeUnit.YEARS),
                jurisdiction="CA",
                legal_reference="Cal. Civ. Proc. Code § 337"
            ),
            LegalTimeframe(
                timeframe_id="sol_securities_federal",
                name="Securities Fraud SOL (Federal)",
                description="Statute of limitations for securities fraud under federal law",
                timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
                period=TimePeriod(amount=5, unit=TimeUnit.YEARS),
                jurisdiction="Federal",
                legal_reference="28 U.S.C. § 1658(b)"
            )
        ]
        
        # Regulatory deadlines
        regulatory_timeframes = [
            LegalTimeframe(
                timeframe_id="sec_form_10k",
                name="SEC Form 10-K Filing Deadline",
                description="Annual report filing deadline for large accelerated filers",
                timeframe_type=TimeframeType.REGULATORY_DEADLINE,
                period=TimePeriod(amount=60, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="17 CFR § 240.15d-1"
            ),
            LegalTimeframe(
                timeframe_id="sec_form_10q",
                name="SEC Form 10-Q Filing Deadline",
                description="Quarterly report filing deadline for large accelerated filers",
                timeframe_type=TimeframeType.REGULATORY_DEADLINE,
                period=TimePeriod(amount=40, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="17 CFR § 240.15d-13"
            ),
            LegalTimeframe(
                timeframe_id="hart_scott_rodino",
                name="Hart-Scott-Rodino Waiting Period",
                description="Waiting period for mergers and acquisitions under Hart-Scott-Rodino",
                timeframe_type=TimeframeType.REGULATORY_DEADLINE,
                period=TimePeriod(amount=30, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="15 U.S.C. § 18a"
            )
        ]
        
        # Litigation timeframes
        litigation_timeframes = [
            LegalTimeframe(
                timeframe_id="frcp_responsive_pleading",
                name="FRCP Responsive Pleading Deadline",
                description="Deadline to respond to a complaint under Federal Rules of Civil Procedure",
                timeframe_type=TimeframeType.DISCOVERY_PERIOD,
                period=TimePeriod(amount=21, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="Fed. R. Civ. P. 12(a)(1)(A)"
            ),
            LegalTimeframe(
                timeframe_id="eeoc_charge_filing",
                name="EEOC Charge Filing Deadline",
                description="Deadline to file a charge with the EEOC for employment discrimination",
                timeframe_type=TimeframeType.REGULATORY_DEADLINE,
                period=TimePeriod(amount=300, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="42 U.S.C. § 2000e-5(e)(1)"
            ),
            LegalTimeframe(
                timeframe_id="ipo_quiet_period",
                name="IPO Quiet Period",
                description="Quiet period following an initial public offering",
                timeframe_type=TimeframeType.CORPORATE_EVENT,
                period=TimePeriod(amount=40, unit=TimeUnit.DAYS),
                jurisdiction="Federal",
                legal_reference="Securities Act of 1933"
            )
        ]
        
        # Add all timeframes to the catalog
        for timeframe in sol_timeframes + regulatory_timeframes + litigation_timeframes:
            self.timeframe_catalog.add_timeframe(timeframe)
    
    def load_timeframes_from_file(self, file_path: str) -> int:
        """Load timeframes from a JSON file.
        
        Args:
            file_path: Path to the timeframes file
            
        Returns:
            Number of timeframes loaded
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                timeframes_data = json.load(f)
            
            count = 0
            for timeframe_data in timeframes_data:
                try:
                    # Convert period to TimePeriod if present
                    if 'period' in timeframe_data:
                        period_data = timeframe_data['period']
                        if isinstance(period_data, dict):
                            timeframe_data['period'] = TimePeriod(
                                amount=period_data['amount'],
                                unit=period_data['unit']
                            )
                    
                    timeframe = LegalTimeframe(**timeframe_data)
                    self.timeframe_catalog.add_timeframe(timeframe)
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to load timeframe: {e}")
            
            self.logger.info(f"Loaded {count} timeframes from {file_path}")
            return count
        except Exception as e:
            self.logger.error(f"Failed to load timeframes from {file_path}: {e}")
            return 0
    
    def load_timeframes_from_directory(self, directory_path: str) -> int:
        """Load timeframes from all JSON files in a directory.
        
        Args:
            directory_path: Path to the directory containing timeframe files
            
        Returns:
            Number of timeframes loaded
        """
        total_count = 0
        
        try:
            for filename in os.listdir(directory_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(directory_path, filename)
                    count = self.load_timeframes_from_file(file_path)
                    total_count += count
        except Exception as e:
            self.logger.error(f"Failed to load timeframes from directory {directory_path}: {e}")
        
        return total_count
    
    def normalize_date(self, date_string: str) -> Optional[datetime]:
        """Normalize a date string to a datetime object.
        
        Args:
            date_string: Date string to normalize
            
        Returns:
            Normalized datetime, or None if parsing failed
        """
        if not date_string:
            return None
        
        try:
            # Try to parse with dateutil parser first (handles many formats)
            return date_parser.parse(date_string)
        except Exception:
            # If dateutil parser fails, try our own formats
            for date_format in self.date_formats:
                if re.match(date_format.regex_pattern, date_string):
                    try:
                        return datetime.strptime(date_string, date_format.strptime_format)
                    except ValueError:
                        continue
            
            # If all formats fail, log a warning and return None
            self.logger.warning(f"Failed to normalize date string: {date_string}")
            return None
    
    def normalize_dates_in_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize dates in a document.
        
        Args:
            document: Document to normalize dates in
            
        Returns:
            Document with normalized dates
        """
        if 'metadata' in document:
            metadata = document['metadata']
            
            # Normalize common date fields
            for date_field in ('date_created', 'date_modified', 'date'):
                if date_field in metadata and isinstance(metadata[date_field], str):
                    normalized_date = self.normalize_date(metadata[date_field])
                    if normalized_date:
                        metadata[date_field] = normalized_date
        
        return document
    
    def get_timeframe(self, timeframe_id: str) -> Optional[LegalTimeframe]:
        """Get a timeframe from the catalog.
        
        Args:
            timeframe_id: ID of the timeframe to get
            
        Returns:
            The timeframe, or None if not found
        """
        return self.timeframe_catalog.get_timeframe(timeframe_id)
    
    def resolve_timeframe(self, timeframe_type: str, jurisdiction: Optional[str] = None,
                        reference_date: Optional[Union[datetime, date]] = None) -> Dict[str, datetime]:
        """Resolve a timeframe to actual dates.
        
        Args:
            timeframe_type: Type of timeframe to resolve
            jurisdiction: Jurisdiction for the timeframe
            reference_date: Reference date for relative timeframes
            
        Returns:
            Dictionary with resolved dates
        """
        if not reference_date:
            reference_date = datetime.now()
        
        try:
            # Try to get timeframe type enum value
            tf_type = TimeframeType(timeframe_type)
        except ValueError:
            # If not a valid enum value, use the string as is
            tf_type = timeframe_type
        
        # Get matching timeframes
        matching_timeframes = []
        
        if isinstance(tf_type, TimeframeType):
            matching_timeframes = self.timeframe_catalog.get_timeframes_by_type(tf_type)
        
        # Filter by jurisdiction if specified
        if jurisdiction and matching_timeframes:
            matching_timeframes = [
                tf for tf in matching_timeframes
                if tf.jurisdiction and tf.jurisdiction.lower() == jurisdiction.lower()
            ]
        
        # If no matching timeframes, try to look up by ID
        if not matching_timeframes:
            timeframe = self.timeframe_catalog.get_timeframe(str(timeframe_type))
            if timeframe:
                matching_timeframes = [timeframe]
        
        # If still no matching timeframes, log a warning and return a default
        if not matching_timeframes:
            self.logger.warning(f"No timeframe found for type {timeframe_type} and jurisdiction {jurisdiction}")
            return {'start': reference_date, 'end': reference_date}
        
        # Use the first matching timeframe
        timeframe = matching_timeframes[0]
        
        # Calculate dates
        dates = timeframe.calculate_dates(reference_date)
        
        return dates
    
    def create_custom_timeframe(self, name: str, period: Dict[str, Any], description: Optional[str] = None,
                             jurisdiction: Optional[str] = None, legal_reference: Optional[str] = None) -> LegalTimeframe:
        """Create a custom timeframe.
        
        Args:
            name: Name of the timeframe
            period: Period specification (e.g., {'amount': 30, 'unit': 'days'})
            description: Description of the timeframe
            jurisdiction: Jurisdiction for the timeframe
            legal_reference: Legal reference for the timeframe
            
        Returns:
            Created timeframe
        """
        timeframe_id = f"custom_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Convert period to TimePeriod
        time_period = TimePeriod(
            amount=period['amount'],
            unit=period['unit']
        )
        
        timeframe = LegalTimeframe(
            timeframe_id=timeframe_id,
            name=name,
            description=description,
            timeframe_type=TimeframeType.CUSTOM,
            period=time_period,
            jurisdiction=jurisdiction,
            legal_reference=legal_reference
        )
        
        # Add to catalog
        self.timeframe_catalog.add_timeframe(timeframe)
        
        return timeframe
    
    def filter_documents_by_date(self, documents: Dict[str, Any], date_field: str,
                              start_date: Union[datetime, date, str], end_date: Union[datetime, date, str]) -> List[str]:
        """Filter documents by date range.
        
        Args:
            documents: Dictionary of documents to filter
            date_field: Field in the documents to filter by
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            List of matching document IDs
        """
        matching_docs = []
        
        # Normalize dates if they are strings
        if isinstance(start_date, str):
            start_date = self.normalize_date(start_date)
            if not start_date:
                return matching_docs
        
        if isinstance(end_date, str):
            end_date = self.normalize_date(end_date)
            if not end_date:
                return matching_docs
        
        # Convert date objects to datetime objects
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        
        if isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())
        
        for doc_id, document in documents.items():
            # Get the date value from the document
            date_value = None
            
            # Check in metadata
            if 'metadata' in document and date_field in document['metadata']:
                date_value = document['metadata'][date_field]
            # Check directly in document
            elif date_field in document:
                date_value = document[date_field]
            
            # Skip if no date value
            if not date_value:
                continue
            
            # Normalize if string
            if isinstance(date_value, str):
                date_value = self.normalize_date(date_value)
                if not date_value:
                    continue
            
            # Convert date to datetime
            if isinstance(date_value, date) and not isinstance(date_value, datetime):
                date_value = datetime.combine(date_value, datetime.min.time())
            
            # Compare with range
            if start_date <= date_value <= end_date:
                matching_docs.append(doc_id)
        
        return matching_docs
    
    def filter_documents_by_timeframe(self, documents: Dict[str, Any], date_field: str,
                                   timeframe_type: str, jurisdiction: Optional[str] = None,
                                   reference_date: Optional[Union[datetime, date]] = None) -> List[str]:
        """Filter documents by a legal timeframe.
        
        Args:
            documents: Dictionary of documents to filter
            date_field: Field in the documents to filter by
            timeframe_type: Type of timeframe to use
            jurisdiction: Jurisdiction for the timeframe
            reference_date: Reference date for the timeframe
            
        Returns:
            List of matching document IDs
        """
        # Resolve the timeframe to dates
        dates = self.resolve_timeframe(timeframe_type, jurisdiction, reference_date)
        
        # Filter by the resolved dates
        return self.filter_documents_by_date(documents, date_field, dates['start'], dates['end'])
    
    def create_timeline(self, documents: Dict[str, Any], date_field: str) -> List[Dict[str, Any]]:
        """Create a timeline of documents.
        
        Args:
            documents: Dictionary of documents to create timeline for
            date_field: Field in the documents to use for timeline
            
        Returns:
            List of timeline entries
        """
        timeline_entries = []
        
        for doc_id, document in documents.items():
            # Get the date value from the document
            date_value = None
            
            # Check in metadata
            if 'metadata' in document and date_field in document['metadata']:
                date_value = document['metadata'][date_field]
            # Check directly in document
            elif date_field in document:
                date_value = document[date_field]
            
            # Skip if no date value
            if not date_value:
                continue
            
            # Normalize if string
            if isinstance(date_value, str):
                date_value = self.normalize_date(date_value)
                if not date_value:
                    continue
            
            # Create timeline entry
            entry = {
                'document_id': doc_id,
                'date': date_value,
                'metadata': document.get('metadata', {})
            }
            
            timeline_entries.append(entry)
        
        # Sort by date
        timeline_entries.sort(key=lambda e: e['date'])
        
        return timeline_entries