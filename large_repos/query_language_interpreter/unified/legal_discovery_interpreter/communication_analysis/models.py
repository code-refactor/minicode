"""Models for communication pattern analysis."""

from typing import Dict, List, Set, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ParticipantRole(str, Enum):
    """Roles of participants in communications."""
    
    SENDER = "sender"
    RECIPIENT = "recipient"
    CC = "cc"
    BCC = "bcc"
    FORWARDED = "forwarded"
    REPLY_TO = "reply_to"
    MENTION = "mention"


class ParticipantInfo(BaseModel):
    """Information about a participant in communications."""
    
    email: str = Field(..., description="Email address of the participant")
    name: Optional[str] = Field(None, description="Name of the participant")
    organization: Optional[str] = Field(None, description="Organization of the participant")
    department: Optional[str] = Field(None, description="Department of the participant")
    title: Optional[str] = Field(None, description="Title of the participant")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class CommunicationParticipant(BaseModel):
    """Model for a participant in a communication."""
    
    participant_info: ParticipantInfo = Field(..., description="Information about the participant")
    role: ParticipantRole = Field(..., description="Role of the participant in the communication")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class MessageType(str, Enum):
    """Types of messages."""
    
    EMAIL = "email"
    CHAT = "chat"
    TEXT = "text"
    MEMO = "memo"
    LETTER = "letter"


class MessageDirection(str, Enum):
    """Directions of messages."""
    
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    EXTERNAL = "external"


class MessageImportance(str, Enum):
    """Importance levels of messages."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(str, Enum):
    """Status of messages."""
    
    SENT = "sent"
    RECEIVED = "received"
    DRAFT = "draft"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """Model for a message in a communication."""
    
    message_id: str = Field(..., description="Unique identifier for the message")
    thread_id: Optional[str] = Field(None, description="Thread identifier for the message")
    in_reply_to: Optional[str] = Field(None, description="Message ID this is in reply to")
    references: Optional[List[str]] = Field(None, description="Message IDs referenced by this message")
    
    message_type: MessageType = Field(..., description="Type of message")
    subject: Optional[str] = Field(None, description="Subject of the message")
    content: str = Field(..., description="Content of the message")
    
    sent_date: Optional[datetime] = Field(None, description="Date and time the message was sent")
    received_date: Optional[datetime] = Field(None, description="Date and time the message was received")
    
    participants: List[CommunicationParticipant] = Field(
        ..., description="Participants in the message"
    )
    
    direction: Optional[MessageDirection] = Field(None, description="Direction of the message")
    importance: MessageImportance = Field(
        default=MessageImportance.NORMAL, description="Importance of the message"
    )
    status: MessageStatus = Field(
        default=MessageStatus.UNKNOWN, description="Status of the message"
    )
    
    attachments: Optional[List[str]] = Field(None, description="Attachment document IDs")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"
    
    def get_sender(self) -> Optional[ParticipantInfo]:
        """Get the sender of the message.
        
        Returns:
            Sender information, or None if not found
        """
        for participant in self.participants:
            if participant.role == ParticipantRole.SENDER:
                return participant.participant_info
        
        return None
    
    def get_recipients(self, include_cc: bool = True, include_bcc: bool = False) -> List[ParticipantInfo]:
        """Get the recipients of the message.
        
        Args:
            include_cc: Whether to include CC recipients
            include_bcc: Whether to include BCC recipients
            
        Returns:
            List of recipient information
        """
        recipients = []
        
        for participant in self.participants:
            if participant.role == ParticipantRole.RECIPIENT:
                recipients.append(participant.participant_info)
            elif include_cc and participant.role == ParticipantRole.CC:
                recipients.append(participant.participant_info)
            elif include_bcc and participant.role == ParticipantRole.BCC:
                recipients.append(participant.participant_info)
        
        return recipients


class MessageThread(BaseModel):
    """Model for a thread of messages."""
    
    thread_id: str = Field(..., description="Unique identifier for the thread")
    subject: Optional[str] = Field(None, description="Subject of the thread")
    messages: Dict[str, Message] = Field(default_factory=dict, description="Messages in the thread")
    
    start_date: Optional[datetime] = Field(None, description="Start date of the thread")
    end_date: Optional[datetime] = Field(None, description="End date of the thread")
    
    participants: Dict[str, ParticipantInfo] = Field(
        default_factory=dict, description="Participants in the thread"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"
    
    def add_message(self, message: Message) -> None:
        """Add a message to the thread.
        
        Args:
            message: Message to add
        """
        self.messages[message.message_id] = message
        
        # Update thread subject if not set
        if not self.subject and message.subject:
            self.subject = message.subject
        
        # Update thread dates
        if message.sent_date:
            if not self.start_date or message.sent_date < self.start_date:
                self.start_date = message.sent_date
            
            if not self.end_date or message.sent_date > self.end_date:
                self.end_date = message.sent_date
        
        # Update participants
        for participant in message.participants:
            participant_info = participant.participant_info
            if participant_info.email not in self.participants:
                self.participants[participant_info.email] = participant_info
    
    def get_message_sequence(self) -> List[Message]:
        """Get the messages in the thread in chronological order.
        
        Returns:
            List of messages in chronological order
        """
        messages = list(self.messages.values())
        
        # Sort by sent date
        messages.sort(key=lambda m: m.sent_date or datetime.min)
        
        return messages
    
    def get_participant_roles(self) -> Dict[str, Set[ParticipantRole]]:
        """Get the roles of participants in the thread.
        
        Returns:
            Dictionary mapping participant emails to sets of roles
        """
        roles = {}
        
        for message in self.messages.values():
            for participant in message.participants:
                email = participant.participant_info.email
                
                if email not in roles:
                    roles[email] = set()
                
                roles[email].add(participant.role)
        
        return roles


class CommunicationGraph(BaseModel):
    """Graph of communications between participants."""
    
    participants: Dict[str, ParticipantInfo] = Field(
        default_factory=dict, description="Participants in the graph"
    )
    
    # Adjacency list representation of the graph
    # Maps participant emails to dictionaries of recipient emails to message counts
    adjacency_list: Dict[str, Dict[str, int]] = Field(
        default_factory=dict, description="Adjacency list of the graph"
    )
    
    # Map of thread IDs to threads
    threads: Dict[str, MessageThread] = Field(
        default_factory=dict, description="Message threads"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"
    
    def add_message(self, message: Message) -> None:
        """Add a message to the graph.
        
        Args:
            message: Message to add
        """
        sender = message.get_sender()
        if not sender:
            return
        
        sender_email = sender.email
        
        # Add sender to participants
        if sender_email not in self.participants:
            self.participants[sender_email] = sender
        
        # Add sender to adjacency list if not present
        if sender_email not in self.adjacency_list:
            self.adjacency_list[sender_email] = {}
        
        # Add the message to the appropriate thread
        if message.thread_id:
            if message.thread_id not in self.threads:
                self.threads[message.thread_id] = MessageThread(
                    thread_id=message.thread_id
                )
            
            self.threads[message.thread_id].add_message(message)
        
        # Process recipients
        recipients = message.get_recipients(include_cc=True, include_bcc=True)
        
        for recipient in recipients:
            recipient_email = recipient.email
            
            # Add recipient to participants
            if recipient_email not in self.participants:
                self.participants[recipient_email] = recipient
            
            # Add recipient to sender's adjacency list
            if recipient_email not in self.adjacency_list[sender_email]:
                self.adjacency_list[sender_email][recipient_email] = 0
            
            self.adjacency_list[sender_email][recipient_email] += 1
            
            # Add recipient to adjacency list if not present
            if recipient_email not in self.adjacency_list:
                self.adjacency_list[recipient_email] = {}
    
    def get_communication_count(self, sender: str, recipient: str) -> int:
        """Get the number of communications from a sender to a recipient.
        
        Args:
            sender: Email of the sender
            recipient: Email of the recipient
            
        Returns:
            Number of communications
        """
        if sender not in self.adjacency_list:
            return 0
        
        return self.adjacency_list[sender].get(recipient, 0)
    
    def get_total_communications(self, participant: str) -> Dict[str, int]:
        """Get the total number of communications for a participant.
        
        Args:
            participant: Email of the participant
            
        Returns:
            Dictionary with sent and received counts
        """
        sent = 0
        received = 0
        
        # Count sent messages
        if participant in self.adjacency_list:
            sent = sum(self.adjacency_list[participant].values())
        
        # Count received messages
        for sender, recipients in self.adjacency_list.items():
            if participant in recipients:
                received += recipients[participant]
        
        return {
            'sent': sent,
            'received': received,
            'total': sent + received
        }
    
    def get_most_active_participants(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most active participants in the graph.
        
        Args:
            limit: Maximum number of participants to return
            
        Returns:
            List of participant information with activity counts
        """
        participants_activity = []
        
        for email in self.participants:
            counts = self.get_total_communications(email)
            
            participants_activity.append({
                'email': email,
                'info': self.participants[email],
                'sent': counts['sent'],
                'received': counts['received'],
                'total': counts['total']
            })
        
        # Sort by total activity in descending order
        participants_activity.sort(key=lambda p: p['total'], reverse=True)
        
        return participants_activity[:limit]
    
    def find_paths(self, start: str, end: str, max_length: int = 3) -> List[List[str]]:
        """Find paths between two participants.
        
        Args:
            start: Email of the starting participant
            end: Email of the ending participant
            max_length: Maximum path length
            
        Returns:
            List of paths, where each path is a list of participant emails
        """
        if start not in self.adjacency_list or end not in self.adjacency_list:
            return []
        
        paths = []
        visited = set()
        
        def dfs(current: str, path: List[str], length: int):
            if length > max_length:
                return
            
            if current == end:
                paths.append(path.copy())
                return
            
            visited.add(current)
            
            for next_participant in self.adjacency_list[current]:
                if next_participant not in visited:
                    path.append(next_participant)
                    dfs(next_participant, path, length + 1)
                    path.pop()
            
            visited.remove(current)
        
        dfs(start, [start], 1)
        
        return paths