"""
Backtest Router.

Endpoints for running backtests and parameter optimization.
"""

import logging

from fastapi import APIRouter, HTTPException

from api.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    OptimizeRequest,
    OptimizeResponse,
    StrategiesListResponse,
)
from api.services.backtest_service import (
    get_strategies,
    optimize_backtest,
    run_backtest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])


@router.get(
    "/strategies",
    response_model=StrategiesListResponse,
    summary="List available strategies",
    description="Return all available backtesting strategies with their parameter schemas.",
)
async def list_strategies() -> StrategiesListResponse:
    """Return available backtesting strategies."""
    strategies = get_strategies()
    return StrategiesListResponse(strategies=strategies)


@router.post(
    "/run",
    response_model=BacktestResponse,
    summary="Run a backtest",
    description="Run a backtest for a given ticker and strategy. "
    "Returns performance metrics, trade records, and equity curve.",
)
async def run(request: BacktestRequest) -> BacktestResponse:
    """Run a backtest with the specified configuration."""
    try:
        result = run_backtest(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Backtest execution failed")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Optimize strategy parameters",
    description="Run parameter optimization for a strategy. "
    "Tests all combinations of parameter values and returns the best result.",
)
async def optimize(request: OptimizeRequest) -> OptimizeResponse:
    """Optimize strategy parameters for a given ticker."""
    try:
        result = optimize_backtest(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Backtest optimization failed")
        raise HTTPException(
            status_code=500, detail=f"Optimization failed: {str(e)}"
        )
