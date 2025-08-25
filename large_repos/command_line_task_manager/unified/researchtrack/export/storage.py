from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any

from common.core import InMemoryStorage
from .models import (
    CitationBlock,
    CodeBlock,
    Document,
    EquationBlock,
    ImageBlock,
    JournalFormat,
    Section,
    TableBlock,
    TextBlock,
)


class ExportStorageInterface(ABC):
    """Abstract interface for export storage implementations."""

    @abstractmethod
    def create_document(self, document: Document) -> Document:
        """
        Create a new document.

        Args:
            document: The document to create

        Returns:
            Document: The created document
        """
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            Optional[Document]: The document if found, None otherwise
        """
        pass

    @abstractmethod
    def update_document(self, document: Document) -> Document:
        """
        Update an existing document.

        Args:
            document: The document with updated fields

        Returns:
            Document: The updated document
        """
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            document_id: The ID of the document to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    def list_documents(self) -> List[Document]:
        """
        List all documents.

        Returns:
            List[Document]: List of all documents
        """
        pass


class InMemoryExportStorage(ExportStorageInterface):
    """In-memory implementation of export storage using common.core."""

    def __init__(self):
        self._document_storage = InMemoryStorage(Document)

    def create_document(self, document: Document) -> Document:
        self._document_storage.create(document)
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        return self._document_storage.get(document_id)

    def update_document(self, document: Document) -> Document:
        updated = self._document_storage.update(document)
        return updated if updated else None

    def delete_document(self, document_id: str) -> bool:
        return self._document_storage.delete(document_id)

    def list_documents(self) -> List[Document]:
        return self._document_storage.list()