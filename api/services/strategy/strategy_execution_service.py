"""
Strategy Execution Service.

Execution lifecycle: universe resolution, screening, node survivor computation,
and the main execute_strategy / execute_strategy_with_progress entry points.

Delegations:
- Fundamental enrichment → strategy_fundamentals.enrich_fundamentals
- Portfolio construction / ranking / node survivors → strategy_portfolio_helpers
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from api.schemas.strategy import (
    NodeIntermediateResult,
    PortfolioConstructionConfig,
    RankingConfig,
    StrategyGraph,
    StrategyNode,
    StrategyResultItem,
)
from screener import StockScreener
from screener.sector_fetcher import get_sector_fetcher
from api.services.screening_service import ScreeningService
from api.services.strategy.strategy_core_service import (
    _is_korean_ticker,
    _sanitize_value,
    build_flat_conditions_from_graph,
    WARN_TICKERS_THRESHOLD,
    MAX_TICKERS_PER_RUN,
)
from api.services.strategy.strategy_fundamentals import enrich_fundamentals
from api.services.strategy.strategy_portfolio_helpers import (
    build_weighted_portfolio as _build_weighted_portfolio,
    build_ranking_outputs as _build_ranking_outputs,
    compute_node_survivors,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Universe resolution
# ---------------------------------------------------------------------------

def _resolve_execution_universes(
    graph: StrategyGraph,
    screening_service: ScreeningService,
    universe_override: Optional[str] = None,
    universe_overrides: Optional[List[str]] = None,
) -> tuple[List[str], str]:
    """
    Resolve strategy execution universes with deterministic priority.

    Priority:
    1) request-level `universe_overrides` (multi)
    2) request-level `universe_override` (single)
    3) graph universe node values (`universes` then `universe`)
    4) default `KOSPI`
    """
    if universe_overrides:
        resolved = screening_service.resolve_universes(universe_overrides)
        return resolved, resolved[0]

    if universe_override:
        resolved = screening_service.resolve_universes(universe_override)
        return resolved, resolved[0]

    for node in graph.nodes:
        if node.data.node_type != "universe":
            continue
        graph_values: Any = node.data.universes or node.data.universe
        if graph_values:
            resolved = screening_service.resolve_universes(graph_values)
            return resolved, resolved[0]
        break

    resolved = screening_service.resolve_universes(None)
    return resolved, resolved[0]


# ---------------------------------------------------------------------------
# Main execution entry points
# ---------------------------------------------------------------------------

def execute_strategy_with_progress(
    graph: StrategyGraph,
    universe_override: Optional[str] = None,
    universe_overrides: Optional[List[str]] = None,
    portfolio_construction: Optional[PortfolioConstructionConfig] = None,
    ranking_config: Optional[RankingConfig] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    skip_enrich: bool = False,
) -> Dict[str, Any]:
    """Execute a visual strategy graph with an optional progress callback."""
    return execute_strategy(
        graph=graph,
        universe_override=universe_override,
        universe_overrides=universe_overrides,
        portfolio_construction=portfolio_construction,
        ranking_config=ranking_config,
        progress_callback=progress_callback,
        skip_enrich=skip_enrich,
    )


def execute_strategy(
    graph: StrategyGraph,
    universe_override: Optional[str] = None,
    universe_overrides: Optional[List[str]] = None,
    portfolio_construction: Optional[PortfolioConstructionConfig] = None,
    ranking_config: Optional[RankingConfig] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    skip_enrich: bool = False,
) -> Dict[str, Any]:
    """
    Execute a visual strategy graph.

    Returns dict with: results, total_count, screened_count, matched_count,
    universe, universes, conditions_used, node_results, weighted_portfolio,
    portfolio_construction_result, ranked_results, long_short_baskets.
    """
    started_at = time.perf_counter()

    # --- Sector node validation ---
    sector_nodes = [n for n in graph.nodes if n.data.node_type == "sector"]
    if len(sector_nodes) > 1:
        raise ValueError("Only one sector node is allowed per strategy graph")
    if sector_nodes:
        sector_name_raw = (sector_nodes[0].data.sector or "").strip()
        if not sector_name_raw:
            raise ValueError("Sector node must have a sector name")
        _incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
        for edge in graph.edges:
            if edge.target in _incoming:
                _incoming[edge.target].append(edge.source)
        _output = [n for n in graph.nodes if n.data.node_type == "output"]
        reachable: set[str] = set()
        if _output:
            stack = [_output[0].id]
            while stack:
                nid = stack.pop()
                if nid in reachable:
                    continue
                reachable.add(nid)
                stack.extend(_incoming.get(nid, []))
        if sector_nodes[0].id not in reachable:
            sector_nodes = []

    leaf_conditions, _, node_meta = build_flat_conditions_from_graph(graph)
    if not leaf_conditions:
        raise ValueError("No conditions found in graph")

    # --- Universe resolution ---
    screening_service = ScreeningService()
    resolve_started_at = time.perf_counter()
    resolved_universes, primary_universe = _resolve_execution_universes(
        graph=graph,
        screening_service=screening_service,
        universe_override=universe_override,
        universe_overrides=universe_overrides,
    )
    resolve_elapsed_ms = (time.perf_counter() - resolve_started_at) * 1000.0

    # --- Ticker fetching ---
    fetch_started_at = time.perf_counter()
    symbols_dict, resolved_universes_from_fetch, failed_errors, ticker_to_market = (
        screening_service._get_symbols_for_universes(
            universe_input=resolved_universes,
            fail_fast=False,
        )
    )
    if not symbols_dict:
        if failed_errors:
            details = ", ".join(f"{k}: {v}" for k, v in failed_errors.items())
            raise ValueError(f"Failed to fetch all universes ({details})")
        raise ValueError(f"No tickers available for universes: {resolved_universes_from_fetch}")
    tickers = list(symbols_dict.keys())
    fetch_elapsed_ms = (time.perf_counter() - fetch_started_at) * 1000.0
    total_count = len(tickers)

    if total_count > WARN_TICKERS_THRESHOLD:
        logger.warning(
            "strategy.guardrail warning: universe_size=%d exceeds warn threshold=%d",
            total_count, WARN_TICKERS_THRESHOLD,
        )
    if total_count > MAX_TICKERS_PER_RUN:
        raise ValueError(
            f"Target universe too large ({total_count}). Maximum allowed per run is {MAX_TICKERS_PER_RUN}"
        )

    # --- Sector filtering ---
    if sector_nodes:
        sector_name = (sector_nodes[0].data.sector or "").strip()
        kr_universes = [u for u in resolved_universes if u in ("KOSPI", "KOSDAQ")]
        if not kr_universes:
            raise ValueError(
                "Sector filtering is supported only when KR universes (KOSPI/KOSDAQ) are included"
            )
        fetcher = get_sector_fetcher()
        sector_tickers: set[str] = set()
        for market in kr_universes:
            sector_tickers.update(fetcher.get_sector_tickers(market, sector_name))
        tickers = [
            t for t in tickers
            if (not _is_korean_ticker(t)) or (t in sector_tickers)
        ]
        logger.info(
            "Sector filter '%s' on KR universes %s: %d -> %d tickers",
            sector_name, ",".join(kr_universes), total_count, len(tickers),
        )

    # --- Screening ---
    screener = StockScreener(
        conditions=leaf_conditions,
        max_workers=5,
        use_full_universe=True,
        use_cache=True,
        stock_names=symbols_dict,
    )
    eval_started_at = time.perf_counter()
    all_results = screener.run(
        tickers=tickers,
        show_progress=False,
        return_all=True,
        progress_callback=progress_callback,
    )
    eval_elapsed_ms = (time.perf_counter() - eval_started_at) * 1000.0

    # --- Node survivor computation ---
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)
    child_ids_set: set[str] = set()
    child_to_parent: Dict[str, str] = {}
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)
            for cid in n.data.child_node_ids:
                child_to_parent[cid] = n.id

    survivor_cache: Dict[str, set] = {}
    node_results: Dict[str, NodeIntermediateResult] = {}
    output_node_id = None

    for node_id, meta in node_meta.items():
        if meta["node_type"] == "output":
            output_node_id = node_id

        survivor_indices = compute_node_survivors(
            node_id, all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, survivor_cache, child_to_parent,
        )
        passing_stocks: List[StrategyResultItem] = []
        for i in sorted(survivor_indices):
            r = all_results[i]
            cond_details = [
                {
                    "condition_name": cr.condition_name,
                    "matched": bool(cr.matched),
                    "details": _sanitize_value(cr.details),
                }
                for cr in r.condition_results
            ]
            passing_stocks.append(
                StrategyResultItem(
                    ticker=r.ticker,
                    name=r.name,
                    current_price=r.current_price,
                    market=ticker_to_market.get(r.ticker),
                    matched=True,
                    conditions=cond_details,
                )
            )
        node_results[node_id] = NodeIntermediateResult(
            node_id=node_id,
            node_type=meta["node_type"],
            label=meta["label"],
            stock_count=len(passing_stocks),
            stocks=passing_stocks,
        )

    # --- Final results ---
    final_items: List[StrategyResultItem] = []
    if output_node_id and output_node_id in node_results:
        final_items = node_results[output_node_id].stocks
    else:
        for result in all_results:
            if result.matched:
                cond_details = [
                    {
                        "condition_name": cr.condition_name,
                        "matched": bool(cr.matched),
                        "details": _sanitize_value(cr.details),
                    }
                    for cr in result.condition_results
                ]
                final_items.append(
                    StrategyResultItem(
                        ticker=result.ticker,
                        name=result.name,
                        current_price=result.current_price,
                        market=ticker_to_market.get(result.ticker),
                        matched=result.matched,
                        conditions=cond_details,
                    )
                )

    if not skip_enrich:
        enrich_fundamentals(final_items)

    weighted_portfolio, construction_result = _build_weighted_portfolio(
        final_items=final_items,
        leaf_conditions=leaf_conditions,
        config=portfolio_construction,
    )
    ranked_results, long_short_baskets = _build_ranking_outputs(
        final_items=final_items,
        ranking_config=ranking_config,
    )

    conditions_used = [type(c).__name__ for c in leaf_conditions]

    total_elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    eval_throughput = (
        (len(tickers) / eval_elapsed_ms * 1000.0) if eval_elapsed_ms > 0 else float(len(tickers))
    )
    logger.info(
        (
            "strategy.metrics universes=%s total_tickers=%d screened=%d matched=%d "
            "resolve_ms=%.1f fetch_ms=%.1f eval_ms=%.1f total_ms=%.1f eval_tps=%.2f"
        ),
        ",".join(resolved_universes),
        total_count, len(tickers), len(final_items),
        resolve_elapsed_ms, fetch_elapsed_ms, eval_elapsed_ms,
        total_elapsed_ms, eval_throughput,
    )

    return {
        "results": final_items,
        "total_count": total_count,
        "screened_count": len(tickers),
        "matched_count": len(final_items),
        "universe": primary_universe,
        "universes": resolved_universes,
        "conditions_used": conditions_used,
        "node_results": node_results,
        "weighted_portfolio": weighted_portfolio,
        "portfolio_construction_result": construction_result,
        "ranked_results": ranked_results,
        "long_short_baskets": long_short_baskets,
    }
