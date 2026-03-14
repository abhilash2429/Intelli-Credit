"""ALM (Asset-Liability Management) Statement Parser."""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this Asset-Liability Management (ALM) statement for an Indian NBFC/bank.

Extract ONLY into this exact JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "currency": "INR",
  "maturity_buckets": [
    {{
      "bucket": "<1 day | 2-7 days | 8-14 days | 15-30 days | 31-90 days | 91-180 days | 181d-1yr | 1-3yr | 3-5yr | >5yr>",
      "assets_cr": <float or null>,
      "liabilities_cr": <float or null>,
      "gap_cr": <float or null>,
      "cumulative_gap_cr": <float or null>
    }}
  ],
  "total_assets_cr": <float or null>,
  "total_liabilities_cr": <float or null>,
  "structural_liquidity_gap_cr": <float or null>,
  "liquidity_coverage_ratio": <float or null>,
  "net_stable_funding_ratio": <float or null>,
  "concentration_risk": {{
    "top_3_lender_pct": <float or null>,
    "short_term_borrowing_pct": <float or null>
  }},
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>,
  "extraction_notes": "<any caveats>"
}}

STRICT RULES:
- All monetary values in INR Crore. Convert if in Lakh (÷100) or Million (÷10).
- Do NOT invent numbers. Use null for missing fields.
- Flag if short-term borrowing > 40% as a red_flag.
- Flag if cumulative gap is deeply negative in < 30 days buckets.

Document text:
{text}
"""


async def parse_alm_statement(file_path: str) -> dict:
    text = _extract_text(file_path)
    from backend.core.llm.llm_client import llm_call, LLMResponse
    result: LLMResponse = await asyncio.to_thread(llm_call, prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    raw_text: str = result.text
    try:
        return json.loads(re.sub(r"```json|```", "", raw_text).strip())
    except Exception:
        logger.warning("ALM parse failed — returning raw partial")
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": raw_text[:300]}


def _extract_text(file_path: str) -> str:
    try:
        low = file_path.lower()
        if low.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif low.endswith((".xlsx", ".xls")):
            import pandas as pd
            dfs = pd.read_excel(file_path, sheet_name=None)
            return "\n\n".join(f"[{k}]\n{v.to_string()}" for k, v in dfs.items())
        elif low.endswith(".csv"):
            import pandas as pd
            return pd.read_csv(file_path).to_string()
    except Exception as e:
        return f"[Read error: {e}]"
    return ""
