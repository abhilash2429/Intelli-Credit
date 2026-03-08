"""
Helpers to persist analysis run state and audit trail.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db_models import AnalysisRun


def _append_log(existing: Optional[List[Dict[str, Any]]], message: str, step: str) -> List[Dict[str, Any]]:
    logs = list(existing or [])
    logs.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "message": message,
        }
    )
    return logs


def _json_safe(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert nested payload to JSON-safe representation for JSONB columns.
    """
    return json.loads(json.dumps(payload, default=str))


async def create_run(
    db: AsyncSession,
    company_id: str,
    *,
    status: str = "queued",
    step: str = "DOCUMENTS_RECEIVED",
) -> AnalysisRun:
    company_uuid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id
    run = AnalysisRun(
        company_id=company_uuid,
        status=status,
        current_step=step,
        progress_pct=0.0,
        audit_log=_append_log([], "Analysis run created", step),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def get_latest_run(db: AsyncSession, company_id: str) -> Optional[AnalysisRun]:
    company_uuid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id
    query = (
        select(AnalysisRun)
        .where(AnalysisRun.company_id == company_uuid)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def update_run(
    db: AsyncSession,
    run: AnalysisRun,
    *,
    status: Optional[str] = None,
    step: Optional[str] = None,
    progress_pct: Optional[float] = None,
    message: Optional[str] = None,
    result_payload: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> AnalysisRun:
    if status is not None:
        run.status = status
    if step is not None:
        run.current_step = step
    if progress_pct is not None:
        run.progress_pct = progress_pct
    if message is not None and step is not None:
        run.audit_log = _append_log(run.audit_log, message, step)
    if result_payload is not None:
        run.result_payload = _json_safe(result_payload)
    if error_message is not None:
        run.error_message = error_message

    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run
