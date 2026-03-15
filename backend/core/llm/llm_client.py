"""
Unified LLM client.

Policy:
- All application LLM calls are served only by Cerebras.
- No secondary LLM provider fallback is allowed.
- OCR/VLM adapters are handled in separate modules.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from backend.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

MAX_RETRIES = 2
RETRY_DELAY = 1.0

SYSTEM_PROMPT = (
    "You are a senior credit analyst at a leading Indian bank. "
    "Provide precise, structured financial analysis using Indian banking terminology. "
    "Never fabricate figures. Use INR and crore scale where relevant."
)


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    text: str
    model_used: str
    provider: str  # "cerebras"
    fallback_triggered: bool
    latency_ms: float
    task: str


def _call_cerebras(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call the configured Cerebras model — the only allowed LLM provider.
    """
    from openai import OpenAI

    if not settings.cerebras_api_key:
        raise RuntimeError("CEREBRAS_API_KEY is required for all LLM tasks")

    client = OpenAI(
        api_key=settings.cerebras_api_key,
        base_url=CEREBRAS_BASE_URL,
    )
    response = client.chat.completions.create(
        model=settings.cerebras_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    text = response.choices[0].message.content
    if not text or len(text.strip()) < 10:
        raise ValueError("Cerebras returned empty response")
    return text


def llm_call(
    prompt: str,
    task: str = "general",
    max_tokens: int = 2000,
    force_provider: Optional[str] = None,
) -> LLMResponse:
    """
    Unified LLM call with Cerebras-only enforcement.
    OCR tasks are NOT routed through this function.
    """
    if force_provider and force_provider != "cerebras":
        logger.warning(
            "[LLM] Ignoring force_provider=%s. Cerebras-only policy is enforced.",
            force_provider,
        )

    for attempt in range(MAX_RETRIES + 1):
        try:
            started = time.time()
            text = _call_cerebras(prompt, max_tokens)
            latency = (time.time() - started) * 1000
            return LLMResponse(
                text=text,
                model_used=settings.cerebras_model,
                provider="cerebras",
                fallback_triggered=False,
                latency_ms=round(latency, 1),
                task=task,
            )
        except Exception as exc:
            logger.warning(
                "[LLM] cerebras attempt %s failed for task '%s': %s",
                attempt + 1,
                task,
                exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Cerebras LLM call failed for task: {task}")


def llm_call_json(
    prompt: str,
    task: str = "json_extraction",
    max_tokens: int = 2000,
) -> dict:
    """
    Call LLM and parse response as JSON.
    Strips markdown code fences and retries parsing.
    """
    for attempt in range(3):
        try:
            response = llm_call(prompt, task=task, max_tokens=max_tokens)
            text = response.text.strip()
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("[LLM] JSON parse attempt %s failed: %s", attempt + 1, exc)
        except Exception as exc:
            logger.warning("[LLM] llm_call_json attempt %s failed: %s", attempt + 1, exc)

    logger.error("[LLM] All JSON parse attempts failed for task: %s", task)
    return {}
