"""Proximity search functionality for document analysis."""

import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from typing import List, Dict, Set, Tuple, Optional, Any, Union
import logging


class ProximitySearchEngine:
    """Engine for performing proximity searches within documents.
    
    This engine allows for searching terms that appear within a specified
    distance of each other in documents.
    """
    
    def __init__(self, logger=None):
        """Initialize the proximity search engine.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Try to download NLTK resources if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
            except Exception as e:
                self.logger.warning(f"Could not download NLTK resources: {e}")
    
    def tokenize_document(self, content: str) -> Dict[str, Any]:
        """Tokenize a document into words, sentences, and paragraphs.
        
        Args:
            content: Document content
            
        Returns:
            Dictionary with tokenized content
        """
        try:
            # Split into paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            # Tokenize sentences and words
            sentences = sent_tokenize(content)
            words = word_tokenize(content.lower())
            
            # Create paragraph boundaries
            paragraph_boundaries = []
            current_position = 0
            for paragraph in paragraphs:
                current_position += len(paragraph)
                paragraph_boundaries.append(current_position)
            
            # Create sentence boundaries
            sentence_boundaries = []
            current_position = 0
            for sentence in sentences:
                current_position += len(sentence)
                sentence_boundaries.append(current_position)
            
            return {
                'words': words,
                'sentences': sentences,
                'paragraphs': paragraphs,
                'paragraph_boundaries': paragraph_boundaries,
                'sentence_boundaries': sentence_boundaries
            }
        except Exception as e:
            self.logger.error(f"Error tokenizing document: {e}")
            # Fallback to a basic tokenization
            words = re.findall(r'\b\w+\b', content.lower())
            return {
                'words': words,
                'sentences': [content],
                'paragraphs': [content],
                'paragraph_boundaries': [len(content)],
                'sentence_boundaries': [len(content)]
            }
    
    def calculate_word_positions(self, words: List[str]) -> Dict[str, List[int]]:
        """Calculate positions of words in a document.
        
        Args:
            words: List of words in the document
            
        Returns:
            Dictionary mapping words to their positions
        """
        positions = {}
        for i, word in enumerate(words):
            word = word.lower()
            if word not in positions:
                positions[word] = []
            positions[word].append(i)
        return positions
    
    def _within_distance(self, positions1: List[int], positions2: List[int], 
                      distance: int) -> List[Tuple[int, int]]:
        """Find pairs of positions from two lists that are within a certain distance.
        
        Args:
            positions1: First list of positions
            positions2: Second list of positions
            distance: Maximum distance between positions
            
        Returns:
            List of position pairs that are within the distance
        """
        matches = []
        for pos1 in positions1:
            for pos2 in positions2:
                if abs(pos1 - pos2) <= distance:
                    matches.append((pos1, pos2))
        return matches
    
    def _within_distance_ordered(self, positions1: List[int], positions2: List[int], 
                              distance: int) -> List[Tuple[int, int]]:
        """Find pairs of positions where the second position follows the first within a certain distance.
        
        Args:
            positions1: First list of positions
            positions2: Second list of positions
            distance: Maximum distance between positions
            
        Returns:
            List of position pairs where the second position follows the first within the distance
        """
        matches = []
        for pos1 in positions1:
            for pos2 in positions2:
                if 0 < pos2 - pos1 <= distance:
                    matches.append((pos1, pos2))
        return matches
    
    def _positions_to_unit(self, positions: List[int], unit: str, tokenized_doc: Dict[str, Any]) -> Set[int]:
        """Convert word positions to the index of the containing unit (sentence, paragraph, etc.).
        
        Args:
            positions: List of word positions
            unit: Unit type (WORDS, SENTENCES, PARAGRAPHS)
            tokenized_doc: Tokenized document
            
        Returns:
            Set of unit indices containing the word positions
        """
        if unit == "WORDS":
            return set(positions)
        
        unit_indices = set()
        
        if unit == "SENTENCES":
            boundaries = tokenized_doc['sentence_boundaries']
        elif unit == "PARAGRAPHS":
            boundaries = tokenized_doc['paragraph_boundaries']
        else:
            # Default to sentences if unit is not recognized
            boundaries = tokenized_doc['sentence_boundaries']
        
        for position in positions:
            # Find the index of the first boundary that is greater than the position
            for i, boundary in enumerate(boundaries):
                if position <= boundary:
                    unit_indices.add(i)
                    break
            else:
                # If no boundary is found, add the last unit index
                unit_indices.add(len(boundaries) - 1)
        
        return unit_indices
    
    def _terms_in_same_unit(self, term_positions: Dict[str, Set[int]], unit: str) -> bool:
        """Check if terms appear in the same unit.
        
        Args:
            term_positions: Dictionary mapping terms to sets of unit indices
            unit: Unit type (SENTENCES, PARAGRAPHS)
            
        Returns:
            True if all terms appear in at least one common unit, False otherwise
        """
        if not term_positions:
            return False
        
        # Get the intersection of all unit sets
        common_units = None
        for positions in term_positions.values():
            if common_units is None:
                common_units = set(positions)
            else:
                common_units.intersection_update(positions)
            
            if not common_units:
                return False
        
        return bool(common_units)
    
    def calculate_proximity(self, content: str, terms: List[str], 
                          distance: int, unit: str = "WORDS", 
                          ordered: bool = False) -> bool:
        """Calculate if terms appear within a specified distance of each other.
        
        Args:
            content: Document content
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            True if terms are within the specified distance, False otherwise
        """
        if not terms or not content:
            return False
        
        # Handle special case for single term
        if len(terms) == 1:
            return terms[0].lower() in content.lower()
        
        try:
            # Tokenize the document
            tokenized_doc = self.tokenize_document(content)
            word_positions = self.calculate_word_positions(tokenized_doc['words'])
            
            # For sentence and paragraph level proximity
            if unit in ("SENTENCES", "PARAGRAPHS"):
                # Find positions for each term
                term_unit_positions = {}
                for term in terms:
                    term = term.lower()
                    if term in word_positions:
                        # Convert word positions to unit positions
                        unit_positions = self._positions_to_unit(
                            word_positions[term], unit, tokenized_doc
                        )
                        term_unit_positions[term] = unit_positions
                
                # Check if all terms appear in at least one common unit
                return self._terms_in_same_unit(term_unit_positions, unit)
            
            # For word level proximity
            # Check proximity between pairs of terms
            if ordered:
                # Terms must appear in the specified order
                for i in range(len(terms) - 1):
                    term1 = terms[i].lower()
                    term2 = terms[i + 1].lower()
                    
                    if term1 not in word_positions or term2 not in word_positions:
                        return False
                    
                    # Check if terms are within distance in order
                    matches = self._within_distance_ordered(
                        word_positions[term1], word_positions[term2], distance
                    )
                    
                    if not matches:
                        return False
            else:
                # Terms can appear in any order
                # Check if any pair of terms is within distance
                for i in range(len(terms)):
                    for j in range(i + 1, len(terms)):
                        term1 = terms[i].lower()
                        term2 = terms[j].lower()
                        
                        if term1 not in word_positions or term2 not in word_positions:
                            continue
                        
                        # Check if terms are within distance
                        matches = self._within_distance(
                            word_positions[term1], word_positions[term2], distance
                        )
                        
                        if matches:
                            return True
                
                # If we get here, no pair of terms is within distance
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error calculating proximity: {e}")
            return False
    
    def find_proximity_matches(self, content: str, terms: List[str], 
                             distance: int, unit: str = "WORDS", 
                             ordered: bool = False) -> List[Dict[str, Any]]:
        """Find occurrences where terms appear within a specified distance.
        
        Args:
            content: Document content
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            List of match information dictionaries
        """
        matches = []
        
        if not terms or not content:
            return matches
        
        try:
            # Tokenize the document
            tokenized_doc = self.tokenize_document(content)
            word_positions = self.calculate_word_positions(tokenized_doc['words'])
            
            # For sentence and paragraph level proximity
            if unit in ("SENTENCES", "PARAGRAPHS"):
                # Find positions for each term
                term_unit_positions = {}
                for term in terms:
                    term = term.lower()
                    if term in word_positions:
                        # Convert word positions to unit positions
                        unit_positions = self._positions_to_unit(
                            word_positions[term], unit, tokenized_doc
                        )
                        term_unit_positions[term] = unit_positions
                
                # Find common units
                common_units = None
                for term, positions in term_unit_positions.items():
                    if common_units is None:
                        common_units = set(positions)
                    else:
                        common_units.intersection_update(positions)
                
                if common_units:
                    for unit_idx in common_units:
                        if unit == "SENTENCES" and unit_idx < len(tokenized_doc['sentences']):
                            matches.append({
                                'unit_type': unit,
                                'unit_index': unit_idx,
                                'content': tokenized_doc['sentences'][unit_idx],
                                'terms': terms
                            })
                        elif unit == "PARAGRAPHS" and unit_idx < len(tokenized_doc['paragraphs']):
                            matches.append({
                                'unit_type': unit,
                                'unit_index': unit_idx,
                                'content': tokenized_doc['paragraphs'][unit_idx],
                                'terms': terms
                            })
            
            # For word level proximity
            elif ordered:
                # Terms must appear in the specified order
                potential_matches = []
                
                for i in range(len(terms) - 1):
                    term1 = terms[i].lower()
                    term2 = terms[i + 1].lower()
                    
                    if term1 not in word_positions or term2 not in word_positions:
                        continue
                    
                    # Check if terms are within distance in order
                    term_matches = self._within_distance_ordered(
                        word_positions[term1], word_positions[term2], distance
                    )
                    
                    if not term_matches:
                        continue
                    
                    potential_matches.append(term_matches)
                
                # Find matches that connect all terms
                if potential_matches:
                    # Find position sequences that connect all terms
                    for match_start in potential_matches[0]:
                        sequence = [match_start]
                        valid_sequence = True
                        
                        for i in range(1, len(potential_matches)):
                            next_match_found = False
                            for match in potential_matches[i]:
                                if sequence[-1][1] == match[0]:
                                    sequence.append(match)
                                    next_match_found = True
                                    break
                            
                            if not next_match_found:
                                valid_sequence = False
                                break
                        
                        if valid_sequence:
                            start_pos = sequence[0][0]
                            end_pos = sequence[-1][1]
                            
                            # Extract the matching text
                            match_words = tokenized_doc['words'][start_pos:end_pos + 1]
                            match_text = ' '.join(match_words)
                            
                            matches.append({
                                'unit_type': 'WORDS',
                                'start_position': start_pos,
                                'end_position': end_pos,
                                'content': match_text,
                                'terms': terms
                            })
            else:
                # Terms can appear in any order
                for i in range(len(terms)):
                    for j in range(i + 1, len(terms)):
                        term1 = terms[i].lower()
                        term2 = terms[j].lower()
                        
                        if term1 not in word_positions or term2 not in word_positions:
                            continue
                        
                        # Check if terms are within distance
                        term_matches = self._within_distance(
                            word_positions[term1], word_positions[term2], distance
                        )
                        
                        for pos1, pos2 in term_matches:
                            start_pos = min(pos1, pos2)
                            end_pos = max(pos1, pos2)
                            
                            # Extract the matching text
                            match_words = tokenized_doc['words'][start_pos:end_pos + 1]
                            match_text = ' '.join(match_words)
                            
                            matches.append({
                                'unit_type': 'WORDS',
                                'start_position': start_pos,
                                'end_position': end_pos,
                                'content': match_text,
                                'terms': [term1, term2]
                            })
            
            return matches
        except Exception as e:
            self.logger.error(f"Error finding proximity matches: {e}")
            return matches
    
    def highlight_proximity_matches(self, content: str, terms: List[str], 
                                  distance: int, unit: str = "WORDS", 
                                  ordered: bool = False) -> str:
        """Highlight occurrences where terms appear within a specified distance.
        
        Args:
            content: Document content
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            Content with highlighted matches
        """
        try:
            matches = self.find_proximity_matches(content, terms, distance, unit, ordered)
            
            if not matches:
                return content
            
            # Create a copy of the content
            highlighted_content = content
            
            # Sort matches by start position in reverse order
            if unit == "WORDS":
                matches.sort(key=lambda m: m.get('start_position', 0), reverse=True)
                
                for match in matches:
                    if 'content' in match and 'start_position' in match and 'end_position' in match:
                        # Find the actual start and end positions in the original content
                        tokenized_doc = self.tokenize_document(content)
                        start_pos = self._find_position_in_content(content, tokenized_doc['words'], match['start_position'])
                        end_pos = self._find_position_in_content(content, tokenized_doc['words'], match['end_position']) + \
                                len(tokenized_doc['words'][match['end_position']])
                        
                        if start_pos is not None and end_pos is not None:
                            # Insert highlighting
                            highlighted_match = f"[HIGHLIGHT]{content[start_pos:end_pos]}[/HIGHLIGHT]"
                            highlighted_content = highlighted_content[:start_pos] + highlighted_match + highlighted_content[end_pos:]
            else:
                # For sentence and paragraph level, just highlight the entire unit
                for match in matches:
                    if 'content' in match:
                        match_content = match['content']
                        highlighted_match = f"[HIGHLIGHT]{match_content}[/HIGHLIGHT]"
                        highlighted_content = highlighted_content.replace(match_content, highlighted_match)
            
            return highlighted_content
        except Exception as e:
            self.logger.error(f"Error highlighting proximity matches: {e}")
            return content
    
    def _find_position_in_content(self, content: str, words: List[str], word_index: int) -> Optional[int]:
        """Find the position of a word in the original content.
        
        Args:
            content: Original content
            words: List of words from tokenization
            word_index: Index of the word to find
            
        Returns:
            Position of the word in the original content, or None if not found
        """
        if word_index < 0 or word_index >= len(words):
            return None
        
        word = words[word_index]
        
        # Build a string of words up to the target word
        prefix_words = words[:word_index]
        prefix = ' '.join(prefix_words)
        
        # Find the approximate position
        prefix_length = content.lower().find(prefix.lower()) if prefix else 0
        if prefix_length < 0:
            prefix_length = 0
        
        # Adjust to the actual position
        word_position = content.lower().find(word.lower(), prefix_length)
        
        return word_position