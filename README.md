# Intelli-Credit (Advanced Prototype)

AI-powered corporate credit appraisal engine for Indian lending workflows.

This repository now contains:
- A production-style FastAPI backend with `/api/v1` endpoints
- End-to-end ingestion -> research -> ML scoring -> CAM generation pipeline
- Structured JSON response envelope + request tracing
- Advanced dashboard pages and visualizations in frontend
- Dockerized local stack (Postgres, Qdrant, Redis, Backend, Worker, Frontend)
- Sample data generation for **Vardhman Agri Processing Pvt. Ltd.**

## What Is Implemented

### Backend
- `backend/core/ingestion`
  - `pdf_parser.py`: fitz + pdfplumber + **Qwen2.5-VL OCR** fallback
  - `gst_parser.py`: GSTR parsing + ITC mismatch analyzer
  - `bank_statement.py`: banking pattern/anomaly extraction
  - `itr_parser.py`: ITR JSON parser
  - `cross_validator.py`: cross-source consistency report
- `backend/core/research`
  - `web_agent.py`: autonomous research orchestration with `mock` + `live` mode
  - `firecrawl_client.py`: Firecrawl SDK wrapper with retries
  - `finding_extractor.py`: LLM-powered finding extraction (Hugging Face free model default)
  - `search_strategies.py`: India-focused research query templates
  - `research_to_delta.py`: CAM research narrative synthesis
  - MCA, eCourts, news and promoter intelligence modules
  - Due diligence note intelligence parser (`due_diligence_ai.py`)
- `backend/databricks`
  - `spark_session.py`: local Spark/Delta or Databricks Connect
  - `delta_writer.py`: Delta writes/upserts
  - `schema_registry.py`: research/ingestion/cross-validation table schemas
  - `pipeline_sink.py`: persists pipeline outputs to Delta Lake
- `backend/core/ml`
  - feature engineering, hard rejection rules, XGBoost scoring
  - risk premium logic + explainability narrative layer
- `backend/core/report`
  - 9-section CAM `.docx` generator with banking layout
- `backend/api/routes`
  - `/api/v1/companies`, `/documents`, `/analyze`, `/status`, `/results`
  - `/dd-input`, `/research`, `/explain`, `/report`, `/report/pdf`, `/health`
  - `/companies/{id}/chat` for CAM chat (Gemini-first)
- `backend/tasks`
  - Celery app + analysis task wrapper
- `backend/core/prefect_flow.py`
  - Prefect 2.x flow wrapper

## Required API Keys and Secrets

Keep the following in `.env`:

- `CEREBRAS_API_KEY`: Required for all text LLM tasks.
- `CEREBRAS_MODEL`: Cerebras model name (default: `qwen-3-235b-a22b-instruct-2507`).
- `DATABRICKS_HOST`: Databricks workspace URL.
- `DATABRICKS_TOKEN`: Databricks PAT.
- `DATABRICKS_CLUSTER_ID`: Target Databricks cluster.
- `TAVILY_API_KEY` and/or `FIRECRAWL_API_KEY`: Required for live web search mode.

Optional fallbacks:

- `HUGGINGFACE_API_TOKEN` (for Qwen2.5-VL OCR path only)

## Pipeline Structure

This implementation follows the target structure:

1. Multi-Source Data Input
2. Document Processing Layer (PyMuPDF/pdfplumber + Qwen2.5-VL OCR via Hugging Face)
3. Structured Knowledge Store (PostgreSQL + Qdrant + Delta Lake on Databricks/local Delta)
4. Web Research Agent (Firecrawl live crawling, extraction, scoring)
5. Risk Scoring Engine (rules + ML + explainability)
6. CAM Generator (template-driven `.docx` with research narrative)
7. Credit Officer Portal (upload, review, explainability, report download)

## Deliverables Coverage (Hackathon 3 Pillars)

1. Data Ingestor (multi-format + high-latency pipeline):
   - PDF/DOCX/CSV/XML/XLS/XLSX/JPEG/PNG upload support
   - OCR stack: `pdfplumber` -> `Qwen2.5-VL (HF)` -> `Tesseract` fallback
   - GST/Bank/ITR parsing + cross-validation + circular-trade heuristics
   - Delta/Databricks sink via `backend/databricks/*`

2. Research Agent ("Digital Credit Manager"):
   - Firecrawl web scraping/crawling in `RESEARCH_MODE=live`
   - MCA/eCourts/news/promoter checks + finding extraction/scoring
   - Credit officer due-diligence input route (`/api/v1/companies/{id}/dd-input`)
   - Human-in-the-loop integration into final score and CAM narrative

3. Recommendation Engine:
   - Explainable scoring: Rules + ML calibration + SHAP-style factors
   - Decision output: recommendation, limit, pricing premium, rationale
   - CAM generation to Word/PDF and Gemini-first CAM chat
   - API: `/api/v1/companies/{id}/report`, `/api/v1/companies/{id}/report/pdf`,
     `/api/v1/companies/{id}/chat`

### Frontend
- Existing Next.js app upgraded with advanced pages/components:
  - upload pipeline view
  - due diligence portal with real-time AI preview
  - analysis results page (Five Cs radar, SHAP bars, timeline, research feed)
  - explainability page with India-context glossary
  - stress test panel + fraud fingerprint graph (D3)

### Data + Tests
- `scripts/generate_sample_data.py` creates:
  - `data/sample_documents/sample_gstr3b.json`
  - `data/sample_documents/sample_bank_statement.csv`
  - `data/sample_documents/sample_annual_report.pdf`
  - `data/sample_documents/sample_itr.json`
  - `data/sample_documents/sample_research_findings.json`
- Backend tests under `tests/backend/` (5 passing tests)

## Architecture

Detailed architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)

## Quick Start

### 1) Environment
```bash
cp .env.example .env
```

### 2) Start infra
```bash
docker run -d --name intelli_postgres -e POSTGRES_DB=intellicredit -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16
docker run -d --name intelli_qdrant -p 6333:6333 qdrant/qdrant:latest

```

### 3) Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4) Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`  
API docs: `http://localhost:8000/docs`

## Docker Compose

```bash
docker compose up --build
```

Services:
- Postgres: `5432`
- Qdrant: `6333`
- Redis: `6379`
- Backend: `8000`
- Celery worker: background
- Frontend: `3000`

## Generate Demo Data

```bash
source .venv/bin/activate
python scripts/generate_sample_data.py
```

## API Surface (`/api/v1`)

- `POST /api/v1/companies`
- `POST /api/v1/companies/{id}/documents` (supports PDF/DOCX/CSV/XML/XLS/XLSX/JPEG/PNG)
- `POST /api/v1/companies/{id}/analyze`
- `GET /api/v1/companies/{id}/status` (SSE)
- `POST /api/v1/companies/{id}/dd-input`
- `GET /api/v1/companies/{id}/results`
- `GET /api/v1/companies/{id}/report`
- `GET /api/v1/companies/{id}/explain`
- `GET /api/v1/companies/{id}/research`
- `GET /api/v1/health`

All `/api/v1` responses use:
```json
{
  "status": "success|error|processing",
  "data": {},
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601",
    "processing_time_ms": 0
  }
}
```

## Run Tests

```bash
source .venv/bin/activate
pytest -q tests/backend
```

## Notes

- Research layer supports:
  - `RESEARCH_MODE=mock` (default deterministic mode)
  - `RESEARCH_MODE=live` (Tavily/Firecrawl search + Firecrawl/Crawl4AI extraction, capped to 20 live web outputs/run)
- Delta persistence is enabled automatically when Spark + Delta dependencies are available; set `SPARK_LOCAL_MODE=false` to use Databricks Connect.
- Existing frontend remains Next.js (already integrated and running). The advanced Vite-style dashboard requirements are implemented functionally in current app pages/components.
