"""
Document Classification HITL API.
Exposes auto-classification results and allows credit officer to
approve / reject / override each classification, configure schemas,
and trigger re-extraction.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.database import get_db
from backend.models.db_models import DocumentClassification, Document
from backend.schemas.common import build_response

router = APIRouter(
    prefix="/api/v1/companies/{company_id}/classifications",
    tags=["classification"],
)

VALID_DOC_TYPES = {"ALM", "SHAREHOLDING", "BORROWING_PROFILE", "ANNUAL_REPORT", "PORTFOLIO"}


def _clf_to_dict(clf: DocumentClassification, filename: str = "") -> dict[str, Any]:
    return {
        "classification_id": str(clf.id),
        "document_id": str(clf.document_id),
        "filename": filename,
        "auto_type": clf.auto_type,
        "auto_confidence": clf.auto_confidence,
        "auto_reasoning": clf.auto_reasoning,
        "effective_type": clf.human_type_override or clf.auto_type,
        "human_approved": clf.human_approved,
        "human_type_override": clf.human_type_override,
        "human_notes": clf.human_notes,
        "reviewed_at": clf.reviewed_at.isoformat() if clf.reviewed_at else None,  # type: ignore[reportGeneralTypeIssues]
        "custom_schema": clf.custom_schema,
        "has_extracted_data": clf.extracted_data is not None,
    }


@router.get("")
async def list_classifications(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    """Get all classifications for company documents."""
    result = await db.execute(
        select(DocumentClassification)
        .where(DocumentClassification.company_id == uuid.UUID(company_id))
        .order_by(DocumentClassification.created_at.asc())
    )
    clfs = result.scalars().all()

    items = []
    for clf in clfs:
        doc = await db.get(Document, clf.document_id)
        filename = doc.file_path.split("/")[-1] if doc else "unknown"
        items.append(_clf_to_dict(clf, filename))

    total = len(items)
    approved = sum(1 for i in items if i["human_approved"] is True)
    pending = sum(1 for i in items if i["human_approved"] is None)
    rejected = sum(1 for i in items if i["human_approved"] is False)

    return build_response(
        {
            "classifications": items,
            "summary": {
                "total": total,
                "approved": approved,
                "pending": pending,
                "rejected": rejected,
                "all_reviewed": pending == 0,
            },
        },
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.patch("/{classification_id}")
async def update_classification(
    company_id: str,
    classification_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    """
    HITL endpoint for classification review.
    Actions: approve, reject, override, set_schema
    """
    clf = await db.get(DocumentClassification, uuid.UUID(classification_id))
    if not clf or str(clf.company_id) != company_id:
        raise HTTPException(status_code=404, detail="Classification not found")

    action = payload.get("action")
    now = datetime.now(timezone.utc)

    if action == "approve":
        clf.human_approved = True  # type: ignore[reportAttributeAccessIssue]
        clf.reviewed_at = now  # type: ignore[reportAttributeAccessIssue]
    elif action == "reject":
        clf.human_approved = False  # type: ignore[reportAttributeAccessIssue]
        clf.reviewed_at = now  # type: ignore[reportAttributeAccessIssue]
    elif action == "override":
        new_type = payload.get("new_type", "").upper()
        if new_type not in VALID_DOC_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid doc type. Must be one of: {VALID_DOC_TYPES}")
        clf.human_type_override = new_type
        clf.human_approved = True  # type: ignore[reportAttributeAccessIssue]
        clf.human_notes = payload.get("notes")  # type: ignore[reportAttributeAccessIssue]
        clf.reviewed_at = now  # type: ignore[reportAttributeAccessIssue]
    elif action == "set_schema":
        schema = payload.get("schema")
        if not schema or not schema.get("fields"):
            raise HTTPException(status_code=400, detail="Schema must have 'fields' list")
        clf.custom_schema = schema
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action!r}")

    await db.commit()
    doc = await db.get(Document, clf.document_id)
    filename = doc.file_path.split("/")[-1] if doc else ""
    return build_response(
        _clf_to_dict(clf, filename),
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.post("/{classification_id}/extract")
async def trigger_extraction(
    company_id: str,
    classification_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    """Trigger (re-)extraction using custom_schema."""
    clf = await db.get(DocumentClassification, uuid.UUID(classification_id))
    if not clf or str(clf.company_id) != company_id:
        raise HTTPException(status_code=404, detail="Classification not found")
    if not clf.custom_schema:  # type: ignore[reportGeneralTypeIssues]
        raise HTTPException(status_code=400, detail="Set a custom schema first via set_schema action")
    if clf.human_approved is False:
        raise HTTPException(status_code=400, detail="Cannot extract from a rejected document")

    doc = await db.get(Document, clf.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document file not found")

    from backend.core.ingestion.schema_extractor import extract_with_schema
    effective_type = clf.human_type_override or clf.auto_type
    extracted = await extract_with_schema(
        file_path=doc.file_path,  # type: ignore[reportArgumentType]
        doc_type=effective_type,  # type: ignore[reportArgumentType]
        schema=clf.custom_schema,  # type: ignore[reportArgumentType]
    )
    clf.extracted_data = extracted  # type: ignore[reportAttributeAccessIssue]
    await db.commit()

    return build_response(
        {"classification_id": classification_id, "extracted_data": extracted},
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )
