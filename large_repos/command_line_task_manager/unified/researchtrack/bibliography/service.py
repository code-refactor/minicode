from datetime import datetime
from typing import Dict, List, Optional, Set, Union

from common.core import BaseService
from .models import Author, AuthorType, Reference, ReferenceType, TaskReferenceLink, CitationStyle
from .storage import BibliographyStorageInterface
from .formatter import format_citation, ReferenceFormatter


class BibliographyService(BaseService[Reference]):
    """Service for managing bibliographic references."""
    
    def __init__(self, storage: BibliographyStorageInterface):
        """
        Initialize the bibliography service.
        
        Args:
            storage: The storage implementation to use
        """
        # Initialize BaseService with the reference storage
        super().__init__(storage._reference_storage)
        self._storage = storage
    
    # Reference operations
    
    def create_reference(
        self,
        title: str,
        type: ReferenceType = ReferenceType.JOURNAL_ARTICLE,
        authors: Optional[List[Union[str, Author]]] = None,
        year: Optional[int] = None,
        journal_name: Optional[str] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None,
        publisher: Optional[str] = None,
        isbn: Optional[str] = None,
        url: Optional[str] = None,
        abstract: Optional[str] = None,
        keywords: Optional[Set[str]] = None,
        venue: Optional[str] = None,
    ) -> Reference:
        """
        Create a new bibliographic reference.
        
        Args:
            title: The title of the work
            type: The type of reference
            authors: List of authors (strings or Author objects)
            year: Publication year
            journal_name: Name of the journal (for articles)
            volume: Volume number
            issue: Issue number
            pages: Page range
            doi: Digital Object Identifier
            publisher: Publisher name
            isbn: ISBN number
            url: URL for online resources
            abstract: Abstract or summary
            keywords: Set of keywords
            venue: Alternative name for journal_name
            
        Returns:
            Reference: The created reference
        """
        # Use venue as journal_name if journal_name is not provided
        if journal_name is None and venue is not None:
            journal_name = venue
        # Process authors
        author_objects = []
        if authors:
            for author in authors:
                if isinstance(author, Author):
                    author_objects.append(author)
                elif isinstance(author, str):
                    # Parse author string (Last, First or First Last)
                    parts = author.split(",")
                    if len(parts) > 1:
                        last_name = parts[0].strip()
                        first_name = parts[1].strip()
                    else:
                        name_parts = author.strip().split()
                        if len(name_parts) > 1:
                            first_name = " ".join(name_parts[:-1])
                            last_name = name_parts[-1]
                        else:
                            first_name = ""
                            last_name = author.strip()
                    
                    author_objects.append(Author(
                        type=AuthorType.PERSON,
                        first_name=first_name,
                        last_name=last_name
                    ))
        
        # Create the reference
        # Use venue parameter as journal_name if provided
        actual_journal_name = venue if venue is not None else journal_name
        
        reference = Reference(
            type=type,
            title=title,
            authors=author_objects,
            year=year,
            journal_name=actual_journal_name,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            publisher=publisher,
            isbn=isbn,
            url=url,
            abstract=abstract,
            keywords=keywords or set(),
        )
        
        # Save the reference
        self._storage.create_reference(reference)
        
        return reference
    
    def get_reference(self, reference_id: str) -> Optional[Reference]:
        """
        Retrieve a reference by ID.
        
        Args:
            reference_id: The ID of the reference to retrieve
            
        Returns:
            Optional[Reference]: The reference if found, None otherwise
        """
        return self._storage.get_reference(reference_id)
    
    def update_reference(
        self,
        reference_id: str,
        title: Optional[str] = None,
        year: Optional[int] = None,
        journal_name: Optional[str] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None,
        publisher: Optional[str] = None,
        isbn: Optional[str] = None,
        url: Optional[str] = None,
        abstract: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> bool:
        """
        Update an existing reference.
        
        Args:
            reference_id: The ID of the reference to update
            title: New title
            year: New year
            journal_name: New journal name
            volume: New volume
            issue: New issue
            pages: New pages
            doi: New DOI
            publisher: New publisher
            isbn: New ISBN
            url: New URL
            abstract: New abstract
            venue: Alternative name for journal_name
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        # Use venue as journal_name if journal_name is not provided
        if journal_name is None and venue is not None:
            journal_name = venue
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if year is not None:
            update_data["year"] = year
        if journal_name is not None:
            update_data["journal_name"] = journal_name
        if volume is not None:
            update_data["volume"] = volume
        if issue is not None:
            update_data["issue"] = issue
        if pages is not None:
            update_data["pages"] = pages
        if doi is not None:
            update_data["doi"] = doi
        if publisher is not None:
            update_data["publisher"] = publisher
        if isbn is not None:
            update_data["isbn"] = isbn
        if url is not None:
            update_data["url"] = url
        if abstract is not None:
            update_data["abstract"] = abstract
        
        reference = reference.update_fields(**update_data)
        return self._storage.update_reference(reference)
    
    def delete_reference(self, reference_id: str) -> bool:
        """
        Delete a reference by ID.
        
        Args:
            reference_id: The ID of the reference to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_reference(reference_id)
    
    def add_author_to_reference(
        self, 
        reference_id: str, 
        first_name_or_author: Union[str, Author, None] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        type: AuthorType = AuthorType.PERSON,
        orcid_id: Optional[str] = None,
    ) -> bool:
        """
        Add an author to a reference. Supports adding an author object directly 
        or creating a new author from provided parameters.
        
        Args:
            reference_id: The ID of the reference
            first_name_or_author: Either the first name of the author (string) or an Author object
            last_name: Last name of the author (for persons)
            organization_name: Name of the organization (for organizations)
            type: Type of author (person or organization)
            orcid_id: ORCID identifier for the author
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist or author information is invalid
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        # If an Author object is provided directly
        if isinstance(first_name_or_author, Author):
            author = first_name_or_author
        else:
            # Create a new Author object from the provided parameters
            first_name = first_name_or_author
            
            # Validate author information
            if type == AuthorType.PERSON and not (first_name or last_name):
                raise ValueError("First name or last name must be provided for person authors")
            if type == AuthorType.ORGANIZATION and not organization_name:
                raise ValueError("Organization name must be provided for organization authors")
            
            # Create author
            author = Author(
                type=type,
                first_name=first_name,
                last_name=last_name,
                organization_name=organization_name,
                orcid_id=orcid_id,
            )
        
        reference.add_author(author)
        return self._storage.update_reference(reference)
    
    def remove_author_from_reference(self, reference_id: str, author_id: str) -> bool:
        """
        Remove an author from a reference.
        
        Args:
            reference_id: The ID of the reference
            author_id: The ID of the author to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        result = reference.remove_author(author_id)
        if result:
            return self._storage.update_reference(reference)
        return False
    
    def add_keyword_to_reference(self, reference_id: str, keyword: str) -> bool:
        """
        Add a keyword to a reference.
        
        Args:
            reference_id: The ID of the reference
            keyword: The keyword to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        reference.add_keyword(keyword)
        return self._storage.update_reference(reference)
    
    def remove_keyword_from_reference(self, reference_id: str, keyword: str) -> bool:
        """
        Remove a keyword from a reference.
        
        Args:
            reference_id: The ID of the reference
            keyword: The keyword to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        reference.remove_keyword(keyword)
        return self._storage.update_reference(reference)
    
    def add_note_to_reference(self, reference_id: str, note: str) -> bool:
        """
        Add a note to a reference.
        
        Args:
            reference_id: The ID of the reference
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        reference.add_note(note)
        return self._storage.update_reference(reference)
    
    def search_references(
        self, 
        author_name: Optional[str] = None, 
        year: Optional[int] = None,
        keywords: Optional[Set[str]] = None,
    ) -> List[Reference]:
        """
        Search for references with optional filtering.
        
        Args:
            author_name: Filter by author name (partial match)
            year: Filter by publication year
            keywords: Filter by keywords (references must have all specified keywords)
            
        Returns:
            List[Reference]: List of references matching the criteria
        """
        return self._storage.list_references(
            author_name=author_name,
            year=year,
            keywords=keywords,
        )
    
    # Task-Reference link operations
    
    def link_task_to_reference(
        self, 
        task_id: str, 
        reference_id: str,
        relevance: Optional[str] = None,
    ) -> str:
        """
        Link a task to a reference.
        
        Args:
            task_id: The ID of the task
            reference_id: The ID of the reference
            relevance: Description of the relevance of this reference to the task
            
        Returns:
            str: The ID of the created link
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        # Check if link already exists
        existing_links = self._storage.get_references_for_task(task_id)
        for ref in existing_links:
            if ref.id == reference_id:
                # Link already exists - return empty string to indicate existing link
                return ""
        
        # Create the link
        link = TaskReferenceLink(
            task_id=task_id,
            reference_id=reference_id,
            relevance=relevance,
        )
        
        return self._storage.create_task_reference_link(link)
    
    def unlink_task_from_reference(self, task_id: str, reference_id: str) -> bool:
        """
        Remove a link between a task and a reference.
        
        Args:
            task_id: The ID of the task
            reference_id: The ID of the reference
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the link using the new storage interface
        links = self._storage.get_links_by_task(task_id)
        matching_links = [link for link in links if link.reference_id == reference_id]
        
        if not matching_links:
            return False
        
        # Delete the link
        return self._storage.delete_task_reference_link(matching_links[0].id)
    
    def get_references_for_task(self, task_id: str) -> List[Reference]:
        """
        Get all references associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[Reference]: List of associated references
        """
        return self._storage.get_references_for_task(task_id)
    
    def get_tasks_for_reference(self, reference_id: str) -> List[str]:
        """
        Get all task IDs associated with a reference.
        
        Args:
            reference_id: The ID of the reference
            
        Returns:
            List[str]: List of associated task IDs
        """
        return self._storage.get_tasks_for_reference(reference_id)
    
    def add_note_to_link(self, task_id: str, reference_id: str, note: str) -> bool:
        """
        Add a note to the link between a task and a reference.
        
        Args:
            task_id: The ID of the task
            reference_id: The ID of the reference
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the link using the new storage interface
        links = self._storage.get_links_by_task(task_id)
        matching_links = [link for link in links if link.reference_id == reference_id]
        
        if not matching_links:
            return False
        
        link = matching_links[0]
        link.add_note(note)
        return self._storage.update_task_reference_link(link)
    
    def format_citation(self, reference_id: str, style: CitationStyle = CitationStyle.APA) -> str:
        """
        Format a reference in a specific citation style.
        
        Args:
            reference_id: The ID of the reference to format
            style: The citation style to use
            
        Returns:
            str: Formatted citation string
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        return format_citation(reference, style)
    
    def format_citations(self, reference_ids: List[str], style: CitationStyle = CitationStyle.APA) -> List[str]:
        """
        Format multiple references in a specific citation style.
        
        Args:
            reference_ids: The IDs of the references to format
            style: The citation style to use
            
        Returns:
            List[str]: List of formatted citation strings
        """
        citations = []
        for ref_id in reference_ids:
            reference = self._storage.get_reference(ref_id)
            if reference:
                citations.append(format_citation(reference, style))
        
        return citations
    
    def format_bibliography(self, reference_ids: List[str], style: CitationStyle = CitationStyle.APA) -> str:
        """
        Format a complete bibliography in a specific citation style.
        
        Args:
            reference_ids: The IDs of the references to include
            style: The citation style to use
            
        Returns:
            str: Formatted bibliography
        """
        citations = self.format_citations(reference_ids, style)
        return "\n\n".join(citations)
        
    def create_person_author(
        self,
        first_name: str,
        last_name: str,
        orcid_id: Optional[str] = None,
    ) -> Author:
        """
        Create a person author.
        
        Args:
            first_name: The first name of the author
            last_name: The last name of the author
            orcid_id: The ORCID identifier for the author
            
        Returns:
            Author: The created author object
        """
        return Author(
            type=AuthorType.PERSON,
            first_name=first_name,
            last_name=last_name,
            orcid_id=orcid_id,
        )
    
    def create_organization_author(
        self,
        organization_name: str,
    ) -> Author:
        """
        Create an organization author.
        
        Args:
            organization_name: The name of the organization
            
        Returns:
            Author: The created author object
        """
        return Author(
            type=AuthorType.ORGANIZATION,
            organization_name=organization_name,
        )
    
    def create_journal_article(
        self,
        title: str,
        authors: List[Author],
        journal_name: str,
        year: Optional[int] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None,
        abstract: Optional[str] = None,
        keywords: Optional[Set[str]] = None,
    ) -> str:
        """
        Create a journal article reference.
        
        Args:
            title: The title of the article
            authors: The authors of the article
            journal_name: The name of the journal
            year: The publication year
            volume: The volume number
            issue: The issue number
            pages: The page range
            doi: The DOI (Digital Object Identifier)
            abstract: The abstract of the article
            keywords: Keywords associated with the article
            
        Returns:
            str: The ID of the created reference
        """
        reference = self.create_reference(
            title=title,
            type=ReferenceType.JOURNAL_ARTICLE,
            authors=authors,
            year=year,
            journal_name=journal_name,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            abstract=abstract,
            keywords=keywords,
        )
        
        return reference.id
    
    def create_book(
        self,
        title: str,
        authors: List[Author],
        publisher: str,
        year: Optional[int] = None,
        isbn: Optional[str] = None,
        edition: Optional[str] = None,
        abstract: Optional[str] = None,
        keywords: Optional[Set[str]] = None,
    ) -> str:
        """
        Create a book reference.
        
        Args:
            title: The title of the book
            authors: The authors of the book
            publisher: The publisher of the book
            year: The publication year
            isbn: The ISBN (International Standard Book Number)
            edition: The edition of the book
            abstract: The abstract or summary of the book
            keywords: Keywords associated with the book
            
        Returns:
            str: The ID of the created reference
        """
        reference = self.create_reference(
            title=title,
            type=ReferenceType.BOOK,
            authors=authors,
            year=year,
            publisher=publisher,
            isbn=isbn,
            abstract=abstract,
            keywords=keywords,
        )
        
        # Add edition as a custom field
        if edition:
            reference.update_custom_field("edition", edition)
            reference.edition = edition
            self._storage.update_reference(reference)
        
        return reference.id
    
    def create_website(
        self,
        title: str,
        authors: List[Author],
        url: str,
        accessed_date: Optional[datetime] = None,
        year: Optional[int] = None,
        abstract: Optional[str] = None,
        keywords: Optional[Set[str]] = None,
    ) -> str:
        """
        Create a website reference.
        
        Args:
            title: The title of the website or webpage
            authors: The authors or organization of the website
            url: The URL of the website
            accessed_date: The date when the website was accessed
            year: The publication or last updated year
            abstract: The abstract or summary of the website content
            keywords: Keywords associated with the website
            
        Returns:
            str: The ID of the created reference
        """
        reference = self.create_reference(
            title=title,
            type=ReferenceType.WEBSITE,
            authors=authors,
            year=year,
            url=url,
            abstract=abstract,
            keywords=keywords,
        )
        
        # Set accessed date
        if accessed_date:
            reference.accessed_date = accessed_date
            self._storage.update_reference(reference)
        
        return reference.id
    
    def create_generic_reference(
        self,
        type: ReferenceType,
        title: str,
        authors: List[Author],
        year: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Create a generic reference of any type.
        
        Args:
            type: The type of reference
            title: The title of the reference
            authors: The authors of the reference
            year: The publication year
            **kwargs: Additional fields specific to the reference type
            
        Returns:
            str: The ID of the created reference
        """
        # Extract standard fields that can be passed directly to create_reference
        standard_fields = {
            'journal_name': kwargs.pop('journal_name', None),
            'volume': kwargs.pop('volume', None),
            'issue': kwargs.pop('issue', None),
            'pages': kwargs.pop('pages', None),
            'doi': kwargs.pop('doi', None),
            'publisher': kwargs.pop('publisher', None),
            'isbn': kwargs.pop('isbn', None),
            'url': kwargs.pop('url', None),
            'abstract': kwargs.pop('abstract', None),
            'keywords': kwargs.pop('keywords', None),
            'venue': kwargs.pop('venue', None),
        }
        
        # Filter out None values
        standard_fields = {k: v for k, v in standard_fields.items() if v is not None}
        
        # Create the reference with standard fields
        reference = self.create_reference(
            title=title,
            type=type,
            authors=authors,
            year=year,
            **standard_fields,
        )
        
        # Add any other custom fields
        for key, value in kwargs.items():
            reference.update_custom_field(key, str(value))
            
            # Also try to set as an attribute if possible
            if hasattr(reference, key):
                setattr(reference, key, value)
        
        # Update the reference in storage
        if kwargs:
            self._storage.update_reference(reference)
        
        return reference.id
    
    def update_reference(self, reference: Reference) -> bool:
        """
        Update a reference.
        
        Args:
            reference: The reference object with updated fields
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If reference doesn't exist
        """
        existing_reference = self._storage.get_reference(reference.id)
        if not existing_reference:
            raise ValueError(f"Reference with ID {reference.id} does not exist")
        
        return self._storage.update_reference(reference)
    
    def format_in_text_citation(self, reference_id: str, style: CitationStyle = CitationStyle.APA) -> str:
        """
        Format an in-text citation for a reference.
        
        Args:
            reference_id: The ID of the reference
            style: The citation style to use
            
        Returns:
            str: Formatted in-text citation
            
        Raises:
            ValueError: If reference doesn't exist
        """
        reference = self._storage.get_reference(reference_id)
        if not reference:
            raise ValueError(f"Reference with ID {reference_id} does not exist")
        
        return ReferenceFormatter.format_in_text_citation(reference, style)
    
    def generate_task_bibliography(self, task_id: str, style: CitationStyle = CitationStyle.APA) -> str:
        """
        Generate a bibliography for all references associated with a task.
        
        Args:
            task_id: The ID of the task
            style: The citation style to use
            
        Returns:
            str: Formatted bibliography
        """
        references = self.get_references_by_task(task_id)
        
        if not references:
            return ""
        
        # Sort references alphabetically by first author's last name
        def sort_key(ref):
            if not ref.authors:
                return ""
            author = ref.authors[0]
            if author.type == AuthorType.ORGANIZATION:
                return author.organization_name or ""
            return author.last_name or ""
        
        references = sorted(references, key=sort_key)
        
        # Format each reference according to the specified style
        formatted_references = [format_citation(ref, style) for ref in references]
        
        # Join with double newlines for readability
        return "\n\n".join(formatted_references)
    
    def get_references_by_task(self, task_id: str) -> List[Reference]:
        """
        Get all references associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[Reference]: List of associated references
        """
        return self.get_references_for_task(task_id)
    
    def get_tasks_by_reference(self, reference_id: str) -> List[str]:
        """
        Get all task IDs associated with a reference.
        
        Args:
            reference_id: The ID of the reference
            
        Returns:
            List[str]: List of associated task IDs
        """
        return self.get_tasks_for_reference(reference_id)
    
    def get_task_reference_link(self, link_id: str) -> Optional[TaskReferenceLink]:
        """
        Get a task-reference link by ID.
        
        Args:
            link_id: The ID of the link
            
        Returns:
            Optional[TaskReferenceLink]: The link if found, None otherwise
        """
        return self._storage.get_task_reference_link(link_id)
    
    def update_task_reference_link(
        self,
        link_id: str,
        relevance: Optional[str] = None,
    ) -> bool:
        """
        Update a task-reference link.
        
        Args:
            link_id: The ID of the link to update
            relevance: New relevance description
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_reference_link(link_id)
        if not link:
            raise ValueError(f"Link with ID {link_id} does not exist")
        
        if relevance is not None:
            link.relevance = relevance
            
        return self._storage.update_task_reference_link(link)
    
    def delete_task_reference_link(self, link_id: str) -> bool:
        """
        Delete a task-reference link.
        
        Args:
            link_id: The ID of the link to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_task_reference_link(link_id)
    
    def add_note_to_link(self, link_id: str, note: str) -> bool:
        """
        Add a note to a task-reference link.
        
        Args:
            link_id: The ID of the link
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_reference_link(link_id)
        if not link:
            raise ValueError(f"Link with ID {link_id} does not exist")
        
        link.add_note(note)
        return self._storage.update_task_reference_link(link)