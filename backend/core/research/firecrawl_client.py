"""
Firecrawl client wrapper with search + scrape helpers.
Uses SDK when available, with HTTP fallback for compatibility.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)


class FirecrawlClient:
    def __init__(self) -> None:
        self.api_key = settings.firecrawl_api_key
        if not self.api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is required for Firecrawl live mode")
        self.base_url = "https://api.firecrawl.dev/v1"
        self._sdk = None
        try:
            from firecrawl import FirecrawlApp

            self._sdk = FirecrawlApp(api_key=self.api_key)
        except Exception as exc:
            logger.warning("firecrawl.sdk_unavailable", error=str(exc))

    def search(
        self,
        query: str,
        *,
        num_results: int = 5,
    ) -> list[dict[str, Any]]:
        logger.info("firecrawl.search.start", query=query[:120], limit=num_results)
        attempts = 2
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                if self._sdk is not None and hasattr(self._sdk, "search"):
                    response = self._sdk.search(query, limit=num_results)  # type: ignore[call-arg]
                    normalized = self._normalize_search_response(response)
                    logger.info("firecrawl.search.complete", query=query[:120], count=len(normalized))
                    return normalized

                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{self.base_url}/search",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"query": query, "limit": int(num_results)},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    normalized = self._normalize_search_response(payload)
                    logger.info("firecrawl.search.complete", query=query[:120], count=len(normalized))
                    return normalized
            except Exception as exc:  # pragma: no cover - provider/runtime error
                last_exc = exc
                err = str(exc).lower()
                non_retryable = any(
                    token in err
                    for token in ("invalid", "unauthorized", "wrong api key", "401", "forbidden", "403")
                )
                if non_retryable or attempt == attempts:
                    raise
                time.sleep(0.4)

        if last_exc:
            raise last_exc
        return []

    async def scrape_urls(
        self,
        urls: list[str],
        *,
        max_concurrency: int = 4,
    ) -> dict[str, str | None]:
        sem = asyncio.Semaphore(max_concurrency)
        results: dict[str, str | None] = {}

        async def _run(url: str) -> None:
            async with sem:
                try:
                    results[url] = await asyncio.to_thread(self.scrape_url, url)
                except Exception as exc:
                    # Never fail the whole pipeline for a single URL scrape failure.
                    logger.warning("firecrawl.scrape.failed", url=url, error=str(exc))
                    results[url] = None

        await asyncio.gather(*[_run(u) for u in urls], return_exceptions=False)
        return results

    def scrape_url(self, url: str) -> str | None:
        logger.info("firecrawl.scrape.start", url=url)
        attempts = 2
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                if self._sdk is not None and hasattr(self._sdk, "scrape_url"):
                    response = self._sdk.scrape_url(url, formats=["markdown"])  # type: ignore[call-arg]
                    text = self._extract_markdown(response)
                    if text:
                        logger.info("firecrawl.scrape.complete", url=url, chars=len(text))
                    return text

                with httpx.Client(timeout=40.0) as client:
                    resp = client.post(
                        f"{self.base_url}/scrape",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"url": url, "formats": ["markdown"]},
                    )
                    resp.raise_for_status()
                    text = self._extract_markdown(resp.json())
                    if text:
                        logger.info("firecrawl.scrape.complete", url=url, chars=len(text))
                    return text
            except Exception as exc:  # pragma: no cover
                last_exc = exc
                err = str(exc).lower()
                non_retryable = any(
                    token in err
                    for token in ("invalid", "unauthorized", "wrong api key", "401", "forbidden", "403")
                )
                if non_retryable:
                    logger.warning("firecrawl.scrape.non_retryable", url=url, error=str(exc))
                    return None
                if attempt == attempts:
                    logger.warning("firecrawl.scrape.exhausted", url=url, error=str(exc))
                    return None
                time.sleep(0.4)

        if last_exc:
            logger.warning("firecrawl.scrape.unknown_failure", url=url, error=str(last_exc))
        return None

    @staticmethod
    def _normalize_search_response(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("results") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("sourceUrl") or item.get("source_url") or ""
            if not url:
                continue
            title = item.get("title", "")
            desc = item.get("description") or item.get("snippet") or item.get("content") or ""
            markdown = item.get("markdown") or item.get("content") or ""
            normalized.append(
                {
                    "url": url,
                    "title": title,
                    "description": desc,
                    "markdown": markdown,
                    "metadata": {
                        "sourceURL": url,
                        "title": title,
                        "description": desc,
                        "score": item.get("score"),
                    },
                }
            )
        return normalized

    @staticmethod
    def _extract_markdown(payload: Any) -> str | None:
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), dict):
                data = payload["data"]
                markdown = data.get("markdown") or data.get("content") or ""
            else:
                markdown = payload.get("markdown") or payload.get("content") or ""
        else:
            markdown = ""
        text = str(markdown or "").strip()
        return text[:8000] if text else None
