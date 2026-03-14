"""
PDF CAM document generator using ReportLab.
Produces a professional Credit Appraisal Memo in PDF format
with color-coded risk flags and formatted tables.
"""

import os
import logging
from datetime import datetime
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from backend.core.formatting import format_currency_cr, format_percentage, format_ratio

logger = logging.getLogger(__name__)


def generate_pdf(state: dict) -> str:
    """
    Generate a professional PDF for the Credit Appraisal Memo.

    Args:
        state: Complete pipeline state dict.

    Returns:
        Path to the generated .pdf file.
    """
    f = state.get("extracted_financials", {})
    company_name = state.get("company_name", "Unknown Company")
    company_id = state.get("company_id", "unknown")

    output_dir = os.path.join("uploads", company_id)
    os.makedirs(output_dir, exist_ok=True)
    safe_name = company_name.replace(" ", "_").replace("/", "_")[:50]
    output_path = os.path.join(output_dir, f"CAM_{safe_name}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name="CamTitle",
        parent=styles["Title"],
        fontSize=24,
        spaceAfter=12,
        alignment=1,
    ))
    styles.add(ParagraphStyle(
        name="CamSubtitle",
        parent=styles["Normal"],
        fontSize=16,
        spaceAfter=8,
        alignment=1,
        textColor=colors.darkblue,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=6,
        spaceBefore=12,
        textColor=colors.darkblue,
    ))
    styles.add(ParagraphStyle(
        name="CriticalFlag",
        parent=styles["Normal"],
        textColor=colors.red,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="HighFlag",
        parent=styles["Normal"],
        textColor=colors.orange,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    ))

    story = []

    # ── Title Page ────────────────────────────────────────────────────
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("CREDIT APPRAISAL MEMO", styles["CamTitle"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(company_name, styles["CamSubtitle"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        f"Date: {datetime.now().strftime('%d %B %Y')} | CIN: {f.get('cin', 'N/A')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.3 * inch))

    # Decision badge
    decision = state.get("decision", "PENDING")
    decision_color = colors.green if decision == "APPROVE" else (
        colors.red if decision == "REJECT" else colors.orange
    )
    story.append(Paragraph(
        f'<font color="{decision_color}" size="18"><b>{decision}</b></font>',
        ParagraphStyle(name="DecisionBadge", parent=styles["Normal"], alignment=1),
    ))

    story.append(PageBreak())

    # ── CAM Content ──────────────────────────────────────────────────
    cam_text = state.get("cam_text", "No CAM text generated.")
    for line in cam_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue

        if line.startswith("#") or (len(line) > 2 and line[0].isdigit() and line[1] == "."):
            clean = line.lstrip("#").lstrip("0123456789.").strip()
            story.append(Paragraph(clean, styles["SectionHeading"]))
        elif "[CRITICAL]" in line:
            story.append(Paragraph(line, styles["CriticalFlag"]))
        elif "[HIGH]" in line:
            story.append(Paragraph(line, styles["HighFlag"]))
        else:
            story.append(Paragraph(line, styles["Normal"]))

    # ── Financial Table ──────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Financial Summary", styles["SectionHeading"]))

    table_data = [
        ["Metric", "Value"],
        ["Revenue", format_currency_cr(f.get("revenue_crore"))],
        ["EBITDA Margin", format_percentage(f.get("ebitda_margin_pct"))],
        ["PAT", format_currency_cr(f.get("pat_crore"))],
        ["DSCR", format_ratio(f.get("dscr"))],
        ["Current Ratio", format_ratio(f.get("current_ratio"))],
        ["Net Worth", format_currency_cr(f.get("net_worth_crore"))],
        ["Total Debt", format_currency_cr(f.get("total_debt_crore"))],
        ["Risk Score", f"{state.get('final_risk_score', 'N/A')}/100"],
        ["Risk Category", str(state.get("risk_category", "N/A"))],
        ["Recommended Limit", format_currency_cr(state.get("recommended_loan_limit_crore"))],
    ]

    table = Table(table_data, colWidths=[3 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
    ]))
    story.append(table)

    # ── Footer ────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        f"Generated by Intelli-Credit AI | {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
        styles["Footer"],
    ))

    # Build PDF
    doc.build(story)
    logger.info(f"[PDF] Saved to {output_path}")
    return output_path
