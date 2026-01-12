"""
RAG Evaluation Metrics

Metrics for comparing retrieval and answer quality between RAG systems.
Uses LLM-as-Judge for answer quality assessment.
"""

import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics"""
    precision_at_3: float
    precision_at_5: float
    recall_at_5: float
    mrr: float  # Mean Reciprocal Rank


@dataclass
class AnswerMetrics:
    """Answer quality metrics (LLM-judged)"""
    relevancy: float  # 1-5
    faithfulness: float  # 1-5
    completeness: float  # 1-5
    reasoning: str


@dataclass
class ContextualMetrics:
    """Contextual quality metrics (LLM-judged)"""
    context_relevancy: float  # 0-1
    context_recall: float  # 0-1


def precision_at_k(retrieved: List[str], ground_truth: List[str], k: int) -> float:
    """What fraction of top-k retrieved docs are relevant?"""
    if k == 0:
        return 0.0
    retrieved_k = retrieved[:k]
    relevant = set(ground_truth)
    hits = sum(1 for doc in retrieved_k if doc in relevant)
    return hits / k


def recall_at_k(retrieved: List[str], ground_truth: List[str], k: int) -> float:
    """What fraction of relevant docs were retrieved in top-k?"""
    if not ground_truth:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant = set(ground_truth)
    hits = len(retrieved_k & relevant)
    return hits / len(relevant)


def mrr(retrieved: List[str], ground_truth: List[str]) -> float:
    """Mean Reciprocal Rank - position of first relevant doc"""
    relevant = set(ground_truth)
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def calculate_retrieval_metrics(
    retrieved_docs: List[str],
    ground_truth_docs: List[str]
) -> RetrievalMetrics:
    """Calculate all retrieval metrics"""
    return RetrievalMetrics(
        precision_at_3=precision_at_k(retrieved_docs, ground_truth_docs, 3),
        precision_at_5=precision_at_k(retrieved_docs, ground_truth_docs, 5),
        recall_at_5=recall_at_k(retrieved_docs, ground_truth_docs, 5),
        mrr=mrr(retrieved_docs, ground_truth_docs)
    )


class LLMJudge:
    """LLM-as-Judge for answer quality assessment"""
    
    def __init__(self, llm_base_url: str, model: str, temperature: float = 0.1, api_key: str = None):
        self.llm_base_url = llm_base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def _generate(self, prompt: str) -> str:
        """Call LLM to generate response"""
        url = f"{self.llm_base_url}/chat/completions"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 1000
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def judge_answer(
        self,
        query: str,
        answer: str,
        context: List[str],
        ground_truth: Optional[str] = None
    ) -> AnswerMetrics:
        """Judge answer quality using LLM"""
        
        context_text = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(context))
        gt_section = f"\nGround Truth Answer: {ground_truth}" if ground_truth else ""
        
        prompt = f"""You are evaluating a RAG system's answer quality.

Query: {query}

Retrieved Context:
{context_text}

Generated Answer: {answer}
{gt_section}

Rate the following on a scale of 1-5:

1. **Relevancy**: Does the answer address the query? (1=completely off-topic, 5=perfectly addresses the query)
2. **Faithfulness**: Is the answer supported by the context without hallucinations? (1=many hallucinations, 5=fully grounded in context)
3. **Completeness**: Does the answer cover all aspects of the query? (1=very incomplete, 5=comprehensive)

Respond ONLY with valid JSON in this exact format:
{{"relevancy": X, "faithfulness": X, "completeness": X, "reasoning": "brief explanation"}}
"""
        
        response = await self._generate(prompt)
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                data = json.loads(response)
            
            return AnswerMetrics(
                relevancy=float(data.get("relevancy", 3)),
                faithfulness=float(data.get("faithfulness", 3)),
                completeness=float(data.get("completeness", 3)),
                reasoning=data.get("reasoning", "")
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback if parsing fails
            return AnswerMetrics(
                relevancy=3.0,
                faithfulness=3.0,
                completeness=3.0,
                reasoning=f"Parse error: {e}"
            )
    
    async def judge_context_relevancy(
        self,
        query: str,
        contexts: List[str]
    ) -> float:
        """Judge if retrieved contexts are relevant to query"""
        
        context_text = "\n\n".join(f"[{i+1}] {c[:500]}..." for i, c in enumerate(contexts))
        
        prompt = f"""Query: {query}

Retrieved Documents:
{context_text}

For each document, rate its relevance to answering the query on a scale of 0.0 to 1.0.
Then provide the average relevance score.

Respond ONLY with valid JSON:
{{"scores": [0.8, 0.9, 0.3], "average": 0.67}}
"""
        
        response = await self._generate(prompt)
        
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                data = json.loads(response)
            return float(data.get("average", 0.5))
        except (json.JSONDecodeError, KeyError):
            return 0.5
    
    async def judge_context_recall(
        self,
        query: str,
        contexts: List[str],
        ground_truth: str
    ) -> float:
        """Judge if context contains all info needed for ground truth answer"""
        
        context_text = "\n\n".join(contexts)
        
        prompt = f"""Query: {query}
Ground Truth Answer: {ground_truth}

Retrieved Context:
{context_text}

Does the retrieved context contain ALL the information needed to produce the ground truth answer?
Score from 0.0 (missing critical info) to 1.0 (all info present).

Respond ONLY with valid JSON:
{{"score": 0.85, "missing_info": "description of any missing information"}}
"""
        
        response = await self._generate(prompt)
        
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                data = json.loads(response)
            return float(data.get("score", 0.5))
        except (json.JSONDecodeError, KeyError):
            return 0.5
    
    async def close(self):
        await self.client.aclose()
