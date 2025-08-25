"""Tests for the communication pattern analysis models."""

import pytest
from datetime import datetime
from legal_discovery_interpreter.communication_analysis.models import (
    ParticipantRole,
    ParticipantInfo,
    CommunicationParticipant,
    MessageType,
    MessageDirection,
    MessageImportance,
    MessageStatus,
    Message,
    MessageThread,
    CommunicationGraph
)


def test_participant_info():
    """Test creating participant information."""
    participant = ParticipantInfo(
        email="john.doe@example.com",
        name="John Doe",
        organization="Example Corp",
        department="Legal",
        title="General Counsel"
    )
    
    assert participant.email == "john.doe@example.com"
    assert participant.name == "John Doe"
    assert participant.organization == "Example Corp"
    assert participant.department == "Legal"
    assert participant.title == "General Counsel"


def test_communication_participant():
    """Test creating a communication participant."""
    participant_info = ParticipantInfo(
        email="john.doe@example.com",
        name="John Doe"
    )
    
    participant = CommunicationParticipant(
        participant_info=participant_info,
        role=ParticipantRole.SENDER
    )
    
    assert participant.participant_info == participant_info
    assert participant.role == ParticipantRole.SENDER


def test_message():
    """Test creating a message."""
    sender = CommunicationParticipant(
        participant_info=ParticipantInfo(email="john.doe@example.com", name="John Doe"),
        role=ParticipantRole.SENDER
    )
    
    recipient = CommunicationParticipant(
        participant_info=ParticipantInfo(email="jane.smith@example.com", name="Jane Smith"),
        role=ParticipantRole.RECIPIENT
    )
    
    message = Message(
        message_id="msg001",
        thread_id="thread001",
        message_type=MessageType.EMAIL,
        subject="Test Email",
        content="This is a test email",
        sent_date=datetime(2020, 1, 1, 10, 0),
        participants=[sender, recipient],
        direction=MessageDirection.OUTBOUND,
        importance=MessageImportance.NORMAL,
        status=MessageStatus.SENT
    )
    
    assert message.message_id == "msg001"
    assert message.thread_id == "thread001"
    assert message.message_type == MessageType.EMAIL
    assert message.subject == "Test Email"
    assert message.content == "This is a test email"
    assert message.sent_date == datetime(2020, 1, 1, 10, 0)
    assert len(message.participants) == 2
    assert message.direction == MessageDirection.OUTBOUND
    assert message.importance == MessageImportance.NORMAL
    assert message.status == MessageStatus.SENT


def test_message_get_sender():
    """Test getting the sender of a message."""
    sender = CommunicationParticipant(
        participant_info=ParticipantInfo(email="john.doe@example.com", name="John Doe"),
        role=ParticipantRole.SENDER
    )
    
    recipient = CommunicationParticipant(
        participant_info=ParticipantInfo(email="jane.smith@example.com", name="Jane Smith"),
        role=ParticipantRole.RECIPIENT
    )
    
    message = Message(
        message_id="msg001",
        message_type=MessageType.EMAIL,
        content="This is a test email",
        participants=[sender, recipient]
    )
    
    sender_info = message.get_sender()
    
    assert sender_info is not None
    assert sender_info.email == "john.doe@example.com"
    assert sender_info.name == "John Doe"


def test_message_get_recipients():
    """Test getting the recipients of a message."""
    sender = CommunicationParticipant(
        participant_info=ParticipantInfo(email="john.doe@example.com", name="John Doe"),
        role=ParticipantRole.SENDER
    )
    
    recipient1 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="jane.smith@example.com", name="Jane Smith"),
        role=ParticipantRole.RECIPIENT
    )
    
    recipient2 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="bob.jones@example.com", name="Bob Jones"),
        role=ParticipantRole.CC
    )
    
    recipient3 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="alice.white@example.com", name="Alice White"),
        role=ParticipantRole.BCC
    )
    
    message = Message(
        message_id="msg001",
        message_type=MessageType.EMAIL,
        content="This is a test email",
        participants=[sender, recipient1, recipient2, recipient3]
    )
    
    # Get all recipients
    recipients = message.get_recipients(include_cc=True, include_bcc=True)
    assert len(recipients) == 3
    assert any(r.email == "jane.smith@example.com" for r in recipients)
    assert any(r.email == "bob.jones@example.com" for r in recipients)
    assert any(r.email == "alice.white@example.com" for r in recipients)
    
    # Get direct recipients and CC
    recipients = message.get_recipients(include_cc=True, include_bcc=False)
    assert len(recipients) == 2
    assert any(r.email == "jane.smith@example.com" for r in recipients)
    assert any(r.email == "bob.jones@example.com" for r in recipients)
    
    # Get only direct recipients
    recipients = message.get_recipients(include_cc=False, include_bcc=False)
    assert len(recipients) == 1
    assert recipients[0].email == "jane.smith@example.com"


def test_message_thread():
    """Test creating and managing a message thread."""
    thread = MessageThread(
        thread_id="thread001",
        subject="Test Thread"
    )
    
    assert thread.thread_id == "thread001"
    assert thread.subject == "Test Thread"
    assert len(thread.messages) == 0
    assert thread.start_date is None
    assert thread.end_date is None
    assert len(thread.participants) == 0
    
    # Create messages
    sender1 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="john.doe@example.com", name="John Doe"),
        role=ParticipantRole.SENDER
    )
    
    recipient1 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="jane.smith@example.com", name="Jane Smith"),
        role=ParticipantRole.RECIPIENT
    )
    
    message1 = Message(
        message_id="msg001",
        thread_id="thread001",
        message_type=MessageType.EMAIL,
        subject="Test Email",
        content="This is the first message",
        sent_date=datetime(2020, 1, 1, 10, 0),
        participants=[sender1, recipient1]
    )
    
    sender2 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="jane.smith@example.com", name="Jane Smith"),
        role=ParticipantRole.SENDER
    )
    
    recipient2 = CommunicationParticipant(
        participant_info=ParticipantInfo(email="john.doe@example.com", name="John Doe"),
        role=ParticipantRole.RECIPIENT
    )
    
    message2 = Message(
        message_id="msg002",
        thread_id="thread001",
        in_reply_to="msg001",
        message_type=MessageType.EMAIL,
        subject="Re: Test Email",
        content="This is the second message",
        sent_date=datetime(2020, 1, 1, 11, 0),
        participants=[sender2, recipient2]
    )
    
    # Add messages to the thread
    thread.add_message(message1)
    thread.add_message(message2)
    
    assert len(thread.messages) == 2
    assert "msg001" in thread.messages
    assert "msg002" in thread.messages
    
    # Check thread dates
    assert thread.start_date == datetime(2020, 1, 1, 10, 0)
    assert thread.end_date == datetime(2020, 1, 1, 11, 0)
    
    # Check participants
    assert len(thread.participants) == 2
    assert "john.doe@example.com" in thread.participants
    assert "jane.smith@example.com" in thread.participants
    
    # Check message sequence
    sequence = thread.get_message_sequence()
    assert len(sequence) == 2
    assert sequence[0].message_id == "msg001"
    assert sequence[1].message_id == "msg002"
    
    # Check participant roles
    roles = thread.get_participant_roles()
    assert len(roles) == 2
    assert ParticipantRole.SENDER in roles["john.doe@example.com"]
    assert ParticipantRole.RECIPIENT in roles["john.doe@example.com"]
    assert ParticipantRole.SENDER in roles["jane.smith@example.com"]
    assert ParticipantRole.RECIPIENT in roles["jane.smith@example.com"]


def test_communication_graph():
    """Test creating and managing a communication graph."""
    graph = CommunicationGraph()
    
    assert len(graph.participants) == 0
    assert len(graph.adjacency_list) == 0
    assert len(graph.threads) == 0
    
    # Create messages
    sender1 = ParticipantInfo(email="john.doe@example.com", name="John Doe")
    recipient1 = ParticipantInfo(email="jane.smith@example.com", name="Jane Smith")
    
    message1 = Message(
        message_id="msg001",
        thread_id="thread001",
        message_type=MessageType.EMAIL,
        content="This is the first message",
        sent_date=datetime(2020, 1, 1, 10, 0),
        participants=[
            CommunicationParticipant(participant_info=sender1, role=ParticipantRole.SENDER),
            CommunicationParticipant(participant_info=recipient1, role=ParticipantRole.RECIPIENT)
        ]
    )
    
    sender2 = ParticipantInfo(email="jane.smith@example.com", name="Jane Smith")
    recipient2 = ParticipantInfo(email="john.doe@example.com", name="John Doe")
    
    message2 = Message(
        message_id="msg002",
        thread_id="thread001",
        in_reply_to="msg001",
        message_type=MessageType.EMAIL,
        content="This is the second message",
        sent_date=datetime(2020, 1, 1, 11, 0),
        participants=[
            CommunicationParticipant(participant_info=sender2, role=ParticipantRole.SENDER),
            CommunicationParticipant(participant_info=recipient2, role=ParticipantRole.RECIPIENT)
        ]
    )
    
    # Add messages to the graph
    graph.add_message(message1)
    graph.add_message(message2)
    
    # Check participants
    assert len(graph.participants) == 2
    assert "john.doe@example.com" in graph.participants
    assert "jane.smith@example.com" in graph.participants
    
    # Check adjacency list
    assert len(graph.adjacency_list) == 2
    assert "john.doe@example.com" in graph.adjacency_list
    assert "jane.smith@example.com" in graph.adjacency_list
    assert "jane.smith@example.com" in graph.adjacency_list["john.doe@example.com"]
    assert "john.doe@example.com" in graph.adjacency_list["jane.smith@example.com"]
    
    # Check threads
    assert len(graph.threads) == 1
    assert "thread001" in graph.threads
    assert len(graph.threads["thread001"].messages) == 2
    
    # Check communication count
    count = graph.get_communication_count("john.doe@example.com", "jane.smith@example.com")
    assert count == 1
    
    count = graph.get_communication_count("jane.smith@example.com", "john.doe@example.com")
    assert count == 1
    
    # Check total communications
    total = graph.get_total_communications("john.doe@example.com")
    assert total["sent"] == 1
    assert total["received"] == 1
    assert total["total"] == 2
    
    # Check most active participants
    active = graph.get_most_active_participants()
    assert len(active) == 2
    assert active[0]["total"] == 2
    
    # Check paths
    paths = graph.find_paths("john.doe@example.com", "jane.smith@example.com")
    assert len(paths) == 1
    assert paths[0] == ["john.doe@example.com", "jane.smith@example.com"]