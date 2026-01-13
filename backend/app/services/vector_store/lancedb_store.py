"""
LanceDB Vector Store - Zero-config file-based vector database.

Features:
- No external container required
- File-based storage (easy backup/migration)
- Dense vector search (cosine similarity)
- Ideal for simple deployments and POCs

Based on AnythingLLM's LanceDB implementation approach.
"""

from typing import List, Dict, Any, Optional
import uuid
import os

from app.core.config import settings
from app.services.vector_store.base import (
    VectorStoreBase, SearchResult, VectorStoreStats,
    extract_chunk_metadata
)

# Lazy import lancedb to avoid startup errors if not installed
_lancedb = None


def get_lancedb():
    """Lazy-load lancedb module"""
    global _lancedb
    if _lancedb is None:
        try:
            import lancedb
            _lancedb = lancedb
        except ImportError:
            raise ImportError(
                "lancedb is not installed. Install with: pip install lancedb"
            )
    return _lancedb


class LanceDBVectorStore(VectorStoreBase):
    """
    LanceDB vector store implementation with dense vector search.
    
    Uses file-based storage for zero-config deployment.
    Implements the same interface as QdrantVectorStore for seamless switching.
    """
    
    def __init__(self):
        self._db = None
        self._db_path = getattr(settings, 'LANCEDB_PATH', '/data/lancedb')
        
        # Ensure directory exists
        os.makedirs(self._db_path, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "lancedb"
    
    @property
    def db(self):
        """Lazy-load database connection"""
        if self._db is None:
            lancedb = get_lancedb()
            self._db = lancedb.connect(self._db_path)
            print(f"LanceDB connected at: {self._db_path}")
        return self._db
    
    def _table_name(self, workspace_id: int) -> str:
        """Generate table name for a workspace"""
        return f"workspace_{workspace_id}"
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        try:
            return table_name in self.db.table_names()
        except Exception:
            return False
    
    def _distance_to_similarity(self, distance: float) -> float:
        """Convert LanceDB cosine distance to similarity score (0-1)"""
        if distance is None or not isinstance(distance, (int, float)):
            return 0.0
        # LanceDB cosine distance range is 0-2 (0 = identical, 2 = opposite)
        # Convert to similarity: 1 - (distance / 2) maps [0,2] -> [1,0]
        # Or simpler: similarity = 1 - distance/2
        similarity = 1.0 - (distance / 2.0)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
    
    async def ensure_collection(self, workspace_id: int) -> None:
        """Ensure table exists for workspace (created on first add)"""
        # LanceDB creates tables on first insert, so nothing to do here
        pass
    
    async def search(
        self,
        workspace_id: int,
        query: str,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        use_hybrid: bool = True,  # Ignored for LanceDB (dense only)
    ) -> List[SearchResult]:
        """Dense vector search using cosine similarity"""
        table_name = self._table_name(workspace_id)
        
        if not self._table_exists(table_name):
            return []
        
        try:
            table = self.db.open_table(table_name)
            
            # Perform vector search
            results = (
                table
                .search(query_embedding)
                .metric("cosine")
                .limit(limit)
                .to_list()
            )
            
            # Convert to SearchResult objects
            search_results = []
            for item in results:
                # LanceDB returns _distance field
                distance = item.get("_distance", 0.0)
                score = self._distance_to_similarity(distance)
                
                if score < score_threshold:
                    continue
                
                search_results.append(SearchResult(
                    content=item.get("content", ""),
                    score=score,
                    document_id=item.get("document_id", 0),
                    chunk_index=item.get("chunk_index", 0),
                    metadata=item,
                    filename=item.get("filename", ""),
                    content_type=item.get("content_type", "text"),
                    section_title=item.get("section_title", ""),
                    has_table=item.get("has_table", False),
                    has_code=item.get("has_code", False),
                    word_count=item.get("word_count", 0),
                ))
            
            return search_results
            
        except Exception as e:
            print(f"LanceDB search error: {e}")
            return []
    
    async def add_document(
        self,
        workspace_id: int,
        document_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add document chunks with embeddings"""
        table_name = self._table_name(workspace_id)
        
        try:
            # Prepare data for insertion
            data = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Extract rich metadata from chunk content
                chunk_meta = extract_chunk_metadata(chunk, i)
                
                # Build record
                record = {
                    "id": str(uuid.uuid4()),
                    "vector": embedding,
                    "content": chunk,
                    "document_id": document_id,
                    "total_chunks": len(chunks),
                    **chunk_meta.to_dict(),
                    **(metadata or {})
                }
                data.append(record)
            
            # Create or append to table
            if self._table_exists(table_name):
                table = self.db.open_table(table_name)
                table.add(data)
            else:
                self.db.create_table(table_name, data)
            
            print(f"LanceDB: Added {len(data)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            print(f"LanceDB add_document error: {e}")
            return False
    
    async def delete_document(self, workspace_id: int, document_id: int) -> bool:
        """Delete all chunks for a document"""
        table_name = self._table_name(workspace_id)
        
        if not self._table_exists(table_name):
            return True
        
        try:
            table = self.db.open_table(table_name)
            # LanceDB uses SQL-like filter syntax
            table.delete(f"document_id = {document_id}")
            print(f"LanceDB: Deleted document {document_id} from {table_name}")
            return True
        except Exception as e:
            print(f"LanceDB delete_document error: {e}")
            return False
    
    async def delete_workspace(self, workspace_id: int) -> bool:
        """Delete entire workspace table"""
        table_name = self._table_name(workspace_id)
        
        try:
            if self._table_exists(table_name):
                self.db.drop_table(table_name)
            return True
        except Exception as e:
            print(f"LanceDB delete_workspace error: {e}")
            return True  # Table might not exist
    
    async def get_stats(self, workspace_id: int) -> VectorStoreStats:
        """Get statistics for a workspace"""
        table_name = self._table_name(workspace_id)
        
        if not self._table_exists(table_name):
            return VectorStoreStats()
        
        try:
            table = self.db.open_table(table_name)
            vector_count = table.count_rows()
            
            # Count unique documents
            all_rows = table.to_pandas()
            unique_docs = all_rows["document_id"].nunique() if "document_id" in all_rows.columns else 0
            
            return VectorStoreStats(
                vector_count=vector_count,
                document_count=unique_docs
            )
        except Exception as e:
            print(f"LanceDB get_stats error: {e}")
            return VectorStoreStats()
    
    async def get_document_chunks(
        self,
        workspace_id: int,
        document_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document (for debugging)"""
        table_name = self._table_name(workspace_id)
        
        if not self._table_exists(table_name):
            return []
        
        try:
            table = self.db.open_table(table_name)
            # Filter by document_id
            df = table.to_pandas()
            doc_rows = df[df["document_id"] == document_id]
            return doc_rows.to_dict("records")
        except Exception as e:
            print(f"LanceDB get_document_chunks error: {e}")
            return []
    
    async def get_document_stats(
        self,
        workspace_id: int,
        document_id: int,
    ) -> Dict[str, Any]:
        """Get aggregated statistics for a document"""
        chunks = await self.get_document_chunks(workspace_id, document_id)
        
        if not chunks:
            return {}
        
        total_words = 0
        total_chars = 0
        tables = 0
        code_blocks = 0
        lists = 0
        
        for chunk in chunks:
            total_words += chunk.get("word_count", 0)
            total_chars += chunk.get("char_count", 0)
            
            content_type = chunk.get("content_type", "text")
            if content_type == "table" or chunk.get("has_table"):
                tables += 1
            if content_type == "code" or chunk.get("has_code"):
                code_blocks += 1
            if content_type == "list" or chunk.get("has_list"):
                lists += 1
        
        return {
            "total_chunks": len(chunks),
            "total_words": total_words,
            "total_tokens": total_chars // 4 if total_chars else total_words,
            "tables": tables,
            "code_blocks": code_blocks,
            "lists": lists,
        }
