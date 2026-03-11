"""Borrowing Profile / Debt Schedule Parser."""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this borrowing profile / debt schedule document for an Indian company.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "total_outstanding_cr": <float or null>,
  "secured_debt_cr": <float or null>,
  "unsecured_debt_cr": <float or null>,
  "facilities": [
    {{
      "lender_name": "<string>",
      "facility_type": "<TERM_LOAN | CC | OD | NCD | DEBENTURE | BOND | OTHERS>",
      "sanctioned_cr": <float or null>,
      "outstanding_cr": <float>,
      "rate_pct": <float or null>,
      "repayment": "<string or null>",
      "security": "<string or null>",
      "maturity_date": "<YYYY-MM-DD or null>",
      "overdue": <boolean>
    }}
  ],
  "debt_maturity_profile": {{
    "within_1yr_pct": <float or null>,
    "1_3yr_pct": <float or null>,
    "3_5yr_pct": <float or null>,
    "beyond_5yr_pct": <float or null>
  }},
  "avg_cost_of_debt_pct": <float or null>,
  "existing_dscr": <float or null>,
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- All amounts in INR Crore. Convert if in Lakh (÷100).
- Flag any overdue facility.
- Flag if short-term (within_1yr_pct) > 40%.
- Flag if no security/collateral provided.

Document text:
{text}
"""


async def parse_borrowing_profile(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.core.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await asyncio.to_thread(llm_call, prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": result[:300]}
