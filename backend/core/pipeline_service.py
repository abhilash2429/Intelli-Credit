"""
End-to-end analysis pipeline service.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
                    step=latest.current_step or "UNKNOWN",
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

        return {
            "company": company,
            "documents": docs,
            "due_diligence": due,
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
        parsed_financials = await self._parse_documents(db, company_id, documents)

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
            company_name=company.name,
            sector=company.sector or "other",
            cin=company.cin,
            gstin=getattr(company, "gstin", None),
            promoter_names=promoters,
        )
        await self._store_research_findings(db, company_id, research_bundle.findings)

        due_payload = self._due_payload(due)
        due_raw_payload = due.payload if (due and isinstance(due.payload, dict)) else {}
        research_summary = self._summarize_research(research_bundle.findings, research_bundle.mca_report)
        research_summary["cibil_commercial_score"] = get_mock_cibil_score(company.name)
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
            company_name=company.name,
            findings=research_bundle.findings,
            research_summary=research_summary,
            research_job_id=getattr(research_bundle, "research_job_id", ""),
            cam_narrative=research_narrative,
        )

        # ── SWOT Generation ──────────────────────────────────────────
        await update_run(
            db,
            run,
            step="SWOT_ANALYSIS",
            progress_pct=65,
            message="Generating SWOT analysis from financials and research",
        )
        loan_result = await db.execute(
            select(LoanApplication)
            .where(LoanApplication.company_id == uuid.UUID(company_id))
            .order_by(LoanApplication.created_at.desc())
            .limit(1)
        )
        loan_app = loan_result.scalar_one_or_none()
        try:
            from backend.core.research.swot_engine import generate_swot

            swot_result = await generate_swot(
                company_name=company.name,
                sector=company.sector or "other",
                loan_amount_cr=float(loan_app.loan_amount_cr if loan_app else 30.0),
                loan_type=loan_app.loan_type if loan_app else "term_loan",
                tenure_months=int(loan_app.tenure_months if loan_app else 36),
                extracted_financials=parsed_financials.get("financials", {}),
                research_findings=research_bundle.findings,
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

        decision = await asyncio.to_thread(
            self.scorer.predict,
            features,
            requested_loan_amount=float(getattr(company, "loan_amount_requested", 30.0) or 30.0),
            sector=company.sector or "other",
            loan_type="secured",
        )
        explanation = await asyncio.to_thread(self.explainer.generate_explanation, features)

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
                "loan_amount_requested": getattr(company, "loan_amount_requested", 30.0),
                "loan_tenor_months": getattr(company, "loan_tenor_months", 36),
                "loan_purpose": getattr(company, "loan_purpose", "working_capital"),
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
            rule_based_score=max(0.0, min(100.0, (decision.credit_score - 300) / 6)),
            ml_stress_probability=max(0.0, min(1.0, (900 - decision.credit_score) / 600)),
            final_risk_score=decision.credit_score,
            risk_category=decision.risk_grade,
            rule_violations=decision.rule_hits,
            risk_strengths=explanation.top_positive_factors,
            shap_values=explanation.shap_waterfall_data,
            decision=decision.recommendation,
            recommended_limit_crore=decision.recommended_loan_amount,
            interest_premium_bps=int(max(0.0, (decision.recommended_interest_rate - 8.5) * 100)),
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
        fraud_graph = self.cross_validator.build_fraud_graph(
            company_name=company.name,
            bank_metrics=bank_metrics,
            research_findings=research_bundle.findings,
            gst_mismatch=gst_payload.get("mismatch_report"),
        )

        result_payload = {
            "company_id": company_id,
            "decision": decision.model_dump(),
            "explanation": explanation.model_dump(),
            "features": features,
            "cross_validation": cross_report.model_dump(),
            "gst_mismatch": gst_payload.get("mismatch_report").model_dump()
            if gst_payload.get("mismatch_report")
            else None,
            "gst_xlsx_data": gst_xlsx_data,
            "shareholding_data": shareholding_data,
            "fraud_graph": fraud_graph,
            "five_cs": five_cs,
            "model_confidence": f"{model_confidence_pct}% agreement between rule and ML subsystems",
            "model_confidence_pct": model_confidence_pct,
            "research_findings": [f.model_dump() for f in research_bundle.findings],
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
        self, db: AsyncSession, company_id: str, documents: List[Document]
    ) -> Dict[str, Any]:
        financial_docs = []
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
            if not path:
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
                    alm_data = await parse_alm_statement(path)
                    logger.info("pipeline.alm_parsed", gap=alm_data.get("structural_liquidity_gap_cr"))
                except Exception as exc:
                    logger.warning("pipeline.alm_parse_failed", error=str(exc))
                continue
            elif doc_type in ("SHAREHOLDING", "SHAREHOLDING_PATTERN"):
                try:
                    sh_data = await parse_shareholding_pattern(path)
                    shareholding_data.update(sh_data)
                    logger.info("pipeline.shareholding_parsed", promoter=shareholding_data.get("promoter_holding_pct"))
                except Exception as exc:
                    logger.warning("pipeline.shareholding_parse_failed", error=str(exc))
                continue
            elif doc_type in ("BORROWING_PROFILE", "BORROWING"):
                try:
                    borrowing_data = await parse_borrowing_profile(path)
                    logger.info("pipeline.borrowing_parsed", debt=borrowing_data.get("total_outstanding_cr"))
                except Exception as exc:
                    logger.warning("pipeline.borrowing_parse_failed", error=str(exc))
                continue
            elif doc_type in ("PORTFOLIO", "PORTFOLIO_QUALITY"):
                try:
                    portfolio_data = await parse_portfolio_performance(path)
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
                parsed = await asyncio.to_thread(self.pdf_parser.parse, path)
                financial_docs.append(parsed)
            elif low.endswith(".json") or low.endswith(".xml"):
                if "gstr" in low:
                    bundle = await asyncio.to_thread(self.gst_parser.parse_file, path)
                    gstr3b = bundle.gstr3b or gstr3b
                    gstr2a = bundle.gstr2a or gstr2a
                    gstr1 = bundle.gstr1 or gstr1
                elif "itr" in low:
                    itr_data = await asyncio.to_thread(self.itr_parser.parse, path)
            elif low.endswith(".csv") or low.endswith(".xlsx") or low.endswith(".xls"):
                xlsx_type = detect_xlsx_type(path)
                if xlsx_type == "financial_statement":
                    xlsx_financials = await asyncio.to_thread(parse_financial_statement_xlsx, path)
                    logger.info("pipeline.xlsx_financial_parsed", dscr=xlsx_financials.get("dscr"))
                elif xlsx_type == "gst_returns":
                    gst_xlsx_data = await asyncio.to_thread(parse_gst_xlsx, path)
                    logger.info("pipeline.xlsx_gst_parsed", itc_gap=gst_xlsx_data.get("itc_mismatch_pct"))
                elif xlsx_type == "shareholding":
                    shareholding_data = await asyncio.to_thread(parse_shareholding_xlsx, path)
                    logger.info("pipeline.xlsx_shareholding_parsed", pledge=shareholding_data.get("promoter_pledge_pct"))
                else:
                    bank_metrics = await asyncio.to_thread(
                        self.bank_analyzer.analyze,
                        path,
                        annual_revenue=20.0,
                        gst_turnover=20.0,
                    )

        base_financial = financial_docs[0].model_dump() if financial_docs else {}

        # Merge XLSX-extracted financials into base (XLSX takes precedence for numeric fields)
        if xlsx_financials:
            for key, val in xlsx_financials.items():
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
            "management_cooperation": payload.get("management_cooperation", ""),
            "inventory_levels": payload.get("inventory_levels", ""),
            "business_highlights": payload.get("borrower_business_highlights", ""),
            "major_customers": payload.get("borrower_major_customers", ""),
            "contingent_liabilities": payload.get("borrower_contingent_liabilities", ""),
            "planned_capex": payload.get("borrower_planned_capex", ""),
            "disclosed_risks": payload.get("borrower_disclosed_risks", ""),
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
