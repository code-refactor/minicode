from .formatter import ReferenceFormatter
try:
    from .importer import BibliographyImporter
except ImportError:
    BibliographyImporter = None
from .models import (
    Author,
    AuthorType,
    CitationStyle,
    Reference,
    ReferenceType,
    TaskReferenceLink,
)
from .service import BibliographyService
from .storage import BibliographyStorageInterface, InMemoryBibliographyStorage

__all__ = [
    "Author",
    "AuthorType",
    "BibliographyService",
    "BibliographyStorageInterface",
    "CitationStyle",
    "InMemoryBibliographyStorage",
    "Reference",
    "ReferenceFormatter",
    "ReferenceType",
    "TaskReferenceLink",
]

# Add BibliographyImporter only if it was successfully imported
if BibliographyImporter is not None:
    __all__.append("BibliographyImporter")