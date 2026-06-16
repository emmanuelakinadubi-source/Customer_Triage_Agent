from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "Customer Triage Agent API"
    app_version: str = "0.1.0"
    allowed_origins: List[str] = ["*"]
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4.1-mini"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./data/triage.db"
    MLFLOW_TRACKING_URI: str = ""
    RAG_POLICY_DOCUMENT_PATH: str = "refund_policy.txt"
    RAG_POLICY_DOCUMENT_PATHS: str = (
        "refund_policy.txt,"
        "delivery_policy.txt,"
        "account_policy.txt,"
        "escalation_policy.txt"
    )
    RAG_TOP_K: int = 3
    RAG_CHUNK_TOKEN_SIZE: int = 120
    RAG_CHUNK_TOKEN_OVERLAP: int = 25
    RAG_EMBEDDING_DIMENSIONS: int = 384
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")


settings = Settings()
