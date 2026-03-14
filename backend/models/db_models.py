"""
SQLAlchemy ORM models for Intelli-Credit database.
Maps to PostgreSQL tables: companies, documents, risk_scores,
cam_outputs, qualitative_inputs, chat_history.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.database import Base


class Company(Base):
    """Corporate entity being appraised."""
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    cin = Column(String(21), nullable=True)
    gstin = Column(String(15), nullable=True)
    sector = Column(String(100), nullable=True)
    pan_number = Column(String(10), nullable=True)
    annual_turnover_cr = Column(Float, nullable=True)
    employee_count = Column(Integer, nullable=True)
    year_of_incorporation = Column(Integer, nullable=True)
    registered_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="company")
    risk_scores = relationship("RiskScore", back_populates="company")
    cam_outputs = relationship("CamOutput", back_populates="company")
    qualitative_inputs = relationship("QualitativeInput", back_populates="company")
    chat_history = relationship("ChatHistory", back_populates="company")
    analysis_runs = relationship("AnalysisRun", back_populates="company")
    research_findings = relationship("ResearchFindingRecord", back_populates="company")
    due_diligence_entries = relationship("DueDiligenceRecord", back_populates="company")
    loan_applications = relationship("LoanApplication", back_populates="company", lazy="selectin")


class Document(Base):
    """Uploaded and processed document (PDF, GST filing, etc.)."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    file_path = Column(Text, nullable=False)
    doc_type = Column(String(50), nullable=True)
    extraction_method = Column(String(20), nullable=True)
    raw_text = Column(Text, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="documents")


class RiskScore(Base):
    """Risk scoring output for a company appraisal."""
    __tablename__ = "risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    rule_based_score = Column(Float, nullable=True)
    ml_stress_probability = Column(Float, nullable=True)
    final_risk_score = Column(Float, nullable=True)
    risk_category = Column(String(20), nullable=True)
    rule_violations = Column(JSONB, nullable=True)
    risk_strengths = Column(JSONB, nullable=True)
    shap_values = Column(JSONB, nullable=True)
    decision = Column(String(30), nullable=True)
    recommended_limit_crore = Column(Float, nullable=True)
    interest_premium_bps = Column(Integer, nullable=True)
    decision_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="risk_scores")


class CamOutput(Base):
    """Generated Credit Appraisal Memo output."""
    __tablename__ = "cam_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    cam_text = Column(Text, nullable=True)
    docx_path = Column(Text, nullable=True)
    pdf_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="cam_outputs")


class QualitativeInput(Base):
    """Credit Officer's qualitative notes and site visit observations."""
    __tablename__ = "qualitative_inputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    notes = Column(Text, nullable=True)
    factory_capacity_pct = Column(Float, nullable=True)
    management_assessment = Column(Text, nullable=True)
    submitted_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="qualitative_inputs")


class ChatHistory(Base):
    """Chat conversation history for RAG-powered Q&A."""
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    message = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    sources = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="chat_history")


class AnalysisRun(Base):
    """Tracks one full analysis execution and its materialized outputs."""

    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    current_step = Column(String(100), nullable=True)
    progress_pct = Column(Float, nullable=False, default=0.0)
    audit_log = Column(JSONB, nullable=False, default=list)
    result_payload = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="analysis_runs")


class ResearchFindingRecord(Base):
    """Stores normalized web research findings for a company."""

    __tablename__ = "research_finding_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    finding_type = Column(String(40), nullable=False)
    severity = Column(String(20), nullable=False)
    source_name = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    raw_snippet = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.7)
    date_of_finding = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="research_findings")


class DueDiligenceRecord(Base):
    """Stores credit officer due diligence inputs and parsed AI insights."""

    __tablename__ = "due_diligence_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    payload = Column(JSONB, nullable=False)
    llm_insight = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="due_diligence_entries")


class LoanApplication(Base):
    """Loan application details for entity onboarding."""
    __tablename__ = "loan_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    loan_type = Column(String(50), nullable=False)
    loan_amount_cr = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    proposed_rate_pct = Column(Float, nullable=True)
    repayment_mode = Column(String(30), nullable=True)
    purpose = Column(Text, nullable=True)
    collateral_type = Column(Text, nullable=True)
    collateral_value_cr = Column(Float, nullable=True)
    status = Column(String(20), default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="loan_applications")


class DocumentClassification(Base):
    """Auto-classification + HITL review of uploaded documents."""
    __tablename__ = "document_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    auto_type = Column(String(50), nullable=False)
    auto_confidence = Column(Float, nullable=False, default=0.5)
    auto_reasoning = Column(Text, nullable=True)
    human_approved = Column(Boolean, nullable=True)
    human_type_override = Column(String(50), nullable=True)
    human_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    custom_schema = Column(JSONB, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SwotAnalysis(Base):
    """SWOT analysis generated during pipeline execution."""
    __tablename__ = "swot_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=True)
    strengths = Column(JSONB, nullable=True)
    weaknesses = Column(JSONB, nullable=True)
    opportunities = Column(JSONB, nullable=True)
    threats = Column(JSONB, nullable=True)
    sector_outlook = Column(Text, nullable=True)
    macro_signals = Column(JSONB, nullable=True)
    investment_thesis = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
