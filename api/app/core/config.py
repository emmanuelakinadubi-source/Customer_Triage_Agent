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
    DATABASE_URL: str = "sqlite:///./data/triage.db"
    MLFLOW_TRACKING_URI: str = ""
    RAG_POLICY_DOCUMENT_PATH: str = "refund_policy.txt"
    RAG_TOP_K: int = 3
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")


settings = Settings()
