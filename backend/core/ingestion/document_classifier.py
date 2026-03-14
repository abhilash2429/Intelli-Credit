"""
Auto-classify uploaded documents into the 5 required types.
Strategy: filename keywords first (deterministic) → LLM content analysis (fallback).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

DOC_TYPES = {
    "ALM": "Asset-Liability Management Statement",
    "SHAREHOLDING": "Shareholding Pattern",
    "BORROWING_PROFILE": "Borrowing Profile / Debt Schedule",
    "ANNUAL_REPORT": "Annual Report (P&L / Balance Sheet / Cashflow)",
    "PORTFOLIO": "Portfolio Cuts / Performance Data",
}

_FILENAME_RULES: list[tuple[list[str], str]] = [
    (["alm", "asset_liab", "assetliab", "liquidity", "maturity_profile", "maturity_bucket"], "ALM"),
    (["shareholding", "share_pattern", "sharehol", "promoter_holding", "sh_pattern"], "SHAREHOLDING"),
    (["borrowing", "debt_schedule", "credit_profile", "loan_profile", "borrowal", "facility_list", "credit_facilities"], "BORROWING_PROFILE"),
    (["annual_report", "annual report", "p&l", "profit_loss", "balance_sheet", "cashflow",
      "financial_statement", "_ar_", "fy20", "fy21", "fy22", "fy23", "fy24", "fy25", "ar_fy", "annual"], "ANNUAL_REPORT"),
    (["portfolio", "performance", "aum", "npa_report", "collection", "disbursement",
      "portfolio_cut", "fund_performance", "port_cut"], "PORTFOLIO"),
]

_CONTENT_PROMPT = """\
Classify this financial document into exactly one of:
  ALM            - Asset-Liability Management: maturity buckets, liquidity gaps
  SHAREHOLDING   - Shareholding pattern: promoter/public/FII holdings, pledge data
  BORROWING_PROFILE - Debt schedule: existing facilities, lender names, repayment
  ANNUAL_REPORT  - Annual report: P&L, Balance Sheet, Cash Flow statements
  PORTFOLIO      - Portfolio performance: AUM, NPA %, collection efficiency, disbursements

Filename: {filename}
First 2000 characters:
{content}

Reply ONLY with this JSON — no markdown, no extra text:
{{"doc_type": "<one of the 5 types above>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}
"""


async def classify_document(file_path: str, filename: str) -> Tuple[str, float, str]:
    """Returns (doc_type, confidence, reasoning)."""
    normalised = re.sub(r"[\s\-\.]", "_", filename.lower())
    for keywords, doc_type in _FILENAME_RULES:
        if any(kw in normalised for kw in keywords):
            return doc_type, 0.92, f"Filename matched keyword pattern for {doc_type}"

    content = _preview_file(file_path, max_chars=2000)
    prompt = _CONTENT_PROMPT.format(filename=filename, content=content)

    try:
        from backend.core.llm.llm_client import llm_call
        result = await asyncio.to_thread(llm_call, prompt=prompt, task="classification")
        raw_text = result.text if hasattr(result, "text") else str(result)
        cleaned = re.sub(r"```json|```", "", raw_text).strip()
        parsed = json.loads(cleaned)
        doc_type = parsed.get("doc_type", "ANNUAL_REPORT")
        if doc_type not in DOC_TYPES:
            doc_type = "ANNUAL_REPORT"
        return doc_type, float(parsed.get("confidence", 0.55)), parsed.get("reasoning", "LLM classification")
    except Exception as e:
        logger.warning(f"Classification LLM failed for {filename}: {e}")
        return "ANNUAL_REPORT", 0.40, f"Classification failed — defaulted. Error: {str(e)[:80]}"


def _preview_file(file_path: str, max_chars: int = 2000) -> str:
    try:
        if file_path.lower().endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages = pdf.pages[:3]
                return "\n".join((p.extract_text() or "") for p in pages)[:max_chars]
        elif file_path.lower().endswith((".xlsx", ".xls")):
            import pandas as pd
            df = pd.read_excel(file_path, nrows=25)
            return df.to_string()[:max_chars]
        elif file_path.lower().endswith(".csv"):
            import pandas as pd
            return pd.read_csv(file_path, nrows=25).to_string()[:max_chars]
    except Exception as e:
        logger.warning(f"Preview extraction failed: {e}")
    return ""
