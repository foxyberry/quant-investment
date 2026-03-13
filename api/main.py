"""
FastAPI application entry point.

Main application instance with middleware configuration and router registration.
"""

from contextlib import asynccontextmanager
import threading
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.database import init_db
from api.routers import analysis_router, broker_router, exchange_rates_router, execution_history_router, health_router, portfolio_router, screening_router, settings_router
from api.services.broker_settings_service import get_broker_settings_service
from api.routers.backtest import router as backtest_router
from api.routers.cross_validation import router as cross_validation_router
from api.routers.market import router as market_router
from api.routers.search import router as search_router
from api.routers.agent_task import router as agent_task_router
from api.routers.kiwoom import router as kiwoom_router
from api.routers.strategy import router as strategy_router
from api.routers.watchlist import router as watchlist_router


def _backfill_metadata():
    """One-time backfill: populate sector/industry/country/exchange for existing holdings."""
    import logging
    _logger = logging.getLogger(__name__)
    try:
        from api.database import SessionLocal
        from api.models.portfolio import Holding
        db = SessionLocal()
        try:
            # Find holdings missing any metadata field
            from sqlalchemy import or_
            rows = db.query(Holding).filter(
                or_(
                    Holding.sector.is_(None),
                    Holding.industry.is_(None),
                    Holding.country.is_(None),
                    Holding.exchange.is_(None),
                )
            ).all()
            if not rows:
                _logger.info("No holdings need metadata backfill")
                return

            _logger.info(f"Backfilling metadata for {len(rows)} holdings...")

            # Partition by market
            kr_kospi = [r for r in rows if r.ticker.endswith(".KS")]
            kr_kosdaq = [r for r in rows if r.ticker.endswith(".KQ")]
            us_tickers = [r for r in rows if not r.ticker.endswith((".KS", ".KQ"))]

            # Korean: batch via SectorFetcher
            try:
                from screener.sector_fetcher import get_sector_fetcher
                fetcher = get_sector_fetcher()

                if kr_kospi:
                    kospi_map = fetcher.get_all_sector_classifications("KOSPI")
                    for r in kr_kospi:
                        r.sector = kospi_map.get(r.ticker)
                        r.country = "South Korea"
                        r.exchange = "KOSPI"

                if kr_kosdaq:
                    kosdaq_map = fetcher.get_all_sector_classifications("KOSDAQ")
                    for r in kr_kosdaq:
                        r.sector = kosdaq_map.get(r.ticker)
                        r.country = "South Korea"
                        r.exchange = "KOSDAQ"
            except Exception as e:
                _logger.warning(f"KR sector backfill failed: {e}")

            # US: parallel yfinance (return pure dicts to avoid thread-unsafe ORM mutation)
            if us_tickers:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                def _fetch_us_meta(ticker: str):
                    try:
                        import yfinance as yf
                        info = yf.Ticker(ticker).info
                        return {
                            "sector": info.get("sector"),
                            "industry": info.get("industry"),
                            "country": info.get("country"),
                            "exchange": info.get("exchange"),
                        }
                    except Exception as e:
                        _logger.warning(f"US metadata fetch failed for {ticker}: {e}")
                        return {}

                ticker_to_holding = {r.ticker: r for r in us_tickers}
                with ThreadPoolExecutor(max_workers=min(len(us_tickers), 8)) as executor:
                    futures = {executor.submit(_fetch_us_meta, r.ticker): r.ticker for r in us_tickers}
                    for f in as_completed(futures):
                        t = futures[f]
                        try:
                            meta = f.result()
                            h = ticker_to_holding[t]
                            h.sector = meta.get("sector")
                            h.industry = meta.get("industry")
                            h.country = meta.get("country")
                            h.exchange = meta.get("exchange")
                        except Exception:
                            pass

            db.commit()
            total = len(kr_kospi) + len(kr_kosdaq) + len(us_tickers)
            _logger.info(f"Backfilled metadata for {total} holdings")
        except Exception as e:
            db.rollback()
            _logger.error(f"Metadata backfill failed: {e}")
        finally:
            db.close()
    except Exception as e:
        _logger.error(f"Metadata backfill initialization failed: {e}")


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
        # Start background metadata backfill for existing holdings
        threading.Thread(target=_backfill_metadata, daemon=True, name="metadata-backfill").start()
        # Start macro background collectors
        try:
            from api.services.investor_flow_collector import run_investor_flow_collector
            threading.Thread(
                target=run_investor_flow_collector,
                daemon=True,
                name="investor-flow-collector",
            ).start()
        except Exception as e:
            print(f"WARNING: Investor flow collector failed to start: {e}")

        try:
            from api.services.fx_collector import run_fx_collector
            threading.Thread(
                target=run_fx_collector,
                daemon=True,
                name="fx-collector",
            ).start()
        except Exception as e:
            print(f"WARNING: FX collector failed to start: {e}")

        try:
            from api.services.market_breadth_collector import run_market_breadth_collector
            threading.Thread(
                target=run_market_breadth_collector,
                daemon=True,
                name="market-breadth-collector",
            ).start()
        except Exception as e:
            print(f"WARNING: Market breadth collector failed to start: {e}")

        try:
            from api.services.macro_market_service import get_macro_market_service
            _macro_svc = get_macro_market_service()  # singleton; router uses same instance
            threading.Thread(
                target=_macro_svc.run_history_collector,
                daemon=True,
                name="macro-history-collector",
            ).start()
        except Exception as e:
            print(f"WARNING: Macro history collector failed to start: {e}")

        try:
            get_broker_settings_service().apply_tiger_settings_to_runtime()
        except Exception as e:
            print(f"WARNING: Tiger settings runtime apply failed: {e}")
        try:
            get_broker_settings_service().apply_ibkr_settings_to_runtime()
        except Exception as e:
            print(f"WARNING: IBKR settings runtime apply failed: {e}")
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
        print("Strategy persistence will be unavailable until DB is reachable.")

    yield

    # Shutdown (종료 시 실행)
    print("Shutting down application...")
    try:
        from api.services.macro_market_service import get_macro_market_service
        get_macro_market_service()._flush_to_db()
    except Exception:
        pass


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
    app.include_router(exchange_rates_router)
    app.include_router(screening_router)
    app.include_router(settings_router)
    app.include_router(search_router)
    app.include_router(strategy_router)
    app.include_router(backtest_router)
    app.include_router(cross_validation_router)
    app.include_router(agent_task_router)
    app.include_router(kiwoom_router)
    app.include_router(broker_router)
    app.include_router(execution_history_router)
    app.include_router(watchlist_router)

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
