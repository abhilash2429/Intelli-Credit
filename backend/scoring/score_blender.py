"""
Final Score Blending module.
Combines rule-based score and ML stress probability into a single risk score.

Formula:
  Final Risk Score = 0.6 × Rule-Based Score + 0.4 × (1 - ML_Stress_Probability) × 100

Decision thresholds (Indian banking context):
  75-100: LOW risk → APPROVE
  55-74:  MODERATE risk → CONDITIONAL APPROVE (with covenants)
  35-54:  HIGH risk → CONDITIONAL APPROVE with collateral enhancement OR REJECT
  0-34:   CRITICAL risk → REJECT (or escalate to credit committee)

Loan limit: MPBF (Maximum Permissible Bank Finance) per RBI Tandon Committee norms.
"""

from typing import Dict, Optional, Tuple

from backend.schemas.credit import RiskCategory

RULE_WEIGHT = 0.6
ML_WEIGHT = 0.4

RISK_THRESHOLDS: Dict[str, Tuple[int, int]] = {
    "LOW": (75, 100),
    "MODERATE": (55, 74),
    "HIGH": (35, 54),
    "CRITICAL": (0, 34),
}

INTEREST_PREMIUMS_BPS: Dict[str, Optional[int]] = {
    "LOW": 50,         # 0.5% over MCLR
    "MODERATE": 150,   # 1.5% over MCLR
    "HIGH": 300,       # 3.0% over MCLR
    "CRITICAL": None,  # REJECT — no lending
}


def blend_scores(rule_score: float, ml_prob: float) -> Tuple[float, str]:
    """
    Blend rule-based score and ML probability into final risk score.

    Args:
        rule_score: Score from rules engine (0-100, 100 = best).
        ml_prob: Stress probability from ML (0-1, 1 = worst).

    Returns:
        Tuple of (final_score, risk_category_string).
    """
    ml_component = (1 - ml_prob) * 100  # Invert: high stress = low score
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
    Compute recommended loan limit in ₹ Crore using MPBF approach.
    Based on RBI's Tandon Committee norms (standard in Indian banking).

    MPBF = 0.75 × (Current Assets - Current Liabilities)
    Final Limit = MPBF × (Score/100)

    Args:
        financials: Extracted financial data dict.
        risk_score: Final blended risk score (0-100).

    Returns:
        Recommended loan limit in ₹ Crore. Returns 0 if REJECT.
    """
    if risk_score < 35:
        return 0.0

    current_assets = financials.get("current_assets_crore") or 0
    current_liabilities = financials.get("current_liabilities_crore") or 0
    mpbf = 0.75 * max(current_assets - current_liabilities, 0)

    risk_multiplier = risk_score / 100
    limit = mpbf * risk_multiplier

    return round(limit, 1)


def determine_decision(risk_category: str, critical_hit: bool) -> str:
    """
    Determine the credit decision based on risk category and critical flags.

    Args:
        risk_category: Risk category string (LOW/MODERATE/HIGH/CRITICAL).
        critical_hit: Whether any CRITICAL rule was triggered.

    Returns:
        Decision string: APPROVE | CONDITIONAL_APPROVE | REJECT.
    """
    if critical_hit or risk_category == "CRITICAL":
        return "REJECT"
    elif risk_category == "LOW":
        return "APPROVE"
    else:
        return "CONDITIONAL_APPROVE"
