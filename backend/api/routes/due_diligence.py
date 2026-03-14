"""
Due diligence intake endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.core.research.due_diligence_ai import DueDiligenceAnalyzer
from backend.database import get_db
from backend.models.db_models import Company, DueDiligenceRecord
from backend.schemas.common import build_response
from backend.schemas.credit import DueDiligenceInput

router = APIRouter(prefix="/api/v1", tags=["due-diligence"])
_analyzer = DueDiligenceAnalyzer()


def _build_enriched_notes(payload: DueDiligenceInput) -> str:
    """
    Combine free text with structured due-diligence fields so heuristic/LLM
    analysis can always reflect borrower and officer inputs.
    """
    parts = [
        payload.free_text_notes or "",
        f"capacity_utilization_percent: {payload.capacity_utilization_percent}",
        f"inventory_levels: {payload.inventory_levels}",
        f"management_cooperation: {payload.management_cooperation}",
        f"management_interview_rating: {payload.management_interview_rating}",
        f"finance_officer_name: {payload.borrower_finance_officer_name}",
        f"business_highlights: {payload.borrower_business_highlights}",
        f"major_customers: {payload.borrower_major_customers}",
        f"contingent_liabilities: {payload.borrower_contingent_liabilities}",
        f"planned_capex: {payload.borrower_planned_capex}",
        f"disclosed_risks: {payload.borrower_disclosed_risks}",
    ]
    return "\n".join(str(p) for p in parts if p not in (None, "", "None"))


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

    enriched_notes = _build_enriched_notes(payload)
    insight = await _analyzer.analyze(company.name, enriched_notes)  # type: ignore[reportArgumentType]
    payload_json = payload.model_dump(mode="json")
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
