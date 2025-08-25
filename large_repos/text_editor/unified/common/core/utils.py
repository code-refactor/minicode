"""Utility functions for the unified text editor library."""

import re
from typing import List, Tuple, Optional, Dict, Any


def count_words(text: str) -> int:
    """Count words in text."""
    return len(re.findall(r'\b\w+\b', text))


def count_lines(text: str) -> int:
    """Count lines in text."""
    return len(text.splitlines())


def count_characters(text: str, include_spaces: bool = True) -> int:
    """Count characters in text."""
    if include_spaces:
        return len(text)
    else:
        return len(re.sub(r'\s', '', text))


def find_all_matches(text: str, pattern: str, case_sensitive: bool = False) -> List[Tuple[int, int]]:
    """Find all matches of a pattern in text."""
    flags = 0 if case_sensitive else re.IGNORECASE
    matches = []
    
    for match in re.finditer(pattern, text, flags):
        matches.append((match.start(), match.end()))
    
    return matches


def get_line_column_from_offset(text: str, offset: int) -> Tuple[int, int]:
    """Convert text offset to line and column position."""
    if offset < 0 or offset > len(text):
        raise ValueError(f"Offset {offset} out of range")
    
    lines = text[:offset].split('\n')
    line = len(lines) - 1
    column = len(lines[-1]) if lines else 0
    
    return line, column


def get_offset_from_line_column(text: str, line: int, column: int) -> int:
    """Convert line and column position to text offset."""
    lines = text.split('\n')
    
    if line < 0 or line >= len(lines):
        raise ValueError(f"Line {line} out of range")
    
    if column < 0 or column > len(lines[line]):
        raise ValueError(f"Column {column} out of range for line {line}")
    
    offset = sum(len(l) + 1 for l in lines[:line])  # +1 for newline
    offset += column
    
    return offset


def extract_sentences(text: str) -> List[str]:
    """Extract sentences from text."""
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_paragraphs(text: str) -> List[str]:
    """Extract paragraphs from text."""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]


def highlight_text(text: str, start: int, end: int, 
                  start_marker: str = ">>", end_marker: str = "<<") -> str:
    """Highlight a portion of text with markers."""
    if start < 0 or end > len(text) or start > end:
        raise ValueError("Invalid highlight range")
    
    return text[:start] + start_marker + text[start:end] + end_marker + text[end:]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def get_indent_level(line: str, tab_size: int = 4) -> int:
    """Get indentation level of a line."""
    indent = 0
    for char in line:
        if char == ' ':
            indent += 1
        elif char == '\t':
            indent += tab_size
        else:
            break
    
    return indent // tab_size  # Return indent level, not spaces


def normalize_line_endings(text: str, line_ending: str = '\n') -> str:
    """Normalize line endings in text."""
    # Replace all types of line endings with the specified one
    text = text.replace('\r\n', '\n')  # Windows
    text = text.replace('\r', '\n')    # Old Mac
    
    if line_ending != '\n':
        text = text.replace('\n', line_ending)
    
    return text


def remove_empty_lines(text: str, keep_one: bool = True) -> str:
    """Remove empty lines from text."""
    lines = text.splitlines()
    result = []
    prev_empty = False
    
    for line in lines:
        is_empty = not line.strip()
        
        if not is_empty:
            result.append(line)
            prev_empty = False
        elif keep_one and not prev_empty:
            result.append(line)
            prev_empty = True
        # else: skip this empty line
    
    return '\n'.join(result)


def wrap_text(text: str, width: int = 80, preserve_paragraphs: bool = True) -> str:
    """Wrap text to specified width."""
    if preserve_paragraphs:
        paragraphs = extract_paragraphs(text)
        wrapped_paragraphs = []
        
        for para in paragraphs:
            wrapped_paragraphs.append(_wrap_paragraph(para, width))
        
        return '\n\n'.join(wrapped_paragraphs)
    else:
        return _wrap_paragraph(text, width)


def _wrap_paragraph(text: str, width: int) -> str:
    """Wrap a single paragraph."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        
        if current_length + word_length + len(current_line) <= width:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def calculate_diff_stats(old_text: str, new_text: str) -> Dict[str, int]:
    """Calculate statistics about differences between two texts."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    old_words = count_words(old_text)
    new_words = count_words(new_text)
    
    old_chars = len(old_text)
    new_chars = len(new_text)
    
    return {
        'lines_added': max(0, len(new_lines) - len(old_lines)),
        'lines_removed': max(0, len(old_lines) - len(new_lines)),
        'words_added': max(0, new_words - old_words),
        'words_removed': max(0, old_words - new_words),
        'chars_added': max(0, new_chars - old_chars),
        'chars_removed': max(0, old_chars - new_chars)
    }


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """Sanitize a filename by removing invalid characters."""
    # Remove invalid characters for most filesystems
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, replacement)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', replacement, filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'untitled'
    
    return filename