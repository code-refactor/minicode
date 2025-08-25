"""ID generation utilities for the unified task scheduling library."""

import uuid
import hashlib
import random
import string
import time
from datetime import datetime
from typing import Optional, Dict, Any
import threading


class IDGenerator:
    """Thread-safe ID generator with various formats."""
    
    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()
        self._node_id = self._generate_node_id()
    
    def generate_uuid(self) -> str:
        """Generate a UUID4 string."""
        return str(uuid.uuid4())
    
    def generate_uuid_hex(self) -> str:
        """Generate a UUID4 as hex string (no dashes)."""
        return uuid.uuid4().hex
    
    def generate_short_id(self, length: int = 8) -> str:
        """Generate a short random ID."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def generate_sequential_id(self, prefix: str = "") -> str:
        """Generate a sequential ID with optional prefix."""
        with self._lock:
            self._counter += 1
            return f"{prefix}{self._counter:06d}"
    
    def generate_timestamp_id(self, prefix: str = "") -> str:
        """Generate an ID based on current timestamp."""
        timestamp = int(time.time() * 1000000)  # microsecond precision
        return f"{prefix}{timestamp}"
    
    def generate_snowflake_id(self) -> int:
        """Generate a Twitter Snowflake-like ID."""
        # Simplified snowflake: timestamp (41 bits) + node_id (10 bits) + sequence (12 bits)
        timestamp = int(time.time() * 1000) - 1640995200000  # Epoch offset (2022-01-01)
        
        with self._lock:
            self._counter = (self._counter + 1) % 4096  # 12-bit sequence
            
        node_part = (self._node_id & 0x3FF) << 12  # 10-bit node ID
        time_part = (timestamp & 0x1FFFFFFFFFF) << 22  # 41-bit timestamp
        
        return time_part | node_part | self._counter
    
    def generate_hash_id(self, data: str, length: int = 16) -> str:
        """Generate a hash-based ID from input data."""
        hash_obj = hashlib.sha256(data.encode())
        return hash_obj.hexdigest()[:length]
    
    def generate_job_id(self, prefix: str = "job") -> str:
        """Generate a job ID with standard format."""
        return f"{prefix}_{self.generate_timestamp_id()}_{self.generate_short_id(4)}"
    
    def generate_node_id(self, prefix: str = "node") -> str:
        """Generate a node ID with standard format."""
        return f"{prefix}_{self.generate_uuid_hex()[:16]}"
    
    def generate_session_id(self, prefix: str = "session") -> str:
        """Generate a session ID with standard format."""
        return f"{prefix}_{self.generate_timestamp_id()}_{self.generate_short_id(8)}"
    
    def _generate_node_id(self) -> int:
        """Generate a unique node ID for snowflake IDs."""
        # Use MAC address or fallback to random
        try:
            import uuid
            mac = uuid.getnode()
            return mac & 0x3FF  # Use last 10 bits
        except:
            return random.randint(0, 1023)


# Global ID generator instance
_global_generator = IDGenerator()

# Convenience functions using global generator
def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return _global_generator.generate_uuid()

def generate_short_id(length: int = 8) -> str:
    """Generate a short random ID."""
    return _global_generator.generate_short_id(length)

def generate_job_id(prefix: str = "job") -> str:
    """Generate a job ID."""
    return _global_generator.generate_job_id(prefix)

def generate_node_id(prefix: str = "node") -> str:
    """Generate a node ID."""
    return _global_generator.generate_node_id(prefix)

def generate_sequential_id(prefix: str = "") -> str:
    """Generate a sequential ID."""
    return _global_generator.generate_sequential_id(prefix)

def generate_timestamp_id(prefix: str = "") -> str:
    """Generate a timestamp-based ID."""
    return _global_generator.generate_timestamp_id(prefix)

def generate_hash_id(data: str, length: int = 16) -> str:
    """Generate a hash-based ID."""
    return _global_generator.generate_hash_id(data, length)


class PrefixedIDGenerator:
    """ID generator that maintains separate counters for different prefixes."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def generate_id(self, prefix: str, format_string: str = "{prefix}_{counter:06d}") -> str:
        """Generate an ID with the given prefix and format."""
        with self._lock:
            if prefix not in self._counters:
                self._counters[prefix] = 0
            self._counters[prefix] += 1
            counter = self._counters[prefix]
        
        return format_string.format(prefix=prefix, counter=counter)
    
    def reset_counter(self, prefix: str):
        """Reset the counter for a specific prefix."""
        with self._lock:
            self._counters[prefix] = 0
    
    def get_counter(self, prefix: str) -> int:
        """Get current counter value for a prefix."""
        return self._counters.get(prefix, 0)


def generate_readable_id(words: Optional[list] = None, separator: str = "-") -> str:
    """Generate a human-readable ID using random words."""
    if words is None:
        # Default word lists for readable IDs
        adjectives = [
            "swift", "bright", "clever", "dynamic", "elegant", "flexible", 
            "golden", "heroic", "infinite", "joyful", "keen", "luminous",
            "mighty", "noble", "optimistic", "powerful", "quiet", "robust",
            "stellar", "trusty", "unique", "vibrant", "wise", "zealous"
        ]
        
        nouns = [
            "falcon", "phoenix", "tiger", "eagle", "wolf", "bear", "lion",
            "hawk", "panther", "leopard", "shark", "whale", "dolphin",
            "rocket", "comet", "star", "galaxy", "nebula", "quasar",
            "thunder", "lightning", "storm", "blizzard", "tornado"
        ]
        
        words = [random.choice(adjectives), random.choice(nouns)]
    
    # Add a random number
    number = random.randint(100, 999)
    words.append(str(number))
    
    return separator.join(words)


def validate_id_format(id_string: str, pattern: str) -> bool:
    """Validate if an ID matches a specific pattern."""
    import re
    try:
        return bool(re.match(pattern, id_string))
    except re.error:
        return False


def extract_timestamp_from_id(id_string: str, timestamp_position: int = 1, 
                             separator: str = "_") -> Optional[datetime]:
    """Extract timestamp from a timestamp-based ID."""
    try:
        parts = id_string.split(separator)
        if len(parts) <= timestamp_position:
            return None
        
        timestamp_str = parts[timestamp_position]
        timestamp = int(timestamp_str) / 1000000  # Convert from microseconds
        
        return datetime.fromtimestamp(timestamp)
    except (ValueError, IndexError, OSError):
        return None