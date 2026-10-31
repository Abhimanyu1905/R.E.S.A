from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET: str

    # LLM
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    LLM_MODEL: str = "gemini-flash-latest"

    # RAG guardrail
    CONFIDENCE_THRESHOLD: float = 0.35

    # CORS
    CORS_ORIGINS: list[str] | str = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors(cls, v: list[str] | str) -> list[str]:
        """Accept a comma-separated string or a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
