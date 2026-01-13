from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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
from app.core.security import get_current_admin, get_password_hash, security
from fastapi.security import HTTPAuthorizationCredentials
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.chat import Chat, Message
from app.models.chat_log import ChatLog
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.document_service import document_service
from app.services.settings_service import settings_service, ADMIN_SETTINGS
from app.models.evaluation import RagEvaluation
from app.models.ab_evaluation import ABTestRun, ABTestQuery, ABTestDocument
from app.models.api_key import APIKey
import secrets

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
    vector_store: str = "qdrant"  # "qdrant" or "lancedb"


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
            stats = await rag_service.vector_store.get_stats(workspace.id)
            if stats.vector_count > 0:
                has_collection = True
                rag_points = stats.vector_count
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
        total_rag_collections=total_collections,
        vector_store=rag_service.vector_store.name
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
    
    elif provider == "pdfplumber":
        try:
            import pdfplumber
            return {
                "status": "available",
                "provider": "pdfplumber",
                "message": "pdfplumber is available (table extraction, better layout)"
            }
        except ImportError:
            return {
                "status": "error",
                "provider": "pdfplumber",
                "error": "pdfplumber not installed"
            }
    
    else:
        return {
            "status": "error",
            "provider": provider,
            "error": f"Unknown provider: {provider}. Use 'docling-api', 'marker-api', or 'pdfplumber'"
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


# =============================================================================
# System Settings
# =============================================================================

class SettingUpdate(BaseModel):
    value: Any


@router.get("/settings")
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get all system settings with current values and sources."""
    return await settings_service.get_all(db)


@router.put("/settings/{key}")
async def update_system_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update a system setting (overrides .env default)."""
    if key not in ADMIN_SETTINGS:
        raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")
    
    success = await settings_service.set(db, key, data.value)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update setting")
    
    # Special handling for vector_store - switch active store
    if key == "vector_store" and data.value in ("qdrant", "lancedb"):
        rag_service.switch_vector_store(data.value)
    
    return {"key": key, "value": data.value, "source": "database"}


@router.delete("/settings/{key}")
async def reset_system_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Reset a setting to .env default."""
    await settings_service.reset(db, key)
    
    # Return the default value
    env_attr = ADMIN_SETTINGS[key][0]
    default_value = getattr(settings, env_attr, None)
    
    # Special handling for vector_store - switch back to default
    if key == "vector_store":
        rag_service.switch_vector_store(default_value or "qdrant")
    
    return {"key": key, "value": default_value, "source": "default"}


# =============================================================================
# A/B Test Evaluator (AnythingLLM vs Private AI)
# =============================================================================

class ABTestConfig(BaseModel):
    name: str
    description: Optional[str] = None
    anythingllm_url: str
    anythingllm_api_key: str
    anythingllm_workspace: str
    privateai_url: str
    privateai_workspace_id: int
    queries: List[Dict[str, Any]]


class ABTestRunResponse(BaseModel):
    id: int
    name: str
    status: str
    num_queries: int
    num_documents: int
    winner: Optional[str]
    anythingllm_recall: Optional[float]
    anythingllm_mrr: Optional[float]
    privateai_recall: Optional[float]
    privateai_mrr: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/abtest/runs")
async def list_ab_test_runs(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all A/B test runs"""
    result = await db.execute(
        select(ABTestRun)
        .order_by(ABTestRun.created_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "status": r.status,
            "num_queries": r.num_queries,
            "num_documents": r.num_documents,
            "winner": r.winner,
            "winner_reason": r.winner_reason,
            "anythingllm_recall": r.anythingllm_recall,
            "anythingllm_mrr": r.anythingllm_mrr,
            "anythingllm_avg_latency": r.anythingllm_avg_latency,
            "anythingllm_avg_faithfulness": r.anythingllm_avg_faithfulness,
            "privateai_recall": r.privateai_recall,
            "privateai_mrr": r.privateai_mrr,
            "privateai_avg_latency": r.privateai_avg_latency,
            "privateai_avg_faithfulness": r.privateai_avg_faithfulness,
            "created_at": r.created_at,
            "completed_at": r.completed_at
        }
        for r in runs
    ]


@router.get("/abtest/config")
async def get_ab_test_config(
    admin: User = Depends(get_current_admin)
):
    """Get A/B test configuration from environment variables"""
    return {
        "anythingllm_url": settings.ABTEST_ANYTHINGLLM_URL,
        "anythingllm_api_key": settings.ABTEST_ANYTHINGLLM_API_KEY,
        "anythingllm_workspace": settings.ABTEST_ANYTHINGLLM_WORKSPACE,
        "privateai_url": settings.ABTEST_PRIVATEAI_URL,
        "privateai_api_key": settings.ABTEST_PRIVATEAI_API_KEY,
        "privateai_workspace_id": settings.ABTEST_PRIVATEAI_WORKSPACE_ID,
    }


@router.get("/abtest/runs/{run_id}")
async def get_ab_test_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get detailed results for a specific A/B test run"""
    result = await db.execute(
        select(ABTestRun).where(ABTestRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # Get all queries for this run
    queries_result = await db.execute(
        select(ABTestQuery)
        .where(ABTestQuery.run_id == run_id)
        .order_by(ABTestQuery.id)
    )
    queries = queries_result.scalars().all()
    
    return {
        "run": {
            "id": run.id,
            "name": run.name,
            "description": run.description,
            "status": run.status,
            "num_queries": run.num_queries,
            "num_documents": run.num_documents,
            "winner": run.winner,
            "winner_reason": run.winner_reason,
            "anythingllm_url": run.anythingllm_url,
            "anythingllm_workspace": run.anythingllm_workspace,
            "privateai_url": run.privateai_url,
            "privateai_workspace_id": run.privateai_workspace_id,
            "anythingllm_recall": run.anythingllm_recall,
            "anythingllm_mrr": run.anythingllm_mrr,
            "anythingllm_avg_latency": run.anythingllm_avg_latency,
            "anythingllm_avg_faithfulness": run.anythingllm_avg_faithfulness,
            "anythingllm_avg_relevancy": run.anythingllm_avg_relevancy,
            "privateai_recall": run.privateai_recall,
            "privateai_mrr": run.privateai_mrr,
            "privateai_avg_latency": run.privateai_avg_latency,
            "privateai_avg_faithfulness": run.privateai_avg_faithfulness,
            "privateai_avg_relevancy": run.privateai_avg_relevancy,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
            "error_message": run.error_message
        },
        "queries": [
            {
                "id": q.id,
                "query_id": q.query_id,
                "query": q.query,
                "category": q.category,
                "difficulty": q.difficulty,
                "ground_truth_docs": q.ground_truth_docs,
                "anythingllm": {
                    "answer": q.anythingllm_answer,
                    "latency": q.anythingllm_latency,
                    "faithfulness": q.anythingllm_faithfulness,
                    "relevancy": q.anythingllm_relevancy,
                    "retrieved_docs": q.anythingllm_retrieved_docs,
                    "recall": q.anythingllm_recall,
                    "mrr": q.anythingllm_mrr
                },
                "privateai": {
                    "answer": q.privateai_answer,
                    "latency": q.privateai_latency,
                    "faithfulness": q.privateai_faithfulness,
                    "relevancy": q.privateai_relevancy,
                    "retrieved_docs": q.privateai_retrieved_docs,
                    "recall": q.privateai_recall,
                    "mrr": q.privateai_mrr
                },
                "winner": q.winner
            }
            for q in queries
        ]
    }


@router.post("/abtest/runs")
async def create_ab_test_run(
    config: ABTestConfig,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a new A/B test run (starts in pending state)"""
    run = ABTestRun(
        name=config.name,
        description=config.description,
        anythingllm_url=config.anythingllm_url,
        anythingllm_workspace=config.anythingllm_workspace,
        privateai_url=config.privateai_url,
        privateai_workspace_id=config.privateai_workspace_id,
        num_queries=len(config.queries),
        num_documents=0,
        status="pending",
        created_by=admin.id
    )
    
    db.add(run)
    await db.commit()
    await db.refresh(run)
    
    # Create query records
    for q in config.queries:
        query = ABTestQuery(
            run_id=run.id,
            query_id=q.get("id", f"q_{len(config.queries)}"),
            query=q["query"],
            category=q.get("category"),
            difficulty=q.get("difficulty"),
            ground_truth_docs=q.get("ground_truth_docs", [])
        )
        db.add(query)
    
    await db.commit()
    
    return {"id": run.id, "status": "pending", "message": "Test run created. Call /abtest/runs/{id}/execute to start."}


@router.post("/abtest/runs/{run_id}/execute")
async def execute_ab_test_run(
    run_id: int,
    anythingllm_api_key: str = Query(..., description="AnythingLLM API key"),
    privateai_api_key: Optional[str] = Query(None, description="Private AI API key (pk_xxx) or leave empty to use current session"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Execute an A/B test run - queries both systems and evaluates results"""
    # Use provided API key or fall back to current session token
    privateai_token = privateai_api_key or credentials.credentials
    result = await db.execute(
        select(ABTestRun).where(ABTestRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    if run.status == "running":
        raise HTTPException(status_code=400, detail="Test is already running")
    
    # Update status
    run.status = "running"
    await db.commit()
    
    # Get queries
    queries_result = await db.execute(
        select(ABTestQuery).where(ABTestQuery.run_id == run_id)
    )
    queries = queries_result.scalars().all()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            for query in queries:
                # Query AnythingLLM
                try:
                    start_time = time.time()
                    allm_response = await client.post(
                        f"{run.anythingllm_url}/api/v1/workspace/{run.anythingllm_workspace}/chat",
                        headers={"Authorization": f"Bearer {anythingllm_api_key}"},
                        json={"message": query.query, "mode": "query"}
                    )
                    allm_latency = (time.time() - start_time) * 1000
                    
                    if allm_response.status_code == 200:
                        allm_data = allm_response.json()
                        query.anythingllm_answer = allm_data.get("textResponse", "")
                        query.anythingllm_latency = allm_latency
                        
                        # Extract sources
                        sources = allm_data.get("sources", [])
                        query.anythingllm_retrieved_docs = [s.get("title", s.get("name", "unknown")) for s in sources]
                except Exception as e:
                    query.anythingllm_answer = f"Error: {str(e)}"
                
                # Query Private AI using the simple v1 API
                try:
                    start_time = time.time()
                    headers = {"Content-Type": "application/json"}
                    if privateai_token:
                        headers["Authorization"] = f"Bearer {privateai_token}"
                    
                    # Use the new simple v1 API endpoint
                    pai_response = await client.post(
                        f"{run.privateai_url}/api/v1/workspace/{run.privateai_workspace_id}/query",
                        headers=headers,
                        json={"message": query.query, "mode": "query"},
                        timeout=120.0
                    )
                    pai_latency = (time.time() - start_time) * 1000
                    
                    if pai_response.status_code == 200:
                        data = pai_response.json()
                        query.privateai_answer = data.get("response", "")
                        query.privateai_latency = data.get("latency_ms", pai_latency)
                        
                        # Extract sources
                        sources = data.get("sources", [])
                        query.privateai_retrieved_docs = [s.get("filename", "unknown") for s in sources]
                    else:
                        query.privateai_answer = f"Error: HTTP {pai_response.status_code} - {pai_response.text[:200]}"
                except Exception as e:
                    query.privateai_answer = f"Error: {str(e)}"
                
                # Calculate retrieval metrics
                gt_docs = set(query.ground_truth_docs or [])
                if gt_docs:
                    # AnythingLLM metrics
                    allm_docs = query.anythingllm_retrieved_docs or []
                    allm_hits = sum(1 for d in allm_docs[:5] if any(gt in d for gt in gt_docs))
                    query.anythingllm_recall = allm_hits / len(gt_docs) if gt_docs else 0
                    query.anythingllm_mrr = next(
                        (1.0 / (i + 1) for i, d in enumerate(allm_docs) if any(gt in d for gt in gt_docs)),
                        0.0
                    )
                    
                    # Private AI metrics
                    pai_docs = query.privateai_retrieved_docs or []
                    pai_hits = sum(1 for d in pai_docs[:5] if any(gt in d for gt in gt_docs))
                    query.privateai_recall = pai_hits / len(gt_docs) if gt_docs else 0
                    query.privateai_mrr = next(
                        (1.0 / (i + 1) for i, d in enumerate(pai_docs) if any(gt in d for gt in gt_docs)),
                        0.0
                    )
                
                # Determine per-query winner based on recall
                if query.privateai_recall and query.anythingllm_recall:
                    if query.privateai_recall > query.anythingllm_recall:
                        query.winner = "PrivateAI"
                    elif query.anythingllm_recall > query.privateai_recall:
                        query.winner = "AnythingLLM"
                    else:
                        query.winner = "TIE"
                
                await db.commit()
        
        # Calculate aggregate metrics
        all_queries = await db.execute(
            select(ABTestQuery).where(ABTestQuery.run_id == run_id)
        )
        all_queries = all_queries.scalars().all()
        
        valid_queries = [q for q in all_queries if q.anythingllm_recall is not None]
        if valid_queries:
            run.anythingllm_recall = sum(q.anythingllm_recall or 0 for q in valid_queries) / len(valid_queries)
            run.anythingllm_mrr = sum(q.anythingllm_mrr or 0 for q in valid_queries) / len(valid_queries)
            run.anythingllm_avg_latency = sum(q.anythingllm_latency or 0 for q in valid_queries) / len(valid_queries)
            
            run.privateai_recall = sum(q.privateai_recall or 0 for q in valid_queries) / len(valid_queries)
            run.privateai_mrr = sum(q.privateai_mrr or 0 for q in valid_queries) / len(valid_queries)
            run.privateai_avg_latency = sum(q.privateai_latency or 0 for q in valid_queries) / len(valid_queries)
            
            # Determine overall winner
            if run.privateai_recall > run.anythingllm_recall:
                run.winner = "PrivateAI"
                improvement = ((run.privateai_recall - run.anythingllm_recall) / run.anythingllm_recall * 100) if run.anythingllm_recall else 0
                run.winner_reason = f"Private AI wins with {improvement:.0f}% better recall ({run.privateai_recall:.2f} vs {run.anythingllm_recall:.2f})"
            elif run.anythingllm_recall > run.privateai_recall:
                run.winner = "AnythingLLM"
                improvement = ((run.anythingllm_recall - run.privateai_recall) / run.privateai_recall * 100) if run.privateai_recall else 0
                run.winner_reason = f"AnythingLLM wins with {improvement:.0f}% better recall ({run.anythingllm_recall:.2f} vs {run.privateai_recall:.2f})"
            else:
                run.winner = "TIE"
                run.winner_reason = "Both systems performed equally"
        
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        await db.commit()
        
        return {
            "status": "completed",
            "winner": run.winner,
            "winner_reason": run.winner_reason,
            "anythingllm_recall": run.anythingllm_recall,
            "privateai_recall": run.privateai_recall
        }
        
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@router.post("/abtest/generate-questions")
async def generate_test_questions(
    files: List[UploadFile] = File(...),
    num_questions: int = Query(default=10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Auto-generate test questions from uploaded PDFs using LLM.
    
    Upload 1-5 PDFs, and the LLM will:
    1. Extract content from each PDF
    2. Generate relevant questions
    3. Create expected answers (ground truth)
    4. Return ready-to-use test configuration
    """
    import json
    
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")
    
    # Extract text from all uploaded files
    all_content = []
    filenames = []
    
    for file in files:
        filename = file.filename
        filenames.append(filename)
        
        # Read file content
        content = await file.read()
        
        # Parse based on file type
        if filename.lower().endswith('.pdf'):
            # Use document service to convert PDF
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                # Try to extract text using pdfplumber (better table extraction)
                import pdfplumber
                from io import BytesIO
                
                text_parts = []
                with pdfplumber.open(BytesIO(content)) as pdf:
                    for page in pdf.pages[:20]:  # Limit to first 20 pages
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                text = "\n\n".join(text_parts)
                
                if text.strip():
                    all_content.append(f"=== Document: {filename} ===\n{text[:15000]}")  # Limit per doc
            except Exception as e:
                all_content.append(f"=== Document: {filename} ===\n[Could not extract text: {str(e)}]")
            finally:
                import os
                os.unlink(tmp_path)
        
        elif filename.lower().endswith(('.txt', '.md')):
            text = content.decode('utf-8', errors='ignore')
            all_content.append(f"=== Document: {filename} ===\n{text[:15000]}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")
    
    combined_content = "\n\n".join(all_content)
    
    # Use LLM to generate questions
    prompt = f"""You are a test question generator for a RAG (Retrieval-Augmented Generation) system evaluation.

Based on the following document content, generate exactly {num_questions} test questions that:
1. Can be answered using information from the documents
2. Cover different aspects and sections of the documents
3. Vary in difficulty (some factual, some requiring synthesis)
4. Are specific enough to have clear answers

For each question, provide:
- The question itself
- The expected answer (ground truth) based on the document
- Which document(s) contain the answer
- A difficulty level (easy/medium/hard)
- A category (factual/procedural/conceptual)

DOCUMENTS:
{combined_content[:30000]}

Respond in this exact JSON format:
{{
  "questions": [
    {{
      "query": "What is the torque specification for the impeller bolts?",
      "expected_answer": "The torque specification is 45 Nm (33 ft-lb) according to the service manual.",
      "ground_truth_docs": ["MJP-5996-SM.pdf"],
      "difficulty": "easy",
      "category": "factual"
    }}
  ]
}}

Generate exactly {num_questions} questions. Only respond with valid JSON, no other text."""

    try:
        # Call LLM
        response_text = ""
        async for chunk in llm_service.chat_completion_stream(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a precise JSON generator. Only output valid JSON.",
            rag_context=None
        ):
            response_text += chunk
        
        # Parse JSON response
        # Try to extract JSON from response (handle markdown code blocks)
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        
        result = json.loads(json_str.strip())
        questions = result.get("questions", [])
        
        return {
            "success": True,
            "num_questions": len(questions),
            "documents": filenames,
            "questions": questions,
            "message": f"Generated {len(questions)} test questions from {len(filenames)} document(s)"
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse LLM response as JSON: {str(e)}",
            "raw_response": response_text[:2000]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")


@router.delete("/abtest/runs/{run_id}")
async def delete_ab_test_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete an A/B test run and all its queries"""
    result = await db.execute(
        select(ABTestRun).where(ABTestRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    # Delete queries first
    await db.execute(
        ABTestQuery.__table__.delete().where(ABTestQuery.run_id == run_id)
    )
    
    # Delete run
    await db.delete(run)
    await db.commit()
    
    return {"deleted": True}


# =============================================================================
# API Key Management
# =============================================================================

class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # Only shown on creation
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/api-keys")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all API keys for the current admin user"""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == admin.id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key[:12] + "...",  # Only show prefix
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used_at": k.last_used_at
        }
        for k in keys
    ]


@router.post("/api-keys")
async def create_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Create a new API key.
    
    The full key is only shown once on creation.
    Store it securely - it cannot be retrieved later.
    """
    # Generate a secure API key
    key = f"pk_{secrets.token_urlsafe(32)}"
    
    api_key = APIKey(
        user_id=admin.id,
        name=data.name,
        key=key,
        is_active=True
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": key,  # Full key - only shown once!
        "is_active": api_key.is_active,
        "created_at": api_key.created_at,
        "message": "Store this key securely. It will not be shown again."
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete an API key"""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == admin.id)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    await db.delete(api_key)
    await db.commit()
    
    return {"deleted": True}


@router.patch("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Enable or disable an API key"""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == admin.id)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = not api_key.is_active
    await db.commit()
    
    return {"id": api_key.id, "is_active": api_key.is_active}
