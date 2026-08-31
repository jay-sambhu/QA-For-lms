from pathlib import Path
from pydantic import BaseSettings, Field, ValidationError
import os

class Settings(BaseSettings):
    # Core configuration
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    GEMINI_API_KEY: str = Field(None, env="GEMINI_API_KEY")
    # Backward compatibility: support GOOGLE_API_KEY as fallback
    GOOGLE_API_KEY: str = Field(None, env="GOOGLE_API_KEY")
    AI_MODEL: str = Field("gemini-3-flash-preview", env="AI_MODEL")
    REDIS_URL: str = Field(None, env="REDIS_URL")
    STORAGE_URL: str = Field(None, env="STORAGE_URL")
    MAX_SCAN_DURATION: int = Field(1800, env="MAX_SCAN_DURATION")
    MAX_PAGES: int = Field(100, env="MAX_PAGES")
    MAX_TEST_CASES: int = Field(200, env="MAX_TEST_CASES")
    MAX_CONCURRENT_SCANS: int = Field(5, env="MAX_CONCURRENT_SCANS")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")

    @property
    def gemini_key(self) -> str:
        """Return the effective Gemini API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY

    class Config:
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instantiate a singleton for import convenience
try:
    settings = Settings()
except ValidationError as exc:
    # Fail fast with clear message if required vars missing
    raise RuntimeError(f"Configuration error: {exc}") from exc
