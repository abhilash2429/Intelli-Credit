"""
Cross-source financial consistency validator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.schemas.credit import (
    Anomaly,
    BankStatementMetrics,
    CrossValidationReport,
    FraudIndicator,
    MismatchReport,
    Severity,
)


class CrossValidator:
    """
    Reconcile GST, banking, and ITR signals into one consistency score.
    """

    def validate(
        self,
        *,
        gst_turnover: float,
        bank_metrics: Optional[BankStatementMetrics] = None,
        itr_data: Optional[Dict[str, Any]] = None,
        gst_mismatch: Optional[MismatchReport] = None,
        annual_debt_obligation: float = 1.0,
        net_cash_flow: Optional[float] = None,
        receivable_days: int = 45,
        inventory_days: int = 35,
        payable_days: int = 30,
        gst_xlsx_data: Optional[Dict[str, Any]] = None,
        shareholding_data: Optional[Dict[str, Any]] = None,
        xlsx_financials: Optional[Dict[str, Any]] = None,
    ) -> CrossValidationReport:
        anomalies: List[Anomaly] = []
        fraud_indicators: List[FraudIndicator] = []
        recommendation_flags: List[str] = []

        has_bank_metrics = bank_metrics is not None
        bank_turnover = float(bank_metrics.banking_turnover) if bank_metrics else float(gst_turnover or 0.0)
        gst_vs_bank_gap = self._pct_gap(gst_turnover, bank_turnover)

        itr_revenue = float((itr_data or {}).get("gross_revenue", 0.0))
        itr_vs_gst_gap = self._pct_gap(itr_revenue, gst_turnover)

        if not has_bank_metrics:
            anomalies.append(
                Anomaly(
                    title="Bank statement unavailable",
                    details="Bank statement metrics missing; GST vs banking reconciliation used fallback estimates.",
                    severity=Severity.MEDIUM,
                )
            )
            recommendation_flags.append(
                "Collect at least 6-12 months of bank statements for stronger cross-validation."
            )

        if has_bank_metrics and gst_vs_bank_gap > 15:
            anomalies.append(
                Anomaly(
                    title="GST vs Banking mismatch",
                    details=f"Gap is {gst_vs_bank_gap:.2f}% between reported GST turnover and bank credits.",
                    severity=Severity.HIGH,
                )
            )
            recommendation_flags.append("Investigate revenue recognition and cash realization.")

        if itr_vs_gst_gap > 10:
            anomalies.append(
                Anomaly(
                    title="ITR vs GST mismatch",
                    details=f"Tax filing turnover differs by {itr_vs_gst_gap:.2f}%.",
                    severity=Severity.MEDIUM,
                )
            )

        if bank_metrics and bank_metrics.year_end_window_dressing:
            fraud_indicators.append(
                FraudIndicator(
                    indicator="Year-end window dressing detected",
                    source="bank_statement",
                    severity=Severity.HIGH,
                    confidence=0.82,
                )
            )
            recommendation_flags.append("Impose monthly stock and debtor statement covenant.")

        if bank_metrics and bank_metrics.circular_credit_debit_pairs:
            fraud_indicators.append(
                FraudIndicator(
                    indicator="Circular credit-debit transaction pattern",
                    source="bank_statement",
                    severity=Severity.CRITICAL,
                    confidence=0.86,
                )
            )

        if gst_mismatch and gst_mismatch.suspected_circular_trading:
            fraud_indicators.append(
                FraudIndicator(
                    indicator="GST ITC anomaly indicates potential circular trading",
                    source="gst_mismatch",
                    severity=Severity.CRITICAL,
                    confidence=0.88,
                )
            )

        # GST ITC mismatch from XLSX-parsed data
        if gst_xlsx_data:
            itc_gap = float(gst_xlsx_data.get("itc_mismatch_pct", 0.0))
            if itc_gap > 5:
                sev = Severity.CRITICAL if itc_gap > 20 else Severity.HIGH
                anomalies.append(
                    Anomaly(
                        title="GST ITC Mismatch",
                        details=f"ITC claimed exceeds available by {itc_gap:.1f}%. "
                                f"Excess: ₹{gst_xlsx_data.get('itc_mismatch_abs', 0):.0f} Cr over "
                                f"₹{gst_xlsx_data.get('itc_2a_available', 0):.0f} Cr available in GSTR-2A.",
                        severity=sev,
                    )
                )
                if itc_gap > 20:
                    recommendation_flags.append("Investigate circular trading and fake invoicing risk.")

        # Round-trip bank transfer detection (wider tolerance: 5% within 3 days)
        if bank_metrics and bank_metrics.circular_credit_debit_pairs:
            pairs = bank_metrics.circular_credit_debit_pairs
            if len(pairs) > 0:
                total_amount = sum(t.amount for t in pairs)
                anomalies.append(
                    Anomaly(
                        title="Round-trip Bank Transfers Detected",
                        details=f"{len(pairs)} circular credit-debit pair(s) found. "
                                f"Total amount: ₹{total_amount:,.0f} Cr. "
                                "Same counterparty, matching amounts within 5%, within 3 calendar days.",
                        severity=Severity.HIGH,
                    )
                )

        # Promoter pledge anomaly
        if shareholding_data:
            pledge_pct = float(shareholding_data.get("promoter_pledge_pct", 0.0))
            if pledge_pct > 75:
                sev = Severity.CRITICAL if pledge_pct > 90 else Severity.HIGH
                anomalies.append(
                    Anomaly(
                        title="Promoter Pledge Critical",
                        details=f"Promoter has pledged {pledge_pct:.1f}% of holdings. "
                                f"{'CRITICAL: >90% pledge indicates extreme financial stress.' if pledge_pct > 90 else 'HIGH: >75% pledge indicates significant stress.'}",
                        severity=sev,
                    )
                )
                recommendation_flags.append("Obtain pledge reduction plan from promoter before sanction.")

        # Contingent liability ratio check
        if xlsx_financials:
            contingent = float(xlsx_financials.get("total_contingent_liabilities", 0.0))
            equity = float(xlsx_financials.get("net_worth_crore", 0.0))
            if equity > 0 and contingent > 0:
                ratio = contingent / equity
                if ratio > 5.0:
                    sev = Severity.CRITICAL if ratio > 10 else Severity.HIGH
                    anomalies.append(
                        Anomaly(
                            title="Contingent Liability Concentration",
                            details=f"Contingent liabilities (₹{contingent:,.0f} Cr) are {ratio:.1f}x net worth (₹{equity:,.0f} Cr). "
                                    f"{'CRITICAL risk of capital erosion.' if ratio > 10 else 'HIGH concentration risk.'}",
                            severity=sev,
                        )
                    )

        effective_cash_flow = (
            net_cash_flow
            if net_cash_flow is not None
            else (bank_turnover * 0.1 if bank_turnover > 0 else max(gst_turnover, 0.0) * 0.08)
        )

        debt_service_coverage_ratio = effective_cash_flow / max(
            annual_debt_obligation, 1.0
        )
        working_capital_cycle_days = int(receivable_days + inventory_days - payable_days)

        base_score = 100.0
        base_score -= min(35.0, gst_vs_bank_gap * 0.8) if has_bank_metrics else 8.0
        base_score -= min(25.0, itr_vs_gst_gap * 0.7)
        base_score -= 20.0 if (bank_metrics and bank_metrics.year_end_window_dressing) else 0.0
        base_score -= (
            min(20.0, len(bank_metrics.circular_credit_debit_pairs) * 2.0)
            if bank_metrics
            else 0.0
        )
        if gst_mismatch and gst_mismatch.risk_level in {Severity.CRITICAL, Severity.HIGH}:
            base_score -= 15.0
        consistency_score = max(0.0, round(base_score, 2))

        if consistency_score < 55:
            recommendation_flags.append("Enhanced forensic review before sanction.")
        elif consistency_score < 75:
            recommendation_flags.append("Conditional approval with tighter monitoring.")

        return CrossValidationReport(
            gst_vs_bank_revenue_gap=round(gst_vs_bank_gap, 2),
            itr_vs_gst_revenue_gap=round(itr_vs_gst_gap, 2),
            debt_service_coverage_ratio=round(debt_service_coverage_ratio, 3),
            working_capital_cycle_days=working_capital_cycle_days,
            anomalies=anomalies,
            overall_data_consistency_score=consistency_score,
            fraud_indicators=fraud_indicators,
            recommendation_flags=recommendation_flags,
        )

    @staticmethod
    def build_fraud_graph(
        *,
        company_name: str,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build relationship-first graph from extracted entities.
        Includes promoters, subsidiaries, and charge holders/lenders.
        """
        data = extracted_data or {}
        nodes: List[Dict[str, Any]] = [
            {
                "id": "main",
                "label": company_name,
                "type": "company",
                "risk": "LOW",
            }
        ]
        links: List[Dict[str, Any]] = []

        promoters = data.get("promoters", []) or []
        for i, promoter in enumerate(promoters):
            node_id = f"promoter_{i}"
            pledge_pct = float(promoter.get("pledge_pct", 0.0) or 0.0)
            risk_level = "HIGH" if pledge_pct > 75 else ("MEDIUM" if pledge_pct > 25 else "LOW")
            nodes.append(
                {
                    "id": node_id,
                    "label": str(promoter.get("name", f"Promoter {i + 1}")),
                    "type": "counterparty",
                    "risk": risk_level,
                }
            )
            holding_pct = float(promoter.get("holding_pct", 0.0) or 0.0)
            label = f"{holding_pct:.1f}% holding"
            links.append(
                {
                    "source": "main",
                    "target": node_id,
                    "value": 20,
                    "confidence": risk_level,
                    "label": label,
                }
            )

        subsidiaries = data.get("subsidiaries", []) or []
        for i, sub in enumerate(subsidiaries):
            node_id = f"sub_{i}"
            nodes.append(
                {
                    "id": node_id,
                    "label": str(sub.get("name", f"Subsidiary {i + 1}")),
                    "type": "counterparty",
                    "risk": "LOW",
                }
            )
            links.append(
                {
                    "source": "main",
                    "target": node_id,
                    "value": 18,
                    "confidence": "LOW",
                    "label": str(sub.get("relationship", "Subsidiary")),
                }
            )

        charges = data.get("mca_charges", []) or []
        for i, charge in enumerate(charges[:3]):
            node_id = f"lender_{i}"
            holder = str(charge.get("holder", f"Lender {i + 1}"))
            amount_cr = float(charge.get("amount_cr", 0.0) or 0.0)
            nodes.append(
                {
                    "id": node_id,
                    "label": holder,
                    "type": "counterparty",
                    "risk": "LOW",
                }
            )
            links.append(
                {
                    "source": "main",
                    "target": node_id,
                    "value": 16,
                    "confidence": "LOW",
                    "label": f"\u20b9{amount_cr:.2f} Cr charge",
                }
            )

        strategic_partners = data.get("strategic_partners", []) or []
        for i, partner in enumerate(strategic_partners[:3]):
            node_id = f"partner_{i}"
            label = str(partner.get("name", f"Strategic Partner {i + 1}"))
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": "counterparty",
                    "risk": "LOW",
                }
            )
            links.append(
                {
                    "source": "main",
                    "target": node_id,
                    "value": 14,
                    "confidence": "LOW",
                    "label": str(partner.get("relationship", "Strategic Partner")),
                }
            )

        rating_agencies = data.get("rating_agencies", []) or []
        for i, agency in enumerate(rating_agencies[:2]):
            node_id = f"rating_{i}"
            label = str(agency.get("name", f"Rating Agency {i + 1}"))
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": "counterparty",
                    "risk": "LOW",
                }
            )
            links.append(
                {
                    "source": "main",
                    "target": node_id,
                    "value": 12,
                    "confidence": "LOW",
                    "label": str(agency.get("relationship", "Rating Agency")),
                }
            )

        # Legacy weak association support (still used by UI disclosure block)
        weak_associations: List[Dict[str, Any]] = []

        # Compatibility: provide `edges` and explicit counters, while retaining `links`.
        edges = [
            {
                "from": link["source"],
                "to": link["target"],
                "label": link.get("label", ""),
            }
            for link in links
        ]
        return {
            "nodes": nodes,
            "links": links,
            "edges": edges,
            "entity_count": len(nodes),
            "connection_count": len(links),
            "weak_associations": weak_associations,
        }

    @staticmethod
    def _pct_gap(a: float, b: float) -> float:
        if a <= 0 and b <= 0:
            return 0.0
        denominator = max(abs(a), abs(b), 1.0)
        return abs(a - b) / denominator * 100
