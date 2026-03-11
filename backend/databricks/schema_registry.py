"""
Delta table schemas used by the Intelli-Credit pipeline.
"""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DateType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


RESEARCH_FINDING_SCHEMA = StructType(
    [
        StructField("finding_id", StringType(), False),
        StructField("company_id", StringType(), False),
        StructField("finding_type", StringType(), True),
        StructField("severity", StringType(), True),
        StructField("headline", StringType(), True),
        StructField("summary", StringType(), True),
        StructField("source_url", StringType(), True),
        StructField("source_name", StringType(), True),
        StructField("source_date", DateType(), True),
        StructField("raw_content", StringType(), True),
        StructField("score_impact", DoubleType(), True),
        StructField("cam_section", StringType(), True),
        StructField("research_job_id", StringType(), True),
        StructField("ingested_at", TimestampType(), False),
    ]
)


CROSS_VALIDATION_SCHEMA = StructType(
    [
        StructField("company_id", StringType(), False),
        StructField("gst_vs_bank_gap_pct", DoubleType(), True),
        StructField("gst_vs_itr_gap_pct", DoubleType(), True),
        StructField("itr_vs_bank_gap_pct", DoubleType(), True),
        StructField("dscr", DoubleType(), True),
        StructField("data_consistency_score", DoubleType(), True),
        StructField("fraud_indicators", ArrayType(StringType()), True),
        StructField("anomalies_json", StringType(), True),
        StructField("overall_verdict", StringType(), True),
        StructField("validated_at", TimestampType(), False),
    ]
)


GST_ANNUAL_SUMMARY_SCHEMA = StructType(
    [
        StructField("company_id", StringType(), False),
        StructField("financial_year", StringType(), False),
        StructField("gst_annual_turnover", DoubleType(), True),
        StructField("total_itc_claimed", DoubleType(), True),
        StructField("total_itc_available_2a", DoubleType(), True),
        StructField("itc_overclaim_amount", DoubleType(), True),
        StructField("overall_itc_gap_pct", DoubleType(), True),
        StructField("filing_compliance_pct", DoubleType(), True),
        StructField("critical_flag_months", ArrayType(StringType()), True),
        StructField("has_circular_trading", BooleanType(), True),
        StructField("ingested_at", TimestampType(), False),
    ]
)


BANK_ANALYTICS_SCHEMA = StructType(
    [
        StructField("company_id", StringType(), False),
        StructField("period_start", DateType(), True),
        StructField("period_end", DateType(), True),
        StructField("banking_turnover_credits", DoubleType(), True),
        StructField("avg_monthly_balance", DoubleType(), True),
        StructField("circular_transaction_count", LongType(), True),
        StructField("circular_transaction_value", DoubleType(), True),
        StructField("window_dressing_detected", BooleanType(), True),
        StructField("window_dressing_amount", DoubleType(), True),
        StructField("emi_payments_annual", DoubleType(), True),
        StructField("banking_to_gst_ratio", DoubleType(), True),
        StructField("ingested_at", TimestampType(), False),
    ]
)


CAM_RESEARCH_SCHEMA = StructType(
    [
        StructField("company_id", StringType(), False),
        StructField("company_name", StringType(), False),
        StructField("research_job_id", StringType(), True),
        StructField("research_verdict", StringType(), True),
        StructField("total_findings", LongType(), True),
        StructField("total_score_impact", DoubleType(), True),
        StructField("cam_narrative", StringType(), True),
        StructField("generated_at", TimestampType(), False),
    ]
)

