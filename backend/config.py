"""
Configuration module for Intelli-Credit backend.
Loads all environment variables using pydantic BaseSettings.
Exports a single `settings` singleton used across the application.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/intellicredit"
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_documents: str = "document_chunks"
    qdrant_collection_research: str = "research_chunks"

    # LLM API Keys
    cerebras_api_key: str = ""   # from CEREBRAS_API_KEY env var
    github_token: str = ""       # from GITHUB_TOKEN env var — PAT with models:read scope
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    firecrawl_api_key: str = ""
    huggingface_api_token: str = ""
    huggingface_base_url: str = "https://router.huggingface.co/v1"
    hf_free_llm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_provider: str = "huggingface"   # huggingface | mock | openai | anthropic
    grok_api_key: str = ""
    sarvam_api_key: str = ""
    qwen_vl_api_key: str = ""
    qwen_vl_base_url: str = "https://router.huggingface.co/v1"
    qwen_vl_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    qwen_vl_provider: str = "huggingface"
    qwen_vl_timeout_sec: int = 90

    # Web Research
    serper_api_key: str = ""
    tavily_api_key: str = ""
    max_firecrawl_pages_per_search: int = 10
    max_research_sources_per_company: int = 50
    research_depth: str = "deep"  # shallow | medium | deep

    # Databricks / Delta Lake
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_cluster_id: str = ""
    databricks_catalog: str = "intelli_credit"
    databricks_schema: str = "credit_appraisal"
    spark_local_mode: bool = True
    delta_lake_path: str = "./delta_lake"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "intelli-credit-secret"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_upload_mime_types: str = (
        "application/pdf,text/csv,application/json,application/xml,"
        "text/xml,application/vnd.ms-excel,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "image/jpeg,image/jpg,image/png"
    )
    allowed_upload_extensions: str = ".pdf,.csv,.json,.xml,.xls,.xlsx,.docx,.jpg,.jpeg,.png"
    research_mode: str = "mock"  # mock | cached | live  (default mock for safe dev)
    cache_dir: str = "./cache"
    cam_output_dir: str = "./outputs/cam"
    report_bank_name: str = "Intelli-Credit Demo Bank"
    base_interest_rate: float = 8.5

    # Pipeline & background processing
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    prefect_api_url: Optional[str] = None

    # Frontend
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def allowed_mime_types(self) -> List[str]:
        return [v.strip() for v in self.allowed_upload_mime_types.split(",") if v.strip()]

    @property
    def allowed_extensions(self) -> List[str]:
        return [v.strip().lower() for v in self.allowed_upload_extensions.split(",") if v.strip()]


settings = Settings()
