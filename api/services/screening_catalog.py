"""Catalog and universe helper functions for ScreeningService."""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional

from api.schemas.screening import PresetInfo, UniverseInfo, normalize_universe_values
from screener import PRESET_REGISTRY, get_preset, list_presets

logger = logging.getLogger(__name__)


def get_available_presets(service) -> List[PresetInfo]:
    presets = []

    for name in list_presets():
        preset_func = PRESET_REGISTRY.get(name)
        description = ""
        conditions = []

        if preset_func:
            description = (preset_func.__doc__ or "").strip()
            try:
                condition_instances = preset_func()
                conditions = [condition.name for condition in condition_instances]
            except Exception as exc:
                logger.warning("Failed to get conditions for preset %s: %s", name, exc)

        presets.append(PresetInfo(
            name=name,
            description=description,
            conditions=conditions,
            source="static",
        ))

    try:
        from api.schemas.strategy import StrategyGraph
        from api.services.strategy_save_service import get_strategy_save_service
        from api.services.strategy_service import build_conditions_from_graph

        saved = get_strategy_save_service().list_strategies()
        for strategy in saved:
            try:
                graph = strategy.graph
                if isinstance(graph, dict):
                    graph = StrategyGraph(**graph)
                cond_list, _ = build_conditions_from_graph(graph)
                if not cond_list:
                    continue
                conditions = [type(condition).__name__ for condition in cond_list]
            except Exception as exc:
                logger.warning(
                    "Skipping unparseable saved strategy %s: %s",
                    strategy.id, exc,
                )
                continue

            presets.append(PresetInfo(
                name=f"custom:{strategy.id}",
                description=strategy.name,
                conditions=conditions,
                source="custom",
            ))
    except Exception as exc:
        logger.warning("Failed to load saved strategies for presets: %s", exc)

    return presets


def get_available_universes(service) -> List[UniverseInfo]:
    universes = []
    for key, info in service.UNIVERSES.items():
        universes.append(UniverseInfo(
            name=info["name"],
            description=info["description"],
            stock_count=get_universe_stock_count(service, key),
        ))
    return universes


def get_universe_stock_count(service, universe: str) -> int:
    universe_upper = universe.upper()
    cached = service._universe_count_cache.get(universe_upper)
    if cached:
        ts, count = cached
        if time.time() - ts < service._UNIVERSE_COUNT_TTL:
            return count

    defaults = {
        "KOSPI": 900,
        "KOSDAQ": 1600,
        "SP500": 500,
        "NASDAQ100": 100,
    }

    try:
        if universe_upper == "KOSPI":
            symbols = service._kospi_fetcher.get_kospi_symbols()
            count = len(symbols)
        elif universe_upper == "KOSDAQ":
            symbols = service._kospi_fetcher.get_kosdaq_symbols()
            count = len(symbols)
        elif universe_upper == "SP500":
            symbols = service._us_fetcher.get_sp500_symbols()
            count = len(symbols)
        elif universe_upper == "NASDAQ100":
            symbols = service._us_fetcher.get_nasdaq100_symbols()
            count = len(symbols) if symbols else defaults.get(universe_upper, 100)
        else:
            return 0

        min_expected = defaults.get(universe_upper, 0) // 2
        if count < min_expected:
            prev = service._universe_count_cache.get(universe_upper)
            if prev:
                _, prev_count = prev
                logger.warning(
                    "%s count (%d) below minimum (%d), keeping previous count (%d)",
                    universe, count, min_expected, prev_count,
                )
                service._universe_count_cache[universe_upper] = (time.time(), prev_count)
                return prev_count

            fallback = defaults.get(universe_upper, 0)
            logger.warning(
                "%s count (%d) below minimum (%d), using default (%d)",
                universe, count, min_expected, fallback,
            )
            service._universe_count_cache[universe_upper] = (time.time(), fallback)
            return fallback

        service._universe_count_cache[universe_upper] = (time.time(), count)
        return count
    except Exception as exc:
        logger.warning("Failed to get stock count for %s: %s", universe, exc)
        prev = service._universe_count_cache.get(universe_upper)
        if prev:
            _, prev_count = prev
            service._universe_count_cache[universe_upper] = (time.time(), prev_count)
            return prev_count
        return defaults.get(universe_upper, 0)


def get_universe_tickers(service, universe: str) -> List[str]:
    universe_upper = universe.upper()
    if universe_upper == "KOSPI":
        return [symbol["symbol"] for symbol in service._kospi_fetcher.get_kospi_symbols()]
    if universe_upper == "KOSDAQ":
        return [symbol["symbol"] for symbol in service._kospi_fetcher.get_kosdaq_symbols()]
    if universe_upper == "SP500":
        return [symbol["symbol"] for symbol in service._us_fetcher.get_sp500_symbols()]
    if universe_upper == "NASDAQ100":
        return [symbol["symbol"] for symbol in service._us_fetcher.get_nasdaq100_symbols()]
    raise ValueError(f"Unknown universe: {universe}")


def resolve_universes(service, universe_input: Any) -> List[str]:
    normalized = normalize_universe_values(universe_input)
    if not normalized:
        normalized = ["KOSPI"]

    invalid = [universe for universe in normalized if universe not in service.UNIVERSES]
    if invalid:
        raise ValueError(f"Unknown universe: {', '.join(invalid)}")
    return normalized


def safe_name(entry: Dict, fallback_key: str = "symbol") -> str:
    name = entry.get("name")
    if name is None:
        return str(entry.get(fallback_key, ""))
    if isinstance(name, float):
        return str(entry.get(fallback_key, "")) if math.isnan(name) else str(name)
    name_str = str(name).strip()
    return name_str if name_str else str(entry.get(fallback_key, ""))


def get_universe_symbols(service, universe: str) -> Dict[str, str]:
    universe_upper = universe.upper()
    if universe_upper == "KOSPI":
        symbols = service._kospi_fetcher.get_kospi_symbols()
        return {symbol["symbol"]: safe_name(symbol) for symbol in symbols}
    if universe_upper == "KOSDAQ":
        symbols = service._kospi_fetcher.get_kosdaq_symbols()
        return {symbol["symbol"]: safe_name(symbol) for symbol in symbols}
    if universe_upper == "SP500":
        symbols = service._us_fetcher.get_sp500_symbols()
        return {symbol["symbol"]: safe_name(symbol) for symbol in symbols}
    if universe_upper == "NASDAQ100":
        symbols = service._us_fetcher.get_nasdaq100_symbols()
        return {symbol["symbol"]: safe_name(symbol) for symbol in symbols} if symbols else {}
    raise ValueError(f"Unknown universe: {universe}")


def get_symbols_for_universes(
    service,
    universe_input: Any,
    fail_fast: bool = False,
) -> tuple[Dict[str, str], List[str], Dict[str, str], Dict[str, str]]:
    resolved_universes = resolve_universes(service, universe_input)
    merged_symbols: Dict[str, str] = {}
    failed_errors: Dict[str, str] = {}
    ticker_to_market: Dict[str, str] = {}

    for universe in resolved_universes:
        try:
            symbols = get_universe_symbols(service, universe)
        except Exception as exc:
            message = str(exc)
            failed_errors[universe] = message
            logger.warning("Universe fetch failed for %s: %s", universe, message)
            if fail_fast:
                raise ValueError(f"Failed to fetch universe {universe}: {message}")
            continue

        for ticker, name in symbols.items():
            if ticker not in merged_symbols:
                merged_symbols[ticker] = name
                ticker_to_market[ticker] = universe

    return merged_symbols, resolved_universes, failed_errors, ticker_to_market


def get_tickers_for_universes(
    service,
    universe_input: Any,
    fail_fast: bool = False,
) -> List[str]:
    symbols, resolved_universes, failed_errors, _ticker_to_market = get_symbols_for_universes(
        service,
        universe_input=universe_input,
        fail_fast=fail_fast,
    )
    if not symbols:
        if failed_errors:
            details = ", ".join(f"{key}: {value}" for key, value in failed_errors.items())
            raise ValueError(f"Failed to fetch all universes ({details})")
        raise ValueError(f"No tickers available for universes: {resolved_universes}")
    return list(symbols.keys())


def get_universe_stock_count_multi(service, universe_input: Any) -> int:
    resolved_universes = resolve_universes(service, universe_input)
    if len(resolved_universes) == 1:
        return get_universe_stock_count(service, resolved_universes[0])

    cache_key = "|".join(resolved_universes)
    cached = service._universe_combo_count_cache.get(cache_key)
    if cached:
        ts, count = cached
        if time.time() - ts < service._UNIVERSE_COUNT_TTL:
            return count

    symbols, _, _, _ = get_symbols_for_universes(service, resolved_universes, fail_fast=False)
    count = len(symbols)
    service._universe_combo_count_cache[cache_key] = (time.time(), count)
    return count


def resolve_conditions(
    service,
    preset: str,
    params: Optional[Dict[str, Any]] = None,
    graph=None,
) -> list:
    if preset.startswith("sample:"):
        from api.schemas.strategy import StrategyGraph as StrategyGraphModel
        from api.services.strategy_service import build_conditions_from_graph

        if graph is None:
            raise ValueError("graph payload is required for sample: presets")
        if isinstance(graph, dict):
            if len(graph.get("nodes", [])) > 50 or len(graph.get("edges", [])) > 100:
                raise ValueError("Sample graph too large (max 50 nodes, 100 edges)")
            graph = StrategyGraphModel(**graph)
        cond_list, _ = build_conditions_from_graph(graph)
        if not cond_list:
            raise ValueError("No conditions in sample strategy graph")
        return cond_list

    if preset.startswith("custom:"):
        strategy_id = preset[len("custom:"):]
        from api.schemas.strategy import StrategyGraph
        from api.services.strategy_save_service import get_strategy_save_service
        from api.services.strategy_service import build_conditions_from_graph

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

    try:
        return get_preset(preset, **(params or {}))
    except ValueError as exc:
        raise ValueError(f"Invalid preset: {exc}")
