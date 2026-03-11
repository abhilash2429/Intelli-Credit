"""
FastAPI application entrypoint for Intelli-Credit.
Configures CORS, includes all routers, and initializes database + vector store on startup.
"""

import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from backend.database import init_db
from backend.config import settings
from backend.core.structured_logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info("startup.begin")
    await init_db()
    try:
        from backend.vector_store.qdrant_client import init_collections
        init_collections()
    except Exception as e:
        logger.warning("startup.qdrant_init_skipped", error=str(e))

    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.cam_output_dir, exist_ok=True)
    logger.info("startup.complete")
    yield
    # Shutdown (nothing to clean up)
    logger.info("shutdown.complete")


app = FastAPI(
    title="Intelli-Credit API",
    description="AI-powered Credit Appraisal Engine for Indian corporate lending",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = int((perf_counter() - started) * 1000)
        logger.exception(
            "request.error",
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
            processing_time_ms=elapsed,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "data": {
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "Unexpected server error",
                },
                "meta": {
                    "request_id": request_id,
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                    "processing_time_ms": elapsed,
                },
            },
        )

    elapsed = int((perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.complete",
        path=str(request.url.path),
        method=request.method,
        request_id=request_id,
        status_code=response.status_code,
        processing_time_ms=elapsed,
    )
    return response

# CORS — allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (v1 API only — legacy routes removed)
from backend.api.routes import health as health_v1
from backend.api.routes import upload as upload_v1
from backend.api.routes import analysis as analysis_v1
from backend.api.routes import due_diligence as dd_v1
from backend.api.routes import report as report_v1
from backend.api.routes import research as research_v1
from backend.api.routes import chat as chat_v1
from backend.api.routes import loan as loan_v1
from backend.api.routes import classification as classification_v1

app.include_router(health_v1.router)
app.include_router(upload_v1.router)
app.include_router(analysis_v1.router)
app.include_router(dd_v1.router)
app.include_router(report_v1.router)
app.include_router(research_v1.router)
app.include_router(chat_v1.router)
app.include_router(loan_v1.router)
app.include_router(classification_v1.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
