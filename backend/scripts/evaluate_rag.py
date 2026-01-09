#!/usr/bin/env python3
"""
RAG vs CAG Evaluation Script

Compares response quality between:
- RAG: Retrieves chunks from Qdrant, LLM answers with context
- CAG: Full document sent as context to LLM

Usage:
    python scripts/evaluate_rag.py --workspace-id 1 --question "Summera färdplanen för Sverige"
"""

import asyncio
import argparse
import json
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.document_service import document_service


async def evaluate_rag(workspace_id: int, question: str, top_n: int = 5):
    """Evaluate RAG response"""
    print(f"\n{'='*60}")
    print("📚 RAG MODE (Retrieval Augmented Generation)")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Search Qdrant
    rag_results = await rag_service.search(
        workspace_id=workspace_id,
        query=question,
        limit=top_n,
        hybrid=True
    )
    
    search_time = time.time() - start_time
    
    if not rag_results:
        print("❌ No RAG results found")
        return None
    
    print(f"\n🔍 Found {len(rag_results)} chunks in {search_time:.2f}s")
    
    # Show retrieved chunks
    for i, r in enumerate(rag_results, 1):
        print(f"\n--- Chunk {i} (score: {r.get('score', 0):.4f}) ---")
        print(f"Type: {r.get('content_type', 'text')}")
        if r.get('section_title'):
            print(f"Section: {r.get('section_title')}")
        print(f"Words: {r.get('word_count', 0)}")
        print(f"Preview: {r.get('content', '')[:200]}...")
    
    # Build context
    context_parts = []
    for i, r in enumerate(rag_results, 1):
        context_parts.append(f"[{i}] {r['content']}")
    rag_context = "\n\n---\n\n".join(context_parts)
    
    # Generate response
    print(f"\n🤖 Generating LLM response...")
    gen_start = time.time()
    
    response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": question}],
        rag_context=rag_context
    ):
        response += chunk
    
    gen_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    print(f"\n📝 RAG Response ({gen_time:.2f}s generation, {total_time:.2f}s total):")
    print("-" * 40)
    print(response)
    
    return {
        "mode": "RAG",
        "chunks_retrieved": len(rag_results),
        "search_time": search_time,
        "generation_time": gen_time,
        "total_time": total_time,
        "response": response,
        "response_length": len(response),
        "context_length": len(rag_context)
    }


async def evaluate_cag(document_path: str, question: str):
    """Evaluate CAG response (full document as context)"""
    print(f"\n{'='*60}")
    print("📄 CAG MODE (Context Augmented Generation)")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Read full document
    if document_path.endswith('.md'):
        content = await document_service.read_markdown(document_path)
    else:
        print(f"❌ Unsupported file type: {document_path}")
        return None
    
    read_time = time.time() - start_time
    
    print(f"\n📖 Document loaded in {read_time:.2f}s")
    print(f"   Length: {len(content)} chars, ~{len(content.split())} words")
    
    # Generate response with full document as context
    print(f"\n🤖 Generating LLM response...")
    gen_start = time.time()
    
    response = ""
    async for chunk in llm_service.chat_completion_stream(
        messages=[{"role": "user", "content": question}],
        file_content=f"[DOCUMENT CONTENT]:\n{content}\n[END DOCUMENT]"
    ):
        response += chunk
    
    gen_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    print(f"\n📝 CAG Response ({gen_time:.2f}s generation, {total_time:.2f}s total):")
    print("-" * 40)
    print(response)
    
    return {
        "mode": "CAG",
        "document_chars": len(content),
        "document_words": len(content.split()),
        "read_time": read_time,
        "generation_time": gen_time,
        "total_time": total_time,
        "response": response,
        "response_length": len(response),
        "context_length": len(content)
    }


async def compare_responses(rag_result: dict, cag_result: dict, question: str):
    """Use LLM to compare and evaluate both responses"""
    print(f"\n{'='*60}")
    print("⚖️  LLM EVALUATION")
    print(f"{'='*60}")
    
    eval_prompt = f"""Du är en expert på att utvärdera AI-svar. Jämför dessa två svar på frågan:

FRÅGA: {question}

--- RAG-SVAR (hämtade relevanta delar från dokument) ---
{rag_result['response']}

--- CAG-SVAR (hela dokumentet som kontext) ---
{cag_result['response']}

Utvärdera på en skala 1-10 för varje svar:
1. **Relevans**: Hur väl besvarar svaret frågan?
2. **Fullständighet**: Täcker svaret alla viktiga aspekter?
3. **Precision**: Är informationen korrekt och specifik?
4. **Läsbarhet**: Är svaret välstrukturerat och lätt att förstå?

Ge sedan en sammanfattande bedömning: Vilket svar är bäst och varför?

Svara i JSON-format:
{{
    "rag_scores": {{"relevans": X, "fullständighet": X, "precision": X, "läsbarhet": X, "total": X}},
    "cag_scores": {{"relevans": X, "fullständighet": X, "precision": X, "läsbarhet": X, "total": X}},
    "winner": "RAG" eller "CAG" eller "TIE",
    "reasoning": "Förklaring..."
}}"""

    response = await llm_service.generate(eval_prompt, temperature=0.3, max_tokens=1000)
    
    print("\n📊 Evaluation Result:")
    print("-" * 40)
    print(response)
    
    # Try to parse JSON
    try:
        # Find JSON in response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            eval_json = json.loads(response[json_start:json_end])
            return eval_json
    except:
        pass
    
    return {"raw_response": response}


async def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG vs CAG")
    parser.add_argument("--workspace-id", type=int, default=1, help="Workspace ID for RAG")
    parser.add_argument("--document", type=str, help="Path to markdown document for CAG")
    parser.add_argument("--question", type=str, required=True, help="Question to ask")
    parser.add_argument("--top-n", type=int, default=5, help="Number of RAG chunks")
    parser.add_argument("--compare", action="store_true", help="Use LLM to compare responses")
    
    args = parser.parse_args()
    
    print(f"\n🎯 Question: {args.question}")
    print(f"📁 Workspace ID: {args.workspace_id}")
    
    results = {}
    
    # Run RAG evaluation
    rag_result = await evaluate_rag(args.workspace_id, args.question, args.top_n)
    if rag_result:
        results["rag"] = rag_result
    
    # Run CAG evaluation if document provided
    if args.document:
        cag_result = await evaluate_cag(args.document, args.question)
        if cag_result:
            results["cag"] = cag_result
    
    # Compare if both available
    if args.compare and "rag" in results and "cag" in results:
        eval_result = await compare_responses(results["rag"], results["cag"], args.question)
        results["evaluation"] = eval_result
    
    # Summary
    print(f"\n{'='*60}")
    print("📈 SUMMARY")
    print(f"{'='*60}")
    
    if "rag" in results:
        r = results["rag"]
        print(f"\nRAG: {r['chunks_retrieved']} chunks, {r['total_time']:.2f}s, {r['response_length']} chars")
    
    if "cag" in results:
        c = results["cag"]
        print(f"CAG: {c['document_words']} words context, {c['total_time']:.2f}s, {c['response_length']} chars")
    
    if "evaluation" in results and "winner" in results["evaluation"]:
        print(f"\n🏆 Winner: {results['evaluation']['winner']}")
        print(f"   Reason: {results['evaluation'].get('reasoning', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
