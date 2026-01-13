"""
RAG Service - High-level RAG operations with vector store abstraction.

This service provides the main interface for RAG operations, delegating
to the configured vector store (Qdrant, LanceDB, etc.) and shared services
(reranker, query expansion).
"""

from typing import List, Optional, Dict, Any
import httpx
from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.reranker_service import reranker_service
from app.services.vector_store import get_vector_store, SearchResult
from app.services.vector_store.factory import get_current_store_type, set_vector_store_type
from app.services.vector_store.base import extract_chunk_metadata


class RAGService:
    """
    High-level RAG service that delegates to the configured vector store.
    
    This class maintains backward compatibility with existing code while
    using the new modular vector store architecture internally.
    """
    
    def __init__(self):
        pass
    
    @property
    def vector_store(self):
        """Get the currently active vector store (dynamically based on admin setting)"""
        return get_vector_store()
    
    def switch_vector_store(self, store_type: str):
        """Switch to a different vector store type (called by admin)"""
        return set_vector_store_type(store_type)
    
    @property
    def reranker(self):
        """Access to shared reranker service (for backward compatibility)"""
        return reranker_service.model
    
    async def _expand_query(self, query: str) -> List[str]:
        """Use LLM to generate query variants for better recall"""
        try:
            prompt = f"""Generate 3 alternative search queries for the following question. 
The alternatives should capture different ways to phrase the same information need.
Return ONLY the 3 queries, one per line, no numbering or explanation.

Original query: {query}

Alternative queries:"""
            
            headers = {"Content-Type": "application/json"}
            if settings.LLM_API_KEY:
                headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 150,
                        "stream": False,
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse the response - each line is a query variant
                variants = [line.strip() for line in content.strip().split('\n') if line.strip()]
                # Filter out any lines that look like numbering or explanations
                variants = [v for v in variants if not v.startswith(('1.', '2.', '3.', '-', '*'))]
                # Take up to 3 variants
                variants = variants[:3]
                
                print(f"Query expansion: '{query}' -> {variants}")
                return [query] + variants  # Original query + variants
                
        except Exception as e:
            print(f"Query expansion failed, using original query: {e}")
            return [query]
    
    def _rerank_with_cross_encoder(self, query: str, candidates: List[dict], top_k: int = 5) -> List[dict]:
        """Rerank candidates using cross-encoder for better relevance"""
        return reranker_service.rerank(query, candidates, top_k=top_k, content_key="content")
    
    async def ensure_collection(self, workspace_id: int):
        """Ensure collection exists for workspace (delegates to vector store)"""
        await self.vector_store.ensure_collection(workspace_id)
    
    def _extract_chunk_metadata(self, chunk: str, chunk_index: int) -> dict:
        """Extract rich metadata from a chunk (delegates to shared function)"""
        chunk_meta = extract_chunk_metadata(chunk, chunk_index)
        return chunk_meta.to_dict()
    
    async def add_document(
        self,
        workspace_id: int,
        document_id: int,
        chunks: List[str],
        metadata: Optional[dict] = None
    ):
        """Add document chunks to vector store (delegates to configured store)"""
        # Generate embeddings
        embeddings = await embedding_service.embed_texts(chunks)
        
        # Delegate to vector store
        await self.vector_store.add_document(
            workspace_id=workspace_id,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata
        )
    
    async def search(
        self,
        workspace_id: int,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.0,
        hybrid: bool = True,
        use_reranking: bool = False,
        rerank_top_k: int = 20,
        use_query_expansion: bool = False
    ) -> List[dict]:
        """
        Search with optional query expansion and reranking.
        
        Delegates vector search to the configured store, but handles
        query expansion and reranking at this level (shared across all stores).
        """
        try:
            # Query expansion: generate multiple query variants for better recall
            if use_query_expansion:
                queries = await self._expand_query(query)
            else:
                queries = [query]
            
            # Collect all candidates from all query variants
            all_candidates: Dict[int, dict] = {}  # Use dict to deduplicate by content hash
            
            for q in queries:
                query_embedding = await embedding_service.embed_text(q)
                
                # Delegate to vector store
                results = await self.vector_store.search(
                    workspace_id=workspace_id,
                    query=q,
                    query_embedding=query_embedding,
                    limit=limit * 2 if use_query_expansion else limit,
                    score_threshold=score_threshold,
                    use_hybrid=hybrid,
                )
                
                # Convert SearchResult to dict and deduplicate
                for result in results:
                    content_key = hash(result.content)
                    result_dict = result.to_dict()
                    if content_key not in all_candidates:
                        all_candidates[content_key] = result_dict
                    elif result.score > all_candidates[content_key]['score']:
                        all_candidates[content_key] = result_dict
            
            # Sort by score and limit
            initial_candidates = sorted(
                all_candidates.values(), 
                key=lambda x: x['score'], 
                reverse=True
            )[:limit]
            
            # Apply cross-encoder reranking if enabled
            if use_reranking and reranker_service.is_available and initial_candidates:
                print(f"Applying cross-encoder reranking to {len(initial_candidates)} candidates")
                return self._rerank_with_cross_encoder(query, initial_candidates, top_k=rerank_top_k)
            
            return initial_candidates
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def get_document_points(self, workspace_id: int, document_id: int) -> list:
        """Get all points for a document (for debugging)"""
        return await self.vector_store.get_document_chunks(workspace_id, document_id)
    
    async def delete_document(self, workspace_id: int, document_id: int):
        """Delete all chunks for a document"""
        await self.vector_store.delete_document(workspace_id, document_id)
    
    async def delete_collection(self, workspace_id: int):
        """Delete entire workspace collection"""
        await self.vector_store.delete_workspace(workspace_id)
    
    async def get_document_stats(self, workspace_id: int, document_id: int) -> dict:
        """Get aggregated statistics for a document"""
        return await self.vector_store.get_document_stats(workspace_id, document_id)


rag_service = RAGService()
