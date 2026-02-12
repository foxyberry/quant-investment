"""
Dependency injection module for FastAPI.

Provides common dependencies used across the application.
"""

from typing import Annotated

from fastapi import Depends

from api.config import Settings, get_settings


# Type alias for settings dependency (설정 의존성 타입 별칭)
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_app_settings() -> Settings:
    """
    Dependency function to get application settings.

    This is a wrapper around get_settings for use in FastAPI's Depends().

    Returns:
        Settings: Application settings instance
    """
    return get_settings()


# Database session dependency placeholder (데이터베이스 세션 의존성 - 추후 구현)
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Dependency function to get database session.
#
#     Yields:
#         AsyncSession: SQLAlchemy async session
#     """
#     async with async_session_maker() as session:
#         yield session


# Cache dependency placeholder (캐시 의존성 - 추후 구현)
# async def get_cache() -> Redis:
#     """
#     Dependency function to get Redis cache client.
#
#     Returns:
#         Redis: Redis client instance
#     """
#     return redis_client
