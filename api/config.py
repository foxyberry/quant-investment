"""
API Configuration module using pydantic-settings.

Manages environment variables and application settings.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        api_host: Host address for the API server (default: 0.0.0.0)
        api_port: Port number for the API server (default: 8000)
        debug: Enable debug mode (default: False)
        cors_origins: List of allowed CORS origins
        app_name: Application name
        app_version: Application version
    """

    # Server settings (서버 설정)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # CORS settings (CORS 설정)
    # Override via env: CORS_ORIGINS='["http://localhost:3002"]'
    # Both localhost and 127.0.0.1 are listed because browsers treat them as different origins.
    cors_origins: List[str] = [
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002",
    ]

    # Database settings (데이터베이스 설정)
    database_url: str = "sqlite:///data/quant.db"

    # Application metadata (애플리케이션 메타데이터)
    app_name: str = "Quant Investment API"
    app_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.

    Returns:
        Settings: Application settings instance
    """
    return Settings()
