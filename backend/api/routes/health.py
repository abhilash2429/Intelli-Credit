"""
Health and readiness endpoints.
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends
from PIL import Image, ImageDraw

from backend.api.deps import RequestContext, get_request_context
from backend.config import settings
from backend.core.structured_logging import get_logger
from backend.schemas.common import build_response

router = APIRouter(prefix="/api/v1", tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health(ctx: RequestContext = Depends(get_request_context)):
    return build_response(
        {
            "service": "intelli-credit-backend",
            "status": "ok",
        },
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.get("/health/integrations")
async def health_integrations(
    live: bool = False,
    ctx: RequestContext = Depends(get_request_context),
):
    """
    Validate key external integrations.
    - live=false: config/readiness checks only
    - live=true: performs lightweight live calls
    """
    report: dict[str, dict] = {
        "cerebras": {"configured": bool(settings.cerebras_api_key), "ok": False},
        "gemini": {"configured": bool(settings.gemini_api_key), "ok": False, "role": "fallback"},
        "tavily": {"configured": bool(settings.tavily_api_key), "ok": False},
        "qwen_vl": {
            "configured": bool(settings.huggingface_api_token or settings.qwen_vl_api_key),
            "ok": False,
        },
        "databricks": {
            "configured": bool(
                settings.databricks_host and settings.databricks_token and settings.databricks_cluster_id
            ),
            "spark_local_mode": bool(settings.spark_local_mode),
            "ok": False,
        },
    }

    if live:
        # Gemini / free-LLM chain check
        try:
            from backend.core.llm.llm_client import llm_call

            llm_resp = llm_call(
                "Reply in one full sentence confirming the CAM chat assistant is available.",
                task="chat_rag",
                max_tokens=40,
            )
            report["gemini"].update(
                {
                    "ok": True,
                    "provider": llm_resp.provider,
                    "model": llm_resp.model_used,
                }
            )
        except Exception as exc:
            report["gemini"]["error"] = str(exc)

        # Tavily check
        try:
            from backend.core.research.tavily_client import TavilyClient

            client = TavilyClient()
            found = client.search("site:example.com", num_results=1)
            report["tavily"].update({"ok": True, "results": len(found)})
        except Exception as exc:
            report["tavily"]["error"] = str(exc)

        # Qwen-VL OCR check
        try:
            from backend.core.ingestion.qwen_vl_ocr import QwenVLOCR

            ocr = QwenVLOCR()
            image = Image.new("RGB", (420, 100), color="white")
            draw = ImageDraw.Draw(image)
            draw.text((10, 35), "CAM OCR TEST 123", fill="black")
            result = ocr.extract_text_from_image(image)
            qwen_remote_ok = result.method.startswith("qwen2.5-vl")
            report["qwen_vl"].update(
                {
                    "ok": qwen_remote_ok,
                    "method": result.method,
                    "confidence": round(float(result.confidence), 3),
                    "fallback_used": not qwen_remote_ok,
                }
            )
        except Exception as exc:
            report["qwen_vl"]["error"] = str(exc)

        # Databricks / Spark check
        try:
            from backend.databricks.spark_session import get_spark

            spark = get_spark()
            rows = spark.sql("SELECT 1 AS integration_ping").collect()
            ping = int(rows[0]["integration_ping"]) if rows else 0
            report["databricks"].update({"ok": ping == 1, "ping": ping})
        except Exception as exc:
            err = str(exc)
            report["databricks"]["error"] = err
            if "required scopes" in err.lower():
                report["databricks"]["hint"] = (
                    "Update DATABRICKS_TOKEN with required Databricks Connect scopes."
                )

    else:
        for key, item in report.items():
            item["ok"] = bool(item.get("configured"))

    overall_ok = all(item.get("ok", False) for item in report.values())
    if not overall_ok:
        logger.warning("health.integrations.partial", report=report, live=live)

    return build_response(
        {
            "live_checks": live,
            "overall_ok": overall_ok,
            "integrations": report,
        },
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )
