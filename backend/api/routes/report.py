"""
CAM report download endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.database import get_db
from backend.models.db_models import CamOutput
from backend.schemas.common import build_response

router = APIRouter(prefix="/api/v1", tags=["report"])


@router.get("/companies/{company_id}/report")
async def download_report(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid company_id") from exc

    result = await db.execute(
        select(CamOutput)
        .where(CamOutput.company_id == company_uuid)
        .order_by(CamOutput.created_at.desc())
        .limit(1)
    )
    cam = result.scalars().first()
    if not cam or not cam.docx_path:  # type: ignore[reportGeneralTypeIssues]
        return build_response(
            {
                "company_id": company_id,
                "status": "processing",
                "message": "CAM DOCX report is still being generated.",
            },
            status="processing",
            request_id=ctx.request_id,
            started_at=ctx.started_at,
        )
    return FileResponse(
        cam.docx_path,  # type: ignore[reportArgumentType]
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="credit_appraisal_memo.docx",
    )


@router.get("/companies/{company_id}/report/pdf")
async def download_report_pdf(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid company_id") from exc

    result = await db.execute(
        select(CamOutput)
        .where(CamOutput.company_id == company_uuid)
        .order_by(CamOutput.created_at.desc())
        .limit(1)
    )
    cam = result.scalars().first()
    if not cam or not cam.pdf_path:  # type: ignore[reportGeneralTypeIssues]
        return build_response(
            {
                "company_id": company_id,
                "status": "processing",
                "message": "CAM PDF report is still being generated.",
            },
            status="processing",
            request_id=ctx.request_id,
            started_at=ctx.started_at,
        )
    return FileResponse(
        cam.pdf_path,  # type: ignore[reportArgumentType]
        media_type="application/pdf",
        filename="credit_appraisal_memo.pdf",
    )
