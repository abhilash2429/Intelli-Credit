"""
Generates CAM research narrative from structured findings.
"""

from __future__ import annotations

from backend.core.llm.llm_client import llm_call
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
- Use concrete evidence: include at least 4 named sources and 4 specific facts.
- Avoid vague phrases like "some concerns" or "various reports indicate".
- 300-450 words.
"""


class ResearchToDelta:
    """
    Cerebras-LLM narrative synthesis with deterministic fallback.
    """

    def __init__(self) -> None:
        self._client = None

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
        top_critical = critical[:4]
        top_positive = positives[:2]

        intro = (
            f"Secondary research for {company_name} indicates a {verdict} profile based on "
            f"{len(findings)} sourced findings across litigation, regulatory, promoter, and sector intelligence."
        )
        if top_critical:
            critical_lines = []
            for item in top_critical:
                critical_lines.append(
                    f"[{item.get('severity')}] {item.get('source_name', 'Web')}: {item.get('summary', 'N/A')}"
                )
            neg = "Key adverse findings: " + " | ".join(critical_lines) + "."
        else:
            neg = "No critical enforcement, insolvency, or fraud signal was identified in the reviewed source set."

        if top_positive:
            positive_lines = []
            for item in top_positive:
                positive_lines.append(
                    f"{item.get('source_name', 'Web')}: {item.get('summary', 'N/A')}"
                )
            pos = "Offsetting comfort signals: " + " | ".join(positive_lines) + "."
        else:
            pos = "No strong external positive catalyst was identified to offset adverse intelligence."
        close = (
            "Research should be treated as an advisory overlay to credit governance: "
            "flagged items require analyst verification, covenant calibration, and tighter post-disbursement monitoring."
        )
        return " ".join([intro, neg, pos, close])
