"""Citation formatting utilities for ResearchBrain."""

from typing import List, Optional, Union

from researchbrain.core.models import Citation, CitationFormat


def format_author_list(authors: List[str], format: CitationFormat) -> str:
    """Format a list of authors according to the specified citation style.
    
    Args:
        authors: List of author names.
        format: Citation format to use.
        
    Returns:
        Formatted author list string.
    """
    if not authors:
        return ""
    
    if format == CitationFormat.APA:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        else:
            return f"{', '.join(authors[:-1])}, & {authors[-1]}"
            
    elif format == CitationFormat.MLA:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        else:
            return f"{authors[0]} et al."
            
    elif format == CitationFormat.CHICAGO:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) <= 3:
            return f"{', '.join(authors[:-1])}, and {authors[-1]}"
        else:
            return f"{authors[0]} et al."
            
    elif format == CitationFormat.HARVARD:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        elif len(authors) == 3:
            return f"{authors[0]}, {authors[1]} and {authors[2]}"
        else:
            return f"{authors[0]} et al."
            
    elif format == CitationFormat.IEEE:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        else:
            return f"{authors[0]} et al."
            
    elif format == CitationFormat.VANCOUVER:
        return ", ".join(authors)
        
    # Default formatter (for BibTeX and RIS or unknown formats)
    return ", ".join(authors)


def format_citation(citation: Citation, format: CitationFormat) -> str:
    """Format a citation according to the specified citation style.
    
    Args:
        citation: Citation object to format.
        format: Citation format to use.
        
    Returns:
        Formatted citation string.
    """
    if format == CitationFormat.BIBTEX:
        return _format_bibtex(citation)
    
    if format == CitationFormat.RIS:
        return _format_ris(citation)
    
    # For other formats, use the appropriate style formatter
    if format == CitationFormat.APA:
        return _format_apa(citation)
    elif format == CitationFormat.MLA:
        return _format_mla(citation)
    elif format == CitationFormat.CHICAGO:
        return _format_chicago(citation)
    elif format == CitationFormat.HARVARD:
        return _format_harvard(citation)
    elif format == CitationFormat.IEEE:
        return _format_ieee(citation)
    elif format == CitationFormat.VANCOUVER:
        return _format_vancouver(citation)
    
    # Default to APA if unknown format
    return _format_apa(citation)


def _format_apa(citation: Citation) -> str:
    """Format a citation in APA style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        APA formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.APA)
        result += f"{author_list}. "
    
    # Year
    if citation.year:
        result += f"({citation.year}). "
    else:
        result += "(n.d.). "
    
    # Title
    if citation.title:
        if citation.citation_type == "article":
            result += f"{citation.title}. "
        else:
            result += f"{citation.title}. "
    
    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"<em>{citation.journal}</em>"
            if citation.volume:
                result += f", {citation.volume}"
            if citation.issue:
                result += f"({citation.issue})"
            if citation.pages:
                result += f", {citation.pages}"
            result += ". "
        else:
            result += f"In <em>{citation.journal}</em>. "
    elif citation.publisher:
        result += f"{citation.publisher}. "
    
    # DOI
    if citation.doi:
        result += f"https://doi.org/{citation.doi}"
    elif citation.url:
        result += citation.url
    
    return result


def _format_mla(citation: Citation) -> str:
    """Format a citation in MLA style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        MLA formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.MLA)
        result += f"{author_list}. "
    
    # Title
    if citation.title:
        if citation.citation_type == "article":
            result += f'"{citation.title}." '
        else:
            result += f"<em>{citation.title}</em>. "

    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"<em>{citation.journal}</em>"
            if citation.volume:
                result += f", vol. {citation.volume}"
            if citation.issue:
                result += f", no. {citation.issue}"
            if citation.year:
                result += f", {citation.year}"
            else:
                result += ", n.d."
            if citation.pages:
                result += f", pp. {citation.pages}"
            result += ". "
        else:
            result += f"{citation.journal}, "
            if citation.year:
                result += f"{citation.year}. "
            else:
                result += "n.d. "
    elif citation.publisher:
        result += f"{citation.publisher}, "
        if citation.year:
            result += f"{citation.year}. "
        else:
            result += "n.d. "
    elif citation.year:
        result += f"{citation.year}. "
    else:
        result += "n.d. "
    
    # DOI/URL
    if citation.doi:
        result += f"DOI: {citation.doi}."
    elif citation.url:
        result += f"URL: {citation.url}."
    
    return result


def _format_chicago(citation: Citation) -> str:
    """Format a citation in Chicago style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        Chicago formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.CHICAGO)
        result += f"{author_list}. "
    
    # Title
    if citation.title:
        if citation.citation_type == "article":
            result += f'"{citation.title}." '
        else:
            result += f"<em>{citation.title}</em>. "
    
    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"<em>{citation.journal}</em> "
            if citation.volume:
                result += f"{citation.volume}"
                if citation.issue:
                    result += f", no. {citation.issue} "
                else:
                    result += " "
            if citation.year:
                result += f"({citation.year})"
            else:
                result += "(n.d.)"
            if citation.pages:
                result += f": {citation.pages}"
            result += ". "
        else:
            result += f"{citation.journal}, "
            if citation.year:
                result += f"{citation.year}. "
            else:
                result += "n.d. "
    elif citation.publisher:
        result += f"{citation.publisher}, "
        if citation.year:
            result += f"{citation.year}. "
        else:
            result += "n.d. "
    elif citation.year:
        result += f"{citation.year}. "
    else:
        result += "n.d. "
    
    # DOI/URL
    if citation.doi:
        result += f"https://doi.org/{citation.doi}."
    elif citation.url:
        result += f"{citation.url}."
    
    return result


def _format_harvard(citation: Citation) -> str:
    """Format a citation in Harvard style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        Harvard formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.HARVARD)
        result += f"{author_list} "
    
    # Year
    if citation.year:
        result += f"({citation.year}) "
    else:
        result += "(n.d.) "
    
    # Title
    if citation.title:
        if citation.citation_type == "article":
            result += f"'{citation.title}', "
        else:
            result += f"<em>{citation.title}</em>, "
    
    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"<em>{citation.journal}</em>"
            if citation.volume:
                result += f", {citation.volume}"
            if citation.issue:
                result += f"({citation.issue})"
            if citation.pages:
                result += f", pp. {citation.pages}"
            result += ". "
        else:
            result += f"{citation.journal}. "
    elif citation.publisher:
        result += f"{citation.publisher}. "
    
    # DOI/URL
    if citation.doi:
        result += f"Available at: https://doi.org/{citation.doi} "
    elif citation.url:
        result += f"Available at: {citation.url} "
    
    return result


def _format_ieee(citation: Citation) -> str:
    """Format a citation in IEEE style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        IEEE formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.IEEE)
        result += f"{author_list}, "
    
    # Title
    if citation.title:
        if citation.citation_type == "article":
            result += f'"{citation.title}," '
        else:
            result += f"<em>{citation.title}</em>, "
    
    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"<em>{citation.journal}</em>"
            if citation.volume:
                result += f", vol. {citation.volume}"
            if citation.issue:
                result += f", no. {citation.issue}"
            if citation.pages:
                result += f", pp. {citation.pages}"
            if citation.year:
                result += f", {citation.year}"
            result += ". "
        else:
            result += f"{citation.journal}, "
            if citation.year:
                result += f"{citation.year}. "
            else:
                result += "n.d. "
    elif citation.publisher:
        result += f"{citation.publisher}, "
        if citation.year:
            result += f"{citation.year}. "
        else:
            result += "n.d. "
    elif citation.year:
        result += f"{citation.year}. "
    
    # DOI/URL
    if citation.doi:
        result += f"doi: {citation.doi}."
    elif citation.url:
        result += f"[Online]. Available: {citation.url}."
    
    return result


def _format_vancouver(citation: Citation) -> str:
    """Format a citation in Vancouver style.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        Vancouver formatted citation string.
    """
    result = ""
    
    # Authors
    if citation.authors:
        author_list = format_author_list(citation.authors, CitationFormat.VANCOUVER)
        result += f"{author_list}. "
    
    # Title
    if citation.title:
        result += f"{citation.title}. "
    
    # Journal/Publisher
    if citation.journal:
        if citation.citation_type == "article":
            result += f"{citation.journal}. "
            if citation.year:
                result += f"{citation.year}"
            else:
                result += "n.d."
            if citation.volume:
                result += f";{citation.volume}"
            if citation.issue:
                result += f"({citation.issue})"
            if citation.pages:
                result += f":{citation.pages}"
            result += ". "
        else:
            result += f"{citation.journal}. "
            if citation.year:
                result += f"{citation.year}. "
            else:
                result += "n.d. "
    elif citation.publisher:
        result += f"{citation.publisher}; "
        if citation.year:
            result += f"{citation.year}. "
        else:
            result += "n.d. "
    elif citation.year:
        result += f"{citation.year}. "
    
    # DOI/URL
    if citation.doi:
        result += f"doi: {citation.doi}"
    elif citation.url:
        result += f"Available from: {citation.url}"
    
    return result


def _format_bibtex(citation: Citation) -> str:
    """Format a citation in BibTeX format.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        BibTeX formatted citation string.
    """
    # If we already have BibTeX data, return it
    if citation.bibtex:
        return citation.bibtex
    
    # Otherwise, generate BibTeX from the citation data
    entry_type = "article"
    if citation.citation_type == "book":
        entry_type = "book"
    elif citation.citation_type == "conference":
        entry_type = "inproceedings"
    elif citation.citation_type == "thesis":
        entry_type = "phdthesis"
    elif citation.citation_type == "report":
        entry_type = "techreport"
    elif citation.citation_type == "webpage":
        entry_type = "misc"
    elif citation.citation_type == "preprint":
        entry_type = "unpublished"
    
    # Generate a citation key
    if citation.authors and citation.year:
        first_author = citation.authors[0].split()[-1].lower()
        citation_key = f"{first_author}{citation.year}"
    else:
        citation_key = f"cite{citation.id.hex[:8]}"
    
    # Start building the BibTeX entry
    result = f"@{entry_type}{{{citation_key},\n"
    
    # Add all available fields
    if citation.title:
        result += f"  title = {{{citation.title}}},\n"
    
    if citation.authors:
        authors_str = " and ".join(citation.authors)
        result += f"  author = {{{authors_str}}},\n"
    
    if citation.year:
        result += f"  year = {{{citation.year}}},\n"
    
    if citation.journal:
        if entry_type == "article":
            result += f"  journal = {{{citation.journal}}},\n"
        elif entry_type == "inproceedings":
            result += f"  booktitle = {{{citation.journal}}},\n"
    
    if citation.volume:
        result += f"  volume = {{{citation.volume}}},\n"
    
    if citation.issue:
        result += f"  number = {{{citation.issue}}},\n"
    
    if citation.pages:
        result += f"  pages = {{{citation.pages}}},\n"
    
    if citation.publisher:
        result += f"  publisher = {{{citation.publisher}}},\n"
    
    if citation.doi:
        result += f"  doi = {{{citation.doi}}},\n"
    
    if citation.url:
        result += f"  url = {{{citation.url}}},\n"
    
    if citation.abstract:
        result += f"  abstract = {{{citation.abstract}}},\n"
    
    if citation.keywords:
        keywords_str = ", ".join(citation.keywords)
        result += f"  keywords = {{{keywords_str}}},\n"
    
    # Remove trailing comma and add closing brace
    result = result.rstrip(",\n") + "\n}"
    
    return result


def _format_ris(citation: Citation) -> str:
    """Format a citation in RIS format.
    
    Args:
        citation: Citation object to format.
        
    Returns:
        RIS formatted citation string.
    """
    result = ""
    
    # Determine TY (Type) field
    if citation.citation_type == "article":
        result += "TY  - JOUR\n"
    elif citation.citation_type == "book":
        result += "TY  - BOOK\n"
    elif citation.citation_type == "conference":
        result += "TY  - CONF\n"
    elif citation.citation_type == "thesis":
        result += "TY  - THES\n"
    elif citation.citation_type == "report":
        result += "TY  - RPRT\n"
    elif citation.citation_type == "webpage":
        result += "TY  - ELEC\n"
    elif citation.citation_type == "preprint":
        result += "TY  - UNPB\n"
    else:
        result += "TY  - GEN\n"
    
    # Title
    if citation.title:
        result += f"TI  - {citation.title}\n"
    
    # Authors
    if citation.authors:
        for author in citation.authors:
            result += f"AU  - {author}\n"
    
    # Year
    if citation.year:
        result += f"PY  - {citation.year}\n"
    
    # Journal/Publisher
    if citation.journal:
        result += f"JO  - {citation.journal}\n"
    
    if citation.volume:
        result += f"VL  - {citation.volume}\n"
    
    if citation.issue:
        result += f"IS  - {citation.issue}\n"
    
    if citation.pages:
        # Split pages into start-end if possible
        if "-" in citation.pages:
            start, end = citation.pages.split("-", 1)
            result += f"SP  - {start}\n"
            result += f"EP  - {end}\n"
        else:
            result += f"SP  - {citation.pages}\n"
    
    if citation.publisher:
        result += f"PB  - {citation.publisher}\n"
    
    if citation.doi:
        result += f"DO  - {citation.doi}\n"
    
    if citation.url:
        result += f"UR  - {citation.url}\n"
    
    if citation.abstract:
        result += f"AB  - {citation.abstract}\n"
    
    if citation.keywords:
        for keyword in citation.keywords:
            result += f"KW  - {keyword}\n"
    
    # End record
    result += "ER  - \n"
    
    return result