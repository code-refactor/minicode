"""
Tests for the asset chunking module.
"""

import os
import random
import struct
import tempfile
from pathlib import Path

import pytest

from gamevault.asset_optimization.chunking import (AssetChunker,
                                                 AssetChunkerFactory,
                                                 AudioChunker, ModelChunker,
                                                 TextureChunker)


@pytest.fixture
def test_data():
    """Generate test binary data for chunking."""
    # Create a simulated PNG file
    png_header = b"\x89PNG\r\n\x1a\n"
    png_ihdr = b"IHDR" + b"\x00" * 13
    png_data1 = b"IDAT" + os.urandom(1000)
    png_data2 = b"IDAT" + os.urandom(2000)
    png_footer = b"IEND" + b"\x00" * 4
    
    # Add length fields and chunk types to create a more realistic PNG
    def add_chunk(chunk_type, data):
        length = struct.pack(">I", len(data))
        crc = b"\x00\x00\x00\x00"  # Dummy CRC
        return length + chunk_type + data + crc
    
    simulated_png = (
        png_header +
        add_chunk(b"IHDR", b"\x00" * 13) +
        add_chunk(b"IDAT", os.urandom(1000)) +
        add_chunk(b"IDAT", os.urandom(2000)) +
        add_chunk(b"IEND", b"")
    )
    
    # Create a simulated WAV file
    wav_header = b"RIFF" + struct.pack("<I", 36 + 1000 + 2000) + b"WAVE"
    wav_fmt = b"fmt " + struct.pack("<I", 16) + b"\x01\x00\x02\x00\x44\xAC\x00\x00\x10\xB1\x02\x00\x04\x00\x10\x00"
    wav_data = b"data" + struct.pack("<I", 1000 + 2000) + os.urandom(1000 + 2000)
    simulated_wav = wav_header + wav_fmt + wav_data
    
    # Create a simulated FBX file
    simulated_fbx = b"Kaydara FBX Binary\x00" + os.urandom(5000)
    
    # Create random binary data
    random_data = os.urandom(10000)
    
    return {
        "png": simulated_png,
        "wav": simulated_wav,
        "fbx": simulated_fbx,
        "random": random_data
    }


def test_base_chunker(test_data):
    """Test the base asset chunker."""
    chunker = AssetChunker()
    
    # Chunk random data using gamevault interface
    chunks = chunker.chunk_file(test_data["random"])
    
    # Verify we get at least one chunk
    assert len(chunks) > 0
    
    # Verify reassembling the chunks produces the original data
    reassembled = b"".join(chunks)
    assert reassembled == test_data["random"]
    
    # Test with file extension hint
    chunks_with_hint = chunker.chunk_file(test_data["random"], ".bin")
    
    # Verify chunking with hint still works
    reassembled = b"".join(chunks_with_hint)
    assert reassembled == test_data["random"]


def test_texture_chunker(test_data):
    """Test the texture chunker."""
    chunker = TextureChunker()
    
    # Chunk PNG data
    chunks = chunker.chunk_file(test_data["png"], ".png")
    
    # Verify we get multiple chunks for the PNG
    assert len(chunks) > 0
    
    # Verify reassembling the chunks produces the original data
    reassembled = b"".join(chunks)
    assert reassembled == test_data["png"]
    
    # Test auto-detection
    auto_chunks = chunker.chunk_file(test_data["png"])
    assert len(auto_chunks) > 0
    reassembled = b"".join(auto_chunks)
    assert reassembled == test_data["png"]


def test_audio_chunker(test_data):
    """Test the audio chunker."""
    chunker = AudioChunker()
    
    # Chunk WAV data
    chunks = chunker.chunk_file(test_data["wav"], ".wav")
    
    # Verify we get multiple chunks for the WAV
    assert len(chunks) > 0
    
    # Verify reassembling the chunks produces the original data
    reassembled = b"".join(chunks)
    assert reassembled == test_data["wav"]
    
    # Test auto-detection
    auto_chunks = chunker.chunk_file(test_data["wav"])
    reassembled = b"".join(auto_chunks)
    assert reassembled == test_data["wav"]


def test_model_chunker(test_data):
    """Test the model chunker."""
    chunker = ModelChunker()
    
    # Chunk FBX data
    chunks = chunker.chunk_file(test_data["fbx"], ".fbx")
    
    # Verify we get chunks
    assert len(chunks) > 0
    
    # Verify reassembling the chunks produces the original data
    reassembled = b"".join(chunks)
    assert reassembled == test_data["fbx"]
    
    # Test auto-detection
    auto_chunks = chunker.chunk_file(test_data["fbx"])
    reassembled = b"".join(auto_chunks)
    assert reassembled == test_data["fbx"]


def test_chunker_factory():
    """Test the asset chunker factory."""
    # Test texture file extensions
    texture_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".psd"]
    for ext in texture_extensions:
        chunker = AssetChunkerFactory.get_chunker(ext)
        assert isinstance(chunker, TextureChunker)
    
    # Test audio file extensions
    audio_extensions = [".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"]
    for ext in audio_extensions:
        chunker = AssetChunkerFactory.get_chunker(ext)
        assert isinstance(chunker, AudioChunker)
    
    # Test model file extensions
    model_extensions = [".fbx", ".obj", ".blend", ".dae", ".3ds", ".max"]
    for ext in model_extensions:
        chunker = AssetChunkerFactory.get_chunker(ext)
        assert isinstance(chunker, ModelChunker)
    
    # Test unknown extension
    default_chunker = AssetChunkerFactory.get_chunker(".unknown")
    assert isinstance(default_chunker, AssetChunker)


def test_chunker_edge_cases():
    """Test chunking with edge cases like empty data and small data."""
    chunkers = [
        AssetChunker(),
        TextureChunker(),
        AudioChunker(),
        ModelChunker()
    ]
    
    # Test with empty data
    for chunker in chunkers:
        chunks = chunker.chunk_file(b"")
        assert chunks == []
    
    # Test with very small data
    small_data = b"Small data"
    for chunker in chunkers:
        chunks = chunker.chunk_file(small_data)
        assert len(chunks) == 1
        assert chunks[0] == small_data


def test_chunk_size_constraints():
    """Test that chunks respect size constraints."""
    # Create a large repeating pattern
    data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 10000
    
    # Create chunkers with different min/max sizes
    chunker1 = AssetChunker(min_chunk_size=64 * 1024, max_chunk_size=128 * 1024)
    chunker2 = AssetChunker(min_chunk_size=32 * 1024, max_chunk_size=64 * 1024)
    
    # Chunk the data
    chunks1 = chunker1.chunk_file(data)
    chunks2 = chunker2.chunk_file(data)
    
    # Verify chunk sizes respect constraints
    for chunk in chunks1:
        assert len(chunk) >= 64 * 1024
        assert len(chunk) <= 128 * 1024
    
    for chunk in chunks2:
        assert len(chunk) >= 32 * 1024
        assert len(chunk) <= 64 * 1024
    
    # Chunker with smaller max size should produce more chunks
    assert len(chunks2) >= len(chunks1)
    
    # Verify reassembling works
    assert b"".join(chunks1) == data
    assert b"".join(chunks2) == data