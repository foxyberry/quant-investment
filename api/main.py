"""
FastAPI application entry point.

Main application instance with middleware configuration and router registration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.database import init_db
from api.routers import analysis_router, health_router, portfolio_router, screening_router
from api.routers.backtest import router as backtest_router
from api.routers.market import router as market_router
from api.routers.search import router as search_router
from api.routers.strategy import router as strategy_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup (시작 시 실행)
    settings = get_settings()
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Debug mode: {settings.debug}")
    try:
        init_db()
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
        print("Strategy persistence will be unavailable until DB is reachable.")

    yield

    # Shutdown (종료 시 실행)
    print("Shutting down application...")


def create_app() -> FastAPI:
    """
    Application factory function.

    Creates and configures the FastAPI application instance.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Backend API for quant-investment platform. "
                    "Provides endpoints for portfolio management, "
                    "stock screening, and market analysis.",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware configuration (CORS 미들웨어 설정)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers (라우터 등록)
    app.include_router(health_router)
    app.include_router(market_router)
    app.include_router(analysis_router)
    app.include_router(portfolio_router)
    app.include_router(screening_router)
    app.include_router(search_router)
    app.include_router(strategy_router)
    app.include_router(backtest_router)

    # Future routers (추후 추가될 라우터)
    # app.include_router(news_router, prefix="/api/v1")

    return app


# Application instance (애플리케이션 인스턴스)
app = create_app()


@app.get(
    "/",
    tags=["Root"],
    summary="Root Endpoint",
    description="Welcome endpoint with API information.",
)
async def root() -> dict:
    """
    Root endpoint.

    Returns basic API information and available endpoints.

    Returns:
        dict: API welcome message and information
    """
    settings = get_settings()

    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
