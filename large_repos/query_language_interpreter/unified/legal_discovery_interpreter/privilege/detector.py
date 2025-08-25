"""Privilege detection for legal discovery."""

import re
import json
import os
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import logging
import asyncio

# Common library imports
from common.services.base_services import BaseDetectorService, ServiceConfig
from common.core.base_models import BaseDocument, ExecutionContext
from common.core.exceptions import ServiceError
from common.utils.logging import get_logger

# Legal-specific imports
from ..core.document import Document, DocumentCollection, EmailDocument
from .models import (
    PrivilegeType,
    PrivilegeIndicatorCategory,
    PrivilegeStatus,
    PrivilegeIndicator,
    Attorney,
    PrivilegeDetectionResult,
    PrivilegeLog
)


class PrivilegeDetector(BaseDetectorService):
    """Detector for privileged content in legal discovery.
    
    This detector identifies documents that may contain privileged
    attorney-client communications or work product.
    """
    
    def __init__(self, config: Optional[ServiceConfig] = None, logger=None):
        """Initialize the privilege detector.
        
        Args:
            config: Service configuration
            logger: Logger instance
        """
        # Initialize with default config if none provided
        if config is None:
            config = ServiceConfig(
                service_name="privilege_detector",
                service_type="detector",
                enabled=True,
                config={}
            )
        
        super().__init__(config)
        
        self.logger = logger or get_logger(__name__)
        self.privilege_indicators: Dict[str, PrivilegeIndicator] = {}
        self.attorneys: Dict[str, Attorney] = {}
        self.privilege_log = PrivilegeLog()
        
        # Initialize default indicators (will be called during initialization)
        self._indicators_initialized = False
    
    def _initialize_default_indicators(self) -> None:
        """Initialize default privilege indicators."""
        default_indicators = [
            PrivilegeIndicator(
                indicator_id="header_attorney_client_privilege",
                name="Attorney-Client Privilege Header",
                description="Header indicating attorney-client privilege",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.HEADER,
                weight=0.9,
                pattern=r"(?i)attorney.client\s+privilege",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="header_privileged_confidential",
                name="Privileged and Confidential Header",
                description="Header indicating privileged and confidential content",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.HEADER,
                weight=0.8,
                pattern=r"(?i)privileged\s+and\s+confidential",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="header_work_product",
                name="Work Product Header",
                description="Header indicating attorney work product",
                indicator_type=PrivilegeType.WORK_PRODUCT,
                category=PrivilegeIndicatorCategory.HEADER,
                weight=0.8,
                pattern=r"(?i)attorney\s+work\s+product",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="subject_legal_advice",
                name="Legal Advice Subject",
                description="Subject line indicating request for legal advice",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.SUBJECT_LINE,
                weight=0.7,
                pattern=r"(?i)(legal\s+advice|attorney\s+advice)",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="content_legal_advice",
                name="Legal Advice Content",
                description="Content indicating legal advice",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.CONTENT,
                weight=0.6,
                pattern=r"(?i)(my\s+legal\s+advice|my\s+advice\s+as\s+(?:your|an)\s+attorney|legal\s+recommendation)",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="content_legal_analysis",
                name="Legal Analysis Content",
                description="Content indicating legal analysis",
                indicator_type=PrivilegeType.WORK_PRODUCT,
                category=PrivilegeIndicatorCategory.CONTENT,
                weight=0.6,
                pattern=r"(?i)(legal\s+analysis|analyzed\s+the\s+legal|legal\s+implications)",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="metadata_attorney_client",
                name="Attorney-Client Metadata",
                description="Metadata indicating attorney-client privilege",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.METADATA,
                weight=0.8,
                pattern=r"(?i)attorney.client",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="footer_do_not_forward",
                name="Do Not Forward Footer",
                description="Footer indicating not to forward the communication",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.FOOTER,
                weight=0.5,
                pattern=r"(?i)(do\s+not\s+forward|do\s+not\s+distribute)",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="document_type_memo",
                name="Legal Memorandum",
                description="Document type is a legal memorandum",
                indicator_type=PrivilegeType.ATTORNEY_CLIENT,
                category=PrivilegeIndicatorCategory.DOCUMENT_TYPE,
                weight=0.6,
                pattern=r"(?i)(legal\s+memorandum|legal\s+memo)",
                case_sensitive=False,
                exact_match=False
            ),
            PrivilegeIndicator(
                indicator_id="content_prepared_request_counsel",
                name="Prepared at Request of Counsel",
                description="Content indicating preparation at request of counsel",
                indicator_type=PrivilegeType.WORK_PRODUCT,
                category=PrivilegeIndicatorCategory.CONTENT,
                weight=0.7,
                pattern=r"(?i)(prepared\s+at\s+the\s+request\s+of\s+counsel|prepared\s+for\s+counsel)",
                case_sensitive=False,
                exact_match=False
            )
        ]
        
        for indicator in default_indicators:
            self.add_privilege_indicator(indicator)
    
    def load_indicators_from_file(self, file_path: str) -> int:
        """Load privilege indicators from a JSON file.
        
        Args:
            file_path: Path to the indicators file
            
        Returns:
            Number of indicators loaded
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                indicators_data = json.load(f)
            
            count = 0
            for indicator_data in indicators_data:
                try:
                    indicator = PrivilegeIndicator(**indicator_data)
                    self.add_privilege_indicator(indicator)
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to load indicator: {e}")
            
            self.logger.info(f"Loaded {count} privilege indicators from {file_path}")
            return count
        except Exception as e:
            self.logger.error(f"Failed to load indicators from {file_path}: {e}")
            return 0
    
    def load_attorneys_from_file(self, file_path: str) -> int:
        """Load attorneys from a JSON file.
        
        Args:
            file_path: Path to the attorneys file
            
        Returns:
            Number of attorneys loaded
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                attorneys_data = json.load(f)
            
            count = 0
            for attorney_data in attorneys_data:
                try:
                    attorney = Attorney(**attorney_data)
                    self.add_attorney(attorney)
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to load attorney: {e}")
            
            self.logger.info(f"Loaded {count} attorneys from {file_path}")
            return count
        except Exception as e:
            self.logger.error(f"Failed to load attorneys from {file_path}: {e}")
            return 0
    
    def add_privilege_indicator(self, indicator: PrivilegeIndicator) -> None:
        """Add a privilege indicator.
        
        Args:
            indicator: Privilege indicator to add
        """
        self.privilege_indicators[indicator.indicator_id] = indicator
    
    def add_attorney(self, attorney: Union[Attorney, Dict[str, Any]]) -> None:
        """Add an attorney.

        Args:
            attorney: Attorney to add (Attorney object or dictionary)
        """
        # Convert dictionary to Attorney object if needed
        if isinstance(attorney, dict):
            attorney = Attorney(**attorney)

        self.attorneys[attorney.attorney_id] = attorney

        # Add by email if available
        if attorney.email:
            self.attorneys[attorney.email.lower()] = attorney
    
    def is_attorney(self, email: str) -> bool:
        """Check if an email belongs to an attorney.
        
        Args:
            email: Email to check
            
        Returns:
            True if the email belongs to an attorney, False otherwise
        """
        email = email.lower()
        
        # Check if the email is directly in the attorneys dictionary
        if email in self.attorneys:
            return True
        
        # Check if any attorney has this email
        for attorney in self.attorneys.values():
            if attorney.email and attorney.email.lower() == email:
                return True
        
        return False
    
    def detect_privilege_indicators(self, document: Document) -> Dict[str, float]:
        """Detect privilege indicators in a document.
        
        Args:
            document: Document to analyze
            
        Returns:
            Dictionary mapping indicator IDs to confidence scores
        """
        detected_indicators = {}
        
        # Get document content and metadata
        content = document.content
        metadata = document.metadata
        
        # Check for indicators in the content
        for indicator_id, indicator in self.privilege_indicators.items():
            if not indicator.pattern:
                continue
            
            # Compile the pattern with the appropriate flags
            flags = 0 if indicator.case_sensitive else re.IGNORECASE
            pattern = re.compile(indicator.pattern, flags)
            
            # Determine what to check based on the indicator category
            if indicator.category == PrivilegeIndicatorCategory.HEADER:
                # Check the first few lines
                first_lines = '\n'.join(content.split('\n')[:5])
                matches = pattern.findall(first_lines)
                if matches:
                    detected_indicators[indicator_id] = indicator.weight
            
            elif indicator.category == PrivilegeIndicatorCategory.FOOTER:
                # Check the last few lines
                last_lines = '\n'.join(content.split('\n')[-5:])
                matches = pattern.findall(last_lines)
                if matches:
                    detected_indicators[indicator_id] = indicator.weight
            
            elif indicator.category == PrivilegeIndicatorCategory.SUBJECT_LINE:
                # Check the subject line if available
                if hasattr(document, 'subject'):
                    subject = getattr(document, 'subject', '')
                    if subject and pattern.search(subject):
                        detected_indicators[indicator_id] = indicator.weight
            
            elif indicator.category == PrivilegeIndicatorCategory.DOCUMENT_TYPE:
                # Check the document type in metadata
                doc_type = getattr(metadata, 'document_type', '')
                if doc_type and pattern.search(doc_type):
                    detected_indicators[indicator_id] = indicator.weight
            
            elif indicator.category == PrivilegeIndicatorCategory.METADATA:
                # Check various metadata fields
                for field in ('title', 'author', 'custodian', 'confidentiality'):
                    value = getattr(metadata, field, '')
                    if value and pattern.search(str(value)):
                        detected_indicators[indicator_id] = indicator.weight
                        break
            
            elif indicator.category == PrivilegeIndicatorCategory.CONTENT:
                # Check the entire content
                matches = pattern.findall(content)
                if matches:
                    detected_indicators[indicator_id] = indicator.weight
        
        return detected_indicators
    
    def detect_attorneys(self, document: Document) -> List[str]:
        """Detect attorneys involved in a document.
        
        Args:
            document: Document to analyze
            
        Returns:
            List of attorney IDs or emails
        """
        detected_attorneys = set()
        
        # Check email fields for EmailDocument
        if isinstance(document, EmailDocument):
            # Check sender
            if self.is_attorney(document.sender):
                detected_attorneys.add(document.sender.lower())
            
            # Check recipients
            for recipient in document.recipients:
                if self.is_attorney(recipient):
                    detected_attorneys.add(recipient.lower())
            
            # Check CC
            if document.cc:
                for cc in document.cc:
                    if self.is_attorney(cc):
                        detected_attorneys.add(cc.lower())
            
            # Check BCC
            if document.bcc:
                for bcc in document.bcc:
                    if self.is_attorney(bcc):
                        detected_attorneys.add(bcc.lower())
        
        # Check for attorney mentions in content
        content = document.content.lower()
        
        for attorney in self.attorneys.values():
            # Skip duplicate checks
            if attorney.attorney_id in detected_attorneys:
                continue
            
            # Check email
            if attorney.email and attorney.email.lower() in content:
                detected_attorneys.add(attorney.attorney_id)
                continue
            
            # Check name
            if attorney.name and attorney.name.lower() in content:
                detected_attorneys.add(attorney.attorney_id)
                continue
        
        return list(detected_attorneys)
    
    def calculate_privilege_score(self, detected_indicators: Dict[str, float],
                               attorneys_involved: List[str]) -> Tuple[float, List[PrivilegeType]]:
        """Calculate a privilege score for a document.
        
        Args:
            detected_indicators: Dictionary mapping indicator IDs to confidence scores
            attorneys_involved: List of attorney IDs or emails involved
            
        Returns:
            Tuple of confidence score and list of detected privilege types
        """
        if not detected_indicators and not attorneys_involved:
            return 0.0, []
        
        # Calculate base score from indicators
        indicator_score = 0.0
        max_score = 0.0
        detected_types = set()
        
        for indicator_id, confidence in detected_indicators.items():
            indicator = self.privilege_indicators.get(indicator_id)
            if indicator:
                indicator_score += confidence
                max_score += 1.0
                detected_types.add(indicator.indicator_type)
        
        # Normalize indicator score
        if max_score > 0:
            indicator_score /= max_score
        
        # Add attorney component
        attorney_score = min(1.0, len(attorneys_involved) * 0.3)
        
        # Combine scores
        # Weight: 70% indicators, 30% attorneys
        combined_score = (indicator_score * 0.7) + (attorney_score * 0.3)
        
        return combined_score, list(detected_types)
    
    def determine_privilege_status(self, confidence: float) -> PrivilegeStatus:
        """Determine privilege status based on confidence score.
        
        Args:
            confidence: Confidence score
            
        Returns:
            Privilege status
        """
        if confidence >= 0.8:
            return PrivilegeStatus.PRIVILEGED
        elif confidence >= 0.5:
            return PrivilegeStatus.POTENTIALLY_PRIVILEGED
        elif confidence > 0:
            return PrivilegeStatus.NOT_PRIVILEGED
        else:
            return PrivilegeStatus.UNKNOWN
    
    def detect_privilege(self, document: Document, privilege_type: Optional[str] = None,
                      attorneys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Detect privilege in a document.
        
        Args:
            document: Document to analyze
            privilege_type: Type of privilege to detect (None for all)
            attorneys: List of attorneys to check for (None for all)
            
        Returns:
            Dictionary with privilege detection results
        """
        # Detect privilege indicators
        detected_indicators = self.detect_privilege_indicators(document)
        
        # Filter by privilege type if specified
        if privilege_type:
            try:
                target_type = PrivilegeType(privilege_type)
                filtered_indicators = {}
                
                for indicator_id, confidence in detected_indicators.items():
                    indicator = self.privilege_indicators.get(indicator_id)
                    if indicator and indicator.indicator_type == target_type:
                        filtered_indicators[indicator_id] = confidence
                
                detected_indicators = filtered_indicators
            except ValueError:
                self.logger.warning(f"Unknown privilege type: {privilege_type}")
        
        # Detect attorneys involved
        attorneys_involved = self.detect_attorneys(document)
        
        # Filter by specified attorneys if provided
        if attorneys:
            attorneys_involved = [
                attorney for attorney in attorneys_involved
                if attorney in attorneys
            ]
        
        # Calculate privilege score
        confidence, privilege_types = self.calculate_privilege_score(
            detected_indicators, attorneys_involved
        )
        
        # Determine privilege status
        status = self.determine_privilege_status(confidence)
        
        # Create result
        doc_id = document.metadata.document_id
        result = PrivilegeDetectionResult(
            document_id=doc_id,
            status=status,
            confidence=confidence,
            privilege_types=privilege_types,
            detected_indicators=detected_indicators,
            attorneys_involved=attorneys_involved
        )
        
        # Add to privilege log
        self.privilege_log.add_entry(result)
        
        # Return as dictionary
        return {
            'document_id': doc_id,
            'status': status,
            'confidence': confidence,
            'privilege_types': privilege_types,
            'detected_indicators': detected_indicators,
            'attorneys_involved': attorneys_involved
        }
    
    def detect_privilege_in_collection(self, collection: DocumentCollection,
                                    privilege_type: Optional[str] = None,
                                    attorneys: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Detect privilege in a collection of documents.
        
        Args:
            collection: Document collection to analyze
            privilege_type: Type of privilege to detect (None for all)
            attorneys: List of attorneys to check for (None for all)
            
        Returns:
            Dictionary mapping document IDs to privilege detection results
        """
        results = {}
        
        for doc_id, document in collection.documents.items():
            results[doc_id] = self.detect_privilege(document, privilege_type, attorneys)
        
        return results
    
    def generate_privilege_log(self, format_type: str = "simple") -> Union[Dict[str, Any], str]:
        """Generate a privilege log.
        
        Args:
            format_type: Format of the log ("simple", "detailed", or "csv")
            
        Returns:
            Privilege log in the specified format
        """
        if format_type == "simple":
            # Simple JSON format
            log = {
                'entries': {},
                'summary': self.privilege_log.count_entries()
            }
            
            for doc_id, result in self.privilege_log.entries.items():
                log['entries'][doc_id] = {
                    'status': result.status,
                    'confidence': result.confidence,
                    'privilege_types': result.privilege_types
                }
            
            return log
        
        elif format_type == "detailed":
            # Detailed JSON format
            log = {
                'entries': {},
                'summary': self.privilege_log.count_entries()
            }
            
            for doc_id, result in self.privilege_log.entries.items():
                log['entries'][doc_id] = result.dict()
            
            return log
        
        elif format_type == "csv":
            # CSV format
            header = "Document ID,Status,Confidence,Privilege Types,Attorneys Involved,Indicator Count\n"
            rows = []
            
            for doc_id, result in self.privilege_log.entries.items():
                privilege_types = ",".join(result.privilege_types)
                attorneys = ",".join(result.attorneys_involved)
                indicator_count = len(result.detected_indicators)
                
                row = f"{doc_id},{result.status},{result.confidence:.2f},\"{privilege_types}\",\"{attorneys}\",{indicator_count}"
                rows.append(row)
            
            return header + "\n".join(rows)
        
        else:
            self.logger.warning(f"Unknown log format: {format_type}")
            return "Unknown log format"
    
    # Implement BaseDetectorService abstract methods
    async def initialize(self) -> None:
        """Initialize the privilege detector service.
        
        Raises:
            ServiceError: If initialization fails
        """
        try:
            if not self._indicators_initialized:
                self._initialize_default_indicators()
                self._indicators_initialized = True
            
            self.logger.info("Privilege detector service initialized successfully")
        except Exception as e:
            raise ServiceError(f"Failed to initialize privilege detector: {str(e)}", 
                             service_name=self.config.service_name, operation="initialize")
    
    async def shutdown(self) -> None:
        """Shutdown the privilege detector service.
        
        Raises:
            ServiceError: If shutdown fails
        """
        try:
            # Clear resources
            self.privilege_indicators.clear()
            self.attorneys.clear()
            self.privilege_log = PrivilegeLog()
            
            self.logger.info("Privilege detector service shutdown successfully")
        except Exception as e:
            raise ServiceError(f"Failed to shutdown privilege detector: {str(e)}", 
                             service_name=self.config.service_name, operation="shutdown")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the privilege detector service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            return {
                "healthy": True,
                "indicators_count": len(self.privilege_indicators),
                "attorneys_count": len(self.attorneys),
                "log_entries_count": len(self.privilege_log.entries),
                "indicators_initialized": self._indicators_initialized
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def detect(
        self,
        content: Union[str, BaseDocument, List[BaseDocument]],
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Detect privilege patterns in content.
        
        Args:
            content: Content to analyze
            context: Optional execution context
            
        Returns:
            Detection results
        """
        if isinstance(content, str):
            # Create a simple document from string content
            from ..core.document import Document, DocumentMetadata
            from datetime import datetime
            
            metadata = DocumentMetadata(
                document_id="temp_doc",
                title="Temporary Document",
                document_type="text",
                date_created=datetime.now()
            )
            
            document = Document(metadata=metadata, content=content)
            return self.detect_privilege(document)
        
        elif isinstance(content, (Document, BaseDocument)):
            return self.detect_privilege(content)
        
        elif isinstance(content, list):
            results = []
            for item in content:
                if isinstance(item, (Document, BaseDocument)):
                    results.append(self.detect_privilege(item))
                else:
                    results.append({"error": f"Unsupported content type: {type(item)}"})
            return {"batch_results": results}
        
        else:
            return {"error": f"Unsupported content type: {type(content)}"}
    
    async def scan_document(
        self,
        document: BaseDocument,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Scan a single document for privilege patterns.
        
        Args:
            document: Document to scan
            context: Optional execution context
            
        Returns:
            Scan results
        """
        try:
            # Convert BaseDocument to Document if needed
            if isinstance(document, BaseDocument) and not isinstance(document, Document):
                # Create a Document from BaseDocument
                from ..core.document import Document, DocumentMetadata
                
                metadata = DocumentMetadata(
                    document_id=document.metadata.document_id,
                    title=document.metadata.title,
                    document_type=document.metadata.document_type,
                    date_created=document.metadata.date_created,
                    date_modified=document.metadata.date_modified,
                    author=document.metadata.author,
                    source=document.metadata.source,
                    file_path=document.metadata.file_path,
                    file_type=document.metadata.file_type,
                    file_size=document.metadata.file_size
                )
                
                legal_document = Document(metadata=metadata, content=document.content)
            else:
                legal_document = document
            
            return self.detect_privilege(legal_document)
        
        except Exception as e:
            return {
                "error": str(e),
                "document_id": getattr(document.metadata, 'document_id', 'unknown')
            }