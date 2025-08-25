"""Pytest fixtures for testing the legal discovery interpreter."""

import os
import json
import datetime
from pathlib import Path
import pytest
from typing import Dict, List, Set, Tuple, Any


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample legal documents for testing."""
    return [
        {
            "id": "doc001",
            "title": "Contract Agreement",
            "content": "This agreement is made between Party A and Party B. Both parties agree to the terms outlined in Sections 1-5. The liability clause mentioned in Section 3 shall be binding.",
            "metadata": {
                "type": "contract",
                "date": "2020-05-15T10:30:00",
                "author": "Legal Department",
                "parties": ["Company X", "Company Y"]
            }
        },
        {
            "id": "doc002",
            "title": "Meeting Minutes",
            "content": "The board convened on July 10, 2020 to discuss the pending litigation. The CEO expressed concerns about the statute of limitations. The general counsel advised on next steps.",
            "metadata": {
                "type": "minutes",
                "date": "2020-07-10T14:00:00",
                "author": "Secretary",
                "participants": ["CEO", "General Counsel", "Board Members"]
            }
        },
        {
            "id": "doc003",
            "title": "Legal Memorandum",
            "content": "CONFIDENTIAL: ATTORNEY-CLIENT PRIVILEGED COMMUNICATION. This memorandum analyzes the legal risks associated with the proposed merger. Based on our research, we recommend proceeding with caution.",
            "metadata": {
                "type": "memorandum",
                "date": "2020-09-22T09:15:00",
                "author": "External Counsel",
                "recipients": ["General Counsel", "CEO"]
            }
        }
    ]


@pytest.fixture
def sample_emails() -> List[Dict[str, Any]]:
    """Sample email communications for testing."""
    return [
        {
            "id": "email001",
            "from": "alice@companyA.com",
            "to": ["bob@companyB.com"],
            "cc": ["carol@companyA.com"],
            "subject": "Re: Proposed Settlement Terms",
            "body": "Bob, I've reviewed the settlement terms you proposed. Let's schedule a call to discuss the liability limits. - Alice",
            "date": "2021-03-15T10:23:45",
            "thread_id": "thread123"
        },
        {
            "id": "email002",
            "from": "bob@companyB.com",
            "to": ["alice@companyA.com"],
            "cc": ["carol@companyA.com", "dave@companyB.com"],
            "subject": "Re: Re: Proposed Settlement Terms",
            "body": "Alice, I agree we should discuss. How about tomorrow at 2pm? - Bob",
            "date": "2021-03-15T11:05:22",
            "thread_id": "thread123",
            "in_reply_to": "email001"
        },
        {
            "id": "email003",
            "from": "john.lawyer@lawfirm.com",
            "to": ["alice@companyA.com"],
            "cc": [],
            "subject": "Legal Advice on Contract",
            "body": "Alice, As your legal counsel, my advice is to reject the current proposal. The indemnification clause is too broad. Let's discuss alternative language. - John Smith, Esq.",
            "date": "2021-03-16T09:30:10",
            "thread_id": "thread456"
        }
    ]


@pytest.fixture
def legal_ontology() -> Dict[str, Set[str]]:
    """Sample legal ontology mapping terms to related concepts."""
    return {
        "liability": {"indemnification", "responsibility", "obligation", "accountability", "duty", "fault"},
        "settlement": {"resolution", "agreement", "compromise", "arrangement", "accord", "negotiation"},
        "statute of limitations": {"time limit", "time bar", "limitation period", "prescription period", "expiry date"},
        "litigation": {"lawsuit", "legal action", "court case", "legal proceeding", "suit", "case"},
        "privilege": {"attorney-client privilege", "legal professional privilege", "confidential communication", "work product"}
    }


@pytest.fixture
def legal_timeframes() -> Dict[str, Dict[str, Any]]:
    """Sample legal timeframes for testing temporal filtering."""
    return {
        "standard_contract_limitations": {
            "jurisdiction": "NY",
            "period": {"years": 6},
            "description": "New York statute of limitations for written contracts"
        },
        "securities_litigation": {
            "jurisdiction": "Federal",
            "period": {"years": 5},
            "description": "Federal securities fraud claims limitation"
        },
        "employment_discrimination": {
            "jurisdiction": "Federal",
            "period": {"days": 300},
            "description": "EEOC filing deadline from date of incident"
        },
        "ipo_quiet_period": {
            "period": {"days": 40},
            "description": "SEC-mandated quiet period following an IPO"
        }
    }


@pytest.fixture
def privilege_indicators() -> Dict[str, float]:
    """Sample privilege indicators and their confidence weights."""
    return {
        "attorney-client privilege": 0.9,
        "privileged and confidential": 0.85,
        "legal advice": 0.7,
        "work product": 0.8,
        "prepared at the request of counsel": 0.75,
        "confidential legal communication": 0.85,
        "do not forward": 0.5
    }


@pytest.fixture
def attorneys_list() -> List[Dict[str, Any]]:
    """Sample list of attorneys for privilege detection testing."""
    return [
        {"email": "john.lawyer@lawfirm.com", "name": "John Smith", "role": "External Counsel"},
        {"email": "jane.doe@lawfirm.com", "name": "Jane Doe", "role": "External Counsel"},
        {"email": "general.counsel@companyA.com", "name": "Sarah Johnson", "role": "General Counsel"},
        {"email": "legal.department@companyB.com", "name": "Legal Department", "role": "Internal Legal"}
    ]