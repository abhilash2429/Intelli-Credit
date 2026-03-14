"""Portfolio Cuts / Performance Data Parser — for NBFCs and financial entities."""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this portfolio performance / portfolio cuts document for an Indian NBFC or financial entity.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "aum_cr": <float or null>,
  "disbursements_cr": <float or null>,
  "borrower_count": <integer or null>,
  "average_ticket_size_lakhs": <float or null>,
  "portfolio_mix": [
    {{"segment": "<string>", "aum_cr": <float>, "pct": <float>}}
  ],
  "geographic_mix": [
    {{"state": "<string>", "pct": <float>}}
  ],
  "asset_quality": {{
    "gnpa_cr": <float or null>,
    "gnpa_pct": <float or null>,
    "nnpa_cr": <float or null>,
    "nnpa_pct": <float or null>,
    "provision_coverage_pct": <float or null>,
    "stage_1_pct": <float or null>,
    "stage_2_pct": <float or null>,
    "stage_3_pct": <float or null>
  }},
  "collection_efficiency_pct": <float or null>,
  "yield_on_portfolio_pct": <float or null>,
  "cost_of_funds_pct": <float or null>,
  "nim_pct": <float or null>,
  "roe_pct": <float or null>,
  "roa_pct": <float or null>,
  "capital_adequacy_ratio_pct": <float or null>,
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- All amounts in INR Crore.
- Flag if GNPA > 5%.
- Flag if collection_efficiency < 90%.
- Flag if stage_3_pct > 5%.

Document text:
{text}
"""


async def parse_portfolio_performance(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.core.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await asyncio.to_thread(llm_call, prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    raw_text = result.text if hasattr(result, "text") else str(result)
    try:
        return json.loads(re.sub(r"```json|```", "", raw_text).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": raw_text[:300]}
