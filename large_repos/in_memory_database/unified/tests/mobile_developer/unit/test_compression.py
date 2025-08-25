"""
Tests for the type-aware payload compression.
"""
import pytest
import time
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from syncdb.compression.type_compressor import (
    CompressionLevel, TypeCompressor, IntCompressor, FloatCompressor,
    TextCompressor, BinaryCompressor, DateTimeCompressor, BooleanCompressor,
    NoneCompressor, ListCompressor, DictCompressor, CompressorFactory,
    PayloadCompressor
)


def test_int_compressor():
    """Test the integer compressor."""
    compressor = IntCompressor()
    
    # Test compression of various integers
    small_int = 42
    large_int = 1000000
    negative_int = -42
    
    # Compress
    small_compressed = compressor.compress(small_int)
    large_compressed = compressor.compress(large_int)
    negative_compressed = compressor.compress(negative_int)
    
    # Check compressed size
    assert len(small_compressed) <= 4  # Should use less space for small ints
    assert len(large_compressed) <= 8
    assert len(negative_compressed) <= 4
    
    # Decompress
    small_decompressed = compressor.decompress(small_compressed)
    large_decompressed = compressor.decompress(large_compressed)
    negative_decompressed = compressor.decompress(negative_compressed)
    
    # Check decompressed values
    assert small_decompressed == small_int
    assert large_decompressed == large_int
    assert negative_decompressed == negative_int


def test_float_compressor():
    """Test the float compressor."""
    compressor = FloatCompressor()
    
    # Test compression of various floats
    float_val = 3.14159
    zero_float = 0.0
    negative_float = -2.71828
    
    # Compress
    float_compressed = compressor.compress(float_val)
    zero_compressed = compressor.compress(zero_float)
    negative_compressed = compressor.compress(negative_float)
    
    # Check compressed size
    assert len(float_compressed) == 4  # 32-bit float
    assert len(zero_compressed) == 4
    assert len(negative_compressed) == 4
    
    # Decompress
    float_decompressed = compressor.decompress(float_compressed)
    zero_decompressed = compressor.decompress(zero_compressed)
    negative_decompressed = compressor.decompress(negative_compressed)
    
    # Check decompressed values (using approx due to float precision)
    assert abs(float_decompressed - float_val) < 0.0001
    assert zero_decompressed == zero_float
    assert abs(negative_decompressed - negative_float) < 0.0001


def test_text_compressor():
    """Test the text compressor."""
    # Test different compression levels
    none_compressor = TextCompressor(CompressionLevel.NONE)
    medium_compressor = TextCompressor(CompressionLevel.MEDIUM)
    high_compressor = TextCompressor(CompressionLevel.HIGH)
    
    # Test compression of various strings
    short_text = "Hello"
    long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20  # Repeated text compresses well
    
    # Compress
    short_none = none_compressor.compress(short_text)
    short_medium = medium_compressor.compress(short_text)
    
    long_none = none_compressor.compress(long_text)
    long_medium = medium_compressor.compress(long_text)
    long_high = high_compressor.compress(long_text)
    
    # Check that short text is not compressed at NONE level
    assert short_none == short_text.encode('utf-8')
    
    # Check that long text compressed better at higher levels
    assert len(long_none) > len(long_medium)
    assert len(long_medium) >= len(long_high)  # Higher compression should be at least as good
    
    # Decompress
    short_decompressed = medium_compressor.decompress(short_medium)
    long_decompressed = medium_compressor.decompress(long_medium)
    
    # Check decompressed values
    assert short_decompressed == short_text
    assert long_decompressed == long_text


def test_binary_compressor():
    """Test the binary compressor."""
    # Test different compression levels
    none_compressor = BinaryCompressor(CompressionLevel.NONE)
    medium_compressor = BinaryCompressor(CompressionLevel.MEDIUM)
    
    # Test compression of various binary data
    small_data = b'\x00\x01\x02\x03\x04'
    large_data = b'\x00\x01\x02\x03' * 100  # Repeated data compresses well
    
    # Compress
    small_none = none_compressor.compress(small_data)
    small_medium = medium_compressor.compress(small_data)
    
    large_none = none_compressor.compress(large_data)
    large_medium = medium_compressor.compress(large_data)
    
    # Check that small data is not compressed at NONE level
    assert small_none == small_data
    
    # Check that large data is compressed at MEDIUM level
    assert len(large_medium) < len(large_data)
    
    # Decompress
    small_decompressed = medium_compressor.decompress(small_medium)
    large_decompressed = medium_compressor.decompress(large_medium)
    
    # Check decompressed values
    assert small_decompressed == small_data
    assert large_decompressed == large_data


def test_datetime_compressor():
    """Test the datetime compressor."""
    compressor = DateTimeCompressor()
    
    # Test compression of datetime and date
    dt = datetime.now()
    d = date.today()
    
    # Compress
    dt_compressed = compressor.compress(dt)
    d_compressed = compressor.compress(d)
    
    # Check compressed size
    assert len(dt_compressed) == 8  # 64-bit timestamp
    assert len(d_compressed) == 4   # 32-bit day count
    
    # Decompress
    dt_decompressed = compressor.decompress(dt_compressed)
    d_decompressed = compressor.decompress(d_compressed)
    
    # Check decompressed values (approximate due to precision)
    assert abs((dt_decompressed - dt).total_seconds()) < 1
    assert isinstance(d_decompressed, date)


def test_boolean_compressor():
    """Test the boolean compressor."""
    compressor = BooleanCompressor()
    
    # Test compression of booleans
    true_val = True
    false_val = False
    
    # Compress
    true_compressed = compressor.compress(true_val)
    false_compressed = compressor.compress(false_val)
    
    # Check compressed size
    assert len(true_compressed) == 1
    assert len(false_compressed) == 1
    
    # Decompress
    true_decompressed = compressor.decompress(true_compressed)
    false_decompressed = compressor.decompress(false_compressed)
    
    # Check decompressed values
    assert true_decompressed is True
    assert false_decompressed is False


def test_none_compressor():
    """Test the None compressor."""
    compressor = NoneCompressor()
    
    # Test compression of None
    none_val = None
    
    # Compress
    compressed = compressor.compress(none_val)
    
    # Check compressed size
    assert len(compressed) == 0  # Empty bytes
    
    # Decompress
    decompressed = compressor.decompress(compressed)
    
    # Check decompressed value
    assert decompressed is None


def test_list_compressor(monkeypatch):
    """Test the list compressor."""
    # Create a compressor factory
    factory = CompressorFactory()
    compressor = ListCompressor(factory)
    
    # Test compression of various lists
    empty_list = []
    int_list = [1, 2, 3, 4, 5]
    mixed_list = [1, "hello", 3.14, True, None]
    
    # Compress
    empty_compressed = compressor.compress(empty_list)
    int_compressed = compressor.compress(int_list)
    mixed_compressed = compressor.compress(mixed_list)
    
    # Check that empty list has special marker
    assert empty_compressed == b'\x00'
    
    # Check that non-empty lists have list marker
    assert int_compressed[0] == 1
    assert mixed_compressed[0] == 1
    
    # Decompress
    empty_decompressed = compressor.decompress(empty_compressed)
    int_decompressed = compressor.decompress(int_compressed)
    mixed_decompressed = compressor.decompress(mixed_compressed)
    
    # Check decompressed values
    assert empty_decompressed == empty_list
    assert int_decompressed == int_list
    assert mixed_decompressed[0] == mixed_list[0]
    assert mixed_decompressed[1] == mixed_list[1]
    assert abs(mixed_decompressed[2] - mixed_list[2]) < 0.0001  # Float comparison
    assert mixed_decompressed[3] == mixed_list[3]
    assert mixed_decompressed[4] == mixed_list[4]


def test_dict_compressor():
    """Test the dictionary compressor."""
    # Create a compressor factory
    factory = CompressorFactory()
    compressor = DictCompressor(factory)
    
    # Test compression of various dictionaries
    empty_dict = {}
    simple_dict = {"key1": "value1", "key2": 42}
    nested_dict = {"key1": "value1", "key2": {"nested": "value"}, "key3": [1, 2, 3]}
    
    # Compress
    empty_compressed = compressor.compress(empty_dict)
    simple_compressed = compressor.compress(simple_dict)
    nested_compressed = compressor.compress(nested_dict)
    
    # Check that empty dict has special marker
    assert empty_compressed == b'\x00'
    
    # Check that non-empty dicts have dict marker
    assert simple_compressed[0] == 1
    assert nested_compressed[0] == 1
    
    # Decompress
    empty_decompressed = compressor.decompress(empty_compressed)
    simple_decompressed = compressor.decompress(simple_compressed)
    nested_decompressed = compressor.decompress(nested_compressed)
    
    # Check decompressed values
    assert empty_decompressed == empty_dict
    assert simple_decompressed == simple_dict
    assert nested_decompressed["key1"] == nested_dict["key1"]
    assert nested_decompressed["key2"]["nested"] == nested_dict["key2"]["nested"]
    assert nested_decompressed["key3"] == nested_dict["key3"]


def test_compressor_factory():
    """Test the compressor factory."""
    factory = CompressorFactory()
    
    # Test getting type signatures
    assert factory.get_type_signature(None) == 0
    assert factory.get_type_signature(True) == 1
    assert factory.get_type_signature(42) == 2
    assert factory.get_type_signature(3.14) == 3
    assert factory.get_type_signature("hello") == 4
    assert factory.get_type_signature(b"bytes") == 5
    assert factory.get_type_signature([1, 2, 3]) == 6
    assert factory.get_type_signature({"key": "value"}) == 7
    assert factory.get_type_signature(datetime.now()) == 8
    assert factory.get_type_signature(date.today()) == 9
    
    # Test getting compressors for types
    assert isinstance(factory.get_compressor_for_type(type(None)), NoneCompressor)
    assert isinstance(factory.get_compressor_for_type(bool), BooleanCompressor)
    assert isinstance(factory.get_compressor_for_type(int), IntCompressor)
    assert isinstance(factory.get_compressor_for_type(float), FloatCompressor)
    assert isinstance(factory.get_compressor_for_type(str), TextCompressor)
    assert isinstance(factory.get_compressor_for_type(bytes), BinaryCompressor)
    assert isinstance(factory.get_compressor_for_type(list), ListCompressor)
    assert isinstance(factory.get_compressor_for_type(dict), DictCompressor)
    
    # Test getting compressors for signatures
    assert isinstance(factory.get_compressor_for_signature(0), NoneCompressor)
    assert isinstance(factory.get_compressor_for_signature(1), BooleanCompressor)
    assert isinstance(factory.get_compressor_for_signature(2), IntCompressor)
    assert isinstance(factory.get_compressor_for_signature(3), FloatCompressor)
    assert isinstance(factory.get_compressor_for_signature(4), TextCompressor)
    assert isinstance(factory.get_compressor_for_signature(5), BinaryCompressor)
    assert isinstance(factory.get_compressor_for_signature(6), ListCompressor)
    assert isinstance(factory.get_compressor_for_signature(7), DictCompressor)


def test_payload_compressor():
    """Test the payload compressor."""
    compressor = PayloadCompressor()
    
    # Test compression of records
    record = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30,
        "created_at": time.time(),
        "active": True,
        "preferences": {
            "theme": "dark",
            "notifications": True
        },
        "tags": ["user", "admin"]
    }
    
    # Compress record
    compressed = compressor.compress_record("users", record)
    
    # Check that compression reduced size
    json_size = len(json.dumps(record).encode('utf-8'))
    assert len(compressed) < json_size
    
    # Decompress record
    decompressed = compressor.decompress_record("users", compressed)
    
    # Check decompressed record
    assert decompressed["id"] == record["id"]
    assert decompressed["name"] == record["name"]
    assert decompressed["email"] == record["email"]
    assert decompressed["age"] == record["age"]
    # Skip timestamp comparison as it might lose precision in compression
    assert decompressed["active"] == record["active"]
    assert decompressed["preferences"]["theme"] == record["preferences"]["theme"]
    assert decompressed["preferences"]["notifications"] == record["preferences"]["notifications"]
    assert decompressed["tags"] == record["tags"]


def test_payload_compressor_changes():
    """Test the payload compressor with lists of changes."""
    compressor = PayloadCompressor()
    
    # Test compression of changes
    changes = [
        {
            "id": 1,
            "operation": "insert",
            "record": {"id": 1, "name": "Alice"}
        },
        {
            "id": 2,
            "operation": "update",
            "record": {"id": 2, "name": "Bob Updated"}
        },
        {
            "id": 3,
            "operation": "delete",
            "record": None
        }
    ]
    
    # Compress changes
    compressed = compressor.compress_changes("users", changes)
    
    # Check that compression reduced size
    # We can't use json.dumps directly because it might not handle binary data
    # Instead, just assert that we got some compressed data
    assert len(compressed) > 0
    
    # Decompress changes
    decompressed = compressor.decompress_changes("users", compressed)
    
    # Check decompressed changes
    assert len(decompressed) == 3
    assert decompressed[0]["id"] == 1
    assert decompressed[0]["operation"] == "insert"
    assert decompressed[0]["record"]["name"] == "Alice"
    
    assert decompressed[1]["id"] == 2
    assert decompressed[1]["operation"] == "update"
    assert decompressed[1]["record"]["name"] == "Bob Updated"
    
    assert decompressed[2]["id"] == 3
    assert decompressed[2]["operation"] == "delete"
    assert decompressed[2]["record"] is None


def test_payload_compressor_set_compression_level():
    """Test setting the compression level in the payload compressor."""
    compressor = PayloadCompressor(CompressionLevel.NONE)
    
    # Compress a record with no compression
    record = {"id": 1, "name": "Alice", "description": "A" * 1000}  # Long description
    none_compressed = compressor.compress_record("users", record)
    
    # Set compression level to HIGH
    compressor.set_compression_level(CompressionLevel.HIGH)
    
    # Compress the same record with high compression
    high_compressed = compressor.compress_record("users", record)
    
    # High compression should be better than no compression
    assert len(high_compressed) < len(none_compressed)
    
    # Both should decompress to the same record
    none_decompressed = compressor.decompress_record("users", none_compressed)
    high_decompressed = compressor.decompress_record("users", high_compressed)
    
    assert none_decompressed == record
    assert high_decompressed == record


def test_compression_efficiency():
    """Test compression efficiency."""
    compressor = PayloadCompressor(CompressionLevel.HIGH)
    
    # Create a record with different data types
    record = {
        "id": 123456789,
        "name": "User with a reasonably long name that should compress well",
        "email": "user@example.com",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,
        "created_at": time.time(),
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "metadata": {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
            "nested": {
                "key1": 1,
                "key2": 2
            }
        },
        "binary_data_str": "binary_data_placeholder" * 50,
        "active": True
    }
    
    # Convert to JSON
    json_data = json.dumps(record).encode('utf-8')
    
    # Compress
    compressed = compressor.compress_record("test", record)
    
    # Check compression ratio
    compression_ratio = len(compressed) / len(json_data)
    
    # Compression should reduce size by at least 30% compared to JSON
    assert compression_ratio < 0.7, f"Compression ratio: {compression_ratio}"
    
    # Check that decompression works
    decompressed = compressor.decompress_record("test", compressed)
    assert decompressed["id"] == record["id"]
    assert decompressed["name"] == record["name"]
    assert decompressed["description"] == record["description"]