"""
Screening Service.

Business logic for stock screening operations.
Bridges the API layer with the screener module.
"""

import logging
import time
from datetime import date
from typing import Callable, List, Dict, Any, Optional

from api.schemas.screening import (
    ScreeningResultItem,
    ConditionResultItem,
    PresetInfo,
    UniverseInfo,
)
from api.services import screening_catalog

# Import screener module
from screener import StockScreener
from screener.kospi_fetcher import KospiListFetcher
from screener.us_fetcher import UsStockFetcher

logger = logging.getLogger(__name__)


class ScreeningService:
    """
    Screening service for stock screening operations.

    Provides methods for running screenings, getting presets, and universes.
    """

    # TTL cache for universe stock counts: {universe: (timestamp, count)}
    _universe_count_cache: Dict[str, tuple] = {}
    _universe_combo_count_cache: Dict[str, tuple] = {}
    _UNIVERSE_COUNT_TTL = 3600  # 1 hour
    WARN_TICKERS_THRESHOLD = 2500
    MAX_TICKERS_PER_RUN = 4000

    # Universe definitions
    UNIVERSES = {
        "KOSPI": {
            "name": "KOSPI",
            "description": "Korea Stock Price Index (Korean Large-Cap)",
            "fetcher": "kospi",
        },
        "KOSDAQ": {
            "name": "KOSDAQ",
            "description": "Korea Securities Dealers Automated Quotations (Korean Growth)",
            "fetcher": "kosdaq",
        },
        "SP500": {
            "name": "SP500",
            "description": "S&P 500 Index (US Large-Cap)",
            "fetcher": "sp500",
        },
        "NASDAQ100": {
            "name": "NASDAQ100",
            "description": "NASDAQ 100 Index (US Technology)",
            "fetcher": "nasdaq100",
        },
    }

    def __init__(self):
        """Initialize the screening service."""
        self._kospi_fetcher = KospiListFetcher()
        self._us_fetcher = UsStockFetcher()

    def get_available_presets(self) -> List[PresetInfo]:
        return screening_catalog.get_available_presets(self)

    def get_available_universes(self) -> List[UniverseInfo]:
        return screening_catalog.get_available_universes(self)

    def _get_universe_stock_count(self, universe: str) -> int:
        return screening_catalog.get_universe_stock_count(self, universe)

    def _get_universe_tickers(self, universe: str) -> List[str]:
        return screening_catalog.get_universe_tickers(self, universe)

    def resolve_universes(self, universe_input: Any) -> List[str]:
        return screening_catalog.resolve_universes(self, universe_input)

    @staticmethod
    def _safe_name(entry: Dict, fallback_key: str = "symbol") -> str:
        return screening_catalog.safe_name(entry, fallback_key)

    def _get_universe_symbols(self, universe: str) -> Dict[str, str]:
        return screening_catalog.get_universe_symbols(self, universe)

    def _get_symbols_for_universes(
        self,
        universe_input: Any,
        fail_fast: bool = False,
    ) -> tuple[Dict[str, str], List[str], Dict[str, str], Dict[str, str]]:
        return screening_catalog.get_symbols_for_universes(self, universe_input, fail_fast)

    def get_tickers_for_universes(
        self,
        universe_input: Any,
        fail_fast: bool = False,
    ) -> List[str]:
        return screening_catalog.get_tickers_for_universes(self, universe_input, fail_fast)

    def _get_universe_stock_count_multi(self, universe_input: Any) -> int:
        return screening_catalog.get_universe_stock_count_multi(self, universe_input)

    def _resolve_conditions(self, preset: str, params: Optional[Dict[str, Any]] = None, graph=None) -> list:
        return screening_catalog.resolve_conditions(self, preset, params, graph)

    def run_screening(
        self,
        preset: str,
        universe: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        universes: Optional[List[str]] = None,
        reference_date: Optional[date] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        graph=None,
    ) -> Dict[str, Any]:
        """
        Run stock screening with the given preset and universe.

        Args:
            preset: Preset name (static name, 'custom:{strategy_id}', or 'sample:{name}')
            universe: Universe name (backward-compatible single value)
            params: Optional parameters to override preset defaults
            universes: Universe list (preferred for multi-market)
            reference_date: Reference date for screening (defaults to today)
            graph: Inline strategy graph for sample: presets

        Returns:
            Dict with results, total_count, matched_count, and resolved universes
        """
        started_at = time.perf_counter()
        conditions = self._resolve_conditions(preset, params, graph=graph)

        requested_universes: Any = universes if universes is not None else universe

        resolve_started_at = time.perf_counter()
        try:
            symbols_dict, resolved_universes, failed_errors, ticker_to_market = self._get_symbols_for_universes(
                universe_input=requested_universes,
                fail_fast=False,
            )
        except ValueError as e:
            raise ValueError(f"Invalid universe: {e}")

        if not symbols_dict:
            if failed_errors:
                details = ", ".join(f"{k}: {v}" for k, v in failed_errors.items())
                raise ValueError(f"Failed to fetch all universes ({details})")
            raise ValueError("No tickers available for screening")
        resolve_elapsed_ms = (time.perf_counter() - resolve_started_at) * 1000.0

        tickers = list(symbols_dict.keys())
        total_count = len(tickers)
        failed_count = len(failed_errors)
        failure_rate = (failed_count / len(resolved_universes)) if resolved_universes else 0.0

        if total_count > self.WARN_TICKERS_THRESHOLD:
            logger.warning(
                "screening.guardrail warning: universe_size=%d exceeds warn threshold=%d",
                total_count,
                self.WARN_TICKERS_THRESHOLD,
            )
        if total_count > self.MAX_TICKERS_PER_RUN:
            raise ValueError(
                f"Target universe too large ({total_count}). Maximum allowed per run is {self.MAX_TICKERS_PER_RUN}"
            )

        # Create screener with pre-fetched stock names
        screener = StockScreener(
            conditions=conditions,
            max_workers=5,
            use_full_universe=False,
            use_cache=True,
            stock_names=symbols_dict,
            reference_date=reference_date,
        )

        # Run screening (show_progress=False for API)
        run_started_at = time.perf_counter()
        results = screener.run(
            tickers=tickers,
            show_progress=False,
            progress_callback=progress_callback,
        )
        run_elapsed_ms = (time.perf_counter() - run_started_at) * 1000.0

        # Convert to response format
        convert_started_at = time.perf_counter()
        total_conditions = len(conditions)
        result_items = []
        for result in results:
            conditions_list = [
                ConditionResultItem(
                    condition_name=cr.condition_name,
                    matched=cr.matched,
                    details=cr.details
                )
                for cr in result.condition_results
            ]

            # Compute condition match score (0-100)
            matched_conditions = sum(1 for cr in result.condition_results if cr.matched)
            score = (matched_conditions / total_conditions) * 100 if total_conditions > 0 else None

            result_items.append(ScreeningResultItem(
                ticker=result.ticker,
                name=result.name,
                market=ticker_to_market.get(result.ticker),
                current_price=result.current_price,
                change_pct=result.change_pct,
                volume=result.volume,
                score=score,
                matched=result.matched,
                conditions=conditions_list,
            ))
        convert_elapsed_ms = (time.perf_counter() - convert_started_at) * 1000.0
        total_elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        eval_throughput = (total_count / run_elapsed_ms * 1000.0) if run_elapsed_ms > 0 else float(total_count)
        logger.info(
            (
                "screening.metrics universes=%s total_tickers=%d matched=%d "
                "resolve_ms=%.1f run_ms=%.1f convert_ms=%.1f total_ms=%.1f "
                "eval_tps=%.2f failed_universe_rate=%.2f"
            ),
            ",".join(resolved_universes),
            total_count,
            len(result_items),
            resolve_elapsed_ms,
            run_elapsed_ms,
            convert_elapsed_ms,
            total_elapsed_ms,
            eval_throughput,
            failure_rate,
        )

        return {
            "results": result_items,
            "total_count": total_count,
            "matched_count": len(result_items),
            "resolved_universes": resolved_universes,
            "failed_universe_errors": failed_errors,
            "elapsed_ms": round(total_elapsed_ms, 1),
        }

    def check_single_stock(
        self,
        ticker: str,
        preset: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ScreeningResultItem:
        """
        Check a single stock against screening conditions.

        Args:
            ticker: Stock ticker symbol
            preset: Preset name
            params: Optional parameters to override preset defaults

        Returns:
            ScreeningResultItem with the evaluation result
        """
        conditions = self._resolve_conditions(preset, params)

        # Create screener
        screener = StockScreener(
            conditions=conditions,
            max_workers=1,
            use_full_universe=False,
            use_cache=True
        )

        # Run single stock screening
        try:
            result = screener.run_single(ticker)
        except ValueError as e:
            raise ValueError(f"Failed to check stock: {e}")

        # Convert to response format
        conditions_list = [
            ConditionResultItem(
                condition_name=cr.condition_name,
                matched=cr.matched,
                details=cr.details
            )
            for cr in result.condition_results
        ]

        # Compute condition match score for single stock
        matched_conditions = sum(1 for cr in result.condition_results if cr.matched)
        total_conds = len(conditions)
        score = (matched_conditions / total_conds) * 100 if total_conds > 0 else None

        return ScreeningResultItem(
            ticker=result.ticker,
            name=result.name,
            current_price=result.current_price,
            change_pct=result.change_pct,
            volume=result.volume,
            score=score,
            matched=result.matched,
            conditions=conditions_list,
        )


# Singleton instance
_screening_service: Optional[ScreeningService] = None


def get_screening_service() -> ScreeningService:
    """
    Get or create the screening service singleton.

    Returns:
        ScreeningService instance
    """
    global _screening_service
    if _screening_service is None:
        _screening_service = ScreeningService()
    return _screening_service
