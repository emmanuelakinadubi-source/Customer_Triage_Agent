from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "Customer Triage Agent API"
    app_version: str = "0.1.0"
    allowed_origins: List[str] = ["*"]
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4.1-mini"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")


settings = Settings()
