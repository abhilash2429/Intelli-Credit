# Intelli-Credit: AI-Powered Credit Appraisal Engine
## Complete Agent Blueprint — Zero to Hero

> **Hackathon:** IIT Hyderabad × Vivriti Capital — "Intelli-Credit" Challenge  
> **Deadline Round 1:** 10 March 2026  
> **Final Demo:** 22 March 2026, IIT Hyderabad  

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Full System Architecture](#2-full-system-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Tech Stack & Dependencies](#4-tech-stack--dependencies)
5. [Environment Setup](#5-environment-setup)
6. [Module 1: Data Ingestion Pipeline](#6-module-1-data-ingestion-pipeline)
7. [Module 2: LangGraph Agent Orchestration](#7-module-2-langgraph-agent-orchestration)
8. [Module 3: Web Research Agent](#8-module-3-web-research-agent)
9. [Module 4: Hybrid Risk Scoring Engine](#9-module-4-hybrid-risk-scoring-engine)
10. [Module 5: CAM Generator](#10-module-5-cam-generator)
11. [Module 6: FastAPI Backend](#11-module-6-fastapi-backend)
12. [Module 7: Next.js Frontend Portal](#12-module-7-nextjs-frontend-portal)
13. [Database Schema](#13-database-schema)
14. [Qdrant Vector Store Setup](#14-qdrant-vector-store-setup)
15. [End-to-End Data Flow](#15-end-to-end-data-flow)
16. [Indian Context: Key Rules & Domain Logic](#16-indian-context-key-rules--domain-logic)
17. [Testing Strategy](#17-testing-strategy)
18. [Demo Script for Judges](#18-demo-script-for-judges)

---

## 1. Project Overview

### What We Are Building
An end-to-end AI-powered **Credit Appraisal Engine** called **Intelli-Credit** that:
1. Ingests multi-format documents (scanned PDFs, GST filings, bank statements, annual reports)
2. Runs autonomous web research on the company, its promoters, sector, and legal history
3. Applies a three-layer hybrid risk scoring engine
4. Generates a professional Credit Appraisal Memo (CAM) in PDF and Word format
5. Provides a Credit Officer portal for human-in-the-loop review and qualitative input

### Core Design Philosophy
- **LLM narrates, rules govern, ML calibrates** — no black boxes
- **Sarvam Vision** handles all Indic-language OCR (22 Indian languages)
- **LangGraph** maintains stateful pipeline across all agents
- **Every decision is traceable** to a specific data source or rule

### Winning Differentiators
- Circular trading detection via GST graph analysis
- 22-language Indian document support via Sarvam Vision
- SHAP-based explainability chart for every credit decision
- Real-time agent progress streaming to the Credit Officer portal
- "Chat with the CAM" — ask why any flag was raised

---

## 2. Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND                             │
│  Marketing: / and /about                                            │
│  App: /app/start → /app/upload → /app/notes → /app/pipeline        │
│       → /app/score /results /explain /chat /cam                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST + SSE (streaming)
┌────────────────────────────▼────────────────────────────────────────┐
│                      FASTAPI BACKEND                                │
│  Primary APIs: /api/v1/*                                            │
│  Compatibility APIs: /ingest /run-pipeline /score /cam /chat        │
└───┬────────────────────────────────────────────────────────────┬────┘
    │                                                            │
┌───▼─────────────────────────────────┐        ┌───────────────▼────┐
│   Core Pipeline (active runtime)    │        │    POSTGRESQL DB    │
│   backend/core/pipeline_service.py  │        │  companies          │
│                                     │        │  documents          │
│  OCR: fitz → pdfplumber → Qwen VL   │        │  due_diligence_*    │
│  GST/Bank/ITR cross-validation      │        │  analysis_runs      │
│  Research: Firecrawl + scrapers     │        │  research_findings  │
│  Risk model + explainability        │        │  risk_scores        │
│  CAM generation (.docx; .pdf route) │        │  cam_outputs        │
└───┬─────────────────────────────────┘        └─────────────────────┘
    │
┌───▼─────────────────────────────────┐        ┌──────────────────────┐
│  LangGraph pipeline (legacy path)   │        │        QDRANT        │
│  backend/agents/* (still available) │        │  document_chunks     │
└──────────────────────────────────────┘        │  research_chunks     │
                                                └──────────────────────┘
```

---

## 3. Repository Structure

```
IITHYD_Argus_v1/
├── backend/
│   ├── main.py                        # FastAPI entrypoint
│   ├── config.py                      # All env vars and constants
│   ├── database.py                    # PostgreSQL connection (SQLAlchemy)
│   ├── api/
│   │   └── routes/                    # Primary /api/v1 endpoints
│   │       ├── upload.py              # companies + document upload
│   │       ├── analysis.py            # analyze, status SSE, results, explain
│   │       ├── due_diligence.py       # DD preview + submission
│   │       ├── research.py            # research findings
│   │       ├── report.py              # CAM docx/pdf downloads
│   │       ├── chat.py                # company-scoped CAM chat
│   │       └── health.py              # health + integration checks
│   ├── core/
│   │   ├── pipeline_service.py        # Active orchestrator
│   │   ├── ingestion/                 # fitz/pdfplumber/Qwen OCR + GST/bank/ITR
│   │   ├── research/                  # Firecrawl + MCA/eCourts/news + DD AI
│   │   ├── ml/                        # features + scorer + explainer
│   │   └── report/                    # CAM generator
│   ├── models/
│   │   └── db_models.py               # SQLAlchemy ORM models
│   ├── agents/
│   │   ├── graph.py                   # LangGraph graph definition (legacy path)
│   │   ├── state.py                   # LangGraph shared state schema
│   │   ├── nodes/
│   │   │   ├── document_router.py     # Node 1: classify document type
│   │   │   ├── ingestion_agent.py     # Node 2: OCR + extraction (Qwen fallback)
│   │   │   ├── gst_reconciler.py      # Node 3: GST vs bank cross-check
│   │   │   ├── research_agent.py      # Node 4: web research
│   │   │   ├── hitl_node.py           # Node 5: human-in-the-loop pause
│   │   │   ├── risk_scorer.py         # Node 6: hybrid scoring
│   │   │   └── cam_generator.py       # Node 7: CAM generation
│   │   └── tools/
│   │       ├── sarvam_tool.py         # Sarvam Vision API wrapper (optional)
│   │       ├── serper_tool.py         # Google Search via Serper
│   │       ├── mca_scraper.py         # MCA21 portal scraper
│   │       ├── ecourts_scraper.py     # eCourts portal scraper
│   │       ├── rbi_scraper.py         # RBI/SEBI regulatory scraper
│   │       └── circular_trade.py      # NetworkX graph fraud detector
│   ├── databricks/                    # Spark/Delta sink integration
│   ├── schemas/                       # Pydantic API/domain schemas
│   ├── tasks/                         # Celery worker tasks
│   ├── scoring/
│   │   ├── rules_engine.py            # Layer 1: deterministic rules
│   │   ├── ml_calibrator.py           # Layer 2: XGBoost model
│   │   ├── shap_explainer.py          # SHAP feature importance
│   │   └── score_blender.py           # Final score fusion
│   ├── cam/
│   │   ├── cam_template.py            # Five Cs structure + prompts
│   │   ├── docx_generator.py          # python-docx Word output
│   │   └── pdf_generator.py           # ReportLab PDF output
│   ├── vector_store/
│   │   └── qdrant_client.py           # Qdrant setup + upsert + query
│   ├── routers/
│   │   ├── ingest.py                  # POST /ingest
│   │   ├── pipeline.py                # POST /run-pipeline + SSE stream
│   │   ├── qualitative.py             # POST /qualitative
│   │   ├── score.py                   # GET /score/{company_id}
│   │   ├── cam.py                     # GET /cam/{company_id}
│   │   └── chat.py                    # POST /chat (RAG over CAM)
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Marketing landing
│   │   ├── about/page.tsx             # Marketing about page
│   │   └── app/                       # Product app routes
│   │       ├── start/page.tsx         # Company/session start
│   │       ├── upload/page.tsx        # Document + optional borrower input
│   │       ├── notes/page.tsx         # Credit officer due diligence
│   │       ├── pipeline/page.tsx      # Live SSE pipeline progress
│   │       ├── score/page.tsx         # Score summary + SHAP
│   │       ├── results/page.tsx       # Advanced dashboard
│   │       ├── explain/page.tsx       # Explainability view
│   │       ├── chat/page.tsx          # Chat with CAM
│   │       └── cam/page.tsx           # CAM preview + download
│   ├── components/
│   │   ├── UploadZone.tsx
│   │   ├── AgentProgressLog.tsx       # SSE streaming log
│   │   ├── ShapChart.tsx              # Recharts horizontal bar
│   │   ├── RiskGauge.tsx              # Circular risk meter
│   │   ├── FiveCsRadar.tsx
│   │   ├── TimelineView.tsx
│   │   ├── ResearchFeed.tsx
│   │   ├── StressTestPanel.tsx
│   │   ├── FraudGraph.tsx
│   │   ├── CamPreview.tsx
│   │   └── ChatInterface.tsx
│   ├── lib/
│   │   └── api.ts                     # API client
│   ├── store/
│   │   └── analysisStore.ts           # Zustand persisted workflow state
│   └── package.json
├── ml/
│   ├── train_model.py                 # XGBoost training script
│   ├── features.py                    # Feature engineering
│   ├── synthetic_data.py              # Generate mock training data
│   └── model/
│       └── xgb_credit_model.pkl       # Trained model artifact
├── data/
│   └── sample/                        # Sample Indian company docs
├── docker-compose.yml                 # PostgreSQL + Qdrant + Backend + Frontend
└── README.md
```

---

## 4. Tech Stack & Dependencies

### Backend (`backend/requirements.txt`)
```
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.0
pydantic==2.7.0
pydantic-settings==2.2.0

# LangGraph + LangChain
langgraph==0.2.0
langchain==0.2.17
langchain-community==0.2.17

# PDF Processing
pdfplumber==0.11.0
pymupdf==1.24.0
pytesseract==0.3.13
Pillow==10.4.0
pdf2image==1.17.0

# HTTP + Scraping
httpx==0.27.0
beautifulsoup4==4.12.0
playwright==1.45.0
requests==2.32.0

# Database
sqlalchemy==2.0.0
asyncpg==0.29.0
alembic==1.13.0
psycopg2-binary==2.9.9
redis==5.0.8

# Vector Store
qdrant-client==1.11.0
sentence-transformers==3.1.0

# ML + Explainability
xgboost==2.1.0
lightgbm==4.5.0
shap==0.46.0
scikit-learn==1.5.0
pandas==2.2.0
numpy==1.26.0
networkx==3.3.0
spacy==3.7.5
transformers==4.44.2

# Document Generation
python-docx==1.1.0
reportlab==4.2.0

# LLM/Providers
google-generativeai==0.8.0
openai==1.30.0
huggingface-hub==0.33.2
anthropic==0.28.0

# Utilities
python-multipart==0.0.9
aiofiles==24.1.0
structlog==24.4.0

# Orchestration / Big data / Research
celery==5.4.0
prefect==2.20.3
pyspark==3.5.2
delta-spark==3.2.0
databricks-connect==14.3.0
firecrawl-py==4.18.0
tenacity==8.3.0
```

### Frontend (`frontend/package.json` deps)
```json
{
  "dependencies": {
    "next": "^14.2.35",
    "react": "^18",
    "react-dom": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.4",
    "recharts": "^2.12",
    "lucide-react": "^0.400",
    "axios": "^1.7",
    "@tanstack/react-query": "^5.59.0",
    "zustand": "^4.5.5",
    "d3": "^7.9.0",
    "react-pdf": "^9.2.1",
    "react-dropzone": "^14.2",
    "react-markdown": "^9.0",
    "eventsource-parser": "^2.0"
  }
}
```

---

## 5. Environment Setup

### `.env` file (backend)
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/intellicredit
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_DOCUMENTS=document_chunks
QDRANT_COLLECTION_RESEARCH=research_chunks

# LLMs
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=your_gemini_api_key
QWEN_VL_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
QWEN_VL_PROVIDER=huggingface
QWEN_VL_API_KEY=
QWEN_VL_BASE_URL=https://router.huggingface.co/v1
QWEN_VL_TIMEOUT_SEC=90
SARVAM_API_KEY=optional_legacy_only

# Web Research
FIRECRAWL_API_KEY=fc-your_firecrawl_key
SERPER_API_KEY=optional
RESEARCH_MODE=live

# App
SECRET_KEY=your_secret_key
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50
```

### `docker-compose.yml`
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: intellicredit
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrantdata:/qdrant/storage
    healthcheck:
      test: [ "CMD-SHELL", "grep -q ':18BD' /proc/net/tcp /proc/net/tcp6 || exit 1" ]

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    ports:
      - "8001:8000"
    env_file: ./.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/intellicredit
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - qdrant
      - redis

  worker:
    build: ./backend
    env_file: ./.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/intellicredit
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      - QDRANT_URL=http://qdrant:6333
    command: celery -A backend.tasks.celery_app.celery_app worker --loglevel=info
    depends_on:
      - postgres
      - redis
      - qdrant

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8001

volumes:
  pgdata:
  qdrantdata:
```

---

## 6. Module 1: Data Ingestion Pipeline

### Overview
The ingestion pipeline uses a smart router to determine what kind of document was uploaded, then applies the correct extraction strategy. Three extraction layers are stacked in priority order.

### `agents/nodes/document_router.py`
```python
"""
Node 1: Document Router
Classifies uploaded PDFs into types so downstream agents know what to extract.

Document Types:
  - ANNUAL_REPORT: Full company annual report (complex tables, charts)
  - GST_FILING: GSTR-3B or GSTR-1 (structured tables)
  - BANK_STATEMENT: Bank account statement (transaction rows)
  - ITR: Income Tax Return (government form)
  - LEGAL_NOTICE: Court notice or legal document
  - SANCTION_LETTER: Loan sanction letter from another bank
  - RATING_REPORT: Rating agency report (CRISIL, ICRA, etc.)
  - UNKNOWN: Fallback
"""

from agents.state import CreditAppraisalState
import pdfplumber
import re

DOCUMENT_KEYWORDS = {
    "ANNUAL_REPORT": ["director's report", "auditor's report", "balance sheet", "statement of profit", "annual report"],
    "GST_FILING": ["gstr", "gstin", "outward supplies", "inward supplies", "input tax credit", "igst", "cgst", "sgst"],
    "BANK_STATEMENT": ["account number", "account no", "transaction date", "debit", "credit", "balance", "ifsc"],
    "ITR": ["income tax return", "assessment year", "pan", "gross total income", "tax payable"],
    "LEGAL_NOTICE": ["hon'ble court", "plaintiff", "defendant", "petition", "writ", "recovery suit", "drt"],
    "SANCTION_LETTER": ["sanction letter", "sanctioned limit", "rate of interest", "repayment schedule", "drawing power"],
    "RATING_REPORT": ["crisil", "icra", "care ratings", "brickwork", "credit rating", "rating rationale"],
}

def classify_document(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for doc_type, keywords in DOCUMENT_KEYWORDS.items():
        scores[doc_type] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "UNKNOWN"

def document_router_node(state: CreditAppraisalState) -> CreditAppraisalState:
    """
    Reads each uploaded document path, extracts first 2 pages of text,
    classifies document type, updates state.
    """
    classified_docs = []
    for doc_path in state["uploaded_document_paths"]:
        try:
            with pdfplumber.open(doc_path) as pdf:
                sample_text = ""
                for page in pdf.pages[:2]:
                    sample_text += (page.extract_text() or "")
            doc_type = classify_document(sample_text)
        except Exception:
            doc_type = "UNKNOWN"
        
        classified_docs.append({
            "path": doc_path,
            "type": doc_type,
            "raw_text": None,  # filled in Node 2
            "extracted_data": {}  # filled in Node 2
        })
    
    state["documents"] = classified_docs
    state["current_node"] = "document_router"
    state["log"].append(f"[Router] Classified {len(classified_docs)} documents: " +
                        ", ".join(d["type"] for d in classified_docs))
    return state
```

### `agents/tools/sarvam_tool.py`
```python
"""
Sarvam Vision API wrapper for Indic-language OCR.
Use this when:
  - pdfplumber returns empty or garbled text (scanned PDF)
  - Document appears to be in a regional Indian language
  - Text extraction confidence is low

API Docs: https://docs.sarvam.ai/vision
"""

import httpx
import base64
import os
from pathlib import Path

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_OCR_URL = "https://api.sarvam.ai/v1/ocr"

def pdf_page_to_base64(pdf_path: str, page_number: int) -> str:
    """Convert a PDF page to base64 image for Sarvam Vision."""
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number, dpi=200)
    if not images:
        raise ValueError(f"Could not convert page {page_number}")
    import io
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def extract_with_sarvam(pdf_path: str, page_number: int) -> dict:
    """
    Send a single PDF page to Sarvam Vision API.
    Returns:
        {
            "text": "extracted text",
            "language": "hi" | "te" | "ta" | "en" | ...,
            "confidence": 0.95,
            "blocks": [...],  # layout blocks with coordinates
        }
    """
    image_b64 = pdf_page_to_base64(pdf_path, page_number)
    
    payload = {
        "image": image_b64,
        "image_format": "png",
        "extract_tables": True,
        "extract_layout": True,
    }
    
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    response = httpx.post(SARVAM_OCR_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()

def extract_full_document_sarvam(pdf_path: str) -> str:
    """Extract all pages of a PDF using Sarvam Vision."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
    
    full_text = []
    for page_num in range(1, total_pages + 1):
        result = extract_with_sarvam(pdf_path, page_num)
        full_text.append(result.get("text", ""))
    
    return "\n\n".join(full_text)
```

### `agents/nodes/ingestion_agent.py`
```python
"""
Node 2: Ingestion Agent
Extracts structured data from each classified document using a 3-tier strategy:

Tier 1 (Structured PDFs): pdfplumber — fast, accurate for digital PDFs
Tier 2 (Scanned/Indic PDFs): Sarvam Vision API — handles 22 Indian languages
Tier 3 (Fallback): Tesseract OCR — open source fallback

After extraction, calls type-specific parsers:
  - parse_annual_report()
  - parse_gst_filing()
  - parse_bank_statement()
  - parse_itr()
  - parse_legal_notice()
"""

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from agents.state import CreditAppraisalState
from agents.tools.sarvam_tool import extract_full_document_sarvam
import re

MIN_TEXT_LENGTH = 100  # below this, consider scan-based extraction

def extract_text_pdfplumber(pdf_path: str) -> str:
    """Extract text from digital PDF using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_tesseract(pdf_path: str) -> str:
    """Fallback OCR using Tesseract (supports Indian language packs)."""
    images = convert_from_path(pdf_path, dpi=200)
    text = ""
    for img in images:
        # Try English + Hindi. Add more langs as needed: 'eng+hin+tel+tam'
        text += pytesseract.image_to_string(img, lang='eng+hin') + "\n"
    return text.strip()

def smart_extract(pdf_path: str) -> tuple[str, str]:
    """
    Returns (extracted_text, method_used)
    method_used: 'pdfplumber' | 'sarvam' | 'tesseract'
    """
    # Tier 1: Try pdfplumber
    text = extract_text_pdfplumber(pdf_path)
    if len(text) >= MIN_TEXT_LENGTH:
        return text, "pdfplumber"
    
    # Tier 2: Sarvam Vision (scanned or Indic)
    try:
        text = extract_full_document_sarvam(pdf_path)
        if len(text) >= MIN_TEXT_LENGTH:
            return text, "sarvam"
    except Exception as e:
        pass  # Fall through to Tesseract
    
    # Tier 3: Tesseract fallback
    text = extract_text_tesseract(pdf_path)
    return text, "tesseract"


# ─── Type-Specific Parsers ───────────────────────────────────────────

def parse_gst_filing(text: str) -> dict:
    """
    Extract key GST metrics from GSTR-3B or GSTR-1 text.
    Returns structured dict of GST data.
    
    Key fields to extract:
    - GSTIN
    - Filing period (month/year)
    - Outward taxable supplies (Table 3.1a of GSTR-3B)
    - Net ITC claimed (Table 4A)
    - Tax paid in cash
    - Tax paid via ITC
    - Nil/exempt supplies
    """
    data = {}
    
    # GSTIN pattern: 15-digit alphanumeric
    gstin_match = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b', text)
    data["gstin"] = gstin_match.group() if gstin_match else None
    
    # Extract outward supplies total
    outward_match = re.search(r'outward taxable supplies[^\d]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    data["outward_supplies"] = float(outward_match.group(1).replace(",", "")) if outward_match else None
    
    # Extract ITC claimed
    itc_match = re.search(r'input tax credit[^\d]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    data["itc_claimed"] = float(itc_match.group(1).replace(",", "")) if itc_match else None
    
    # Filing period
    period_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', text, re.IGNORECASE)
    data["filing_period"] = period_match.group() if period_match else None
    
    return data

def parse_bank_statement(text: str) -> dict:
    """
    Extract aggregated bank data from statement text.
    Returns monthly credit/debit totals, average balance, unusual transactions.
    
    Key metrics for credit analysis:
    - Total credits (12 months)
    - Total debits (12 months)  
    - Average monthly balance
    - Number of ECS/EMI debits (existing loan obligations)
    - Returned/bounced cheques count
    - Cash deposit patterns (unusual cash = potential inflation)
    """
    data = {
        "total_credits": 0,
        "total_debits": 0,
        "bounced_cheques": 0,
        "emi_debits": 0,
        "large_cash_deposits": 0,
        "transactions": []
    }
    
    # Count bounced cheques
    data["bounced_cheques"] = len(re.findall(r'(chq.{0,10}return|bounce|dishonour)', text, re.IGNORECASE))
    
    # Count EMI/ECS debits
    data["emi_debits"] = len(re.findall(r'(emi|ecs|nach)', text, re.IGNORECASE))
    
    # Extract all debit/credit amounts (simplified - enhance with LLM for production)
    credit_matches = re.findall(r'cr[^\d]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    debit_matches = re.findall(r'dr[^\d]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    
    data["total_credits"] = sum(float(m.replace(",", "")) for m in credit_matches[:100])
    data["total_debits"] = sum(float(m.replace(",", "")) for m in debit_matches[:100])
    
    return data

def parse_annual_report(text: str, gemini_client) -> dict:
    """
    Use Gemini to extract structured financial data from annual report text.
    Annual reports are too complex for regex — use LLM with structured output.
    
    Extract:
    - Revenue (last 3 years)
    - EBITDA and EBITDA margin
    - PAT (Profit After Tax)
    - Total Debt
    - Net Worth
    - Current Ratio
    - DSCR (Debt Service Coverage Ratio)
    - Promoter shareholding %
    - Auditor's opinion (qualified/unqualified)
    - Key risks mentioned
    """
    prompt = f"""
    You are a financial analyst. Extract the following from this annual report text.
    Return ONLY valid JSON with these exact keys:
    
    {{
        "revenue_crore": [year1_value, year2_value, year3_value],
        "ebitda_crore": float,
        "ebitda_margin_pct": float,
        "pat_crore": float,
        "total_debt_crore": float,
        "net_worth_crore": float,
        "current_ratio": float,
        "dscr": float,
        "promoter_holding_pct": float,
        "auditor_opinion": "qualified" | "unqualified" | "adverse" | "disclaimer",
        "key_risks": ["risk1", "risk2", ...],
        "directors": ["name1", "name2", ...],
        "company_name": "string",
        "cin": "string"
    }}
    
    If a value cannot be found, use null.
    
    ANNUAL REPORT TEXT:
    {text[:8000]}
    """
    
    response = gemini_client.generate_content(prompt)
    import json
    try:
        return json.loads(response.text)
    except:
        return {}

def ingestion_agent_node(state: CreditAppraisalState) -> CreditAppraisalState:
    """Main ingestion node — processes all classified documents."""
    import google.generativeai as genai
    import os
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini = genai.GenerativeModel("gemini-1.5-pro")
    
    for doc in state["documents"]:
        # Smart extraction
        raw_text, method = smart_extract(doc["path"])
        doc["raw_text"] = raw_text
        doc["extraction_method"] = method
        
        # Type-specific parsing
        if doc["type"] == "GST_FILING":
            doc["extracted_data"] = parse_gst_filing(raw_text)
        elif doc["type"] == "BANK_STATEMENT":
            doc["extracted_data"] = parse_bank_statement(raw_text)
        elif doc["type"] == "ANNUAL_REPORT":
            doc["extracted_data"] = parse_annual_report(raw_text, gemini)
        elif doc["type"] == "LEGAL_NOTICE":
            doc["extracted_data"] = {"text": raw_text[:2000], "type": "legal"}
        
        state["log"].append(f"[Ingestion] {doc['type']} extracted via {method} — "
                           f"{len(raw_text)} chars")
        
        # Embed chunks into Qdrant
        _embed_document_to_qdrant(doc, state["company_id"])
    
    # Consolidate all extracted financials into state
    state["extracted_financials"] = _consolidate_financials(state["documents"])
    state["current_node"] = "ingestion_agent"
    return state

def _embed_document_to_qdrant(doc: dict, company_id: str):
    """Chunk document text and upsert to Qdrant for later RAG queries."""
    from vector_store.qdrant_client import upsert_document_chunks
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer("BAAI/bge-m3")  # multilingual, works with Indic text
    
    # Chunk text into 500-char overlapping windows
    text = doc["raw_text"] or ""
    chunks = [text[i:i+500] for i in range(0, len(text), 400)]
    
    embeddings = model.encode(chunks).tolist()
    
    payloads = [{
        "company_id": company_id,
        "doc_type": doc["type"],
        "chunk_text": chunk,
        "chunk_index": i
    } for i, chunk in enumerate(chunks)]
    
    upsert_document_chunks(embeddings, payloads)

def _consolidate_financials(documents: list) -> dict:
    """Merge all extracted data from all documents into a single financials dict."""
    financials = {}
    for doc in documents:
        if doc["type"] == "ANNUAL_REPORT":
            financials.update(doc["extracted_data"])
        elif doc["type"] == "GST_FILING":
            financials["gst"] = doc["extracted_data"]
        elif doc["type"] == "BANK_STATEMENT":
            financials["bank"] = doc["extracted_data"]
    return financials
```

---

## 7. Module 2: LangGraph Agent Orchestration

### `agents/state.py`
```python
"""
Shared state that flows through the entire LangGraph pipeline.
Every node reads from and writes to this TypedDict.
"""

from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum

class RiskCategory(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CreditAppraisalState(TypedDict):
    # Identity
    company_id: str
    company_name: str
    
    # Document tracking
    uploaded_document_paths: List[str]
    documents: List[Dict]  # [{path, type, raw_text, extracted_data, extraction_method}]
    
    # Extracted financial data (consolidated from all docs)
    extracted_financials: Dict[str, Any]
    
    # GST reconciliation
    gst_bank_mismatch_pct: Optional[float]
    circular_trading_detected: bool
    circular_trading_entities: List[str]
    gst_flags: List[str]
    
    # Research results
    news_summary: str
    mca_data: Dict[str, Any]
    litigation_data: List[Dict]
    rbi_regulatory_flags: List[str]
    promoter_background: Dict[str, Any]
    research_red_flags: List[str]
    
    # Human-in-the-loop (qualitative inputs from Credit Officer)
    qualitative_notes: Optional[str]
    site_visit_capacity_pct: Optional[float]
    management_assessment: Optional[str]
    hitl_complete: bool
    
    # Risk scoring
    rule_based_score: Optional[float]       # 0-100 (100 = lowest risk)
    ml_stress_probability: Optional[float]  # 0-1 (1 = highest stress)
    final_risk_score: Optional[float]       # blended 0-100
    risk_category: Optional[RiskCategory]
    shap_values: Optional[Dict[str, float]] # feature_name -> contribution
    rule_violations: List[str]              # list of triggered rules
    risk_strengths: List[str]               # positive factors
    
    # Decision
    decision: Optional[str]                 # APPROVE | CONDITIONAL_APPROVE | REJECT
    recommended_loan_limit_crore: Optional[float]
    interest_rate_premium_bps: Optional[int] # basis points over base rate
    decision_rationale: str
    
    # CAM output
    cam_text: Optional[str]
    cam_docx_path: Optional[str]
    cam_pdf_path: Optional[str]
    
    # Pipeline metadata
    current_node: str
    log: List[str]
    errors: List[str]
```

### `agents/graph.py`
```python
"""
LangGraph stateful graph definition.
This is the MAIN ORCHESTRATOR of the entire Intelli-Credit pipeline.

Graph Flow:
  document_router → ingestion_agent → gst_reconciler → research_agent
  → hitl_node (PAUSE for human input) → risk_scorer → cam_generator → END

Conditional edges:
  - If circular_trading_detected: add "FRAUD WARNING" to state before scoring
  - If DSCR < 1.0 after ingestion: skip ML calibration, auto-escalate risk
  - hitl_node pauses and waits for Credit Officer to submit qualitative notes
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.state import CreditAppraisalState
from agents.nodes.document_router import document_router_node
from agents.nodes.ingestion_agent import ingestion_agent_node
from agents.nodes.gst_reconciler import gst_reconciler_node
from agents.nodes.research_agent import research_agent_node
from agents.nodes.hitl_node import hitl_node
from agents.nodes.risk_scorer import risk_scorer_node
from agents.nodes.cam_generator import cam_generator_node

def should_escalate_fraud(state: CreditAppraisalState) -> str:
    """Conditional edge: if circular trading detected, mark state before scoring."""
    if state.get("circular_trading_detected"):
        state["rule_violations"].append("CRITICAL: Circular trading pattern detected in GST graph")
    return "research_agent"  # always continue to research

def hitl_routing(state: CreditAppraisalState) -> str:
    """Pause pipeline at HITL node until Credit Officer submits notes."""
    if state.get("hitl_complete"):
        return "risk_scorer"
    return "hitl_node"  # loop back — graph will pause here via interrupt

def build_graph() -> StateGraph:
    graph = StateGraph(CreditAppraisalState)
    
    # Add all nodes
    graph.add_node("document_router", document_router_node)
    graph.add_node("ingestion_agent", ingestion_agent_node)
    graph.add_node("gst_reconciler", gst_reconciler_node)
    graph.add_node("research_agent", research_agent_node)
    graph.add_node("hitl_node", hitl_node)
    graph.add_node("risk_scorer", risk_scorer_node)
    graph.add_node("cam_generator", cam_generator_node)
    
    # Define edges
    graph.set_entry_point("document_router")
    graph.add_edge("document_router", "ingestion_agent")
    graph.add_edge("ingestion_agent", "gst_reconciler")
    graph.add_conditional_edges("gst_reconciler", should_escalate_fraud)
    graph.add_edge("research_agent", "hitl_node")
    graph.add_conditional_edges("hitl_node", hitl_routing)
    graph.add_edge("risk_scorer", "cam_generator")
    graph.add_edge("cam_generator", END)
    
    # Interrupt at HITL node to wait for Credit Officer input
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer, interrupt_before=["hitl_node"])

# Global graph instance
credit_graph = build_graph()
```

---

## 8. Module 3: Web Research Agent

### `agents/nodes/research_agent.py`
```python
"""
Node 4: Web Research Agent
Autonomously researches the company across 4 sources:
  1. Serper (Google Search) — news, fraud alerts, sector news
  2. MCA21 Portal — company registration, directors, charges
  3. eCourts Portal — litigation history
  4. RBI/SEBI pages — sector-specific regulatory alerts

Uses Gemini to summarize and extract structured insights from raw scraped text.
Populates state with: news_summary, mca_data, litigation_data,
                      rbi_regulatory_flags, promoter_background, research_red_flags
"""

import os
from agents.state import CreditAppraisalState
from agents.tools.serper_tool import search_news, search_promoter
from agents.tools.mca_scraper import scrape_mca21
from agents.tools.ecourts_scraper import search_ecourts
from agents.tools.rbi_scraper import get_rbi_alerts
import google.generativeai as genai

def research_agent_node(state: CreditAppraisalState) -> CreditAppraisalState:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini = genai.GenerativeModel("gemini-1.5-pro")
    
    company = state["company_name"]
    log = state["log"]
    red_flags = []
    
    # ── 1. News Research ─────────────────────────────────────────────
    log.append(f"[Research] Searching news for: {company}")
    news_results = search_news(f"{company} fraud default NPA litigation RBI")
    sector_news = search_news(f"{_get_sector(state)} RBI regulation India 2024 2025")
    
    news_summary = _summarize_with_gemini(gemini, 
        f"Company news:\n{news_results}\n\nSector news:\n{sector_news}",
        "Summarize key risks and negative signals for a credit analyst. "
        "Flag: fraud, defaults, NPA, regulatory action, promoter issues."
    )
    state["news_summary"] = news_summary
    if any(word in news_summary.lower() for word in ["fraud", "default", "npa", "arrested", "sebi action"]):
        red_flags.append(f"Negative news detected: {news_summary[:200]}")
    
    # ── 2. MCA21 Research ────────────────────────────────────────────
    log.append(f"[Research] Fetching MCA21 data for: {company}")
    mca_data = scrape_mca21(company)
    state["mca_data"] = mca_data
    
    if mca_data.get("charge_count", 0) > 3:
        red_flags.append(f"High charge count on MCA21: {mca_data['charge_count']} charges registered")
    if mca_data.get("din_disqualified"):
        red_flags.append("Director DIN disqualified — regulatory red flag")
    
    # ── 3. eCourts Litigation ────────────────────────────────────────
    log.append(f"[Research] Searching eCourts for: {company}")
    litigation = search_ecourts(company)
    state["litigation_data"] = litigation
    
    active_cases = [c for c in litigation if c.get("status") == "pending"]
    recovery_suits = [c for c in active_cases if "recovery" in c.get("type", "").lower()]
    if len(active_cases) >= 3:
        red_flags.append(f"{len(active_cases)} active court cases found")
    if recovery_suits:
        red_flags.append(f"{len(recovery_suits)} recovery suits pending (loan default indicator)")
    
    # ── 4. RBI/SEBI Regulatory Flags ─────────────────────────────────
    log.append(f"[Research] Checking RBI/SEBI for sector alerts")
    rbi_flags = get_rbi_alerts(_get_sector(state))
    state["rbi_regulatory_flags"] = rbi_flags
    if rbi_flags:
        red_flags.append(f"Regulatory headwinds: {'; '.join(rbi_flags[:2])}")
    
    # ── 5. Promoter Background ───────────────────────────────────────
    directors = state.get("extracted_financials", {}).get("directors", [])
    promoter_bg = {}
    for director in directors[:3]:  # Check top 3 directors
        news = search_promoter(director)
        if any(w in news.lower() for w in ["fraud", "arrested", "wilful defaulter", "lookout"]):
            red_flags.append(f"Promoter alert: {director} — negative news found")
            promoter_bg[director] = "RED"
        else:
            promoter_bg[director] = "CLEAR"
    
    state["promoter_background"] = promoter_bg
    state["research_red_flags"] = red_flags
    state["current_node"] = "research_agent"
    log.append(f"[Research] Complete — {len(red_flags)} red flags identified")
    
    return state

def _get_sector(state: CreditAppraisalState) -> str:
    """Extract sector/industry from annual report data."""
    return state.get("extracted_financials", {}).get("sector", "manufacturing India")

def _summarize_with_gemini(gemini, content: str, instruction: str) -> str:
    prompt = f"{instruction}\n\nCONTENT:\n{content[:6000]}"
    response = gemini.generate_content(prompt)
    return response.text
```

### `agents/tools/serper_tool.py`
```python
"""
Google Search via Serper API.
Serper gives structured JSON results from Google Search.
Sign up: https://serper.dev (free tier: 2500 queries/month)
"""

import httpx
import os

SERPER_URL = "https://google.serper.dev/search"

def _search(query: str, num_results: int = 10) -> str:
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": num_results, "gl": "in", "hl": "en"}
    response = httpx.post(SERPER_URL, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    results = []
    for item in data.get("organic", []):
        results.append(f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}\nLink: {item.get('link')}")
    return "\n\n".join(results)

def search_news(query: str) -> str:
    return _search(f"{query} site:economictimes.com OR site:livemint.com OR site:business-standard.com")

def search_promoter(name: str) -> str:
    return _search(f'"{name}" fraud default SEBI RBI arrested wilful defaulter India')
```

### `agents/tools/mca_scraper.py`
```python
"""
MCA21 Portal Scraper
Ministry of Corporate Affairs — India's company registration database.
Public data available at: https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do

Key data points:
- Company CIN (Corporate Identification Number)
- Director DIns and their disqualification status
- Registered charges (loans secured against assets)
- Filing compliance status (ROC filings)
- Company status (active/struck off/under liquidation)

IMPORTANT: MCA21 does not have a public API. Use headless browser (Playwright) 
for dynamic pages. Respect robots.txt and rate limit to 1 req/3 sec.
"""

import httpx
from bs4 import BeautifulSoup
import time
import re

MCA_BASE = "https://www.mca.gov.in"

def scrape_mca21(company_name: str) -> dict:
    """
    Scrape MCA21 for company data.
    Returns structured dict with:
    - cin, company_status, incorporation_date
    - directors: [{name, din, designation}]
    - charge_count (number of registered charges/loans)
    - din_disqualified (bool)
    - roc_compliance_status
    """
    # NOTE: Actual implementation requires Playwright for JS-rendered pages
    # This is the request structure — implement with async Playwright in production
    
    try:
        # Step 1: Search for company
        search_url = f"https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"
        # In production: use Playwright to fill form and submit
        
        # Mock structure — replace with actual scraping
        return {
            "cin": None,
            "company_status": "ACTIVE",
            "incorporation_date": None,
            "directors": [],
            "charge_count": 0,
            "din_disqualified": False,
            "roc_compliance_status": "COMPLIANT",
            "authorized_capital_lakh": None,
            "paid_up_capital_lakh": None
        }
    except Exception as e:
        return {"error": str(e)}

def scrape_mca21_with_playwright(company_name: str) -> dict:
    """
    Production implementation using Playwright for JS-rendered MCA pages.
    Install: pip install playwright && playwright install chromium
    """
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to MCA company search
        page.goto("https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do")
        page.wait_for_load_state("networkidle")
        
        # Fill company name and search
        page.fill('input[name="companyName"]', company_name)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")
        
        # Extract results
        content = page.content()
        browser.close()
        
        return _parse_mca_results(content)

def _parse_mca_results(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    # Parse company table — structure varies, implement based on actual MCA page DOM
    return {}
```

### `agents/tools/ecourts_scraper.py`
```python
"""
eCourts Portal Scraper
India's national e-courts portal: https://services.ecourts.gov.in

Search for:
- Company name as plaintiff or defendant
- Recovery suits (Debt Recovery Tribunal)
- Winding up petitions (Company Court)
- Criminal cases involving directors

IMPORTANT: eCourts has CAPTCHA on its main portal. Strategies:
1. Use the eCourts API if available for your use case
2. DRT (Debt Recovery Tribunal) has separate portal: https://drt.gov.in
3. NCLT (National Company Law Tribunal) orders: https://nclt.gov.in
4. Use case search on individual High Court portals

Rate limit aggressively — 1 request per 5 seconds.
"""

import httpx
from bs4 import BeautifulSoup

def search_ecourts(company_name: str) -> list:
    """
    Returns list of cases:
    [{
        "case_number": str,
        "court": str,
        "type": str,  # "recovery", "winding_up", "criminal", "civil"
        "status": str,  # "pending", "disposed"
        "year": int,
        "parties": str
    }]
    """
    results = []
    
    # Search DRT (Debt Recovery Tribunal) — most relevant for corporate credit
    drt_cases = _search_drt(company_name)
    results.extend(drt_cases)
    
    # Search NCLT for winding up petitions
    nclt_cases = _search_nclt(company_name)
    results.extend(nclt_cases)
    
    return results

def _search_drt(company_name: str) -> list:
    """Search Debt Recovery Tribunal portal."""
    # DRT portal: https://drt.gov.in/drt/
    # Implement based on actual DRT portal structure
    return []

def _search_nclt(company_name: str) -> list:
    """Search NCLT for insolvency/winding up cases."""
    # NCLT search: https://nclt.gov.in/case-status
    return []
```

### `agents/tools/circular_trade.py`
```python
"""
Circular Trading Detector
Uses NetworkX graph analysis to detect circular GST transaction patterns.

What is circular trading?
Company A → pays GST to Company B
Company B → pays GST to Company C  
Company C → pays GST back to Company A
= Fake revenue inflation. All three boost their "outward supplies" without real economic activity.

How to detect:
1. Extract buyer-seller relationships from GSTR-1/2A/2B filings
2. Build a directed graph: edge from seller → buyer for each transaction
3. Detect cycles in the graph using networkx.find_cycle()
4. Flag cycles involving significant value (> 10 lakh)
"""

import networkx as nx
from typing import List, Tuple

def build_gst_graph(transactions: List[dict]) -> nx.DiGraph:
    """
    Build directed graph from GST transactions.
    Each transaction: {seller_gstin, buyer_gstin, value}
    """
    G = nx.DiGraph()
    for txn in transactions:
        G.add_edge(
            txn["seller_gstin"],
            txn["buyer_gstin"],
            weight=txn.get("value", 0)
        )
    return G

def detect_circular_trading(transactions: List[dict]) -> Tuple[bool, List]:
    """
    Returns (is_circular, list_of_circular_entities)
    """
    if not transactions:
        return False, []
    
    G = build_gst_graph(transactions)
    
    try:
        cycle = nx.find_cycle(G, orientation="original")
        # Extract entities in the cycle
        entities = list(set([edge[0] for edge in cycle] + [edge[1] for edge in cycle]))
        return True, entities
    except nx.NetworkXNoCycle:
        return False, []

def check_gst_bank_mismatch(gst_outward_supplies: float, bank_total_credits: float) -> float:
    """
    Compare GST-declared turnover with actual bank credits.
    Returns mismatch percentage.
    
    Red flags:
    - Mismatch > 25%: Potential revenue inflation
    - GST > Bank: Possible fictitious invoicing
    - Bank >> GST: Possible GST evasion
    
    Indian context: 
    - GSTR-3B outward supplies should roughly match bank account credits
    - Adjust for advance payments, export receipts, inter-company transfers
    """
    if not gst_outward_supplies or not bank_total_credits:
        return 0.0
    
    mismatch = abs(gst_outward_supplies - bank_total_credits) / max(gst_outward_supplies, bank_total_credits)
    return round(mismatch * 100, 2)
```

---

## 9. Module 4: Hybrid Risk Scoring Engine

### `scoring/rules_engine.py`
```python
"""
Layer 1: Deterministic Rule-Based Risk Engine
Encodes Indian banking underwriting logic for the Five Cs of Credit.

Rules are applied sequentially. Each rule:
  - Checks a specific condition
  - Assigns a score penalty (0-100 scale, 100 = best)
  - Adds a human-readable violation string if triggered

Base score starts at 100. Rules subtract points.
Critical rules (marked CRITICAL) are hard stops that force REJECT.
"""

from agents.state import CreditAppraisalState

RULES = [
    # ── CAPACITY RULES (ability to repay) ────────────────────────────
    {
        "id": "CAP_001",
        "name": "DSCR Below 1.0",
        "severity": "CRITICAL",
        "check": lambda f: (f.get("dscr") or 999) < 1.0,
        "penalty": 40,
        "message": "DSCR below 1.0 — company cannot service debt from operations (hard stop)"
    },
    {
        "id": "CAP_002",
        "name": "DSCR Between 1.0 and 1.25",
        "severity": "HIGH",
        "check": lambda f: 1.0 <= (f.get("dscr") or 999) < 1.25,
        "penalty": 20,
        "message": "DSCR between 1.0–1.25: thin coverage margin, vulnerable to cash flow stress"
    },
    {
        "id": "CAP_003",
        "name": "EBITDA Margin Below 5%",
        "severity": "HIGH",
        "check": lambda f: (f.get("ebitda_margin_pct") or 999) < 5.0,
        "penalty": 15,
        "message": "EBITDA margin below 5% — low operational profitability"
    },
    {
        "id": "CAP_004",
        "name": "Revenue Declining 3 Years",
        "severity": "MEDIUM",
        "check": lambda f: _is_declining(f.get("revenue_crore", [])),
        "penalty": 10,
        "message": "Revenue declining for 3 consecutive years — business contraction signal"
    },

    # ── CAPITAL RULES (financial leverage) ───────────────────────────
    {
        "id": "CAP_005",
        "name": "Debt-to-Equity > 3x",
        "severity": "HIGH",
        "check": lambda f: _compute_de_ratio(f) > 3.0,
        "penalty": 20,
        "message": "Debt-to-Equity above 3x — highly leveraged balance sheet"
    },
    {
        "id": "CAP_006",
        "name": "Current Ratio Below 1.0",
        "severity": "HIGH",
        "check": lambda f: (f.get("current_ratio") or 999) < 1.0,
        "penalty": 15,
        "message": "Current ratio below 1.0 — negative working capital, liquidity risk"
    },
    {
        "id": "CAP_007",
        "name": "Negative Net Worth",
        "severity": "CRITICAL",
        "check": lambda f: (f.get("net_worth_crore") or 1) < 0,
        "penalty": 50,
        "message": "Negative net worth — company is technically insolvent (hard stop)"
    },

    # ── CHARACTER RULES (promoter integrity) ─────────────────────────
    {
        "id": "CHAR_001",
        "name": "Promoter Litigation Red Flag",
        "severity": "HIGH",
        "check": lambda f: f.get("promoter_red_flag", False),
        "penalty": 25,
        "message": "Promoter has active fraud/default news — character risk"
    },
    {
        "id": "CHAR_002",
        "name": "Director DIN Disqualified",
        "severity": "CRITICAL",
        "check": lambda f: f.get("din_disqualified", False),
        "penalty": 50,
        "message": "Director DIN disqualified by MCA — regulatory red flag (hard stop)"
    },
    {
        "id": "CHAR_003",
        "name": "Qualified Auditor Opinion",
        "severity": "HIGH",
        "check": lambda f: f.get("auditor_opinion") in ["qualified", "adverse", "disclaimer"],
        "penalty": 20,
        "message": f"Auditor gave qualified/adverse opinion — financial statement reliability risk"
    },

    # ── COLLATERAL/FRAUD RULES ────────────────────────────────────────
    {
        "id": "FRAUD_001",
        "name": "Circular Trading Detected",
        "severity": "CRITICAL",
        "check": lambda f: f.get("circular_trading_detected", False),
        "penalty": 60,
        "message": "Circular GST trading pattern detected — revenue inflation suspected (hard stop)"
    },
    {
        "id": "FRAUD_002",
        "name": "GST-Bank Mismatch > 25%",
        "severity": "HIGH",
        "check": lambda f: (f.get("gst_bank_mismatch_pct") or 0) > 25,
        "penalty": 25,
        "message": f"GST declared revenue and bank credits mismatch by more than 25%"
    },

    # ── LITIGATION RULES ──────────────────────────────────────────────
    {
        "id": "LIT_001",
        "name": "3 or More Active Litigations",
        "severity": "HIGH",
        "check": lambda f: (f.get("active_litigation_count") or 0) >= 3,
        "penalty": 20,
        "message": "3 or more active litigation cases — legal contingency risk"
    },
    {
        "id": "LIT_002",
        "name": "Recovery Suit / DRT Case",
        "severity": "CRITICAL",
        "check": lambda f: f.get("has_recovery_suit", False),
        "penalty": 40,
        "message": "Active recovery suit / DRT case — prior loan default indicator (hard stop)"
    },

    # ── CONDITIONS RULES (sector/macro) ──────────────────────────────
    {
        "id": "COND_001",
        "name": "Factory Capacity Below 50%",
        "severity": "MEDIUM",
        "check": lambda f: 0 < (f.get("factory_capacity_pct") or 100) < 50,
        "penalty": 15,
        "message": "Factory operating below 50% capacity — underutilization, projected cash flows adjusted"
    },
    {
        "id": "COND_002",
        "name": "Sector Regulatory Headwind",
        "severity": "LOW",
        "check": lambda f: f.get("sector_headwind", False),
        "penalty": 5,
        "message": "Active RBI/SEBI regulatory restriction on sector"
    },
]

def _is_declining(revenue_list: list) -> bool:
    if len(revenue_list) < 3:
        return False
    return revenue_list[0] > revenue_list[1] > revenue_list[2]

def _compute_de_ratio(financials: dict) -> float:
    debt = financials.get("total_debt_crore") or 0
    equity = financials.get("net_worth_crore") or 1
    return debt / equity if equity > 0 else 999

def apply_rules(financials: dict) -> tuple:
    """
    Apply all rules to financials dict.
    Returns (score: float, violations: list[str], critical_hit: bool)
    """
    score = 100.0
    violations = []
    strengths = []
    critical_hit = False
    
    for rule in RULES:
        try:
            if rule["check"](financials):
                score -= rule["penalty"]
                violations.append(f"[{rule['severity']}] {rule['message']}")
                if rule["severity"] == "CRITICAL":
                    critical_hit = True
        except Exception:
            pass
    
    # Identify strengths (inverse of violations)
    if (financials.get("dscr") or 0) >= 1.5:
        strengths.append("Strong DSCR above 1.5x — comfortable debt servicing capacity")
    if (financials.get("current_ratio") or 0) >= 2.0:
        strengths.append("Healthy current ratio above 2.0 — good liquidity position")
    if not financials.get("circular_trading_detected"):
        strengths.append("No circular trading detected — GST transactions appear genuine")
    if financials.get("auditor_opinion") == "unqualified":
        strengths.append("Clean unqualified auditor opinion — financial statements reliable")
    
    return max(score, 0), violations, strengths, critical_hit
```

### `scoring/ml_calibrator.py`
```python
"""
Layer 2: XGBoost ML Calibration
Captures nonlinear relationships between financial features.
Output: probability of credit stress (0.0 = no stress, 1.0 = definite stress)

Training data: Generate synthetic Indian corporate credit data using synthetic_data.py
Features are engineered from the same extracted_financials dict.

The model does NOT make the credit decision.
It provides a calibrated probability that ADJUSTS the rule-based score.
"""

import xgboost as xgb
import numpy as np
import pickle
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../ml/model/xgb_credit_model.pkl")

FEATURE_NAMES = [
    "dscr",
    "ebitda_margin_pct",
    "current_ratio",
    "debt_to_equity",
    "revenue_growth_yoy",
    "gst_bank_mismatch_pct",
    "active_litigation_count",
    "promoter_red_flag",        # 0 or 1
    "factory_capacity_pct",
    "auditor_qualified",        # 0 or 1
    "charge_count",
    "bounced_cheques_12m",
    "sector_risk_index",        # 0-10 scale by sector
]

def extract_ml_features(financials: dict) -> np.ndarray:
    """Convert extracted financials dict to ML feature vector."""
    revenue = financials.get("revenue_crore", [0, 0])
    revenue_growth = (revenue[0] - revenue[1]) / revenue[1] if len(revenue) >= 2 and revenue[1] else 0
    
    features = [
        financials.get("dscr") or 1.0,
        financials.get("ebitda_margin_pct") or 0.0,
        financials.get("current_ratio") or 1.0,
        _compute_de_ratio(financials),
        revenue_growth,
        financials.get("gst_bank_mismatch_pct") or 0.0,
        financials.get("active_litigation_count") or 0,
        int(financials.get("promoter_red_flag", False)),
        financials.get("factory_capacity_pct") or 80.0,
        int(financials.get("auditor_opinion") in ["qualified", "adverse"]),
        financials.get("charge_count") or 0,
        financials.get("bounced_cheques") or 0,
        SECTOR_RISK_INDEX.get(financials.get("sector", "other"), 5),
    ]
    return np.array(features).reshape(1, -1)

def _compute_de_ratio(financials: dict) -> float:
    debt = financials.get("total_debt_crore") or 0
    equity = financials.get("net_worth_crore") or 1
    return min(debt / equity if equity > 0 else 10.0, 10.0)

SECTOR_RISK_INDEX = {
    "nbfc": 8, "real_estate": 7, "construction": 7, "aviation": 9,
    "telecom": 6, "steel": 5, "fmcg": 3, "pharma": 3, "it": 2,
    "manufacturing": 4, "agriculture": 5, "textile": 5, "other": 5
}

def predict_stress_probability(financials: dict) -> float:
    """Load trained XGBoost model and predict stress probability."""
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        features = extract_ml_features(financials)
        prob = model.predict_proba(features)[0][1]  # probability of class 1 (stress)
        return float(prob)
    except FileNotFoundError:
        # Model not trained yet — return neutral 0.5
        return 0.5
```

### `scoring/shap_explainer.py`
```python
"""
SHAP Explainability
Generates feature importance values for each prediction.
These values are shown in the SHAP waterfall chart in the Next.js frontend.

SHAP values show: "How much did each feature INCREASE or DECREASE the risk score?"
Positive SHAP = increases stress probability (bad)
Negative SHAP = decreases stress probability (good)
"""

import shap
import numpy as np
import pickle
from scoring.ml_calibrator import extract_ml_features, FEATURE_NAMES

def compute_shap_values(financials: dict) -> dict:
    """
    Returns dict of {feature_name: shap_value} sorted by absolute importance.
    """
    try:
        with open("ml/model/xgb_credit_model.pkl", "rb") as f:
            model = pickle.load(f)
        
        features = extract_ml_features(financials)
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(features)[0]  # for positive class
        
        result = {name: float(val) for name, val in zip(FEATURE_NAMES, shap_values)}
        # Sort by absolute value (most impactful first)
        return dict(sorted(result.items(), key=lambda x: abs(x[1]), reverse=True))
    
    except Exception:
        # Fallback: return rule contributions as mock SHAP
        return {
            "dscr": financials.get("dscr", 1.0) - 1.25,
            "gst_bank_mismatch_pct": (financials.get("gst_bank_mismatch_pct") or 0) / 100,
            "active_litigation_count": (financials.get("active_litigation_count") or 0) * 0.05,
        }
```

### `scoring/score_blender.py`
```python
"""
Final Score Blending
Combines rule-based score and ML stress probability into a single risk score.

Formula:
  Final Risk Score = 0.6 × Rule-Based Score + 0.4 × (1 - ML_Stress_Probability) × 100

The 0.6/0.4 weights ensure:
  - Rules DOMINATE (regulatory/governance alignment)
  - ML adds nuance without overriding critical rule violations

Decision thresholds:
  Score 75–100: LOW risk → APPROVE
  Score 55–74:  MODERATE risk → CONDITIONAL APPROVE (with covenants)
  Score 35–54:  HIGH risk → CONDITIONAL APPROVE with collateral enhancement OR REJECT
  Score 0–34:   CRITICAL risk → REJECT (or escalate to credit committee)

Loan limit calculation (MPBF-style — Maximum Permissible Bank Finance):
  Based on RBI's Tandon Committee norms (standard in Indian banking):
  Working Capital Limit = 0.75 × (Current Assets - Current Liabilities)
  Adjusted by risk score: Final Limit = MPBF × (Score/100) × Sector_Cap_Multiplier
"""

from agents.state import RiskCategory

RULE_WEIGHT = 0.6
ML_WEIGHT = 0.4

RISK_THRESHOLDS = {
    "LOW": (75, 100),
    "MODERATE": (55, 74),
    "HIGH": (35, 54),
    "CRITICAL": (0, 34),
}

INTEREST_PREMIUMS_BPS = {
    "LOW": 50,        # 0.5% over base
    "MODERATE": 150,  # 1.5% over base
    "HIGH": 300,      # 3.0% over base
    "CRITICAL": None, # REJECT
}

def blend_scores(rule_score: float, ml_prob: float) -> tuple:
    """Returns (final_score, risk_category)"""
    ml_component = (1 - ml_prob) * 100  # invert: high stress prob = low score
    final = (RULE_WEIGHT * rule_score) + (ML_WEIGHT * ml_component)
    final = round(max(0, min(100, final)), 1)
    
    category = "CRITICAL"
    for cat, (low, high) in RISK_THRESHOLDS.items():
        if low <= final <= high:
            category = cat
            break
    
    return final, category

def compute_loan_limit(financials: dict, risk_score: float) -> float:
    """
    Compute recommended loan limit in Crore using MPBF approach.
    Returns 0 if REJECT.
    """
    if risk_score < 35:
        return 0.0
    
    # MPBF = 0.75 × (Current Assets - Current Liabilities)
    current_assets = financials.get("current_assets_crore") or 0
    current_liabilities = financials.get("current_liabilities_crore") or 0
    mpbf = 0.75 * max(current_assets - current_liabilities, 0)
    
    # Risk adjustment
    risk_multiplier = risk_score / 100
    limit = mpbf * risk_multiplier
    
    return round(limit, 1)

def determine_decision(risk_category: str, critical_hit: bool) -> str:
    if critical_hit or risk_category == "CRITICAL":
        return "REJECT"
    elif risk_category == "LOW":
        return "APPROVE"
    else:
        return "CONDITIONAL_APPROVE"
```

---

## 10. Module 5: CAM Generator

### `cam/cam_template.py`
```python
"""
CAM Generator — Credit Appraisal Memo
Produces professional CAM document structured around the Five Cs of Credit.

The LLM (Gemini) is given ONLY structured data — it explains, not decides.
All scores, limits, and decisions come from the rules/ML engine.
"""

CAM_SYSTEM_PROMPT = """
You are a senior credit analyst at a leading Indian bank (SBI/HDFC/Axis level).
You are writing a Credit Appraisal Memo (CAM) for the credit committee.

CRITICAL RULES:
1. You did NOT make the credit decision. The scoring engine did.
2. Your job is to explain the decision clearly and professionally.
3. Reference SPECIFIC data points from the structured inputs provided.
4. Use Indian banking terminology: MPBF, DSCR, TOL/TNW, NWC, DPG, ROC, etc.
5. Be concise but thorough. This document will be reviewed by the credit committee.
6. Never fabricate figures. If data is missing, state "Not Available."
7. Flag all risks explicitly, even if the decision is APPROVE.
"""

def build_cam_prompt(state: dict) -> str:
    f = state.get("extracted_financials", {})
    
    return f"""
{CAM_SYSTEM_PROMPT}

=== STRUCTURED INPUTS (DO NOT DEVIATE FROM THESE NUMBERS) ===

COMPANY: {state.get('company_name')}
DECISION: {state.get('decision')}
FINAL RISK SCORE: {state.get('final_risk_score')}/100 ({state.get('risk_category')} RISK)
RECOMMENDED LOAN LIMIT: ₹{state.get('recommended_loan_limit_crore')} Crore
INTEREST PREMIUM: {state.get('interest_rate_premium_bps')} bps over MCLR

FINANCIALS:
- Revenue (3 years): {f.get('revenue_crore')} Crore
- EBITDA Margin: {f.get('ebitda_margin_pct')}%
- PAT: ₹{f.get('pat_crore')} Crore
- DSCR: {f.get('dscr')}x
- Current Ratio: {f.get('current_ratio')}x
- Debt/Equity: {_compute_de(f)}x
- Net Worth: ₹{f.get('net_worth_crore')} Crore
- Total Debt: ₹{f.get('total_debt_crore')} Crore
- Auditor Opinion: {f.get('auditor_opinion')}
- Promoter Holding: {f.get('promoter_holding_pct')}%

GST & BANK:
- GST-Bank Mismatch: {state.get('gst_bank_mismatch_pct')}%
- Circular Trading: {'DETECTED - HIGH RISK' if state.get('circular_trading_detected') else 'Not detected'}

RESEARCH:
- Active Litigations: {len([c for c in state.get('litigation_data', []) if c.get('status') == 'pending'])}
- News Summary: {state.get('news_summary', 'No adverse news')[:300]}
- Promoter Status: {state.get('promoter_background')}
- RBI Flags: {', '.join(state.get('rbi_regulatory_flags', [])) or 'None'}

RULE VIOLATIONS TRIGGERED:
{chr(10).join(state.get('rule_violations', ['None']))}

RISK STRENGTHS:
{chr(10).join(state.get('risk_strengths', ['None']))}

QUALITATIVE NOTES (Credit Officer):
{state.get('qualitative_notes', 'None provided')}
Factory Capacity: {state.get('site_visit_capacity_pct', 'Not visited')}%
Management Assessment: {state.get('management_assessment', 'None')}

=== WRITE THE CREDIT APPRAISAL MEMO WITH THESE EXACT SECTIONS ===

1. EXECUTIVE SUMMARY (3-4 sentences, include decision and key rationale)

2. BORROWER PROFILE (company background, promoters, sector, CIN)

3. FIVE Cs ANALYSIS:
   a. CHARACTER (promoter integrity, track record, MCA/court findings)
   b. CAPACITY (cash flows, DSCR, repayment ability)
   c. CAPITAL (net worth, leverage, balance sheet strength)
   d. COLLATERAL (assets pledged, MCA charges, security coverage)
   e. CONDITIONS (sector outlook, macro factors, RBI regulations)

4. FINANCIAL ANALYSIS (tabular summary, trend analysis, ratio benchmarks)

5. GST & BANKING CONDUCT ANALYSIS

6. RISK ASSESSMENT & RED FLAGS (cite specific sources for each flag)

7. RECOMMENDATION
   - Decision: {state.get('decision')}
   - Loan Limit: ₹{state.get('recommended_loan_limit_crore')} Crore
   - Interest Rate: MCLR + {state.get('interest_rate_premium_bps')}bps
   - Covenants (if Conditional Approve): list specific conditions
   - Rejection Rationale (if Reject): cite exact rule violations triggered

8. DECLARATION
   This CAM was generated by the Intelli-Credit AI system. Final decision authority 
   rests with the authorized credit committee per RBI guidelines.
"""

def _compute_de(f):
    debt = f.get("total_debt_crore") or 0
    equity = f.get("net_worth_crore") or 1
    return round(debt/equity, 2) if equity > 0 else "N/A"
```

---

## 11. Module 6: FastAPI Backend

### Active API Surface (Current)

Primary backend routes are versioned and live under `backend/api/routes/*`:

- `POST /api/v1/companies` — create company context
- `POST /api/v1/companies/{id}/documents` — upload files
- `POST /api/v1/companies/{id}/dd-input` — due diligence submission
- `POST /api/v1/companies/{id}/analyze` — trigger end-to-end analysis
- `GET /api/v1/companies/{id}/status` — SSE status/log stream
- `GET /api/v1/companies/{id}/results` — merged decision payload
- `GET /api/v1/companies/{id}/explain` — explanation payload
- `GET /api/v1/companies/{id}/research` — normalized findings
- `GET /api/v1/companies/{id}/report` — CAM `.docx`
- `GET /api/v1/companies/{id}/report/pdf` — CAM `.pdf` (if available)
- `POST /api/v1/companies/{id}/chat` — RAG chat over CAM + documents
- `GET /api/v1/health`, `GET /api/v1/health/integrations` — readiness checks

Legacy compatibility routes remain mounted under `backend/routers/*`:
`/ingest`, `/run-pipeline`, `/pipeline-stream/{company_id}`, `/score/{company_id}`, `/cam/{company_id}`, `/chat`.

### Runtime Orchestration

The active runtime orchestrator is:

- `backend/core/pipeline_service.py` (`IntelliCreditPipeline`)

It runs:

1. ingestion (`core/ingestion/*`)
2. cross-validation and GST mismatch checks
3. web research (`core/research/*`)
4. feature engineering + ML scoring (`core/ml/*`)
5. CAM generation (`core/report/cam_generator.py`)
6. persistence to `analysis_runs`, `risk_scores`, `cam_outputs`, etc.

---

## 12. Module 7: Next.js Frontend Portal

### Page Structure

Current frontend uses App Router with product routes nested under `app/app/*`:

- `app/page.tsx` — marketing landing
- `app/about/page.tsx` — project architecture story
- `app/app/start/page.tsx` — starts session + company context
- `app/app/upload/page.tsx` — application details + documents + optional borrower input
- `app/app/notes/page.tsx` — due diligence notes for credit officer
- `app/app/pipeline/page.tsx` — live pipeline status stream
- `app/app/score/page.tsx` — score summary + SHAP
- `app/app/results/page.tsx` — full dashboard (Five Cs, anomalies, timeline, research)
- `app/app/explain/page.tsx` — decision explainability narrative
- `app/app/chat/page.tsx` — chat with CAM/data context
- `app/app/cam/page.tsx` — CAM preview + report download

### `app/app/pipeline/page.tsx` — Live Agent Progress
```typescript
// Streams /api/v1/companies/{companyId}/status using AgentProgressLog
// Shows step progress %, audit logs, and completion redirect to /app/score
```

### `app/app/score/page.tsx` — Score + SHAP
```typescript
// Horizontal bar chart showing SHAP feature contributions
// Uses RiskGauge + ShapChart components with API-backed values
```

### `components/ShapChart.tsx`
```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'

interface ShapEntry { feature: string; value: number }

export function ShapChart({ data }: { data: ShapEntry[] }) {
  return (
    <BarChart data={data} layout="vertical" width={600} height={400}>
      <XAxis type="number" domain={[-1, 1]} tickFormatter={(v) => v.toFixed(2)} />
      <YAxis type="category" dataKey="feature" width={180} />
      <Tooltip formatter={(v: number) => [v.toFixed(3), 'SHAP Value']} />
      <Bar dataKey="value">
        {data.map((entry, i) => (
          <Cell key={i} fill={entry.value > 0 ? '#ef4444' : '#22c55e'} />
        ))}
      </Bar>
    </BarChart>
  )
}
```

---

## 13. Database Schema

```sql
-- PostgreSQL Schema

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    cin VARCHAR(21),
    gstin VARCHAR(15),
    sector VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    file_path TEXT NOT NULL,
    doc_type VARCHAR(50),  -- ANNUAL_REPORT, GST_FILING, etc.
    extraction_method VARCHAR(20),  -- fitz/pdfplumber/qwen/sarvam/tesseract
    raw_text TEXT,
    extracted_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    rule_based_score FLOAT,
    ml_stress_probability FLOAT,
    final_risk_score FLOAT,
    risk_category VARCHAR(20),
    rule_violations JSONB,
    risk_strengths JSONB,
    shap_values JSONB,
    decision VARCHAR(30),
    recommended_limit_crore FLOAT,
    interest_premium_bps INTEGER,
    decision_rationale TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cam_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    cam_text TEXT,
    docx_path TEXT,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE qualitative_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    notes TEXT,
    factory_capacity_pct FLOAT,
    management_assessment TEXT,
    submitted_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    message TEXT,
    response TEXT,
    sources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    status VARCHAR(30) NOT NULL,
    current_step VARCHAR(100),
    progress_pct FLOAT NOT NULL DEFAULT 0,
    audit_log JSONB NOT NULL DEFAULT '[]'::jsonb,
    result_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE research_finding_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    finding_type VARCHAR(40) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL,
    summary TEXT NOT NULL,
    raw_snippet TEXT,
    confidence FLOAT NOT NULL DEFAULT 0.7,
    date_of_finding TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE due_diligence_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    payload JSONB NOT NULL,
    llm_insight JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 14. Qdrant Vector Store Setup

### `vector_store/qdrant_client.py`
```python
"""
Qdrant setup for semantic search over document chunks and research results.
Collection: document_chunks — for RAG over uploaded company documents
Collection: research_chunks — for RAG over web research results

Embedding model: BAAI/bge-m3 (multilingual, handles Indian language text)
Vector dimension: 1024
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import os
import uuid

client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
embed_model = SentenceTransformer("BAAI/bge-m3")
VECTOR_DIM = 1024

def init_collections():
    """Create Qdrant collections if they don't exist. Call on startup."""
    for collection_name in ["document_chunks", "research_chunks"]:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
            )

def upsert_document_chunks(embeddings: list, payloads: list):
    """Upsert document chunks with embeddings into Qdrant."""
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=emb, payload=pay)
        for emb, pay in zip(embeddings, payloads)
    ]
    client.upsert(collection_name="document_chunks", points=points)

def search_chunks(query: str, company_id: str, top_k: int = 5) -> list:
    """Semantic search over document chunks for a specific company."""
    query_vector = embed_model.encode(query).tolist()
    
    results = client.search(
        collection_name="document_chunks",
        query_vector=query_vector,
        limit=top_k,
        query_filter={
            "must": [{"key": "company_id", "match": {"value": company_id}}]
        }
    )
    
    return [{"chunk_text": r.payload["chunk_text"], 
             "doc_type": r.payload["doc_type"],
             "score": r.score} for r in results]
```

---

## 15. End-to-End Data Flow

```
Credit Officer starts new assessment
            ↓
POST /api/v1/companies
            ↓
POST /api/v1/companies/{id}/documents
            ↓
POST /api/v1/companies/{id}/dd-input
            ↓
POST /api/v1/companies/{id}/analyze
            ↓
GET /api/v1/companies/{id}/status (SSE)
  → OCR extraction
  → GST/bank/ITR reconciliation
  → research agent (MCA + eCourts + web/news)
  → scoring + explainability
  → CAM generation
            ↓
GET /api/v1/companies/{id}/results
  → decision + features + anomalies + due_diligence + audit_events
            ↓
GET /api/v1/companies/{id}/explain, /research, /report, /chat
  → explainability + research feed + CAM download + Q&A
```

Legacy equivalents (`/ingest`, `/run-pipeline`, `/pipeline-stream`) remain available,
but the frontend flow in this repository is primarily wired to `/api/v1/*`.

---

## 16. Indian Context: Key Rules & Domain Logic

### Critical Indian Banking Terminology to Implement

| Term | Meaning | How to Compute |
|------|---------|----------------|
| DSCR | Debt Service Coverage Ratio | EBITDA / (Principal + Interest repayment) |
| MPBF | Maximum Permissible Bank Finance | 0.75 × (Current Assets - Current Liabilities) |
| TOL/TNW | Total Outside Liabilities / Tangible Net Worth | Total Debt / (Net Worth - Intangibles) |
| NWC | Net Working Capital | Current Assets - Current Liabilities |
| DPG | Deferred Payment Guarantee | Contingent liability — reduce from net worth |
| GSTR-3B vs 2A | 3B = what company claims; 2A = what suppliers filed | Mismatch = ITC fraud risk |
| CIBIL Commercial | Business credit score (300-900) | Must be > 700 for healthy status |
| Wilful Defaulter | RBI blacklist | Search RBI's wilful defaulter list |

### GST-Specific Rules
```python
# GSTR-3B vs GSTR-2A mismatch logic
# GSTR-2A: Auto-populated from supplier's GSTR-1
# GSTR-3B: What borrower CLAIMS as ITC
# If GSTR-3B ITC > GSTR-2A by > 20% → potential fake ITC fraud

def check_itc_mismatch(gstr_3b_itc: float, gstr_2a_itc: float) -> bool:
    if not gstr_2a_itc:
        return False
    mismatch = (gstr_3b_itc - gstr_2a_itc) / gstr_2a_itc
    return mismatch > 0.20  # > 20% overclaim is a red flag
```

---

## 17. Testing Strategy

### Sample Test Company
Create a synthetic company profile in `data/sample/` with:
- `annual_report.pdf` — downloadable from NSE/BSE for any listed company
- `gst_data.json` — synthetic data generated by `ml/synthetic_data.py`
- `bank_statement.pdf` — use any public template
- `legal_notice.pdf` — synthetic DRT notice

### Unit Tests
```python
# Test rules engine
def test_dscr_below_1_triggers_critical():
    financials = {"dscr": 0.85}
    score, violations, strengths, critical = apply_rules(financials)
    assert critical == True
    assert any("DSCR" in v for v in violations)

# Test GST mismatch
def test_gst_mismatch_detection():
    mismatch = check_gst_bank_mismatch(118_00_00_000, 89_00_00_000)
    assert mismatch > 20.0

# Test circular trading
def test_circular_trade_detection():
    txns = [
        {"seller_gstin": "A", "buyer_gstin": "B", "value": 1000000},
        {"seller_gstin": "B", "buyer_gstin": "C", "value": 900000},
        {"seller_gstin": "C", "buyer_gstin": "A", "value": 800000},
    ]
    is_circular, entities = detect_circular_trading(txns)
    assert is_circular == True
    assert len(entities) == 3
```

---

## 18. Demo Script for Judges

### 5-Minute Demo Flow
```
0:00 — Open Next.js portal → "Sharma Textiles Pvt Ltd"
0:30 — Upload 4 documents (annual report, GST, bank statement, legal notice in Hindi)
1:00 — Click "Run Credit Analysis" → Live agent log streams in:
         ▸ [Router] Classified 4 documents
         ▸ [Ingestion] Annual report: 8 financial ratios extracted via pdfplumber
         ▸ [Ingestion] Legal notice (Hindi): extracted via Sarvam Vision
         ▸ [GST] Mismatch detected: 24.6%
         ▸ [Research] DRT case found on eCourts
         ▸ [Research] NPA news found on Economic Times
         ⏸ Waiting for qualitative input...
2:00 — Enter: "Factory at 65% capacity. MD was evasive on payables."
2:20 — Click Resume → scoring runs → REJECT decision appears
2:30 — Click SHAP Chart → show DSCR and DRT case as top risk drivers
3:00 — Download CAM PDF → open and show professional document
3:30 — Chat interface: "Why was the legal notice flagged?"
         → AI explains citing specific text from the Hindi DRT notice
4:00 — Walk judge through explainability: point to specific rule that caused REJECT
4:30 — Q&A
```

### Key Answers for Judge Questions

**"How is this different from a simple PDF reader + GPT?"**
→ Three-layer architecture: deterministic rules cannot be overridden by LLM hallucination. The LLM only explains — it never scores.

**"How do you handle Indian language documents?"**
→ Sarvam Vision API with 87.36% word accuracy across 22 Indian languages — best-in-class on the Sarvam Indic OCR Bench.

**"How do you prevent the AI from making wrong credit decisions?"**
→ Critical rules are hard stops. If DSCR < 1.0 or a DRT case exists, it's REJECT regardless of what the LLM or ML model says. Rules govern.

**"Is this RBI compliant?"**
→ The MPBF calculation follows RBI's Tandon Committee norms. DSCR thresholds follow IBA (Indian Banks' Association) guidelines. Decision audit trail is fully preserved in PostgreSQL.

---

*Built for IIT Hyderabad × Vivriti Capital Intelli-Credit Hackathon — March 2026*
*Stack: Python · FastAPI · LangGraph · Sarvam Vision · Gemini · XGBoost · SHAP · Next.js · PostgreSQL · Qdrant*


