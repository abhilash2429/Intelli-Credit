"""
Crawl4AI-powered web scraper for financial intelligence research.
Used as the primary scraper in live research mode.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional
from datetime import date

logger = logging.getLogger(__name__)


class Crawl4AIScraper:
    """
    Crawl4AI-based intelligent scraper for financial news and regulatory data.
    Falls back gracefully if crawl4ai is not installed.
    """

    def __init__(self) -> None:
        self._available: Optional[bool] = None

    def _check_available(self) -> bool:
        if self._available is None:
            try:
                import crawl4ai  # noqa: F401
                self._available = True
                logger.info("[Crawl4AI] Library available and ready")
            except ImportError:
                self._available = False
                logger.warning("[Crawl4AI] Not installed — web scraping will use httpx fallback")
        return self._available

    async def scrape_url(self, url: str, *, timeout: int = 30) -> Optional[str]:
        """
        Scrape a URL and return markdown-formatted content.
        Returns None if scraping fails or library is unavailable.
        """
        if not self._check_available():
            return await self._httpx_fallback(url, timeout=timeout)

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                browser_type="chromium",
            )
            run_cfg = CrawlerRunConfig(
                markdown_generator=None,  # type: ignore[reportArgumentType]
                cache_mode=CacheMode.BYPASS,
                page_timeout=timeout * 1000,
            )

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
                if result.success:  # type: ignore[reportAttributeAccessIssue]
                    # Prefer fit_markdown (cleaner) over raw markdown
                    content = (
                        getattr(result, "markdown", None)
                        or getattr(result, "fit_markdown", None)
                        or ""
                    )
                    if hasattr(content, "fit_markdown"):
                        content = content.fit_markdown or content.raw_markdown or ""  # type: ignore[reportAttributeAccessIssue]
                    return str(content)[:8000] if content else None
                else:
                    logger.warning("[Crawl4AI] Scrape failed for %s: %s", url, result.error_message)  # type: ignore[reportAttributeAccessIssue]
                    return None
        except Exception as exc:
            logger.warning("[Crawl4AI] Exception scraping %s: %s", url, exc)
            return await self._httpx_fallback(url, timeout=timeout)

    async def scrape_urls(self, urls: List[str], *, max_concurrency: int = 4) -> dict[str, Optional[str]]:
        """
        Scrape multiple URLs concurrently, respecting max_concurrency.
        Returns mapping of url -> content (or None on failure).
        """
        if not self._check_available():
            # Use httpx batch fallback
            results = {}
            sem = asyncio.Semaphore(max_concurrency)

            async def _scrape(url: str) -> None:
                async with sem:
                    results[url] = await self._httpx_fallback(url)

            await asyncio.gather(*[_scrape(url) for url in urls])
            return results

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

            browser_cfg = BrowserConfig(headless=True, verbose=False)
            run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

            results: dict[str, Optional[str]] = {}
            sem = asyncio.Semaphore(max_concurrency)

            async def _scrape_with_crawler(url: str, crawler: "AsyncWebCrawler") -> None:
                async with sem:
                    try:
                        result = await crawler.arun(url=url, config=run_cfg)
                        if result.success:  # type: ignore[reportAttributeAccessIssue]
                            content = (
                                getattr(result, "markdown", None)
                                or getattr(result, "fit_markdown", None)
                                or ""
                            )
                            if hasattr(content, "fit_markdown"):
                                content = content.fit_markdown or content.raw_markdown or ""  # type: ignore[reportAttributeAccessIssue]
                            results[url] = str(content)[:8000] if content else None
                        else:
                            results[url] = None
                    except Exception as exc:
                        logger.warning("[Crawl4AI] Batch scrape error for %s: %s", url, exc)
                        results[url] = await self._httpx_fallback(url)

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                await asyncio.gather(*[_scrape_with_crawler(url, crawler) for url in urls])

            return results
        except Exception as exc:
            logger.warning("[Crawl4AI] Batch scrape failed: %s — falling back to httpx", exc)
            results = {}
            for url in urls:
                results[url] = await self._httpx_fallback(url)
            return results

    @staticmethod
    async def _httpx_fallback(url: str, *, timeout: int = 15) -> Optional[str]:
        """Simple httpx-based fallback scraper for when Crawl4AI is unavailable."""
        try:
            import httpx
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; IntelliCredit-Research/1.0; "
                    "+https://intellicredit.ai/bot)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "html.parser")
                # Remove boilerplate
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]
                return "\n".join(lines)[:6000]
        except Exception as exc:
            logger.warning("[Crawl4AI httpx fallback] Error for %s: %s", url, exc)
            return None
