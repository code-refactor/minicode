from typing import List, Optional, Dict, Any, Union

from common.core import BaseService, InMemoryStorage
from .models import (
    Document, Section, TextBlock, ImageBlock,
    TableBlock, CodeBlock, EquationBlock, CitationBlock, JournalFormat
)
from .storage import ExportStorageInterface, InMemoryExportStorage
from .formatter import ExportFormatter


class ExportService(BaseService[Document]):
    """Service for creating and managing academic document exports."""

    def __init__(self, storage: Optional[ExportStorageInterface] = None):
        # Initialize with document storage for base service
        doc_storage = InMemoryStorage(Document) if storage is None else None
        super().__init__(doc_storage) if doc_storage else None
        
        # Use provided storage or default
        self.storage = storage or InMemoryExportStorage()
        self.formatter = ExportFormatter()

    def create_document(
        self,
        title: str,
        authors: Optional[List[str]] = None,
        affiliations: Optional[List[str]] = None,
        corresponding_email: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        format: JournalFormat = JournalFormat.DEFAULT,
    ) -> Document:
        """Create a new academic document."""
        document = Document(
            title=title,
            authors=authors or [],
            affiliations=affiliations or [],
            corresponding_email=corresponding_email,
            keywords=keywords or [],
            format=format,
        )
        return self.storage.create_document(document)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by its ID."""
        return self.storage.get_document(document_id)

    def update_document(self, document: Document) -> Document:
        """Update an existing document."""
        return self.storage.update_document(document)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document by its ID."""
        return self.storage.delete_document(document_id)

    def add_section(
        self,
        document_id: str,
        title: str,
        order: Optional[int] = None
    ) -> Optional[Section]:
        """Add a new section to a document."""
        document = self.storage.get_document(document_id)
        if not document:
            return None

        section = Section(
            title=title,
            content_blocks=[]
        )

        if order is not None and 0 <= order < len(document.sections):
            document.sections.insert(order, section)
        else:
            document.sections.append(section)

        self.storage.update_document(document)
        return section

    def add_content_block(
        self,
        document_id: str,
        section_index: int,
        block: Any,
        order: Optional[int] = None
    ) -> Optional[Any]:
        """Add a content block to a specific section."""
        document = self.storage.get_document(document_id)
        if not document or section_index >= len(document.sections):
            return None

        section = document.sections[section_index]

        if order is not None and 0 <= order < len(section.content_blocks):
            section.content_blocks.insert(order, block)
        else:
            section.content_blocks.append(block)

        self.storage.update_document(document)
        return block

    def create_text_block(self, content: str) -> TextBlock:
        """Create a text content block."""
        return TextBlock(content=content)

    def create_image_block(
        self,
        path: str,
        caption: Optional[str] = None,
        width: Optional[int] = None
    ) -> ImageBlock:
        """Create an image content block."""
        return ImageBlock(path=path, caption=caption, width=width)

    def create_table_block(
        self,
        data: List[List[str]],
        headers: List[str],
        caption: Optional[str] = None
    ) -> TableBlock:
        """Create a table content block."""
        return TableBlock(headers=headers, data=data, caption=caption)

    def create_code_block(
        self,
        code: str,
        language: str = "python"
    ) -> CodeBlock:
        """Create a code content block."""
        return CodeBlock(code=code, language=language)

    def create_equation_block(self, equation: str) -> EquationBlock:
        """Create an equation content block."""
        return EquationBlock(equation=equation)

    def create_citation_block(
        self,
        reference_ids: List[Union[str, str]],
        context: Optional[str] = None
    ) -> CitationBlock:
        """Create a citation content block."""
        # Convert UUIDs to strings if necessary
        str_reference_ids = [str(ref_id) for ref_id in reference_ids]
        return CitationBlock(reference_ids=str_reference_ids, context=context)

    def generate_markdown(self, document_id: str) -> str:
        """Generate markdown for an academic document."""
        document = self.storage.get_document(document_id)
        if not document:
            return ""

        return self.formatter.format_document(document)

    def export_to_file(self, document_id: str, file_path: str) -> bool:
        """Export document as markdown to a file."""
        markdown = self.generate_markdown(document_id)
        if not markdown:
            return False

        try:
            with open(file_path, 'w') as f:
                f.write(markdown)
            return True
        except Exception:
            return False