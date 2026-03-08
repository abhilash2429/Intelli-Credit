"""
Five Cs scoring helper for CAM generation and dashboard.
Each dimension is scored independently on a 1-10 scale.
"""

from __future__ import annotations

from typing import Dict


def analyze_five_cs(features: Dict[str, float]) -> Dict[str, Dict[str, object]]:
    """
    Convert feature vector to Character/Capacity/Capital/Collateral/Conditions scores.
    Each axis is scored independently using dimension-specific signals.
    """
    # CHARACTER: Promoter integrity, auditor opinion, MCA compliance, litigation
    char_deductions = (
        (features.get("has_promoter_fraud_news", 0) * 3.5)
        + (features.get("has_mca_struck_off_associates", 0) * 2.5)
        + (features.get("has_auditor_qualification", 0) * 2.0)
        + (features.get("has_going_concern_doubt", 0) * 2.0)
        + (features.get("has_litigation", 0) * 1.5)
        + (1.5 if features.get("management_integrity_score", 5) < 5 else 0)
        + (1.0 if features.get("gstr3b_vs_2a_itc_gap", 0) > 20 else 0)
    )
    character = max(1, 10 - char_deductions)

    # CAPACITY: Ability to repay — DSCR, interest coverage, EBITDA margin, capacity utilization
    dscr = features.get("dscr", 1.0)
    icr = features.get("interest_coverage_ratio", 1.0)
    capacity_util = features.get("factory_capacity_utilization", 60) / 100.0
    ebitda = features.get("ebitda_margin", 10) / 100.0
    capacity = min(10, max(1, dscr * 2.5 + icr * 0.8 + capacity_util * 3 + ebitda * 8))

    # CAPITAL: Financial leverage — D/E, current ratio, net worth adequacy
    de = features.get("debt_equity_ratio", 1.5)
    cr = features.get("current_ratio", 1.3)
    capital_score = max(1, min(10, 10 - de * 1.5 + cr * 1.2))

    # COLLATERAL: Security coverage and quality
    col_coverage = features.get("collateral_coverage_ratio", 1.0)
    col_type = features.get("collateral_type_score", 5)
    collateral = min(10, max(1, col_coverage * 3.5 + col_type / 2.5))

    # CONDITIONS: Sector, regulatory, macro environment
    conditions_deductions = (
        (features.get("has_sector_headwinds", 0) * 2.5)
        + (features.get("has_revenue_inflation_signals", 0) * 2.0)
        + (features.get("has_nclt_proceedings", 0) * 1.5)
        + (features.get("has_circular_trading_signals", 0) * 1.5)
    )
    conditions = max(1, min(10, 8 - conditions_deductions))

    def with_level(score: float) -> Dict[str, object]:
        if score >= 7.5:
            level = "LOW"
        elif score >= 5.0:
            level = "MEDIUM"
        else:
            level = "HIGH"
        return {"score": round(float(score), 2), "risk_level": level}

    return {
        "character": with_level(character),
        "capacity": with_level(capacity),
        "capital": with_level(capital_score),
        "collateral": with_level(collateral),
        "conditions": with_level(conditions),
    }

