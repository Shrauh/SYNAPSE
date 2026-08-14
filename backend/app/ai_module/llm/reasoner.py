"""
SYNAPSE LLM Reasoner — Generates Human-Readable RCA Explanations.

Supports multiple providers:
- "mock" — deterministic template-based (no API cost, good for dev/demo)
- "openai" — OpenAI API with JSON mode

Converts GNN anomaly scores + causal DAG into structured RCA reports.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.ai_module.llm.cache import RCACache
from app.ai_module.llm.prompt_templates import (
    SYSTEM_PROMPT,
    build_mock_response,
    build_rca_prompt,
)
from app.config import settings


class LLMReasoner:
    """Generates RCA explanations using LLM or mock templates."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider or settings.llm_provider
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.cache = RCACache()
        self._client = None

    def _get_openai_client(self):
        """Lazy-init OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    async def explain(
        self,
        root_candidates: List[Tuple[str, float]],
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
        metric_deltas: Dict[str, Dict[str, str]],
        dependency_edges: Optional[List[Tuple[str, str]]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Generate an RCA explanation from analysis results.

        Args:
            root_candidates: [(service, score), ...] ranked root causes.
            anomaly_scores: {service: score} for all anomalous services.
            causal_edges: [(src, tgt, strength), ...] from causal discovery.
            metric_deltas: {service: {metric: "delta%"}} changes from baseline.
            dependency_edges: Service topology edges for context.
            use_cache: Whether to check/update the response cache.

        Returns:
            Dict with root_cause, confidence, explanation, etc.
        """
        # Check cache
        if use_cache:
            cached = self.cache.get(
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
            )
            if cached is not None:
                cached["_cached"] = True
                return cached

        start_time = time.time()

        if self.provider == "mock":
            result = build_mock_response(
                root_candidates=root_candidates,
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                metric_deltas=metric_deltas,
            )
        elif self.provider == "openai":
            result = await self._call_openai(
                root_candidates=root_candidates,
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                metric_deltas=metric_deltas,
                dependency_edges=dependency_edges,
            )
        else:
            # Unknown provider — use mock
            result = build_mock_response(
                root_candidates=root_candidates,
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                metric_deltas=metric_deltas,
            )

        elapsed_ms = (time.time() - start_time) * 1000
        result["_inference_time_ms"] = round(elapsed_ms, 1)
        result["_provider"] = self.provider
        result["_cached"] = False

        # Update cache
        if use_cache:
            self.cache.put(
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                response=result,
            )

        return result

    async def _call_openai(
        self,
        root_candidates: List[Tuple[str, float]],
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
        metric_deltas: Dict[str, Dict[str, str]],
        dependency_edges: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Call OpenAI API with structured JSON output."""
        user_prompt = build_rca_prompt(
            anomaly_scores=anomaly_scores,
            causal_edges=causal_edges,
            root_candidates=root_candidates,
            metric_deltas=metric_deltas,
            dependency_edges=dependency_edges,
        )

        try:
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Validate required fields
            required = ["root_cause", "confidence", "explanation"]
            for field in required:
                if field not in result:
                    result[field] = "unknown" if isinstance(field, str) else 0.0

            return result

        except Exception as e:
            # Fallback to mock on any error
            print(f"[LLM] OpenAI call failed: {e}. Falling back to mock.")
            return build_mock_response(
                root_candidates=root_candidates,
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                metric_deltas=metric_deltas,
            )


# Module-level singleton
llm_reasoner = LLMReasoner()
