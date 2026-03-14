"""
Research findings retrieval endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.database import get_db
from backend.models.db_models import ResearchFindingRecord
from backend.schemas.common import build_response

router = APIRouter(prefix="/api/v1", tags=["research"])


@router.get("/companies/{company_id}/research")
async def get_research_findings(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid company_id") from exc

    result = await db.execute(
        select(ResearchFindingRecord)
        .where(ResearchFindingRecord.company_id == company_uuid)
        .order_by(ResearchFindingRecord.created_at.desc())
    )
    rows = result.scalars().all()
    findings = [
        {
            "source_url": r.source_url,
            "source_name": r.source_name,
            "finding_type": r.finding_type,
            "summary": r.summary,
            "severity": r.severity,
            "confidence": r.confidence,
            "date_of_finding": r.date_of_finding.isoformat() if r.date_of_finding else None,  # type: ignore[reportGeneralTypeIssues]
            "raw_snippet": r.raw_snippet,
        }
        for r in rows
    ]
    return build_response(
        findings,
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )

