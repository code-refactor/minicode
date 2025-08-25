"""Delta compression for versioned files."""

import struct
from typing import Optional, List, Tuple


class DeltaCompressor:
    """Binary delta compression for versioned files."""
    
    def __init__(self, block_size: int = 4096):
        """
        Initialize delta compressor.
        
        Args:
            block_size: Block size for delta computation
        """
        self.block_size = block_size
        self._has_bsdiff = False
        
        try:
            import bsdiff4
            self._has_bsdiff = True
        except ImportError:
            pass
    
    def create_delta(self, old_data: bytes, new_data: bytes) -> bytes:
        """
        Create a delta between two versions.
        
        Args:
            old_data: Original data
            new_data: New data
        
        Returns:
            Delta data
        """
        if self._has_bsdiff:
            try:
                import bsdiff4
                return bsdiff4.diff(old_data, new_data)
            except Exception:
                pass
        
        # Fallback to simple delta implementation
        return self._simple_delta(old_data, new_data)
    
    def apply_delta(self, old_data: bytes, delta_data: bytes) -> bytes:
        """
        Apply a delta to recreate the new version.
        
        Args:
            old_data: Original data
            delta_data: Delta data
        
        Returns:
            New data
        """
        if self._has_bsdiff and delta_data.startswith(b'BSDIFF'):
            try:
                import bsdiff4
                return bsdiff4.patch(old_data, delta_data)
            except Exception:
                pass
        
        # Fallback to simple delta application
        return self._apply_simple_delta(old_data, delta_data)
    
    def is_delta_efficient(self, old_data: bytes, new_data: bytes, 
                          threshold: float = 0.7) -> bool:
        """
        Check if using delta would be more efficient than storing full data.
        
        Args:
            old_data: Original data
            new_data: New data
            threshold: Size ratio threshold
        
        Returns:
            True if delta is efficient
        """
        # Don't use delta for small files
        if len(new_data) < 1024:
            return False
        
        # Quick check: if sizes are very different, delta might not help
        size_ratio = len(new_data) / max(len(old_data), 1)
        if size_ratio > 2 or size_ratio < 0.5:
            return False
        
        # Estimate delta size (sample-based)
        sample_size = min(10240, len(new_data))
        sample_old = old_data[:sample_size]
        sample_new = new_data[:sample_size]
        
        delta = self.create_delta(sample_old, sample_new)
        delta_ratio = len(delta) / len(sample_new)
        
        return delta_ratio < threshold
    
    def _simple_delta(self, old_data: bytes, new_data: bytes) -> bytes:
        """
        Create a simple delta using block-based comparison.
        
        Args:
            old_data: Original data
            new_data: New data
        
        Returns:
            Simple delta format
        """
        operations = []
        
        # Find common blocks
        old_blocks = self._create_block_index(old_data)
        new_offset = 0
        
        while new_offset < len(new_data):
            # Try to find matching block
            block_end = min(new_offset + self.block_size, len(new_data))
            block = new_data[new_offset:block_end]
            block_hash = hash(block)
            
            if block_hash in old_blocks:
                # Found matching block
                old_offset = old_blocks[block_hash]
                operations.append(('copy', old_offset, len(block)))
                new_offset = block_end
            else:
                # No match, add literal data
                literal_end = new_offset + 1
                while literal_end < len(new_data):
                    test_block = new_data[literal_end:literal_end + self.block_size]
                    if hash(test_block) in old_blocks:
                        break
                    literal_end += 1
                
                literal_data = new_data[new_offset:literal_end]
                operations.append(('add', literal_data))
                new_offset = literal_end
        
        # Encode operations
        return self._encode_operations(operations)
    
    def _apply_simple_delta(self, old_data: bytes, delta_data: bytes) -> bytes:
        """
        Apply simple delta to recreate new data.
        
        Args:
            old_data: Original data
            delta_data: Delta data
        
        Returns:
            New data
        """
        operations = self._decode_operations(delta_data)
        result = []
        
        for op in operations:
            if op[0] == 'copy':
                _, offset, length = op
                result.append(old_data[offset:offset + length])
            elif op[0] == 'add':
                _, data = op
                result.append(data)
        
        return b''.join(result)
    
    def _create_block_index(self, data: bytes) -> dict:
        """
        Create index of blocks for matching.
        
        Args:
            data: Data to index
        
        Returns:
            Dictionary mapping block hash to offset
        """
        index = {}
        for offset in range(0, len(data), self.block_size):
            block = data[offset:offset + self.block_size]
            block_hash = hash(block)
            if block_hash not in index:
                index[block_hash] = offset
        return index
    
    def _encode_operations(self, operations: List[Tuple]) -> bytes:
        """
        Encode delta operations to bytes.
        
        Args:
            operations: List of operations
        
        Returns:
            Encoded delta
        """
        result = [b'SIMPLE_DELTA_V1']
        
        for op in operations:
            if op[0] == 'copy':
                # Format: 'C' + offset (4 bytes) + length (4 bytes)
                result.append(b'C')
                result.append(struct.pack('!II', op[1], op[2]))
            elif op[0] == 'add':
                # Format: 'A' + length (4 bytes) + data
                data = op[1]
                result.append(b'A')
                result.append(struct.pack('!I', len(data)))
                result.append(data)
        
        return b''.join(result)
    
    def _decode_operations(self, delta_data: bytes) -> List[Tuple]:
        """
        Decode delta operations from bytes.
        
        Args:
            delta_data: Encoded delta
        
        Returns:
            List of operations
        """
        if not delta_data.startswith(b'SIMPLE_DELTA_V1'):
            raise ValueError("Invalid delta format")
        
        operations = []
        offset = len(b'SIMPLE_DELTA_V1')
        
        while offset < len(delta_data):
            op_type = delta_data[offset:offset + 1]
            offset += 1
            
            if op_type == b'C':
                # Copy operation
                old_offset, length = struct.unpack('!II', delta_data[offset:offset + 8])
                operations.append(('copy', old_offset, length))
                offset += 8
            elif op_type == b'A':
                # Add operation
                length = struct.unpack('!I', delta_data[offset:offset + 4])[0]
                offset += 4
                data = delta_data[offset:offset + length]
                operations.append(('add', data))
                offset += length
        
        return operations