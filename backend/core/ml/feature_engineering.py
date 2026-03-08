"""
Feature engineering for Intelli-Credit hybrid scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

from backend.core.india_context import sector_risk_multiplier

logger = logging.getLogger(__name__)


CREDIT_FEATURES = {
    "revenue_cagr_3yr": float,
    "ebitda_margin": float,
    "debt_equity_ratio": float,
    "current_ratio": float,
    "interest_coverage_ratio": float,
    "dscr": float,
    "gst_banking_ratio": float,
    "itr_gst_consistency_score": float,
    "average_bank_balance_to_limit_ratio": float,
    "has_auditor_qualification": bool,
    "has_going_concern_doubt": bool,
    "has_litigation": bool,
    "has_mca_struck_off_associates": bool,
    "has_circular_trading_signals": bool,
    "has_revenue_inflation_signals": bool,
    "has_promoter_fraud_news": bool,
    "has_sector_headwinds": bool,
    "has_nclt_proceedings": bool,
    "gstr3b_vs_2a_itc_gap": float,
    "gst_return_filing_consistency": float,
    "mca_filing_compliance_score": float,
    "cibil_commercial_score": float,
    "management_integrity_score": float,
    "factory_capacity_utilization": float,
    "due_diligence_risk_adjustment": float,
    "collateral_coverage_ratio": float,
    "collateral_type_score": float,
}


def _safe_num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return float(value)
    except (TypeError, ValueError):
        return default


def build_feature_vector(payload: Dict[str, Any]) -> Dict[str, float]:
    """
    Build complete model feature vector from normalized pipeline payload.
    """
    financials = payload.get("financials", {})
    bank = payload.get("bank_metrics", {})
    gst = payload.get("gst", {})
    research = payload.get("research", {})
    due = payload.get("due_diligence", {})
    collateral = payload.get("collateral", {})
    gst_xlsx = payload.get("gst_xlsx", {})

    revenue_series = financials.get("revenue_figures", [])
    rev_values = [
        _safe_num(v.get("amount") if isinstance(v, dict) else v, 0.0)
        for v in revenue_series[:3]
    ]
    while len(rev_values) < 3:
        rev_values.append(rev_values[-1] if rev_values else 0.0)

    r0, r1, r2 = rev_values[0], max(rev_values[1], 1.0), max(rev_values[2], 1.0)
    revenue_cagr_3yr = ((max(r0, 1.0) / max(r2, 1.0)) ** (1 / 2) - 1) if r2 > 0 else 0.0

    sector = str(payload.get("sector", "other")).lower()
    sector_multiplier = sector_risk_multiplier(sector)

    # DSCR: prefer XLSX-extracted value, then cross-validation, then fallback
    dscr_value = _safe_num(financials.get("dscr"), 0.0)
    cross_dscr = _safe_num(payload.get("cross_validation", {}).get("debt_service_coverage_ratio"), 0.0)
    if dscr_value > 0:
        dscr = dscr_value
    elif cross_dscr > 0:
        dscr = cross_dscr
    else:
        dscr = 1.3  # default fallback
        logger.warning("[Features] DSCR is 0.0 from all sources, using default 1.3")

    # GST ITC gap: prefer XLSX-parsed value, then mismatch report
    gst_itc_gap = _safe_num(gst_xlsx.get("itc_mismatch_pct"), 0.0)
    if gst_itc_gap == 0.0:
        gst_itc_gap = _safe_num(gst.get("itc_inflation_percentage"), 0.0)

    # Circular trading: check both sources
    has_circular = bool(gst.get("suspected_circular_trading", False)) or bool(gst_xlsx.get("has_circular_trading_signals", False))

    vector = {
        "revenue_cagr_3yr": revenue_cagr_3yr,
        "ebitda_margin": _safe_num(financials.get("ebitda_margin"), 10.0),
        "debt_equity_ratio": _safe_num(financials.get("debt_equity_ratio"), 1.5),
        "current_ratio": _safe_num(financials.get("current_ratio"), 1.4),
        "interest_coverage_ratio": _safe_num(financials.get("interest_coverage_ratio"), 2.0),
        "dscr": dscr,
        "gst_banking_ratio": _safe_num(bank.get("banking_to_gst_ratio"), 1.0),
        "itr_gst_consistency_score": _safe_num(
            100 - payload.get("cross_validation", {}).get("itr_vs_gst_revenue_gap", 0.0), 80.0
        ),
        "average_bank_balance_to_limit_ratio": _safe_num(bank.get("abb_to_claimed_revenue_ratio"), 0.15),
        "has_auditor_qualification": float(bool(financials.get("auditor_qualifications"))),
        "has_going_concern_doubt": float(bool(financials.get("going_concern_doubts"))),
        "has_litigation": float(bool(research.get("litigation_count", 0) > 0)),
        "has_mca_struck_off_associates": float(bool(research.get("mca_struck_off_count", 0) > 0)),
        "has_circular_trading_signals": float(has_circular),
        "has_revenue_inflation_signals": float(bool(gst.get("revenue_inflation_flag", False))),
        "has_promoter_fraud_news": float(bool(research.get("promoter_fraud_hits", 0) > 0)),
        "has_sector_headwinds": float(bool(research.get("sector_headwinds", False))),
        "has_nclt_proceedings": float(bool(research.get("has_nclt", False))),
        "gstr3b_vs_2a_itc_gap": gst_itc_gap,
        "gst_return_filing_consistency": _safe_num(gst.get("filing_consistency_pct"), 85.0),
        "mca_filing_compliance_score": _safe_num(research.get("mca_filing_compliance_score"), 80.0),
        "cibil_commercial_score": _safe_num(research.get("cibil_commercial_score"), 700.0),
        "management_integrity_score": _safe_num(due.get("management_integrity_score"), 6.0),
        "factory_capacity_utilization": _safe_num(due.get("factory_capacity_utilization"), 65.0),
        "due_diligence_risk_adjustment": _safe_num(due.get("due_diligence_risk_adjustment"), 0.0),
        "collateral_coverage_ratio": _safe_num(collateral.get("collateral_coverage_ratio"), 1.1),
        "collateral_type_score": _safe_num(collateral.get("collateral_type_score"), 6.0),
    }

    # Sector multiplier penalizes riskier sectors in capacity and leverage-sensitive features.
    vector["debt_equity_ratio"] *= sector_multiplier
    vector["dscr"] /= max(sector_multiplier, 0.8)
    return vector

