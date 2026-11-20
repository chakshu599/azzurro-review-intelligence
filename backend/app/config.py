"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Azzurro Review Intelligence"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://harsh@/azzurro?host=/tmp&port=5433"
    sync_database_url: str = "postgresql+psycopg2://harsh@/azzurro?host=/tmp&port=5433"

    # AI integrations (optional)
    groq_api_key: str = ""
    openai_api_key: str = ""
    ai_model: str = "llama-3.1-8b-instant"
    ai_enabled: bool = True

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Collection
    scraper_request_delay: float = 2.0
    scraper_max_retries: int = 3
    scraper_timeout_seconds: int = 45
    scraper_headless: bool = True

    # Rate limiting for public endpoints
    rate_limit_enabled: bool = False

    # Timezone for weekly analytics
    reporting_timezone: str = "Australia/Sydney"

    # Secret for protecting collection/import endpoints
    admin_secret: str = ""

    # Sentiment model
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    sentiment_fallback: str = "vader"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_ai_key(self) -> bool:
        return bool(self.groq_api_key or self.openai_api_key)


settings = Settings()