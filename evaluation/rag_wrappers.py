"""
RAG System Wrappers for A/B Testing

Unified interface for querying both AnythingLLM and Private AI Chatspace.
Both systems share the same external LLM and Embedder services.
"""

import httpx
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class RAGResponse:
    """Standardized response from any RAG system"""
    system: str
    query: str
    answer: str
    retrieved_docs: List[str]  # Document names/IDs
    retrieved_texts: List[str]  # Actual chunk content
    latency_ms: float
    metadata: Dict[str, Any]


class RAGSystemWrapper(ABC):
    """Abstract base class for RAG system wrappers"""
    
    def __init__(self, name: str, base_url: str, api_key: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    @abstractmethod
    async def query(self, question: str) -> RAGResponse:
        """Send query and get response with sources"""
        pass
    
    @abstractmethod
    async def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Upload and embed a document"""
        pass
    
    @abstractmethod
    async def wait_for_embedding(self, doc_id: str, timeout: int = 300) -> bool:
        """Wait for document embedding to complete"""
        pass
    
    async def close(self):
        await self.client.aclose()


class AnythingLLMWrapper(RAGSystemWrapper):
    """Wrapper for AnythingLLM API"""
    
    def __init__(self, base_url: str, api_key: str, workspace_slug: str):
        super().__init__("AnythingLLM+LanceDB", base_url, api_key)
        self.workspace_slug = workspace_slug
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def query(self, question: str) -> RAGResponse:
        """Query AnythingLLM workspace"""
        start_time = time.time()
        
        url = f"{self.base_url}/api/v1/workspace/{self.workspace_slug}/chat"
        payload = {
            "message": question,
            "mode": "query"  # RAG mode
        }
        
        response = await self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract sources from response
        sources = data.get("sources", []) or data.get("documents", []) or []
        
        return RAGResponse(
            system=self.name,
            query=question,
            answer=data.get("textResponse", "") or data.get("response", ""),
            retrieved_docs=[s.get("title", s.get("name", "unknown")) for s in sources],
            retrieved_texts=[s.get("text", s.get("content", "")) for s in sources],
            latency_ms=latency_ms,
            metadata={"raw_response": data}
        )
    
    async def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Upload document to AnythingLLM"""
        # Step 1: Upload file
        upload_url = f"{self.base_url}/api/v1/document/upload"
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.client.post(upload_url, headers=headers, files=files)
            response.raise_for_status()
            upload_data = response.json()
        
        # Get the document location
        doc_location = upload_data.get("location") or upload_data.get("documents", [{}])[0].get("location")
        
        if not doc_location:
            raise ValueError(f"Could not get document location from upload response: {upload_data}")
        
        # Step 2: Add to workspace and embed
        embed_url = f"{self.base_url}/api/v1/workspace/{self.workspace_slug}/update-embeddings"
        embed_payload = {
            "adds": [doc_location],
            "deletes": []
        }
        
        response = await self.client.post(embed_url, headers=self.headers, json=embed_payload)
        response.raise_for_status()
        
        return {"location": doc_location, "status": "embedding"}
    
    async def wait_for_embedding(self, doc_id: str, timeout: int = 300) -> bool:
        """Wait for AnythingLLM to finish embedding"""
        # AnythingLLM doesn't have a direct status endpoint
        # We poll the workspace documents until the doc appears
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            url = f"{self.base_url}/api/v1/workspace/{self.workspace_slug}"
            response = await self.client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("workspace", {}).get("documents", [])
                
                # Check if our document is in the list and embedded
                for doc in docs:
                    if doc_id in doc.get("docpath", ""):
                        return True
            
            await asyncio.sleep(2)
        
        return False


class PrivateAIChatspaceWrapper(RAGSystemWrapper):
    """Wrapper for our Private AI Chatspace API"""
    
    def __init__(self, base_url: str, workspace_id: str, email: str = None, password: str = None, api_key: str = None):
        super().__init__("PrivateAI+Qdrant", base_url, api_key or "")
        self.workspace_id = workspace_id
        self.email = email
        self.password = password
        self._token: Optional[str] = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        self.chat_id: Optional[str] = None
    
    async def _ensure_auth(self):
        """Login and get token if not already authenticated"""
        if self._token:
            self.headers["Authorization"] = f"Bearer {self._token}"
            return
        
        if self.email and self.password:
            url = f"{self.base_url}/api/auth/login"
            payload = {"email": self.email, "password": self.password}
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self.headers["Authorization"] = f"Bearer {self._token}"
    
    async def _ensure_chat(self) -> str:
        """Create or get a chat for testing"""
        await self._ensure_auth()
        
        if self.chat_id:
            return self.chat_id
        
        # Create a new chat for evaluation
        url = f"{self.base_url}/api/chats"
        payload = {
            "workspace_id": self.workspace_id,
            "title": "RAG Evaluation Test"
        }
        
        response = await self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        self.chat_id = data["id"]
        return self.chat_id
    
    async def query(self, question: str) -> RAGResponse:
        """Query Private AI Chatspace with RAG enabled"""
        import json as json_lib
        
        start_time = time.time()
        
        chat_id = await self._ensure_chat()
        url = f"{self.base_url}/api/chats/{chat_id}/messages"
        
        payload = {
            "content": question,
            "use_rag": True
        }
        
        # The endpoint returns Server-Sent Events (streaming)
        async with self.client.stream("POST", url, headers=self.headers, json=payload) as response:
            response.raise_for_status()
            
            full_content = ""
            rag_sources = []
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json_lib.loads(line[6:])
                        
                        # Accumulate content
                        if "content" in data:
                            full_content += data["content"]
                        
                        # Capture sources (sent as 'sources' not 'rag_sources')
                        if "sources" in data:
                            rag_sources = data["sources"]
                        
                        # Stop when done
                        if data.get("done"):
                            break
                    except json_lib.JSONDecodeError:
                        continue
        
        latency_ms = (time.time() - start_time) * 1000
        
        return RAGResponse(
            system=self.name,
            query=question,
            answer=full_content,
            retrieved_docs=[s.get("filename", s.get("document_name", "unknown")) for s in rag_sources],
            retrieved_texts=[s.get("content", "") for s in rag_sources],
            latency_ms=latency_ms,
            metadata={
                "rag_sources": rag_sources
            }
        )
    
    async def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Upload document to Private AI Chatspace"""
        await self._ensure_auth()
        
        # Endpoint is /api/documents/workspace/{workspace_id}/upload
        url = f"{self.base_url}/api/documents/workspace/{self.workspace_id}/upload"
        
        with open(file_path, "rb") as f:
            filename = file_path.split("/")[-1]
            files = {"file": (filename, f, "application/octet-stream")}
            headers = {"Authorization": f"Bearer {self._token}"}
            
            response = await self.client.post(url, headers=headers, files=files)
            response.raise_for_status()
            return response.json()
    
    async def wait_for_embedding(self, doc_id: str, timeout: int = 300) -> bool:
        """Wait for document embedding to complete"""
        # Our system embeds synchronously during upload
        # But we can verify by checking document status
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            url = f"{self.base_url}/api/documents/{doc_id}"
            response = await self.client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("indexed", False) or data.get("status") == "indexed":
                    return True
            
            await asyncio.sleep(2)
        
        return False


async def create_wrappers(config: Dict) -> tuple[AnythingLLMWrapper, PrivateAIChatspaceWrapper]:
    """Create both RAG system wrappers from config"""
    
    anythingllm = AnythingLLMWrapper(
        base_url=config["anythingllm"]["base_url"],
        api_key=config["anythingllm"]["api_key"],
        workspace_slug=config["anythingllm"]["workspace_slug"]
    )
    
    privateai = PrivateAIChatspaceWrapper(
        base_url=config["privateai"]["base_url"],
        api_key=config["privateai"]["api_key"],
        workspace_id=config["privateai"]["workspace_id"]
    )
    
    return anythingllm, privateai
