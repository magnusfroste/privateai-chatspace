#!/usr/bin/env python3
"""
RAG A/B Testing Evaluation Runner

Runs the same queries against both AnythingLLM and Private AI Chatspace,
collects metrics, and generates a comparison report.
"""

import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import asdict

from rag_wrappers import (
    AnythingLLMWrapper,
    PrivateAIChatspaceWrapper,
    RAGResponse
)
from metrics import (
    LLMJudge,
    calculate_retrieval_metrics,
    RetrievalMetrics,
    AnswerMetrics
)


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_test_queries(queries_path: str = "test_data/queries.json") -> List[Dict]:
    """Load test queries with ground truth"""
    with open(queries_path) as f:
        return json.load(f)


async def evaluate_single_query(
    query_data: Dict,
    anythingllm: AnythingLLMWrapper,
    privateai: PrivateAIChatspaceWrapper,
    judge: LLMJudge
) -> Dict[str, Any]:
    """Evaluate a single query against both systems"""
    
    query = query_data["query"]
    gt_answer = query_data.get("ground_truth_answer")
    gt_docs = query_data.get("ground_truth_docs", [])
    
    print(f"  Query: {query[:60]}...")
    
    # Query both systems
    try:
        anythingllm_response = await anythingllm.query(query)
    except Exception as e:
        print(f"    AnythingLLM error: {e}")
        anythingllm_response = RAGResponse(
            system="AnythingLLM+LanceDB",
            query=query,
            answer=f"ERROR: {e}",
            retrieved_docs=[],
            retrieved_texts=[],
            latency_ms=0,
            metadata={"error": str(e)}
        )
    
    try:
        privateai_response = await privateai.query(query)
    except Exception as e:
        print(f"    PrivateAI error: {e}")
        privateai_response = RAGResponse(
            system="PrivateAI+Qdrant",
            query=query,
            answer=f"ERROR: {e}",
            retrieved_docs=[],
            retrieved_texts=[],
            latency_ms=0,
            metadata={"error": str(e)}
        )
    
    # Calculate retrieval metrics
    anythingllm_retrieval = calculate_retrieval_metrics(
        anythingllm_response.retrieved_docs, gt_docs
    )
    privateai_retrieval = calculate_retrieval_metrics(
        privateai_response.retrieved_docs, gt_docs
    )
    
    # LLM-judge answer quality
    anythingllm_answer_metrics = await judge.judge_answer(
        query,
        anythingllm_response.answer,
        anythingllm_response.retrieved_texts,
        gt_answer
    )
    privateai_answer_metrics = await judge.judge_answer(
        query,
        privateai_response.answer,
        privateai_response.retrieved_texts,
        gt_answer
    )
    
    # Context relevancy
    anythingllm_ctx_rel = await judge.judge_context_relevancy(
        query, anythingllm_response.retrieved_texts
    ) if anythingllm_response.retrieved_texts else 0.0
    
    privateai_ctx_rel = await judge.judge_context_relevancy(
        query, privateai_response.retrieved_texts
    ) if privateai_response.retrieved_texts else 0.0
    
    # Context recall (if ground truth available)
    anythingllm_ctx_recall = 0.0
    privateai_ctx_recall = 0.0
    if gt_answer:
        anythingllm_ctx_recall = await judge.judge_context_recall(
            query, anythingllm_response.retrieved_texts, gt_answer
        ) if anythingllm_response.retrieved_texts else 0.0
        
        privateai_ctx_recall = await judge.judge_context_recall(
            query, privateai_response.retrieved_texts, gt_answer
        ) if privateai_response.retrieved_texts else 0.0
    
    return {
        "test_id": query_data.get("id", "unknown"),
        "category": query_data.get("category", "general"),
        "query": query,
        "ground_truth_answer": gt_answer,
        "ground_truth_docs": gt_docs,
        "anythingllm": {
            "answer": anythingllm_response.answer,
            "retrieved_docs": anythingllm_response.retrieved_docs,
            "latency_ms": anythingllm_response.latency_ms,
            "retrieval": asdict(anythingllm_retrieval),
            "answer_quality": asdict(anythingllm_answer_metrics),
            "context_relevancy": anythingllm_ctx_rel,
            "context_recall": anythingllm_ctx_recall,
        },
        "privateai": {
            "answer": privateai_response.answer,
            "retrieved_docs": privateai_response.retrieved_docs,
            "latency_ms": privateai_response.latency_ms,
            "retrieval": asdict(privateai_retrieval),
            "answer_quality": asdict(privateai_answer_metrics),
            "context_relevancy": privateai_ctx_rel,
            "context_recall": privateai_ctx_recall,
        }
    }


async def run_evaluation(config: Dict, queries: List[Dict]) -> List[Dict]:
    """Run full evaluation across all queries"""
    
    # Create wrappers
    anythingllm = AnythingLLMWrapper(
        base_url=config["anythingllm"]["base_url"],
        api_key=config["anythingllm"]["api_key"],
        workspace_slug=config["anythingllm"]["workspace_slug"]
    )
    
    privateai = PrivateAIChatspaceWrapper(
        base_url=config["privateai"]["base_url"],
        workspace_id=config["privateai"]["workspace_id"],
        email=config["privateai"].get("email"),
        password=config["privateai"].get("password"),
        api_key=config["privateai"].get("api_key")
    )
    
    # Create LLM judge (using shared LLM)
    judge = LLMJudge(
        llm_base_url=config["shared"]["llm"]["base_url"],
        model=config["shared"]["llm"]["model"],
        temperature=config["evaluation"].get("judge_temperature", 0.1),
        api_key=config["shared"]["llm"].get("api_key")
    )
    
    results = []
    max_queries = config["evaluation"].get("max_queries", len(queries))
    
    print(f"\nRunning evaluation on {min(max_queries, len(queries))} queries...")
    print("=" * 60)
    
    for i, query_data in enumerate(queries[:max_queries]):
        print(f"\n[{i+1}/{min(max_queries, len(queries))}]")
        
        result = await evaluate_single_query(
            query_data, anythingllm, privateai, judge
        )
        results.append(result)
        
        # Print quick comparison
        a_faith = result["anythingllm"]["answer_quality"]["faithfulness"]
        p_faith = result["privateai"]["answer_quality"]["faithfulness"]
        a_lat = result["anythingllm"]["latency_ms"]
        p_lat = result["privateai"]["latency_ms"]
        
        print(f"    AnythingLLM: faith={a_faith:.1f}, latency={a_lat:.0f}ms")
        print(f"    PrivateAI:   faith={p_faith:.1f}, latency={p_lat:.0f}ms")
    
    # Cleanup
    await anythingllm.close()
    await privateai.close()
    await judge.close()
    
    return results


def save_results(results: List[Dict], output_dir: str):
    """Save evaluation results to JSON"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"evaluation_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {filename}")
    return filename


def print_summary(results: List[Dict]):
    """Print summary comparison"""
    
    # Aggregate metrics
    anythingllm_metrics = {
        "latency": [],
        "faithfulness": [],
        "relevancy": [],
        "precision_at_5": [],
        "recall_at_5": [],
        "mrr": [],
        "context_relevancy": [],
    }
    
    privateai_metrics = {
        "latency": [],
        "faithfulness": [],
        "relevancy": [],
        "precision_at_5": [],
        "recall_at_5": [],
        "mrr": [],
        "context_relevancy": [],
    }
    
    for r in results:
        a = r["anythingllm"]
        p = r["privateai"]
        
        anythingllm_metrics["latency"].append(a["latency_ms"])
        anythingllm_metrics["faithfulness"].append(a["answer_quality"]["faithfulness"])
        anythingllm_metrics["relevancy"].append(a["answer_quality"]["relevancy"])
        anythingllm_metrics["precision_at_5"].append(a["retrieval"]["precision_at_5"])
        anythingllm_metrics["recall_at_5"].append(a["retrieval"]["recall_at_5"])
        anythingllm_metrics["mrr"].append(a["retrieval"]["mrr"])
        anythingllm_metrics["context_relevancy"].append(a["context_relevancy"])
        
        privateai_metrics["latency"].append(p["latency_ms"])
        privateai_metrics["faithfulness"].append(p["answer_quality"]["faithfulness"])
        privateai_metrics["relevancy"].append(p["answer_quality"]["relevancy"])
        privateai_metrics["precision_at_5"].append(p["retrieval"]["precision_at_5"])
        privateai_metrics["recall_at_5"].append(p["retrieval"]["recall_at_5"])
        privateai_metrics["mrr"].append(p["retrieval"]["mrr"])
        privateai_metrics["context_relevancy"].append(p["context_relevancy"])
    
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0
    
    print("\n" + "=" * 70)
    print("RAG A/B TEST RESULTS")
    print("=" * 70)
    print(f"\nTotal queries evaluated: {len(results)}")
    print("\n" + "-" * 70)
    print(f"{'Metric':<25} {'AnythingLLM':<20} {'PrivateAI':<20} {'Winner'}")
    print("-" * 70)
    
    metrics_to_compare = [
        ("Latency (ms)", "latency", True),  # lower is better
        ("Faithfulness (1-5)", "faithfulness", False),
        ("Relevancy (1-5)", "relevancy", False),
        ("Precision@5", "precision_at_5", False),
        ("Recall@5", "recall_at_5", False),
        ("MRR", "mrr", False),
        ("Context Relevancy", "context_relevancy", False),
    ]
    
    for name, key, lower_is_better in metrics_to_compare:
        a_val = avg(anythingllm_metrics[key])
        p_val = avg(privateai_metrics[key])
        
        if lower_is_better:
            winner = "AnythingLLM" if a_val < p_val else "PrivateAI"
        else:
            winner = "AnythingLLM" if a_val > p_val else "PrivateAI"
        
        if abs(a_val - p_val) < 0.05:
            winner = "Tie"
        
        print(f"{name:<25} {a_val:<20.3f} {p_val:<20.3f} {winner}")
    
    print("-" * 70)


async def main():
    """Main entry point"""
    print("RAG A/B Testing Framework")
    print("=" * 60)
    
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("Copy config.example.yaml to config.yaml and fill in your values.")
        return
    
    config = load_config(str(config_path))
    
    # Load queries
    queries_path = Path(__file__).parent / "test_data" / "queries.json"
    if not queries_path.exists():
        print(f"ERROR: Queries file not found: {queries_path}")
        print("Create test_data/queries.json with your test queries.")
        return
    
    queries = load_test_queries(str(queries_path))
    print(f"Loaded {len(queries)} test queries")
    
    # Run evaluation
    results = await run_evaluation(config, queries)
    
    # Save results
    output_dir = config["evaluation"].get("results_dir", "./results")
    save_results(results, output_dir)
    
    # Print summary
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
