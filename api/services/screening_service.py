"""
Screening Service.

Business logic for stock screening operations.
Bridges the API layer with the screener module.
"""

import logging
import time
from typing import Callable, List, Dict, Any, Optional

from api.schemas.screening import (
    ScreeningResultItem,
    ConditionResultItem,
    PresetInfo,
    UniverseInfo,
    normalize_universe_values,
)

# Import screener module
from screener import StockScreener, get_preset, list_presets, PRESET_REGISTRY
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
        """
        Get list of available screening presets.

        Returns static presets and saved QuantCanvas strategies.

        Returns:
            List of PresetInfo with preset details
        """
        presets = []

        # Static presets
        for name in list_presets():
            preset_func = PRESET_REGISTRY.get(name)
            description = ""
            conditions = []

            if preset_func:
                description = (preset_func.__doc__ or "").strip()
                try:
                    condition_instances = preset_func()
                    conditions = [c.name for c in condition_instances]
                except Exception as e:
                    logger.warning(f"Failed to get conditions for preset {name}: {e}")

            presets.append(PresetInfo(
                name=name,
                description=description,
                conditions=conditions,
                source="static",
            ))

        # Saved QuantCanvas strategies
        try:
            from api.services.strategy_save_service import get_strategy_save_service
            from api.services.strategy_service import build_conditions_from_graph
            from api.schemas.strategy import StrategyGraph

            saved = get_strategy_save_service().list_strategies()
            for strategy in saved:
                try:
                    graph = strategy.graph
                    if isinstance(graph, dict):
                        graph = StrategyGraph(**graph)
                    cond_list, _ = build_conditions_from_graph(graph)
                    if not cond_list:
                        continue
                    conditions = [type(c).__name__ for c in cond_list]
                except Exception as e:
                    logger.warning(
                        "Skipping unparseable saved strategy %s: %s",
                        strategy.id, e,
                    )
                    continue

                presets.append(PresetInfo(
                    name=f"custom:{strategy.id}",
                    description=strategy.name,
                    conditions=conditions,
                    source="custom",
                ))
        except Exception as e:
            logger.warning("Failed to load saved strategies for presets: %s", e)

        return presets

    def get_available_universes(self) -> List[UniverseInfo]:
        """
        Get list of available stock universes.

        Returns:
            List of UniverseInfo with universe details
        """
        universes = []

        for key, info in self.UNIVERSES.items():
            stock_count = self._get_universe_stock_count(key)
            universes.append(UniverseInfo(
                name=info["name"],
                description=info["description"],
                stock_count=stock_count
            ))

        return universes

    def _get_universe_stock_count(self, universe: str) -> int:
        """
        Get approximate stock count for a universe.

        Uses a TTL cache to avoid re-fetching symbol lists on every call.

        Args:
            universe: Universe name

        Returns:
            Approximate number of stocks
        """
        universe_upper = universe.upper()

        # Check cache
        cached = self._universe_count_cache.get(universe_upper)
        if cached:
            ts, count = cached
            if time.time() - ts < self._UNIVERSE_COUNT_TTL:
                return count

        defaults = {
            "KOSPI": 900,
            "KOSDAQ": 1600,
            "SP500": 500,
            "NASDAQ100": 100,
        }

        try:
            if universe_upper == "KOSPI":
                symbols = self._kospi_fetcher.get_kospi_symbols()
                count = len(symbols)
            elif universe_upper == "KOSDAQ":
                symbols = self._kospi_fetcher.get_kosdaq_symbols()
                count = len(symbols)
            elif universe_upper == "SP500":
                symbols = self._us_fetcher.get_sp500_symbols()
                count = len(symbols)
            elif universe_upper == "NASDAQ100":
                symbols = self._us_fetcher.get_nasdaq100_symbols()
                count = len(symbols) if symbols else defaults.get(universe_upper, 100)
            else:
                return 0

            self._universe_count_cache[universe_upper] = (time.time(), count)
            return count
        except Exception as e:
            logger.warning(f"Failed to get stock count for {universe}: {e}")
            return defaults.get(universe_upper, 0)

    def _get_universe_tickers(self, universe: str) -> List[str]:
        """
        Get list of tickers for a universe.

        Args:
            universe: Universe name

        Returns:
            List of ticker symbols
        """
        universe_upper = universe.upper()

        if universe_upper == "KOSPI":
            symbols = self._kospi_fetcher.get_kospi_symbols()
            return [s["symbol"] for s in symbols]
        elif universe_upper == "KOSDAQ":
            symbols = self._kospi_fetcher.get_kosdaq_symbols()
            return [s["symbol"] for s in symbols]
        elif universe_upper == "SP500":
            symbols = self._us_fetcher.get_sp500_symbols()
            return [s["symbol"] for s in symbols]
        elif universe_upper == "NASDAQ100":
            symbols = self._us_fetcher.get_nasdaq100_symbols()
            return [s["symbol"] for s in symbols]
        else:
            raise ValueError(f"Unknown universe: {universe}")

    def resolve_universes(self, universe_input: Any) -> List[str]:
        """
        Resolve universe input to a validated, normalized list.

        Rules:
            - "KOSPI" -> ["KOSPI"]
            - "KOSPI,KOSDAQ" -> ["KOSPI", "KOSDAQ"]
            - []/None -> ["KOSPI"]
            - stable order + dedupe
        """
        normalized = normalize_universe_values(universe_input)
        if not normalized:
            normalized = ["KOSPI"]

        invalid = [u for u in normalized if u not in self.UNIVERSES]
        if invalid:
            raise ValueError(f"Unknown universe: {', '.join(invalid)}")
        return normalized

    @staticmethod
    def _safe_name(entry: Dict, fallback_key: str = "symbol") -> str:
        """Return a sanitised stock name from a fetcher entry.

        Handles empty strings, NaN floats, and missing keys by falling
        back to the ticker symbol itself.
        """
        import math

        name = entry.get("name")
        if name is None:
            return str(entry.get(fallback_key, ""))
        if isinstance(name, float):
            return str(entry.get(fallback_key, "")) if math.isnan(name) else str(name)
        name_str = str(name).strip()
        return name_str if name_str else str(entry.get(fallback_key, ""))

    def _get_universe_symbols(self, universe: str) -> Dict[str, str]:
        """
        Get {ticker: name} mapping for a universe.

        Returns the full symbol-to-name dict so callers can inject
        pre-fetched names into StockScreener, avoiding N+1 yfinance calls.
        Names are normalised: empty/NaN values fall back to the ticker symbol.

        Args:
            universe: Universe name

        Returns:
            Dict mapping ticker symbols to stock names
        """
        universe_upper = universe.upper()

        if universe_upper == "KOSPI":
            symbols = self._kospi_fetcher.get_kospi_symbols()
            return {s["symbol"]: self._safe_name(s) for s in symbols}
        elif universe_upper == "KOSDAQ":
            symbols = self._kospi_fetcher.get_kosdaq_symbols()
            return {s["symbol"]: self._safe_name(s) for s in symbols}
        elif universe_upper == "SP500":
            symbols = self._us_fetcher.get_sp500_symbols()
            return {s["symbol"]: self._safe_name(s) for s in symbols}
        elif universe_upper == "NASDAQ100":
            symbols = self._us_fetcher.get_nasdaq100_symbols()
            return {s["symbol"]: self._safe_name(s) for s in symbols} if symbols else {}
        else:
            raise ValueError(f"Unknown universe: {universe}")

    def _get_symbols_for_universes(
        self,
        universe_input: Any,
        fail_fast: bool = False,
    ) -> tuple[Dict[str, str], List[str], Dict[str, str]]:
        """
        Merge symbols across universes with stable-order dedupe.

        Returns:
            (merged_symbols, resolved_universes, failed_universe_errors)
        """
        resolved_universes = self.resolve_universes(universe_input)
        merged_symbols: Dict[str, str] = {}
        failed_errors: Dict[str, str] = {}

        for universe in resolved_universes:
            try:
                symbols = self._get_universe_symbols(universe)
            except Exception as e:
                message = str(e)
                failed_errors[universe] = message
                logger.warning("Universe fetch failed for %s: %s", universe, message)
                if fail_fast:
                    raise ValueError(f"Failed to fetch universe {universe}: {message}")
                continue

            # Stable merge: first seen ticker wins.
            for ticker, name in symbols.items():
                if ticker not in merged_symbols:
                    merged_symbols[ticker] = name

        return merged_symbols, resolved_universes, failed_errors

    def get_tickers_for_universes(
        self,
        universe_input: Any,
        fail_fast: bool = False,
    ) -> List[str]:
        """Return deduplicated tickers across one or more universes."""
        symbols, resolved_universes, failed_errors = self._get_symbols_for_universes(
            universe_input=universe_input,
            fail_fast=fail_fast,
        )
        if not symbols:
            if failed_errors:
                details = ", ".join(f"{k}: {v}" for k, v in failed_errors.items())
                raise ValueError(f"Failed to fetch all universes ({details})")
            raise ValueError(f"No tickers available for universes: {resolved_universes}")
        return list(symbols.keys())

    def _get_universe_stock_count_multi(self, universe_input: Any) -> int:
        """
        Get approximate stock count for one or more universes.

        Single universe uses existing per-universe cache.
        Multi-universe uses combo cache keyed by normalized list.
        """
        resolved_universes = self.resolve_universes(universe_input)
        if len(resolved_universes) == 1:
            return self._get_universe_stock_count(resolved_universes[0])

        cache_key = "|".join(resolved_universes)
        cached = self._universe_combo_count_cache.get(cache_key)
        if cached:
            ts, count = cached
            if time.time() - ts < self._UNIVERSE_COUNT_TTL:
                return count

        symbols, _, _ = self._get_symbols_for_universes(resolved_universes, fail_fast=False)
        count = len(symbols)
        self._universe_combo_count_cache[cache_key] = (time.time(), count)
        return count

    def _resolve_conditions(self, preset: str, params: Optional[Dict[str, Any]] = None) -> list:
        """Resolve conditions from a static preset or custom strategy."""
        if preset.startswith("custom:"):
            strategy_id = preset[len("custom:"):]
            from api.services.strategy_save_service import get_strategy_save_service
            from api.services.strategy_service import build_conditions_from_graph
            from api.schemas.strategy import StrategyGraph

            strategy = get_strategy_save_service().get_strategy(strategy_id)
            if strategy is None:
                raise ValueError(f"Saved strategy not found: {strategy_id}")
            graph = strategy.graph
            if isinstance(graph, dict):
                graph = StrategyGraph(**graph)
            cond_list, _ = build_conditions_from_graph(graph)
            if not cond_list:
                raise ValueError(f"No conditions in saved strategy: {strategy_id}")
            return cond_list

        preset_params = params or {}
        try:
            return get_preset(preset, **preset_params)
        except ValueError as e:
            raise ValueError(f"Invalid preset: {e}")

    def run_screening(
        self,
        preset: str,
        universe: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        universes: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run stock screening with the given preset and universe.

        Args:
            preset: Preset name (static name or 'custom:{strategy_id}')
            universe: Universe name (backward-compatible single value)
            params: Optional parameters to override preset defaults
            universes: Universe list (preferred for multi-market)

        Returns:
            Dict with results, total_count, matched_count, and resolved universes
        """
        started_at = time.perf_counter()
        conditions = self._resolve_conditions(preset, params)

        requested_universes: Any = universes if universes is not None else universe

        resolve_started_at = time.perf_counter()
        try:
            symbols_dict, resolved_universes, failed_errors = self._get_symbols_for_universes(
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

            result_items.append(ScreeningResultItem(
                ticker=result.ticker,
                name=result.name,
                current_price=result.current_price,
                matched=result.matched,
                conditions=conditions_list
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

        return ScreeningResultItem(
            ticker=result.ticker,
            name=result.name,
            current_price=result.current_price,
            matched=result.matched,
            conditions=conditions_list
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
