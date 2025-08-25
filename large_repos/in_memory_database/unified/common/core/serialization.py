"""Serialization utilities for the unified library."""

from typing import Any, Dict, Type, Callable, Optional, Tuple, List
from abc import ABC, abstractmethod
import json
import pickle
import base64
from datetime import datetime, date
from decimal import Decimal
from dataclasses import is_dataclass, asdict
from enum import Enum
import struct


class Serializable(ABC):
    """Mixin for serializable objects."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable':
        """Create object from dictionary."""
        pass
    
    def to_json(self, **kwargs) -> str:
        """Convert object to JSON string."""
        return json.dumps(self.to_dict(), cls=ExtendedJSONEncoder, **kwargs)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Serializable':
        """Create object from JSON string."""
        return cls.from_dict(json.loads(json_str, cls=ExtendedJSONDecoder))
    
    def to_bytes(self, encoding: str = 'json') -> bytes:
        """Convert object to bytes.
        
        Args:
            encoding: Encoding to use ('json', 'pickle', 'msgpack-like')
        """
        if encoding == 'json':
            return self.to_json().encode('utf-8')
        elif encoding == 'pickle':
            return pickle.dumps(self.to_dict())
        elif encoding == 'msgpack-like':
            return SimpleMsgPack.pack(self.to_dict())
        else:
            raise ValueError(f"Unknown encoding: {encoding}")
    
    @classmethod
    def from_bytes(cls, data: bytes, encoding: str = 'json') -> 'Serializable':
        """Create object from bytes.
        
        Args:
            data: Bytes to decode
            encoding: Encoding used ('json', 'pickle', 'msgpack-like')
        """
        if encoding == 'json':
            return cls.from_json(data.decode('utf-8'))
        elif encoding == 'pickle':
            return cls.from_dict(pickle.loads(data))
        elif encoding == 'msgpack-like':
            return cls.from_dict(SimpleMsgPack.unpack(data))
        else:
            raise ValueError(f"Unknown encoding: {encoding}")


class ExtendedJSONEncoder(json.JSONEncoder):
    """Extended JSON encoder supporting additional types."""
    
    def default(self, obj):
        """Encode additional types."""
        # Datetime types
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'value': obj.isoformat()
            }
        elif isinstance(obj, date):
            return {
                '__type__': 'date',
                'value': obj.isoformat()
            }
        
        # Decimal
        elif isinstance(obj, Decimal):
            return {
                '__type__': 'decimal',
                'value': str(obj)
            }
        
        # Bytes
        elif isinstance(obj, bytes):
            return {
                '__type__': 'bytes',
                'value': base64.b64encode(obj).decode('ascii')
            }
        
        # Sets
        elif isinstance(obj, set):
            return {
                '__type__': 'set',
                'value': list(obj)
            }
        
        # Enums
        elif isinstance(obj, Enum):
            return {
                '__type__': 'enum',
                'class': obj.__class__.__name__,
                'value': obj.value
            }
        
        # Dataclasses
        elif is_dataclass(obj):
            return {
                '__type__': 'dataclass',
                'class': obj.__class__.__name__,
                'value': asdict(obj)
            }
        
        # Serializable objects
        elif hasattr(obj, 'to_dict'):
            return {
                '__type__': 'serializable',
                'class': obj.__class__.__name__,
                'value': obj.to_dict()
            }
        
        return super().default(obj)


class ExtendedJSONDecoder(json.JSONDecoder):
    """Extended JSON decoder supporting additional types."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
    
    def object_hook(self, dct):
        """Decode additional types."""
        if '__type__' not in dct:
            return dct
        
        type_name = dct['__type__']
        value = dct['value']
        
        # Datetime types
        if type_name == 'datetime':
            return datetime.fromisoformat(value)
        elif type_name == 'date':
            return date.fromisoformat(value)
        
        # Decimal
        elif type_name == 'decimal':
            return Decimal(value)
        
        # Bytes
        elif type_name == 'bytes':
            return base64.b64decode(value.encode('ascii'))
        
        # Sets
        elif type_name == 'set':
            return set(value)
        
        # For enums, dataclasses, and serializable objects,
        # we return the dict as-is since we don't have the class references
        return dct


class SerializationContext:
    """Context for complex serialization with type registry."""
    
    def __init__(self):
        """Initialize serialization context."""
        self._type_serializers: Dict[Type, Callable] = {}
        self._type_deserializers: Dict[str, Callable] = {}
        self._register_defaults()
    
    def register_type(self, type_class: Type, 
                     serializer: Callable[[Any], Dict],
                     deserializer: Callable[[Dict], Any],
                     type_name: Optional[str] = None) -> None:
        """Register custom serialization for a type.
        
        Args:
            type_class: The class to register
            serializer: Function to serialize instances
            deserializer: Function to deserialize data
            type_name: Optional type name (defaults to class name)
        """
        self._type_serializers[type_class] = serializer
        name = type_name or type_class.__name__
        self._type_deserializers[name] = deserializer
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        data = self._serialize_value(obj)
        return json.dumps(data).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object."""
        json_data = json.loads(data.decode('utf-8'))
        return self._deserialize_value(json_data)
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value."""
        # Check for registered types
        for type_class, serializer in self._type_serializers.items():
            if isinstance(value, type_class):
                return {
                    '__type__': type_class.__name__,
                    'data': serializer(value)
                }
        
        # Handle built-in types
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, bytes):
            return {
                '__type__': 'bytes',
                'data': base64.b64encode(value).decode('ascii')
            }
        elif hasattr(value, 'to_dict'):
            return {
                '__type__': value.__class__.__name__,
                'data': value.to_dict()
            }
        else:
            # Fallback to pickle for unknown types
            return {
                '__type__': 'pickle',
                'data': base64.b64encode(pickle.dumps(value)).decode('ascii')
            }
    
    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize a single value."""
        if isinstance(value, dict) and '__type__' in value:
            type_name = value['__type__']
            data = value['data']
            
            # Check for registered deserializers
            if type_name in self._type_deserializers:
                return self._type_deserializers[type_name](data)
            
            # Handle built-in special types
            elif type_name == 'bytes':
                return base64.b64decode(data.encode('ascii'))
            elif type_name == 'pickle':
                return pickle.loads(base64.b64decode(data.encode('ascii')))
            else:
                # Return as-is if we can't deserialize
                return value
        
        elif isinstance(value, list):
            return [self._deserialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._deserialize_value(v) for k, v in value.items()}
        else:
            return value
    
    def _register_defaults(self) -> None:
        """Register default type serializers."""
        # Datetime
        self.register_type(
            datetime,
            lambda dt: dt.isoformat(),
            lambda s: datetime.fromisoformat(s),
            'datetime'
        )
        
        # Date
        self.register_type(
            date,
            lambda d: d.isoformat(),
            lambda s: date.fromisoformat(s),
            'date'
        )
        
        # Decimal
        self.register_type(
            Decimal,
            lambda d: str(d),
            lambda s: Decimal(s),
            'decimal'
        )
        
        # Set
        self.register_type(
            set,
            lambda s: list(s),
            lambda l: set(l),
            'set'
        )


class SimpleMsgPack:
    """Simple MessagePack-like binary serialization."""
    
    # Type codes
    NIL = 0xc0
    FALSE = 0xc2
    TRUE = 0xc3
    UINT8 = 0xcc
    UINT16 = 0xcd
    UINT32 = 0xce
    INT8 = 0xd0
    INT16 = 0xd1
    INT32 = 0xd2
    FLOAT32 = 0xca
    FLOAT64 = 0xcb
    STR8 = 0xd9
    STR16 = 0xda
    BIN8 = 0xc4
    BIN16 = 0xc5
    ARRAY16 = 0xdc
    MAP16 = 0xde
    
    @classmethod
    def pack(cls, obj: Any) -> bytes:
        """Pack an object to bytes."""
        buffer = bytearray()
        cls._pack_value(obj, buffer)
        return bytes(buffer)
    
    @classmethod
    def unpack(cls, data: bytes) -> Any:
        """Unpack bytes to an object."""
        return cls._unpack_value(data, [0])[0]
    
    @classmethod
    def _pack_value(cls, value: Any, buffer: bytearray) -> None:
        """Pack a single value."""
        if value is None:
            buffer.append(cls.NIL)
        
        elif value is False:
            buffer.append(cls.FALSE)
        
        elif value is True:
            buffer.append(cls.TRUE)
        
        elif isinstance(value, int):
            if 0 <= value <= 127:
                buffer.append(value)
            elif -32 <= value < 0:
                buffer.append(0xe0 | (value + 32))
            elif 0 <= value <= 0xff:
                buffer.append(cls.UINT8)
                buffer.append(value)
            elif -0x80 <= value <= 0x7f:
                buffer.append(cls.INT8)
                buffer.extend(struct.pack('b', value))
            elif 0 <= value <= 0xffff:
                buffer.append(cls.UINT16)
                buffer.extend(struct.pack('>H', value))
            elif -0x8000 <= value <= 0x7fff:
                buffer.append(cls.INT16)
                buffer.extend(struct.pack('>h', value))
            elif 0 <= value <= 0xffffffff:
                buffer.append(cls.UINT32)
                buffer.extend(struct.pack('>I', value))
            elif -0x80000000 <= value <= 0x7fffffff:
                buffer.append(cls.INT32)
                buffer.extend(struct.pack('>i', value))
            else:
                # Fallback to float for large numbers
                buffer.append(cls.FLOAT64)
                buffer.extend(struct.pack('>d', float(value)))
        
        elif isinstance(value, float):
            buffer.append(cls.FLOAT64)
            buffer.extend(struct.pack('>d', value))
        
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            length = len(encoded)
            
            if length <= 31:
                buffer.append(0xa0 | length)
            elif length <= 0xff:
                buffer.append(cls.STR8)
                buffer.append(length)
            elif length <= 0xffff:
                buffer.append(cls.STR16)
                buffer.extend(struct.pack('>H', length))
            else:
                raise ValueError(f"String too long: {length}")
            
            buffer.extend(encoded)
        
        elif isinstance(value, bytes):
            length = len(value)
            
            if length <= 0xff:
                buffer.append(cls.BIN8)
                buffer.append(length)
            elif length <= 0xffff:
                buffer.append(cls.BIN16)
                buffer.extend(struct.pack('>H', length))
            else:
                raise ValueError(f"Bytes too long: {length}")
            
            buffer.extend(value)
        
        elif isinstance(value, (list, tuple)):
            length = len(value)
            
            if length <= 15:
                buffer.append(0x90 | length)
            elif length <= 0xffff:
                buffer.append(cls.ARRAY16)
                buffer.extend(struct.pack('>H', length))
            else:
                raise ValueError(f"Array too long: {length}")
            
            for item in value:
                cls._pack_value(item, buffer)
        
        elif isinstance(value, dict):
            length = len(value)
            
            if length <= 15:
                buffer.append(0x80 | length)
            elif length <= 0xffff:
                buffer.append(cls.MAP16)
                buffer.extend(struct.pack('>H', length))
            else:
                raise ValueError(f"Map too long: {length}")
            
            for k, v in value.items():
                cls._pack_value(k, buffer)
                cls._pack_value(v, buffer)
        
        else:
            # Fallback to JSON string
            json_str = json.dumps(value)
            cls._pack_value(json_str, buffer)
    
    @classmethod
    def _unpack_value(cls, data: bytes, offset: List[int]) -> Tuple[Any, None]:
        """Unpack a single value."""
        if offset[0] >= len(data):
            raise ValueError("Unexpected end of data")
        
        byte = data[offset[0]]
        offset[0] += 1
        
        # Fixed values
        if byte == cls.NIL:
            return None, None
        elif byte == cls.FALSE:
            return False, None
        elif byte == cls.TRUE:
            return True, None
        
        # Positive fixint
        elif byte <= 0x7f:
            return byte, None
        
        # Fixmap
        elif 0x80 <= byte <= 0x8f:
            length = byte & 0x0f
            result = {}
            for _ in range(length):
                k, _ = cls._unpack_value(data, offset)
                v, _ = cls._unpack_value(data, offset)
                result[k] = v
            return result, None
        
        # Fixarray
        elif 0x90 <= byte <= 0x9f:
            length = byte & 0x0f
            result = []
            for _ in range(length):
                v, _ = cls._unpack_value(data, offset)
                result.append(v)
            return result, None
        
        # Fixstr
        elif 0xa0 <= byte <= 0xbf:
            length = byte & 0x1f
            s = data[offset[0]:offset[0]+length].decode('utf-8')
            offset[0] += length
            return s, None
        
        # Negative fixint
        elif 0xe0 <= byte <= 0xff:
            return byte - 256, None
        
        # Type-specific unpacking
        elif byte == cls.UINT8:
            v = data[offset[0]]
            offset[0] += 1
            return v, None
        
        elif byte == cls.UINT16:
            v = struct.unpack('>H', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            return v, None
        
        elif byte == cls.UINT32:
            v = struct.unpack('>I', data[offset[0]:offset[0]+4])[0]
            offset[0] += 4
            return v, None
        
        elif byte == cls.INT8:
            v = struct.unpack('b', data[offset[0]:offset[0]+1])[0]
            offset[0] += 1
            return v, None
        
        elif byte == cls.INT16:
            v = struct.unpack('>h', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            return v, None
        
        elif byte == cls.INT32:
            v = struct.unpack('>i', data[offset[0]:offset[0]+4])[0]
            offset[0] += 4
            return v, None
        
        elif byte == cls.FLOAT32:
            v = struct.unpack('>f', data[offset[0]:offset[0]+4])[0]
            offset[0] += 4
            return v, None
        
        elif byte == cls.FLOAT64:
            v = struct.unpack('>d', data[offset[0]:offset[0]+8])[0]
            offset[0] += 8
            return v, None
        
        elif byte == cls.STR8:
            length = data[offset[0]]
            offset[0] += 1
            s = data[offset[0]:offset[0]+length].decode('utf-8')
            offset[0] += length
            return s, None
        
        elif byte == cls.STR16:
            length = struct.unpack('>H', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            s = data[offset[0]:offset[0]+length].decode('utf-8')
            offset[0] += length
            return s, None
        
        elif byte == cls.BIN8:
            length = data[offset[0]]
            offset[0] += 1
            b = data[offset[0]:offset[0]+length]
            offset[0] += length
            return bytes(b), None
        
        elif byte == cls.BIN16:
            length = struct.unpack('>H', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            b = data[offset[0]:offset[0]+length]
            offset[0] += length
            return bytes(b), None
        
        elif byte == cls.ARRAY16:
            length = struct.unpack('>H', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            result = []
            for _ in range(length):
                v, _ = cls._unpack_value(data, offset)
                result.append(v)
            return result, None
        
        elif byte == cls.MAP16:
            length = struct.unpack('>H', data[offset[0]:offset[0]+2])[0]
            offset[0] += 2
            result = {}
            for _ in range(length):
                k, _ = cls._unpack_value(data, offset)
                v, _ = cls._unpack_value(data, offset)
                result[k] = v
            return result, None
        
        else:
            raise ValueError(f"Unknown type code: {hex(byte)}")