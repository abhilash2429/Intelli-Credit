"""
Database connection module for Intelli-Credit.
Provides async SQLAlchemy engine, session factory, and startup initialization.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import settings


engine = create_async_engine(settings.database_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all database tables on application startup."""
    async with engine.begin() as conn:
        from backend.models.db_models import (
            Company,
            Document,
            RiskScore,
            CamOutput,
            QualitativeInput,
            ChatHistory,
            AnalysisRun,
            ResearchFindingRecord,
            DueDiligenceRecord,
            LoanApplication,
            DocumentClassification,
            SwotAnalysis,
        )
        await conn.run_sync(Base.metadata.create_all)
