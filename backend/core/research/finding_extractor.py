"""
LLM-backed extractor that turns page content into structured findings.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, date
from typing import Any

from backend.core.llm.llm_client import llm_call_json
from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)

EXTRACTION_PROMPT = """You are a senior Indian credit risk analyst.
Extract credit-relevant findings from the supplied web page content.

Company: {company_name}
Search Query: {search_query}
URL: {url}

Page content:
{content}

Return only valid JSON:
{{
  "findings": [
    {{
      "headline": "short title",
      "summary": "2-3 sentence factual summary",
      "finding_type": "FRAUD_ALERT|LITIGATION|REGULATORY_ACTION|PROMOTER_BACKGROUND|SECTOR_NEWS|COMPANY_NEWS|MCA_FILING|INFORMATIONAL",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL",
      "source_date": "YYYY-MM-DD or null",
      "score_impact": -30 to +5,
      "cam_section": "character|capacity|capital|collateral|conditions|research_summary",
      "is_relevant": true
    }}
  ]
}}
"""


class FindingExtractor:
    """
    Uses Anthropic if available, otherwise unified free LLM, then heuristics.
    """

    def __init__(self) -> None:
        self._client = None
        self._enabled = bool(settings.anthropic_api_key)
        if self._enabled:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except Exception:
                logger.warning("finding_extractor.anthropic_unavailable")
                self._enabled = False

    def extract(
        self,
        *,
        raw_content: str,
        url: str,
        search_query: str,
        company_name: str,
    ) -> list[dict[str, Any]]:
        content = (raw_content or "").strip()
        if len(content) < 120:
            return []

        if self._enabled and self._client is not None:
            findings = self._extract_llm(content, url, search_query, company_name)
            if findings:
                return findings
        findings = self._extract_unified_llm(content, url, search_query, company_name)
        if findings:
            return findings
        return self._extract_heuristic(content, url, search_query, company_name)

    def _extract_llm(
        self,
        content: str,
        url: str,
        search_query: str,
        company_name: str,
    ) -> list[dict[str, Any]]:
        prompt = EXTRACTION_PROMPT.format(
            company_name=company_name,
            search_query=search_query,
            url=url,
            content=content[:8000],
        )
        try:
            response = self._client.messages.create(  # type: ignore[union-attr]
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            cleaned = self._strip_fences(raw)
            parsed = json.loads(cleaned)
            out = []
            for item in parsed.get("findings", []):
                if not item.get("is_relevant", True):
                    continue
                out.append(
                    {
                        "headline": str(item.get("headline", ""))[:180],
                        "summary": str(item.get("summary", ""))[:1200],
                        "finding_type": self._normalize_finding_type(item.get("finding_type")),
                        "severity": self._normalize_severity(item.get("severity")),
                        "source_date": self._parse_date(item.get("source_date")),
                        "score_impact": float(item.get("score_impact", 0.0)),
                        "cam_section": str(item.get("cam_section", "research_summary")),
                        "source_url": url,
                        "source_name": self._source_name(url),
                        "raw_snippet": content[:1200],
                    }
                )
            return out
        except Exception as exc:
            logger.warning("finding_extractor.llm_failed", error=str(exc), url=url[:120])
            return []

    def _extract_unified_llm(
        self,
        content: str,
        url: str,
        search_query: str,
        company_name: str,
    ) -> list[dict[str, Any]]:
        prompt = EXTRACTION_PROMPT.format(
            company_name=company_name,
            search_query=search_query,
            url=url,
            content=content[:8000],
        )
        try:
            parsed = llm_call_json(
                prompt,
                task="research_finding_extraction",
                max_tokens=1800,
            )
            out = []
            for item in parsed.get("findings", []):
                if not item.get("is_relevant", True):
                    continue
                out.append(
                    {
                        "headline": str(item.get("headline", ""))[:180],
                        "summary": str(item.get("summary", ""))[:1200],
                        "finding_type": self._normalize_finding_type(item.get("finding_type")),
                        "severity": self._normalize_severity(item.get("severity")),
                        "source_date": self._parse_date(item.get("source_date")),
                        "score_impact": float(item.get("score_impact", 0.0)),
                        "cam_section": str(item.get("cam_section", "research_summary")),
                        "source_url": url,
                        "source_name": self._source_name(url),
                        "raw_snippet": content[:1200],
                    }
                )
            return out
        except Exception as exc:
            logger.warning("finding_extractor.unified_llm_failed", error=str(exc), url=url[:120])
            return []

    def _extract_heuristic(
        self,
        content: str,
        url: str,
        search_query: str,
        company_name: str,
    ) -> list[dict[str, Any]]:
        low = content.lower()
        hits: list[tuple[str, str, str, float]] = []
        rules = [
            (r"\bed raid\b|\bcbi\b|\bsfio\b|\bgst fraud\b|\bfake invoice\b", "FRAUD_ALERT", "CRITICAL", -24.0),
            (r"\bnclt\b|\binsolvency\b|\bcirp\b|\bliquidation\b", "LITIGATION", "CRITICAL", -22.0),
            (r"\bdefault\b|\bnpa\b|\bcheque bounce\b", "FRAUD_ALERT", "HIGH", -14.0),
            (r"\bcourt\b|\blawsuit\b|\barbitration\b|\bdrt\b", "LITIGATION", "MEDIUM", -7.0),
            (r"\brbi\b|\bsebi\b|\bfssai\b|\bregulatory\b", "REGULATORY_ACTION", "MEDIUM", -6.0),
            (r"\bgrowth\b|\bexpansion\b|\baward\b|\bstrong demand\b", "COMPANY_NEWS", "LOW", 2.0),
        ]
        for pattern, ftype, sev, impact in rules:
            if re.search(pattern, low):
                hits.append((ftype, sev, self._headline_from_content(content, search_query), impact))

        if not hits:
            return []

        out = []
        for ftype, sev, headline, impact in hits[:3]:
            out.append(
                {
                    "headline": headline,
                    "summary": content[:400].replace("\n", " ").strip(),
                    "finding_type": ftype,
                    "severity": sev,
                    "source_date": None,
                    "score_impact": impact,
                    "cam_section": "research_summary",
                    "source_url": url,
                    "source_name": self._source_name(url),
                    "raw_snippet": content[:1200],
                }
            )
        return out

    @staticmethod
    def _source_name(url: str) -> str:
        try:
            from urllib.parse import urlparse

            host = urlparse(url).netloc.replace("www.", "")
            return host.split(".")[0].title() if host else "Web"
        except Exception:
            return "Web"

    @staticmethod
    def _headline_from_content(content: str, fallback: str) -> str:
        for line in content.splitlines():
            line = line.strip()
            if 15 <= len(line) <= 180:
                return line
        return fallback[:180]

    @staticmethod
    def _strip_fences(text: str) -> str:
        value = text.strip()
        if value.startswith("```"):
            value = value.strip("`")
            if value.startswith("json"):
                value = value[4:]
        return value.strip()

    @staticmethod
    def _normalize_severity(value: Any) -> str:
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"}
        v = str(value or "INFORMATIONAL").upper()
        return v if v in valid else "INFORMATIONAL"

    @staticmethod
    def _normalize_finding_type(value: Any) -> str:
        allowed = {
            "FRAUD_ALERT",
            "LITIGATION",
            "REGULATORY_ACTION",
            "PROMOTER_BACKGROUND",
            "SECTOR_NEWS",
            "COMPANY_NEWS",
            "MCA_FILING",
            "INFORMATIONAL",
        }
        v = str(value or "INFORMATIONAL").upper()
        return v if v in allowed else "INFORMATIONAL"

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if value in (None, "", "null"):
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None
