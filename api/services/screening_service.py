"""
Screening Service.

Business logic for stock screening operations.
Bridges the API layer with the screener module.
"""

import logging
from typing import List, Dict, Any, Optional

from api.schemas.screening import (
    ScreeningResultItem,
    ConditionResultItem,
    PresetInfo,
    UniverseInfo,
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

        Args:
            universe: Universe name

        Returns:
            Approximate number of stocks
        """
        try:
            universe_upper = universe.upper()

            if universe_upper == "KOSPI":
                symbols = self._kospi_fetcher.get_kospi_symbols()
                return len(symbols)
            elif universe_upper == "KOSDAQ":
                symbols = self._kospi_fetcher.get_kosdaq_symbols()
                return len(symbols)
            elif universe_upper == "SP500":
                symbols = self._us_fetcher.get_sp500_symbols()
                return len(symbols)
            elif universe_upper == "NASDAQ100":
                symbols = self._us_fetcher.get_nasdaq100_symbols()
                return len(symbols) if symbols else 100  # Fallback
            else:
                return 0
        except Exception as e:
            logger.warning(f"Failed to get stock count for {universe}: {e}")
            # Return approximate values
            defaults = {
                "KOSPI": 900,
                "KOSDAQ": 1600,
                "SP500": 500,
                "NASDAQ100": 100,
            }
            return defaults.get(universe.upper(), 0)

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
        universe: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run stock screening with the given preset and universe.

        Args:
            preset: Preset name (static name or 'custom:{strategy_id}')
            universe: Universe name
            params: Optional parameters to override preset defaults

        Returns:
            Dict with results, total_count, and matched_count
        """
        conditions = self._resolve_conditions(preset, params)

        # Create screener
        screener = StockScreener(
            conditions=conditions,
            max_workers=5,
            use_full_universe=True,
            use_cache=True
        )

        # Get tickers for the universe
        try:
            tickers = self._get_universe_tickers(universe)
        except ValueError as e:
            raise ValueError(f"Invalid universe: {e}")

        total_count = len(tickers)

        # Run screening (show_progress=False for API)
        results = screener.run(tickers=tickers, show_progress=False)

        # Convert to response format
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

        return {
            "results": result_items,
            "total_count": total_count,
            "matched_count": len(result_items)
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
