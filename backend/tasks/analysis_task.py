"""
Celery task wrapper for the Intelli-Credit analysis pipeline.
"""

from __future__ import annotations

import asyncio

from backend.core.pipeline_service import IntelliCreditPipeline
from backend.database import AsyncSessionLocal
from backend.tasks.celery_app import celery_app

pipeline = IntelliCreditPipeline()


@celery_app.task(name="intelli_credit.run_analysis")
def run_analysis_task(company_id: str) -> dict:
    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            result = await pipeline.run_analysis(db, company_id)
            return result

    # Explicit new event loop avoids RuntimeError when a loop is already running
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


