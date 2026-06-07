from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_title: str = "Customer Triage Agent API"
    app_version: str = "0.1.0"
    allowed_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
