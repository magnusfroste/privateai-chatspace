"""
Qdrant Vector Store - Enterprise-grade vector database with hybrid search.

Features:
- Hybrid search (dense + sparse BM25)
- External container-based deployment
- Scalable for large datasets
"""

from typing import List, Dict, Any, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, SparseVectorParams, 
    SparseVector, Modifier, Filter, FieldCondition, MatchValue
)

from app.core.config import settings
from app.services.vector_store.base import (
    VectorStoreBase, SearchResult, VectorStoreStats, 
    ChunkMetadata, extract_chunk_metadata
)


class QdrantVectorStore(VectorStoreBase):
    """
    Qdrant vector store implementation with hybrid search support.
    
    Uses both dense vectors (semantic) and sparse vectors (BM25-style)
    for improved retrieval quality through Reciprocal Rank Fusion (RRF).
    """
    
    def __init__(self):
        # Parse URL to handle HTTPS properly
        url = settings.QDRANT_URL
        if url.startswith("https://"):
            host = url.replace("https://", "")
            self.client = QdrantClient(host=host, port=443, https=True, timeout=60)
        elif url.startswith("http://"):
            self.client = QdrantClient(url=url, timeout=60)
        else:
            self.client = QdrantClient(url=url, timeout=60)
        
        self._dimension: Optional[int] = None
    
    @property
    def name(self) -> str:
        return "qdrant"
    
    def _collection_name(self, workspace_id: int) -> str:
        """Generate collection name for a workspace"""
        return f"workspace_{workspace_id}"
    
    def _text_to_sparse(self, text: str) -> SparseVector:
        """Convert text to sparse BM25-style vector using simple tokenization"""
        words = text.lower().split()
        word_counts: Dict[int, float] = {}
        
        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            if word and len(word) > 1:
                # Use hash as index (mod large number to keep indices reasonable)
                idx = hash(word) % 1000000
                word_counts[idx] = word_counts.get(idx, 0.0) + 1.0
        
        # Convert to sorted lists (Qdrant requires sorted indices)
        indices = sorted(word_counts.keys())
        values = [word_counts[idx] for idx in indices]
        
        return SparseVector(indices=indices, values=values)
    
    async def _get_dimension(self, sample_embedding: List[float]) -> int:
        """Get or cache embedding dimension"""
        if self._dimension is None:
            self._dimension = len(sample_embedding)
        return self._dimension
    
    async def ensure_collection(self, workspace_id: int) -> None:
        """Create collection with hybrid search support (dense + sparse vectors)"""
        collection_name = self._collection_name(workspace_id)
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if not exists:
            # Get dimension from embedder
            from app.services.embedding_service import embedding_service
            test_embedding = await embedding_service.embed_texts(["test"])
            dimension = await self._get_dimension(test_embedding[0])
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=dimension,
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        modifier=Modifier.IDF  # BM25-style IDF weighting
                    )
                }
            )
    
    async def search(
        self,
        workspace_id: int,
        query: str,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        use_hybrid: bool = True,
    ) -> List[SearchResult]:
        """Hybrid search using both dense vectors and sparse BM25"""
        collection_name = self._collection_name(workspace_id)
        
        try:
            # Check if collection has named vectors (hybrid support)
            collection_info = self.client.get_collection(collection_name)
            vectors_config = collection_info.config.params.vectors
            has_named_vectors = isinstance(vectors_config, dict) and "dense" in vectors_config
            
            if use_hybrid and has_named_vectors:
                return await self._hybrid_search(
                    collection_name, query, query_embedding, limit, score_threshold
                )
            elif has_named_vectors:
                return await self._dense_search(
                    collection_name, query_embedding, limit, score_threshold, use_named=True
                )
            else:
                return await self._dense_search(
                    collection_name, query_embedding, limit, score_threshold, use_named=False
                )
                
        except Exception as e:
            print(f"Qdrant search error: {e}")
            return []
    
    async def _hybrid_search(
        self,
        collection_name: str,
        query: str,
        query_embedding: List[float],
        limit: int,
        score_threshold: float,
    ) -> List[SearchResult]:
        """Hybrid search with RRF fusion of dense and sparse results"""
        sparse_query = self._text_to_sparse(query)
        
        # Dense semantic search
        dense_results = self.client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            using="dense",
            limit=limit * 2
        )
        
        # Sparse keyword search
        sparse_results = self.client.query_points(
            collection_name=collection_name,
            query=sparse_query,
            using="sparse",
            limit=limit * 2
        )
        
        # Manual RRF fusion
        rrf_scores: Dict[str, Dict[str, Any]] = {}
        k = 60  # RRF constant
        
        for rank, hit in enumerate(dense_results.points):
            point_id = str(hit.id)
            if point_id not in rrf_scores:
                rrf_scores[point_id] = {"hit": hit, "score": 0.0}
            rrf_scores[point_id]["score"] += 1.0 / (k + rank + 1)
        
        for rank, hit in enumerate(sparse_results.points):
            point_id = str(hit.id)
            if point_id not in rrf_scores:
                rrf_scores[point_id] = {"hit": hit, "score": 0.0}
            rrf_scores[point_id]["score"] += 1.0 / (k + rank + 1)
        
        # Sort by RRF score and take top results
        sorted_results = sorted(
            rrf_scores.values(), 
            key=lambda x: x["score"], 
            reverse=True
        )[:limit]
        
        # Convert to SearchResult objects
        # Note: RRF scores are not comparable to cosine similarity (0-1 range)
        # so we don't apply score_threshold here - filtering happens at limit
        return [
            self._hit_to_search_result(item["hit"], item["score"])
            for item in sorted_results
        ]
    
    async def _dense_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        score_threshold: float,
        use_named: bool,
    ) -> List[SearchResult]:
        """Dense-only vector search"""
        if use_named:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                using="dense",
                limit=limit,
                score_threshold=score_threshold if score_threshold > 0 else None
            )
        else:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold if score_threshold > 0 else None
            )
        
        return [
            self._hit_to_search_result(hit, hit.score)
            for hit in results.points
        ]
    
    def _hit_to_search_result(self, hit: Any, score: float) -> SearchResult:
        """Convert Qdrant hit to SearchResult"""
        payload = hit.payload or {}
        return SearchResult(
            content=payload.get("content", ""),
            score=score,
            document_id=payload.get("document_id", 0),
            chunk_index=payload.get("chunk_index", 0),
            metadata=payload,
            filename=payload.get("filename", ""),
            content_type=payload.get("content_type", "text"),
            section_title=payload.get("section_title", ""),
            has_table=payload.get("has_table", False),
            has_code=payload.get("has_code", False),
            word_count=payload.get("word_count", 0),
        )
    
    async def add_document(
        self,
        workspace_id: int,
        document_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add document chunks with both dense and sparse vectors"""
        await self.ensure_collection(workspace_id)
        collection_name = self._collection_name(workspace_id)
        
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            sparse_vec = self._text_to_sparse(chunk)
            
            # Extract rich metadata from chunk content
            chunk_meta = extract_chunk_metadata(chunk, i)
            
            # Merge with document-level metadata
            full_metadata = {
                "document_id": document_id,
                "content": chunk,
                "total_chunks": len(chunks),
                **chunk_meta.to_dict(),
                **(metadata or {})
            }
            
            points.append(PointStruct(
                id=point_id,
                vector={
                    "dense": embedding,
                    "sparse": sparse_vec
                },
                payload=full_metadata
            ))
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        print(f"Qdrant: Added {len(points)} chunks for document {document_id}")
        return True
    
    async def delete_document(self, workspace_id: int, document_id: int) -> bool:
        """Delete all chunks for a document"""
        collection_name = self._collection_name(workspace_id)
        
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return True
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            print(f"Qdrant: Deleted document {document_id} from {collection_name}")
            return True
        except Exception as e:
            print(f"Qdrant: Error deleting document {document_id}: {e}")
            return False
    
    async def delete_workspace(self, workspace_id: int) -> bool:
        """Delete entire workspace collection"""
        collection_name = self._collection_name(workspace_id)
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return True  # Collection might not exist
    
    async def get_stats(self, workspace_id: int) -> VectorStoreStats:
        """Get statistics for a workspace"""
        collection_name = self._collection_name(workspace_id)
        
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return VectorStoreStats()
            
            collection_info = self.client.get_collection(collection_name)
            vector_count = collection_info.points_count or 0
            
            # Count unique documents
            results, _ = self.client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=["document_id"]
            )
            unique_docs = set()
            for point in results:
                if point.payload and "document_id" in point.payload:
                    unique_docs.add(point.payload["document_id"])
            
            return VectorStoreStats(
                vector_count=vector_count,
                document_count=len(unique_docs)
            )
        except Exception as e:
            print(f"Qdrant: Error getting stats: {e}")
            return VectorStoreStats()
    
    async def get_document_chunks(
        self,
        workspace_id: int,
        document_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document (for debugging)"""
        collection_name = self._collection_name(workspace_id)
        
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return []
            
            results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            
            return [point.payload for point in results if point.payload]
        except Exception as e:
            print(f"Qdrant: Error getting document chunks: {e}")
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
        
        for payload in chunks:
            total_words += payload.get("word_count", 0)
            total_chars += payload.get("char_count", 0)
            
            content_type = payload.get("content_type", "text")
            if content_type == "table" or payload.get("has_table"):
                tables += 1
            if content_type == "code" or payload.get("has_code"):
                code_blocks += 1
            if content_type == "list" or payload.get("has_list"):
                lists += 1
        
        return {
            "total_chunks": len(chunks),
            "total_words": total_words,
            "total_tokens": total_chars // 4 if total_chars else total_words,
            "tables": tables,
            "code_blocks": code_blocks,
            "lists": lists,
        }
