"""Common query operators and utility functions for the unified query language interpreter."""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from datetime import datetime, date, timedelta
from decimal import Decimal

from .base_models import QueryOperator, DistanceUnit, TemporalUnit


class ComparisonOperator:
    """Handles comparison operations between values."""
    
    @staticmethod
    def equals(left: Any, right: Any) -> bool:
        """Check if two values are equal."""
        return left == right
    
    @staticmethod
    def not_equals(left: Any, right: Any) -> bool:
        """Check if two values are not equal."""
        return left != right
    
    @staticmethod
    def greater_than(left: Any, right: Any) -> bool:
        """Check if left value is greater than right value."""
        try:
            return left > right
        except TypeError:
            return False
    
    @staticmethod
    def less_than(left: Any, right: Any) -> bool:
        """Check if left value is less than right value."""
        try:
            return left < right
        except TypeError:
            return False
    
    @staticmethod
    def greater_than_equals(left: Any, right: Any) -> bool:
        """Check if left value is greater than or equal to right value."""
        try:
            return left >= right
        except TypeError:
            return False
    
    @staticmethod
    def less_than_equals(left: Any, right: Any) -> bool:
        """Check if left value is less than or equal to right value."""
        try:
            return left <= right
        except TypeError:
            return False
    
    @staticmethod
    def contains(left: Any, right: Any) -> bool:
        """Check if left value contains right value."""
        try:
            if isinstance(left, str) and isinstance(right, str):
                return right.lower() in left.lower()
            elif isinstance(left, (list, tuple, set)):
                return right in left
            elif isinstance(left, dict):
                return right in left.values()
            return str(right).lower() in str(left).lower()
        except (AttributeError, TypeError):
            return False
    
    @staticmethod
    def starts_with(left: Any, right: Any) -> bool:
        """Check if left value starts with right value."""
        try:
            return str(left).lower().startswith(str(right).lower())
        except (AttributeError, TypeError):
            return False
    
    @staticmethod
    def ends_with(left: Any, right: Any) -> bool:
        """Check if left value ends with right value."""
        try:
            return str(left).lower().endswith(str(right).lower())
        except (AttributeError, TypeError):
            return False
    
    @staticmethod
    def in_list(left: Any, right: List[Any]) -> bool:
        """Check if left value is in the right list."""
        try:
            if not isinstance(right, (list, tuple, set)):
                return False
            return left in right
        except TypeError:
            return False
    
    @staticmethod
    def between(left: Any, right: Tuple[Any, Any]) -> bool:
        """Check if left value is between two right values (inclusive)."""
        try:
            if not isinstance(right, (tuple, list)) or len(right) != 2:
                return False
            min_val, max_val = right
            return min_val <= left <= max_val
        except (TypeError, ValueError):
            return False


class TextOperator:
    """Handles text-specific operations."""
    
    @staticmethod
    def fuzzy_match(text: str, pattern: str, threshold: float = 0.8) -> bool:
        """Perform fuzzy text matching.
        
        Args:
            text: Text to search in
            pattern: Pattern to search for
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if fuzzy match exceeds threshold
        """
        try:
            # Simple implementation using character overlap
            # In a real system, you might use libraries like fuzzywuzzy
            text_lower = text.lower()
            pattern_lower = pattern.lower()
            
            if pattern_lower in text_lower:
                return True
            
            # Calculate character overlap
            text_chars = set(text_lower)
            pattern_chars = set(pattern_lower)
            overlap = len(text_chars.intersection(pattern_chars))
            total_chars = len(text_chars.union(pattern_chars))
            
            similarity = overlap / total_chars if total_chars > 0 else 0.0
            return similarity >= threshold
        except (AttributeError, TypeError):
            return False
    
    @staticmethod
    def regex_match(text: str, pattern: str, flags: int = 0) -> bool:
        """Perform regex pattern matching.
        
        Args:
            text: Text to search in
            pattern: Regex pattern
            flags: Regex flags
            
        Returns:
            True if pattern matches
        """
        try:
            return bool(re.search(pattern, str(text), flags))
        except (re.error, TypeError):
            return False
    
    @staticmethod
    def soundex_match(text1: str, text2: str) -> bool:
        """Perform soundex matching for phonetically similar words.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if soundex codes match
        """
        def soundex(word: str) -> str:
            """Generate soundex code for a word."""
            if not word:
                return "0000"
            
            word = word.upper()
            soundex_code = word[0]
            
            # Mapping for consonants
            mapping = {
                'B': '1', 'F': '1', 'P': '1', 'V': '1',
                'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
                'D': '3', 'T': '3',
                'L': '4',
                'M': '5', 'N': '5',
                'R': '6'
            }
            
            for char in word[1:]:
                if char in mapping:
                    code = mapping[char]
                    if code != soundex_code[-1]:  # Avoid consecutive duplicates
                        soundex_code += code
                
                if len(soundex_code) >= 4:
                    break
            
            # Pad with zeros
            soundex_code = (soundex_code + "0000")[:4]
            return soundex_code
        
        try:
            return soundex(text1) == soundex(text2)
        except (AttributeError, TypeError):
            return False


class ProximityOperator:
    """Handles proximity operations for text and spatial data."""
    
    @staticmethod
    def text_proximity(
        text: str,
        terms: List[str],
        distance: int,
        unit: DistanceUnit = DistanceUnit.WORDS,
        ordered: bool = False
    ) -> bool:
        """Check if terms are within proximity in text.
        
        Args:
            text: Text to search in
            terms: Terms to find
            distance: Maximum distance between terms
            unit: Unit of distance measurement
            ordered: Whether terms must appear in order
            
        Returns:
            True if terms are within proximity
        """
        if not terms or len(terms) < 2:
            return False
        
        text_lower = text.lower()
        terms_lower = [term.lower() for term in terms]
        
        # Find positions of all terms
        term_positions = {}
        for term in terms_lower:
            positions = []
            start = 0
            while True:
                pos = text_lower.find(term, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            term_positions[term] = positions
        
        # Check if all terms were found
        if not all(positions for positions in term_positions.values()):
            return False
        
        # Convert positions based on unit
        if unit == DistanceUnit.WORDS:
            # Split text into words and find word positions
            words = text_lower.split()
            word_positions = {}
            char_to_word = {}
            
            char_pos = 0
            for word_idx, word in enumerate(words):
                word_start = text_lower.find(word, char_pos)
                word_end = word_start + len(word)
                for i in range(word_start, word_end):
                    char_to_word[i] = word_idx
                char_pos = word_end
            
            # Convert character positions to word positions
            for term, char_positions in term_positions.items():
                word_positions[term] = [
                    char_to_word.get(pos, -1) for pos in char_positions if pos in char_to_word
                ]
            
            term_positions = word_positions
        
        # Check proximity between term positions
        return ProximityOperator._check_proximity_positions(
            term_positions, terms_lower, distance, ordered
        )
    
    @staticmethod
    def _check_proximity_positions(
        term_positions: Dict[str, List[int]],
        terms: List[str],
        distance: int,
        ordered: bool
    ) -> bool:
        """Check if term positions are within proximity constraints."""
        if len(terms) != 2:
            # For simplicity, only handle pairs of terms
            return False
        
        term1, term2 = terms
        positions1 = term_positions.get(term1, [])
        positions2 = term_positions.get(term2, [])
        
        for pos1 in positions1:
            for pos2 in positions2:
                if ordered:
                    # Terms must be in order
                    if pos2 > pos1 and (pos2 - pos1) <= distance:
                        return True
                else:
                    # Terms can be in any order
                    if abs(pos2 - pos1) <= distance:
                        return True
        
        return False


class TemporalOperator:
    """Handles temporal operations and date/time comparisons."""
    
    @staticmethod
    def date_equals(date1: Union[datetime, date, str], date2: Union[datetime, date, str]) -> bool:
        """Check if two dates are equal."""
        try:
            d1 = TemporalOperator._parse_date(date1)
            d2 = TemporalOperator._parse_date(date2)
            return d1.date() == d2.date() if isinstance(d1, datetime) and isinstance(d2, datetime) else d1 == d2
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def date_before(date1: Union[datetime, date, str], date2: Union[datetime, date, str]) -> bool:
        """Check if date1 is before date2."""
        try:
            d1 = TemporalOperator._parse_date(date1)
            d2 = TemporalOperator._parse_date(date2)
            return d1 < d2
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def date_after(date1: Union[datetime, date, str], date2: Union[datetime, date, str]) -> bool:
        """Check if date1 is after date2."""
        try:
            d1 = TemporalOperator._parse_date(date1)
            d2 = TemporalOperator._parse_date(date2)
            return d1 > d2
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def date_within(
        target_date: Union[datetime, date, str],
        start_date: Union[datetime, date, str],
        end_date: Union[datetime, date, str]
    ) -> bool:
        """Check if target date is within start and end dates."""
        try:
            target = TemporalOperator._parse_date(target_date)
            start = TemporalOperator._parse_date(start_date)
            end = TemporalOperator._parse_date(end_date)
            return start <= target <= end
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def time_within_duration(
        target_time: Union[datetime, str],
        reference_time: Union[datetime, str],
        duration: int,
        unit: TemporalUnit = TemporalUnit.MINUTES
    ) -> bool:
        """Check if target time is within duration of reference time."""
        try:
            target = TemporalOperator._parse_datetime(target_time)
            reference = TemporalOperator._parse_datetime(reference_time)
            
            # Convert duration to timedelta
            if unit == TemporalUnit.SECONDS:
                delta = timedelta(seconds=duration)
            elif unit == TemporalUnit.MINUTES:
                delta = timedelta(minutes=duration)
            elif unit == TemporalUnit.HOURS:
                delta = timedelta(hours=duration)
            elif unit == TemporalUnit.DAYS:
                delta = timedelta(days=duration)
            elif unit == TemporalUnit.WEEKS:
                delta = timedelta(weeks=duration)
            else:
                # For months and years, use approximate values
                if unit == TemporalUnit.MONTHS:
                    delta = timedelta(days=duration * 30)
                elif unit == TemporalUnit.YEARS:
                    delta = timedelta(days=duration * 365)
                else:
                    return False
            
            return abs(target - reference) <= delta
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _parse_date(date_val: Union[datetime, date, str]) -> Union[datetime, date]:
        """Parse various date formats into date or datetime object."""
        if isinstance(date_val, (datetime, date)):
            return date_val
        elif isinstance(date_val, str):
            # Try various date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_val, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse date: {date_val}")
        else:
            raise TypeError(f"Invalid date type: {type(date_val)}")
    
    @staticmethod
    def _parse_datetime(datetime_val: Union[datetime, str]) -> datetime:
        """Parse various datetime formats into datetime object."""
        if isinstance(datetime_val, datetime):
            return datetime_val
        elif isinstance(datetime_val, str):
            return TemporalOperator._parse_date(datetime_val)
        else:
            raise TypeError(f"Invalid datetime type: {type(datetime_val)}")


class NumericOperator:
    """Handles numeric operations and comparisons."""
    
    @staticmethod
    def approximately_equals(
        num1: Union[int, float, Decimal],
        num2: Union[int, float, Decimal],
        tolerance: float = 1e-6
    ) -> bool:
        """Check if two numbers are approximately equal within tolerance."""
        try:
            return abs(float(num1) - float(num2)) <= tolerance
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def in_range(
        value: Union[int, float, Decimal],
        min_val: Union[int, float, Decimal],
        max_val: Union[int, float, Decimal],
        inclusive: bool = True
    ) -> bool:
        """Check if value is in numeric range."""
        try:
            val = float(value)
            min_v = float(min_val)
            max_v = float(max_val)
            
            if inclusive:
                return min_v <= val <= max_v
            else:
                return min_v < val < max_v
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_even(value: Union[int, float]) -> bool:
        """Check if number is even."""
        try:
            return int(value) % 2 == 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_odd(value: Union[int, float]) -> bool:
        """Check if number is odd."""
        try:
            return int(value) % 2 != 0
        except (ValueError, TypeError):
            return False


class OperatorRegistry:
    """Registry for query operators and their implementations."""
    
    def __init__(self):
        """Initialize the operator registry with default operators."""
        self._operators = {}
        self._register_default_operators()
    
    def _register_default_operators(self) -> None:
        """Register default operators."""
        # Comparison operators
        self._operators[QueryOperator.EQUALS] = ComparisonOperator.equals
        self._operators[QueryOperator.GREATER_THAN] = ComparisonOperator.greater_than
        self._operators[QueryOperator.LESS_THAN] = ComparisonOperator.less_than
        self._operators[QueryOperator.GREATER_THAN_EQUALS] = ComparisonOperator.greater_than_equals
        self._operators[QueryOperator.LESS_THAN_EQUALS] = ComparisonOperator.less_than_equals
        self._operators[QueryOperator.CONTAINS] = ComparisonOperator.contains
        self._operators[QueryOperator.STARTS_WITH] = ComparisonOperator.starts_with
        self._operators[QueryOperator.ENDS_WITH] = ComparisonOperator.ends_with
        self._operators[QueryOperator.IN] = ComparisonOperator.in_list
        self._operators[QueryOperator.BETWEEN] = ComparisonOperator.between
        
        # Logical operators are handled separately as they combine results
    
    def register_operator(self, operator: QueryOperator, implementation: callable) -> None:
        """Register a custom operator implementation.
        
        Args:
            operator: Query operator enum
            implementation: Function that implements the operator
        """
        self._operators[operator] = implementation
    
    def get_operator(self, operator: QueryOperator) -> Optional[callable]:
        """Get the implementation for an operator.
        
        Args:
            operator: Query operator enum
            
        Returns:
            Operator implementation function or None
        """
        return self._operators.get(operator)
    
    def apply_operator(
        self,
        operator: QueryOperator,
        left: Any,
        right: Any
    ) -> bool:
        """Apply an operator to two values.
        
        Args:
            operator: Query operator to apply
            left: Left operand
            right: Right operand
            
        Returns:
            Result of the operation
            
        Raises:
            ValueError: If operator is not registered
        """
        implementation = self._operators.get(operator)
        if not implementation:
            raise ValueError(f"Operator {operator} is not registered")
        
        try:
            return implementation(left, right)
        except Exception as e:
            # Log the error and return False
            return False
    
    def list_operators(self) -> List[QueryOperator]:
        """List all registered operators.
        
        Returns:
            List of registered operators
        """
        return list(self._operators.keys())


# Create a default operator registry instance
default_operator_registry = OperatorRegistry()