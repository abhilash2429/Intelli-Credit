"""
SWOT Analysis Engine.
Generates evidence-backed SWOT from extracted financials + research findings + sector context.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_SWOT_PROMPT = """\
You are a senior credit analyst at a top Indian investment bank.
Generate a structured SWOT analysis for this loan/investment decision.

COMPANY: {company_name}
SECTOR: {sector}
LOAN: ₹{loan_amount_cr} Cr {loan_type} | Tenure: {tenure_months} months

KEY FINANCIAL METRICS:
{financials}

RESEARCH FINDINGS:
{research}

SECTOR / MACRO CONTEXT:
{macro}

RULES (strictly follow):
1. Every SWOT point MUST cite a specific number or fact from the data above.
2. Generic points like "experienced management" with no evidence are FORBIDDEN.
3. Minimum 3 points per quadrant, maximum 5.
4. Opportunities and Threats should reference sector/macro context, not just company data.

Reply ONLY with this JSON — no markdown, no extra text:
{{
  "strengths": [
    {{"point": "<specific claim>", "evidence": "<exact number or fact>", "source": "<document type>"}}
  ],
  "weaknesses": [
    {{"point": "<specific claim>", "evidence": "<exact number or fact>", "source": "<document type>"}}
  ],
  "opportunities": [
    {{"point": "<specific claim>", "evidence": "<macro/sector fact>", "source": "Sector Research"}}
  ],
  "threats": [
    {{"point": "<specific claim>", "evidence": "<risk factor>", "source": "Research / Market"}}
  ],
  "sector_outlook": "<2-3 sentences on sector and macro context>",
  "macro_signals": {{
    "rbi_repo_rate_pct": <float or null>,
    "india_gdp_growth_pct": <float or null>,
    "sector_credit_growth_pct": <float or null>,
    "inflation_cpi_pct": <float or null>
  }},
  "investment_thesis": "<1 sentence summary of the credit case>",
  "recommendation": "<2-3 sentence overall recommendation>"
}}
"""

_MACRO_PROMPT = """\
Provide current (early 2026) sector and macro context for an Indian {sector} company.

Cover briefly:
1. RBI repo rate (as of early 2026)
2. India GDP growth rate
3. {sector} sector growth trends and headwinds
4. Key regulatory risks for {sector}
5. Competitive landscape signals

Be concise and factual. Focus on what matters for a credit/investment decision.
"""


async def generate_swot(
    company_name: str,
    sector: str,
    loan_amount_cr: float,
    loan_type: str,
    tenure_months: int,
    extracted_financials: dict,
    research_findings: list,
) -> dict:
    from backend.core.llm.llm_client import llm_call

    # Step 1: Sector macro context
    try:
        macro_text = await asyncio.to_thread(
            llm_call,
            prompt=_MACRO_PROMPT.format(sector=sector),
            task="research",
        )
    except Exception:
        macro_text = "Macro data unavailable."

    # Step 2: Build prompt
    financials_str = _format_financials(extracted_financials)
    research_str = _format_research(research_findings)

    prompt = _SWOT_PROMPT.format(
        company_name=company_name,
        sector=sector,
        loan_amount_cr=loan_amount_cr,
        loan_type=loan_type,
        tenure_months=tenure_months,
        financials=financials_str,
        research=research_str,
        macro=macro_text[:2000],
    )

    # Step 3: Generate
    try:
        result = await asyncio.to_thread(llm_call, prompt=prompt, task="cam_narrative")
        cleaned = re.sub(r"```json|```", "", result).strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"SWOT generation failed: {e}")
        return {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "sector_outlook": "Analysis unavailable — run analysis pipeline first.",
            "macro_signals": {},
            "investment_thesis": "Insufficient data",
            "recommendation": "Manual review required.",
        }


def _format_financials(data: dict) -> str:
    KEY_FIELDS = [
        ("revenue_crore", "Revenue (₹Cr)"),
        ("ebitda_margin_pct", "EBITDA Margin %"),
        ("ebitda_margin", "EBITDA Margin %"),
        ("pat_crore", "PAT (₹Cr)"),
        ("de_ratio", "D/E Ratio"),
        ("debt_equity_ratio", "D/E Ratio"),
        ("current_ratio", "Current Ratio"),
        ("dscr", "DSCR"),
        ("interest_coverage", "Interest Coverage"),
        ("interest_coverage_ratio", "Interest Coverage"),
        ("promoter_holding_pct", "Promoter Holding %"),
        ("total_pledged_pct", "Pledged %"),
        ("gnpa_pct", "GNPA %"),
        ("collection_efficiency_pct", "Collection Efficiency %"),
        ("aum_cr", "AUM (₹Cr)"),
        ("total_outstanding_cr", "Total Debt Outstanding (₹Cr)"),
        ("structural_liquidity_gap_cr", "ALM Liquidity Gap (₹Cr)"),
    ]
    lines = []
    seen_labels = set()
    for key, label in KEY_FIELDS:
        val = data.get(key)
        if val is not None and label not in seen_labels:
            lines.append(f"  {label}: {val}")
            seen_labels.add(label)
    return "\n".join(lines) or "  No extracted financial data available."


def _format_research(findings: list) -> str:
    if not findings:
        return "  No adverse research findings."
    out = []
    for f in findings[:12]:
        if hasattr(f, "severity"):
            severity = f.severity
            summary = f.summary
            source = getattr(f, "source_name", "Web")
        elif isinstance(f, dict):
            severity = f.get("severity", "LOW")
            summary = f.get("summary", "")
            source = f.get("source_name", "Web")
        else:
            continue
        out.append(f"  [{severity}] {summary} (Source: {source})")
    return "\n".join(out)
