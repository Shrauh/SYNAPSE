"""
SYNAPSE LLM Reasoner — Generates Human-Readable RCA Explanations.

Provider chain (in priority order):
  1. Groq (FREE — llama-3.1-70b-versatile, 14,400 req/day)
  2. OpenAI (GPT-4o-mini, paid fallback)
  3. Mock template (deterministic, no API needed)

Converts GNN anomaly scores + causal DAG into structured RCA reports.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.ai_module.llm.cache import RCACache
from app.ai_module.llm.prompt_templates import (
    SYSTEM_PROMPT,
    build_mock_response,
    build_rca_prompt,
)
from app.config import settings

logger = logging.getLogger(__name__)


class LLMReasoner:
    """Generates RCA explanations using LLM or mock templates.

    Always tries Groq first (free), then OpenAI, then mock.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.groq_api_key = settings.groq_api_key
        self.openai_api_key = api_key or settings.openai_api_key
        self.openai_model = model or settings.openai_model
        self.cache = RCACache()
        self._openai_client = None

    def _get_openai_client(self):
        """Lazy-init OpenAI client."""
        if self._openai_client is None:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._openai_client

    def _determine_provider(self) -> str:
        """Determine which LLM provider to use based on available keys."""
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "mock"

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
            Dict with root_cause, confidence, explanation, recommended_actions, etc.
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
            )
            if cached is not None:
                cached["_cached"] = True
                return cached

        start_time = time.time()
        provider = self._determine_provider()
        result = None

        # 1. Try Groq (primary)
        if provider == "groq":
            try:
                result = await self._call_groq(
                    root_candidates=root_candidates,
                    anomaly_scores=anomaly_scores,
                    causal_edges=causal_edges,
                    metric_deltas=metric_deltas,
                    dependency_edges=dependency_edges,
                )
                logger.info("[LLM] Used Groq (llama-3.1-70b-versatile)")
            except Exception as e:
                logger.warning(f"[LLM] Groq failed: {e}. Trying OpenAI...")
                provider = "openai" if self.openai_api_key else "mock"

        # 2. Try OpenAI (fallback)
        if result is None and provider == "openai":
            try:
                result = await self._call_openai(
                    root_candidates=root_candidates,
                    anomaly_scores=anomaly_scores,
                    causal_edges=causal_edges,
                    metric_deltas=metric_deltas,
                    dependency_edges=dependency_edges,
                )
                logger.info("[LLM] Used OpenAI (gpt-4o-mini)")
            except Exception as e:
                logger.warning(f"[LLM] OpenAI failed: {e}. Falling back to mock.")
                provider = "mock"

        # 3. Mock template (last resort — always works)
        if result is None:
            result = build_mock_response(
                root_candidates=root_candidates,
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                metric_deltas=metric_deltas,
            )
            logger.info("[LLM] Used mock template (no API keys configured)")

        elapsed_ms = (time.time() - start_time) * 1000
        result["_inference_time_ms"] = round(elapsed_ms, 1)
        result["_provider"] = provider
        result["_cached"] = False

        # Update cache
        if use_cache:
            self.cache.put(
                anomaly_scores=anomaly_scores,
                causal_edges=causal_edges,
                response=result,
            )

        return result

    async def _call_groq(
        self,
        root_candidates: List[Tuple[str, float]],
        anomaly_scores: Dict[str, float],
        causal_edges: List[Tuple[str, str, float]],
        metric_deltas: Dict[str, Dict[str, str]],
        dependency_edges: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Call Groq API with JSON mode."""
        from app.ai_module.llm.groq_client import groq_client

        user_prompt = build_rca_prompt(
            anomaly_scores=anomaly_scores,
            causal_edges=causal_edges,
            root_candidates=root_candidates,
            metric_deltas=metric_deltas,
            dependency_edges=dependency_edges,
        )

        result = await groq_client.complete_json(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
            max_tokens=1200,
        )

        # Validate required fields
        for field, default in [
            ("root_cause", root_candidates[0][0] if root_candidates else "unknown"),
            ("confidence", 0.7),
            ("explanation", "Analysis complete."),
        ]:
            if field not in result:
                result[field] = default

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

        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_call():
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000,
            )
            return json.loads(response.choices[0].message.content)

        result = await loop.run_in_executor(None, _sync_call)

        # Validate required fields
        required = ["root_cause", "confidence", "explanation"]
        for field in required:
            if field not in result:
                result[field] = "unknown" if field != "confidence" else 0.0

        return result


# Module-level singleton
llm_reasoner = LLMReasoner()
