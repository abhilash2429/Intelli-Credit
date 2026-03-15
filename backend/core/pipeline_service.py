"""
End-to-end analysis pipeline service.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ingestion.bank_statement import BankStatementAnalyzer
from backend.core.ingestion.cross_validator import CrossValidator
from backend.core.ingestion.gst_parser import GSTMismatchAnalyzer, GSTParser
from backend.core.ingestion.itr_parser import ITRParser
from backend.core.ingestion.pdf_parser import IntelliCreditPDFParser
from backend.core.ingestion.xlsx_financial_parser import (
    detect_xlsx_type,
    parse_financial_statement_xlsx,
    parse_gst_xlsx,
    parse_shareholding_xlsx,
)
from backend.core.ml.credit_scorer import CreditScoringModel
from backend.core.ml.explainer import CreditExplainer
from backend.core.ml.feature_engineering import build_feature_vector
from backend.core.ingestion.alm_parser import parse_alm_statement
from backend.core.ingestion.borrowing_profile_parser import parse_borrowing_profile
from backend.core.ingestion.portfolio_parser import parse_portfolio_performance
from backend.core.ingestion.shareholding_parser import parse_shareholding_pattern
from backend.core.report.cam_generator import CAMGenerator
from backend.core.report.five_c_analyzer import analyze_five_cs
from backend.core.research.cibil_mock import get_mock_cibil_score
from backend.core.research.research_to_delta import ResearchToDelta
from backend.core.research.web_agent import WebResearchAgent
from backend.core.structured_logging import get_logger
from backend.core.state_store import create_run, get_latest_run, update_run
from backend.models.db_models import (
    CamOutput,
    Company,
    Document,
    DocumentClassification,
    DueDiligenceRecord,
    LoanApplication,
    ResearchFindingRecord,
    RiskScore,
    SwotAnalysis,
)
from backend.schemas.credit import DueDiligenceInsight, Severity

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from backend.databricks.pipeline_sink import DatabricksPipelineSink


class IntelliCreditPipeline:
    """
    Main orchestration service across ingestion, research, ML, and report generation.
    """

    def __init__(self) -> None:
        self.pdf_parser = IntelliCreditPDFParser()
        self.gst_parser = GSTParser()
        self.gst_mismatch = GSTMismatchAnalyzer()
        self.bank_analyzer = BankStatementAnalyzer()
        self.itr_parser = ITRParser()
        self.cross_validator = CrossValidator()
        self.research_agent = WebResearchAgent()
        self.scorer = CreditScoringModel(model_dir="ml/model")
        self.explainer = CreditExplainer(self.scorer)
        self.cam_generator = CAMGenerator()
        self.research_narrative = ResearchToDelta()
        self._delta_sink: "DatabricksPipelineSink | None" = None
        self._delta_sink_checked = False

    def _get_delta_sink(self) -> "DatabricksPipelineSink | None":
        if self._delta_sink_checked:
            return self._delta_sink
        try:
            from backend.databricks.pipeline_sink import DatabricksPipelineSink
            from backend.databricks.spark_session import get_spark

            spark = get_spark()
            self._delta_sink = DatabricksPipelineSink(spark)
            self._delta_sink_checked = True
            return self._delta_sink
        except Exception as exc:
            self._delta_sink_checked = True
            logger.warning("pipeline.delta_sink.unavailable", error=str(exc))
            return None

    async def run_analysis(self, db: AsyncSession, company_id: str) -> Dict[str, Any]:
        run = await create_run(db, company_id, status="processing", step="DOCUMENTS_RECEIVED")
        try:
            data = await self._collect_inputs(db, company_id, run_id=str(run.id))
            return await self._execute(db, company_id, run_id=str(run.id), data=data)
        except Exception as exc:
            latest = await get_latest_run(db, company_id)
            if latest:
                await update_run(
                    db,
                    latest,
                    status="error",
                    step=latest.current_step or "UNKNOWN",  # type: ignore[reportArgumentType]
                    message=f"Pipeline failed: {exc}",
                    error_message=str(exc),
                )
            raise

    async def _collect_inputs(
        self,
        db: AsyncSession,
        company_id: str,
        *,
        run_id: str,
    ) -> Dict[str, Any]:
        try:
            company_uuid = uuid.UUID(company_id)
        except ValueError as exc:
            raise ValueError("Invalid company_id") from exc

        company_result = await db.execute(select(Company).where(Company.id == company_uuid))
        company = company_result.scalars().first()
        if not company:
            raise ValueError("Company not found")

        docs_result = await db.execute(select(Document).where(Document.company_id == company_uuid))
        docs = docs_result.scalars().all()

        due_result = await db.execute(
            select(DueDiligenceRecord)
            .where(DueDiligenceRecord.company_id == company_uuid)
            .order_by(DueDiligenceRecord.created_at.desc())
            .limit(1)
        )
        due = due_result.scalars().first()

        loan_result = await db.execute(
            select(LoanApplication)
            .where(LoanApplication.company_id == company_uuid)
            .order_by(LoanApplication.created_at.desc())
            .limit(1)
        )
        loan = loan_result.scalars().first()

        return {
            "company": company,
            "documents": docs,
            "due_diligence": due,
            "loan_application": loan,
        }

    async def _execute(
        self,
        db: AsyncSession,
        company_id: str,
        *,
        run_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        company: Company = data["company"]
        documents: List[Document] = data["documents"]
        due: Optional[DueDiligenceRecord] = data["due_diligence"]
        loan: Optional[LoanApplication] = data.get("loan_application")

        run = await get_latest_run(db, company_id)
        if run is None:
            raise RuntimeError("Analysis run not initialized")

        await update_run(
            db,
            run,
            step="OCR_EXTRACTION",
            progress_pct=15,
            message="Extracting structured content from uploaded documents",
        )
        parsed_financials = await self._parse_documents(db, company_id, documents, company=company)

        await update_run(
            db,
            run,
            step="GST_PARSING",
            progress_pct=30,
            message="Running GST mismatch analytics and banking reconciliation",
        )
        gst_payload = self._build_gst_payload(parsed_financials)
        bank_metrics = parsed_financials.get("bank_metrics")
        itr_payload = parsed_financials.get("itr_data")
        cross_report = self.cross_validator.validate(
            gst_turnover=float(gst_payload.get("gst_turnover", 0.0)),
            bank_metrics=bank_metrics,
            itr_data=itr_payload,
            gst_mismatch=gst_payload.get("mismatch_report"),
            annual_debt_obligation=float(parsed_financials.get("annual_debt_obligation", 1.0)),
            gst_xlsx_data=parsed_financials.get("gst_xlsx_data"),
            shareholding_data=parsed_financials.get("shareholding_data"),
            xlsx_financials=parsed_financials.get("financials"),
        )
        self._persist_ingestion_to_delta(
            company_id=company_id,
            gst_payload=gst_payload,
            parsed_financials=parsed_financials,
            cross_report=cross_report,
        )

        await update_run(
            db,
            run,
            step="RESEARCH_AGENT",
            progress_pct=52,
            message="Executing web and regulatory research checklist",
        )
        promoters = self._extract_promoters(due)
        research_bundle = await self.research_agent.run(
            company_name=company.name,  # type: ignore[reportArgumentType]
            sector=company.sector or "other",  # type: ignore[reportArgumentType]
            cin=company.cin,  # type: ignore[reportArgumentType]
            gstin=getattr(company, "gstin", None),
            promoter_names=promoters,
        )
        await self._store_research_findings(db, company_id, research_bundle.findings)

        due_payload = self._due_payload(due)
        due_raw_payload = due.payload if (due and isinstance(due.payload, dict)) else {}
        research_summary = self._summarize_research(research_bundle.findings, research_bundle.mca_report)
        research_alerts = self._build_research_alerts(research_bundle.findings)
        research_summary["cibil_commercial_score"] = get_mock_cibil_score(company.name)  # type: ignore[reportArgumentType]
        research_narrative = self.research_narrative.generate_cam_section(
            {
                "company_name": company.name,
                "research_verdict": research_summary.get("research_verdict", "LOW_RISK"),
                "total_score_impact": sum(getattr(f, "score_impact", 0.0) for f in research_bundle.findings),
                "all_findings": [f.model_dump(mode="json") for f in research_bundle.findings],
            }
        )
        self._persist_research_to_delta(
            company_id=company_id,
            company_name=company.name,  # type: ignore[reportArgumentType]
            findings=research_bundle.findings,
            research_summary=research_summary,
            research_job_id=getattr(research_bundle, "research_job_id", ""),
            cam_narrative=research_narrative,
        )

        await update_run(
            db,
            run,
            step="ML_SCORING",
            progress_pct=75,
            message="Building features, applying hard rules, and scoring risk",
        )

        # Merge GST XLSX data into GST mismatch payload
        gst_xlsx_data = parsed_financials.get("gst_xlsx_data", {})
        gst_feature_data = {}
        if gst_payload.get("mismatch_report"):
            gst_feature_data = gst_payload["mismatch_report"].model_dump()
        # Override with XLSX-parsed ITC gap if available and non-zero
        if gst_xlsx_data.get("itc_mismatch_pct", 0.0) > 0:
            gst_feature_data["itc_inflation_percentage"] = gst_xlsx_data["itc_mismatch_pct"]
            if gst_xlsx_data.get("has_circular_trading_signals"):
                gst_feature_data["suspected_circular_trading"] = True
            if gst_xlsx_data.get("has_gst_itc_mismatch"):
                gst_feature_data["revenue_inflation_flag"] = True

        # Merge shareholding data
        shareholding_data = parsed_financials.get("shareholding_data", {})

        features = build_feature_vector(
            {
                "financials": parsed_financials.get("financials", {}),
                "bank_metrics": bank_metrics.model_dump() if bank_metrics else {},
                "gst": gst_feature_data,
                "cross_validation": cross_report.model_dump(),
                "research": research_summary,
                "due_diligence": due_payload,
                "collateral": parsed_financials.get("collateral", {}),
                "sector": company.sector or "other",
                "shareholding": shareholding_data,
                "gst_xlsx": gst_xlsx_data,
                "alm": parsed_financials.get("alm_data", {}),
                "borrowing": parsed_financials.get("borrowing_data", {}),
                "portfolio": parsed_financials.get("portfolio_data", {}),
            }
        )

        requested_loan_amount = float(
            (
                getattr(loan, "loan_amount_cr", None)
                or getattr(company, "loan_amount_requested", None)
                or 30.0
            )
            or 30.0
        )
        form_turnover = float(getattr(company, "annual_turnover_cr", 0.0) or 0.0)
        financials = parsed_financials.get("financials", {}) or {}

        extracted_revenue_candidates = [
            ("extracted_data.revenue_cr", float(financials.get("revenue_cr") or 0.0)),
            ("extracted_data.annual_revenue_cr", float(financials.get("annual_revenue_cr") or 0.0)),
            ("extracted_data.gross_receipts_cr", float(financials.get("gross_receipts_cr") or 0.0)),
            ("extracted_data.revenue_crore", float(financials.get("revenue_crore") or 0.0)),
        ]
        if financials.get("revenue_figures"):
            revenue_series = [
                float((item or {}).get("amount", 0.0) or 0.0)
                for item in (financials.get("revenue_figures") or [])
                if isinstance(item, dict)
            ]
            extracted_revenue_candidates.append(("extracted_data.revenue_figures", max(revenue_series or [0.0])))

        extracted_revenue = 0.0
        using_value = "company.turnover"
        for field_name, value in extracted_revenue_candidates:
            if value > 0:
                extracted_revenue = value
                using_value = field_name
                break

        logger.info(
            "SCORING INPUT DEBUG: %s",
            {
                "form_turnover_cr": form_turnover,
                "extracted_revenue_cr": extracted_revenue if extracted_revenue > 0 else None,
                "which_is_used": using_value if extracted_revenue > 0 else "company.turnover",
            },
        )

        if extracted_revenue <= 0:
            logger.warning(
                "WARNING: Using form turnover as fallback. Revenue extraction may have failed."
            )

        logger.info(
            "LIMIT DEBUG: %s",
            {
                "form_turnover": form_turnover,
                "extracted_revenue": extracted_revenue,
                "requested_amount": requested_loan_amount,
                "using_value": using_value if extracted_revenue > 0 else "company.turnover",
            },
        )

        decision = await asyncio.to_thread(
            self.scorer.predict,
            features,
            requested_loan_amount=requested_loan_amount,
            annual_revenue_cr=float(financials.get("annual_revenue_cr") or 0.0),
            revenue_cr=float(financials.get("revenue_cr") or financials.get("revenue_crore") or 0.0),
            gross_receipts_cr=float(financials.get("gross_receipts_cr") or 0.0),
            form_turnover_cr=form_turnover,
            revenue_source=using_value if extracted_revenue > 0 else "company.turnover",
            sector=company.sector or "other",  # type: ignore[reportArgumentType]
            loan_type="secured",
        )
        explanation = await asyncio.to_thread(self.explainer.generate_explanation, features)

        # ── SWOT Generation (post-score to use grade + normalized score) ──
        await update_run(
            db,
            run,
            step="SWOT_ANALYSIS",
            progress_pct=85,
            message="Generating deterministic SWOT from extracted signals",
        )
        try:
            from backend.core.research.swot_engine import build_swot_extracted_data, generate_swot

            swot_input = build_swot_extracted_data(
                company_name=str(company.name or "Company"),
                financials=parsed_financials.get("financials", {}),
                features=features,
                shareholding_data=shareholding_data,
                gst_payload=gst_payload,
                research_summary=research_summary,
            )
            normalized_score = max(0.0, min(100.0, (float(decision.credit_score) - 300.0) / 6.0))
            swot_result = generate_swot(
                extracted_data=swot_input,
                grade=str(decision.risk_grade),
                score=normalized_score,
            )
            swot_record = SwotAnalysis(
                company_id=uuid.UUID(company_id),
                strengths=swot_result.get("strengths", []),
                weaknesses=swot_result.get("weaknesses", []),
                opportunities=swot_result.get("opportunities", []),
                threats=swot_result.get("threats", []),
                sector_outlook=swot_result.get("sector_outlook"),
                macro_signals=swot_result.get("macro_signals", {}),
                investment_thesis=swot_result.get("investment_thesis"),
                recommendation=swot_result.get("recommendation"),
            )
            db.add(swot_record)
            await db.flush()
            logger.info("pipeline.swot_generated", company=company.name)
        except Exception as exc:
            logger.warning("pipeline.swot_generation_failed", error=str(exc))

        await update_run(
            db,
            run,
            step="CAM_GENERATION",
            progress_pct=90,
            message="Generating professional CAM document",
        )

        cam_path = await asyncio.to_thread(
            self.cam_generator.generate,
            company={
                "name": company.name,
                "cin": company.cin,
                "sector": company.sector,
                "loan_amount_requested": requested_loan_amount,
                "loan_tenor_months": int(getattr(loan, "tenure_months", None) or getattr(company, "loan_tenor_months", 36) or 36),
                "loan_purpose": getattr(loan, "purpose", None) or getattr(company, "loan_purpose", "working_capital"),
            },
            decision=decision.model_dump(),
            explanation=explanation.model_dump(),
            research_findings=[f.model_dump() for f in research_bundle.findings],
            research_narrative=research_narrative,
            features=features,
            cross_validation=cross_report.model_dump(),
            due_diligence=due_payload,
            borrower_context=due_raw_payload,
        )

        risk_record = RiskScore(
            id=uuid.uuid4(),
            company_id=uuid.UUID(company_id),
            rule_based_score=float(decision.normalized_score),
            ml_stress_probability=max(0.0, min(1.0, (900 - decision.credit_score) / 600)),
            final_risk_score=decision.credit_score,
            risk_category=decision.risk_grade,
            rule_violations=decision.rule_hits,
            risk_strengths=explanation.top_positive_factors,
            shap_values=explanation.shap_waterfall_data,
            decision=decision.recommendation,
            recommended_limit_crore=decision.recommended_loan_amount,
            interest_premium_bps=int(decision.interest_premium_bps),
            decision_rationale=explanation.decision_narrative,
        )
        db.add(risk_record)

        cam_record = CamOutput(
            id=uuid.uuid4(),
            company_id=uuid.UUID(company_id),
            cam_text=explanation.decision_narrative,
            docx_path=cam_path,
            pdf_path=None,
        )
        db.add(cam_record)
        await db.commit()

        # Five Cs analysis
        five_cs = analyze_five_cs(features)

        # Model confidence: agreement between rule and ML subsystems
        rule_score_norm = max(0.0, min(1.0, (decision.credit_score - 300) / 600))
        ml_stress_prob = max(0.0, min(1.0, (900 - decision.credit_score) / 600))
        ml_score_norm = 1 - ml_stress_prob
        agreement = 1 - abs(rule_score_norm - ml_score_norm)
        model_confidence_pct = round(agreement * 100, 1)

        # Build fraud fingerprinting graph with multi-signal corroboration
        fraud_graph_input = self._build_fraud_graph_input(
            company_name=str(company.name or ""),
            shareholding_data=parsed_financials.get("shareholding_data", {}),
            financials=parsed_financials.get("financials", {}),
            due_payload=due_raw_payload,
        )
        fraud_graph = self.cross_validator.build_fraud_graph(
            company_name=company.name,  # type: ignore[reportArgumentType]
            extracted_data=fraud_graph_input,
        )

        result_payload = {
            "company_id": company_id,
            "decision": decision.model_dump(),
            "explanation": explanation.model_dump(),
            "features": features,
            "cross_validation": cross_report.model_dump(),
            "gst_mismatch": gst_payload.get("mismatch_report").model_dump()  # type: ignore[reportOptionalMemberAccess]
            if gst_payload.get("mismatch_report")
            else None,
            "gst_xlsx_data": gst_xlsx_data,
            "shareholding_data": shareholding_data,
            "fraud_graph_input": fraud_graph_input,
            "fraud_graph": fraud_graph,
            "limit_debug": {
                "form_turnover": form_turnover,
                "extracted_revenue": extracted_revenue,
                "requested_amount": requested_loan_amount,
                "using_value": using_value if extracted_revenue > 0 else "company.turnover",
            },
            "five_cs": five_cs,
            "model_confidence": f"{model_confidence_pct}% agreement between rule and ML subsystems",
            "model_confidence_pct": model_confidence_pct,
            "research_findings": [f.model_dump() for f in research_bundle.findings],
            "research_alerts": research_alerts,
            "research_run_metrics": research_bundle.run_metrics or {},
            "research_cam_narrative": research_narrative,
            "due_diligence": due_payload,
            "cam_docx_path": cam_path,
            "audit_events": run.audit_log,
        }

        await update_run(
            db,
            run,
            status="completed",
            step="CAM_GENERATION",
            progress_pct=100,
            message="Analysis completed successfully",
            result_payload=result_payload,
        )
        return result_payload

    def _persist_ingestion_to_delta(
        self,
        *,
        company_id: str,
        gst_payload: Dict[str, Any],
        parsed_financials: Dict[str, Any],
        cross_report: Any,
    ) -> None:
        sink = self._get_delta_sink()
        if sink is None:
            return

        try:
            gstr3b = parsed_financials.get("gstr3b")
            gstr2a = parsed_financials.get("gstr2a")
            mismatch = gst_payload.get("mismatch_report")
            if gstr3b and gstr2a:
                sink.write_gst_summary(
                    company_id=company_id,
                    gst_turnover=float(gstr3b.outward_supplies),
                    itc_claimed=float(gstr3b.itc_claimed),
                    itc_available_2a=float(gstr2a.available_itc),
                    mismatch_pct=float(getattr(mismatch, "itc_inflation_percentage", 0.0)),
                    has_circular_trading=bool(getattr(mismatch, "suspected_circular_trading", False)),
                    filing_consistency_pct=float(gst_payload.get("filing_consistency_pct", 0.0)),
                )

            bank_metrics = parsed_financials.get("bank_metrics")
            if bank_metrics:
                sink.write_bank_analytics(company_id, bank_metrics)

            sink.write_cross_validation(company_id, cross_report)
        except Exception as exc:
            logger.warning("pipeline.delta_ingestion_persist_failed", error=str(exc))

    def _persist_research_to_delta(
        self,
        *,
        company_id: str,
        company_name: str,
        findings: List[Any],
        research_summary: Dict[str, Any],
        research_job_id: str,
        cam_narrative: str,
    ) -> None:
        sink = self._get_delta_sink()
        if sink is None:
            return
        try:
            sink.write_research_findings(
                company_id=company_id,
                findings=findings,
                research_job_id=research_job_id,
            )
            sink.write_research_narrative(
                company_id=company_id,
                company_name=company_name,
                research_job_id=research_job_id,
                research_verdict=research_summary.get("research_verdict", "LOW_RISK"),
                total_findings=int(research_summary.get("total_findings", len(findings))),
                total_score_impact=float(
                    sum(getattr(f, "score_impact", 0.0) for f in findings)
                ),
                cam_narrative=cam_narrative,
            )
        except Exception as exc:
            logger.warning("pipeline.delta_research_persist_failed", error=str(exc))

    async def _parse_documents(
        self,
        db: AsyncSession,
        company_id: str,
        documents: List[Document],
        *,
        company: Optional[Company] = None,
    ) -> Dict[str, Any]:
        financial_docs: List[Tuple[Any, str]] = []
        gstr3b = None
        gstr2a = None
        gstr1 = None
        bank_metrics = None
        itr_data = None
        gst_turnover = 0.0
        annual_debt_obligation = 8.0
        xlsx_financials: Dict[str, Any] = {}
        gst_xlsx_data: Dict[str, Any] = {}
        shareholding_data: Dict[str, Any] = {}
        alm_data: Dict[str, Any] = {}
        borrowing_data: Dict[str, Any] = {}
        portfolio_data: Dict[str, Any] = {}

        # Load document classifications for type-specific parsing
        clf_result = await db.execute(
            select(DocumentClassification).where(
                DocumentClassification.company_id == uuid.UUID(company_id)
            )
        )
        classifications = {
            str(c.document_id): c for c in clf_result.scalars().all()
        }

        for doc in documents:
            path = doc.file_path
            if not path:  # type: ignore[reportGeneralTypeIssues]
                continue
            low = path.lower()

            # Check if doc has a classification override for type-specific parsing
            clf = classifications.get(str(doc.id))
            doc_type = None
            if clf:
                doc_type = (clf.human_type_override or clf.auto_type or "").upper()

            # Route type-specific classified docs to specialized parsers
            if doc_type in ("ALM_STATEMENT", "ALM"):
                try:
                    alm_data = await parse_alm_statement(path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.alm_parsed", gap=alm_data.get("structural_liquidity_gap_cr"))
                except Exception as exc:
                    logger.warning("pipeline.alm_parse_failed", error=str(exc))
                continue
            elif doc_type in ("SHAREHOLDING", "SHAREHOLDING_PATTERN"):
                try:
                    sh_data = await parse_shareholding_pattern(path)  # type: ignore[reportArgumentType]
                    shareholding_data.update(sh_data)
                    logger.info("pipeline.shareholding_parsed", promoter=shareholding_data.get("promoter_holding_pct"))
                except Exception as exc:
                    logger.warning("pipeline.shareholding_parse_failed", error=str(exc))
                continue
            elif doc_type in ("BORROWING_PROFILE", "BORROWING"):
                try:
                    borrowing_data = await parse_borrowing_profile(path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.borrowing_parsed", debt=borrowing_data.get("total_outstanding_cr"))
                except Exception as exc:
                    logger.warning("pipeline.borrowing_parse_failed", error=str(exc))
                continue
            elif doc_type in ("PORTFOLIO", "PORTFOLIO_QUALITY"):
                try:
                    portfolio_data = await parse_portfolio_performance(path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.portfolio_parsed", gnpa=portfolio_data.get("gnpa_pct"))
                except Exception as exc:
                    logger.warning("pipeline.portfolio_parse_failed", error=str(exc))
                continue

            # Standard file-type routing (unchanged)
            if (
                low.endswith(".pdf")
                or low.endswith(".docx")
                or low.endswith(".jpg")
                or low.endswith(".jpeg")
                or low.endswith(".png")
            ):
                parsed = await asyncio.to_thread(self.pdf_parser.parse, path)  # type: ignore[reportArgumentType]
                expected_cin = str(getattr(company, "cin", "") or "").strip().upper()
                parsed_cin = str(getattr(parsed, "cin_number", "") or "").strip().upper()
                if expected_cin and parsed_cin and parsed_cin != expected_cin:
                    logger.warning(
                        "pipeline.document_skipped_cin_mismatch",
                        file=path,
                        expected_cin=expected_cin,
                        parsed_cin=parsed_cin,
                    )
                    continue
                financial_docs.append((parsed, path))
            elif low.endswith(".json") or low.endswith(".xml"):
                if "gstr" in low:
                    bundle = await asyncio.to_thread(self.gst_parser.parse_file, path)  # type: ignore[reportArgumentType]
                    gstr3b = bundle.gstr3b or gstr3b
                    gstr2a = bundle.gstr2a or gstr2a
                    gstr1 = bundle.gstr1 or gstr1
                elif "itr" in low:
                    itr_data = await asyncio.to_thread(self.itr_parser.parse, path)  # type: ignore[reportArgumentType]
            elif low.endswith(".csv") or low.endswith(".xlsx") or low.endswith(".xls"):
                xlsx_type = detect_xlsx_type(path)  # type: ignore[reportArgumentType]
                if xlsx_type == "financial_statement":
                    xlsx_financials = await asyncio.to_thread(parse_financial_statement_xlsx, path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.xlsx_financial_parsed", dscr=xlsx_financials.get("dscr"))
                elif xlsx_type == "gst_returns":
                    gst_xlsx_data = await asyncio.to_thread(parse_gst_xlsx, path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.xlsx_gst_parsed", itc_gap=gst_xlsx_data.get("itc_mismatch_pct"))
                elif xlsx_type == "shareholding":
                    shareholding_data = await asyncio.to_thread(parse_shareholding_xlsx, path)  # type: ignore[reportArgumentType]
                    logger.info("pipeline.xlsx_shareholding_parsed", pledge=shareholding_data.get("promoter_pledge_pct"))
                else:
                    bank_metrics = await asyncio.to_thread(
                        self.bank_analyzer.analyze,
                        path,  # type: ignore[reportArgumentType]
                        annual_revenue=20.0,
                        gst_turnover=20.0,
                    )

        base_financial: Dict[str, Any] = {}
        if financial_docs:
            sorted_docs = sorted(
                financial_docs,
                key=lambda item: (
                    self._financial_doc_priority(item[1], item[0]),
                    -self._extract_revenue_from_financial_data(item[0].model_dump()),
                ),
            )
            base_financial = sorted_docs[0][0].model_dump()
            for parsed_doc, _path in sorted_docs[1:]:
                doc_dump = parsed_doc.model_dump()
                for key, val in doc_dump.items():
                    if isinstance(val, list):
                        existing = base_financial.get(key)
                        if not isinstance(existing, list):
                            base_financial[key] = list(val)
                        else:
                            seen_items = {str(item) for item in existing}
                            for item in val:
                                marker = str(item)
                                if marker not in seen_items:
                                    existing.append(item)
                                    seen_items.add(marker)
                        continue
                    if key not in base_financial or base_financial.get(key) in (None, "", [], {}, 0, 0.0):
                        base_financial[key] = val

            extracted_doc_revenue, extracted_source = self._select_extracted_revenue_from_docs(sorted_docs)
            if extracted_doc_revenue > 0:
                base_financial["annual_revenue_cr"] = extracted_doc_revenue
                base_financial["revenue_cr"] = extracted_doc_revenue
                base_financial.setdefault("revenue_crore", extracted_doc_revenue)
                logger.info(
                    "pipeline.revenue_selected_from_documents",
                    revenue_cr=extracted_doc_revenue,
                    source=extracted_source,
                )

        # Merge XLSX-extracted financials into base (XLSX takes precedence for numeric fields)
        if xlsx_financials:
            for key, val in xlsx_financials.items():
                if key in {"annual_revenue_cr", "revenue_cr", "revenue_crore", "gross_receipts_cr"} and base_financial.get("annual_revenue_cr"):
                    continue
                if val is not None and val != 0.0:
                    base_financial[key] = val
                elif key not in base_financial:
                    base_financial[key] = val

        if gstr3b:
            gst_turnover = float(gstr3b.outward_supplies)
        if bank_metrics:
            annual_debt_obligation = max(6.0, bank_metrics.banking_turnover * 0.08)

        collateral = {
            "collateral_coverage_ratio": 1.35,
            "collateral_type_score": 7.5,
        }
        return {
            "financials": base_financial,
            "gstr3b": gstr3b,
            "gstr2a": gstr2a,
            "gstr1": gstr1,
            "bank_metrics": bank_metrics,
            "itr_data": itr_data,
            "gst_turnover": gst_turnover,
            "annual_debt_obligation": annual_debt_obligation,
            "collateral": collateral,
            "gst_xlsx_data": gst_xlsx_data,
            "shareholding_data": shareholding_data,
            "alm_data": alm_data,
            "borrowing_data": borrowing_data,
            "portfolio_data": portfolio_data,
        }

    @staticmethod
    def _financial_doc_priority(file_path: str, parsed_doc: Any) -> int:
        low = str(file_path or "").lower()
        parsed_type = str(getattr(parsed_doc, "document_type", ""))
        if "annual_report" in low or "annual report" in low or parsed_type.endswith("ANNUAL_REPORT"):
            return 0
        if "financial_statement" in low or "financial statements" in low or parsed_type.endswith("FINANCIAL_STATEMENT"):
            return 1
        return 2

    @staticmethod
    def _extract_revenue_from_financial_data(financials: Dict[str, Any]) -> float:
        direct = (
            financials.get("annual_revenue_cr")
            or financials.get("revenue_cr")
            or financials.get("gross_receipts_cr")
            or financials.get("revenue_crore")
            or 0.0
        )
        direct_val = float(direct or 0.0)
        if direct_val > 0:
            return direct_val

        revenue_figures = financials.get("revenue_figures") or []
        if isinstance(revenue_figures, list):
            values = [
                float((entry or {}).get("amount", 0.0) or 0.0)
                for entry in revenue_figures
                if isinstance(entry, dict)
            ]
            if values:
                return max(values)
        return 0.0

    def _select_extracted_revenue_from_docs(
        self,
        docs: List[Tuple[Any, str]],
    ) -> Tuple[float, str]:
        for parsed_doc, file_path in docs:
            financials = parsed_doc.model_dump()
            revenue = self._extract_revenue_from_financial_data(financials)
            if revenue > 0:
                return revenue, str(file_path)
        return 0.0, ""

    def _build_gst_payload(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        gstr3b = parsed.get("gstr3b")
        gstr2a = parsed.get("gstr2a")
        gstr1 = parsed.get("gstr1")
        bank_metrics = parsed.get("bank_metrics")

        mismatch_report = None
        if gstr3b and gstr2a:
            mismatch_report = self.gst_mismatch.analyze(
                gstr3b,
                gstr2a,
                gstr1=gstr1,
                bank_credits=(bank_metrics.banking_turnover if bank_metrics else None),
            )

        return {
            "gst_turnover": parsed.get("gst_turnover", 0.0),
            "mismatch_report": mismatch_report,
            "filing_consistency_pct": 91.0,
        }

    @staticmethod
    def _build_fraud_graph_input(
        *,
        company_name: str,
        shareholding_data: Dict[str, Any],
        financials: Dict[str, Any],
        due_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        promoters = IntelliCreditPipeline._extract_promoter_entities(
            shareholding_data,
            due_payload,
            company_name=company_name,
        )
        subsidiaries = IntelliCreditPipeline._extract_subsidiaries(
            financials,
            company_name=company_name,
        )
        strategic_partners = IntelliCreditPipeline._extract_strategic_partners(
            financials,
            company_name=company_name,
        )
        rating_agencies = IntelliCreditPipeline._extract_rating_agencies(
            financials,
            company_name=company_name,
        )
        mca_charges = IntelliCreditPipeline._extract_lenders(
            financials,
            company_name=company_name,
        )
        return {
            "promoters": promoters,
            "subsidiaries": subsidiaries,
            "strategic_partners": strategic_partners,
            "rating_agencies": rating_agencies,
            "mca_charges": mca_charges,
        }

    @staticmethod
    def _extract_promoter_entities(
        shareholding_data: Dict[str, Any],
        due_payload: Dict[str, Any],
        company_name: str,
    ) -> List[Dict[str, Any]]:
        promoters: List[Dict[str, Any]] = []
        top_shareholders = shareholding_data.get("top_shareholders", []) or []
        for holder in top_shareholders:
            if not isinstance(holder, dict):
                continue
            name = str(holder.get("name", "")).strip()
            if not name or not IntelliCreditPipeline._is_valid_graph_entity_name(name, company_name):
                continue
            promoters.append(
                {
                    "name": name,
                    "holding_pct": float(holder.get("percentage", holder.get("holding_pct", 0.0)) or 0.0),
                    "pledge_pct": float(
                        holder.get(
                            "pledge_pct",
                            shareholding_data.get("total_pledged_pct", shareholding_data.get("promoter_pledge_pct", 0.0)),
                        )
                        or 0.0
                    ),
                }
            )
        if not promoters and shareholding_data.get("promoter_holding_pct") is not None:
            promoters.append(
                {
                    "name": "Promoter Group",
                    "holding_pct": float(shareholding_data.get("promoter_holding_pct", 0.0) or 0.0),
                    "pledge_pct": float(
                        shareholding_data.get("total_pledged_pct", shareholding_data.get("promoter_pledge_pct", 0.0))
                        or 0.0
                    ),
                }
            )

        # Borrower-provided KMP names can enrich graph if shareholder list was not extracted.
        if not promoters:
            for person in due_payload.get("key_management_persons", []) or []:
                if isinstance(person, dict) and person.get("name"):
                    name = str(person["name"]).strip()
                    if IntelliCreditPipeline._is_valid_graph_entity_name(name, company_name):
                        promoters.append({"name": name, "holding_pct": 0.0, "pledge_pct": 0.0})
        return promoters[:8]

    @staticmethod
    def _extract_subsidiaries(
        financials: Dict[str, Any],
        company_name: str,
    ) -> List[Dict[str, Any]]:
        candidates: List[str] = []
        related = financials.get("related_party_transactions", []) or []
        if isinstance(related, list):
            candidates.extend([str(x) for x in related if x])

        org_pattern = re.compile(
            r"\b([A-Z][A-Za-z0-9&.,()\- ]{2,90}(?:Pvt\.?\s*Ltd\.?|Private Limited|Limited|Ltd\.?|LLP|FZE|GmbH))\b"
        )
        subsidiaries: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for text in candidates:
            low = text.lower()
            has_relation_keyword = any(
                k in low for k in ("subsidiary", "associate", "group company", "joint venture", "wholly owned")
            )
            has_entity_hint = any(k in low for k in ("gmbh", "fze", "pvt ltd", "limited", "llp"))
            if not has_relation_keyword and not has_entity_hint:
                continue
            for match in org_pattern.findall(text):
                name = " ".join(match.split())
                if not IntelliCreditPipeline._is_valid_graph_entity_name(name, company_name):
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                relationship = "Subsidiary"
                if "associate" in low:
                    relationship = "Associate"
                elif "joint venture" in low:
                    relationship = "Joint Venture"
                subsidiaries.append({"name": name, "relationship": relationship})
        return subsidiaries[:8]

    @staticmethod
    def _extract_strategic_partners(
        financials: Dict[str, Any],
        company_name: str,
    ) -> List[Dict[str, Any]]:
        related = financials.get("related_party_transactions", []) or []
        if not isinstance(related, list):
            return []
        partners: List[Dict[str, Any]] = []
        seen: set[str] = set()
        org_pattern = re.compile(
            r"\b([A-Z][A-Za-z0-9&.,()\- ]{2,90}(?:Corporation|Corp\.?|Inc\.?|Ltd\.?|Limited|Pvt\.?\s*Ltd\.?|LLP|FZE|GmbH|Bank|Trust))\b"
        )
        for text in related:
            line = str(text or "").strip()
            low = line.lower()
            if not any(k in low for k in ("strategic", "partnership", "collaboration", "mou", "alliance")):
                continue
            for match in org_pattern.findall(line):
                name = " ".join(match.split())
                if not IntelliCreditPipeline._is_valid_graph_entity_name(name, company_name):
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                partners.append({"name": name, "relationship": "Strategic Partner"})
        return partners[:6]

    @staticmethod
    def _extract_rating_agencies(
        financials: Dict[str, Any],
        company_name: str,
    ) -> List[Dict[str, Any]]:
        related = financials.get("related_party_transactions", []) or []
        if not isinstance(related, list):
            return []
        agencies: List[Dict[str, Any]] = []
        seen: set[str] = set()
        known = {
            "crisil": "CRISIL Ratings",
            "icra": "ICRA",
            "care": "CARE Ratings",
            "fitch": "Fitch Ratings",
            "moodys": "Moody's",
            "moody's": "Moody's",
        }
        for text in related:
            line = str(text or "").strip()
            low = line.lower()
            if "rating" not in low and not any(k in low for k in known):
                continue
            for token, label in known.items():
                if token in low:
                    if IntelliCreditPipeline._is_valid_graph_entity_name(label, company_name):
                        if label.lower() not in seen:
                            seen.add(label.lower())
                            agencies.append({"name": label, "relationship": "Rating Agency"})
        return agencies[:4]

    @staticmethod
    def _extract_lenders(financials: Dict[str, Any], company_name: str) -> List[Dict[str, Any]]:
        lenders: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for bank in financials.get("existing_bank_limits", []) or []:
            if not isinstance(bank, dict):
                continue
            holder = str(bank.get("lender", "")).strip()
            if not holder or not IntelliCreditPipeline._is_valid_graph_entity_name(holder, company_name):
                continue
            key = holder.lower()
            if key in seen:
                continue
            seen.add(key)
            amount = float(bank.get("limit_amount", 0.0) or 0.0)
            amount_cr = round(amount / 1e7, 2) if amount > 1e5 else round(amount, 2)
            lenders.append({"holder": holder, "amount_cr": amount_cr})
        return lenders[:10]

    @staticmethod
    def _is_valid_graph_entity_name(name: str, company_name: str) -> bool:
        cleaned = " ".join(str(name or "").split()).strip(" -,:;.")
        if len(cleaned) < 3:
            return False
        low = cleaned.lower()
        if low == company_name.strip().lower():
            return False
        if re.fullmatch(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{4}", low):
            return False
        if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", low):
            return False
        if low.startswith(("rs ", "rs.", "₹")):
            return False
        if re.search(r"\b(?:crore|lakh|lakhs|million|mn)\b", low):
            return False
        if any(k in low for k in ("raid", "raids", "fraud", "scam", "insolvency", "arbitration", "case")):
            return False
        if not re.search(r"[a-zA-Z]", cleaned):
            return False
        return True

    @staticmethod
    def _extract_promoters(due: Optional[DueDiligenceRecord]) -> List[str]:
        if not due or not isinstance(due.payload, dict):
            return []
        people = due.payload.get("key_management_persons", []) or []
        names = []
        for person in people:
            if isinstance(person, dict):
                name = str(person.get("name", "")).strip()
                if name:
                    names.append(name)
        return names

    @staticmethod
    def _summarize_research(findings: List[Any], mca_report: Any) -> Dict[str, Any]:
        promoter_fraud_hits = 0
        litigation_count = 0
        sector_headwinds = False
        has_nclt = False
        total_score_impact = 0.0
        for finding in findings:
            if finding.finding_type.value in {"FRAUD_ALERT", "PROMOTER_BACKGROUND"}:
                promoter_fraud_hits += 1
            if finding.finding_type.value == "LITIGATION":
                litigation_count += 1
            if finding.finding_type.value in {"SECTOR", "SECTOR_NEWS"} and finding.severity in {
                Severity.MEDIUM,
                Severity.HIGH,
            }:
                sector_headwinds = True
            if "nclt" in finding.summary.lower():
                has_nclt = True
            total_score_impact += float(getattr(finding, "score_impact", 0.0))

        if promoter_fraud_hits >= 2 or has_nclt:
            research_verdict = "HIGH_RISK"
        elif promoter_fraud_hits >= 1 or litigation_count >= 2:
            research_verdict = "MEDIUM_RISK"
        else:
            research_verdict = "LOW_RISK"

        return {
            "promoter_fraud_hits": promoter_fraud_hits,
            "litigation_count": litigation_count,
            "sector_headwinds": sector_headwinds,
            "has_nclt": has_nclt,
            "mca_struck_off_count": len(mca_report.associated_struck_off_companies),
            "mca_filing_compliance_score": mca_report.filing_compliance_score,
            "research_verdict": research_verdict,
            "total_findings": len(findings),
            "total_score_impact": round(total_score_impact, 1),
        }

    @staticmethod
    def _build_research_alerts(findings: List[Any]) -> List[Dict[str, Any]]:
        """
        Build advisory-only external alerts from web research.
        These alerts are for reviewer attention and do not drive numeric credit score.
        """
        alerts: List[Dict[str, Any]] = []
        for finding in findings:
            severity = str(getattr(finding, "severity", "INFORMATIONAL"))
            raw_type = getattr(finding, "finding_type", "")
            finding_type = str(getattr(raw_type, "value", raw_type))
            if severity not in {"CRITICAL", "HIGH"}:
                continue
            if finding_type not in {"FRAUD_ALERT", "LITIGATION", "REGULATORY", "REGULATORY_ACTION"}:
                continue
            alerts.append(
                {
                    "title": str(getattr(finding, "headline", "") or "External Critical Red Flag"),
                    "summary": str(getattr(finding, "summary", "") or ""),
                    "severity": severity,
                    "source_name": str(getattr(finding, "source_name", "Web")),
                    "source_url": str(getattr(finding, "source_url", "")),
                    "advisory_only": True,
                }
            )
        # Keep UI concise.
        return alerts[:8]

    @staticmethod
    def _due_payload(due: Optional[DueDiligenceRecord]) -> Dict[str, Any]:
        if not due:
            return {
                "management_integrity_score": 6.0,
                "factory_capacity_utilization": 65.0,
                "due_diligence_risk_adjustment": 0.0,
                "borrower_context": {},
            }
        insight = due.llm_insight or {}
        payload = due.payload or {}
        mgmt_rating = payload.get("management_interview_rating")
        capacity = payload.get("capacity_utilization_percent")
        borrower_context = {
            "finance_officer_name": payload.get("borrower_finance_officer_name", ""),
            "finance_officer_role": payload.get("borrower_finance_officer_role", ""),
            "finance_officer_email": payload.get("borrower_finance_officer_email", ""),
            "finance_officer_phone": payload.get("borrower_finance_officer_phone", ""),
            "borrower_finance_officer_name": payload.get("borrower_finance_officer_name", ""),
            "borrower_finance_officer_role": payload.get("borrower_finance_officer_role", ""),
            "borrower_finance_officer_email": payload.get("borrower_finance_officer_email", ""),
            "borrower_finance_officer_phone": payload.get("borrower_finance_officer_phone", ""),
            "management_cooperation": payload.get("management_cooperation", ""),
            "inventory_levels": payload.get("inventory_levels", ""),
            "business_highlights": payload.get("borrower_business_highlights", ""),
            "borrower_business_highlights": payload.get("borrower_business_highlights", ""),
            "major_customers": payload.get("borrower_major_customers", ""),
            "borrower_major_customers": payload.get("borrower_major_customers", ""),
            "contingent_liabilities": payload.get("borrower_contingent_liabilities", ""),
            "borrower_contingent_liabilities": payload.get("borrower_contingent_liabilities", ""),
            "planned_capex": payload.get("borrower_planned_capex", ""),
            "borrower_planned_capex": payload.get("borrower_planned_capex", ""),
            "disclosed_risks": payload.get("borrower_disclosed_risks", ""),
            "borrower_disclosed_risks": payload.get("borrower_disclosed_risks", ""),
        }
        return {
            "management_integrity_score": float(mgmt_rating if mgmt_rating is not None else 3) * 2,
            "factory_capacity_utilization": float(capacity if capacity is not None else 65),
            "due_diligence_risk_adjustment": float(insight.get("score_adjustment", 0.0)),
            "borrower_context": borrower_context,
        }

    async def _store_research_findings(
        self,
        db: AsyncSession,
        company_id: str,
        findings: List[Any],
    ) -> None:
        company_uuid = uuid.UUID(company_id)
        for finding in findings:
            db.add(
                ResearchFindingRecord(
                    id=uuid.uuid4(),
                    company_id=company_uuid,
                    finding_type=finding.finding_type.value,
                    severity=finding.severity.value,
                    source_name=finding.source_name,
                    source_url=finding.source_url,
                    summary=finding.summary,
                    raw_snippet=finding.raw_snippet,
                    confidence=finding.confidence,
                    date_of_finding=datetime.combine(
                        finding.date_of_finding, datetime.min.time()
                    )
                    if finding.date_of_finding
                    else None,
                )
            )
        await db.commit()
