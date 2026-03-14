"""Shareholding Pattern Parser — promoter/public/FII holdings, pledge data."""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this shareholding pattern document for an Indian listed/unlisted company.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "company_name": "<string or null>",
  "total_shares": <integer or null>,
  "promoter_holding_pct": <float>,
  "total_pledged_pct": <float or null>,
  "categories": [
    {{
      "category": "<Promoter & Promoter Group | FII/FPI | MF/DII | Public-Non-Institutional | ESOP | Other>",
      "shares": <integer or null>,
      "percentage": <float>,
      "pledged_shares": <integer or null>,
      "pledged_pct": <float or null>
    }}
  ],
  "top_shareholders": [
    {{"rank": <int>, "name": "<string>", "shares": <integer>, "percentage": <float>}}
  ],
  "changes_qoq": [
    {{"category": "<string>", "prev_pct": <float>, "curr_pct": <float>, "delta": <float>}}
  ],
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- promoter_holding_pct = sum of all promoter sub-categories.
- Flag if total_pledged_pct > 25%.
- Flag if promoter_holding_pct < 26%.
- Flag if single non-promoter entity holds > 15%.
- Do NOT invent numbers. Use null where unavailable.

Document text:
{text}
"""


async def parse_shareholding_pattern(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.core.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await asyncio.to_thread(llm_call, prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    raw_text = result.text if hasattr(result, "text") else str(result)
    try:
        return json.loads(re.sub(r"```json|```", "", raw_text).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": raw_text[:300]}
