"""
Type-aware compression for different data types.
"""
from typing import Dict, List, Any, Optional, Callable, Type, Union, Tuple
import json
import base64
import zlib
import struct
import re
from datetime import datetime, date, timedelta
from enum import Enum
import time


class CompressionLevel(Enum):
    """Compression level for balancing CPU usage and size reduction."""
    NONE = 0  # No compression
    LOW = 1   # Low compression, less CPU usage
    MEDIUM = 2  # Medium compression, balanced
    HIGH = 3  # High compression, more CPU usage


class TypeCompressor:
    """Base class for type-specific compressors."""
    def compress(self, value: Any) -> bytes:
        """Compress a value to bytes."""
        raise NotImplementedError
    
    def decompress(self, data: bytes) -> Any:
        """Decompress bytes to a value."""
        raise NotImplementedError


class IntCompressor(TypeCompressor):
    """Compressor for integer values."""
    def compress(self, value: int) -> bytes:
        """Compress an integer to bytes."""
        # Use variable-length encoding to save space for small integers
        if -128 <= value < 128:
            return struct.pack('b', value)  # 1 byte
        elif -32768 <= value < 32768:
            return struct.pack('>h', value)  # 2 bytes
        elif -2147483648 <= value < 2147483648:
            return struct.pack('>i', value)  # 4 bytes
        else:
            return struct.pack('>q', value)  # 8 bytes
    
    def decompress(self, data: bytes) -> int:
        """Decompress bytes to an integer."""
        if len(data) == 1:
            return struct.unpack('b', data)[0]
        elif len(data) == 2:
            return struct.unpack('>h', data)[0]
        elif len(data) == 4:
            return struct.unpack('>i', data)[0]
        else:
            return struct.unpack('>q', data)[0]


class FloatCompressor(TypeCompressor):
    """Compressor for floating point values."""
    def compress(self, value: float) -> bytes:
        """Compress a float to bytes."""
        return struct.pack('>f', value)  # 4 bytes
    
    def decompress(self, data: bytes) -> float:
        """Decompress bytes to a float."""
        return struct.unpack('>f', data)[0]


class TextCompressor(TypeCompressor):
    """Compressor for text values."""
    def __init__(self, level: CompressionLevel = CompressionLevel.MEDIUM):
        self.level = level
    
    def compress(self, value: str) -> bytes:
        """Compress a string to bytes."""
        # For very short strings, compression might increase size
        if len(value) < 10 or self.level == CompressionLevel.NONE:
            # Just encode to UTF-8
            return value.encode('utf-8')
        
        # For longer strings, use zlib compression
        utf8_bytes = value.encode('utf-8')
        compression_level = min(9, max(1, self.level.value * 3))  # Map to zlib levels 1-9
        return zlib.compress(utf8_bytes, level=compression_level)
    
    def decompress(self, data: bytes) -> str:
        """Decompress bytes to a string."""
        try:
            # Try to decompress (if it was compressed)
            return zlib.decompress(data).decode('utf-8')
        except zlib.error:
            # If decompression fails, assume it wasn't compressed
            return data.decode('utf-8')


class BinaryCompressor(TypeCompressor):
    """Compressor for binary data."""
    def __init__(self, level: CompressionLevel = CompressionLevel.MEDIUM):
        self.level = level
    
    def compress(self, value: bytes) -> bytes:
        """Compress binary data."""
        if len(value) < 50 or self.level == CompressionLevel.NONE:
            # For very small binary data, don't compress
            return value
        
        # For larger binary data, use zlib compression
        compression_level = min(9, max(1, self.level.value * 3))  # Map to zlib levels 1-9
        return zlib.compress(value, level=compression_level)
    
    def decompress(self, data: bytes) -> bytes:
        """Decompress binary data."""
        try:
            # Try to decompress (if it was compressed)
            return zlib.decompress(data)
        except zlib.error:
            # If decompression fails, assume it wasn't compressed
            return data


class DateTimeCompressor(TypeCompressor):
    """Compressor for datetime values."""
    def compress(self, value: Union[datetime, date]) -> bytes:
        """Compress a datetime to bytes."""
        if isinstance(value, datetime):
            # Store as Unix timestamp (seconds since epoch)
            timestamp = value.timestamp()
            return struct.pack('>d', timestamp)  # 8 bytes
        elif isinstance(value, date):
            # Store as days since epoch (January 1, 1970)
            epoch = date(1970, 1, 1)
            days = (value - epoch).days
            return struct.pack('>i', days)  # 4 bytes
        else:
            raise ValueError(f"Unsupported date type: {type(value)}")
    
    def decompress(self, data: bytes) -> Union[datetime, date]:
        """Decompress bytes to a datetime."""
        if len(data) == 8:
            # Datetime (timestamp)
            timestamp = struct.unpack('>d', data)[0]
            return datetime.fromtimestamp(timestamp)
        else:
            # Date (days since epoch)
            days = struct.unpack('>i', data)[0]
            epoch = date(1970, 1, 1)
            return epoch + timedelta(days=days)


class BooleanCompressor(TypeCompressor):
    """Compressor for boolean values."""
    def compress(self, value: bool) -> bytes:
        """Compress a boolean to bytes."""
        return struct.pack('?', value)  # 1 byte
    
    def decompress(self, data: bytes) -> bool:
        """Decompress bytes to a boolean."""
        return struct.unpack('?', data)[0]


class NoneCompressor(TypeCompressor):
    """Compressor for None values."""
    def compress(self, value: None) -> bytes:
        """Compress None to bytes."""
        return b''  # Empty bytes
    
    def decompress(self, data: bytes) -> None:
        """Decompress bytes to None."""
        return None


class ListCompressor(TypeCompressor):
    """Compressor for lists of values."""
    def __init__(self, compressor_factory: 'CompressorFactory'):
        self.compressor_factory = compressor_factory
    
    def compress(self, value: List[Any]) -> bytes:
        """Compress a list to bytes."""
        # For empty lists, return special marker
        if not value:
            return b'\x00'
        
        # Compress each element
        compressed_items = []
        for item in value:
            # Get the type signature
            type_signature = self.compressor_factory.get_type_signature(item)
            
            # Get the compressor for this type
            compressor = self.compressor_factory.get_compressor_for_type(type(item))
            
            # Compress the item
            compressed_item = compressor.compress(item)

            # Handle large compressed values
            if len(compressed_item) > 255:
                # Use a special marker for large values (255)
                item_length = 255
                # Store the actual length as a 4-byte integer
                item_size_bytes = struct.pack('>I', len(compressed_item))
            else:
                item_length = len(compressed_item)
                item_size_bytes = b''

            # Store type signature and length with the compressed item
            item_header = struct.pack('>BB', type_signature, item_length) + item_size_bytes
            compressed_items.append(item_header + compressed_item)
        
        # Join all compressed items
        return b'\x01' + b''.join(compressed_items)
    
    def decompress(self, data: bytes) -> List[Any]:
        """Decompress bytes to a list."""
        # Check for empty list marker
        if data == b'\x00':
            return []
        
        # Skip the list marker
        data = data[1:]
        
        result = []
        offset = 0
        
        while offset < len(data):
            # Read the type signature and length
            type_signature, item_length = struct.unpack('>BB', data[offset:offset+2])
            offset += 2

            # Check if this is a large value
            if item_length == 255:
                # Read the actual length as a 4-byte integer
                actual_length = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                item_length = actual_length

            # Read the compressed item
            compressed_item = data[offset:offset+item_length]
            offset += item_length
            
            # Get the compressor for this type
            compressor = self.compressor_factory.get_compressor_for_signature(type_signature)
            
            # Decompress the item
            item = compressor.decompress(compressed_item)
            result.append(item)
        
        return result


class DictCompressor(TypeCompressor):
    """Compressor for dictionaries."""
    def __init__(self, compressor_factory: 'CompressorFactory'):
        self.compressor_factory = compressor_factory
        self.text_compressor = TextCompressor()
    
    def compress(self, value: Dict[str, Any]) -> bytes:
        """Compress a dictionary to bytes."""
        # For empty dicts, return special marker
        if not value:
            return b'\x00'
        
        # Compress each key-value pair
        compressed_items = []
        for key, val in value.items():
            # Compress the key (always a string)
            compressed_key = self.text_compressor.compress(key)
            key_header = struct.pack('>B', len(compressed_key))
            
            # Get the type signature for the value
            type_signature = self.compressor_factory.get_type_signature(val)
            
            # Get the compressor for this type
            compressor = self.compressor_factory.get_compressor_for_type(type(val))
            
            # Compress the value
            compressed_val = compressor.compress(val)

            # Handle large compressed values - break into chunks if needed
            if len(compressed_val) > 255:
                # Use a special marker for large values (255)
                val_length = 255
                is_large = True
                # Store the actual length as a 4-byte integer
                val_size_bytes = struct.pack('>I', len(compressed_val))
            else:
                val_length = len(compressed_val)
                is_large = False
                val_size_bytes = b''

            # Store type signature and length with the compressed value
            val_header = struct.pack('>BB', type_signature, val_length) + val_size_bytes
            
            # Combine key and value
            compressed_items.append(key_header + compressed_key + val_header + compressed_val)
        
        # Join all compressed items
        return b'\x01' + b''.join(compressed_items)
    
    def decompress(self, data: bytes) -> Dict[str, Any]:
        """Decompress bytes to a dictionary."""
        # Check for empty dict marker
        if data == b'\x00':
            return {}
        
        # Skip the dict marker
        data = data[1:]
        
        result = {}
        offset = 0
        
        while offset < len(data):
            # Read the key length
            key_length = struct.unpack('>B', data[offset:offset+1])[0]
            offset += 1
            
            # Read the compressed key
            compressed_key = data[offset:offset+key_length]
            offset += key_length
            
            # Decompress the key
            key = self.text_compressor.decompress(compressed_key)
            
            # Read the value type signature and length
            val_type, val_length = struct.unpack('>BB', data[offset:offset+2])
            offset += 2

            # Check if this is a large value (length marker = 255)
            if val_length == 255:
                # Read the actual length as a 4-byte integer
                actual_length = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                val_length = actual_length

            # Read the compressed value
            compressed_val = data[offset:offset+val_length]
            offset += val_length
            
            # Get the compressor for this type
            compressor = self.compressor_factory.get_compressor_for_signature(val_type)
            
            # Decompress the value
            val = compressor.decompress(compressed_val)
            
            # Add to result
            result[key] = val
        
        return result


class CompressorFactory:
    """Factory for creating and managing type-specific compressors."""
    def __init__(self, compression_level: CompressionLevel = CompressionLevel.MEDIUM):
        self.compression_level = compression_level
        self.type_to_signature: Dict[Type, int] = {
            type(None): 0,
            bool: 1,
            int: 2,
            float: 3,
            str: 4,
            bytes: 5,
            list: 6,
            dict: 7,
            datetime: 8,
            date: 9
        }
        self.signature_to_compressor: Dict[int, TypeCompressor] = {}
        self._initialize_compressors()
    
    def _initialize_compressors(self) -> None:
        """Initialize the compressors for each type."""
        self.signature_to_compressor = {
            0: NoneCompressor(),
            1: BooleanCompressor(),
            2: IntCompressor(),
            3: FloatCompressor(),
            4: TextCompressor(self.compression_level),
            5: BinaryCompressor(self.compression_level),
            6: ListCompressor(self),  # Uses this factory for recursive compression
            7: DictCompressor(self),  # Uses this factory for recursive compression
            8: DateTimeCompressor(),
            9: DateTimeCompressor()
        }
    
    def get_type_signature(self, value: Any) -> int:
        """Get the type signature for a value."""
        value_type = type(value)
        return self.type_to_signature.get(value_type, 0)
    
    def get_compressor_for_type(self, value_type: Type) -> TypeCompressor:
        """Get the compressor for a specific type."""
        type_signature = self.type_to_signature.get(value_type, 0)
        return self.signature_to_compressor.get(type_signature, NoneCompressor())
    
    def get_compressor_for_signature(self, type_signature: int) -> TypeCompressor:
        """Get the compressor for a specific type signature."""
        return self.signature_to_compressor.get(type_signature, NoneCompressor())
    
    def set_compression_level(self, level: CompressionLevel) -> None:
        """Set the compression level for all compressors."""
        self.compression_level = level
        # Reinitialize compressors with the new level
        self._initialize_compressors()


class PayloadCompressor:
    """
    Compresses and decompresses data for efficient transfer.
    """
    def __init__(self, 
                compression_level: CompressionLevel = CompressionLevel.MEDIUM, 
                schema: Optional[Dict[str, Dict[str, Type]]] = None):
        self.compressor_factory = CompressorFactory(compression_level)
        self.schema = schema or {}  # Table name -> {column name -> type}
    
    def compress_record(self, 
                       table_name: str, 
                       record: Dict[str, Any]) -> bytes:
        """
        Compress a record using type-aware compression.
        
        Args:
            table_name: Name of the table
            record: Record to compress
            
        Returns:
            Compressed record as bytes
        """
        # Use the dict compressor for the entire record
        compressor = self.compressor_factory.get_compressor_for_type(dict)
        return compressor.compress(record)
    
    def decompress_record(self, 
                         table_name: str, 
                         data: bytes) -> Dict[str, Any]:
        """
        Decompress a record.
        
        Args:
            table_name: Name of the table
            data: Compressed record data
            
        Returns:
            Decompressed record
        """
        # Use the dict compressor for the entire record
        compressor = self.compressor_factory.get_compressor_for_type(dict)
        return compressor.decompress(data)
    
    def compress_changes(self, 
                        table_name: str, 
                        changes: List[Dict[str, Any]]) -> bytes:
        """
        Compress a list of changes.
        
        Args:
            table_name: Name of the table
            changes: List of changes to compress
            
        Returns:
            Compressed changes as bytes
        """
        # Use the list compressor for the list of changes
        compressor = self.compressor_factory.get_compressor_for_type(list)
        return compressor.compress(changes)
    
    def decompress_changes(self, 
                          table_name: str, 
                          data: bytes) -> List[Dict[str, Any]]:
        """
        Decompress a list of changes.
        
        Args:
            table_name: Name of the table
            data: Compressed changes data
            
        Returns:
            Decompressed list of changes
        """
        # Use the list compressor for the list of changes
        compressor = self.compressor_factory.get_compressor_for_type(list)
        return compressor.decompress(data)
    
    def set_compression_level(self, level: CompressionLevel) -> None:
        """Set the compression level."""
        self.compressor_factory.set_compression_level(level)
    
    def set_schema(self, schema: Dict[str, Dict[str, Type]]) -> None:
        """Set the schema for type-aware compression."""
        self.schema = schema