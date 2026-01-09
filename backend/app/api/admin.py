from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import time
import os
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_admin, get_password_hash
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.chat import Chat, Message
from app.models.chat_log import ChatLog
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.document_service import document_service
from app.models.evaluation import RagEvaluation

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatLogResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: Optional[int]
    chat_id: Optional[int]
    prompt: str
    response: str
    model: Optional[str]
    latency_ms: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_users: int
    total_workspaces: int
    total_chats: int
    total_messages: int
    total_logs: int


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    users = await db.execute(select(func.count(User.id)))
    workspaces = await db.execute(select(func.count(Workspace.id)))
    chats = await db.execute(select(func.count(Chat.id)))
    messages = await db.execute(select(func.count(Message.id)))
    logs = await db.execute(select(func.count(ChatLog.id)))
    
    return StatsResponse(
        total_users=users.scalar() or 0,
        total_workspaces=workspaces.scalar() or 0,
        total_chats=chats.scalar() or 0,
        total_messages=messages.scalar() or 0,
        total_logs=logs.scalar() or 0
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        name=data.name,
        role=data.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    if data.password is not None:
        user.password_hash = get_password_hash(data.password)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await db.delete(user)
    await db.commit()
    
    return {"status": "deleted"}


@router.get("/logs", response_model=List[ChatLogResponse])
async def list_chat_logs(
    limit: int = Query(100, le=1000),
    offset: int = 0,
    user_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    query = select(ChatLog).order_by(ChatLog.created_at.desc())
    
    if user_id:
        query = query.where(ChatLog.user_id == user_id)
    if workspace_id:
        query = query.where(ChatLog.workspace_id == workspace_id)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/logs/{log_id}", response_model=ChatLogResponse)
async def get_chat_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(ChatLog).where(ChatLog.id == log_id))
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return log


class ServiceStatus(BaseModel):
    name: str
    status: str  # "online", "offline", "error"
    url: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class SystemHealthResponse(BaseModel):
    llm: ServiceStatus
    embedder: ServiceStatus
    qdrant: ServiceStatus


class WorkspaceInfo(BaseModel):
    id: int
    name: str
    owner_email: str
    document_count: int
    embedded_count: int
    has_rag_collection: bool
    rag_points: int
    admin_pinned: bool


class SystemOverviewResponse(BaseModel):
    workspaces: List[WorkspaceInfo]
    total_rag_collections: int


@router.get("/health/services", response_model=SystemHealthResponse)
async def check_services_health(
    admin: User = Depends(get_current_admin)
):
    """Check health of LLM, Embedder, and Qdrant services"""
    
    async def check_service(name: str, url: str, health_path: str = "", api_key: str = None) -> ServiceStatus:
        import time
        start = time.time()
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}{health_path}", headers=headers)
                latency = (time.time() - start) * 1000
                if response.status_code == 200:
                    return ServiceStatus(name=name, status="online", url=url, latency_ms=latency)
                else:
                    return ServiceStatus(name=name, status="error", url=url, latency_ms=latency, error=f"HTTP {response.status_code}")
        except Exception as e:
            return ServiceStatus(name=name, status="offline", url=url, error=str(e))
    
    llm_status = await check_service("LLM", settings.LLM_BASE_URL, "/models", settings.LLM_API_KEY)
    embedder_status = await check_service("Embedder", settings.EMBEDDER_BASE_URL, "/models", settings.EMBEDDER_API_KEY)
    qdrant_status = await check_service("Qdrant", settings.QDRANT_URL, "/collections")
    
    return SystemHealthResponse(
        llm=llm_status,
        embedder=embedder_status,
        qdrant=qdrant_status
    )


@router.get("/system/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get overview of workspaces and RAG collections"""
    
    # Get all workspaces with owner info
    result = await db.execute(
        select(Workspace, User.email)
        .join(User, Workspace.owner_id == User.id)
        .order_by(Workspace.id)
    )
    workspace_data = result.all()
    
    workspaces_info = []
    total_collections = 0
    
    for workspace, owner_email in workspace_data:
        # Count documents
        doc_result = await db.execute(
            select(func.count(Document.id))
            .where(Document.workspace_id == workspace.id)
        )
        doc_count = doc_result.scalar() or 0
        
        # Count embedded documents
        embedded_result = await db.execute(
            select(func.count(Document.id))
            .where(Document.workspace_id == workspace.id)
            .where(Document.is_embedded == True)
        )
        embedded_count = embedded_result.scalar() or 0
        
        # Check if RAG collection exists and get point count
        has_collection = False
        rag_points = 0
        try:
            collection_name = f"workspace_{workspace.id}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.QDRANT_URL}/collections/{collection_name}")
                if response.status_code == 200:
                    has_collection = True
                    data = response.json()
                    rag_points = data.get("result", {}).get("points_count", 0)
                    total_collections += 1
        except:
            pass
        
        workspaces_info.append(WorkspaceInfo(
            id=workspace.id,
            name=workspace.name,
            owner_email=owner_email,
            document_count=doc_count,
            embedded_count=embedded_count,
            has_rag_collection=has_collection,
            rag_points=rag_points,
            admin_pinned=workspace.admin_pinned or False
        ))
    
    return SystemOverviewResponse(
        workspaces=workspaces_info,
        total_rag_collections=total_collections
    )


@router.get("/test/llm")
async def test_llm_connection(
    admin: User = Depends(get_current_admin)
):
    """Test LLM connection and list available models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.LLM_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"} if settings.LLM_API_KEY else {}
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", m) for m in data.get("data", [])]
                return {
                    "status": "connected",
                    "url": settings.LLM_BASE_URL,
                    "models": models,
                    "configured_model": settings.LLM_MODEL
                }
            else:
                return {"status": "error", "url": settings.LLM_BASE_URL, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "url": settings.LLM_BASE_URL, "error": str(e)}


@router.get("/test/embedder")
async def test_embedder_connection(
    admin: User = Depends(get_current_admin)
):
    """Test Embedder connection and list available models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.EMBEDDER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.EMBEDDER_API_KEY}"} if settings.EMBEDDER_API_KEY else {}
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", m) for m in data.get("data", [])]
                return {
                    "status": "connected",
                    "url": settings.EMBEDDER_BASE_URL,
                    "models": models,
                    "configured_model": settings.EMBEDDER_MODEL
                }
            else:
                return {"status": "error", "url": settings.EMBEDDER_BASE_URL, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "url": settings.EMBEDDER_BASE_URL, "error": str(e)}


@router.get("/test/pdf-provider")
async def test_pdf_provider(
    admin: User = Depends(get_current_admin)
):
    """Test PDF to Markdown provider configuration"""
    provider = settings.PDF_PROVIDER.lower()
    
    if provider == "docling-api":
        if not settings.DOCLING_SERVICE_URL:
            return {
                "status": "not_configured",
                "provider": "docling-api",
                "message": "DOCLING_SERVICE_URL not set. Configure it to use docling-serve API."
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.DOCLING_SERVICE_URL}/health")
                if response.status_code == 200:
                    return {
                        "status": "connected",
                        "provider": "docling-api",
                        "url": settings.DOCLING_SERVICE_URL,
                        "message": "Docling-serve API is available (GPU-accelerated)"
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "docling-api",
                        "url": settings.DOCLING_SERVICE_URL,
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "provider": "docling-api",
                "url": settings.DOCLING_SERVICE_URL,
                "error": str(e)
            }
    
    elif provider == "marker-api":
        if not settings.OCR_SERVICE_URL:
            return {
                "status": "not_configured",
                "provider": "marker-api",
                "message": "OCR_SERVICE_URL not set. Configure it to use Marker API."
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.OCR_SERVICE_URL}/health")
                if response.status_code == 200:
                    return {
                        "status": "connected",
                        "provider": "marker-api",
                        "url": settings.OCR_SERVICE_URL,
                        "message": "Marker API is available for PDF OCR"
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "marker-api",
                        "url": settings.OCR_SERVICE_URL,
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "provider": "marker-api",
                "url": settings.OCR_SERVICE_URL,
                "error": str(e)
            }
    
    elif provider == "pypdf2":
        try:
            from PyPDF2 import PdfReader
            return {
                "status": "available",
                "provider": "pypdf2",
                "message": "PyPDF2 is available (basic text extraction, no OCR)"
            }
        except ImportError:
            return {
                "status": "error",
                "provider": "pypdf2",
                "error": "PyPDF2 not installed"
            }
    
    else:
        return {
            "status": "error",
            "provider": provider,
            "error": f"Unknown provider: {provider}. Use 'docling', 'marker-api', or 'pypdf2'"
        }


@router.get("/test/qdrant")
async def test_qdrant_connection(
    admin: User = Depends(get_current_admin)
):
    """Test Qdrant connection and list collections"""
    try:
        collections = rag_service.client.get_collections()
        collection_info = []
        for c in collections.collections:
            try:
                info = rag_service.client.get_collection(c.name)
                collection_info.append({
                    "name": c.name,
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count
                })
            except:
                collection_info.append({"name": c.name, "points_count": "?", "vectors_count": "?"})
        
        return {
            "status": "connected",
            "url": settings.QDRANT_URL,
            "collections": collection_info,
            "total_collections": len(collection_info)
        }
    except Exception as e:
        return {"status": "error", "url": settings.QDRANT_URL, "error": str(e)}


@router.put("/workspaces/{workspace_id}/pin")
async def toggle_workspace_pin(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Toggle admin_pinned status for a workspace"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace.admin_pinned = not workspace.admin_pinned
    await db.commit()
    await db.refresh(workspace)
    
    return {"id": workspace.id, "admin_pinned": workspace.admin_pinned}


# ============================================================================
# RAG EVALUATOR
# ============================================================================

class EvaluationRequest(BaseModel):
    workspace_id: int
    document_id: int
    question: str
    top_n: int = 5


class EvaluationResult(BaseModel):
    mode: str
    response: str
    response_length: int
    context_length: int
    time_seconds: float
    chunks_retrieved: Optional[int] = None
    document_words: Optional[int] = None


class ComparisonResult(BaseModel):
    rag: EvaluationResult
    cag: EvaluationResult
    evaluation: Optional[Dict[str, Any]] = None


@router.post("/evaluate/rag")
async def evaluate_rag_mode(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Evaluate RAG response for a question against a workspace"""
    start_time = time.time()
    
    # Search Qdrant
    rag_results = await rag_service.search(
        workspace_id=request.workspace_id,
        query=request.question,
        limit=request.top_n,
        hybrid=True
    )
    
    if not rag_results:
        raise HTTPException(status_code=404, detail="No RAG results found")
    
    # Build context
    context_parts = []
    for i, r in enumerate(rag_results, 1):
        context_parts.append(f"[{i}] {r['content']}")
    rag_context = "\n\n---\n\n".join(context_parts)
    
    # Generate response
    response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": request.question}],
        rag_context=rag_context
    ):
        response += chunk
    
    total_time = time.time() - start_time
    
    # Estimate tokens (4 chars ≈ 1 token)
    context_tokens = len(rag_context) // 4
    response_tokens = len(response) // 4
    
    return {
        "mode": "RAG",
        "response": response,
        "response_tokens": response_tokens,
        "context_tokens": context_tokens,
        "time_seconds": round(total_time, 2),
        "chunks_retrieved": len(rag_results),
        "chunks": [
            {
                "content_type": r.get("content_type", "text"),
                "section_title": r.get("section_title", ""),
                "word_count": r.get("word_count", 0),
                "score": round(r.get("score", 0), 4),
                "preview": r.get("content", "")[:200]
            }
            for r in rag_results
        ]
    }


@router.post("/evaluate/cag")
async def evaluate_cag_mode(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Evaluate CAG response (full document as context)"""
    start_time = time.time()
    
    # Get document
    result = await db.execute(select(Document).where(Document.id == request.document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Read markdown content
    if not document.markdown_path or not os.path.exists(document.markdown_path):
        raise HTTPException(status_code=404, detail="Markdown file not found")
    
    with open(document.markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Generate response with full document
    response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": request.question}],
        file_content=f"[DOCUMENT: {document.original_filename}]:\n{content}\n[END DOCUMENT]"
    ):
        response += chunk
    
    total_time = time.time() - start_time
    
    # Estimate tokens (4 chars ≈ 1 token)
    context_tokens = len(content) // 4
    response_tokens = len(response) // 4
    
    return {
        "mode": "CAG",
        "response": response,
        "response_tokens": response_tokens,
        "context_tokens": context_tokens,
        "time_seconds": round(total_time, 2),
        "document_words": len(content.split()),
        "document_name": document.original_filename
    }


@router.post("/evaluate/compare")
async def evaluate_compare(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Compare RAG vs CAG and get LLM evaluation"""
    
    # Run RAG evaluation
    rag_start = time.time()
    rag_results = await rag_service.search(
        workspace_id=request.workspace_id,
        query=request.question,
        limit=request.top_n,
        hybrid=True
    )
    
    if not rag_results:
        raise HTTPException(status_code=404, detail="No RAG results found")
    
    context_parts = [f"[{i}] {r['content']}" for i, r in enumerate(rag_results, 1)]
    rag_context = "\n\n---\n\n".join(context_parts)
    
    rag_response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": request.question}],
        rag_context=rag_context
    ):
        rag_response += chunk
    rag_time = time.time() - rag_start
    
    # Run CAG evaluation
    cag_start = time.time()
    result = await db.execute(select(Document).where(Document.id == request.document_id))
    document = result.scalar_one_or_none()
    
    if not document or not document.markdown_path:
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(document.markdown_path, "r", encoding="utf-8") as f:
        doc_content = f.read()
    
    cag_response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": request.question}],
        file_content=f"[DOCUMENT]:\n{doc_content}\n[END DOCUMENT]"
    ):
        cag_response += chunk
    cag_time = time.time() - cag_start
    
    # LLM evaluation
    eval_prompt = f"""Jämför dessa två AI-svar på frågan och utvärdera kvaliteten.

FRÅGA: {request.question}

--- RAG-SVAR (hämtade {len(rag_results)} relevanta delar) ---
{rag_response}

--- CAG-SVAR (hela dokumentet som kontext) ---
{cag_response}

Utvärdera på skala 1-10:
1. Relevans - Hur väl besvaras frågan?
2. Fullständighet - Täcks alla viktiga aspekter?
3. Precision - Är informationen korrekt och specifik?
4. Läsbarhet - Är svaret välstrukturerat?

Svara ENDAST med JSON (inget annat):
{{"rag_scores": {{"relevans": X, "fullständighet": X, "precision": X, "läsbarhet": X, "total": X}}, "cag_scores": {{"relevans": X, "fullständighet": X, "precision": X, "läsbarhet": X, "total": X}}, "winner": "RAG" eller "CAG" eller "TIE", "reasoning": "Kort förklaring"}}"""

    eval_response = await llm_service.generate(eval_prompt, temperature=0.2, max_tokens=800)
    
    # Parse evaluation JSON
    evaluation = None
    try:
        import json
        json_start = eval_response.find('{')
        json_end = eval_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            evaluation = json.loads(eval_response[json_start:json_end])
    except:
        evaluation = {"raw": eval_response}
    
    return {
        "question": request.question,
        "rag": {
            "response": rag_response,
            "response_tokens": len(rag_response) // 4,
            "context_tokens": len(rag_context) // 4,
            "time_seconds": round(rag_time, 2),
            "chunks_retrieved": len(rag_results)
        },
        "cag": {
            "response": cag_response,
            "response_tokens": len(cag_response) // 4,
            "context_tokens": len(doc_content) // 4,
            "time_seconds": round(cag_time, 2),
            "document_words": len(doc_content.split())
        },
        "evaluation": evaluation
    }


@router.get("/evaluate/documents/{workspace_id}")
async def get_evaluable_documents(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get documents available for evaluation in a workspace.
    
    Returns all documents that have markdown (for CAG).
    RAG evaluation requires is_embedded=True, but CAG only needs markdown.
    """
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
    )
    documents = result.scalars().all()
    
    # Filter to documents that have markdown file
    evaluable = []
    for doc in documents:
        if doc.markdown_path:
            # Handle both relative and absolute paths
            md_path = doc.markdown_path
            if not os.path.isabs(md_path):
                # Try relative to DATA_DIR first, then current dir
                base_dir = settings.DATA_DIR.rstrip('/')
                if md_path.startswith('data/'):
                    md_path = md_path.replace('data/', f'{base_dir}/', 1)
                else:
                    md_path = os.path.join(base_dir, md_path.lstrip('/'))
            
            if os.path.exists(md_path):
                evaluable.append({
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "is_embedded": doc.is_embedded,
                    "embedded_at": doc.embedded_at
                })
    
    return evaluable


@router.post("/evaluate/save")
async def save_evaluation(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Save an evaluation result to the database"""
    evaluation = RagEvaluation(
        workspace_id=data.get("workspace_id"),
        document_id=data.get("document_id"),
        document_name=data.get("document_name"),
        question=data.get("question"),
        rag_response=data.get("rag", {}).get("response"),
        rag_context_tokens=data.get("rag", {}).get("context_tokens"),
        rag_response_tokens=data.get("rag", {}).get("response_tokens"),
        rag_time_seconds=data.get("rag", {}).get("time_seconds"),
        rag_chunks_retrieved=data.get("rag", {}).get("chunks_retrieved"),
        cag_response=data.get("cag", {}).get("response"),
        cag_context_tokens=data.get("cag", {}).get("context_tokens"),
        cag_response_tokens=data.get("cag", {}).get("response_tokens"),
        cag_time_seconds=data.get("cag", {}).get("time_seconds"),
        rag_scores=data.get("evaluation", {}).get("rag_scores"),
        cag_scores=data.get("evaluation", {}).get("cag_scores"),
        winner=data.get("evaluation", {}).get("winner"),
        reasoning=data.get("evaluation", {}).get("reasoning"),
        created_by=admin.id
    )
    
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    
    return {"id": evaluation.id, "saved": True}


@router.get("/evaluate/history")
async def get_evaluation_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get saved evaluation history"""
    from sqlalchemy import desc
    
    result = await db.execute(
        select(RagEvaluation)
        .order_by(desc(RagEvaluation.created_at))
        .limit(limit)
    )
    evaluations = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "workspace_id": e.workspace_id,
            "document_name": e.document_name,
            "question": e.question,
            "winner": e.winner,
            "rag_score": e.rag_scores.get("total") if e.rag_scores else None,
            "cag_score": e.cag_scores.get("total") if e.cag_scores else None,
            "rag_context_tokens": e.rag_context_tokens,
            "cag_context_tokens": e.cag_context_tokens,
            "created_at": e.created_at
        }
        for e in evaluations
    ]


@router.get("/evaluate/history/{evaluation_id}")
async def get_evaluation_detail(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get full details of a saved evaluation"""
    result = await db.execute(
        select(RagEvaluation).where(RagEvaluation.id == evaluation_id)
    )
    e = result.scalar_one_or_none()
    
    if not e:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return {
        "id": e.id,
        "workspace_id": e.workspace_id,
        "document_id": e.document_id,
        "document_name": e.document_name,
        "question": e.question,
        "rag": {
            "response": e.rag_response,
            "context_tokens": e.rag_context_tokens,
            "response_tokens": e.rag_response_tokens,
            "time_seconds": e.rag_time_seconds,
            "chunks_retrieved": e.rag_chunks_retrieved
        },
        "cag": {
            "response": e.cag_response,
            "context_tokens": e.cag_context_tokens,
            "response_tokens": e.cag_response_tokens,
            "time_seconds": e.cag_time_seconds
        },
        "evaluation": {
            "rag_scores": e.rag_scores,
            "cag_scores": e.cag_scores,
            "winner": e.winner,
            "reasoning": e.reasoning
        },
        "created_at": e.created_at
    }


@router.delete("/evaluate/history/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a saved evaluation"""
    result = await db.execute(
        select(RagEvaluation).where(RagEvaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    await db.delete(evaluation)
    await db.commit()
    
    return {"deleted": True}
