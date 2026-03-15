"""
Research orchestration with Crawl4AI-powered scraping, live Tavily search, and deterministic fallback.
Live web outputs are hard-capped at 20 per run.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from urllib.parse import urlparse

from backend.config import settings
from backend.core.india_context import red_flag_keywords
from backend.core.research.crawl4ai_scraper import Crawl4AIScraper
from backend.core.research.ecourt_scraper import ECourtsScraper
from backend.core.research.firecrawl_client import FirecrawlClient
from backend.core.research.finding_extractor import FindingExtractor
from backend.core.research.tavily_client import TavilyClient
from backend.core.research.mca_scraper import MCAScraper
from backend.core.research.news_scraper import NewsScraper
from backend.core.research.search_strategies import get_all_queries
from backend.core.structured_logging import get_logger
from backend.schemas.credit import FindingType, MCAReport, ResearchFinding, Severity

logger = get_logger(__name__)

AGENT_TOOLS = [
    "tavily_search",
    "firecrawl_search",
    "firecrawl_scrape",
    "crawl4ai_scrape",
    "mca_lookup",
    "court_search",
    "news_search",
    "keyword_scan",
]
MAX_LIVE_OUTPUTS_PER_RUN = 20

RESEARCH_CHECKLIST = [
    "Search fraud/default/enforcement actions",
    "Search promoter legal and enforcement history",
    "Search MCA filings and struck-off linkages",
    "Search eCourts and NCLT/DRT proceedings",
    "Search sector and regulatory intelligence",
]


@dataclass
class ResearchBundle:
    findings: List[ResearchFinding]
    mca_report: MCAReport
    checklist_executed: List[str]
    research_job_id: str = ""
    run_metrics: dict[str, int | bool] | None = None


class WebResearchAgent:
    """
    Hybrid research agent.
    - `RESEARCH_MODE=live`: Crawl4AI + Tavily + LLM extraction
    - otherwise: deterministic scrapers/mock intelligence
    """

    def __init__(self) -> None:
        self.mca_scraper = MCAScraper()
        self.ecourts_scraper = ECourtsScraper()
        self.news_scraper = NewsScraper()
        self.finding_extractor = FindingExtractor()
        self.crawl4ai = Crawl4AIScraper()
        self.live_mode = settings.research_mode.lower() == "live"
        self.tavily_client = None
        self.firecrawl_client = None
        if self.live_mode and settings.tavily_api_key:
            try:
                self.tavily_client = TavilyClient()
            except Exception as exc:
                logger.warning("research.tavily_init_failed", error=str(exc))
        if self.live_mode and settings.firecrawl_api_key:
            try:
                self.firecrawl_client = FirecrawlClient()
            except Exception as exc:
                logger.warning("research.firecrawl_init_failed", error=str(exc))
        self.job_id = ""

    async def run(
        self,
        *,
        company_name: str,
        sector: str,
        cin: Optional[str] = None,
        gstin: Optional[str] = None,
        promoter_names: Optional[List[str]] = None,
    ) -> ResearchBundle:
        self.job_id = str(uuid.uuid4())
        findings: List[ResearchFinding] = []
        run_metrics: dict[str, int | bool] = {
            "live_mode_enabled": self.live_mode,
            "output_cap": min(max(int(settings.max_research_sources_per_company), 1), MAX_LIVE_OUTPUTS_PER_RUN),
        }

        mca_report = await self.mca_scraper.lookup(company_name, cin=cin)
        findings.extend(self._mca_findings(mca_report))
        findings.extend(await self.ecourts_scraper.search(company_name))

        if self.live_mode and (self.tavily_client is not None or self.firecrawl_client is not None):
            live_findings, live_metrics = await self._run_live_tavily(
                company_name=company_name,
                sector=sector,
                cin=cin,
                gstin=gstin,
                promoter_names=promoter_names or [],
            )
            findings.extend(live_findings)
            run_metrics.update(live_metrics)
        else:
            findings.extend(await self.news_scraper.search_company(company_name, sector))
            for promoter in promoter_names or []:
                findings.extend(await self.news_scraper.search_promoter(promoter))
            findings.extend(self._infer_regulatory_findings(company_name, sector))
            run_metrics.update(
                {
                    "queries_built": 0,
                    "queries_executed": 0,
                    "urls_selected_for_scrape": 0,
                    "urls_scraped_successfully": 0,
                    "live_findings_before_cap": 0,
                    "live_findings_returned": 0,
                    "live_fallback_used": 0,
                }
            )

        findings.extend(self._run_keyword_scan(findings))
        findings = self._deduplicate(findings)
        run_metrics["total_findings_after_dedupe"] = len(findings)

        return ResearchBundle(
            findings=findings,
            mca_report=mca_report,
            checklist_executed=RESEARCH_CHECKLIST,
            research_job_id=self.job_id,
            run_metrics=run_metrics,
        )

    async def _run_live_tavily(
        self,
        *,
        company_name: str,
        sector: str,
        cin: str | None,
        gstin: str | None,
        promoter_names: List[str],
    ) -> tuple[List[ResearchFinding], dict[str, int | bool]]:
        output_cap = min(max(int(settings.max_research_sources_per_company), 1), MAX_LIVE_OUTPUTS_PER_RUN)
        queries = get_all_queries(
            company_name=company_name,
            sector=sector,
            promoter_names=promoter_names,
            cin=cin,
            gstin=gstin,
            depth=settings.research_depth,
        )
        # De-duplicate queries while preserving priority order.
        deduped: list[dict] = []
        seen_queries: set[str] = set()
        for q in queries:
            q_text = str(q.get("query", "")).strip().lower()
            if not q_text or q_text in seen_queries:
                continue
            seen_queries.add(q_text)
            deduped.append(q)
        queries = deduped[: max(1, int(settings.max_live_queries))]
        logger.info("research.live.queries_built", count=len(queries), company=company_name)

        sem = asyncio.Semaphore(max(1, int(settings.live_query_concurrency)))
        query_results: list[tuple[dict, list[dict]]] = []
        primary_provider_quota_hit = asyncio.Event()
        primary_provider_errors = 0

        async def _run_query(q: dict) -> None:
            async with sem:
                nonlocal primary_provider_errors
                try:
                    results: list[dict] = []
                    # Keep per-query fanout compact to reduce crawl latency.
                    limit = min(int(settings.max_tavily_results_per_search), output_cap, 4)

                    # Primary preference: Tavily (if configured)
                    if self.tavily_client is not None:
                        try:
                            results = await asyncio.to_thread(
                                self.tavily_client.search,  # type: ignore[reportOptionalMemberAccess]
                                q["query"],
                                num_results=limit,
                            )
                        except Exception as exc:
                            err = str(exc)
                            primary_provider_errors += 1
                            logger.warning("research.live.tavily_failed", query=q["query"][:120], error=err)
                            if "429" in err or "quota" in err.lower() or "unauthorized" in err.lower() or "401" in err:
                                primary_provider_quota_hit.set()

                            # Provider failover to Firecrawl for this query
                            if self.firecrawl_client is not None:
                                results = await asyncio.to_thread(
                                    self.firecrawl_client.search,  # type: ignore[reportOptionalMemberAccess]
                                    q["query"],
                                    num_results=limit,
                                )
                    elif self.firecrawl_client is not None:
                        results = await asyncio.to_thread(
                            self.firecrawl_client.search,  # type: ignore[reportOptionalMemberAccess]
                            q["query"],
                            num_results=limit,
                        )

                    query_results.append((q, results))
                    logger.info(
                        "research.live.query_done",
                        query=q["query"][:120],
                        results=len(results),
                    )
                except Exception as exc:
                    err = str(exc)
                    primary_provider_errors += 1
                    logger.warning("research.live.query_failed", query=q["query"][:120], error=err)
                    if "429" in err or "quota" in err.lower() or "unauthorized" in err.lower() or "401" in err:
                        primary_provider_quota_hit.set()

        await asyncio.gather(*[_run_query(q) for q in queries])

        successful_query_count = sum(1 for _, res in query_results if res)
        if successful_query_count == 0:
            logger.warning(
                "research.live.fallback_deterministic",
                reason="all_live_search_providers_failed",
                company=company_name,
            )
            fallback: List[ResearchFinding] = []
            fallback.extend(await self.news_scraper.search_company(company_name, sector))
            for promoter in promoter_names:
                fallback.extend(await self.news_scraper.search_promoter(promoter))
            fallback.extend(self._infer_regulatory_findings(company_name, sector))
            fallback = fallback[:output_cap]
            return fallback, {
                "queries_built": len(queries),
                "queries_executed": len(query_results),
                "urls_selected_for_scrape": 0,
                "urls_scraped_successfully": 0,
                "live_findings_before_cap": len(fallback),
                "live_findings_returned": len(fallback),
                "live_fallback_used": 1,
                "output_cap": output_cap,
                "primary_provider_quota_hit": primary_provider_quota_hit.is_set(),
                "primary_provider_errors": primary_provider_errors,
            }

        # Gather unique URLs to deep-scrape with Crawl4AI
        url_to_meta: dict[str, tuple[dict, dict]] = {}
        filtered_out_count = 0
        for query_meta, results in query_results:
            query_type = str(query_meta.get("type", "")).upper()
            for result in results:
                url = result.get("url", "")
                if not url:
                    continue
                if self._is_excluded_domain(url):
                    filtered_out_count += 1
                    continue
                if settings.research_strict_source_filter and not self._is_allowed_source(url, query_type):
                    filtered_out_count += 1
                    continue
                if url not in url_to_meta:
                    url_to_meta[url] = (query_meta, result)

        # Limit total URLs to avoid overwhelming crawl budget
        all_urls = list(url_to_meta.keys())[: min(output_cap, max(1, int(settings.max_live_urls_to_scrape)))]
        logger.info("research.crawl4ai.scraping", urls=len(all_urls), company=company_name)
        scrape_concurrency = max(1, min(4, int(settings.live_query_concurrency)))

        # Use Crawl4AI to scrape all URLs in batch
        if self.firecrawl_client is not None:
            scraped_contents = await self.firecrawl_client.scrape_urls(all_urls, max_concurrency=scrape_concurrency)
            # Fallback failed pages to Crawl4AI/httpx pipeline
            failed_urls = [url for url, content in scraped_contents.items() if not content]
            if failed_urls:
                crawl4ai_fallback = await self.crawl4ai.scrape_urls(failed_urls, max_concurrency=scrape_concurrency)
                for url, content in crawl4ai_fallback.items():
                    if content:
                        scraped_contents[url] = content
        else:
            scraped_contents = await self.crawl4ai.scrape_urls(all_urls, max_concurrency=scrape_concurrency)

        scraped_success = sum(1 for v in scraped_contents.values() if v)
        logger.info("research.crawl4ai.done", scraped=scraped_success)

        findings: List[ResearchFinding] = []
        for url, content in scraped_contents.items():
            if not content:
                # Fall back to Tavily's own snippet if Crawl4AI failed
                _, result = url_to_meta[url]
                content = result.get("markdown", "") or result.get("content", "")
            if not content:
                continue

            query_meta, _ = url_to_meta[url]
            extracted = await asyncio.to_thread(
                self.finding_extractor.extract,
                raw_content=content,
                url=url,
                search_query=query_meta["query"],
                company_name=company_name,
            )
            findings.extend([self._to_research_finding(item) for item in extracted])
            if len(findings) >= output_cap:
                break

        uncapped_count = len(findings)
        findings = findings[:output_cap]
        return findings, {
            "queries_built": len(queries),
            "queries_executed": len(query_results),
            "urls_selected_for_scrape": len(all_urls),
            "urls_scraped_successfully": scraped_success,
            "live_findings_before_cap": uncapped_count,
            "live_findings_returned": len(findings),
            "live_fallback_used": 0,
            "output_cap": output_cap,
            "search_provider": "tavily" if self.tavily_client is not None else "firecrawl",
            "scrape_provider": "firecrawl+crawl4ai_fallback" if self.firecrawl_client is not None else "crawl4ai",
            "primary_provider_quota_hit": primary_provider_quota_hit.is_set(),
            "primary_provider_errors": primary_provider_errors,
            "urls_filtered_out": filtered_out_count,
        }

    @staticmethod
    def _mca_findings(mca_report: MCAReport) -> List[ResearchFinding]:
        if mca_report.associated_struck_off_companies:
            return [
                ResearchFinding(
                    headline="Director linkage with struck-off entities",
                    source_url="https://www.mca.gov.in/content/mca/global/en/mca/master-data.html",
                    source_name="MCA",
                    finding_type=FindingType.FRAUD_ALERT,
                    summary="Director linkage with struck-off entities detected from MCA records.",
                    severity=Severity.HIGH,
                    date_of_finding=date.today(),
                    confidence=0.9,
                    raw_snippet=", ".join(mca_report.associated_struck_off_companies),
                    score_impact=-10.0,
                    cam_section="character",
                )
            ]
        return [
            ResearchFinding(
                headline="MCA compliance healthy",
                source_url="https://www.mca.gov.in/content/mca/global/en/mca/master-data.html",
                source_name="MCA",
                finding_type=FindingType.NEUTRAL,
                summary="MCA records show compliant filing history with no struck-off associations.",
                severity=Severity.INFORMATIONAL,
                date_of_finding=date.today(),
                confidence=0.75,
                raw_snippet=f"Filing compliance score: {mca_report.filing_compliance_score:.1f}%",
                score_impact=0.0,
                cam_section="research_summary",
            )
        ]

    @staticmethod
    def _infer_regulatory_findings(company_name: str, sector: str) -> List[ResearchFinding]:
        low_sector = sector.lower()
        severity = Severity.LOW
        score_impact = -1.0
        summary = "No direct RBI/SEBI enforcement action found in sampled sources."
        if "real_estate" in low_sector:
            severity = Severity.MEDIUM
            score_impact = -5.0
            summary = "Sector-level regulatory tightening observed for real-estate debt underwriting."
        return [
            ResearchFinding(
                headline=f"{sector} regulatory context",
                source_url="https://www.rbi.org.in/",
                source_name="Regulatory Intel",
                finding_type=FindingType.REGULATORY,
                summary=summary,
                severity=severity,
                date_of_finding=date.today(),
                confidence=0.68,
                raw_snippet=f"{company_name} screened against RBI/SEBI/FSSAI alerts.",
                score_impact=score_impact,
                cam_section="conditions",
            )
        ]

    @staticmethod
    def _run_keyword_scan(findings: List[ResearchFinding]) -> List[ResearchFinding]:
        keywords = red_flag_keywords()
        alerts: List[ResearchFinding] = []
        for finding in findings:
            low = f"{finding.summary} {finding.raw_snippet}".lower()
            hits = [k for k in keywords if k in low]
            if not hits:
                continue
            alerts.append(
                ResearchFinding(
                    headline=f"Keyword alert from {finding.source_name}",
                    source_url=finding.source_url,
                    source_name=f"{finding.source_name} (Keyword Classifier)",
                    finding_type=FindingType.FRAUD_ALERT,
                    summary=f"Potential red-flag term(s) detected: {', '.join(hits[:3])}.",
                    severity=Severity.HIGH,
                    date_of_finding=finding.date_of_finding,
                    confidence=min(0.95, finding.confidence + 0.1),
                    raw_snippet=finding.raw_snippet[:600],
                    score_impact=-8.0,
                    cam_section="character",
                )
            )
        return alerts[:15]

    @staticmethod
    def _deduplicate(findings: List[ResearchFinding]) -> List[ResearchFinding]:
        seen = set()
        out: List[ResearchFinding] = []
        for finding in findings:
            key = (
                finding.source_url[:120].lower(),
                finding.summary[:120].lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(finding)
        return out

    @staticmethod
    def _is_excluded_domain(url: str) -> bool:
        excluded_domains = [
            "amazon.in",
            "flipkart.com",
            "justdial.com",
            "tradeindia.com",
            "indiamart.com",
            "instagram.com",
            "facebook.com",
            "x.com",
            "twitter.com",
            "youtube.com",
        ]
        low = url.lower()
        if any(domain in low for domain in excluded_domains):
            return True

        # Skip heavy or non-HTML assets that are slow to crawl and low-value for narrative extraction.
        # PDFs are explicitly allowed since legal/MCA evidence often arrives as PDF documents.
        blocked_extensions = (
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".svg",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
        )
        if low.split("?", 1)[0].endswith(blocked_extensions):
            return True

        return False

    @staticmethod
    def _domain_matches(url: str, allowed_domains: list[str]) -> bool:
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            return False
        if not host:
            return False
        normalized = host[4:] if host.startswith("www.") else host
        for domain in allowed_domains:
            d = domain.strip().lower()
            if not d:
                continue
            if normalized == d or normalized.endswith(f".{d}"):
                return True
        return False

    @staticmethod
    def _is_allowed_source(url: str, query_type: str) -> bool:
        legal_types = {"LITIGATION"}
        mca_types = {"MCA_FILING"}
        regulatory_types = {"REGULATORY_ACTION"}
        news_types = {"SECTOR_NEWS", "COMPANY_NEWS", "FRAUD_ALERT", "PROMOTER_BACKGROUND"}

        if query_type in legal_types:
            return WebResearchAgent._domain_matches(url, settings.legal_domains)
        if query_type in mca_types:
            return WebResearchAgent._domain_matches(url, settings.mca_domains)
        if query_type in regulatory_types:
            return WebResearchAgent._domain_matches(url, settings.regulatory_domains)
        if query_type in news_types:
            return WebResearchAgent._domain_matches(url, settings.news_domains)

        # Default strict behavior: allow only from the union of trusted lists.
        all_allowed = (
            settings.news_domains
            + settings.legal_domains
            + settings.mca_domains
            + settings.regulatory_domains
        )
        return WebResearchAgent._domain_matches(url, all_allowed)

    @staticmethod
    def _to_research_finding(item: dict) -> ResearchFinding:
        finding_type = WebResearchAgent._map_finding_type(item.get("finding_type"))
        severity = WebResearchAgent._map_severity(item.get("severity"))
        return ResearchFinding(
            headline=item.get("headline"),
            source_url=item.get("source_url", ""),
            source_name=item.get("source_name", "Web"),
            finding_type=finding_type,
            summary=item.get("summary", ""),
            severity=severity,
            date_of_finding=item.get("source_date"),
            confidence=0.82 if severity in {Severity.CRITICAL, Severity.HIGH} else 0.72,
            raw_snippet=item.get("raw_snippet", ""),
            score_impact=float(item.get("score_impact", 0.0)),
            cam_section=item.get("cam_section", "research_summary"),
        )

    @staticmethod
    def _map_finding_type(value: object) -> FindingType:
        raw = str(value or "").upper()
        if raw in {"FRAUD_ALERT", "PROMOTER_BACKGROUND"}:
            return FindingType.FRAUD_ALERT
        if raw in {"LITIGATION"}:
            return FindingType.LITIGATION
        if raw in {"REGULATORY_ACTION"}:
            return FindingType.REGULATORY
        if raw in {"SECTOR_NEWS"}:
            return FindingType.SECTOR
        if raw in {"MCA_FILING"}:
            return FindingType.REGULATORY
        if raw in {"COMPANY_NEWS", "INFORMATIONAL"}:
            return FindingType.NEUTRAL
        return FindingType.NEUTRAL

    @staticmethod
    def _map_severity(value: object) -> Severity:
        raw = str(value or "").upper()
        mapping = {
            "CRITICAL": Severity.CRITICAL,
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
            "INFORMATIONAL": Severity.INFORMATIONAL,
        }
        return mapping.get(raw, Severity.INFORMATIONAL)
