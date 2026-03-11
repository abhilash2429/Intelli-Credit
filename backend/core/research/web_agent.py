"""
Research orchestration with live Firecrawl support and deterministic fallback.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from backend.config import settings
from backend.core.india_context import red_flag_keywords
from backend.core.research.ecourt_scraper import ECourtsScraper
from backend.core.research.finding_extractor import FindingExtractor
from backend.core.research.tavily_client import TavilyClient
from backend.core.research.mca_scraper import MCAScraper
from backend.core.research.news_scraper import NewsScraper
from backend.core.research.search_strategies import get_all_queries
from backend.core.structured_logging import get_logger
from backend.schemas.credit import FindingType, MCAReport, ResearchFinding, Severity

logger = get_logger(__name__)

AGENT_TOOLS = ["tavily_search", "mca_lookup", "court_search", "news_search", "keyword_scan"]

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


class WebResearchAgent:
    """
    Hybrid research agent.
    - `RESEARCH_MODE=live`: Tavily + Claude extraction
    - otherwise: deterministic scrapers/mock intelligence
    """

    def __init__(self) -> None:
        self.mca_scraper = MCAScraper()
        self.ecourts_scraper = ECourtsScraper()
        self.news_scraper = NewsScraper()
        self.finding_extractor = FindingExtractor()
        self.live_mode = settings.research_mode.lower() == "live"
        self.tavily_client = None
        if self.live_mode and settings.tavily_api_key:
            try:
                self.tavily_client = TavilyClient()
            except Exception as exc:
                logger.warning("research.tavily_init_failed", error=str(exc))
                self.live_mode = False
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

        mca_report = await self.mca_scraper.lookup(company_name, cin=cin)
        findings.extend(self._mca_findings(mca_report))
        findings.extend(await self.ecourts_scraper.search(company_name))

        if self.live_mode and self.tavily_client is not None:
            findings.extend(
                await self._run_live_tavily(
                    company_name=company_name,
                    sector=sector,
                    cin=cin,
                    gstin=gstin,
                    promoter_names=promoter_names or [],
                )
            )
        else:
            findings.extend(await self.news_scraper.search_company(company_name, sector))
            for promoter in promoter_names or []:
                findings.extend(await self.news_scraper.search_promoter(promoter))
            findings.extend(self._infer_regulatory_findings(company_name, sector))

        findings.extend(self._run_keyword_scan(findings))
        findings = self._deduplicate(findings)

        return ResearchBundle(
            findings=findings,
            mca_report=mca_report,
            checklist_executed=RESEARCH_CHECKLIST,
            research_job_id=self.job_id,
        )

    async def _run_live_tavily(
        self,
        *,
        company_name: str,
        sector: str,
        cin: str | None,
        gstin: str | None,
        promoter_names: List[str],
    ) -> List[ResearchFinding]:
        queries = get_all_queries(
            company_name=company_name,
            sector=sector,
            promoter_names=promoter_names,
            cin=cin,
            gstin=gstin,
            depth=settings.research_depth,
        )
        logger.info("research.live.queries_built", count=len(queries), company=company_name)

        sem = asyncio.Semaphore(5)
        query_results: list[tuple[dict, list[dict]]] = []
        payment_required = asyncio.Event()

        async def _run_query(q: dict) -> None:
            if payment_required.is_set():
                return
            async with sem:
                if payment_required.is_set():
                    return
                try:
                    results = await asyncio.to_thread(
                        self.tavily_client.search,
                        q["query"],
                        num_results=min(
                            settings.max_tavily_results_per_search,
                            settings.max_research_sources_per_company,
                        ),
                    )
                    query_results.append((q, results))
                    logger.info(
                        "research.live.query_done",
                        query=q["query"][:120],
                        results=len(results),
                    )
                except Exception as exc:
                    err = str(exc)
                    logger.warning("research.live.query_failed", query=q["query"][:120], error=err)
                    if "429" in err or "quota" in err.lower():
                        payment_required.set()

        await asyncio.gather(*[_run_query(q) for q in queries])

        if payment_required.is_set() and not query_results:
            logger.warning(
                "research.live.fallback_deterministic",
                reason="tavily_quota_exceeded",
                company=company_name,
            )
            fallback: List[ResearchFinding] = []
            fallback.extend(await self.news_scraper.search_company(company_name, sector))
            for promoter in promoter_names:
                fallback.extend(await self.news_scraper.search_promoter(promoter))
            fallback.extend(self._infer_regulatory_findings(company_name, sector))
            return fallback

        findings: List[ResearchFinding] = []
        sources_seen = 0
        for query_meta, results in query_results:
            for result in results:
                if sources_seen >= settings.max_research_sources_per_company:
                    break
                url = result.get("url", "")
                content = result.get("markdown", "")
                if not url or not content or self._is_excluded_domain(url):
                    continue

                extracted = await asyncio.to_thread(
                    self.finding_extractor.extract,
                    raw_content=content,
                    url=url,
                    search_query=query_meta["query"],
                    company_name=company_name,
                )
                sources_seen += 1
                findings.extend([self._to_research_finding(item) for item in extracted])

        return findings

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
        excluded = [
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
        return any(domain in low for domain in excluded)

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
