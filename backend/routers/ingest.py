"""
Ingest router — handles PDF upload and document storage.
POST /ingest: Saves uploaded PDFs to uploads/<company_id>/, creates DB records.
"""

import os
import uuid
import logging
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.config import settings
from backend.models.db_models import Company, Document

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest")
async def ingest_documents(
    company_name: str = Form(...),
    sector: str = Form(default="manufacturing"),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and save PDFs for a company. Creates company record if new.

    Args:
        company_name: Name of the company.
        sector: Industry sector.
        files: List of PDF files to upload.
        db: Database session.

    Returns:
        Dict with company_id and list of saved file paths.
    """
    # Create company record
    company_id = uuid.uuid4()
    company = Company(
        id=company_id,
        name=company_name,
        sector=sector,
    )
    db.add(company)

    # Save files
    upload_dir = os.path.join(settings.upload_dir, company_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_paths = []
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Create document record
        doc = Document(
            id=uuid.uuid4(),
            company_id=company_id,
            file_path=file_path,
        )
        db.add(doc)
        file_paths.append(file_path)

    await db.commit()

    logger.info(f"[Ingest] Saved {len(files)} files for {company_name} ({company_id})")

    return {
        "company_id": str(company_id),
        "company_name": company_name,
        "file_paths": file_paths,
        "file_count": len(file_paths),
    }
