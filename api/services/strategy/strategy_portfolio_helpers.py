"""
Strategy Portfolio Helpers.

Internal helpers for portfolio construction, ranking, and node survivor
computation used by strategy_execution_service. Not exposed directly as
part of the public API surface.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from api.schemas.strategy import (
    LongShortBasketItem,
    LongShortBaskets,
    NodeIntermediateResult,
    PortfolioConstructionConfig,
    PortfolioConstructionResult,
    RankedResultItem,
    RankingConfig,
    StrategyNode,
    StrategyResultItem,
    WeightedPortfolioItem,
)
from screener import StockScreener
from api.services.strategy.strategy_core_service import _to_optional_float

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weight math
# ---------------------------------------------------------------------------

def _normalize_weights(raw: np.ndarray) -> np.ndarray:
    clipped = np.clip(raw.astype(float), 0.0, None)
    total = float(clipped.sum())
    if not np.isfinite(total) or total <= 0:
        return np.array([])
    return clipped / total


def _build_equal_weights(asset_count: int) -> np.ndarray:
    if asset_count <= 0:
        return np.array([])
    return np.ones(asset_count, dtype=float) / float(asset_count)


def _compute_inverse_vol_weights(vols: np.ndarray) -> np.ndarray:
    safe_vols = np.where(np.isfinite(vols) & (vols > 1e-9), vols, np.nan)
    inv = 1.0 / safe_vols
    inv = np.where(np.isfinite(inv), inv, 0.0)
    weights = _normalize_weights(inv)
    if weights.size == 0:
        return _build_equal_weights(len(vols))
    return weights


def _compute_risk_parity_weights(cov: np.ndarray, max_iter: int = 300, tol: float = 1e-7) -> np.ndarray:
    n = cov.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])

    w = _build_equal_weights(n)
    target_budget = np.ones(n, dtype=float) / n
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    cov = (cov + cov.T) / 2.0

    for _ in range(max_iter):
        port_var = float(w @ cov @ w)
        if not np.isfinite(port_var) or port_var <= 1e-12:
            return _build_equal_weights(n)
        mrc = cov @ w
        rc = (w * mrc) / np.sqrt(port_var)
        target_rc = target_budget * np.sqrt(port_var)
        gap = rc - target_rc
        if float(np.max(np.abs(gap))) < tol:
            break
        denom = np.where(np.abs(rc) < 1e-12, 1e-12, rc)
        w = w * (target_rc / denom)
        w = _normalize_weights(w)
        if w.size == 0:
            return _build_equal_weights(n)
    return w


def _estimate_return_matrix(
    tickers: List[str],
    lookback_days: int,
    probe_conditions: List,
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    screener = StockScreener(
        conditions=probe_conditions,
        max_workers=1,
        use_full_universe=True,
        use_cache=True,
    )
    return_map: Dict[str, pd.Series] = {}

    for ticker in tickers:
        try:
            data = screener._fetch_data(ticker, lookback_days + 30)  # type: ignore[attr-defined]
        except Exception:
            data = None
        if data is None or data.empty or "close" not in data.columns:
            continue
        series = pd.to_numeric(data["close"], errors="coerce").pct_change().dropna().tail(lookback_days)
        if len(series) < max(20, lookback_days // 3):
            continue
        return_map[ticker] = series

    if not return_map:
        return pd.DataFrame()

    matrix = pd.DataFrame(return_map).dropna(axis=1, how="all")
    if matrix.empty:
        return pd.DataFrame()
    matrix = matrix.tail(lookback_days).dropna(how="all")
    return matrix


# ---------------------------------------------------------------------------
# Portfolio construction
# ---------------------------------------------------------------------------

def build_weighted_portfolio(
    final_items: List[StrategyResultItem],
    leaf_conditions: List,
    config: Optional[PortfolioConstructionConfig],
) -> tuple[List[WeightedPortfolioItem], Optional[PortfolioConstructionResult]]:
    if not config:
        return [], None

    requested = max(0, int(config.max_assets))
    candidates = final_items[:requested]
    if not candidates:
        return [], PortfolioConstructionResult(
            mode_requested=config.mode,
            mode_applied="equal_weight",
            lookback_days=config.lookback_days,
            assets_requested=requested,
            assets_used=0,
            target_volatility=config.target_volatility,
            fallback_reason="no_matched_assets",
        )

    tickers = [item.ticker for item in candidates]
    returns_matrix = _estimate_return_matrix(tickers, config.lookback_days, leaf_conditions)

    used_tickers: List[str]
    weights: np.ndarray
    vols: np.ndarray
    cov: np.ndarray
    mode_applied = config.mode
    fallback_reason: Optional[str] = None

    if returns_matrix.empty or returns_matrix.shape[1] < 2:
        used_tickers = tickers
        weights = _build_equal_weights(len(used_tickers))
        vols = np.zeros(len(used_tickers), dtype=float)
        cov = np.diag(np.where(vols > 0, vols ** 2, 1e-8))
        mode_applied = "equal_weight"
        fallback_reason = "insufficient_return_history"
    else:
        used_tickers = list(returns_matrix.columns)
        vols_series = returns_matrix.std(ddof=1).replace([np.inf, -np.inf], np.nan).fillna(0.0) * np.sqrt(252.0)
        vols = vols_series.to_numpy(dtype=float)
        cov_df = returns_matrix.cov(ddof=1).fillna(0.0) * 252.0
        cov = cov_df.to_numpy(dtype=float)
        if config.mode == "risk_parity":
            weights = _compute_risk_parity_weights(cov)
            if weights.size == 0:
                weights = _compute_inverse_vol_weights(vols)
                mode_applied = "inverse_vol"
                fallback_reason = "risk_parity_solver_failed"
        else:
            weights = _compute_inverse_vol_weights(vols)

    if weights.size == 0:
        used_tickers = tickers
        weights = _build_equal_weights(len(used_tickers))
        vols = np.zeros(len(used_tickers), dtype=float)
        cov = np.diag(np.where(vols > 0, vols ** 2, 1e-8))
        mode_applied = "equal_weight"
        fallback_reason = fallback_reason or "weight_normalization_failed"

    item_by_ticker = {item.ticker: item for item in candidates}
    weighted_items: List[WeightedPortfolioItem] = []
    for idx, ticker in enumerate(used_tickers):
        item = item_by_ticker.get(ticker)
        if item is None:
            continue
        vol = float(vols[idx]) if idx < len(vols) and np.isfinite(vols[idx]) else None
        weighted_items.append(
            WeightedPortfolioItem(
                ticker=ticker,
                name=item.name,
                weight=float(weights[idx]),
                current_price=item.current_price,
                annualized_volatility=vol,
            )
        )

    portfolio_vol: Optional[float] = None
    suggested_leverage: Optional[float] = None
    if cov.size > 0 and weights.size > 0:
        est_var = float(weights @ cov @ weights)
        if np.isfinite(est_var) and est_var > 0:
            portfolio_vol = float(np.sqrt(est_var))
            if config.target_volatility:
                suggested_leverage = float(config.target_volatility / portfolio_vol)

    return weighted_items, PortfolioConstructionResult(
        mode_requested=config.mode,
        mode_applied=mode_applied,
        lookback_days=config.lookback_days,
        assets_requested=requested,
        assets_used=len(weighted_items),
        estimated_portfolio_volatility=portfolio_vol,
        target_volatility=config.target_volatility,
        suggested_gross_leverage=suggested_leverage,
        fallback_reason=fallback_reason,
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def extract_ranking_score(item: StrategyResultItem, metric_key: str) -> Optional[float]:
    if metric_key == "current_price":
        return _to_optional_float(item.current_price)
    if metric_key == "per":
        return _to_optional_float(item.per)
    if metric_key == "pbr":
        return _to_optional_float(item.pbr)
    if metric_key == "dividend_yield":
        return _to_optional_float(item.dividend_yield)

    for cond in item.conditions:
        details = cond.get("details", {}) if isinstance(cond, dict) else {}
        if isinstance(details, dict) and metric_key in details:
            score = _to_optional_float(details.get(metric_key))
            if score is not None:
                return score
    return None


def build_ranking_outputs(
    final_items: List[StrategyResultItem],
    ranking_config: Optional[RankingConfig],
) -> tuple[List[RankedResultItem], Optional[LongShortBaskets]]:
    if not ranking_config:
        return [], None

    candidates = final_items[: int(ranking_config.max_assets)]
    scored_rows: List[tuple[StrategyResultItem, float]] = []
    for item in candidates:
        score = extract_ranking_score(item, ranking_config.metric_key)
        if score is None or not np.isfinite(score):
            continue
        scored_rows.append((item, float(score)))

    if not scored_rows:
        return [], LongShortBaskets(
            metric_key=ranking_config.metric_key,
            direction=ranking_config.direction,
            long=[],
            short=[],
        )

    reverse = ranking_config.direction == "desc"
    scored_rows.sort(key=lambda row: row[1], reverse=reverse)

    ranked_results: List[RankedResultItem] = []
    for idx, (item, score) in enumerate(scored_rows, start=1):
        ranked_results.append(
            RankedResultItem(
                ticker=item.ticker,
                name=item.name,
                score=score,
                rank=idx,
            )
        )

    n = len(scored_rows)
    top_n = max(1, int(np.ceil(n * (ranking_config.top_percent / 100.0))))
    long_rows = scored_rows[:top_n]

    short_rows: List[tuple[StrategyResultItem, float]] = []
    if ranking_config.long_short and ranking_config.bottom_percent > 0:
        bottom_n = max(1, int(np.ceil(n * (ranking_config.bottom_percent / 100.0))))
        short_rows = scored_rows[-bottom_n:]

    long_weight = (1.0 / len(long_rows)) if long_rows else 0.0
    short_weight = (1.0 / len(short_rows)) if short_rows else 0.0

    long_basket = [
        LongShortBasketItem(
            ticker=item.ticker,
            name=item.name,
            score=score,
            side="long",
            weight=float(long_weight),
        )
        for item, score in long_rows
    ]
    short_basket = [
        LongShortBasketItem(
            ticker=item.ticker,
            name=item.name,
            score=score,
            side="short",
            weight=float(short_weight),
        )
        for item, score in short_rows
    ]

    return ranked_results, LongShortBaskets(
        metric_key=ranking_config.metric_key,
        direction=ranking_config.direction,
        long=long_basket,
        short=short_basket,
    )


# ---------------------------------------------------------------------------
# Node survivor computation
# ---------------------------------------------------------------------------

def passes_node(result: Any, meta: dict) -> bool:
    """Check whether a screening result passes a given node's conditions."""
    indices = meta["leaf_indices"]
    if not indices:
        return True

    operator = meta.get("operator", "and")
    relevant = [
        result.condition_results[i]
        for i in indices
        if i < len(result.condition_results)
    ]
    if not relevant:
        return True

    if operator == "or":
        return any(r.matched for r in relevant)
    if operator == "not":
        return not relevant[0].matched
    return all(r.matched for r in relevant)


def compute_node_survivors(
    node_id: str,
    all_results: list,
    nodes_by_id: Dict[str, StrategyNode],
    incoming: Dict[str, List[str]],
    node_meta: Dict[str, dict],
    child_ids_set: set,
    cache: Dict[str, set],
    child_to_parent: Optional[Dict[str, str]] = None,
) -> set:
    """Compute the set of result indices that survive up to this node."""
    if node_id in cache:
        return cache[node_id]

    node = nodes_by_id.get(node_id)
    if node is None:
        cache[node_id] = set()
        return set()

    all_indices = set(range(len(all_results)))

    if node.data.node_type in ("universe", "sector"):
        cache[node_id] = all_indices
        return all_indices

    if node.data.node_type == "condition":
        meta = node_meta.get(node_id, {})
        leaf_idx = meta.get("leaf_indices", [])
        own_passers = set()
        for i, r in enumerate(all_results):
            if leaf_idx and leaf_idx[0] < len(r.condition_results):
                if r.condition_results[leaf_idx[0]].matched:
                    own_passers.add(i)
        upstream_ids = incoming.get(node_id, [])
        if not upstream_ids and child_to_parent and node_id in child_to_parent:
            parent_id = child_to_parent[node_id]
            parent = nodes_by_id.get(parent_id)
            if parent and parent.data.child_node_ids:
                upstream_ids = [
                    uid
                    for uid in incoming.get(parent_id, [])
                    if uid not in set(parent.data.child_node_ids)
                ]
        if upstream_ids:
            upstream = set.intersection(*(
                compute_node_survivors(
                    uid, all_results, nodes_by_id, incoming,
                    node_meta, child_ids_set, cache, child_to_parent,
                )
                for uid in upstream_ids
            ))
            result = own_passers & upstream
        else:
            result = own_passers
        cache[node_id] = result
        return result

    if node.data.node_type == "logic":
        operator = (node.data.logic_operator or "and").lower()
        child_ids = node.data.child_node_ids or []
        source_ids = child_ids if child_ids else incoming.get(node_id, [])

        child_sets = [
            compute_node_survivors(
                sid, all_results, nodes_by_id, incoming,
                node_meta, child_ids_set, cache, child_to_parent,
            )
            for sid in source_ids
            if nodes_by_id.get(sid) and nodes_by_id[sid].data.node_type != "universe"
        ]

        if not child_sets:
            combined = all_indices
        elif operator == "or":
            combined = set.union(*child_sets)
        elif operator == "not":
            combined = all_indices - child_sets[0]
        else:
            combined = set.intersection(*child_sets)

        if child_ids:
            upstream_ids = [
                uid for uid in incoming.get(node_id, [])
                if uid not in set(child_ids)
            ]
            if upstream_ids:
                upstream = set.intersection(*(
                    compute_node_survivors(
                        uid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache, child_to_parent,
                    )
                    for uid in upstream_ids
                ))
                combined = combined & upstream

        cache[node_id] = combined
        return combined

    if node.data.node_type == "output":
        child_sets = []
        reachable: set[str] = set()

        def _collect_reachable(nid: str) -> None:
            if nid in reachable:
                return
            reachable.add(nid)
            for uid in incoming.get(nid, []):
                _collect_reachable(uid)
            rn = nodes_by_id.get(nid)
            if rn and rn.data.child_node_ids:
                for cid in rn.data.child_node_ids:
                    _collect_reachable(cid)

        _collect_reachable(node_id)

        for sid in incoming.get(node_id, []):
            if nodes_by_id.get(sid) and nodes_by_id[sid].data.node_type != "universe":
                child_sets.append(
                    compute_node_survivors(
                        sid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache, child_to_parent,
                    )
                )
        for n in nodes_by_id.values():
            if (
                n.data.node_type in ("logic", "condition")
                and n.id not in child_ids_set
                and n.id not in reachable
            ):
                child_sets.append(
                    compute_node_survivors(
                        n.id, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache, child_to_parent,
                    )
                )
        if not child_sets:
            combined = all_indices
        else:
            combined = set.intersection(*child_sets)
        cache[node_id] = combined
        return combined

    cache[node_id] = all_indices
    return all_indices
