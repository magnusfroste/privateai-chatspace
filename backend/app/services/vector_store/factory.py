"""
Vector Store Factory - Creates the appropriate vector store based on configuration.

This module implements the factory pattern to instantiate the correct
vector store implementation based on the VECTOR_STORE setting (admin-configurable).
"""

from typing import Optional, Dict
from app.core.config import settings
from app.services.vector_store.base import VectorStoreBase

# Cache vector store instances by type
_vector_store_instances: Dict[str, VectorStoreBase] = {}
_current_store_type: Optional[str] = None


def _get_store_type_from_config() -> str:
    """Get vector store type from config (sync, for startup)"""
    return getattr(settings, 'VECTOR_STORE', 'qdrant').lower()


def _create_store(store_type: str) -> VectorStoreBase:
    """Create a vector store instance of the specified type"""
    if store_type == "lancedb":
        from app.services.vector_store.lancedb_store import LanceDBVectorStore
        return LanceDBVectorStore()
    else:
        from app.services.vector_store.qdrant_store import QdrantVectorStore
        return QdrantVectorStore()


def get_vector_store(store_type: Optional[str] = None) -> VectorStoreBase:
    """
    Get the configured vector store instance.
    
    Caches instances by type so switching between stores is efficient.
    The vector store type is determined by:
    1. Explicit store_type parameter (if provided)
    2. Current active store type (set by admin via set_vector_store_type)
    3. VECTOR_STORE environment variable (default)
    
    Returns:
        VectorStoreBase implementation
    """
    global _vector_store_instances, _current_store_type
    
    # Use provided type, or current active type, or config default
    if store_type is None:
        if _current_store_type is not None:
            store_type = _current_store_type
        else:
            store_type = _get_store_type_from_config()
    
    store_type = store_type.lower()
    
    # Create instance if not cached
    if store_type not in _vector_store_instances:
        _vector_store_instances[store_type] = _create_store(store_type)
        print(f"Vector store initialized: {store_type.upper()}")
    
    # Track current type
    if _current_store_type != store_type:
        _current_store_type = store_type
        print(f"Vector store active: {store_type.upper()}")
    
    return _vector_store_instances[store_type]


def get_current_store_type() -> str:
    """Get the currently active vector store type"""
    global _current_store_type, _vector_store_instances
    
    # If we have an active store, return its type
    if _current_store_type is not None:
        return _current_store_type
    
    # Otherwise get from config
    _current_store_type = _get_store_type_from_config()
    return _current_store_type


def set_vector_store_type(store_type: str) -> VectorStoreBase:
    """
    Switch to a different vector store type.
    
    Called when admin changes the vector_store setting.
    Returns the new active store instance.
    """
    global _current_store_type
    store_type = store_type.lower()
    
    if store_type not in ("qdrant", "lancedb"):
        raise ValueError(f"Invalid vector store type: {store_type}")
    
    _current_store_type = store_type
    return get_vector_store(store_type)


def reset_vector_store() -> None:
    """
    Reset all vector store instances.
    
    Useful for testing or when configuration changes.
    """
    global _vector_store_instances, _current_store_type
    _vector_store_instances = {}
    _current_store_type = None
