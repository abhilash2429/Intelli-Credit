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
    raw_text = ""
    try:
        result = await asyncio.to_thread(llm_call, prompt=_PROMPT.format(text=text[:9000]), task="extraction")
        raw_text = result.text if hasattr(result, "text") else str(result)
        parsed = json.loads(re.sub(r"```json|```", "", raw_text).strip())
        if _is_shareholding_payload_usable(parsed):
            return parsed
    except Exception:
        logger.warning("shareholding.llm_parse_failed", file=file_path)

    fallback = _heuristic_shareholding_parse(text)
    fallback["raw_snippet"] = raw_text[:300]
    fallback["fallback_used"] = True
    return fallback


def _is_shareholding_payload_usable(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    holders = payload.get("top_shareholders", []) or []
    if isinstance(holders, list) and len(holders) >= 2:
        return True
    confidence = float(payload.get("extraction_confidence", 0.0) or 0.0)
    return confidence >= 0.6


def _heuristic_shareholding_parse(text: str) -> dict:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln and ln.strip()]
    company_name = _extract_company_name(lines)
    holder_rows = _extract_holder_rows(lines)
    top_shareholders = []
    for idx, (name, pct) in enumerate(holder_rows[:12], start=1):
        top_shareholders.append(
            {
                "rank": idx,
                "name": name,
                "shares": None,
                "percentage": pct,
            }
        )

    promoter_holding_pct = _extract_percent_by_keyword(lines, ("promoter", "promoter group"))
    if promoter_holding_pct is None:
        promoter_holding_pct = round(
            sum(
                pct
                for name, pct in holder_rows
                if any(k in name.lower() for k in ("promoter", "family trust", "holdings"))
            ),
            2,
        )

    total_pledged_pct = _extract_percent_by_keyword(lines, ("pledge", "pledged"))

    red_flags = []
    if total_pledged_pct is not None and total_pledged_pct > 25:
        red_flags.append(f"Promoter pledge is high at {total_pledged_pct:.2f}%")
    if promoter_holding_pct is not None and promoter_holding_pct < 26:
        red_flags.append(f"Promoter holding is low at {promoter_holding_pct:.2f}%")

    return {
        "report_date": None,
        "company_name": company_name,
        "total_shares": None,
        "promoter_holding_pct": float(promoter_holding_pct or 0.0),
        "total_pledged_pct": float(total_pledged_pct or 0.0),
        "categories": [],
        "top_shareholders": top_shareholders,
        "changes_qoq": [],
        "red_flags": red_flags,
        "extraction_confidence": 0.72 if top_shareholders else 0.35,
    }


def _extract_company_name(lines: list[str]) -> str | None:
    for line in lines[:40]:
        if len(line) > 80:
            continue
        low = line.lower()
        if "limited" in low or "pvt" in low or "llp" in low:
            return " ".join(line.split())
    return None


def _extract_holder_rows(lines: list[str]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    seen: set[str] = set()
    for line in lines:
        if "%" not in line:
            continue
        if len(line) > 180:
            continue
        match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", line)
        if not match:
            continue
        pct = float(match.group(1))
        if pct <= 0 or pct > 100:
            continue
        name_part = line[: match.start()].strip(" -:|")
        name_part = re.sub(r"^\d+\s*[\).:-]\s*", "", name_part).strip()
        name_part = re.sub(r"\s{2,}", " ", name_part)
        if len(name_part) < 3:
            continue
        low_name = name_part.lower()
        if any(k in low_name for k in ("category", "shareholding", "promoter holding", "public holding", "total")):
            continue
        if low_name in seen:
            continue
        seen.add(low_name)
        rows.append((name_part, round(pct, 2)))
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def _extract_percent_by_keyword(lines: list[str], keywords: tuple[str, ...]) -> float | None:
    for line in lines:
        low = line.lower()
        if not all(k in low for k in keywords[:1]):
            continue
        match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", line)
        if match:
            return round(float(match.group(1)), 2)
    return None
