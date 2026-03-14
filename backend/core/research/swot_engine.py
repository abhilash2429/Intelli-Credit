"""
Deterministic SWOT analysis engine.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.core.formatting import format_currency_cr, format_percentage, format_ratio


def generate_swot(extracted_data: dict, grade: str, score: float) -> dict:
    """
    extracted_data: dict of all extracted fields from documents
    grade: credit grade string e.g. 'AA-'
    score: normalized score 0-100
    """
    strengths = []
    weaknesses = []
    opportunities = []
    threats = []

    # ── STRENGTHS ──
    pledge = extracted_data.get("promoter_pledge_pct", -1)
    if pledge == 0:
        strengths.append("Zero promoter pledge - shares fully unencumbered")
    elif 0 < pledge <= 20:
        strengths.append(f"Low promoter pledge at {format_percentage(pledge)}")

    rating_action = extracted_data.get("crisil_rating_action", "")
    rating = extracted_data.get("crisil_rating", "")
    if rating_action == "UPGRADED" and rating:
        strengths.append(f"Credit rating upgraded to {rating} - improving profile")
    elif rating in ["AAA", "AA+", "AA", "AA-", "A+", "A"]:
        strengths.append(f"Investment grade rating: {rating}")

    ebitda_margin = extracted_data.get("ebitda_margin_pct", 0)
    if ebitda_margin > 20:
        strengths.append(
            f"Strong EBITDA margin of {format_percentage(ebitda_margin)} (sector benchmark ~15%)"
        )

    interest_cov = extracted_data.get("interest_coverage_ratio", 0)
    if interest_cov > 5:
        strengths.append(f"Comfortable interest coverage of {format_ratio(interest_cov, decimals=1)}")

    de_ratio = extracted_data.get("de_ratio", None)
    if isinstance(de_ratio, (int, float)) and de_ratio < 0.5:
        strengths.append(f"Conservative leverage at D/E {format_ratio(de_ratio)}")

    revenue_cagr = extracted_data.get("revenue_cagr_3yr", 0)
    if revenue_cagr > 12:
        strengths.append(f"Revenue CAGR of {format_percentage(revenue_cagr)} over 3 years")

    gst_mismatch = extracted_data.get("gst_mismatch_pct", 100)
    if gst_mismatch == 0:
        strengths.append("GST reconciliation clean - 0% mismatch, no circular trading")

    # ── WEAKNESSES ──
    customer_conc = extracted_data.get("customer_concentration_top5_pct", 0)
    if customer_conc > 50:
        weaknesses.append(
            f"Customer concentration risk - top 5 = {format_percentage(customer_conc)} of revenue"
        )

    if isinstance(de_ratio, (int, float)) and de_ratio > 1.5:
        weaknesses.append(f"Elevated leverage at D/E {format_ratio(de_ratio)}")

    current_ratio = extracted_data.get("current_ratio", 0)
    if 1.0 < current_ratio < 1.3:
        weaknesses.append(f"Tight current ratio of {format_ratio(current_ratio)}")

    pat_margin = extracted_data.get("pat_margin_pct", 0)
    if 0 < pat_margin < 7:
        weaknesses.append(f"Thin PAT margin of {format_percentage(pat_margin)}")

    # ── OPPORTUNITIES ──
    ev_loi = extracted_data.get("ev_loi_cr", 0)
    if ev_loi > 0:
        opportunities.append(f"EV component LoIs worth {format_currency_cr(ev_loi)} secured from OEMs")

    export_growth = extracted_data.get("export_growth_pct", 0)
    if export_growth > 15:
        opportunities.append(
            f"Export revenues growing {format_percentage(export_growth)} - international expansion"
        )

    capex_irr = extracted_data.get("expansion_irr_pct", 0)
    if capex_irr > 15:
        opportunities.append(f"Approved capacity expansion with IRR of {format_percentage(capex_irr)}")

    strategic_partner = extracted_data.get("strategic_partnership_mentioned", "")
    if strategic_partner:
        opportunities.append(f"Strategic partnership discussions with {strategic_partner}")

    # ── THREATS ──
    litigation_cr = extracted_data.get("total_litigation_exposure_cr", 0)
    net_worth_cr = extracted_data.get("net_worth_cr", 1)
    if net_worth_cr and litigation_cr > net_worth_cr * 0.5:
        threats.append(
            f"Litigation exposure {format_currency_cr(litigation_cr)} = "
            f"{format_ratio(litigation_cr / net_worth_cr, decimals=1)} net worth"
        )
    elif litigation_cr > 0:
        threats.append(f"Contingent liabilities of {format_currency_cr(litigation_cr)} under appeal")

    commodity_risk = extracted_data.get("commodity_price_risk", False)
    if commodity_risk:
        threats.append("Input cost volatility from commodity price movements")

    pledge = extracted_data.get("promoter_pledge_pct", 0)
    if pledge > 75:
        threats.append(
            f"Promoter pledge {format_percentage(pledge)} - forced selling risk if share price falls"
        )

    parent_risk = extracted_data.get("parent_debt_risk", False)
    if parent_risk:
        threats.append("Parent company debt obligations may require dividend upstreaming")

    # ── FALLBACKS ──
    if not strengths:
        strengths = [f"Score of {score:.0f}/100 indicates acceptable credit quality"]
    if not weaknesses:
        weaknesses = ["No material weaknesses identified from available documents"]
    if not opportunities:
        opportunities = ["Sector growth trajectory supports future revenue expansion"]
    if not threats:
        threats = ["Standard macro and sector risks apply"]

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
        "investment_thesis": (
            f"{extracted_data.get('company_name', 'Company')} is rated {grade} "
            f"with a credit score of {score:.0f}/100. "
            f"{'Strong fundamentals support full approval.' if score >= 75 else 'Conditional approval recommended with covenants.'}"
        ),
    }


def build_swot_extracted_data(
    *,
    company_name: str,
    financials: Dict[str, Any],
    features: Dict[str, float],
    shareholding_data: Dict[str, Any],
    gst_payload: Dict[str, Any],
    research_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Build extracted_data payload expected by generate_swot."""
    gst_mismatch = gst_payload.get("mismatch_report")
    if hasattr(gst_mismatch, "itc_inflation_percentage"):
        gst_mismatch_pct = float(getattr(gst_mismatch, "itc_inflation_percentage", 0.0))
    elif isinstance(gst_mismatch, dict):
        gst_mismatch_pct = float(gst_mismatch.get("itc_inflation_percentage", 0.0) or 0.0)
    else:
        gst_mismatch_pct = 0.0

    return {
        "company_name": company_name,
        "promoter_pledge_pct": float(
            shareholding_data.get("total_pledged_pct", shareholding_data.get("promoter_pledge_pct", 0.0)) or 0.0
        ),
        "crisil_rating_action": financials.get("crisil_rating_action", ""),
        "crisil_rating": financials.get("crisil_rating", ""),
        "ebitda_margin_pct": float(financials.get("ebitda_margin_pct", financials.get("ebitda_margin", 0.0)) or 0.0),
        "interest_coverage_ratio": float(financials.get("interest_coverage_ratio", 0.0) or 0.0),
        "de_ratio": (
            float(financials.get("de_ratio"))
            if financials.get("de_ratio") not in (None, "")
            else (
                float(financials.get("debt_equity_ratio"))
                if financials.get("debt_equity_ratio") not in (None, "")
                else None
            )
        ),
        "revenue_cagr_3yr": float(features.get("revenue_cagr_3yr", 0.0) or 0.0),
        "gst_mismatch_pct": gst_mismatch_pct,
        "customer_concentration_top5_pct": float(financials.get("customer_concentration_top5_pct", 0.0) or 0.0),
        "current_ratio": float(financials.get("current_ratio", 0.0) or 0.0),
        "pat_margin_pct": float(financials.get("pat_margin_pct", 0.0) or 0.0),
        "ev_loi_cr": float(financials.get("ev_loi_cr", 0.0) or 0.0),
        "export_growth_pct": float(financials.get("export_growth_pct", 0.0) or 0.0),
        "expansion_irr_pct": float(financials.get("expansion_irr_pct", 0.0) or 0.0),
        "strategic_partnership_mentioned": financials.get("strategic_partnership_mentioned", ""),
        "total_litigation_exposure_cr": float(
            financials.get("total_litigation_exposure_cr", financials.get("total_contingent_liabilities", 0.0)) or 0.0
        ),
        "net_worth_cr": float(financials.get("net_worth_cr", financials.get("net_worth_crore", 1.0)) or 1.0),
        "commodity_price_risk": bool(research_summary.get("sector_headwinds", False)),
        "parent_debt_risk": bool(research_summary.get("parent_debt_risk", False)),
        "has_mca_struck_off_associates": int(research_summary.get("mca_struck_off_count", 0) or 0) > 0,
        "has_nclt_proceedings": bool(research_summary.get("has_nclt", False)),
        "due_diligence_risk_adjustment": float(features.get("due_diligence_risk_adjustment", 0.0) or 0.0),
    }
