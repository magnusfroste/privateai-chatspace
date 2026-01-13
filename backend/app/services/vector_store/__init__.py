"""
Vector Store Module - Abstraction layer for vector databases.

Provides a unified interface for different vector store backends:
- Qdrant: Enterprise-grade with hybrid search (dense + sparse)
- LanceDB: Zero-config file-based for simple deployments

Usage:
    from app.services.vector_store import get_vector_store
    
    store = get_vector_store()
    results = await store.search(workspace_id, query, embedding)
"""

from app.services.vector_store.base import (
    VectorStoreBase,
    SearchResult,
    VectorStoreStats,
)
from app.services.vector_store.factory import (
    get_vector_store,
    get_current_store_type,
    set_vector_store_type,
)

__all__ = [
    "VectorStoreBase",
    "SearchResult", 
    "VectorStoreStats",
    "get_vector_store",
    "get_current_store_type",
    "set_vector_store_type",
]
