"""
Private AI Chatspace - Simple API v1

Developer-friendly API endpoints for integrations.
Designed to be as simple as AnythingLLM's API.

Key differences from internal API:
- Non-streaming responses (JSON)
- API key authentication (in addition to email/password)
- Single endpoint for query with sources
- Auto-embed on upload
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Response
from app import __version__
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.document_service import document_service

router = APIRouter(prefix="/api/v1", tags=["v1-simple-api"])


# =============================================================================
# Request/Response Models
# =============================================================================

class QueryRequest(BaseModel):
    """Simple query request - like AnythingLLM"""
    message: str
    mode: str = "query"  # "query" (RAG), "chat" (no RAG)
    top_k: Optional[int] = None  # Override default
    include_sources: bool = True


class SourceInfo(BaseModel):
    """Source document info"""
    filename: str
    content: str
    score: Optional[float] = None
    document_id: Optional[int] = None


class QueryResponse(BaseModel):
    """Simple query response - like AnythingLLM"""
    response: str
    sources: List[SourceInfo]
    latency_ms: float
    tokens_used: Optional[int] = None
    mode: str


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    id: int
    filename: str
    status: str  # "uploaded", "embedded", "error"
    chunks: Optional[int] = None
    message: Optional[str] = None


class WorkspaceInfo(BaseModel):
    """Workspace info for listing"""
    id: int
    name: str
    document_count: int
    created_at: datetime


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/workspaces", response_model=List[WorkspaceInfo])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all workspaces accessible to the user.
    
    Returns workspace ID, name, and document count.
    """
    if current_user.role == "admin":
        result = await db.execute(select(Workspace))
    else:
        result = await db.execute(
            select(Workspace).where(Workspace.owner_id == current_user.id)
        )
    
    workspaces = result.scalars().all()
    
    response = []
    for ws in workspaces:
        doc_result = await db.execute(
            select(Document).where(Document.workspace_id == ws.id)
        )
        doc_count = len(doc_result.scalars().all())
        
        response.append(WorkspaceInfo(
            id=ws.id,
            name=ws.name,
            document_count=doc_count,
            created_at=ws.created_at
        ))
    
    return response


@router.post("/workspace/{workspace_id}/query", response_model=QueryResponse)
async def query_workspace(
    workspace_id: int,
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query a workspace with RAG.
    
    Simple, non-streaming endpoint for integrations.
    Returns complete response with sources in one JSON object.
    
    **Modes:**
    - `query`: RAG mode - searches documents and answers based on context
    - `chat`: Chat mode - direct LLM response without document search
    
    **Example:**
    ```
    POST /api/v1/workspace/1/query
    {
        "message": "What is the torque specification?",
        "mode": "query"
    }
    ```
    """
    start_time = time.time()
    
    # Verify workspace access
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if current_user.role != "admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sources: List[SourceInfo] = []
    rag_context = None
    
    # RAG search if mode is "query"
    if request.mode == "query":
        top_k = request.top_k or settings.DEFAULT_TOP_N
        
        # Use workspace settings for hybrid/reranking
        use_hybrid = workspace.use_hybrid_search if workspace.use_hybrid_search is not None else settings.DEFAULT_USE_HYBRID_SEARCH
        use_reranking = workspace.use_reranking if workspace.use_reranking else False
        rerank_top_k = workspace.rerank_top_k if workspace.rerank_top_k else 20
        use_query_expansion = workspace.use_query_expansion if workspace.use_query_expansion else False
        
        initial_limit = rerank_top_k if use_reranking else top_k
        
        rag_results = await rag_service.search(
            workspace_id,
            request.message,
            limit=initial_limit,
            score_threshold=settings.DEFAULT_SIMILARITY_THRESHOLD,
            hybrid=use_hybrid,
            use_reranking=use_reranking,
            rerank_top_k=top_k,
            use_query_expansion=use_query_expansion
        )
        
        if rag_results:
            context_parts = []
            for i, r in enumerate(rag_results, 1):
                filename = r.get("filename", "")
                if not filename:
                    doc_id = r.get("document_id")
                    if doc_id:
                        doc_result = await db.execute(
                            select(Document).where(Document.id == doc_id)
                        )
                        doc = doc_result.scalar_one_or_none()
                        filename = doc.original_filename if doc else f"Document {doc_id}"
                
                content = r.get("content", "")
                score = r.get("score")
                
                context_parts.append(f"[{i}] (Source: {filename})\n{content}")
                
                if request.include_sources:
                    sources.append(SourceInfo(
                        filename=filename,
                        content=content,
                        score=score,
                        document_id=r.get("document_id")
                    ))
            
            rag_context = "\n\n---\n\n".join(context_parts)
        
        # If query mode and no context, return error
        if not rag_context:
            return QueryResponse(
                response="No relevant documents found in this workspace.",
                sources=[],
                latency_ms=(time.time() - start_time) * 1000,
                mode=request.mode
            )
    
    # Generate LLM response (non-streaming)
    messages = [{"role": "user", "content": request.message}]
    system_prompt = workspace.system_prompt if workspace.system_prompt else None
    
    response_text = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=messages,
        system_prompt=system_prompt,
        rag_context=rag_context
    ):
        response_text += chunk
    
    latency_ms = (time.time() - start_time) * 1000
    
    return QueryResponse(
        response=response_text,
        sources=sources if request.include_sources else [],
        latency_ms=latency_ms,
        mode=request.mode
    )


@router.post("/workspace/{workspace_id}/upload", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: int,
    file: UploadFile = File(...),
    auto_embed: bool = Query(default=True, description="Automatically embed after upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and optionally embed a document in one step.
    
    **Parameters:**
    - `auto_embed`: If true (default), document is embedded immediately
    
    **Supported formats:** PDF, DOCX, TXT, MD
    
    **Example:**
    ```
    POST /api/v1/workspace/1/upload?auto_embed=true
    Content-Type: multipart/form-data
    file: <your-document.pdf>
    ```
    """
    # Verify workspace access
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if current_user.role != "admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Save original file
    original_path = await document_service.save_original(
        file, workspace_id, file.filename
    )
    
    # Create document record
    document = Document(
        workspace_id=workspace_id,
        original_filename=file.filename,
        original_path=original_path,
        file_type=file.filename.split(".")[-1].lower() if "." in file.filename else "unknown",
        file_size=0,  # Will be updated
        uploaded_by=current_user.id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Convert to markdown
    try:
        markdown_path = await document_service.convert_to_markdown(
            original_path, workspace_id, document.id
        )
        document.markdown_path = markdown_path
        await db.commit()
    except Exception as e:
        return DocumentUploadResponse(
            id=document.id,
            filename=file.filename,
            status="error",
            message=f"Failed to convert document: {str(e)}"
        )
    
    # Auto-embed if requested
    chunks = None
    if auto_embed:
        try:
            markdown_content = await document_service.read_markdown(markdown_path)
            text_chunks = document_service.chunk_text(markdown_content)
            
            await rag_service.index_document(
                workspace_id=workspace_id,
                document_id=document.id,
                filename=file.filename,
                chunks=text_chunks
            )
            
            document.indexed = True
            document.indexed_at = datetime.utcnow()
            await db.commit()
            
            chunks = len(text_chunks)
            status = "embedded"
        except Exception as e:
            return DocumentUploadResponse(
                id=document.id,
                filename=file.filename,
                status="uploaded",
                message=f"Upload successful but embedding failed: {str(e)}"
            )
    else:
        status = "uploaded"
    
    return DocumentUploadResponse(
        id=document.id,
        filename=file.filename,
        status=status,
        chunks=chunks
    )


@router.get("/workspace/{workspace_id}/documents")
async def list_documents(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all documents in a workspace.
    
    Returns document ID, filename, status, and chunk count.
    """
    # Verify workspace access
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if current_user.role != "admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id)
    )
    documents = result.scalars().all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.original_filename,
            "file_type": doc.file_type,
            "indexed": doc.indexed,
            "indexed_at": doc.indexed_at,
            "uploaded_at": doc.created_at
        }
        for doc in documents
    ]


@router.delete("/workspace/{workspace_id}/documents/{document_id}")
async def delete_document(
    workspace_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document from workspace.
    
    Removes both the file and its embeddings from the vector store.
    """
    # Verify workspace access
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if current_user.role != "admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    try:
        await rag_service.delete_document(workspace_id, document_id)
    except Exception:
        pass  # Continue even if vector deletion fails
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return {"deleted": True, "document_id": document_id}


@router.get("/health")
async def health_check(response: Response):
    """
    Simple health check endpoint.
    
    Returns API version and status.
    """
    response.headers["X-API-Version"] = __version__
    return {
        "status": "ok",
        "version": __version__,
        "api": "Private AI Chatspace Simple API"
    }
