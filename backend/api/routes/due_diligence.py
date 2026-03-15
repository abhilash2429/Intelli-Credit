"""
Due diligence intake endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.core.research.due_diligence_ai import DueDiligenceAnalyzer
from backend.database import get_db
from backend.models.db_models import Company, DueDiligenceRecord
from backend.schemas.common import build_response
from backend.schemas.credit import DueDiligenceInput

router = APIRouter(prefix="/api/v1", tags=["due-diligence"])
_analyzer = DueDiligenceAnalyzer()
BORROWER_CONTEXT_FIELDS = (
    "borrower_finance_officer_name",
    "borrower_finance_officer_role",
    "borrower_finance_officer_email",
    "borrower_finance_officer_phone",
    "borrower_business_highlights",
    "borrower_major_customers",
    "borrower_contingent_liabilities",
    "borrower_planned_capex",
    "borrower_disclosed_risks",
    "key_management_persons",
)


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _get_field(payload: DueDiligenceInput | dict, key: str) -> object:
    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)


def _build_enriched_notes(payload: DueDiligenceInput | dict) -> str:
    """
    Combine free text with structured due-diligence fields so heuristic/LLM
    analysis can always reflect borrower and officer inputs.
    """
    parts = [
        str(_get_field(payload, "free_text_notes") or ""),
        f"capacity_utilization_percent: {_get_field(payload, 'capacity_utilization_percent')}",
        f"inventory_levels: {_get_field(payload, 'inventory_levels')}",
        f"management_cooperation: {_get_field(payload, 'management_cooperation')}",
        f"management_interview_rating: {_get_field(payload, 'management_interview_rating')}",
        f"finance_officer_name: {_get_field(payload, 'borrower_finance_officer_name')}",
        f"business_highlights: {_get_field(payload, 'borrower_business_highlights')}",
        f"major_customers: {_get_field(payload, 'borrower_major_customers')}",
        f"contingent_liabilities: {_get_field(payload, 'borrower_contingent_liabilities')}",
        f"planned_capex: {_get_field(payload, 'borrower_planned_capex')}",
        f"disclosed_risks: {_get_field(payload, 'borrower_disclosed_risks')}",
    ]
    return "\n".join(str(p) for p in parts if p not in (None, "", "None"))


def _merge_with_previous_payload(current: dict, previous: dict) -> dict:
    merged = dict(current)
    for key in BORROWER_CONTEXT_FIELDS:
        if _is_blank(merged.get(key)) and not _is_blank(previous.get(key)):
            merged[key] = previous.get(key)
    return merged


@router.post("/due-diligence/preview")
async def preview_due_diligence(
    payload: dict,
    ctx: RequestContext = Depends(get_request_context),
):
    notes = str(payload.get("free_text_notes", ""))
    company_name = str(payload.get("company_name", "Unknown Company"))
    insight = await _analyzer.analyze(company_name, notes)
    return build_response(
        insight.model_dump(),
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.post("/companies/{company_id}/dd-input")
async def submit_due_diligence(
    company_id: str,
    payload: DueDiligenceInput,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid company_id") from exc

    company = await db.get(Company, company_uuid)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    latest_result = await db.execute(
        select(DueDiligenceRecord)
        .where(DueDiligenceRecord.company_id == company_uuid)
        .order_by(DueDiligenceRecord.created_at.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    previous_payload = latest.payload if latest and isinstance(latest.payload, dict) else {}
    payload_json = _merge_with_previous_payload(payload.model_dump(mode="json"), previous_payload)

    enriched_notes = _build_enriched_notes(payload_json)
    insight = await _analyzer.analyze(company.name, enriched_notes)  # type: ignore[reportArgumentType]
    insight_json = insight.model_dump(mode="json")

    record = DueDiligenceRecord(
        id=uuid.uuid4(),
        company_id=company_uuid,
        payload=payload_json,
        llm_insight=insight_json,
    )
    db.add(record)
    await db.commit()

    return build_response(
        {
            "company_id": company_id,
            "due_diligence": payload_json,
            "ai_insight": insight_json,
        },
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )
