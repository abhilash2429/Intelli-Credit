"""
Core pydantic schemas for the Intelli-Credit v1 API.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskCategory(str, Enum):
    """Risk classification categories for credit decisions."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DocumentType(str, Enum):
    ANNUAL_REPORT = "ANNUAL_REPORT"
    SANCTION_LETTER = "SANCTION_LETTER"
    LEGAL_NOTICE = "LEGAL_NOTICE"
    RATING_REPORT = "RATING_REPORT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    BOARD_MINUTES = "BOARD_MINUTES"
    GST = "GST"
    BANK_STATEMENT = "BANK_STATEMENT"
    ITR = "ITR"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class FindingType(str, Enum):
    FRAUD_ALERT = "FRAUD_ALERT"
    LITIGATION = "LITIGATION"
    REGULATORY = "REGULATORY"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    SECTOR = "SECTOR"
    SECTOR_NEWS = "SECTOR_NEWS"
    COMPANY_NEWS = "COMPANY_NEWS"
    PROMOTER_BACKGROUND = "PROMOTER_BACKGROUND"
    MCA_FILING = "MCA_FILING"
    INFORMATIONAL = "INFORMATIONAL"
    NEUTRAL = "NEUTRAL"


class MoneyAmount(BaseModel):
    amount: float
    currency: str = "INR"
    period: Optional[str] = None
    source: Optional[str] = None
    confidence_score: float = 0.8


class BankLimit(BaseModel):
    lender: str
    limit_amount: float
    facility_type: str = "CC/OD"
    confidence_score: float = 0.7


class LegalDispute(BaseModel):
    title: str
    court: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    confidence_score: float = 0.7


class Transaction(BaseModel):
    date: date
    party: str
    amount: float
    txn_type: str
    narration: Optional[str] = None


class EMIPayment(BaseModel):
    date: date
    lender: Optional[str] = None
    amount: float
    confidence_score: float = 0.7


class ExtractedFinancialData(BaseModel):
    company_name: str = "Unknown"
    cin_number: Optional[str] = None
    pan_number: Optional[str] = None
    revenue_figures: List[MoneyAmount] = Field(default_factory=list)
    profit_figures: List[MoneyAmount] = Field(default_factory=list)
    total_debt: Optional[MoneyAmount] = None
    existing_bank_limits: List[BankLimit] = Field(default_factory=list)
    collateral_descriptions: List[str] = Field(default_factory=list)
    legal_disputes: List[LegalDispute] = Field(default_factory=list)
    key_risks_mentioned: List[str] = Field(default_factory=list)
    related_party_transactions: List[str] = Field(default_factory=list)
    auditor_qualifications: List[str] = Field(default_factory=list)
    going_concern_doubts: bool = False
    document_type: DocumentType = DocumentType.UNKNOWN
    extraction_confidence: float = 0.5
    needs_human_review: bool = False


class GSTR3BData(BaseModel):
    period: str
    outward_supplies: float
    itc_claimed: float
    tax_paid: float


class GSTR2AData(BaseModel):
    period: str
    available_itc: float
    vendor_purchases: Dict[str, float] = Field(default_factory=dict)


class GSTR1Data(BaseModel):
    period: str
    invoice_sales_total: float
    hsn_summary: Dict[str, float] = Field(default_factory=dict)


class MismatchReport(BaseModel):
    itc_inflation_percentage: float
    revenue_inflation_flag: bool
    suspected_circular_trading: bool
    risk_level: Severity
    explanation: str


class BankStatementMetrics(BaseModel):
    average_monthly_balance: float
    abb_to_claimed_revenue_ratio: float
    max_debit_single_transaction: float
    circular_credit_debit_pairs: List[Transaction] = Field(default_factory=list)
    emi_payments: List[EMIPayment] = Field(default_factory=list)
    suspected_shell_company_transfers: List[str] = Field(default_factory=list)
    cash_withdrawal_pattern: str
    year_end_window_dressing: bool
    banking_turnover: float
    banking_to_gst_ratio: float


class Anomaly(BaseModel):
    title: str
    details: str
    severity: Severity


class FraudIndicator(BaseModel):
    indicator: str
    source: str
    severity: Severity
    confidence: float


class CrossValidationReport(BaseModel):
    gst_vs_bank_revenue_gap: float
    itr_vs_gst_revenue_gap: float
    debt_service_coverage_ratio: float
    working_capital_cycle_days: int
    anomalies: List[Anomaly] = Field(default_factory=list)
    overall_data_consistency_score: float
    fraud_indicators: List[FraudIndicator] = Field(default_factory=list)
    recommendation_flags: List[str] = Field(default_factory=list)


class Director(BaseModel):
    name: str
    din: Optional[str] = None
    status: Optional[str] = None


class Charge(BaseModel):
    lender: str
    amount: float
    charge_type: str


class MCAReport(BaseModel):
    company_cin: str
    registration_date: date
    authorized_capital: float
    paid_up_capital: float
    directors: List[Director] = Field(default_factory=list)
    associated_struck_off_companies: List[str] = Field(default_factory=list)
    registered_charges: List[Charge] = Field(default_factory=list)
    filing_compliance_score: float
    last_agm_date: Optional[date] = None
    mca_red_flags: List[str] = Field(default_factory=list)


class ResearchFinding(BaseModel):
    headline: Optional[str] = None
    source_url: str
    source_name: str
    finding_type: FindingType
    summary: str
    severity: Severity
    date_of_finding: Optional[date] = None
    confidence: float = 0.7
    raw_snippet: str
    score_impact: float = 0.0
    cam_section: str = "research_summary"


class KMPAssessment(BaseModel):
    name: str
    role: str
    credibility_score: Optional[int] = None
    notes: Optional[str] = None


class DueDiligenceInput(BaseModel):
    factory_visit_date: Optional[date] = None
    capacity_utilization_percent: Optional[int] = Field(default=None, ge=0, le=100)
    factory_condition: Optional[str] = None
    inventory_levels: Optional[str] = None
    management_cooperation: Optional[str] = None
    free_text_notes: str = ""
    management_interview_rating: Optional[int] = Field(default=None, ge=1, le=5)
    borrower_finance_officer_name: Optional[str] = None
    borrower_finance_officer_role: Optional[str] = None
    borrower_finance_officer_email: Optional[str] = None
    borrower_finance_officer_phone: Optional[str] = None
    borrower_business_highlights: Optional[str] = None
    borrower_major_customers: Optional[str] = None
    borrower_contingent_liabilities: Optional[str] = None
    borrower_planned_capex: Optional[str] = None
    borrower_disclosed_risks: Optional[str] = None
    key_management_persons: List[KMPAssessment] = Field(default_factory=list)


class DueDiligenceInsight(BaseModel):
    sentiment: str
    risk_factors: List[str]
    positive_factors: List[str]
    score_adjustment: float
    cam_concerns: List[str]


class CreditDecision(BaseModel):
    credit_score: float
    normalized_score: float
    score_band: str
    risk_grade: str
    recommendation: str
    recommended_loan_amount: float
    recommended_interest_rate: float
    interest_premium_bps: int
    confidence_interval: List[float]
    human_input_impact_points: float = 0.0
    rule_hits: List[str] = Field(default_factory=list)


class Explanation(BaseModel):
    top_positive_factors: List[str]
    top_negative_factors: List[str]
    decision_narrative: str
    shap_waterfall_data: Dict[str, float]
    confidence_in_decision: float


class PipelineStep(str, Enum):
    DOCUMENTS_RECEIVED = "DOCUMENTS_RECEIVED"
    OCR_EXTRACTION = "OCR_EXTRACTION"
    GST_PARSING = "GST_PARSING"
    RESEARCH_AGENT = "RESEARCH_AGENT"
    ML_SCORING = "ML_SCORING"
    CAM_GENERATION = "CAM_GENERATION"


class AuditEvent(BaseModel):
    timestamp: datetime
    step: PipelineStep
    message: str
    source: str
    severity: Severity = Severity.INFORMATIONAL


class CompanyCreateInput(BaseModel):
    name: str
    cin: Optional[str] = None
    sector: str = "agri_processing"
    loan_amount_requested: float = 0.0
    loan_tenor_months: int = 36
    loan_purpose: str = "working_capital"
    pan_number: Optional[str] = None
    annual_turnover_cr: Optional[float] = None
    year_of_incorporation: Optional[int] = None
    registered_address: Optional[str] = None


class CompanySummary(BaseModel):
    company_id: str
    name: str
    sector: str
    status: str = "created"
