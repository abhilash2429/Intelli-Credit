"""
CAM chat endpoint (v1 envelope + company-scoped path).
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.llm.llm_client import llm_call
from backend.api.deps import RequestContext, get_request_context
from backend.config import settings
from backend.database import get_db
from backend.models.db_models import CamOutput, ChatHistory, ResearchFindingRecord, RiskScore
from backend.schemas.common import build_response
from backend.vector_store.qdrant_client import search_chunks

router = APIRouter(prefix="/api/v1", tags=["chat"])


def _fallback_answer(message: str, context: str) -> str:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    if not lines:
        return (
            "I could not access model reasoning right now, and no CAM context was available. "
            "Please retry in a few seconds."
        )

    keywords = [w.lower() for w in message.split() if len(w) > 3][:6]
    matched = [line for line in lines if any(kw in line.lower() for kw in keywords)]
    selected = matched[:6] if matched else lines[:6]
    bullets = "\n".join(f"- {item[:220]}" for item in selected)
    return (
        "I could not reach the chat model right now. "
        "Using available CAM data, here are the most relevant points:\n"
        f"{bullets}"
    )


async def _build_context(
    db: AsyncSession,
    company_uuid: uuid.UUID,
    vector_chunks: List[dict],
) -> str:
    parts: List[str] = []

    if vector_chunks:
        chunk_text = "\n".join(
            [
                f"[{c.get('doc_type') or 'DOCUMENT'}] {c.get('chunk_text', '')[:400]}"
                for c in vector_chunks
                if c.get("chunk_text")
            ]
        )
        if chunk_text.strip():
            parts.append(f"Retrieved document context:\n{chunk_text}")

    latest_cam = await db.execute(
        select(CamOutput)
        .where(CamOutput.company_id == company_uuid)
        .order_by(CamOutput.created_at.desc())
        .limit(1)
    )
    cam = latest_cam.scalars().first()
    if cam and cam.cam_text:
        parts.append(f"Latest CAM narrative:\n{cam.cam_text[:2500]}")

    latest_risk = await db.execute(
        select(RiskScore)
        .where(RiskScore.company_id == company_uuid)
        .order_by(RiskScore.created_at.desc())
        .limit(1)
    )
    risk = latest_risk.scalars().first()
    if risk:
        parts.append(
            "Latest risk snapshot:\n"
            f"- Final risk score: {risk.final_risk_score}\n"
            f"- Risk category: {risk.risk_category}\n"
            f"- Decision: {risk.decision}\n"
            f"- Recommended limit (crore): {risk.recommended_limit_crore}\n"
            f"- Decision rationale: {risk.decision_rationale or 'Not available'}"
        )

    research = await db.execute(
        select(ResearchFindingRecord)
        .where(ResearchFindingRecord.company_id == company_uuid)
        .order_by(ResearchFindingRecord.created_at.desc())
        .limit(5)
    )
    findings = research.scalars().all()
    if findings:
        research_lines = [
            f"- [{f.severity}] {f.finding_type}: {f.summary[:260]}"
            for f in findings
        ]
        parts.append("Recent research findings:\n" + "\n".join(research_lines))

    context = "\n\n".join(parts).strip()
    return context[:7000]


@router.post("/companies/{company_id}/chat")
async def chat_with_cam_v1(
    company_id: str,
    message: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid company_id") from exc

    try:
        # Keep chat responsive; avoid runtime embedding-model downloads in request path.
        relevant_chunks = search_chunks(
            query=message,
            company_id=company_id,
            top_k=5,
            use_semantic=False,
        )
    except Exception:
        relevant_chunks = []

    context = await _build_context(db, company_uuid, relevant_chunks)
    if not context.strip():
        context = "No document context available for this company."

    prompt = f"""You are a credit analysis assistant for an Indian bank.
Answer questions using only the provided company context.
If data is unavailable, explicitly say it is unavailable in the uploaded documents and research.
Use Indian lending terms where relevant (DSCR, MPBF, NPA, CIRP, DRT, GSTR-3B).

COMPANY CONTEXT:
{context}

QUESTION:
{message}
"""

    try:
        response = llm_call(prompt, task="chat_rag", max_tokens=900)
        answer = response.text
        model_info = {
            "provider": response.provider,
            "model": response.model_used,
            "fallback_triggered": response.fallback_triggered,
            "latency_ms": response.latency_ms,
            "gemini_enabled": bool(settings.gemini_api_key),
        }
    except Exception as exc:
        answer = _fallback_answer(message, context)
        model_info = {"error": str(exc)}

    try:
        db.add(
            ChatHistory(
                id=uuid.uuid4(),
                company_id=company_uuid,
                message=message,
                response=answer,
                sources=list({c.get("doc_type", "") for c in relevant_chunks if c.get("doc_type")}),
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()

    return build_response(
        {
            "response": answer,
            "sources": [c.get("doc_type", "") for c in relevant_chunks if c.get("doc_type")],
            "model_info": model_info,
        },
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )
