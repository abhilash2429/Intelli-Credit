"""
Sarvam Vision API wrapper for Indic-language OCR.
Handles scanned PDFs and documents in 22 Indian languages.
API: https://docs.sarvam.ai/api-reference-docs/endpoints/optical-character-recognition
"""

import base64
import io
import logging
from typing import Dict

import httpx
import pdfplumber

from backend.config import settings

logger = logging.getLogger(__name__)

SARVAM_OCR_URL = "https://api.sarvam.ai/v1/ocr"


def pdf_page_to_base64(pdf_path: str, page_number: int) -> str:
    """
    Convert a single PDF page to a base64-encoded PNG string.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number to convert.

    Returns:
        Base64-encoded PNG image string.

    Raises:
        ValueError: If page conversion fails.
    """
    from pdf2image import convert_from_path

    images = convert_from_path(
        pdf_path, first_page=page_number, last_page=page_number, dpi=200
    )
    if not images:
        raise ValueError(f"Could not convert page {page_number} of {pdf_path}")

    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_with_sarvam(pdf_path: str, page_number: int) -> Dict:
    """
    Send a single PDF page to Sarvam Vision API for OCR extraction.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.

    Returns:
        Dict with keys: text, language, confidence, blocks.
    """
    image_b64 = pdf_page_to_base64(pdf_path, page_number)

    payload = {
        "image": image_b64,
        "image_format": "png",
        "extract_tables": True,
        "extract_layout": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.sarvam_api_key}",
        "Content-Type": "application/json",
    }

    response = httpx.post(SARVAM_OCR_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def extract_full_document_sarvam(pdf_path: str) -> str:
    """
    Extract text from all pages of a PDF using Sarvam Vision.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    full_text = []
    for page_num in range(1, total_pages + 1):
        try:
            result = extract_with_sarvam(pdf_path, page_num)
            full_text.append(result.get("text", ""))
        except Exception as e:
            logger.warning(f"[Sarvam] Page {page_num} failed: {e}")
            full_text.append("")

    return "\n\n".join(full_text)
