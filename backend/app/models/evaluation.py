from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class RagEvaluation(Base):
    __tablename__ = "rag_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, nullable=False)
    document_id = Column(Integer, nullable=False)
    document_name = Column(String, nullable=True)
    question = Column(Text, nullable=False)
    
    # RAG results
    rag_response = Column(Text, nullable=True)
    rag_context_tokens = Column(Integer, nullable=True)
    rag_response_tokens = Column(Integer, nullable=True)
    rag_time_seconds = Column(Float, nullable=True)
    rag_chunks_retrieved = Column(Integer, nullable=True)
    
    # CAG results
    cag_response = Column(Text, nullable=True)
    cag_context_tokens = Column(Integer, nullable=True)
    cag_response_tokens = Column(Integer, nullable=True)
    cag_time_seconds = Column(Float, nullable=True)
    
    # Evaluation scores (JSON)
    rag_scores = Column(JSON, nullable=True)
    cag_scores = Column(JSON, nullable=True)
    winner = Column(String, nullable=True)  # RAG, CAG, TIE
    reasoning = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, nullable=True)  # admin user id
