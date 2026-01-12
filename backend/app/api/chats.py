from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import time
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.chat import Chat, Message
from app.models.chat_log import ChatLog
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.search_agent_service import search_agent_service
from app.services.firecrawl_service import firecrawl_service
from app.services.file_parser import parse_pdf, parse_docx
from app.core.config import settings

router = APIRouter(prefix="/api/chats", tags=["chats"])


class ChatCreate(BaseModel):
    workspace_id: int
    title: Optional[str] = "New Chat"


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class ChatResponse(BaseModel):
    id: int
    title: str
    workspace_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    use_rag: bool = True
    files: Optional[List[str]] = None  # File contents as text/markdown


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/workspace/{workspace_id}", response_model=List[ChatResponse])
async def list_chats(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat)
        .where(Chat.workspace_id == workspace_id)
        .where(Chat.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ChatResponse)
async def create_chat(
    data: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Workspace).where(Workspace.id == data.workspace_id)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if current_user.role != "admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    chat = Chat(
        title=data.title,
        workspace_id=data.workspace_id,
        user_id=current_user.id
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    return chat


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return chat


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    data: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if data.title is not None:
        chat.title = data.title
    
    await db.commit()
    await db.refresh(chat)
    
    return chat


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send message without file attachments (JSON body)"""
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.workspace))
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=data.content
    )
    db.add(user_message)
    await db.commit()
    
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    history = [{"role": m.role, "content": m.content} for m in messages]
    
    rag_context = None
    rag_sources = []
    web_sources = []
    if data.use_rag:
        # Determine RAG settings based on rag_mode
        rag_mode = chat.workspace.rag_mode if chat.workspace and chat.workspace.rag_mode else "global"
        
        if rag_mode == "precise":
            top_n = settings.RAG_PRECISE_TOP_N
            threshold = settings.RAG_PRECISE_THRESHOLD
        elif rag_mode == "comprehensive":
            top_n = settings.RAG_COMPREHENSIVE_TOP_N
            threshold = settings.RAG_COMPREHENSIVE_THRESHOLD
        else:  # "global" - use global defaults
            top_n = settings.DEFAULT_TOP_N
            threshold = settings.DEFAULT_SIMILARITY_THRESHOLD
        
        use_hybrid = chat.workspace.use_hybrid_search if chat.workspace and chat.workspace.use_hybrid_search is not None else settings.DEFAULT_USE_HYBRID_SEARCH
        use_reranking = chat.workspace.use_reranking if chat.workspace else False
        rerank_top_k = chat.workspace.rerank_top_k if chat.workspace else 20
        use_query_expansion = chat.workspace.use_query_expansion if chat.workspace else False
        
        # If reranking is enabled, fetch more candidates initially, then rerank and limit to top_n
        initial_limit = rerank_top_k if use_reranking else top_n
        
        rag_results = await rag_service.search(
            chat.workspace_id, 
            data.content, 
            limit=initial_limit, 
            score_threshold=threshold, 
            hybrid=use_hybrid,
            use_reranking=use_reranking,
            rerank_top_k=top_n,  # Pass final desired count to reranker
            use_query_expansion=use_query_expansion
        )
        if rag_results:
            # Format context with source markers like [1], [2], etc.
            context_parts = []
            seen_files = {}
            for i, r in enumerate(rag_results, 1):
                filename = r.get("filename", "")
                # If filename is empty, get it from database using document_id
                if not filename:
                    doc_id = r.get("document_id")
                    if doc_id:
                        doc_result = await db.execute(
                            select(Document).where(Document.id == doc_id)
                        )
                        doc = doc_result.scalar_one_or_none()
                        if doc:
                            filename = doc.original_filename
                        else:
                            filename = f"Document {doc_id}"
                    else:
                        filename = "Unknown"
                
                if filename not in seen_files:
                    seen_files[filename] = len(seen_files) + 1
                source_num = seen_files[filename]
                # Include filename in context so LLM knows what to cite
                context_parts.append(f"[{source_num}] (Source: {filename})\n{r['content']}")
                if filename not in [s["filename"] for s in rag_sources]:
                    rag_sources.append({"num": source_num, "filename": filename, "type": "rag"})
            rag_context = "\n\n---\n\n".join(context_parts)
    
    # Prepare web search tool for LLM (if enabled)
    tools = []
    use_web_search = chat.workspace.use_web_search if chat.workspace and chat.workspace.use_web_search else False
    
    if use_web_search and settings.FIRECRAWL_API_KEY:
        # Define web search tool for LLM to use when needed
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information, news, facts, or real-time data. Use this when the user asks about recent events, current news, or information you don't have in your training data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant information"
                        }
                    },
                    "required": ["query"]
                }
            }
        }]
        print(f"[Tool Calling] Web search tool available for LLM")
    
    system_prompt = chat.workspace.system_prompt if chat.workspace else None
    chat_mode = chat.workspace.chat_mode if chat.workspace else "chat"
    
    # In query mode, refuse to answer if no RAG context found
    if chat_mode == "query" and not rag_context:
        no_context_response = "There is no relevant information in this workspace to answer your query."
        
        async def refuse():
            yield f"data: {json.dumps({'content': no_context_response})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            
            async with db.begin():
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=no_context_response
                )
                db.add(assistant_message)
                await db.commit()
        
        return StreamingResponse(
            refuse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    async def generate():
        start_time = time.time()
        full_response = ""
        
        try:
            # Use tool calling if web search is available
            if tools:
                print(f"[Tool Calling] Checking if LLM wants to use tools...")
                
                # First, ask LLM if it wants to use tools (non-streaming)
                llm_response = await llm_service.chat_with_tools(
                    messages=history,
                    tools=tools,
                    system_prompt=system_prompt,
                    rag_context=rag_context
                )
                
                # Check if LLM made tool calls
                tool_calls = llm_response.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
                
                if tool_calls:
                    # LLM wants to use tools - execute them
                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        tool_name = function.get("name")
                        arguments = json.loads(function.get("arguments", "{}"))
                        
                        if tool_name == "web_search":
                            query = arguments.get("query", "")
                            print(f"[Tool Calling] LLM requested web search: {query}")
                            
                            # Execute web search with more results
                            search_result = await firecrawl_service.search(query=query, limit=5)
                            
                            if search_result:
                                # Unpack result and sources
                                result_text, web_sources_list = search_result
                                web_sources.extend(web_sources_list)
                                
                                # Add search result to context and stream final response
                                enhanced_context = f"{rag_context}\n\n---\n\nWeb Search Results:\n{result_text}" if rag_context else f"Web Search Results:\n{result_text}"
                                
                                async for chunk in llm_service.chat_completion_stream(
                                    messages=history,
                                    system_prompt=system_prompt,
                                    rag_context=enhanced_context
                                ):
                                    full_response += chunk
                                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                            else:
                                print(f"[Tool Calling] Web search returned no results, using original response")
                                content = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                                full_response = content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                else:
                    # No tool calls - stream the response directly
                    print(f"[Tool Calling] LLM decided not to use tools")
                    content = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    full_response = content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            else:
                # Regular streaming completion without tools
                async for chunk in llm_service.chat_completion_stream(
                    messages=history,
                    system_prompt=system_prompt,
                    rag_context=rag_context
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # Send sources/citations if available (prioritize web sources over RAG if both exist)
            sources_to_send = web_sources if web_sources else rag_sources
            if sources_to_send:
                yield f"data: {json.dumps({'sources': sources_to_send})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
            async with db.begin():
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=full_response
                )
                db.add(assistant_message)
                
                chat_log = ChatLog(
                    user_id=current_user.id,
                    workspace_id=chat.workspace_id,
                    chat_id=chat_id,
                    prompt=data.content,
                    response=full_response,
                    latency_ms=(time.time() - start_time) * 1000,
                    rag_context=rag_context
                )
                db.add(chat_log)
                await db.commit()
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/{chat_id}/messages/upload")
async def send_message_with_files(
    chat_id: int,
    content: str = Form(...),
    use_rag: bool = Form(True),
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.workspace))
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Parse attached files to text/markdown
    file_contents = []
    if files:
        for file in files:
            if file.filename:
                try:
                    # Read file content
                    file_content = await file.read()
                    
                    # Parse based on file type
                    if file.filename.lower().endswith('.pdf'):
                        text_content = await parse_pdf(file_content)
                    elif file.filename.lower().endswith('.docx'):
                        text_content = await parse_docx(file_content)
                    elif file.filename.lower().endswith('.txt') or file.filename.lower().endswith('.md'):
                        text_content = file_content.decode('utf-8')
                    else:
                        continue  # Skip unsupported files
                    
                    file_contents.append(f"[CONTEXT FILE: {file.filename}]:\n{text_content}\n[END CONTEXT FILE: {file.filename}]")
                except Exception as e:
                    print(f"Error parsing file {file.filename}: {e}")
                    continue
    
    # Store the original user message (without file content) for chat history
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=content  # Only the user message, not including file content
    )
    db.add(user_message)
    await db.commit()
    
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    history = [{"role": m.role, "content": m.content} for m in messages]
    
    rag_context = None
    rag_sources = []
    if use_rag:
        top_n = chat.workspace.top_n if chat.workspace and chat.workspace.top_n else 4
        threshold = chat.workspace.similarity_threshold if chat.workspace and chat.workspace.similarity_threshold else 0.0
        use_hybrid = chat.workspace.use_hybrid_search if chat.workspace and chat.workspace.use_hybrid_search is not None else True
        use_reranking = chat.workspace.use_reranking if chat.workspace else False
        rerank_top_k = chat.workspace.rerank_top_k if chat.workspace else 20
        use_query_expansion = chat.workspace.use_query_expansion if chat.workspace else False
        
        # If reranking is enabled, fetch more candidates initially, then rerank and limit to top_n
        initial_limit = rerank_top_k if use_reranking else top_n
        
        rag_results = await rag_service.search(
            chat.workspace_id, 
            content, 
            limit=initial_limit, 
            score_threshold=threshold, 
            hybrid=use_hybrid,
            use_reranking=use_reranking,
            rerank_top_k=top_n,  # Pass final desired count to reranker
            use_query_expansion=use_query_expansion
        )
        if rag_results:
            # Format context with source markers like [1], [2], etc.
            context_parts = []
            seen_files = {}
            for i, r in enumerate(rag_results, 1):
                filename = r.get("filename", "")
                # If filename is empty, get it from database using document_id
                if not filename:
                    doc_id = r.get("document_id")
                    if doc_id:
                        doc_result = await db.execute(
                            select(Document).where(Document.id == doc_id)
                        )
                        doc = doc_result.scalar_one_or_none()
                        if doc:
                            filename = doc.original_filename
                        else:
                            filename = f"Document {doc_id}"
                    else:
                        filename = "Unknown"
                
                if filename not in seen_files:
                    seen_files[filename] = len(seen_files) + 1
                source_num = seen_files[filename]
                # Include filename in context so LLM knows what to cite
                context_parts.append(f"[{source_num}] (Source: {filename})\n{r['content']}")
                if filename not in [s["filename"] for s in rag_sources]:
                    rag_sources.append({"num": source_num, "filename": filename, "type": "rag"})
            rag_context = "\n\n---\n\n".join(context_parts)
    
    # Web search via external agent (n8n)
    web_search_context = None
    use_web_search = chat.workspace.use_web_search if chat.workspace and chat.workspace.use_web_search else False
    if use_web_search and search_agent_service.is_available():
        web_result = await search_agent_service.search(
            query=content,
            session_id=str(chat.id),
            system_prompt=chat.workspace.system_prompt if chat.workspace else None
        )
        if web_result:
            web_search_context = f"Web Search Results:\n{web_result}"
    
    system_prompt = chat.workspace.system_prompt if chat.workspace else None
    chat_mode = chat.workspace.chat_mode if chat.workspace else "chat"
    
    # Combine file contents for LLM context (AnythingLLM-style formatting)
    file_context = "\n\n".join(file_contents) if file_contents else None
    
    # In query mode, refuse to answer if no RAG context and no file context
    if chat_mode == "query" and not rag_context and not file_context:
        no_context_response = "There is no relevant information in this workspace to answer your query."
        
        async def refuse():
            yield f"data: {json.dumps({'content': no_context_response})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            
            async with db.begin():
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=no_context_response
                )
                db.add(assistant_message)
                await db.commit()
        
        return StreamingResponse(
            refuse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    # Combine RAG and web search contexts
    combined_context = None
    if rag_context and web_search_context:
        combined_context = f"{rag_context}\n\n---\n\n{web_search_context}"
    elif rag_context:
        combined_context = rag_context
    elif web_search_context:
        combined_context = web_search_context
    
    async def generate():
        start_time = time.time()
        full_response = ""
        
        try:
            async for chunk in llm_service.chat_completion_stream(
                messages=history,
                system_prompt=system_prompt,
                rag_context=combined_context,
                file_content=file_context
            ):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
            async with db.begin():
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=full_response
                )
                db.add(assistant_message)
                
                # Store the full prompt including files for logging
                full_prompt = content
                if file_context:
                    full_prompt += "\n\n" + file_context
                
                chat_log = ChatLog(
                    user_id=current_user.id,
                    workspace_id=chat.workspace_id,
                    chat_id=chat_id,
                    prompt=full_prompt,  # Store the full prompt including files
                    response=full_response,
                    latency_ms=(time.time() - start_time) * 1000,
                    rag_context=rag_context
                )
                db.add(chat_log)
                await db.commit()
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(chat)
    await db.commit()
    
    return {"status": "deleted"}


@router.put("/{chat_id}/title")
async def update_chat_title(
    chat_id: int,
    title: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if current_user.role != "admin" and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    chat.title = title
    await db.commit()
    
    return {"status": "updated"}
