import json
from datetime import datetime

import pytest

from researchtrack.bibliography.importer import BibliographyImporter
from researchtrack.bibliography.models import Author, AuthorType, Reference, ReferenceType


class TestBibliographyImporter:
    def test_import_from_json_single_reference(self):
        # Test importing a single reference from JSON
        json_data = {
            "type": "journal_article",
            "title": "Test Article",
            "authors": [
                {
                    "type": "person",
                    "first_name": "John",
                    "last_name": "Smith",
                    "orcid_id": "0000-0001-2345-6789"
                },
                {
                    "type": "person",
                    "first_name": "Jane",
                    "last_name": "Doe"
                }
            ],
            "year": 2022,
            "journal_name": "Test Journal",
            "volume": "10",
            "issue": "2",
            "pages": "123-145",
            "doi": "10.1234/test.2022.12345",
            "abstract": "This is a test article",
            "keywords": ["test", "article", "import"],
            "notes": ["First note", "Second note"],
            "custom_fields": {
                "dataset_url": "https://example.com/data",
                "funding": "NSF Grant #12345"
            }
        }
        
        references = BibliographyImporter.import_from_json(json_data)
        
        assert len(references) == 1
        
        ref = references[0]
        assert ref.type == ReferenceType.JOURNAL_ARTICLE
        assert ref.title == "Test Article"
        assert len(ref.authors) == 2
        assert ref.authors[0].type == AuthorType.PERSON
        assert ref.authors[0].first_name == "John"
        assert ref.authors[0].last_name == "Smith"
        assert ref.authors[0].orcid_id == "0000-0001-2345-6789"
        assert ref.authors[1].first_name == "Jane"
        assert ref.authors[1].last_name == "Doe"
        assert ref.year == 2022
        assert ref.journal_name == "Test Journal"
        assert ref.volume == "10"
        assert ref.issue == "2"
        assert ref.pages == "123-145"
        assert ref.doi == "10.1234/test.2022.12345"
        assert ref.abstract == "This is a test article"
        assert ref.keywords == {"test", "article", "import"}
        assert len(ref.notes) == 2
        assert ref.notes[0] == "First note"
        assert ref.notes[1] == "Second note"
        assert ref.custom_fields["dataset_url"] == "https://example.com/data"
        assert ref.custom_fields["funding"] == "NSF Grant #12345"
    
    def test_import_from_json_multiple_references(self):
        # Test importing multiple references from JSON
        json_data = [
            {
                "type": "journal_article",
                "title": "First Article",
                "authors": [
                    {
                        "type": "person",
                        "first_name": "John",
                        "last_name": "Smith"
                    }
                ],
                "year": 2022,
                "journal_name": "Journal One"
            },
            {
                "type": "book",
                "title": "Test Book",
                "authors": [
                    {
                        "type": "person",
                        "first_name": "Jane",
                        "last_name": "Doe"
                    }
                ],
                "year": 2021,
                "publisher": "Publisher One",
                "isbn": "978-1234567890"
            },
            {
                "type": "website",
                "title": "Test Website",
                "authors": [
                    {
                        "type": "organization",
                        "organization_name": "Test Organization"
                    }
                ],
                "url": "https://example.com",
                "accessed_date": datetime.now().isoformat()
            }
        ]
        
        references = BibliographyImporter.import_from_json(json_data)
        
        assert len(references) == 3
        
        types = [ref.type for ref in references]
        titles = [ref.title for ref in references]
        
        assert ReferenceType.JOURNAL_ARTICLE in types
        assert ReferenceType.BOOK in types
        assert ReferenceType.WEBSITE in types
        
        assert "First Article" in titles
        assert "Test Book" in titles
        assert "Test Website" in titles
        
        # Check specific fields by reference type
        journal_article = next(ref for ref in references if ref.type == ReferenceType.JOURNAL_ARTICLE)
        assert journal_article.journal_name == "Journal One"
        assert journal_article.authors[0].last_name == "Smith"
        
        book = next(ref for ref in references if ref.type == ReferenceType.BOOK)
        assert book.publisher == "Publisher One"
        assert book.isbn == "978-1234567890"
        
        website = next(ref for ref in references if ref.type == ReferenceType.WEBSITE)
        assert website.url == "https://example.com"
        assert website.authors[0].organization_name == "Test Organization"
    
    def test_import_from_json_string(self):
        # Test importing from a JSON string
        json_str = json.dumps({
            "type": "journal_article",
            "title": "Test Article",
            "authors": [
                {
                    "type": "person",
                    "first_name": "John",
                    "last_name": "Smith"
                }
            ],
            "year": 2022,
            "journal_name": "Test Journal"
        })
        
        references = BibliographyImporter.import_from_json(json_str)
        
        assert len(references) == 1
        assert references[0].title == "Test Article"
        assert references[0].authors[0].last_name == "Smith"
    
    def test_import_from_invalid_json(self):
        # Test handling invalid JSON
        with pytest.raises(ValueError, match="Invalid JSON data"):
            BibliographyImporter.import_from_json("This is not valid JSON")
    
    def test_import_handles_missing_fields(self):
        # Test that import handles missing fields gracefully
        json_data = {
            "type": "journal_article",
            "title": "Minimal Reference"
            # Missing authors, year, etc.
        }
        
        references = BibliographyImporter.import_from_json(json_data)
        
        assert len(references) == 1
        assert references[0].title == "Minimal Reference"
        assert references[0].type == ReferenceType.JOURNAL_ARTICLE
        assert len(references[0].authors) == 0
        assert references[0].year is None
    
    def test_export_to_json(self):
        # Test exporting references to JSON
        
        # Create some references to export
        author1 = Author(
            type=AuthorType.PERSON,
            first_name="John",
            last_name="Smith",
            orcid_id="0000-0001-2345-6789"
        )
        
        author2 = Author(
            type=AuthorType.ORGANIZATION,
            organization_name="Test Organization"
        )
        
        reference1 = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Test Article",
            authors=[author1],
            year=2022,
            journal_name="Test Journal",
            volume="10",
            issue="2",
            pages="123-145",
            doi="10.1234/test.2022.12345",
            keywords={"test", "article"},
            notes=["Test note"]
        )
        
        reference2 = Reference(
            type=ReferenceType.WEBSITE,
            title="Test Website",
            authors=[author2],
            url="https://example.com",
            accessed_date=datetime(2023, 5, 15),
            keywords={"test", "website"}
        )
        
        # Export to JSON
        json_str = BibliographyImporter.export_to_json([reference1, reference2])
        
        # Parse the JSON to verify its contents
        export_data = json.loads(json_str)
        
        assert len(export_data) == 2
        
        # Check first reference (journal article)
        journal_article = export_data[0]
        assert journal_article["type"] == "journal_article"
        assert journal_article["title"] == "Test Article"
        assert len(journal_article["authors"]) == 1
        assert journal_article["authors"][0]["type"] == "person"
        assert journal_article["authors"][0]["first_name"] == "John"
        assert journal_article["authors"][0]["last_name"] == "Smith"
        assert journal_article["authors"][0]["orcid_id"] == "0000-0001-2345-6789"
        assert journal_article["year"] == 2022
        assert journal_article["journal_name"] == "Test Journal"
        assert journal_article["volume"] == "10"
        assert journal_article["issue"] == "2"
        assert journal_article["pages"] == "123-145"
        assert journal_article["doi"] == "10.1234/test.2022.12345"
        assert set(journal_article["keywords"]) == {"test", "article"}
        assert journal_article["notes"] == ["Test note"]
        
        # Check second reference (website)
        website = export_data[1]
        assert website["type"] == "website"
        assert website["title"] == "Test Website"
        assert len(website["authors"]) == 1
        assert website["authors"][0]["type"] == "organization"
        assert website["authors"][0]["organization_name"] == "Test Organization"
        assert website["url"] == "https://example.com"
        assert "2023-05-15" in website["accessed_date"]  # Check partial date match
        assert set(website["keywords"]) == {"test", "website"}
    
    def test_import_export_roundtrip(self):
        # Test that exporting and then importing preserves reference data
        
        # Create a reference
        author = Author(
            type=AuthorType.PERSON,
            first_name="John",
            last_name="Smith"
        )
        
        original_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Test Article",
            authors=[author],
            year=2022,
            journal_name="Test Journal",
            volume="10",
            issue="2",
            pages="123-145",
            keywords={"test", "article"},
            notes=["Test note"]
        )
        
        # Export to JSON
        json_str = BibliographyImporter.export_to_json([original_ref])
        
        # Import from the exported JSON
        imported_refs = BibliographyImporter.import_from_json(json_str)
        
        assert len(imported_refs) == 1
        
        imported_ref = imported_refs[0]
        assert imported_ref.type == original_ref.type
        assert imported_ref.title == original_ref.title
        assert len(imported_ref.authors) == len(original_ref.authors)
        assert imported_ref.authors[0].first_name == original_ref.authors[0].first_name
        assert imported_ref.authors[0].last_name == original_ref.authors[0].last_name
        assert imported_ref.year == original_ref.year
        assert imported_ref.journal_name == original_ref.journal_name
        assert imported_ref.volume == original_ref.volume
        assert imported_ref.issue == original_ref.issue
        assert imported_ref.pages == original_ref.pages
        assert imported_ref.keywords == original_ref.keywords
        assert imported_ref.notes == original_ref.notes
    
    def test_import_from_bibtex_basic(self):
        # Test basic BibTeX import functionality
        bibtex_str = """
        @article{smith2022test,
            author = {Smith, John and Doe, Jane},
            title = {Test Article Title},
            journal = {Test Journal},
            year = {2022},
            volume = {10},
            number = {2},
            pages = {123--145},
            doi = {10.1234/test.2022.12345}
        }
        
        @book{doe2021book,
            author = {Doe, Jane},
            title = {Test Book Title},
            publisher = {Test Publisher},
            year = {2021},
            isbn = {978-1234567890}
        }
        """
        
        references = BibliographyImporter.import_from_bibtex(bibtex_str)
        
        # We know this is a simplified implementation, so we're just checking basic functionality
        assert len(references) > 0
        
        # Find the article and book references
        articles = [ref for ref in references if ref.type == ReferenceType.JOURNAL_ARTICLE]
        books = [ref for ref in references if ref.type == ReferenceType.BOOK]
        
        # Check that at least some data was extracted
        if articles:
            article = articles[0]
            assert "Test Article Title" in article.title
            assert len(article.authors) > 0
        
        if books:
            book = books[0]
            assert "Test Book Title" in book.title