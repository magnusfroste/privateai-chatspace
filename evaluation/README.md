# RAG A/B Testing Framework

Automated comparison between:
- **AnythingLLM + LanceDB** 
- **Private AI Chatspace + Qdrant**

Both systems share the same external services:
- **LLM**: Qwen3-80B via vLLM (http://localhost:8001)
- **Embedder**: Qwen 4B via vLLM (http://localhost:8002)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED INFRASTRUCTURE                         │
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │  Qwen3-80B (vLLM)   │    │  Qwen 4B Embedder   │             │
│  │  GPU 1 - RTX 5090   │    │  GPU 2 - RTX 5090   │             │
│  │  :8001              │    │  :8002              │             │
│  └─────────────────────┘    └─────────────────────┘             │
│            │                          │                          │
│            └──────────┬───────────────┘                          │
│                       │                                          │
│         ┌─────────────┴─────────────┐                           │
│         │                           │                            │
│         ▼                           ▼                            │
│  ┌─────────────────┐    ┌─────────────────────────┐             │
│  │  AnythingLLM    │    │  Private AI Chatspace   │             │
│  │  + LanceDB      │    │  + Qdrant               │             │
│  │  :3001          │    │  :8000                  │             │
│  └─────────────────┘    └─────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Configure endpoints
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and endpoints

# 2. Prepare test documents
python prepare_test_data.py

# 3. Upload documents to both systems
python upload_documents.py

# 4. Run evaluation
python run_evaluation.py

# 5. View results
python generate_report.py
```

## Test Dataset

Place test documents in `test_data/documents/`:
- PDFs, markdown, text files
- Same documents will be uploaded to both systems

Queries are defined in `test_data/queries.json`

## Metrics Measured

### Retrieval Quality
- Precision@K, Recall@K
- Mean Reciprocal Rank (MRR)
- Contextual Relevancy (LLM-judged)

### Answer Quality
- Faithfulness (no hallucinations)
- Answer Relevancy
- Completeness

### System Performance
- Latency (retrieval + generation)
- Token usage
