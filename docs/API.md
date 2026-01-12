# Private AI Chatspace - Simple API v1

Developer-friendly API for integrations. Designed to be as simple as AnythingLLM.

## Quick Start

```bash
# 1. Get an API key from Admin → Settings → API Keys
# 2. Query your workspace
curl -X POST "https://your-instance.com/api/v1/workspace/1/query" \
  -H "Authorization: Bearer pk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the torque specification?"}'
```

## Authentication

Two options:

### Option 1: API Key (Recommended for integrations)

```bash
Authorization: Bearer pk_xxxxxxxxxxxxx
```

Generate API keys in **Admin → Settings → API Keys**.

### Option 2: JWT Token (For web apps)

```bash
# Login
curl -X POST "https://your-instance.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use the token
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Endpoints

### Health Check

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0",
  "api": "Private AI Chatspace Simple API"
}
```

---

### List Workspaces

```http
GET /api/v1/workspaces
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Technical Docs",
    "document_count": 15,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### Query Workspace (RAG)

```http
POST /api/v1/workspace/{workspace_id}/query
Authorization: Bearer {token}
Content-Type: application/json
```

**Request:**
```json
{
  "message": "What is the torque specification for MJP impeller bolts?",
  "mode": "query",
  "top_k": 5,
  "include_sources": true
}
```

**Parameters:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | string | required | The question to ask |
| `mode` | string | `"query"` | `"query"` (RAG) or `"chat"` (no RAG) |
| `top_k` | int | 5 | Number of documents to retrieve |
| `include_sources` | bool | true | Include source documents in response |

**Response:**
```json
{
  "response": "The torque specification for MJP impeller bolts is 45 Nm according to the service manual [1].",
  "sources": [
    {
      "filename": "MJP-5996-SM-A1.pdf",
      "content": "Impeller bolt torque: 45 Nm (33 ft-lb)...",
      "score": 0.95,
      "document_id": 42
    }
  ],
  "latency_ms": 1234.5,
  "mode": "query"
}
```

---

### Upload Document

```http
POST /api/v1/workspace/{workspace_id}/upload?auto_embed=true
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Parameters:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | file | required | The document to upload |
| `auto_embed` | bool | true | Automatically embed after upload |

**Response:**
```json
{
  "id": 42,
  "filename": "manual.pdf",
  "status": "embedded",
  "chunks": 156
}
```

**Supported formats:** PDF, DOCX, TXT, MD

---

### List Documents

```http
GET /api/v1/workspace/{workspace_id}/documents
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 42,
    "filename": "manual.pdf",
    "file_type": "pdf",
    "indexed": true,
    "indexed_at": "2024-01-15T10:35:00Z",
    "uploaded_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### Delete Document

```http
DELETE /api/v1/workspace/{workspace_id}/documents/{document_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "deleted": true,
  "document_id": 42
}
```

---

## Comparison: Private AI vs AnythingLLM

| Feature | Private AI | AnythingLLM |
|---------|------------|-------------|
| Query endpoint | `POST /api/v1/workspace/{id}/query` | `POST /api/v1/workspace/{slug}/chat` |
| Auth | API Key (`pk_xxx`) or JWT | API Key |
| Response format | JSON with sources | JSON with sources |
| Streaming | Optional (use `/api/chats/{id}/messages`) | Optional |
| Upload + embed | Single request with `auto_embed=true` | Two requests |

---

## Python Example

```python
import httpx

class PrivateAIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def query(self, workspace_id: int, message: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workspace/{workspace_id}/query",
                headers=self.headers,
                json={"message": message, "mode": "query"}
            )
            return response.json()

# Usage
client = PrivateAIClient("https://your-instance.com", "pk_your_api_key")
result = await client.query(1, "What is the torque spec?")
print(result["response"])
```

---

## JavaScript Example

```javascript
const privateAI = {
  baseUrl: 'https://your-instance.com',
  apiKey: 'pk_your_api_key',
  
  async query(workspaceId, message) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/workspace/${workspaceId}/query`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message, mode: 'query' })
      }
    );
    return response.json();
  }
};

// Usage
const result = await privateAI.query(1, 'What is the torque spec?');
console.log(result.response);
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 401 | Invalid or missing API key/token |
| 403 | Access denied to workspace |
| 404 | Workspace or document not found |
| 500 | Internal server error |

---

## Rate Limits

No rate limits by default. Configure in your deployment if needed.

---

## OpenAPI/Swagger

Interactive API docs available at:
- Swagger UI: `https://your-instance.com/docs`
- ReDoc: `https://your-instance.com/redoc`
