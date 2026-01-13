"""
Vector Store Base - Abstract interface and data models.

This module defines the contract that all vector store implementations must follow,
ensuring consistent behavior across different backends (Qdrant, LanceDB, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class SearchResult:
    """
    Standardized search result from any vector store.
    
    All vector store implementations return results in this format
    to ensure consistent handling in the application layer.
    """
    content: str
    score: float
    document_id: int
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields populated by metadata
    filename: str = ""
    content_type: str = "text"
    section_title: str = ""
    has_table: bool = False
    has_code: bool = False
    word_count: int = 0
    
    # Rerank score (populated if reranking is applied)
    rerank_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "content": self.content,
            "score": self.score,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "filename": self.filename,
            "content_type": self.content_type,
            "section_title": self.section_title,
            "has_table": self.has_table,
            "has_code": self.has_code,
            "word_count": self.word_count,
        }
        if self.rerank_score is not None:
            result["rerank_score"] = self.rerank_score
        return result


@dataclass
class VectorStoreStats:
    """Statistics for a workspace's vector store"""
    vector_count: int = 0
    document_count: int = 0
    
    
@dataclass
class ChunkMetadata:
    """
    Rich metadata extracted from a text chunk.
    
    Used to enhance retrieval with content-type filtering
    and section-aware search.
    """
    chunk_index: int
    char_count: int
    word_count: int
    content_type: str  # "text", "table", "code", "list"
    has_table: bool = False
    has_code: bool = False
    has_list: bool = False
    has_header: bool = False
    section_level: Optional[int] = None
    section_title: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "chunk_index": self.chunk_index,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "content_type": self.content_type,
            "has_table": self.has_table,
            "has_code": self.has_code,
            "has_list": self.has_list,
            "has_header": self.has_header,
            "section_level": self.section_level,
            "section_title": self.section_title,
        }


def extract_chunk_metadata(chunk: str, chunk_index: int) -> ChunkMetadata:
    """
    Extract rich metadata from a chunk for better filtering and retrieval.
    
    This is a shared utility used by all vector store implementations.
    """
    # Detect content types
    has_table = bool(re.search(r'\|[^\n]+\|', chunk))
    has_code = bool(re.search(r'```[\s\S]*?```', chunk))
    has_list = bool(re.search(r'^\s*[-*•]\s', chunk, re.MULTILINE))
    has_header = bool(re.search(r'^#{1,6}\s', chunk, re.MULTILINE))
    
    # Determine primary content type
    if has_table:
        content_type = "table"
    elif has_code:
        content_type = "code"
    elif has_list:
        content_type = "list"
    else:
        content_type = "text"
    
    # Extract section title if chunk starts with header
    section_level = None
    section_title = None
    header_match = re.match(r'^(#{1,6})\s+(.+?)(?:\n|$)', chunk)
    if header_match:
        section_level = len(header_match.group(1))
        section_title = header_match.group(2).strip()
    
    return ChunkMetadata(
        chunk_index=chunk_index,
        char_count=len(chunk),
        word_count=len(chunk.split()),
        content_type=content_type,
        has_table=has_table,
        has_code=has_code,
        has_list=has_list,
        has_header=has_header,
        section_level=section_level,
        section_title=section_title,
    )


class VectorStoreBase(ABC):
    """
    Abstract base class for vector store implementations.
    
    All vector stores (Qdrant, LanceDB, etc.) must implement this interface
    to ensure consistent behavior across the application.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this vector store implementation"""
        pass
    
    @abstractmethod
    async def search(
        self,
        workspace_id: int,
        query: str,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        use_hybrid: bool = True,
    ) -> List[SearchResult]:
        """
        Search for similar documents in the vector store.
        
        Args:
            workspace_id: The workspace to search in
            query: The search query text (for hybrid/sparse search)
            query_embedding: The dense vector embedding of the query
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            use_hybrid: Whether to use hybrid search (if supported)
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        pass
    
    @abstractmethod
    async def add_document(
        self,
        workspace_id: int,
        document_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add document chunks with embeddings to the vector store.
        
        Args:
            workspace_id: The workspace to add to
            document_id: The document ID these chunks belong to
            chunks: List of text chunks
            embeddings: List of embedding vectors (same length as chunks)
            metadata: Optional document-level metadata
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete_document(
        self,
        workspace_id: int,
        document_id: int,
    ) -> bool:
        """
        Delete all chunks for a document from the vector store.
        
        Args:
            workspace_id: The workspace containing the document
            document_id: The document to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def delete_workspace(
        self,
        workspace_id: int,
    ) -> bool:
        """
        Delete entire workspace collection from the vector store.
        
        Args:
            workspace_id: The workspace to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def get_stats(
        self,
        workspace_id: int,
    ) -> VectorStoreStats:
        """
        Get statistics for a workspace.
        
        Args:
            workspace_id: The workspace to get stats for
            
        Returns:
            VectorStoreStats with vector and document counts
        """
        pass
    
    @abstractmethod
    async def ensure_collection(
        self,
        workspace_id: int,
    ) -> None:
        """
        Ensure the collection/table exists for a workspace.
        
        Creates the collection if it doesn't exist.
        
        Args:
            workspace_id: The workspace to ensure exists
        """
        pass
    
    async def get_document_chunks(
        self,
        workspace_id: int,
        document_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document (optional, for debugging).
        
        Default implementation returns empty list.
        Subclasses can override for debugging support.
        """
        return []
    
    async def get_document_stats(
        self,
        workspace_id: int,
        document_id: int,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a document.
        
        Default implementation returns empty dict.
        Subclasses can override for detailed stats.
        """
        return {}
