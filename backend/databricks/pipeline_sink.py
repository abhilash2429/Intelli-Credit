"""
Pipeline-to-Delta bridge.

Persists pipeline outputs to Delta Lake for Databricks-native CAM assembly.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Iterable

from pyspark.sql import Row, SparkSession

from backend.core.structured_logging import get_logger
from backend.databricks.delta_writer import DeltaWriter
from backend.databricks.schema_registry import (
    BANK_ANALYTICS_SCHEMA,
    CAM_RESEARCH_SCHEMA,
    CROSS_VALIDATION_SCHEMA,
    GST_ANNUAL_SUMMARY_SCHEMA,
    RESEARCH_FINDING_SCHEMA,
)
from backend.schemas.credit import BankStatementMetrics, CrossValidationReport, ResearchFinding

logger = get_logger(__name__)


class DatabricksPipelineSink:
    """
    Writes key pipeline outputs to Delta Lake.
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.writer = DeltaWriter(spark)

    def write_gst_summary(
        self,
        *,
        company_id: str,
        gst_turnover: float,
        itc_claimed: float,
        itc_available_2a: float,
        mismatch_pct: float,
        has_circular_trading: bool,
        filing_consistency_pct: float,
        financial_year: str = "unknown",
    ) -> None:
        overclaim = max(0.0, itc_claimed - itc_available_2a)
        row = Row(
            company_id=company_id,
            financial_year=financial_year,
            gst_annual_turnover=float(gst_turnover),
            total_itc_claimed=float(itc_claimed),
            total_itc_available_2a=float(itc_available_2a),
            itc_overclaim_amount=float(overclaim),
            overall_itc_gap_pct=float(mismatch_pct),
            filing_compliance_pct=float(filing_consistency_pct),
            critical_flag_months=["Unknown"] if has_circular_trading else [],
            has_circular_trading=bool(has_circular_trading),
            ingested_at=datetime.utcnow(),
        )
        df = self.spark.createDataFrame([row], GST_ANNUAL_SUMMARY_SCHEMA)
        self.writer.upsert(df, "gst_annual_summary", ["company_id", "financial_year"])

    def write_bank_analytics(self, company_id: str, metrics: BankStatementMetrics) -> None:
        circular_pairs = metrics.circular_credit_debit_pairs or []
        circular_value = float(sum(t.amount for t in circular_pairs))
        dates = [t.date for t in circular_pairs if getattr(t, "date", None)]
        row = Row(
            company_id=company_id,
            period_start=min(dates) if dates else None,
            period_end=max(dates) if dates else None,
            banking_turnover_credits=float(metrics.banking_turnover),
            avg_monthly_balance=float(metrics.average_monthly_balance),
            circular_transaction_count=int(len(circular_pairs)),
            circular_transaction_value=circular_value,
            window_dressing_detected=bool(metrics.year_end_window_dressing),
            window_dressing_amount=0.0,
            emi_payments_annual=float(sum(e.amount for e in (metrics.emi_payments or []))),
            banking_to_gst_ratio=float(metrics.banking_to_gst_ratio),
            ingested_at=datetime.utcnow(),
        )
        df = self.spark.createDataFrame([row], BANK_ANALYTICS_SCHEMA)
        self.writer.upsert(df, "bank_analytics", ["company_id", "period_start"])

    def write_cross_validation(self, company_id: str, report: CrossValidationReport) -> None:
        anomalies = [
            {
                "title": a.title,
                "details": a.details,
                "severity": a.severity.value,
            }
            for a in report.anomalies
        ]
        fraud_indicators = [f"{f.indicator} ({f.severity.value})" for f in report.fraud_indicators]
        verdict = "LOW_RISK"
        score = float(report.overall_data_consistency_score)
        if score < 50:
            verdict = "HIGH_RISK"
        elif score < 75:
            verdict = "MEDIUM_RISK"

        row = Row(
            company_id=company_id,
            gst_vs_bank_gap_pct=float(report.gst_vs_bank_revenue_gap),
            gst_vs_itr_gap_pct=float(report.itr_vs_gst_revenue_gap),
            itr_vs_bank_gap_pct=0.0,
            dscr=float(report.debt_service_coverage_ratio),
            data_consistency_score=score,
            fraud_indicators=fraud_indicators,
            anomalies_json=json.dumps(anomalies),
            overall_verdict=verdict,
            validated_at=datetime.utcnow(),
        )
        df = self.spark.createDataFrame([row], CROSS_VALIDATION_SCHEMA)
        self.writer.upsert(df, "cross_validation", ["company_id"])

    def write_research_findings(
        self,
        *,
        company_id: str,
        findings: Iterable[ResearchFinding],
        research_job_id: str = "",
    ) -> None:
        rows = []
        now = datetime.utcnow()
        for finding in findings:
            summary = finding.summary or ""
            headline = summary.split(".")[0][:180] if summary else finding.source_name
            rows.append(
                Row(
                    finding_id=str(uuid.uuid4()),
                    company_id=company_id,
                    finding_type=finding.finding_type.value,
                    severity=finding.severity.value,
                    headline=headline,
                    summary=summary,
                    source_url=finding.source_url,
                    source_name=finding.source_name,
                    source_date=finding.date_of_finding,
                    raw_content=(finding.raw_snippet or "")[:2000],
                    score_impact=self._score_impact_from_severity(finding.severity.value),
                    cam_section="research_summary",
                    research_job_id=research_job_id,
                    ingested_at=now,
                )
            )

        if not rows:
            return

        df = self.spark.createDataFrame(rows, RESEARCH_FINDING_SCHEMA)
        self.writer.upsert(df, "research_findings", ["finding_id"])

    def write_research_narrative(
        self,
        *,
        company_id: str,
        company_name: str,
        research_job_id: str,
        research_verdict: str,
        total_findings: int,
        total_score_impact: float,
        cam_narrative: str,
    ) -> None:
        row = Row(
            company_id=company_id,
            company_name=company_name,
            research_job_id=research_job_id,
            research_verdict=research_verdict,
            total_findings=int(total_findings),
            total_score_impact=float(total_score_impact),
            cam_narrative=cam_narrative,
            generated_at=datetime.utcnow(),
        )
        df = self.spark.createDataFrame([row], CAM_RESEARCH_SCHEMA)
        self.writer.upsert(df, "cam_research", ["company_id"])

    @staticmethod
    def _score_impact_from_severity(severity: str) -> float:
        mapping = {
            "CRITICAL": -20.0,
            "HIGH": -12.0,
            "MEDIUM": -6.0,
            "LOW": -1.0,
            "INFORMATIONAL": 0.0,
        }
        return mapping.get(severity.upper(), 0.0)

