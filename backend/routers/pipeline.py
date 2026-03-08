"""
Pipeline router — starts and monitors the LangGraph credit appraisal pipeline.
POST /run-pipeline: Start pipeline for a company.
GET /pipeline-stream/{company_id}: SSE stream of live agent progress logs.
POST /submit-qualitative/{company_id}: Resume pipeline after HITL pause.
"""

import json
import logging
from typing import List, Optional

import asyncio
from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from backend.agents.graph import credit_graph

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run-pipeline")
async def run_pipeline(
    company_id: str = Body(...),
    company_name: str = Body(...),
    document_paths: List[str] = Body(...),
):
    """
    Initialize and start the LangGraph credit appraisal pipeline.

    Args:
        company_id: UUID of the company.
        company_name: Company name.
        document_paths: List of uploaded PDF file paths.

    Returns:
        Dict with run_id and status.
    """
    initial_state = {
        "company_id": company_id,
        "company_name": company_name,
        "uploaded_document_paths": document_paths,
        "documents": [],
        "extracted_financials": {},
        "gst_bank_mismatch_pct": None,
        "circular_trading_detected": False,
        "circular_trading_entities": [],
        "gst_flags": [],
        "news_summary": "",
        "mca_data": {},
        "litigation_data": [],
        "rbi_regulatory_flags": [],
        "promoter_background": {},
        "research_red_flags": [],
        "severity_summary": {},
        "qualitative_notes": None,
        "site_visit_capacity_pct": None,
        "management_assessment": None,
        "hitl_complete": False,
        "rule_based_score": None,
        "ml_stress_probability": None,
        "final_risk_score": None,
        "risk_category": None,
        "shap_values": None,
        "rule_violations": [],
        "risk_strengths": [],
        "critical_hit": False,
        "decision": None,
        "recommended_loan_limit_crore": None,
        "interest_rate_premium_bps": None,
        "decision_rationale": "",
        "cam_text": None,
        "cam_docx_path": None,
        "cam_pdf_path": None,
        "current_node": "start",
        "log": [],
        "errors": [],
    }

    config = {"configurable": {"thread_id": company_id}}

    # Run until HITL interrupt (offloaded to thread to avoid blocking event loop)
    def _run_graph():
        for event in credit_graph.stream(initial_state, config=config):
            pass

    try:
        await asyncio.to_thread(_run_graph)
    except Exception as e:
        logger.error(f"[Pipeline] Error during run: {e}")

    return {"run_id": company_id, "status": "running_until_hitl"}


@router.get("/pipeline-stream/{company_id}")
async def pipeline_stream(company_id: str):
    """
    SSE endpoint — streams log messages to the frontend AgentProgressLog.

    Args:
        company_id: UUID of the company/pipeline run.

    Returns:
        StreamingResponse with text/event-stream media type.
    """
    async def event_generator():
        config = {"configurable": {"thread_id": company_id}}
        sent_count = 0

        while True:
            try:
                current_state = credit_graph.get_state(config)
                logs = current_state.values.get("log", [])

                # Send new log entries
                for log_entry in logs[sent_count:]:
                    yield f"data: {json.dumps({'log': log_entry})}\n\n"
                    sent_count += 1

                current_node = current_state.values.get("current_node", "")

                # Check for HITL pause
                if current_node == "hitl_node" and not current_state.values.get("hitl_complete"):
                    yield f"data: {json.dumps({'status': 'hitl_pause'})}\n\n"

                # Check for completion
                if current_node == "cam_generator" and current_state.values.get("cam_text"):
                    yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                    break

            except Exception as e:
                logger.error(f"[SSE] Error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/submit-qualitative/{company_id}")
async def submit_qualitative(
    company_id: str,
    notes: str = Body(...),
    capacity_pct: Optional[float] = Body(default=None),
    mgmt: Optional[str] = Body(default=None),
):
    """
    Resume pipeline after Credit Officer submits qualitative notes.

    Args:
        company_id: UUID of the company.
        notes: Qualitative observation notes.
        capacity_pct: Factory capacity percentage from site visit.
        mgmt: Management assessment notes.

    Returns:
        Dict with resume status.
    """
    config = {"configurable": {"thread_id": company_id}}

    # Update graph state with qualitative inputs
    credit_graph.update_state(config, {
        "qualitative_notes": notes,
        "site_visit_capacity_pct": capacity_pct,
        "management_assessment": mgmt,
        "hitl_complete": True,
    })

    # Resume graph from HITL node (offloaded to thread to avoid blocking event loop)
    def _resume_graph():
        for event in credit_graph.stream(None, config=config):
            pass

    try:
        await asyncio.to_thread(_resume_graph)
    except Exception as e:
        logger.error(f"[Pipeline] Resume error: {e}")
        return {"status": "error", "detail": str(e)}

    return {"status": "resumed", "company_id": company_id}
