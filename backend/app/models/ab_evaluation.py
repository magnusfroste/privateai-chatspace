from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class ABTestRun(Base):
    """A/B test run comparing AnythingLLM vs Private AI"""
    __tablename__ = "ab_test_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    anythingllm_url = Column(String, nullable=False)
    anythingllm_workspace = Column(String, nullable=False)
    privateai_url = Column(String, nullable=False)
    privateai_workspace_id = Column(Integer, nullable=False)
    
    # Test parameters
    num_queries = Column(Integer, nullable=False)
    num_documents = Column(Integer, nullable=False)
    
    # Aggregate results
    anythingllm_avg_latency = Column(Float, nullable=True)
    anythingllm_avg_faithfulness = Column(Float, nullable=True)
    anythingllm_avg_relevancy = Column(Float, nullable=True)
    anythingllm_recall = Column(Float, nullable=True)
    anythingllm_mrr = Column(Float, nullable=True)
    
    privateai_avg_latency = Column(Float, nullable=True)
    privateai_avg_faithfulness = Column(Float, nullable=True)
    privateai_avg_relevancy = Column(Float, nullable=True)
    privateai_recall = Column(Float, nullable=True)
    privateai_mrr = Column(Float, nullable=True)
    
    # Winner summary
    winner = Column(String, nullable=True)  # AnythingLLM, PrivateAI, TIE
    winner_reason = Column(Text, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)


class ABTestQuery(Base):
    """Individual query result within an A/B test run"""
    __tablename__ = "ab_test_queries"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=False, index=True)
    
    # Query info
    query_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    ground_truth_docs = Column(JSON, nullable=True)
    
    # AnythingLLM results
    anythingllm_answer = Column(Text, nullable=True)
    anythingllm_latency = Column(Float, nullable=True)
    anythingllm_faithfulness = Column(Float, nullable=True)
    anythingllm_relevancy = Column(Float, nullable=True)
    anythingllm_retrieved_docs = Column(JSON, nullable=True)
    anythingllm_recall = Column(Float, nullable=True)
    anythingllm_mrr = Column(Float, nullable=True)
    
    # Private AI results
    privateai_answer = Column(Text, nullable=True)
    privateai_latency = Column(Float, nullable=True)
    privateai_faithfulness = Column(Float, nullable=True)
    privateai_relevancy = Column(Float, nullable=True)
    privateai_retrieved_docs = Column(JSON, nullable=True)
    privateai_recall = Column(Float, nullable=True)
    privateai_mrr = Column(Float, nullable=True)
    
    # Per-query winner
    winner = Column(String, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())


class ABTestDocument(Base):
    """Documents used in an A/B test run"""
    __tablename__ = "ab_test_documents"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=False, index=True)
    
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Upload status per system
    anythingllm_uploaded = Column(Integer, default=0)  # 0=no, 1=yes
    privateai_uploaded = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
