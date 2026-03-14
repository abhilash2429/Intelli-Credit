"""
Dynamic Schema Extractor.
Given a user-defined schema + file, extracts data into that exact schema.
Used when credit officer customises the output fields.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = """\
Extract data from this document into the user-defined schema below.

SCHEMA (extract ONLY these fields, using exact field names and types):
{schema_description}

RULES:
- Output ONLY a flat JSON object with the field names above as keys.
- Use null for any field not found in the document.
- For float fields: output numbers, not strings. No commas in numbers.
- For date fields: use YYYY-MM-DD format.
- Do NOT add extra fields. Do NOT rename fields.
- Do NOT invent data.

Document content:
{content}
"""


async def extract_with_schema(file_path: str, doc_type: str, schema: dict) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.core.llm.llm_client import llm_call

    fields = schema.get("fields", [])
    if not fields:
        return {"error": "empty_schema"}

    schema_desc = "\n".join(
        f"  - {f['name']} ({f['type']}): {f.get('description', '')}"
        for f in fields
    )
    content = _extract_text(file_path)
    prompt = _PROMPT.format(schema_description=schema_desc, content=content[:10000])

    result = await asyncio.to_thread(llm_call, prompt=prompt, task="extraction")
    raw_text = result.text if hasattr(result, "text") else str(result)
    try:
        return json.loads(re.sub(r"```json|```", "", raw_text).strip())
    except Exception:
        return {"error": "extraction_failed", "raw_snippet": raw_text[:300]}
