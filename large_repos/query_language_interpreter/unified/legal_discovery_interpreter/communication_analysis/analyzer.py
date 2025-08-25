"""Communication analyzer for legal discovery."""

import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import logging
import asyncio
from collections import defaultdict

# Common library imports
from common.services.base_services import BaseAnalyzerService, ServiceConfig
from common.core.base_models import BaseDocument, ExecutionContext
from common.core.exceptions import ServiceError
from common.utils.logging import get_logger

# Legal-specific imports
from ..core.document import Document, DocumentCollection, EmailDocument
from .models import (
    ParticipantInfo,
    CommunicationParticipant,
    ParticipantRole,
    Message,
    MessageType,
    MessageDirection,
    MessageStatus,
    MessageThread,
    CommunicationGraph
)


class CommunicationAnalyzer(BaseAnalyzerService):
    """Analyzer for communication patterns in legal discovery.
    
    This analyzer provides functionality for analyzing email and message
    communications to identify exchanges between specific individuals or
    departments.
    """
    
    def __init__(self, config: Optional[ServiceConfig] = None, logger=None):
        """Initialize the communication analyzer.
        
        Args:
            config: Service configuration
            logger: Logger instance
        """
        # Initialize with default config if none provided
        if config is None:
            config = ServiceConfig(
                service_name="communication_analyzer",
                service_type="analyzer",
                enabled=True,
                config={}
            )
        
        super().__init__(config)
        
        self.logger = logger or get_logger(__name__)
        self.communication_graph = CommunicationGraph()
        self.participant_map: Dict[str, ParticipantInfo] = {}
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+(?:\.\w+)+')
        self.email_to_org_map: Dict[str, str] = {}
    
    def extract_email_address(self, text: str) -> Optional[str]:
        """Extract an email address from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            Extracted email address, or None if not found
        """
        match = self.email_pattern.search(text)
        if match:
            return match.group(0).lower()
        
        return None
    
    def parse_participant_string(self, text: str) -> List[ParticipantInfo]:
        """Parse a string containing participant information.
        
        Args:
            text: String to parse (e.g., "John Doe <john.doe@example.com>")
            
        Returns:
            List of parsed participant information
        """
        participants = []
        
        # Split by commas or semicolons
        parts = re.split(r'[,;]', text)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Try to extract email and name
            email_match = self.email_pattern.search(part)
            if email_match:
                email = email_match.group(0).lower()
                
                # Extract name
                name = part.replace(email_match.group(0), '').strip()
                name = re.sub(r'[<>"]', '', name).strip()
                
                if not name:
                    # Try to infer a name from the email
                    name_part = email.split('@')[0]
                    name = name_part.replace('.', ' ').title()
                
                # Get organization from domain
                organization = None
                if '@' in email:
                    domain = email.split('@')[1]
                    organization = domain.split('.')[0].title()
                
                participant = ParticipantInfo(
                    email=email,
                    name=name if name else None,
                    organization=organization
                )
                
                participants.append(participant)
                
                # Add to the participant map
                self.participant_map[email] = participant
                
                # Add to the organization map
                if organization:
                    self.email_to_org_map[email] = organization
            else:
                # No email found, try the next part
                continue
        
        return participants
    
    def parse_email_document(self, document: EmailDocument) -> Optional[Message]:
        """Parse an email document into a message.
        
        Args:
            document: Email document to parse
            
        Returns:
            Parsed message, or None if parsing failed
        """
        try:
            # Create participants
            participants = []
            
            # Add sender
            sender_info = self.parse_participant_string(document.sender)
            if sender_info:
                participants.append(
                    CommunicationParticipant(
                        participant_info=sender_info[0],
                        role=ParticipantRole.SENDER
                    )
                )
            
            # Add recipients
            for recipient in document.recipients:
                recipient_infos = self.parse_participant_string(recipient)
                for recipient_info in recipient_infos:
                    participants.append(
                        CommunicationParticipant(
                            participant_info=recipient_info,
                            role=ParticipantRole.RECIPIENT
                        )
                    )
            
            # Add CC recipients if available
            if document.cc:
                for cc in document.cc:
                    cc_infos = self.parse_participant_string(cc)
                    for cc_info in cc_infos:
                        participants.append(
                            CommunicationParticipant(
                                participant_info=cc_info,
                                role=ParticipantRole.CC
                            )
                        )
            
            # Add BCC recipients if available
            if document.bcc:
                for bcc in document.bcc:
                    bcc_infos = self.parse_participant_string(bcc)
                    for bcc_info in bcc_infos:
                        participants.append(
                            CommunicationParticipant(
                                participant_info=bcc_info,
                                role=ParticipantRole.BCC
                            )
                        )
            
            # Create the message
            message = Message(
                message_id=document.metadata.document_id,
                thread_id=document.thread_id,
                in_reply_to=document.in_reply_to,
                message_type=MessageType.EMAIL,
                subject=document.subject,
                content=document.content,
                sent_date=document.sent_date,
                participants=participants,
                status=MessageStatus.SENT,
                attachments=document.attachments
            )
            
            # Determine message direction
            if sender_info:
                sender_domain = sender_info[0].email.split('@')[1] if '@' in sender_info[0].email else None
                outbound = True
                
                for participant in participants:
                    if participant.role in (ParticipantRole.RECIPIENT, ParticipantRole.CC, ParticipantRole.BCC):
                        recipient_domain = participant.participant_info.email.split('@')[1] if '@' in participant.participant_info.email else None
                        
                        if recipient_domain and sender_domain and recipient_domain == sender_domain:
                            outbound = False
                
                message.direction = MessageDirection.OUTBOUND if outbound else MessageDirection.INTERNAL
            
            return message
        except Exception as e:
            self.logger.error(f"Error parsing email document {document.metadata.document_id}: {e}")
            return None
    
    def extract_messages_from_collection(self, collection: DocumentCollection) -> List[Message]:
        """Extract messages from a document collection.
        
        Args:
            collection: Document collection to extract from
            
        Returns:
            List of extracted messages
        """
        messages = []
        
        for doc_id, document in collection.documents.items():
            if isinstance(document, EmailDocument):
                message = self.parse_email_document(document)
                if message:
                    messages.append(message)
                    
                    # Add the message to the communication graph
                    self.communication_graph.add_message(message)
            elif isinstance(document, Document):
                # Try to detect if this is an email from content
                content = document.content.lower()
                if 'from:' in content and 'to:' in content and ('subject:' in content or 'sent:' in content):
                    # This might be an email, try to extract information
                    try:
                        # Extract sender
                        sender_match = re.search(r'from:([^\n]+)', content)
                        sender = sender_match.group(1).strip() if sender_match else None
                        
                        # Extract recipients
                        recipients_match = re.search(r'to:([^\n]+)', content)
                        recipients = recipients_match.group(1).strip() if recipients_match else None
                        
                        # Extract subject
                        subject_match = re.search(r'subject:([^\n]+)', content)
                        subject = subject_match.group(1).strip() if subject_match else None
                        
                        # Extract date
                        date_match = re.search(r'sent:([^\n]+)', content) or re.search(r'date:([^\n]+)', content)
                        date_str = date_match.group(1).strip() if date_match else None
                        sent_date = None
                        
                        if date_str:
                            # Try to parse the date
                            try:
                                # Try common date formats
                                for fmt in ('%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%d %b %Y %H:%M:%S'):
                                    try:
                                        sent_date = datetime.strptime(date_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                # If date parsing fails, just continue without a date
                                pass
                        
                        # Create participants
                        participants = []
                        
                        # Add sender
                        if sender:
                            sender_infos = self.parse_participant_string(sender)
                            for sender_info in sender_infos:
                                participants.append(
                                    CommunicationParticipant(
                                        participant_info=sender_info,
                                        role=ParticipantRole.SENDER
                                    )
                                )
                        
                        # Add recipients
                        if recipients:
                            recipient_infos = self.parse_participant_string(recipients)
                            for recipient_info in recipient_infos:
                                participants.append(
                                    CommunicationParticipant(
                                        participant_info=recipient_info,
                                        role=ParticipantRole.RECIPIENT
                                    )
                                )
                        
                        # Create the message
                        message = Message(
                            message_id=doc_id,
                            message_type=MessageType.EMAIL,
                            subject=subject,
                            content=content,
                            sent_date=sent_date,
                            participants=participants,
                            status=MessageStatus.SENT
                        )
                        
                        messages.append(message)
                        
                        # Add the message to the communication graph
                        self.communication_graph.add_message(message)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract email from document {doc_id}: {e}")
        
        return messages
    
    def build_communication_graph(self, messages: List[Message]) -> CommunicationGraph:
        """Build a communication graph from messages.
        
        Args:
            messages: List of messages to build the graph from
            
        Returns:
            Built communication graph
        """
        graph = CommunicationGraph()
        
        for message in messages:
            graph.add_message(message)
        
        return graph
    
    def find_communications(self, participants: List[str], direction: Optional[str] = None,
                         date_range: Optional[Dict[str, datetime]] = None,
                         analyze_threads: bool = False, include_cc: bool = True,
                         include_bcc: bool = False) -> List[str]:
        """Find communications involving specific participants.
        
        Args:
            participants: List of participant emails or domains
            direction: Direction of communication (e.g., 'from', 'to', 'between')
            date_range: Date range for filtering
            analyze_threads: Whether to analyze message threads
            include_cc: Whether to include CC recipients
            include_bcc: Whether to include BCC recipients
            
        Returns:
            List of matching message IDs
        """
        matching_messages = []
        
        # Normalize participants to lowercase
        participants = [p.lower() for p in participants]
        
        # Check if participants are emails or domains
        participant_domains = []
        for participant in participants:
            if '@' not in participant:
                participant_domains.append(participant.lower())
        
        for thread_id, thread in self.communication_graph.threads.items():
            thread_matches = False
            message_matches = {}
            
            for message_id, message in thread.messages.items():
                # Check date range if specified
                if date_range:
                    if message.sent_date:
                        if 'start' in date_range and message.sent_date < date_range['start']:
                            continue
                        
                        if 'end' in date_range and message.sent_date > date_range['end']:
                            continue
                    else:
                        # Skip messages without a sent date if date range is specified
                        continue
                
                # Check participants
                message_match = False
                sender = message.get_sender()
                recipients = message.get_recipients(include_cc=include_cc, include_bcc=include_bcc)
                
                sender_matches = False
                if sender:
                    sender_email = sender.email.lower()
                    if sender_email in participants:
                        sender_matches = True
                    else:
                        # Check domain
                        for domain in participant_domains:
                            if '@' in sender_email and sender_email.split('@')[1].startswith(domain):
                                sender_matches = True
                                break
                
                recipient_matches = []
                for recipient in recipients:
                    recipient_email = recipient.email.lower()
                    if recipient_email in participants:
                        recipient_matches.append(recipient_email)
                    else:
                        # Check domain
                        for domain in participant_domains:
                            if '@' in recipient_email and recipient_email.split('@')[1].startswith(domain):
                                recipient_matches.append(recipient_email)
                                break
                
                # Check direction
                if direction:
                    if direction.lower() == 'from':
                        if sender_matches:
                            message_match = True
                    elif direction.lower() == 'to':
                        if recipient_matches:
                            message_match = True
                    elif direction.lower() == 'between':
                        if sender_matches and recipient_matches:
                            message_match = True
                    else:
                        # Default to any direction
                        if sender_matches or recipient_matches:
                            message_match = True
                else:
                    # No direction specified, match any participant
                    if sender_matches or recipient_matches:
                        message_match = True
                
                if message_match:
                    message_matches[message_id] = True
                    thread_matches = True
            
            if thread_matches:
                if analyze_threads:
                    # Include all messages in the thread
                    for message_id in thread.messages:
                        matching_messages.append(message_id)
                else:
                    # Include only the matching messages
                    matching_messages.extend(message_matches.keys())
        
        return matching_messages
    
    def analyze_communication(self, message_ids: List[str]) -> Dict[str, Any]:
        """Analyze communication patterns in a set of messages.
        
        Args:
            message_ids: List of message IDs to analyze
            
        Returns:
            Analysis results
        """
        if not message_ids:
            return {
                'message_count': 0,
                'thread_count': 0,
                'participants': {},
                'thread_analysis': {},
                'timeline': []
            }
        
        # Collect messages and threads
        messages = []
        thread_ids = set()
        participants = set()
        
        for thread_id, thread in self.communication_graph.threads.items():
            thread_has_match = False
            thread_messages = []
            
            for message_id, message in thread.messages.items():
                if message_id in message_ids:
                    thread_has_match = True
                    thread_messages.append(message)
                    
                    # Add participants
                    sender = message.get_sender()
                    if sender:
                        participants.add(sender.email)
                    
                    for recipient in message.get_recipients(include_cc=True, include_bcc=True):
                        participants.add(recipient.email)
            
            if thread_has_match:
                thread_ids.add(thread_id)
                messages.extend(thread_messages)
        
        # Build analysis results
        results = {
            'message_count': len(messages),
            'thread_count': len(thread_ids),
            'participants': {},
            'thread_analysis': {},
            'timeline': []
        }
        
        # Analyze participants
        participant_counts = defaultdict(lambda: {'sent': 0, 'received': 0})
        org_counts = defaultdict(lambda: {'sent': 0, 'received': 0})
        
        for message in messages:
            sender = message.get_sender()
            if sender:
                sender_email = sender.email
                participant_counts[sender_email]['sent'] += 1
                
                # Add organization counts
                sender_org = self.email_to_org_map.get(sender_email)
                if sender_org:
                    org_counts[sender_org]['sent'] += 1
            
            for recipient in message.get_recipients(include_cc=True, include_bcc=True):
                recipient_email = recipient.email
                participant_counts[recipient_email]['received'] += 1
                
                # Add organization counts
                recipient_org = self.email_to_org_map.get(recipient_email)
                if recipient_org:
                    org_counts[recipient_org]['received'] += 1
        
        # Add participant information to results
        for email, counts in participant_counts.items():
            counts['total'] = counts['sent'] + counts['received']
            
            results['participants'][email] = {
                'info': self.participant_map.get(email, {'email': email}),
                'counts': counts
            }
        
        # Add organization information to results
        results['organizations'] = {}
        for org, counts in org_counts.items():
            counts['total'] = counts['sent'] + counts['received']
            
            results['organizations'][org] = {
                'name': org,
                'counts': counts
            }
        
        # Analyze threads
        for thread_id in thread_ids:
            thread = self.communication_graph.threads.get(thread_id)
            if not thread:
                continue
            
            thread_messages = thread.get_message_sequence()
            thread_timeline = []
            
            for message in thread_messages:
                if message.message_id in message_ids:
                    sender = message.get_sender()
                    recipients = message.get_recipients(include_cc=True, include_bcc=True)
                    
                    timeline_entry = {
                        'message_id': message.message_id,
                        'sent_date': message.sent_date,
                        'subject': message.subject,
                        'sender': sender.email if sender else None,
                        'recipients': [r.email for r in recipients]
                    }
                    
                    thread_timeline.append(timeline_entry)
            
            if thread_timeline:
                results['thread_analysis'][thread_id] = {
                    'subject': thread.subject,
                    'timeline': thread_timeline,
                    'participant_count': len(thread.participants),
                    'message_count': len([m for m in thread_messages if m.message_id in message_ids])
                }
        
        # Create overall timeline
        timeline = []
        for message in messages:
            sender = message.get_sender()
            recipients = message.get_recipients(include_cc=True, include_bcc=True)
            
            timeline_entry = {
                'message_id': message.message_id,
                'thread_id': message.thread_id,
                'sent_date': message.sent_date,
                'subject': message.subject,
                'sender': sender.email if sender else None,
                'recipients': [r.email for r in recipients]
            }
            
            timeline.append(timeline_entry)
        
        # Sort timeline by sent date
        timeline.sort(key=lambda entry: entry['sent_date'] or datetime.min)
        
        results['timeline'] = timeline
        
        return results
    
    def find_key_participants(self, message_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Find key participants in a set of messages.
        
        Args:
            message_ids: List of message IDs to analyze
            limit: Maximum number of participants to return
            
        Returns:
            List of key participants with their information and activity
        """
        analysis = self.analyze_communication(message_ids)
        
        # Sort participants by total message count
        key_participants = []
        for email, data in analysis['participants'].items():
            key_participants.append({
                'email': email,
                'info': data['info'],
                'sent': data['counts']['sent'],
                'received': data['counts']['received'],
                'total': data['counts']['total']
            })
        
        # Sort by total in descending order
        key_participants.sort(key=lambda p: p['total'], reverse=True)
        
        return key_participants[:limit]
    
    # Implement BaseAnalyzerService abstract methods
    async def initialize(self) -> None:
        """Initialize the communication analyzer service.
        
        Raises:
            ServiceError: If initialization fails
        """
        try:
            # Initialize communication graph and other resources
            self.communication_graph = CommunicationGraph()
            self.participant_map = {}
            self.email_to_org_map = {}
            
            self.logger.info("Communication analyzer service initialized successfully")
        except Exception as e:
            raise ServiceError(f"Failed to initialize communication analyzer: {str(e)}", 
                             service_name=self.config.service_name, operation="initialize")
    
    async def shutdown(self) -> None:
        """Shutdown the communication analyzer service.
        
        Raises:
            ServiceError: If shutdown fails
        """
        try:
            # Clear resources
            self.communication_graph = CommunicationGraph()
            self.participant_map.clear()
            self.email_to_org_map.clear()
            
            self.logger.info("Communication analyzer service shutdown successfully")
        except Exception as e:
            raise ServiceError(f"Failed to shutdown communication analyzer: {str(e)}", 
                             service_name=self.config.service_name, operation="shutdown")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the communication analyzer service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            return {
                "healthy": True,
                "threads_count": len(self.communication_graph.threads),
                "participants_count": len(self.participant_map),
                "organizations_count": len(self.email_to_org_map)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def analyze(
        self,
        data: Any,
        analysis_type: str,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Analyze communication data.
        
        Args:
            data: Data to analyze (document collection or message list)
            analysis_type: Type of analysis ('extract_messages', 'build_graph', 'analyze_patterns')
            context: Optional execution context
            
        Returns:
            Analysis results
        """
        try:
            if analysis_type == "extract_messages":
                if isinstance(data, DocumentCollection):
                    messages = self.extract_messages_from_collection(data)
                    return {"messages": [msg.dict() for msg in messages]}
                else:
                    return {"error": "Data must be a DocumentCollection for extract_messages analysis"}
            
            elif analysis_type == "build_graph":
                if isinstance(data, list):
                    # Assume list of messages
                    graph = self.build_communication_graph(data)
                    return {"graph_info": {
                        "threads_count": len(graph.threads),
                        "total_messages": sum(len(thread.messages) for thread in graph.threads.values()),
                        "participants_count": len(graph.participants)
                    }}
                else:
                    return {"error": "Data must be a list of messages for build_graph analysis"}
            
            elif analysis_type == "analyze_patterns":
                if isinstance(data, list):
                    # Assume list of message IDs
                    return self.analyze_communication(data)
                else:
                    return {"error": "Data must be a list of message IDs for analyze_patterns analysis"}
            
            elif analysis_type == "find_key_participants":
                if isinstance(data, list):
                    limit = context.user_context.get("limit", 10) if context else 10
                    return {"key_participants": self.find_key_participants(data, limit)}
                else:
                    return {"error": "Data must be a list of message IDs for find_key_participants analysis"}
            
            else:
                return {"error": f"Unsupported analysis type: {analysis_type}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def extract_features(
        self,
        data: Any,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Extract features from communication data.
        
        Args:
            data: Data to extract features from
            context: Optional execution context
            
        Returns:
            Extracted features
        """
        try:
            if isinstance(data, Document):
                if isinstance(data, EmailDocument):
                    message = self.parse_email_document(data)
                    if message:
                        return {
                            "message_type": message.message_type.value,
                            "participants_count": len(message.participants),
                            "subject": message.subject,
                            "has_attachments": bool(message.attachments),
                            "direction": message.direction.value if message.direction else None,
                            "thread_id": message.thread_id
                        }
                
                return {
                    "document_type": data.metadata.document_type,
                    "content_length": len(data.content),
                    "has_email_patterns": bool(self.email_pattern.search(data.content))
                }
            
            elif isinstance(data, Message):
                return {
                    "message_type": data.message_type.value,
                    "participants_count": len(data.participants),
                    "subject": data.subject,
                    "has_attachments": bool(data.attachments),
                    "direction": data.direction.value if data.direction else None,
                    "thread_id": data.thread_id,
                    "content_length": len(data.content) if data.content else 0
                }
            
            else:
                return {"error": f"Unsupported data type for feature extraction: {type(data)}"}
        
        except Exception as e:
            return {"error": str(e)}