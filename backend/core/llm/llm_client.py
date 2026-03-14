"""
Unified LLM client with automatic fallback chain.
Primary provider: Cerebras gpt-oss-120b for all explanation/analysis tasks.
Fallback path: Cerebras -> Gemini -> Hugging Face -> GitHub Models.
OCR layers (Qwen2.5-VL, Sarvam, Tesseract) are handled separately.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

from backend.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

HF_MODEL = settings.hf_free_llm_model
GEMINI_MODEL = settings.gemini_model
CEREBRAS_MODEL = "gpt-oss-120b"
GITHUB_MODEL = "gpt-4o"

HF_BASE_URL = settings.huggingface_base_url
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"

MAX_RETRIES = 2
RETRY_DELAY = 1.0
TIMEOUT = 30

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
    provider: str  # "cerebras" | "gemini" | "huggingface" | "github_models"
    fallback_triggered: bool
    latency_ms: float
    task: str


def _call_cerebras(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call Cerebras gpt-oss-120b — primary provider for all explanation tasks.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("CEREBRAS_API_KEY", settings.cerebras_api_key),
        base_url=CEREBRAS_BASE_URL,
    )
    response = client.chat.completions.create(
        model=CEREBRAS_MODEL,
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


def _call_gemini(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call Google Gemini — fallback provider.
    """
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY", settings.gemini_api_key)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=api_key)  # type: ignore[reportPrivateImportUsage]
    model = genai.GenerativeModel(  # type: ignore[reportPrivateImportUsage]
        GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": max_tokens,
        },
    )

    text = (getattr(response, "text", "") or "").strip()
    if not text:
        # Some Gemini responses may not populate `.text` directly.
        parts: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    parts.append(part_text)
        text = "\n".join(parts).strip()

    if not text or len(text.strip()) < 10:
        raise ValueError("Gemini returned empty response")
    return text


def _call_huggingface(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call a free/open Hugging Face model — fallback provider.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("HUGGINGFACE_API_TOKEN", settings.huggingface_api_token),
        base_url=HF_BASE_URL,
    )
    response = client.chat.completions.create(
        model=HF_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    text = response.choices[0].message.content
    if not text or len(text.strip()) < 10:
        raise ValueError("Hugging Face model returned empty response")
    return text


def _call_github_models(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call GitHub Models (Azure-hosted) — last-resort fallback.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("GITHUB_TOKEN", settings.github_token),
        base_url=GITHUB_BASE_URL,
    )
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    text = response.choices[0].message.content
    if not text or len(text.strip()) < 10:
        raise ValueError("GitHub Models returned empty response")
    return text


def llm_call(
    prompt: str,
    task: str = "general",
    max_tokens: int = 2000,
    force_provider: Optional[str] = None,
) -> LLMResponse:
    """
    Unified LLM call with automatic fallback.
    All explanation tasks: Cerebras -> Gemini -> Hugging Face -> GitHub Models.
    OCR tasks are NOT routed through this function.
    """
    providers = []
    has_cerebras = bool(os.getenv("CEREBRAS_API_KEY", settings.cerebras_api_key))
    has_gemini = bool(os.getenv("GEMINI_API_KEY", settings.gemini_api_key))
    has_hf = bool(os.getenv("HUGGINGFACE_API_TOKEN", settings.huggingface_api_token))
    has_github = bool(os.getenv("GITHUB_TOKEN", settings.github_token))

    if force_provider:
        if force_provider == "cerebras":
            providers = [("cerebras", _call_cerebras)]
        elif force_provider == "gemini":
            providers = [("gemini", _call_gemini)]
        elif force_provider == "huggingface":
            providers = [("huggingface", _call_huggingface)]
        elif force_provider == "github_models":
            providers = [("github_models", _call_github_models)]
        else:
            providers = [("cerebras", _call_cerebras)]
    else:
        # Cerebras is always primary for all explanation tasks
        if has_cerebras:
            providers.append(("cerebras", _call_cerebras))
        if has_gemini:
            providers.append(("gemini", _call_gemini))
        if has_hf:
            providers.append(("huggingface", _call_huggingface))
        if has_github:
            providers.append(("github_models", _call_github_models))

    if not providers:
        raise RuntimeError(
            "No LLM provider is configured. Set CEREBRAS_API_KEY or GEMINI_API_KEY "
            "or HUGGINGFACE_API_TOKEN or GITHUB_TOKEN."
        )

    fallback_triggered = False
    for index, (provider_name, call_fn) in enumerate(providers):
        if index > 0:
            fallback_triggered = True
        for attempt in range(MAX_RETRIES + 1):
            try:
                started = time.time()
                text = call_fn(prompt, max_tokens)
                latency = (time.time() - started) * 1000
                model_used = (
                    CEREBRAS_MODEL
                    if provider_name == "cerebras"
                    else GEMINI_MODEL
                    if provider_name == "gemini"
                    else HF_MODEL
                    if provider_name == "huggingface"
                    else GITHUB_MODEL
                )
                return LLMResponse(
                    text=text,
                    model_used=model_used,
                    provider=provider_name,
                    fallback_triggered=fallback_triggered,
                    latency_ms=round(latency, 1),
                    task=task,
                )
            except Exception as exc:
                logger.warning(
                    "[LLM] %s attempt %s failed for task '%s': %s",
                    provider_name,
                    attempt + 1,
                    task,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

    raise RuntimeError(f"All LLM providers failed for task: {task}")


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
