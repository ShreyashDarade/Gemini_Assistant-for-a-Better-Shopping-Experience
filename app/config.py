"""
Production-ready configuration management.
All settings loaded from environment variables only.
"""

import json
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ===========================================
    # AI Configuration (Required - from .env)
    # ===========================================
    gemini_api_key: str  # Required - must be set in .env
    ai_model: str = "gemini-3-pro-preview"  # Can be overridden in .env
    ai_max_tokens: int = 2048
    ai_temperature: float = 0.7
    
    # ===========================================
    # Database
    # ===========================================
    database_url: str = "sqlite+aiosqlite:///./shopping_assistant.db"
    
    # ===========================================
    # Server Configuration
    # ===========================================
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    debug: bool = False
    
    # ===========================================
    # CORS
    # ===========================================
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    # ===========================================
    # Rate Limiting
    # ===========================================
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # ===========================================
    # Logging
    # ===========================================
    log_level: str = "INFO"
    log_format: str = "json"
    
    # ===========================================
    # Cache & Session
    # ===========================================
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000
    session_timeout_minutes: int = 30
    max_conversation_history: int = 20


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()


# Convenience function for dependency injection
def get_config() -> Settings:
    """Get settings for FastAPI dependency injection."""
    return get_settings()
