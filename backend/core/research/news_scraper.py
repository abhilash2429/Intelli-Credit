"""
News and promoter intelligence provider.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List

from backend.config import settings
from backend.schemas.credit import FindingType, ResearchFinding, Severity

logger = logging.getLogger(__name__)


class NewsScraper:
    """
    Mock-first provider with company-specific intelligence for known test cases.
    All mock results are clearly labelled with (Mock) in source_name.
    """

    async def search_company(self, company_name: str, sector: str) -> List[ResearchFinding]:
        low = company_name.lower()
        findings: List[ResearchFinding] = []

        # Company-specific mock intelligence
        if "vedanta" in low:
            findings.extend(self._vedanta_findings())
        elif "pvr" in low or "inox" in low:
            findings.extend(self._pvr_inox_findings())
        elif "varun" in low and "beverage" in low:
            findings.extend(self._varun_beverages_findings())
        elif "vardhman" in low:
            findings.extend(self._vardhman_findings())

        # Generic sector finding
        findings.append(
            ResearchFinding(
                source_url="https://news.example/sector-outlook-2026",
                source_name=f"Sector Pulse (Mock)",
                finding_type=FindingType.SECTOR,
                summary=(
                    f"{sector.replace('_', ' ').title()} sector expected to remain stable with moderate "
                    "margin pressure due to logistics costs."
                ),
                severity=Severity.LOW,
                date_of_finding=date(2026, 1, 10),
                confidence=0.72,
                raw_snippet="Sector growth 8-10%, but working capital cycles remain stretched.",
            )
        )

        if not any("vedanta" in f.summary.lower() or "pvr" in f.summary.lower()
                    or "varun" in f.summary.lower() for f in findings if f.source_name != "Sector Pulse (Mock)"):
            logger.warning(f"[Research] No company-specific mock data for '{company_name}' — using generic only")

        return findings

    async def search_promoter(self, promoter_name: str) -> List[ResearchFinding]:
        low = promoter_name.lower()
        if "agarwal" in low or "vedanta" in low:
            return [
                ResearchFinding(
                    source_url="https://news.example/agarwal-promoter-pledge",
                    source_name="Moneycontrol (Mock)",
                    finding_type=FindingType.FRAUD_ALERT,
                    summary="Promoter Anil Agarwal has pledged 92.3% of holdings in Vedanta Limited; SEBI inquiry ongoing.",
                    severity=Severity.HIGH,
                    date_of_finding=date(2025, 11, 15),
                    confidence=0.82,
                    raw_snippet="Promoter pledge at 92.3% of category; SEBI has issued show-cause notice.",
                    score_impact=-8.0,
                    cam_section="character",
                )
            ]
        if "kumar" in low:
            return [
                ResearchFinding(
                    source_url="https://news.example/promoter-award",
                    source_name="Economic Times (Mock)",
                    finding_type=FindingType.NEUTRAL,
                    summary="Promoter received an MSME export award in 2024.",
                    severity=Severity.INFORMATIONAL,
                    date_of_finding=date(2024, 9, 2),
                    confidence=0.61,
                    raw_snippet="Awarded by state exports promotion council.",
                )
            ]
        return []

    @staticmethod
    def _vedanta_findings() -> List[ResearchFinding]:
        return [
            ResearchFinding(
                source_url="https://main.sci.gov.in/supremecourt/2019/14812",
                source_name="Supreme Court of India (Mock)",
                finding_type=FindingType.LITIGATION,
                summary="Vedanta Limited: SLP(C) No. 14812/2019 — ₹25,000 Cr Sterlite Copper environmental liability case pending in Supreme Court.",
                severity=Severity.CRITICAL,
                date_of_finding=date(2025, 3, 10),
                confidence=0.92,
                raw_snippet="SLP(C) No. 14812/2019 — Tamil Nadu Pollution Control Board vs Vedanta (Sterlite Copper). Amount at stake: ₹25,000 Cr+. Status: Pending.",
                score_impact=-15.0,
                cam_section="character",
            ),
            ResearchFinding(
                source_url="https://news.example/vedanta-sebi-inquiry-2025",
                source_name="SEBI Order (Mock)",
                finding_type=FindingType.REGULATORY,
                summary="SEBI inquiry into Vedanta's related-party transactions with Vedanta Resources (UK parent) and pricing of inter-company loans.",
                severity=Severity.HIGH,
                date_of_finding=date(2025, 6, 20),
                confidence=0.85,
                raw_snippet="SEBI has directed Vedanta to provide details of all related-party transactions exceeding ₹100 Cr with parent entity.",
                score_impact=-8.0,
                cam_section="character",
            ),
            ResearchFinding(
                source_url="https://news.example/vedanta-debt-restructure-2025",
                source_name="Reuters (Mock)",
                finding_type=FindingType.FRAUD_ALERT,
                summary="Vedanta Resources (UK parent) completed debt restructuring of $3.2B in bonds; cross-default risk to Indian subsidiary.",
                severity=Severity.HIGH,
                date_of_finding=date(2025, 9, 5),
                confidence=0.88,
                raw_snippet="Parent entity Vedanta Resources restructured offshore bonds; analysts flag cross-default triggers in Indian entity loan covenants.",
                score_impact=-10.0,
                cam_section="capital",
            ),
            ResearchFinding(
                source_url="https://news.example/vedanta-sterlite-protest",
                source_name="Business Standard (Mock)",
                finding_type=FindingType.SECTOR,
                summary="Vedanta's Sterlite Copper Tuticorin plant remains shut since 2018; environmental clearance still pending. Revenue impact ~₹3,000 Cr annually.",
                severity=Severity.MEDIUM,
                date_of_finding=date(2025, 1, 15),
                confidence=0.80,
                raw_snippet="Sterlite Copper: plant closure continues; government panel recommends conditional reopening.",
                score_impact=-5.0,
                cam_section="conditions",
            ),
        ]

    @staticmethod
    def _pvr_inox_findings() -> List[ResearchFinding]:
        return [
            ResearchFinding(
                source_url="https://news.example/pvr-inox-merger-integration",
                source_name="ET Markets (Mock)",
                finding_type=FindingType.NEUTRAL,
                summary="PVR INOX post-merger integration on track; synergy savings of ₹150 Cr realized in FY2024.",
                severity=Severity.INFORMATIONAL,
                date_of_finding=date(2025, 8, 12),
                confidence=0.75,
                raw_snippet="PVR INOX reports successful consolidation of 1,700+ screens; EBITDA margin improving.",
                score_impact=2.0,
                cam_section="capacity",
            ),
        ]

    @staticmethod
    def _varun_beverages_findings() -> List[ResearchFinding]:
        return [
            ResearchFinding(
                source_url="https://news.example/varun-beverages-expansion",
                source_name="Mint (Mock)",
                finding_type=FindingType.NEUTRAL,
                summary="Varun Beverages: strong volume growth in Q3FY25; Africa expansion on track.",
                severity=Severity.INFORMATIONAL,
                date_of_finding=date(2025, 10, 22),
                confidence=0.78,
                raw_snippet="Varun Beverages reports 18% YoY volume growth; PepsiCo partnership strengthened.",
                score_impact=3.0,
                cam_section="capacity",
            ),
        ]

    @staticmethod
    def _vardhman_findings() -> List[ResearchFinding]:
        return [
            ResearchFinding(
                source_url="https://news.example/vardhman-promoter-tax-query",
                source_name="Business Chronicle (Mock)",
                finding_type=FindingType.FRAUD_ALERT,
                summary="One promoter entity was issued an income-tax query notice; no prosecution reported.",
                severity=Severity.MEDIUM,
                date_of_finding=date(2025, 7, 22),
                confidence=0.66,
                raw_snippet="Tax department sought clarification on inter-company transactions.",
            ),
        ]

