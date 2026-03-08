"""
eCourts litigation checker with deterministic mock fallback.
"""

from __future__ import annotations

from datetime import date
from typing import List

from backend.schemas.credit import FindingType, ResearchFinding, Severity


class ECourtsScraper:
    async def search(self, company_name: str) -> List[ResearchFinding]:
        findings: List[ResearchFinding] = []
        low = company_name.lower()

        if "vedanta" in low:
            findings.extend([
                ResearchFinding(
                    source_url="https://main.sci.gov.in/supremecourt/2019/14812",
                    source_name="eCourts (Mock)",
                    finding_type=FindingType.LITIGATION,
                    summary="SLP(C) No. 14812/2019 — Sterlite Copper environmental liability. Supreme Court. Amount: ₹25,000 Cr+. Status: Pending.",
                    severity=Severity.CRITICAL,
                    date_of_finding=date(2025, 3, 10),
                    confidence=0.92,
                    raw_snippet="Tamil Nadu Pollution Control Board vs Vedanta Limited (Sterlite Copper Tuticorin). Supreme Court SLP(C) 14812/2019.",
                    score_impact=-12.0,
                    cam_section="character",
                ),
                ResearchFinding(
                    source_url="https://ecourts.example/vedanta-nclt-goa",
                    source_name="eCourts (Mock)",
                    finding_type=FindingType.LITIGATION,
                    summary="Vedanta: Goa mining lease dispute at NCLT — government seeking forfeiture of mining rights.",
                    severity=Severity.HIGH,
                    date_of_finding=date(2025, 5, 18),
                    confidence=0.80,
                    raw_snippet="NCLT Goa Bench: Government of Goa vs Sesa Goa (Vedanta subsidiary). Mining lease renewal contested.",
                    score_impact=-6.0,
                    cam_section="conditions",
                ),
            ])
        elif "agri" in low:
            findings.append(
                ResearchFinding(
                    source_url="https://ecourts.example/case/2024-cs-102",
                    source_name="eCourts (Mock)",
                    finding_type=FindingType.LITIGATION,
                    summary="One commercial recovery suit filed by a packaging vendor; matter under mediation.",
                    severity=Severity.MEDIUM,
                    date_of_finding=date(2024, 11, 4),
                    confidence=0.74,
                    raw_snippet="Civil Suit 102/2024 - vendor payment dispute, amount disputed ₹42 lakh.",
                )
            )
        else:
            findings.append(
                ResearchFinding(
                    source_url="https://ecourts.example/no-major-cases",
                    source_name="eCourts (Mock)",
                    finding_type=FindingType.NEUTRAL,
                    summary="No material litigation found in district and high court records.",
                    severity=Severity.INFORMATIONAL,
                    date_of_finding=date(2025, 8, 1),
                    confidence=0.68,
                    raw_snippet="No significant cases were linked to this entity in sampled jurisdictions.",
                )
            )
        return findings

