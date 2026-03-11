"""
Generates CAM research narrative from structured findings.
"""

from __future__ import annotations

from backend.core.llm.llm_client import llm_call
from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)

NARRATIVE_PROMPT = """You are a senior credit analyst at an Indian bank.
Write "Section 6 — Research Findings" for a Credit Appraisal Memo.

Company: {company_name}
Research verdict: {verdict}
Score impact: {score_impact}

Findings:
{findings}

Requirements:
- Formal bank-grade prose.
- Mention critical negatives first.
- Mention sector context and positives, if any.
- Explain risk implication for sanction decision.
- 300-450 words.
"""


class ResearchToDelta:
    """
    LLM-based narrative synthesis with deterministic fallback.
    """

    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except Exception:
                logger.warning("research_to_delta.anthropic_unavailable")

    def generate_cam_section(self, research_summary: dict) -> str:
        findings = research_summary.get("all_findings", [])[:20]
        findings_text = "\n".join(
            [
                f"[{f.get('severity')}] {f.get('headline', f.get('source_name', 'Finding'))}: "
                f"{f.get('summary', '')} (Source: {f.get('source_name', 'Unknown')})"
                for f in findings
            ]
        )
        prompt = NARRATIVE_PROMPT.format(
            company_name=research_summary.get("company_name", "Unknown Company"),
            verdict=research_summary.get("research_verdict", "LOW_RISK"),
            score_impact=research_summary.get("total_score_impact", 0),
            findings=findings_text or "No material findings identified.",
        )

        if self._client is not None:
            try:
                response = self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text.strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning("research_to_delta.llm_failed", error=str(exc))

        try:
            response = llm_call(
                prompt,
                task="cam_research_narrative",
                max_tokens=1200,
            )
            if response.text and response.text.strip():
                return response.text.strip()
        except Exception as exc:
            logger.warning("research_to_delta.unified_llm_failed", error=str(exc))

        return self._fallback(research_summary)

    @staticmethod
    def _fallback(research_summary: dict) -> str:
        findings = research_summary.get("all_findings", [])
        critical = [f for f in findings if f.get("severity") in {"CRITICAL", "HIGH"}]
        positives = [f for f in findings if float(f.get("score_impact", 0)) > 0]
        verdict = research_summary.get("research_verdict", "LOW_RISK")
        company_name = research_summary.get("company_name", "the borrower")

        intro = (
            f"Secondary research for {company_name} indicates a {verdict} profile based on "
            f"{len(findings)} sourced findings across litigation, regulatory, promoter, and sector intelligence."
        )
        neg = (
            "Critical and high-severity signals were identified, requiring enhanced monitoring and tighter covenants."
            if critical
            else "No critical enforcement or insolvency signal was identified in the reviewed source set."
        )
        pos = (
            f"Positive external intelligence was also observed in {len(positives)} source items, "
            "indicating partially offsetting comfort factors."
            if positives
            else "No strong positive external signal was observed to offset identified concerns."
        )
        close = (
            "Overall, research output should be treated as a risk-adjusting input to sanction terms, "
            "including pricing premium, covenant package, and post-disbursement review cadence."
        )
        return " ".join([intro, neg, pos, close])
