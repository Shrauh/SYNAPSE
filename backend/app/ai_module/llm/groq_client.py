"""
SYNAPSE Groq Client — Primary LLM Provider.

Groq provides ultra-fast inference on Llama 3.1 70B for FREE
(14,400 requests/day on the free tier). This is the primary
LLM used by SYNAPSE for RCA explanation generation.

Usage:
    from app.ai_module.llm.groq_client import groq_client
    response = await groq_client.complete(messages=[...])

Reference:
    https://console.groq.com/docs/quickstart
    Model: llama-3.1-70b-versatile
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Async wrapper around the Groq Python SDK.

    The Groq SDK is synchronous; we run it in a thread pool to
    remain non-blocking inside the FastAPI async event loop.

    Rate limits (free tier):
        - 14,400 requests/day
        - 6,000 tokens/minute
        - 30 requests/minute
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or settings.groq_api_key
        self._model = model or settings.groq_model
        self._client = None
        self._available = False

    def _get_client(self):
        """Lazy-init the Groq client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "GROQ_API_KEY is not set. "
                    "Get a free key at https://console.groq.com"
                )
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key)
                self._available = True
            except ImportError:
                raise ImportError(
                    "groq package not installed. Run: pip install groq"
                )
        return self._client

    def _sync_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Synchronous Groq API call (runs in thread pool)."""
        client = self._get_client()

        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1200,
        json_mode: bool = True,
    ) -> str:
        """Async Groq completion — non-blocking.

        Args:
            messages: OpenAI-style message list [{"role": ..., "content": ...}].
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens in response.
            json_mode: If True, forces JSON output (recommended for RCA).

        Returns:
            Response text string (JSON if json_mode=True).

        Raises:
            Exception: On API errors (caller should handle and fall back).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_complete,
            messages,
            temperature,
            max_tokens,
            json_mode,
        )

    async def complete_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        """Convenience wrapper: returns parsed JSON dict.

        Args:
            system: System prompt (defines the assistant's role).
            user: User prompt (the actual RCA request).
            temperature: Sampling temperature.
            max_tokens: Token limit.

        Returns:
            Parsed JSON dictionary from the model response.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"[Groq] Failed to parse JSON response: {e}. Raw: {raw[:200]}")
            # Extract JSON from response if wrapped in text
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    @property
    def is_available(self) -> bool:
        """Check if Groq is configured and available."""
        return bool(self._api_key)

    @property
    def model(self) -> str:
        """Current model name."""
        return self._model


# Module-level singleton
groq_client = GroqClient()
