#!/usr/bin/env python3
"""Centralized environment configuration using pydantic-settings.
All fields are optional to allow test environments that do not provide them.
The `gemini_key` property prefers GEMINI_API_KEY over the legacy GOOGLE_API_KEY.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError

class Settings(BaseSettings):
    # Core configuration (optional for test environments)
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    # Backward compatibility: support GOOGLE_API_KEY as fallback
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    AI_MODEL: str = Field(default="gemini-3-flash-preview", env="AI_MODEL")
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    STORAGE_URL: Optional[str] = Field(default=None, env="STORAGE_URL")
    MAX_SCAN_DURATION: int = Field(default=1800, env="MAX_SCAN_DURATION")
    MAX_PAGES: int = Field(default=100, env="MAX_PAGES")
    MAX_TEST_CASES: int = Field(default=200, env="MAX_TEST_CASES")
    MAX_CONCURRENT_SCANS: int = Field(default=5, env="MAX_CONCURRENT_SCANS")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    @property
    def gemini_key(self) -> Optional[str]:
        """Effective Gemini API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    class Config:
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Silently ignore any extra env vars (e.g., Supabase keys) that are not declared here.
        extra = "ignore"

# Instantiate a singleton for import convenience
try:
    settings = Settings()
except ValidationError as exc:
    # Fail fast with clear message if required vars missing
    raise RuntimeError(f"Configuration error: {exc}") from exc
