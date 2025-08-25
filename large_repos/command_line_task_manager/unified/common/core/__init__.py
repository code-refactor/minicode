"""Core components of the common library."""

from .models import (
    BaseEntity,
    TimestampedMixin,
    StatusMixin,
    TaggedMixin,
    ValidationMixin,
    NamedEntity,
    HierarchicalEntity,
    StatusChange,
    ValidationError
)

from .storage import (
    StorageInterface,
    InMemoryStorage,
    FileStorage
)

from .service import (
    BaseService,
    ServiceRegistry,
    CrossReferenceValidator
)

from .validation import (
    validate_uuid,
    validate_email,
    validate_date_range,
    validate_enum_value,
    validate_required,
    validate_string_length,
    validate_number_range,
    validate_url,
    validate_file_path,
    validate_list_length,
    validate_dict_keys,
    validate_regex,
    CompositeValidator,
    FieldValidator
)

from .utils import (
    to_dict,
    from_dict,
    json_encoder,
    json_decoder_hook,
    ensure_directory,
    safe_file_write,
    atomic_file_update,
    merge_metadata,
    filter_dict,
    deep_update,
    flatten_dict,
    unflatten_dict,
    chunk_list,
    batch_process,
    safe_get_nested,
    safe_set_nested,
    generate_id,
    format_file_size,
    parse_file_size,
    create_backup,
    restore_backup
)

__all__ = [
    # Models
    'BaseEntity',
    'TimestampedMixin',
    'StatusMixin',
    'TaggedMixin',
    'ValidationMixin',
    'NamedEntity',
    'HierarchicalEntity',
    'StatusChange',
    'ValidationError',
    
    # Storage
    'StorageInterface',
    'InMemoryStorage',
    'FileStorage',
    
    # Service
    'BaseService',
    'ServiceRegistry',
    'CrossReferenceValidator',
    
    # Validation
    'validate_uuid',
    'validate_email',
    'validate_date_range',
    'validate_enum_value',
    'validate_required',
    'validate_string_length',
    'validate_number_range',
    'validate_url',
    'validate_file_path',
    'validate_list_length',
    'validate_dict_keys',
    'validate_regex',
    'CompositeValidator',
    'FieldValidator',
    
    # Utils
    'to_dict',
    'from_dict',
    'json_encoder',
    'json_decoder_hook',
    'ensure_directory',
    'safe_file_write',
    'atomic_file_update',
    'merge_metadata',
    'filter_dict',
    'deep_update',
    'flatten_dict',
    'unflatten_dict',
    'chunk_list',
    'batch_process',
    'safe_get_nested',
    'safe_set_nested',
    'generate_id',
    'format_file_size',
    'parse_file_size',
    'create_backup',
    'restore_backup'
]
