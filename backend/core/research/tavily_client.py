"""
Tavily client wrapper with retries, normalization, and structured logs.
"""

from __future__ import annotations

from typing import Any, List

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)


class TavilyClient:
    """
    Thin production-safe wrapper over tavily-python SDK.
    """

    def __init__(self) -> None:
        self.max_results = settings.max_tavily_results_per_search
        self.api_key = settings.tavily_api_key
        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY is required for live research mode")
        try:
            from tavily import TavilyClient as SDKTavilyClient
        except ImportError as exc:
            raise RuntimeError("tavily-python is not installed") from exc
        self.client = SDKTavilyClient(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(Exception),
    )
    def search(
        self,
        query: str,
        *,
        num_results: int | None = None,
        search_depth: str = "advanced",
    ) -> list[dict[str, Any]]:
        limit = int(num_results or self.max_results)
        logger.info("tavily.search.start", query=query[:120], limit=limit, depth=search_depth)
        
        # We always want raw content for extraction
        response = self.client.search(
            query=query,
            search_depth=search_depth,  # type: ignore[reportArgumentType]
            max_results=limit,
            include_raw_content=True,
        )
        
        results = response.get("results", [])
        normalized = [self._normalize_result(r) for r in results]
        
        logger.info("tavily.search.complete", query=query[:120], count=len(normalized))
        return normalized

    @staticmethod
    def _normalize_result(item: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize Tavily search format to the format expected by the finding extractor.
        """
        url = item.get("url", "")
        title = item.get("title", "")
        content = item.get("content", "")
        raw_content = item.get("raw_content", "")
        
        # For the markdown field, we use raw_content if available, falling back to summary content
        markdown = raw_content if raw_content else content

        return {
            "url": url,
            "title": title,
            "description": content,  # Tavily's content is a snippet/summary
            "markdown": markdown,
            "metadata": {
                "sourceURL": url,
                "title": title,
                "description": content,
                "score": item.get("score"),
            },
        }
