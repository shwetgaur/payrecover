from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_ROOT.parent / ".env"), extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    groq_fallback_model: str = "llama-3.1-8b-instant"
    razorpay_webhook_secret: str = ""
    database_url: str = f"sqlite:///{(DATA_DIR / 'payrecover.db').as_posix()}"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Allow Vercel production + preview URLs without listing every deploy.
    cors_allow_vercel: bool = True
    demo_now_ist: str = "2026-08-22T14:30:00"
    app_name: str = "PayRecover"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_resolved(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
