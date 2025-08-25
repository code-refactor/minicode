import time
from uuid import uuid4

import pytest

from researchtrack.bibliography.formatter import ReferenceFormatter
from researchtrack.bibliography.models import (
    Author,
    AuthorType,
    CitationStyle,
    Reference,
    ReferenceType,
)
from researchtrack.bibliography.service import BibliographyService
from researchtrack.bibliography.storage import InMemoryBibliographyStorage


class TestBibliographyPerformance:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryBibliographyStorage()
        self.service = BibliographyService(self.storage)
    
    def test_large_bibliography_operations(self):
        """Test performance with a large bibliography (10,000+ references)."""
        # Create a large number of references
        reference_ids = []
        
        # Create 10,000 references
        start_time = time.time()
        
        # Pre-generate some authors to reuse
        authors = []
        for i in range(1000):  # 1000 different authors
            author = self.service.create_person_author(
                first_name=f"FirstName{i}",
                last_name=f"LastName{i}",
            )
            authors.append(author)
        
        # Generate references
        for i in range(10000):
            # Select authors for this reference (1-3 authors per reference)
            ref_authors = [authors[i % 1000]]
            if i % 3 == 1:
                ref_authors.append(authors[(i + 500) % 1000])
            if i % 5 == 2:
                ref_authors.append(authors[(i + 800) % 1000])
            
            # Determine reference type
            if i % 5 == 0:
                # Create journal article
                ref_id = self.service.create_journal_article(
                    title=f"Journal Article {i}",
                    authors=ref_authors,
                    journal_name=f"Journal {i % 50}",
                    year=2000 + (i % 23),
                    volume=f"{1 + (i % 20)}",
                    issue=f"{1 + (i % 4)}",
                    pages=f"{10 * (i % 20) + 1}-{10 * (i % 20) + 10}",
                    keywords={f"keyword{i % 100}", f"category{i % 20}"},
                )
            elif i % 5 == 1:
                # Create book
                ref_id = self.service.create_book(
                    title=f"Book {i}",
                    authors=ref_authors,
                    publisher=f"Publisher {i % 20}",
                    year=2000 + (i % 23),
                    isbn=f"978-{i % 10000:04d}-{i % 100:02d}-{i % 10}",
                    keywords={f"keyword{i % 100}", f"subject{i % 30}"},
                )
            elif i % 5 == 2:
                # Create conference paper
                ref_id = self.service.create_generic_reference(
                    type=ReferenceType.CONFERENCE_PAPER,
                    title=f"Conference Paper {i}",
                    authors=ref_authors,
                    year=2000 + (i % 23),
                    conference_name=f"Conference {i % 50}",
                    conference_location=f"Location {i % 30}",
                    keywords={f"keyword{i % 100}", f"topic{i % 40}"},
                )
            elif i % 5 == 3:
                # Create report
                ref_id = self.service.create_generic_reference(
                    type=ReferenceType.REPORT,
                    title=f"Report {i}",
                    authors=ref_authors,
                    year=2000 + (i % 23),
                    publisher=f"Organization {i % 40}",
                    keywords={f"keyword{i % 100}", f"report{i % 20}"},
                )
            else:
                # Create website
                ref_id = self.service.create_generic_reference(
                    type=ReferenceType.WEBSITE,
                    title=f"Website {i}",
                    authors=ref_authors,
                    year=2000 + (i % 23),
                    url=f"https://example{i}.com",
                    keywords={f"keyword{i % 100}", f"online{i % 20}"},
                )
            
            reference_ids.append(ref_id)
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / 10000
        
        # Test search performance
        start_time = time.time()
        author_search = self.service.search_references(author_name="LastName100")
        author_search_time = time.time() - start_time
        
        start_time = time.time()
        keyword_search = self.service.search_references(keywords={"keyword50"})
        keyword_search_time = time.time() - start_time
        
        start_time = time.time()
        year_search = self.service.search_references(year=2015)
        year_search_time = time.time() - start_time
        
        # Test retrieval performance
        get_times = []
        for i in range(1000):  # Test with 1000 random references
            ref_id = reference_ids[i * 10]  # Spread across the 10,000 references
            
            start_time = time.time()
            self.service.get_reference(ref_id)
            get_times.append(time.time() - start_time)
        
        avg_get_time = sum(get_times) / len(get_times)
        
        # Test formatting performance
        format_citation_times = []
        for i in range(100):  # Test with 100 random references
            ref_id = reference_ids[i * 100]
            
            start_time = time.time()
            self.service.format_citation(ref_id, CitationStyle.APA)
            format_citation_times.append(time.time() - start_time)
        
        avg_format_time = sum(format_citation_times) / len(format_citation_times)
        
        # Test bibliography generation with many references
        start_time = time.time()
        # Create a subset of references for the bibliography generation test
        selected_refs = [self.service.get_reference(reference_ids[i * 50]) for i in range(200)]
        bibliography = ReferenceFormatter.generate_bibliography(selected_refs, CitationStyle.APA)
        bibliography_generation_time = time.time() - start_time
        
        # Assert performance metrics (adjust these based on actual performance)
        assert avg_creation_time < 0.05, f"Average reference creation took {avg_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_get_time < 0.05, f"Average reference retrieval took {avg_get_time:.6f}s, exceeding 50ms limit"
        assert author_search_time < 0.5, f"Author search took {author_search_time:.6f}s, exceeding reasonable limit"
        assert keyword_search_time < 0.5, f"Keyword search took {keyword_search_time:.6f}s, exceeding reasonable limit"
        assert year_search_time < 0.5, f"Year search took {year_search_time:.6f}s, exceeding reasonable limit"
        assert avg_format_time < 0.05, f"Average citation formatting took {avg_format_time:.6f}s, exceeding 50ms limit"
        assert bibliography_generation_time < 3.0, f"Bibliography generation took {bibliography_generation_time:.6f}s, exceeding 3s limit"
    
    def test_task_reference_link_performance(self):
        """Test performance with many task-reference links."""
        # Create references and tasks
        reference_ids = []
        task_ids = []
        
        # Create 1000 references
        for i in range(1000):
            author = self.service.create_person_author(
                first_name=f"Author{i}",
                last_name=f"LastName{i}",
            )
            
            ref_id = self.service.create_journal_article(
                title=f"Article {i}",
                authors=[author],
                journal_name=f"Journal {i % 50}",
                year=2010 + (i % 13),
            )
            
            reference_ids.append(ref_id)
        
        # Create 500 task IDs
        for i in range(500):
            task_ids.append(uuid4())
        
        # Create links (many-to-many relationship)
        link_ids = []
        
        start_time = time.time()
        
        # Each task has 5-10 references
        for i, task_id in enumerate(task_ids):
            # Determine how many references for this task
            num_refs = 5 + (i % 6)
            
            for j in range(num_refs):
                # Pick a reference (ensure some overlap between tasks)
                ref_index = (i * 17 + j * 23) % 1000  # Use primes for better distribution
                ref_id = reference_ids[ref_index]
                
                # Create the link
                link_id = self.service.link_task_to_reference(
                    task_id=task_id,
                    reference_id=ref_id,
                    relevance=f"Relevance description {i}-{j}",
                )
                
                link_ids.append(link_id)
        
        link_creation_time = time.time() - start_time
        avg_link_creation_time = link_creation_time / len(link_ids)
        
        # Test getting references by task
        get_refs_times = []
        for i in range(100):  # Test with 100 random tasks
            task_id = task_ids[i * 5]
            
            start_time = time.time()
            refs = self.service.get_references_by_task(task_id)
            get_refs_times.append(time.time() - start_time)
        
        avg_get_refs_time = sum(get_refs_times) / len(get_refs_times)
        
        # Test getting tasks by reference
        get_tasks_times = []
        for i in range(100):  # Test with 100 random references
            ref_id = reference_ids[i * 10]
            
            start_time = time.time()
            tasks = self.service.get_tasks_by_reference(ref_id)
            get_tasks_times.append(time.time() - start_time)
        
        avg_get_tasks_time = sum(get_tasks_times) / len(get_tasks_times)
        
        # Test generating bibliographies for tasks
        bibliography_times = []
        for i in range(20):  # Test with 20 random tasks
            task_id = task_ids[i * 25]
            
            start_time = time.time()
            bibliography = self.service.generate_task_bibliography(task_id, CitationStyle.APA)
            bibliography_times.append(time.time() - start_time)
        
        avg_bibliography_time = sum(bibliography_times) / len(bibliography_times)
        
        # Assert performance metrics
        assert avg_link_creation_time < 0.05, f"Average link creation took {avg_link_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_get_refs_time < 0.05, f"Average get references by task took {avg_get_refs_time:.6f}s, exceeding 50ms limit"
        assert avg_get_tasks_time < 0.05, f"Average get tasks by reference took {avg_get_tasks_time:.6f}s, exceeding 50ms limit"
        assert avg_bibliography_time < 0.2, f"Average task bibliography generation took {avg_bibliography_time:.6f}s, exceeding reasonable limit"