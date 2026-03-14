"""Loan application CRUD for the entity onboarding stage."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import RequestContext, get_request_context
from backend.database import get_db
from backend.models.db_models import Company, LoanApplication
from backend.schemas.common import build_response

router = APIRouter(prefix="/api/v1/companies/{company_id}/loan", tags=["loan"])


class LoanCreateInput(BaseModel):
    loan_type: str
    loan_amount_cr: float
    tenure_months: int
    proposed_rate_pct: Optional[float] = None
    repayment_mode: Optional[str] = None
    purpose: Optional[str] = None
    collateral_type: Optional[str] = None
    collateral_value_cr: Optional[float] = None


class LoanUpdateInput(BaseModel):
    loan_type: Optional[str] = None
    loan_amount_cr: Optional[float] = None
    tenure_months: Optional[int] = None
    proposed_rate_pct: Optional[float] = None
    repayment_mode: Optional[str] = None
    purpose: Optional[str] = None
    collateral_type: Optional[str] = None
    collateral_value_cr: Optional[float] = None


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
        "created_at": loan.created_at.isoformat() if loan.created_at else None,  # type: ignore[reportGeneralTypeIssues]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_loan(
    company_id: str,
    payload: LoanCreateInput,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    company = await db.get(Company, uuid.UUID(company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    loan = LoanApplication(
        company_id=uuid.UUID(company_id),
        loan_type=payload.loan_type,
        loan_amount_cr=payload.loan_amount_cr,
        tenure_months=payload.tenure_months,
        proposed_rate_pct=payload.proposed_rate_pct,
        repayment_mode=payload.repayment_mode,
        purpose=payload.purpose,
        collateral_type=payload.collateral_type,
        collateral_value_cr=payload.collateral_value_cr,
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)
    return build_response(
        _loan_to_dict(loan),
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.get("")
async def get_loan(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
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
    return build_response(
        _loan_to_dict(loan),
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )


@router.patch("")
async def update_loan(
    company_id: str,
    payload: LoanUpdateInput,
    db: AsyncSession = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
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

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(loan, field, value)

    await db.commit()
    await db.refresh(loan)
    return build_response(
        _loan_to_dict(loan),
        request_id=ctx.request_id,
        started_at=ctx.started_at,
    )
