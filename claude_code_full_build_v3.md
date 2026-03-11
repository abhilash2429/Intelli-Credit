# INTELLI-CREDIT — CLAUDE CODE BUILD PROMPT
# IIT Hyderabad × Vivriti Capital Hackathon | Final Demo: March 22, 2026
# Today: March 11, 2026 — 11 days remaining
#
# ══════════════════════════════════════════════════════════════════════════════
# HOW TO USE THIS PROMPT
# ══════════════════════════════════════════════════════════════════════════════
# 1. Open Claude Code in the project root (where docker-compose.yml lives).
# 2. Paste this entire file as your first message.
# 3. Claude Code will read files, implement in order, and verify each phase.
# 4. Do NOT skip phases. Do NOT write code before reading the files it modifies.
# ══════════════════════════════════════════════════════════════════════════════

---

## PROJECT CONTEXT (GROUND TRUTH)

You are working on **Intelli-Credit**, a full-stack AI credit appraisal engine.

**Current tech stack (confirmed):**
- Backend: FastAPI + SQLAlchemy async + Celery + pdfplumber + PyMuPDF + Qwen2.5-VL + XGBoost + SHAP + Qdrant + Firecrawl
- Frontend: Next.js 14 App Router + React 18 + TailwindCSS + Recharts + Zustand + TanStack Query
- DB: PostgreSQL (core tables: companies, documents, risk_scores, cam_outputs, analysis_runs, research_finding_records, due_diligence_records, chat_history, qualitative_inputs)
- Vector: Qdrant (collections: document_chunks, research_chunks) — embeddings: BAAI/bge-m3
- Primary pipeline: `backend/core/pipeline_service.py` (NOT the LangGraph agents)
- API contract: `/api/v1/*` with standard response envelope — DO NOT BREAK THIS

**Confirmed existing frontend pages:**
- `/app/start` — company creation
- `/app/upload` — document upload
- `/app/notes` — due diligence notes
- `/app/pipeline` — SSE progress
- `/app/score` — RiskGauge + SHAP
- `/app/results` — Five Cs, anomalies, research
- `/app/explain`, `/app/chat`, `/app/cam`

**Confirmed existing ingestion parsers:**
- `backend/core/ingestion/pdf_parser.py` (annual reports)
- `backend/core/ingestion/gst_parser.py`
- `backend/core/ingestion/bank_statement.py`
- `backend/core/ingestion/itr_parser.py`
- `backend/core/ingestion/cross_validator.py`

**Confirmed existing research:**
- `backend/core/research/web_agent.py` (mock/live)
- `backend/core/research/firecrawl_client.py`
- `backend/core/research/finding_extractor.py`
- `backend/core/research/search_strategies.py`

---

## GAP ANALYSIS vs HACKATHON REQUIREMENTS

### Stage 1 — Entity Onboarding
| Required | Current Status |
|---|---|
| CIN field | ✅ EXISTS — companies table has `cin` |
| PAN field | ❌ MISSING — not in companies table |
| Sector field | ✅ EXISTS |
| Turnover field | ❌ MISSING |
| Loan Type/Amount/Tenure/Interest | ❌ MISSING — no loan_applications table |
| Multi-step form UX | ❌ MISSING — /app/start is single step |

### Stage 2 — Document Ingestion
| Required Doc Type | Current Status |
|---|---|
| Annual Reports (P&L, BS, CF) | ✅ pdf_parser.py handles this |
| ALM Statement | ❌ MISSING — no parser |
| Shareholding Pattern | ❌ MISSING — no parser |
| Borrowing Profile | ❌ MISSING — no parser |
| Portfolio Cuts / Performance | ❌ MISSING — no parser |

### Stage 3 — Classification + HITL + Schema
| Required | Current Status |
|---|---|
| Auto-classify uploaded docs | ❌ MISSING — no classifier runs on upload |
| HITL approve/deny/edit | ❌ MISSING — no such UI or API endpoint |
| Dynamic schema config | ❌ MISSING — schemas hardcoded in parsers |
| Re-extract per custom schema | ❌ MISSING |

### Stage 4 — Secondary Analysis + Report
| Required | Current Status |
|---|---|
| Secondary research (news/legal/macro) | ✅ PARTIAL — web_agent.py exists |
| Sector/subsector/macro trends | ❌ MISSING — no sector macro analysis |
| Triangulate research vs financials | ❌ PARTIAL — cross_validator.py is financial only |
| Reasoning engine | ✅ PARTIAL — SHAP + rules engine exists |
| SWOT analysis | ❌ MISSING |
| Downloadable investment report | ❌ MISSING — only CAM DOCX exists |

---

## IMPLEMENTATION PLAN (11 PHASES)

Complete phases IN ORDER. Each phase depends on the previous.

---

## PHASE 0 — MANDATORY READING (do this before writing a single line)

```bash
# Read before touching anything
cat README.md
cat backend/models/db_models.py
cat backend/core/pipeline_service.py
cat backend/api/routes/companies.py 2>/dev/null || cat backend/api/routes/company.py
cat backend/api/routes/upload.py 2>/dev/null || grep -r "documents" backend/api/routes/ --include="*.py" -l
cat backend/schemas/credit.py 2>/dev/null || ls backend/schemas/
cat frontend/app/app/start/page.tsx
cat frontend/lib/api.ts
cat frontend/store/analysisStore.ts
```

Produce a **READ REPORT** listing:
- Exact column names on the `companies` table ORM model
- The exact function signature of the upload handler
- The exact Pydantic schema for company creation
- The exact response envelope format used (e.g., `{"data": ..., "request_id": ...}`)
- Any existing document type enum or constants file

---

## PHASE 1 — DATABASE: ADD MISSING COLUMNS AND TABLES

**Read `backend/models/db_models.py` first. Then:**

### 1A — Add missing columns to `Company` model

Find the existing `Company` ORM class. Add ONLY these missing columns (do not remove or rename existing ones):

```python
# Add to Company class — check each doesn't already exist first
pan_number            = Column(String(10), nullable=True)
annual_turnover_cr    = Column(Float, nullable=True)       # ₹ Crore
employee_count        = Column(Integer, nullable=True)
year_of_incorporation = Column(Integer, nullable=True)
registered_address    = Column(Text, nullable=True)
```

### 1B — Create `LoanApplication` model

Add this new model to `db_models.py`:

```python
class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id          = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    loan_type           = Column(String(50), nullable=False)   # TERM_LOAN, WORKING_CAPITAL, CC, OD, NCD
    loan_amount_cr      = Column(Float, nullable=False)        # ₹ Crore
    tenure_months       = Column(Integer, nullable=False)
    proposed_rate_pct   = Column(Float, nullable=True)         # % p.a.
    repayment_mode      = Column(String(30), nullable=True)    # EMI, BULLET, QUARTERLY
    purpose             = Column(Text, nullable=True)
    collateral_type     = Column(String(50), nullable=True)    # PROPERTY, STOCKS, FD, NONE
    collateral_value_cr = Column(Float, nullable=True)
    status              = Column(String(20), default="PENDING", index=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="loan_applications")
```

Also add to `Company` class:
```python
loan_applications = relationship("LoanApplication", back_populates="company", lazy="selectin")
```

### 1C — Create `DocumentClassification` model

```python
class DocumentClassification(Base):
    __tablename__ = "document_classifications"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id         = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id          = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Auto-classification
    auto_type           = Column(String(50), nullable=False)   # ALM, SHAREHOLDING, BORROWING_PROFILE, ANNUAL_REPORT, PORTFOLIO
    auto_confidence     = Column(Float, nullable=False, default=0.5)
    auto_reasoning      = Column(Text, nullable=True)

    # HITL
    human_approved      = Column(Boolean, nullable=True)       # None=pending, True=approved, False=rejected
    human_type_override = Column(String(50), nullable=True)    # set when user overrides auto_type
    human_notes         = Column(Text, nullable=True)
    reviewed_at         = Column(DateTime(timezone=True), nullable=True)

    # Dynamic schema and extraction result
    custom_schema       = Column(JSONB, nullable=True)
    extracted_data      = Column(JSONB, nullable=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
```

### 1D — Create `SwotAnalysis` model

```python
class SwotAnalysis(Base):
    __tablename__ = "swot_analyses"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id    = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id        = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=True)

    strengths     = Column(JSONB, nullable=True)    # list of {point, evidence, source}
    weaknesses    = Column(JSONB, nullable=True)
    opportunities = Column(JSONB, nullable=True)
    threats       = Column(JSONB, nullable=True)

    sector_outlook    = Column(Text, nullable=True)
    macro_signals     = Column(JSONB, nullable=True)   # {rbi_rate, inflation, sector_growth}
    investment_thesis = Column(Text, nullable=True)
    recommendation    = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 1E — Apply and verify

```bash
# Verify tables created (assuming create_all pattern or run alembic if used)
python3 -c "
import asyncio, os
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/intellicredit')
from backend.database import engine, Base
from backend.models import db_models  # ensure all models imported
async def verify():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    print('Tables:', sorted(Base.metadata.tables.keys()))
asyncio.run(verify())
"
```

Expected output includes: `loan_applications`, `document_classifications`, `swot_analyses`

---

## PHASE 2 — BACKEND: LOAN APPLICATION API

**Read the existing companies router first to understand response envelope format.**

Create `backend/api/routes/loan.py`:

```python
"""Loan application CRUD for the entity onboarding stage."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db  # use existing dep — check actual import path
from backend.models.db_models import Company, LoanApplication

router = APIRouter(prefix="/api/v1/companies/{company_id}/loan", tags=["loan"])

# ── helpers ────────────────────────────────────────────────────────────────
def _loan_to_dict(loan: LoanApplication) -> dict[str, Any]:
    return {
        "loan_id": str(loan.id),
        "company_id": str(loan.company_id),
        "loan_type": loan.loan_type,
        "loan_amount_cr": loan.loan_amount_cr,
        "tenure_months": loan.tenure_months,
        "proposed_rate_pct": loan.proposed_rate_pct,
        "repayment_mode": loan.repayment_mode,
        "purpose": loan.purpose,
        "collateral_type": loan.collateral_type,
        "collateral_value_cr": loan.collateral_value_cr,
        "status": loan.status,
        "created_at": loan.created_at.isoformat() if loan.created_at else None,
    }

def _wrap(data):
    """Match the existing API response envelope. Adjust if envelope is different."""
    return {"data": data, "success": True}

# ── routes ──────────────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_loan(
    company_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, uuid.UUID(company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    loan = LoanApplication(
        company_id=uuid.UUID(company_id),
        loan_type=payload["loan_type"],
        loan_amount_cr=float(payload["loan_amount_cr"]),
        tenure_months=int(payload["tenure_months"]),
        proposed_rate_pct=payload.get("proposed_rate_pct"),
        repayment_mode=payload.get("repayment_mode"),
        purpose=payload.get("purpose"),
        collateral_type=payload.get("collateral_type"),
        collateral_value_cr=payload.get("collateral_value_cr"),
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)
    return _wrap(_loan_to_dict(loan))


@router.get("")
async def get_loan(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LoanApplication)
        .where(LoanApplication.company_id == uuid.UUID(company_id))
        .order_by(LoanApplication.created_at.desc())
        .limit(1)
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="No loan application found")
    return _wrap(_loan_to_dict(loan))


@router.patch("")
async def update_loan(
    company_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoanApplication)
        .where(LoanApplication.company_id == uuid.UUID(company_id))
        .order_by(LoanApplication.created_at.desc())
        .limit(1)
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="No loan application found")

    updatable = ["loan_type", "loan_amount_cr", "tenure_months", "proposed_rate_pct",
                 "repayment_mode", "purpose", "collateral_type", "collateral_value_cr"]
    for field in updatable:
        if field in payload:
            setattr(loan, field, payload[field])

    loan.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(loan)
    return _wrap(_loan_to_dict(loan))
```

**Register in `backend/main.py`:**
```python
from backend.api.routes.loan import router as loan_router
app.include_router(loan_router)
```

**Also update `POST /api/v1/companies` to accept new fields.** Find the companies creation schema and add:
```python
pan_number: Optional[str] = None
annual_turnover_cr: Optional[float] = None
year_of_incorporation: Optional[int] = None
registered_address: Optional[str] = None
```

---

## PHASE 3 — BACKEND: AUTO-CLASSIFIER + 4 NEW PARSERS

### 3A — Document Classifier

Create `backend/core/ingestion/document_classifier.py`:

```python
"""
Auto-classify uploaded documents into the 5 required types.
Strategy: filename keywords first (deterministic) → LLM content analysis (fallback).
"""
from __future__ import annotations
import re
import json
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

DOC_TYPES = {
    "ALM": "Asset-Liability Management Statement",
    "SHAREHOLDING": "Shareholding Pattern",
    "BORROWING_PROFILE": "Borrowing Profile / Debt Schedule",
    "ANNUAL_REPORT": "Annual Report (P&L / Balance Sheet / Cashflow)",
    "PORTFOLIO": "Portfolio Cuts / Performance Data",
}

# Lower-cased keyword fragments → doc type (checked against normalised filename)
_FILENAME_RULES: list[tuple[list[str], str]] = [
    (["alm", "asset_liab", "assetliab", "liquidity", "maturity_profile", "maturity_bucket"], "ALM"),
    (["shareholding", "share_pattern", "sharehol", "promoter_holding", "sh_pattern"], "SHAREHOLDING"),
    (["borrowing", "debt_schedule", "credit_profile", "loan_profile", "borrowal", "facility_list", "credit_facilities"], "BORROWING_PROFILE"),
    (["annual_report", "annual report", "p&l", "profit_loss", "balance_sheet", "cashflow",
      "financial_statement", "_ar_", "fy20", "fy21", "fy22", "fy23", "fy24", "fy25", "ar_fy", "annual"], "ANNUAL_REPORT"),
    (["portfolio", "performance", "aum", "npa_report", "collection", "disbursement",
      "portfolio_cut", "fund_performance", "port_cut"], "PORTFOLIO"),
]

_CONTENT_PROMPT = """\
Classify this financial document into exactly one of:
  ALM            - Asset-Liability Management: maturity buckets, liquidity gaps
  SHAREHOLDING   - Shareholding pattern: promoter/public/FII holdings, pledge data
  BORROWING_PROFILE - Debt schedule: existing facilities, lender names, repayment
  ANNUAL_REPORT  - Annual report: P&L, Balance Sheet, Cash Flow statements
  PORTFOLIO      - Portfolio performance: AUM, NPA %, collection efficiency, disbursements

Filename: {filename}
First 2000 characters:
{content}

Reply ONLY with this JSON — no markdown, no extra text:
{{"doc_type": "<one of the 5 types above>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}
"""


async def classify_document(file_path: str, filename: str) -> Tuple[str, float, str]:
    """
    Returns (doc_type, confidence, reasoning).
    Tries filename heuristics first; falls back to LLM content analysis.
    """
    # Step 1: Filename heuristics
    normalised = re.sub(r"[\s\-\.]", "_", filename.lower())
    for keywords, doc_type in _FILENAME_RULES:
        if any(kw in normalised for kw in keywords):
            return doc_type, 0.92, f"Filename matched keyword pattern for {doc_type}"

    # Step 2: Content-based LLM classification
    content = _preview_file(file_path, max_chars=2000)
    prompt = _CONTENT_PROMPT.format(filename=filename, content=content)

    try:
        from backend.agents.llm.llm_client import llm_call  # existing LLM client
        result = await llm_call(prompt=prompt, task="classification")
        cleaned = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(cleaned)
        doc_type = parsed.get("doc_type", "ANNUAL_REPORT")
        if doc_type not in DOC_TYPES:
            doc_type = "ANNUAL_REPORT"
        return doc_type, float(parsed.get("confidence", 0.55)), parsed.get("reasoning", "LLM classification")
    except Exception as e:
        logger.warning(f"Classification LLM failed for {filename}: {e}")
        return "ANNUAL_REPORT", 0.40, f"Classification failed — defaulted. Error: {str(e)[:80]}"


def _preview_file(file_path: str, max_chars: int = 2000) -> str:
    try:
        if file_path.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages = pdf.pages[:3]
                return "\n".join((p.extract_text() or "") for p in pages)[:max_chars]
        elif file_path.endswith((".xlsx", ".xls")):
            import pandas as pd
            df = pd.read_excel(file_path, nrows=25)
            return df.to_string()[:max_chars]
        elif file_path.endswith(".csv"):
            import pandas as pd
            return pd.read_csv(file_path, nrows=25).to_string()[:max_chars]
    except Exception as e:
        logger.warning(f"Preview extraction failed: {e}")
    return ""
```

### 3B — ALM Parser

Create `backend/core/ingestion/alm_parser.py`:

```python
"""ALM (Asset-Liability Management) Statement Parser."""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this Asset-Liability Management (ALM) statement for an Indian NBFC/bank.

Extract ONLY into this exact JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "currency": "INR",
  "maturity_buckets": [
    {{
      "bucket": "<1 day | 2-7 days | 8-14 days | 15-30 days | 31-90 days | 91-180 days | 181d-1yr | 1-3yr | 3-5yr | >5yr>",
      "assets_cr": <float or null>,
      "liabilities_cr": <float or null>,
      "gap_cr": <float or null>,
      "cumulative_gap_cr": <float or null>
    }}
  ],
  "total_assets_cr": <float or null>,
  "total_liabilities_cr": <float or null>,
  "structural_liquidity_gap_cr": <float or null>,
  "liquidity_coverage_ratio": <float or null>,
  "net_stable_funding_ratio": <float or null>,
  "concentration_risk": {{
    "top_3_lender_pct": <float or null>,
    "short_term_borrowing_pct": <float or null>
  }},
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>,
  "extraction_notes": "<any caveats>"
}}

STRICT RULES:
- All monetary values in ₹ Crore. Convert if in Lakh (÷100) or Million (÷10).
- Do NOT invent numbers. Use null for missing fields.
- Flag if short-term borrowing > 40%% as a red_flag.
- Flag if cumulative gap is deeply negative in < 30 days buckets.

Document text:
{text}
"""

async def parse_alm_statement(file_path: str) -> dict:
    text = _extract_text(file_path)
    from backend.agents.llm.llm_client import llm_call
    result = await llm_call(prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        logger.warning("ALM parse failed — returning raw partial")
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": result[:300]}


def _extract_text(file_path: str) -> str:
    try:
        if file_path.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif file_path.endswith((".xlsx", ".xls")):
            import pandas as pd
            dfs = pd.read_excel(file_path, sheet_name=None)
            return "\n\n".join(f"[{k}]\n{v.to_string()}" for k, v in dfs.items())
        elif file_path.endswith(".csv"):
            import pandas as pd
            return pd.read_csv(file_path).to_string()
    except Exception as e:
        return f"[Read error: {e}]"
    return ""
```

### 3C — Shareholding Pattern Parser

Create `backend/core/ingestion/shareholding_parser.py`:

```python
"""Shareholding Pattern Parser — promoter/public/FII holdings, pledge data."""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this shareholding pattern document for an Indian listed/unlisted company.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "company_name": "<string or null>",
  "total_shares": <integer or null>,
  "promoter_holding_pct": <float>,
  "total_pledged_pct": <float or null>,
  "categories": [
    {{
      "category": "<Promoter & Promoter Group | FII/FPI | MF/DII | Public-Non-Institutional | ESOP | Other>",
      "shares": <integer or null>,
      "percentage": <float>,
      "pledged_shares": <integer or null>,
      "pledged_pct": <float or null>
    }}
  ],
  "top_shareholders": [
    {{"rank": <int>, "name": "<string>", "shares": <integer>, "percentage": <float>}}
  ],
  "changes_qoq": [
    {{"category": "<string>", "prev_pct": <float>, "curr_pct": <float>, "delta": <float>}}
  ],
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- promoter_holding_pct = sum of all promoter sub-categories.
- Flag if total_pledged_pct > 25%%.
- Flag if promoter_holding_pct < 26%%.
- Flag if single non-promoter entity holds > 15%%.
- Do NOT invent numbers. Use null where unavailable.

Document text:
{text}
"""

async def parse_shareholding_pattern(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.agents.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await llm_call(prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": result[:300]}
```

### 3D — Borrowing Profile Parser

Create `backend/core/ingestion/borrowing_profile_parser.py`:

```python
"""Borrowing Profile / Debt Schedule Parser."""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this borrowing profile / debt schedule document for an Indian company.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "total_outstanding_cr": <float or null>,
  "secured_debt_cr": <float or null>,
  "unsecured_debt_cr": <float or null>,
  "facilities": [
    {{
      "lender_name": "<string>",
      "facility_type": "<TERM_LOAN | CC | OD | NCD | DEBENTURE | BOND | OTHERS>",
      "sanctioned_cr": <float or null>,
      "outstanding_cr": <float>,
      "rate_pct": <float or null>,
      "repayment": "<string or null>",
      "security": "<string or null>",
      "maturity_date": "<YYYY-MM-DD or null>",
      "overdue": <boolean>
    }}
  ],
  "debt_maturity_profile": {{
    "within_1yr_pct": <float or null>,
    "1_3yr_pct": <float or null>,
    "3_5yr_pct": <float or null>,
    "beyond_5yr_pct": <float or null>
  }},
  "avg_cost_of_debt_pct": <float or null>,
  "existing_dscr": <float or null>,
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- All amounts in ₹ Crore. Convert if in Lakh (÷100).
- Flag any overdue facility.
- Flag if short-term (within_1yr_pct) > 40%%.
- Flag if no security/collateral provided.

Document text:
{text}
"""

async def parse_borrowing_profile(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.agents.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await llm_call(prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": result[:300]}
```

### 3E — Portfolio Performance Parser

Create `backend/core/ingestion/portfolio_parser.py`:

```python
"""Portfolio Cuts / Performance Data Parser — for NBFCs and financial entities."""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_PROMPT = """\
Parse this portfolio performance / portfolio cuts document for an Indian NBFC or financial entity.

Extract ONLY this JSON — no markdown, no extra text:
{{
  "report_date": "<YYYY-MM-DD or null>",
  "aum_cr": <float or null>,
  "disbursements_cr": <float or null>,
  "borrower_count": <integer or null>,
  "average_ticket_size_lakhs": <float or null>,
  "portfolio_mix": [
    {{"segment": "<string>", "aum_cr": <float>, "pct": <float>}}
  ],
  "geographic_mix": [
    {{"state": "<string>", "pct": <float>}}
  ],
  "asset_quality": {{
    "gnpa_cr": <float or null>,
    "gnpa_pct": <float or null>,
    "nnpa_cr": <float or null>,
    "nnpa_pct": <float or null>,
    "provision_coverage_pct": <float or null>,
    "stage_1_pct": <float or null>,
    "stage_2_pct": <float or null>,
    "stage_3_pct": <float or null>
  }},
  "collection_efficiency_pct": <float or null>,
  "yield_on_portfolio_pct": <float or null>,
  "cost_of_funds_pct": <float or null>,
  "nim_pct": <float or null>,
  "roe_pct": <float or null>,
  "roa_pct": <float or null>,
  "capital_adequacy_ratio_pct": <float or null>,
  "red_flags": ["<string>"],
  "extraction_confidence": <0.0-1.0>
}}

STRICT RULES:
- All amounts in ₹ Crore.
- Flag if GNPA > 5%%.
- Flag if collection_efficiency < 90%%.
- Flag if stage_3_pct > 5%%.

Document text:
{text}
"""

async def parse_portfolio_performance(file_path: str) -> dict:
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.agents.llm.llm_client import llm_call
    text = _extract_text(file_path)
    result = await llm_call(prompt=_PROMPT.format(text=text[:9000]), task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        return {"error": "parse_failed", "extraction_confidence": 0.0, "raw_snippet": result[:300]}
```

### 3F — Schema-Based Dynamic Extractor

Create `backend/core/ingestion/schema_extractor.py`:

```python
"""
Dynamic Schema Extractor.
Given a user-defined schema + file, extracts data into that exact schema.
Used when credit officer customises the output fields.
"""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_PROMPT = """\
Extract data from this document into the user-defined schema below.

SCHEMA (extract ONLY these fields, using exact field names and types):
{schema_description}

RULES:
- Output ONLY a flat JSON object with the field names above as keys.
- Use null for any field not found in the document.
- For float fields: output numbers, not strings. No commas in numbers.
- For date fields: use YYYY-MM-DD format.
- Do NOT add extra fields. Do NOT rename fields.
- Do NOT invent data.

Document content:
{content}
"""

async def extract_with_schema(file_path: str, doc_type: str, schema: dict) -> dict:
    """
    schema format:
    {
      "fields": [
        {"name": "revenue_fy25_cr", "type": "float", "description": "Revenue FY25 in ₹ Crore"},
        {"name": "auditor_name", "type": "string", "description": "Name of statutory auditor"}
      ]
    }
    """
    from backend.core.ingestion.alm_parser import _extract_text
    from backend.agents.llm.llm_client import llm_call

    fields = schema.get("fields", [])
    if not fields:
        return {"error": "empty_schema"}

    schema_desc = "\n".join(
        f"  - {f['name']} ({f['type']}): {f.get('description', '')}"
        for f in fields
    )
    content = _extract_text(file_path)
    prompt = _PROMPT.format(schema_description=schema_desc, content=content[:10000])

    result = await llm_call(prompt=prompt, task="extraction")
    try:
        return json.loads(re.sub(r"```json|```", "", result).strip())
    except Exception:
        return {"error": "extraction_failed", "raw_snippet": result[:300]}
```

---

## PHASE 4 — BACKEND: CLASSIFICATION + HITL API

Create `backend/api/routes/classification.py`:

```python
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

from backend.api.deps import get_db
from backend.models.db_models import DocumentClassification, Document

router = APIRouter(
    prefix="/api/v1/companies/{company_id}/classifications",
    tags=["classification"],
)


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
        "reviewed_at": clf.reviewed_at.isoformat() if clf.reviewed_at else None,
        "custom_schema": clf.custom_schema,
        "has_extracted_data": clf.extracted_data is not None,
    }


@router.get("")
async def list_classifications(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all classifications for company documents. Called when HITL review page loads."""
    result = await db.execute(
        select(DocumentClassification)
        .where(DocumentClassification.company_id == uuid.UUID(company_id))
        .order_by(DocumentClassification.created_at.asc())
    )
    clfs = result.scalars().all()

    items = []
    for clf in clfs:
        # Get filename from documents table
        doc = await db.get(Document, clf.document_id)
        filename = doc.file_path.split("/")[-1] if doc else "unknown"
        items.append(_clf_to_dict(clf, filename))

    # Summary stats
    total = len(items)
    approved = sum(1 for i in items if i["human_approved"] is True)
    pending = sum(1 for i in items if i["human_approved"] is None)
    rejected = sum(1 for i in items if i["human_approved"] is False)

    return {
        "data": {
            "classifications": items,
            "summary": {
                "total": total,
                "approved": approved,
                "pending": pending,
                "rejected": rejected,
                "all_reviewed": pending == 0,
            }
        },
        "success": True,
    }


@router.patch("/{classification_id}")
async def update_classification(
    company_id: str,
    classification_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    HITL endpoint.

    Actions:
    - {"action": "approve"}
    - {"action": "reject"}
    - {"action": "override", "new_type": "ALM", "notes": "optional reason"}
    - {"action": "set_schema", "schema": {"fields": [{"name":"...", "type":"...", "description":"..."}]}}
    """
    clf = await db.get(DocumentClassification, uuid.UUID(classification_id))
    if not clf or str(clf.company_id) != company_id:
        raise HTTPException(status_code=404, detail="Classification not found")

    action = payload.get("action")
    now = datetime.now(timezone.utc)

    VALID_TYPES = {"ALM", "SHAREHOLDING", "BORROWING_PROFILE", "ANNUAL_REPORT", "PORTFOLIO"}

    if action == "approve":
        clf.human_approved = True
        clf.reviewed_at = now
    elif action == "reject":
        clf.human_approved = False
        clf.reviewed_at = now
    elif action == "override":
        new_type = payload.get("new_type", "").upper()
        if new_type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid doc type. Must be one of: {VALID_TYPES}")
        clf.human_type_override = new_type
        clf.human_approved = True
        clf.human_notes = payload.get("notes")
        clf.reviewed_at = now
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
    return {"data": _clf_to_dict(clf, filename), "success": True}


@router.post("/{classification_id}/extract")
async def trigger_extraction(
    company_id: str,
    classification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger (re-)extraction using the custom_schema configured by the user.
    Returns extracted JSON data and stores it on the record.
    """
    clf = await db.get(DocumentClassification, uuid.UUID(classification_id))
    if not clf or str(clf.company_id) != company_id:
        raise HTTPException(status_code=404, detail="Classification not found")
    if not clf.custom_schema:
        raise HTTPException(status_code=400, detail="Set a custom schema first via set_schema action")
    if clf.human_approved is False:
        raise HTTPException(status_code=400, detail="Cannot extract from a rejected document")

    doc = await db.get(Document, clf.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document file not found")

    from backend.core.ingestion.schema_extractor import extract_with_schema
    effective_type = clf.human_type_override or clf.auto_type
    extracted = await extract_with_schema(
        file_path=doc.file_path,
        doc_type=effective_type,
        schema=clf.custom_schema,
    )
    clf.extracted_data = extracted
    await db.commit()

    return {"data": {"classification_id": classification_id, "extracted_data": extracted}, "success": True}
```

**Register in `backend/main.py`:**
```python
from backend.api.routes.classification import router as classification_router
app.include_router(classification_router)
```

---

## PHASE 5 — HOOK CLASSIFIER INTO UPLOAD

**Read the upload handler first.** Find where `POST /api/v1/companies/{company_id}/documents` saves the file and creates the `Document` DB record. After that `await db.commit()` line, add:

```python
# Auto-classify document immediately after save
try:
    from backend.core.ingestion.document_classifier import classify_document
    from backend.models.db_models import DocumentClassification

    auto_type, confidence, reasoning = await classify_document(
        file_path=saved_file_path,          # adjust to the actual variable name
        filename=original_filename,         # adjust to the actual variable name
    )

    clf = DocumentClassification(
        document_id=document.id,            # adjust to the actual document ORM object
        company_id=uuid.UUID(company_id),
        auto_type=auto_type,
        auto_confidence=confidence,
        auto_reasoning=reasoning,
        human_approved=None,                # awaiting HITL review
    )
    db.add(clf)
    await db.commit()
    logger.info(
        f"[Upload] {original_filename} → classified as {auto_type} "
        f"(confidence={confidence:.0%})"
    )
except Exception as exc:
    logger.error(f"[Upload] Classification failed for {original_filename}: {exc}")
    # Do NOT fail the upload if classification fails
```

---

## PHASE 6 — SWOT ENGINE

Create `backend/core/research/swot_engine.py`:

```python
"""
SWOT Analysis Engine.
Generates evidence-backed SWOT from extracted financials + research findings + sector context.
"""
from __future__ import annotations
import re, json, logging
logger = logging.getLogger(__name__)

_SWOT_PROMPT = """\
You are a senior credit analyst at a top Indian investment bank.
Generate a structured SWOT analysis for this loan/investment decision.

COMPANY: {company_name}
SECTOR: {sector}
LOAN: ₹{loan_amount_cr} Cr {loan_type} | Tenure: {tenure_months} months

KEY FINANCIAL METRICS:
{financials}

RESEARCH FINDINGS:
{research}

SECTOR / MACRO CONTEXT:
{macro}

RULES (strictly follow):
1. Every SWOT point MUST cite a specific number or fact from the data above.
2. Generic points like "experienced management" with no evidence are FORBIDDEN.
3. Minimum 3 points per quadrant, maximum 5.
4. Opportunities and Threats should reference sector/macro context, not just company data.

Reply ONLY with this JSON — no markdown, no extra text:
{{
  "strengths": [
    {{"point": "<specific claim>", "evidence": "<exact number or fact>", "source": "<document type>"}}
  ],
  "weaknesses": [
    {{"point": "<specific claim>", "evidence": "<exact number or fact>", "source": "<document type>"}}
  ],
  "opportunities": [
    {{"point": "<specific claim>", "evidence": "<macro/sector fact>", "source": "Sector Research"}}
  ],
  "threats": [
    {{"point": "<specific claim>", "evidence": "<risk factor>", "source": "Research / Market"}}
  ],
  "sector_outlook": "<2-3 sentences on sector and macro context>",
  "macro_signals": {{
    "rbi_repo_rate_pct": <float or null>,
    "india_gdp_growth_pct": <float or null>,
    "sector_credit_growth_pct": <float or null>,
    "inflation_cpi_pct": <float or null>
  }},
  "investment_thesis": "<1 sentence summary of the credit case>",
  "recommendation": "<2-3 sentence overall recommendation>"
}}
"""

_MACRO_PROMPT = """\
Provide current (early 2026) sector and macro context for an Indian {sector} company.

Cover briefly:
1. RBI repo rate (as of early 2026)
2. India GDP growth rate
3. {sector} sector growth trends and headwinds
4. Key regulatory risks for {sector}
5. Competitive landscape signals

Be concise and factual. Focus on what matters for a credit/investment decision.
"""


async def generate_swot(
    company_name: str,
    sector: str,
    loan_amount_cr: float,
    loan_type: str,
    tenure_months: int,
    extracted_financials: dict,
    research_findings: list,
) -> dict:
    from backend.agents.llm.llm_client import llm_call

    # Step 1: Sector macro context
    try:
        macro_text = await llm_call(
            prompt=_MACRO_PROMPT.format(sector=sector),
            task="research",
        )
    except Exception:
        macro_text = "Macro data unavailable."

    # Step 2: Build prompts
    financials_str = _format_financials(extracted_financials)
    research_str = _format_research(research_findings)

    prompt = _SWOT_PROMPT.format(
        company_name=company_name,
        sector=sector,
        loan_amount_cr=loan_amount_cr,
        loan_type=loan_type,
        tenure_months=tenure_months,
        financials=financials_str,
        research=research_str,
        macro=macro_text[:2000],
    )

    # Step 3: Generate
    try:
        result = await llm_call(prompt=prompt, task="cam_narrative")
        cleaned = re.sub(r"```json|```", "", result).strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"SWOT generation failed: {e}")
        return {
            "strengths": [], "weaknesses": [], "opportunities": [], "threats": [],
            "sector_outlook": "Analysis unavailable — run analysis pipeline first.",
            "macro_signals": {},
            "investment_thesis": "Insufficient data",
            "recommendation": "Manual review required.",
        }


def _format_financials(data: dict) -> str:
    KEY_FIELDS = [
        ("revenue_crore", "Revenue (₹Cr)"),
        ("ebitda_margin_pct", "EBITDA Margin %"),
        ("pat_crore", "PAT (₹Cr)"),
        ("de_ratio", "D/E Ratio"),
        ("current_ratio", "Current Ratio"),
        ("dscr", "DSCR"),
        ("interest_coverage", "Interest Coverage"),
        ("promoter_holding_pct", "Promoter Holding %"),
        ("total_pledged_pct", "Pledged %"),
        ("gnpa_pct", "GNPA %"),
        ("collection_efficiency_pct", "Collection Efficiency %"),
        ("aum_cr", "AUM (₹Cr)"),
        ("total_outstanding_cr", "Total Debt Outstanding (₹Cr)"),
        ("structural_liquidity_gap_cr", "ALM Liquidity Gap (₹Cr)"),
    ]
    lines = []
    for key, label in KEY_FIELDS:
        val = data.get(key)
        if val is not None:
            lines.append(f"  {label}: {val}")
    return "\n".join(lines) or "  No extracted financial data available."


def _format_research(findings: list) -> str:
    if not findings:
        return "  No adverse research findings."
    out = []
    # findings are dicts or ORM objects — handle both
    for f in findings[:12]:
        if hasattr(f, "severity"):
            severity = f.severity
            summary = f.summary
            source = getattr(f, "source_name", "Web")
        else:
            severity = f.get("severity", "LOW")
            summary = f.get("summary", "")
            source = f.get("source_name", "Web")
        out.append(f"  [{severity}] {summary} (Source: {source})")
    return "\n".join(out)
```

---

## PHASE 7 — SWOT + INVESTMENT REPORT API

### 7A — SWOT endpoint

Find or create `backend/api/routes/analysis.py` and add:

```python
@router.get("/companies/{company_id}/swot")
async def get_swot(company_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from backend.models.db_models import SwotAnalysis
    result = await db.execute(
        select(SwotAnalysis)
        .where(SwotAnalysis.company_id == uuid.UUID(company_id))
        .order_by(SwotAnalysis.created_at.desc()).limit(1)
    )
    swot = result.scalar_one_or_none()
    if not swot:
        raise HTTPException(404, "No SWOT analysis found. Run analysis pipeline first.")
    return {
        "data": {
            "strengths": swot.strengths or [],
            "weaknesses": swot.weaknesses or [],
            "opportunities": swot.opportunities or [],
            "threats": swot.threats or [],
            "sector_outlook": swot.sector_outlook,
            "macro_signals": swot.macro_signals or {},
            "investment_thesis": swot.investment_thesis,
            "recommendation": swot.recommendation,
            "generated_at": swot.created_at.isoformat() if swot.created_at else None,
        },
        "success": True,
    }
```

### 7B — Investment Report endpoint

Add to the same routes file:

```python
@router.get("/companies/{company_id}/investment-report")
async def download_investment_report(company_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and stream the investment report DOCX."""
    from backend.core.report.investment_report_generator import generate_investment_report
    from fastapi.responses import FileResponse
    import os

    try:
        path = await generate_investment_report(company_id=company_id, db=db)
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {e}")

    if not os.path.exists(path):
        raise HTTPException(500, "Report file not created")

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"IntelliCredit_InvestmentReport_{company_id[:8]}.docx",
    )
```

### 7C — Investment Report Generator

Create `backend/core/report/investment_report_generator.py`:

```python
"""
Investment Report Generator.
Generates a structured downloadable DOCX covering all 4 hackathon stages:
entity profile, document analysis, secondary research, SWOT, reasoning, recommendation.
"""
from __future__ import annotations
import os, uuid, logging
from datetime import datetime
from docx import Document as DocxDocument
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

_BLUE  = RGBColor(0x1E, 0x6F, 0xD9)
_INK   = RGBColor(0x0F, 0x1F, 0x3D)
_GREEN = RGBColor(0x16, 0xA3, 0x4A)
_RED   = RGBColor(0xDC, 0x26, 0x26)
_GRAY  = RGBColor(0x6B, 0x72, 0x80)

async def generate_investment_report(company_id: str, db: AsyncSession) -> str:
    from backend.models.db_models import (
        Company, LoanApplication, RiskScore, SwotAnalysis,
        ResearchFindingRecord, DocumentClassification, Document,
    )

    # ── Fetch all data ───────────────────────────────────────────────────────
    company = await db.get(Company, uuid.UUID(company_id))
    if not company:
        raise ValueError(f"Company {company_id} not found")

    async def latest(model, filter_col):
        r = await db.execute(
            select(model).where(filter_col == uuid.UUID(company_id))
            .order_by(model.created_at.desc()).limit(1)
        )
        return r.scalar_one_or_none()

    loan  = await latest(LoanApplication, LoanApplication.company_id)
    score = await latest(RiskScore, RiskScore.company_id)
    swot  = await latest(SwotAnalysis, SwotAnalysis.company_id)

    findings_r = await db.execute(
        select(ResearchFindingRecord)
        .where(ResearchFindingRecord.company_id == uuid.UUID(company_id))
    )
    findings = findings_r.scalars().all()

    clf_r = await db.execute(
        select(DocumentClassification)
        .where(DocumentClassification.company_id == uuid.UUID(company_id))
        .where(DocumentClassification.human_approved != False)  # noqa: E712
    )
    classifications = clf_r.scalars().all()

    # ── Build document ───────────────────────────────────────────────────────
    doc = DocxDocument()
    _set_base_style(doc)

    # Cover
    _heading(doc, "INVESTMENT CREDIT REPORT", level=0)
    _info_table(doc, [
        ("Entity", company.name),
        ("CIN", getattr(company, "cin", None) or "N/A"),
        ("Sector", getattr(company, "sector", None) or "N/A"),
        ("PAN", getattr(company, "pan_number", None) or "N/A"),
        ("Report Date", datetime.now().strftime("%B %d, %Y")),
        ("Prepared by", "Intelli-Credit AI Engine v2.0"),
    ])
    doc.add_page_break()

    # ── §1 Executive Summary ─────────────────────────────────────────────────
    _heading(doc, "§1 Executive Summary", 1)
    if score:
        decision_color = _GREEN if score.decision == "APPROVE" else (_RED if score.decision == "REJECT" else None)
        p = doc.add_paragraph()
        run = p.add_run(f"Credit Decision: {score.decision}")
        run.bold = True
        if decision_color:
            run.font.color.rgb = decision_color
        doc.add_paragraph(f"Risk Score: {score.final_risk_score:.1f} / 100 — {score.risk_category}")
        if score.recommended_limit_crore:
            doc.add_paragraph(f"Recommended Limit: ₹{score.recommended_limit_crore:.1f} Cr")

    if swot and swot.investment_thesis:
        doc.add_paragraph(f"Investment Thesis: {swot.investment_thesis}")
    doc.add_page_break()

    # ── §2 Entity & Loan Profile ──────────────────────────────────────────────
    _heading(doc, "§2 Entity & Loan Profile", 1)
    entity_rows = [
        ("Company Name", company.name),
        ("CIN", getattr(company, "cin", None) or "N/A"),
        ("Sector", getattr(company, "sector", None) or "N/A"),
        ("Annual Turnover", f"₹{getattr(company, 'annual_turnover_cr', None) or 'N/A'} Cr"),
        ("Year of Incorporation", getattr(company, "year_of_incorporation", None) or "N/A"),
    ]
    _info_table(doc, entity_rows)

    if loan:
        _heading(doc, "Loan Details", 2)
        _info_table(doc, [
            ("Loan Type", loan.loan_type),
            ("Amount Requested", f"₹{loan.loan_amount_cr:.1f} Cr"),
            ("Tenure", f"{loan.tenure_months} months"),
            ("Proposed Rate", f"{loan.proposed_rate_pct or 'TBD'}% p.a."),
            ("Repayment Mode", loan.repayment_mode or "N/A"),
            ("Purpose", loan.purpose or "N/A"),
            ("Collateral", f"{loan.collateral_type or 'None'} — ₹{loan.collateral_value_cr or 0:.1f} Cr"),
        ])
    doc.add_page_break()

    # ── §3 Documents Analysed ─────────────────────────────────────────────────
    _heading(doc, "§3 Documents Analysed & Classification", 1)
    for clf in classifications:
        etype = clf.human_type_override or clf.auto_type
        status = "✓ APPROVED" if clf.human_approved else "PENDING"
        if clf.human_type_override:
            status += f" (overridden from {clf.auto_type})"
        doc.add_paragraph(
            f"  • {etype} — {status} | Auto-confidence: {clf.auto_confidence:.0%} | {clf.auto_reasoning or ''}",
            style="List Bullet",
        )
    doc.add_page_break()

    # ── §4 Financial Analysis ──────────────────────────────────────────────────
    _heading(doc, "§4 Financial Analysis", 1)
    if score and score.rule_based_score is not None:
        _heading(doc, "Score Breakdown", 2)
        _info_table(doc, [
            ("Rule-based Score", f"{score.rule_based_score:.1f} / 100"),
            ("ML Stress Probability", f"{score.ml_stress_probability:.1%}" if score.ml_stress_probability else "N/A"),
            ("Final Weighted Score", f"{score.final_risk_score:.1f} / 100"),
        ])

    if score and score.shap_values:
        _heading(doc, "Top Risk Drivers (SHAP)", 2)
        shap_sorted = sorted(score.shap_values.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
        for feat, val in shap_sorted:
            direction = "▲ RISK" if val > 0 else "▼ RISK"
            doc.add_paragraph(f"  • {feat}: {val:+.3f} ({direction})", style="List Bullet")
    doc.add_page_break()

    # ── §5 Secondary Research ──────────────────────────────────────────────────
    _heading(doc, "§5 Secondary Research Findings", 1)
    if findings:
        for f in sorted(findings, key=lambda x: x.severity if hasattr(x, "severity") else "LOW", reverse=True):
            severity = getattr(f, "severity", "LOW")
            summary = getattr(f, "summary", str(f))
            source = getattr(f, "source_name", "Web Research")
            p = doc.add_paragraph(style="List Bullet")
            run = p.add_run(f"[{severity}] ")
            run.bold = True
            if severity == "HIGH":
                run.font.color.rgb = _RED
            elif severity == "MEDIUM":
                run.font.color.rgb = RGBColor(0xD9, 0x77, 0x06)
            p.add_run(f"{summary} — Source: {source}")
    else:
        doc.add_paragraph("No adverse research findings identified.")

    if swot and swot.sector_outlook:
        _heading(doc, "Sector & Macro Context", 2)
        doc.add_paragraph(swot.sector_outlook)
        if swot.macro_signals:
            ms = swot.macro_signals
            _info_table(doc, [
                ("RBI Repo Rate", f"{ms.get('rbi_repo_rate_pct', 'N/A')}%"),
                ("India GDP Growth", f"{ms.get('india_gdp_growth_pct', 'N/A')}%"),
                ("Sector Credit Growth", f"{ms.get('sector_credit_growth_pct', 'N/A')}%"),
                ("CPI Inflation", f"{ms.get('inflation_cpi_pct', 'N/A')}%"),
            ])
    doc.add_page_break()

    # ── §6 SWOT Analysis ───────────────────────────────────────────────────────
    _heading(doc, "§6 SWOT Analysis", 1)
    if swot:
        for quadrant, label in [
            ("strengths", "STRENGTHS"),
            ("weaknesses", "WEAKNESSES"),
            ("opportunities", "OPPORTUNITIES"),
            ("threats", "THREATS"),
        ]:
            _heading(doc, label, 2)
            items = getattr(swot, quadrant) or []
            for item in items:
                if isinstance(item, dict):
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(item.get("point", "")).bold = True
                    p.add_run(f" — {item.get('evidence', '')} [{item.get('source', '')}]")
                else:
                    doc.add_paragraph(str(item), style="List Bullet")
    doc.add_page_break()

    # ── §7 Reasoning Engine ────────────────────────────────────────────────────
    _heading(doc, "§7 Reasoning Engine — Why This Decision", 1)
    if score:
        violations = score.rule_violations or []
        if violations:
            _heading(doc, "Hard Stop Rules Triggered", 2)
            for v in violations:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(f"⚠ {v.get('id', '')}: ")
                run.bold = True
                run.font.color.rgb = _RED
                p.add_run(v.get("description", ""))

        strengths = score.risk_strengths or []
        if strengths:
            _heading(doc, "Credit Strengths", 2)
            for st in strengths:
                doc.add_paragraph(f"✓ {st.get('description', '')}", style="List Bullet")

        if score.decision_rationale:
            _heading(doc, "AI Narrative", 2)
            doc.add_paragraph(score.decision_rationale)
    doc.add_page_break()

    # ── §8 Recommendation ─────────────────────────────────────────────────────
    _heading(doc, "§8 Recommendation", 1)
    if score:
        p = doc.add_paragraph()
        run = p.add_run(f"DECISION: {score.decision}")
        run.bold = True
        run.font.size = Pt(14)
        if loan:
            doc.add_paragraph(f"Requested: ₹{loan.loan_amount_cr:.1f} Cr | Recommended: ₹{score.recommended_limit_crore or loan.loan_amount_cr:.1f} Cr")
        if getattr(score, "interest_premium_bps", None):
            doc.add_paragraph(f"Pricing Guidance: MCLR + {score.interest_premium_bps}bps")
    if swot and swot.recommendation:
        doc.add_paragraph(swot.recommendation)

    # ── §9 Declaration ────────────────────────────────────────────────────────
    _heading(doc, "§9 Declaration", 1)
    doc.add_paragraph(
        "This report has been generated by the Intelli-Credit AI Engine. "
        "All analysis is subject to review and approval by a qualified credit officer. "
        "The AI engine provides structured analysis and quantitative inputs; "
        "the final credit decision rests with the authorised credit authority per RBI guidelines."
    )
    doc.add_paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST")
    doc.add_paragraph("Intelli-Credit | IIT Hyderabad × Vivriti Capital Hackathon 2026")

    # ── Save ──────────────────────────────────────────────────────────────────
    output_dir = os.environ.get("CAM_OUTPUT_DIR", "outputs/reports")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"investment_report_{company_id}.docx")
    doc.save(path)
    logger.info(f"Investment report saved: {path}")
    return path


# ── docx helpers ──────────────────────────────────────────────────────────────
def _heading(doc, text: str, level: int):
    if level == 0:
        p = doc.add_heading(text, 0)
    else:
        p = doc.add_heading(text, level)
    for run in p.runs:
        run.font.color.rgb = _INK


def _info_table(doc, rows: list[tuple[str, str]]):
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(rows):
        row = table.rows[i]
        cell_label = row.cells[0]
        cell_value = row.cells[1]
        cell_label.text = label
        cell_value.text = str(value)
        for run in cell_label.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = _GRAY
    doc.add_paragraph("")  # spacer


def _set_base_style(doc):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
```

---

## PHASE 8 — PIPELINE: SWOT + NEW PARSERS WIRED IN

**Read `backend/core/pipeline_service.py` fully before editing.**

Find the main `run_full_analysis()` method (or equivalent). You need to add two integration points:

### 8A — Call new parsers per doc type

After the existing ingestion step, find where `extracted_data` is built. Add a dispatch loop:

```python
# After existing pdf_parser call — add routing for new doc types
from backend.core.ingestion.document_classifier import DOC_TYPES
from backend.core.ingestion.alm_parser import parse_alm_statement
from backend.core.ingestion.shareholding_parser import parse_shareholding_pattern
from backend.core.ingestion.borrowing_profile_parser import parse_borrowing_profile
from backend.core.ingestion.portfolio_parser import parse_portfolio_performance

_PARSER_MAP = {
    "ALM": parse_alm_statement,
    "SHAREHOLDING": parse_shareholding_pattern,
    "BORROWING_PROFILE": parse_borrowing_profile,
    "PORTFOLIO": parse_portfolio_performance,
    "ANNUAL_REPORT": None,  # handled by existing pdf_parser
}

# Fetch approved classifications for this company
from backend.models.db_models import DocumentClassification, Document
from sqlalchemy import select

clf_result = await db.execute(
    select(DocumentClassification)
    .where(DocumentClassification.company_id == company_uuid)
    .where(DocumentClassification.human_approved != False)
)
classifications = clf_result.scalars().all()

for clf in classifications:
    effective_type = clf.human_type_override or clf.auto_type
    parser_fn = _PARSER_MAP.get(effective_type)
    if parser_fn is None:
        continue  # annual report handled by existing flow

    doc_record = await db.get(Document, clf.document_id)
    if not doc_record:
        continue

    try:
        parsed = await parser_fn(doc_record.file_path)
        # Merge into main extracted_data dict (new fields, don't overwrite existing)
        for k, v in parsed.items():
            if v is not None and k not in ("red_flags", "extraction_confidence", "error"):
                extracted_data.setdefault(k, v)

        # Propagate red flags to research findings
        for flag in parsed.get("red_flags", []):
            pipeline_findings.append({
                "severity": "MEDIUM",
                "summary": flag,
                "source_name": f"{effective_type} Parser",
                "finding_type": "DOCUMENT_FLAG",
            })
    except Exception as e:
        logger.error(f"Parser failed for {effective_type} ({doc_record.file_path}): {e}")
```

### 8B — Generate SWOT after research step

Find where research findings are saved to the DB. After that point, add:

```python
# Generate SWOT analysis
try:
    from backend.core.research.swot_engine import generate_swot
    from backend.models.db_models import SwotAnalysis, LoanApplication
    from sqlalchemy import select

    loan_r = await db.execute(
        select(LoanApplication).where(LoanApplication.company_id == company_uuid)
        .order_by(LoanApplication.created_at.desc()).limit(1)
    )
    loan_obj = loan_r.scalar_one_or_none()

    swot_data = await generate_swot(
        company_name=company.name,
        sector=getattr(company, "sector", "General"),
        loan_amount_cr=loan_obj.loan_amount_cr if loan_obj else 0.0,
        loan_type=loan_obj.loan_type if loan_obj else "TERM_LOAN",
        tenure_months=loan_obj.tenure_months if loan_obj else 60,
        extracted_financials=extracted_data,
        research_findings=all_findings,  # adjust to actual variable name
    )

    swot_record = SwotAnalysis(
        company_id=company_uuid,
        strengths=swot_data.get("strengths"),
        weaknesses=swot_data.get("weaknesses"),
        opportunities=swot_data.get("opportunities"),
        threats=swot_data.get("threats"),
        sector_outlook=swot_data.get("sector_outlook"),
        macro_signals=swot_data.get("macro_signals"),
        investment_thesis=swot_data.get("investment_thesis"),
        recommendation=swot_data.get("recommendation"),
    )
    db.add(swot_record)
    await db.commit()
    logger.info(f"SWOT generated for {company.name}")
except Exception as e:
    logger.error(f"SWOT generation failed: {e}")  # non-fatal
```

### 8C — Feature engineering update

Read `backend/core/ml/` files. Find the feature engineering function that builds the feature vector from `extracted_data`. Add these new features at the end:

```python
# New features from new document parsers
features["alm_liquidity_gap_cr"]     = safe_float(extracted_data.get("structural_liquidity_gap_cr"))
features["alm_short_term_borrow_pct"]= safe_float(extracted_data.get("concentration_risk", {}).get("short_term_borrowing_pct") if isinstance(extracted_data.get("concentration_risk"), dict) else 0)
features["promoter_holding_pct"]     = safe_float(extracted_data.get("promoter_holding_pct"))
features["pledged_pct"]              = safe_float(extracted_data.get("total_pledged_pct"))
features["existing_debt_cr"]         = safe_float(extracted_data.get("total_outstanding_cr"))
features["avg_cost_of_debt_pct"]     = safe_float(extracted_data.get("avg_cost_of_debt_pct"))
features["gnpa_pct"]                 = safe_float(extracted_data.get("asset_quality", {}).get("gnpa_pct") if isinstance(extracted_data.get("asset_quality"), dict) else 0)
features["collection_efficiency"]    = safe_float(extracted_data.get("collection_efficiency_pct"), default=100.0)
```

Where `safe_float` should be an existing helper or define as:
```python
def safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default
```

---

## PHASE 9 — FRONTEND: MULTI-STEP ONBOARDING

**Read `frontend/app/app/start/page.tsx` and `frontend/lib/api.ts` before editing.**

Replace the content of `frontend/app/app/start/page.tsx` with a 3-step form:

### Step structure:
- **Step 1 — Entity Details:** Company Name, CIN, PAN, GSTIN, Sector (dropdown), Annual Turnover (₹Cr), Year of Incorporation, Registered Address
- **Step 2 — Loan Details:** Loan Type (dropdown), Loan Amount (₹Cr), Tenure (months), Proposed Rate %, Repayment Mode (dropdown), Purpose, Collateral Type + Value
- **Step 3 — Review & Submit:** Summary of all inputs, submit button

### Implementation requirements:

```typescript
// ── Types ─────────────────────────────────────────────────────────────────
interface EntityForm {
  name: string;
  cin: string;
  pan_number: string;
  gstin?: string;
  sector: string;
  annual_turnover_cr: number | "";
  year_of_incorporation: number | "";
  registered_address?: string;
}

interface LoanForm {
  loan_type: "TERM_LOAN" | "WORKING_CAPITAL" | "CC" | "OD" | "NCD";
  loan_amount_cr: number | "";
  tenure_months: number | "";
  proposed_rate_pct?: number | "";
  repayment_mode: "EMI" | "BULLET" | "QUARTERLY";
  purpose: string;
  collateral_type?: "PROPERTY" | "STOCKS" | "FD" | "NONE";
  collateral_value_cr?: number | "";
}

// ── Validation helpers ─────────────────────────────────────────────────────
const validateCIN = (v: string) =>
  /^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/.test(v);

const validatePAN = (v: string) =>
  /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(v);

// ── On submit (Step 3) ─────────────────────────────────────────────────────
// 1. POST /api/v1/companies  with entityForm data → get company_id
// 2. POST /api/v1/companies/{company_id}/loan  with loanForm data
// 3. useAnalysisStore().setCompanyId(company_id)   — use existing Zustand store
// 4. router.push("/app/upload")
```

### Sector options (dropdown):
```
NBFC | Manufacturing | Real Estate | Infrastructure |
Pharma & Healthcare | IT/ITeS | Retail & FMCG | Logistics |
Construction | Energy & Power | Other
```

### UI design requirements:
- Use a step indicator at the top (1 → 2 → 3) matching existing Tailwind style
- Each field gets an inline validation error on blur
- CIN field: show example format `L17110MH1973PLC019786` as placeholder
- PAN field: show example `AAACR5055K` as placeholder
- Loan Amount + Turnover fields show `₹` prefix
- Progress bar at the bottom (33% / 66% / 100%)

---

## PHASE 10 — FRONTEND: CLASSIFICATION HITL PAGE

Create `frontend/app/app/classify/page.tsx`:

This is the document review screen that appears between upload and analysis.

### Layout:

```
┌─────────────────────────────────────────────────────────┐
│  Step 3 of 5: Review Document Classifications           │
│  "Our AI has classified your documents. Review and      │
│   approve before running analysis."                     │
├─────────────────────────────────────────────────────────┤
│  [Summary pills: 5 docs · 2 approved · 3 pending]       │
├─────────────────────────────────────────────────────────┤
│  Document cards (one per row):                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 📄 ALM_FY25.pdf     [ALM] 94% confident           │ │
│  │ "Filename matched ALM keyword pattern"              │ │
│  │ [✅ Approve] [✏️ Change Type] [❌ Reject]          │ │
│  │ [⚙ Configure Schema ▼]                            │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  [Continue to Analysis →] (disabled until all reviewed) │
└─────────────────────────────────────────────────────────┘
```

### Key interactions:

1. **Approve** → `PATCH /api/v1/companies/{id}/classifications/{clf_id}` `{action:"approve"}`
2. **Change Type** → opens dropdown to select correct type → `{action:"override", new_type:...}`
3. **Reject** → `{action:"reject"}`
4. **Configure Schema** → expandable panel with a field builder:
   - User adds rows: `field_name | type (string/float/int/date) | description`
   - `[Save Schema]` → `{action:"set_schema", schema:{fields:[...]}}`
   - `[Re-extract with Schema]` → `POST .../extract`
   - Shows extracted JSON in a readonly code block
5. **Continue** button → only enabled when `summary.pending === 0` → `router.push("/app/pipeline")`

### API calls (add to `frontend/lib/api.ts`):
```typescript
// Add to api.ts
getClassifications: (companyId: string) =>
  fetchApi(`/api/v1/companies/${companyId}/classifications`),

updateClassification: (companyId: string, classificationId: string, payload: object) =>
  fetchApi(`/api/v1/companies/${companyId}/classifications/${classificationId}`, {
    method: "PATCH", body: JSON.stringify(payload),
  }),

triggerExtraction: (companyId: string, classificationId: string) =>
  fetchApi(`/api/v1/companies/${companyId}/classifications/${classificationId}/extract`, {
    method: "POST",
  }),
```

### Navigation: add `/app/classify` between `/app/upload` and the existing pipeline trigger

---

## PHASE 11 — FRONTEND: SWOT + INVESTMENT REPORT

### 11A — Update `frontend/app/app/results/page.tsx`

Find where the results tabs are defined. Add a new "SWOT & Report" tab:

```typescript
// Add tab definition
{ id: "swot", label: "SWOT & Report", icon: "📊" }
```

### 11B — Create `frontend/components/SwotMatrix.tsx`:

```tsx
interface SwotPoint { point: string; evidence: string; source: string; }
interface SwotData {
  strengths: SwotPoint[];
  weaknesses: SwotPoint[];
  opportunities: SwotPoint[];
  threats: SwotPoint[];
  sector_outlook: string;
  macro_signals: Record<string, number>;
  investment_thesis: string;
  recommendation: string;
}

// Layout: 2×2 grid of quadrants
// Strengths (green bg), Weaknesses (red bg), Opportunities (blue bg), Threats (amber bg)
// Each quadrant: title + bullet list
// Each bullet: bold point, then grey "— evidence [source]"
// Below grid: sector_outlook text + macro_signals pills + recommendation box
// "📥 Download Investment Report" button → GET /api/v1/companies/{id}/investment-report
```

Styling requirements:
- Use existing TailwindCSS classes consistent with rest of app
- Strengths: `bg-green-50 border-green-200`
- Weaknesses: `bg-red-50 border-red-200`
- Opportunities: `bg-blue-50 border-blue-200`
- Threats: `bg-amber-50 border-amber-200`
- Each quadrant header bold + icon (💪 / ⚠️ / 🎯 / ⚡)
- "Download Report" button: `bg-blue-600 text-white` with download icon

### 11C — Add API calls to `frontend/lib/api.ts`:
```typescript
getSwot: (companyId: string) =>
  fetchApi(`/api/v1/companies/${companyId}/swot`),

downloadInvestmentReport: (companyId: string) =>
  fetch(`${API_BASE}/api/v1/companies/${companyId}/investment-report`)
    .then(res => res.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `IntelliCredit_Report_${companyId.slice(0, 8)}.docx`;
      a.click();
    }),
```

---

## PHASE 12 — VERIFICATION & FINAL SMOKE TEST

### 12.1 — Unit test new parsers

```bash
python3 - << 'EOF'
import asyncio

async def test_classifier():
    from backend.core.ingestion.document_classifier import classify_document
    # Test filename heuristics (no file needed)
    t, c, r = await classify_document("/tmp/fake_alm.pdf", "ALM_Statement_FY25.pdf")
    assert t == "ALM", f"Expected ALM, got {t}"
    assert c >= 0.9
    print(f"✅ ALM filename rule: {t} ({c:.0%}) — {r}")

    t, c, r = await classify_document("/tmp/fake.xlsx", "Shareholding_Pattern_Q3FY26.xlsx")
    assert t == "SHAREHOLDING"
    print(f"✅ Shareholding filename rule: {t} ({c:.0%})")

    t, c, r = await classify_document("/tmp/fake.pdf", "Annual_Report_FY2025.pdf")
    assert t == "ANNUAL_REPORT"
    print(f"✅ Annual report filename rule: {t}")

asyncio.run(test_classifier())
EOF
```

### 12.2 — DB schema verification

```bash
python3 - << 'EOF'
import asyncio, os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/intellicredit")

async def check_tables():
    from backend.database import engine, Base
    import backend.models.db_models as m  # imports all models
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda c: c.dialect.get_table_names(c, schema="public"))
    required = {"loan_applications", "document_classifications", "swot_analyses"}
    missing = required - set(tables)
    if missing:
        print(f"❌ Missing tables: {missing}")
    else:
        print(f"✅ All required tables exist: {required}")

asyncio.run(check_tables())
EOF
```

### 12.3 — Full API smoke test

```bash
set -e
BASE="http://localhost:8000"

echo "=== 1. Create company with new fields ==="
COMPANY_ID=$(curl -s -X POST "$BASE/api/v1/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TestNBFC Ltd",
    "cin": "U65929TN2005PTC056988",
    "sector": "NBFC",
    "pan_number": "AADCT1234C",
    "annual_turnover_cr": 500
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])")
echo "Company ID: $COMPANY_ID"

echo "=== 2. Create loan application ==="
curl -s -X POST "$BASE/api/v1/companies/$COMPANY_ID/loan" \
  -H "Content-Type: application/json" \
  -d '{
    "loan_type": "TERM_LOAN",
    "loan_amount_cr": 50,
    "tenure_months": 60,
    "proposed_rate_pct": 10.5,
    "purpose": "Business expansion"
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ Loan:', d['data']['loan_id'])"

echo "=== 3. Check classifications endpoint ==="
curl -s "$BASE/api/v1/companies/$COMPANY_ID/classifications" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ Classifications:', d['data']['summary'])"

echo "=== 4. Health check ==="
curl -s "$BASE/api/v1/health" | python3 -c "import sys,json; print('✅ Health:', json.load(sys.stdin))"

echo ""
echo "✅ All smoke tests passed"
```

### 12.4 — Evaluate against hackathon criteria

After running the full pipeline on provided sample documents, verify:

```
OPERATIONAL EXCELLENCE
  [ ] Multi-step onboarding saves correctly (company + loan in one flow)
  [ ] All 5 doc types upload without error
  [ ] Classification HITL page loads with correct auto-types
  [ ] Approval/override/reject all persist to DB
  [ ] Schema builder saves and re-extract returns JSON
  [ ] Pipeline runs without crash on all 5 doc types
  [ ] Investment report downloads as DOCX

EXTRACTION ACCURACY
  [ ] ALM: maturity buckets extracted correctly
  [ ] Shareholding: promoter % and pledge % correct
  [ ] Borrowing Profile: lender-wise outstanding extracted
  [ ] Portfolio: GNPA % and collection efficiency extracted
  [ ] Annual Report: EBITDA margin in Crore (not Lakh) ← existing bug B2

ANALYTICAL DEPTH
  [ ] SWOT has specific evidence-backed points, not generic
  [ ] Each SWOT point cites a number from extracted data
  [ ] Sector outlook mentions macro context (RBI rate, GDP)
  [ ] Research finds news + legal + MCA data
  [ ] Reasoning engine shows which rules fired + SHAP values
  [ ] Triangulation note appears when GST ≠ Annual Report revenue

USER EXPERIENCE
  [ ] CIN + PAN validation shows inline errors
  [ ] Step progress indicator visible throughout onboarding
  [ ] Confidence bars visible on classification page
  [ ] SWOT renders as 4-quadrant visual
  [ ] Download Investment Report is one-click from results page
  [ ] Entire flow from onboarding to report takes < 5 minutes
```

---

## PRIORITY ORDER IF TIME IS SHORT

If you have less than a full day, implement strictly in this order — each item is
independently demoable and adds judge points:

1. **DB + Loan API** (Phase 1 + 2) — 45 min → Stage 1 fully working
2. **Multi-step onboarding UI** (Phase 9) — 60 min → Stage 1 demoable
3. **Document classifier** (Phase 3A) — 30 min → Classification exists
4. **Classification API + upload hook** (Phase 4 + 5) — 45 min → Stage 3 partially working
5. **Classification HITL UI** (Phase 10) — 60 min → Stage 3 fully demoable
6. **4 new parsers** (Phase 3B–3E) — 60 min → Stage 2 fully working
7. **SWOT engine** (Phase 6) — 45 min → Stage 4 partially working
8. **SWOT UI** (Phase 11A–11B) — 30 min → Stage 4 partially demoable
9. **Investment report** (Phase 7C + 11C) — 45 min → Stage 4 fully demoable
10. **Pipeline integration** (Phase 8) — 60 min → everything wired end-to-end
11. **Verification** (Phase 12) — 30 min → demo-ready

**Do not touch existing scoring logic, CAM generator, or research agent unless explicitly required above.**
All changes must preserve the `/api/v1/*` response envelope.

---

*Intelli-Credit · IIT Hyderabad × Vivriti Capital Hackathon 2026*
*Prompt version: v3 (grounded against confirmed project structure)*
*Generated: March 11, 2026*
