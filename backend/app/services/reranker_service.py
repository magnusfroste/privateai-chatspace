"""
Reranker Service - Cross-encoder reranking for improved search relevance.

This service is shared across all vector store implementations (Qdrant, LanceDB, etc.)
to provide consistent reranking capabilities.
"""

from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("Warning: sentence-transformers not available. Reranking will be disabled.")


class RerankerService:
    """
    Cross-encoder reranker for improving search result relevance.
    
    Uses the ms-marco-MiniLM-L-6-v2 model which is optimized for 
    passage reranking tasks. Implements lazy-loading to avoid 
    slow startup times.
    """
    
    MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    
    def __init__(self):
        self._reranker: Optional[CrossEncoder] = None
        self._loaded = False
    
    @property
    def is_available(self) -> bool:
        """Check if reranking is available (model can be loaded)"""
        return CROSS_ENCODER_AVAILABLE
    
    @property
    def model(self) -> Optional[CrossEncoder]:
        """Lazy-load reranker model on first use"""
        if not self._loaded:
            self._loaded = True
            if CROSS_ENCODER_AVAILABLE:
                try:
                    self._reranker = CrossEncoder(self.MODEL_NAME)
                    print(f"Cross-encoder reranker loaded successfully: {self.MODEL_NAME}")
                except Exception as e:
                    print(f"Failed to load cross-encoder: {e}")
                    self._reranker = None
        return self._reranker
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        content_key: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder for better relevance.
        
        Args:
            query: The search query
            candidates: List of candidate results with content
            top_k: Number of top results to return
            content_key: Key in candidate dict containing the text content
            
        Returns:
            Reranked list of candidates with added 'rerank_score' field
        """
        if not self.model or not candidates:
            return candidates[:top_k]
        
        try:
            # Prepare query-document pairs for cross-encoder
            pairs = [[query, candidate.get(content_key, "")] for candidate in candidates]
            
            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Combine with candidates and add rerank score
            scored_candidates = []
            for candidate, score in zip(candidates, scores):
                candidate_copy = candidate.copy()
                candidate_copy['rerank_score'] = float(score)
                scored_candidates.append(candidate_copy)
            
            # Sort by rerank score (higher is better) and return top_k
            scored_candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
            return scored_candidates[:top_k]
            
        except Exception as e:
            print(f"Reranking failed, falling back to original ranking: {e}")
            return candidates[:top_k]


# Singleton instance for shared use across services
reranker_service = RerankerService()
