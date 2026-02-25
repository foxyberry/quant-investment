"""
Strategy Service.

Business logic for the visual strategy builder.
Converts graph representations into screener conditions and executes them.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np
import pandas as pd

from api.schemas.strategy import (
    ConditionInfo,
    ConditionParamInfo,
    LongShortBasketItem,
    LongShortBaskets,
    NodeIntermediateResult,
    PortfolioConstructionConfig,
    PortfolioConstructionResult,
    RankedResultItem,
    RankingConfig,
    StrategyGraph,
    StrategyNode,
    StrategyResultItem,
    WeightedPortfolioItem,
)
from screener.conditions import BaseCondition, AndCondition, OrCondition, NotCondition
from screener.conditions.registry import get_condition_class_map, get_condition_metadata
from screener import StockScreener
from screener.sector_fetcher import get_sector_fetcher
from api.services.screening_service import ScreeningService
from utils.fundamental_cache import FundamentalCache

logger = logging.getLogger(__name__)

FUNDAMENTAL_TTL_SECONDS = 24 * 60 * 60
_fundamental_cache = FundamentalCache()
WARN_TICKERS_THRESHOLD = 2500
MAX_TICKERS_PER_RUN = 4000

# Auto-populated from @register_condition decorators
CONDITION_CLASS_MAP: Dict[str, Type[BaseCondition]] = get_condition_class_map()
CONDITION_METADATA: Dict[str, Dict[str, Any]] = get_condition_metadata()


def _to_optional_float(value: Any) -> Optional[float]:
    """Safely convert a value to float; return None for NaN/inf/non-numeric."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    return numeric


def _is_korean_ticker(ticker: str) -> bool:
    return ticker.endswith(".KS") or ticker.endswith(".KQ")


def _extract_krx_code(ticker: str) -> str:
    return ticker.split(".")[0]


def _normalize_dividend_yield(value: Any) -> Optional[float]:
    """Normalize dividend yield to percentage points (e.g., 3.2 for 3.2%)."""
    dividend_yield = _to_optional_float(value)
    if dividend_yield is None:
        return None
    # yfinance generally uses decimal (0.03 = 3%), while pykrx uses percent.
    if 0 <= dividend_yield <= 1:
        return dividend_yield * 100.0
    return dividend_yield


def _fetch_kr_fundamentals(tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Fetch KR fundamentals in bulk via pykrx (best effort)."""
    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    missing_tickers: List[str] = []

    for ticker in tickers:
        cached = _fundamental_cache.get("fundamental_kr", ticker, FUNDAMENTAL_TTL_SECONDS)
        if cached is not None:
            fundamentals[ticker] = {
                "per": cached.get("per"),
                "pbr": cached.get("pbr"),
                "dividend_yield": cached.get("dividend_yield"),
            }
        else:
            missing_tickers.append(ticker)

    if not missing_tickers:
        return fundamentals

    try:
        from pykrx import stock as pykrx_stock
    except ImportError:
        return fundamentals

    by_market: Dict[str, Dict[str, str]] = {"KOSPI": {}, "KOSDAQ": {}}
    for ticker in missing_tickers:
        if ticker.endswith(".KS"):
            by_market["KOSPI"][_extract_krx_code(ticker)] = ticker
        elif ticker.endswith(".KQ"):
            by_market["KOSDAQ"][_extract_krx_code(ticker)] = ticker

    for market, code_to_ticker in by_market.items():
        if not code_to_ticker:
            continue

        df = None
        # Weekend/holiday-safe lookup: try recent dates.
        for days_back in range(0, 11):
            date_str = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
            try:
                candidate = pykrx_stock.get_market_fundamental_by_ticker(
                    date=date_str,
                    market=market,
                )
                if candidate is not None and not candidate.empty:
                    df = candidate
                    break
            except Exception:
                continue

        if df is None or df.empty:
            continue

        for code, full_ticker in code_to_ticker.items():
            if code not in df.index:
                continue

            row = df.loc[code]
            parsed = {
                "per": _to_optional_float(row.get("PER")),
                "pbr": _to_optional_float(row.get("PBR")),
                "dividend_yield": _to_optional_float(row.get("DIV")),  # pykrx DIV is already in %
            }
            fundamentals[full_ticker] = parsed
            _fundamental_cache.set("fundamental_kr", full_ticker, parsed)

    return fundamentals


def _fetch_us_fundamentals(tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Fetch US fundamentals via yfinance info (best effort)."""
    if not tickers:
        return {}

    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    missing_tickers: List[str] = []

    for ticker in tickers:
        cached = _fundamental_cache.get("fundamental_us", ticker, FUNDAMENTAL_TTL_SECONDS)
        if cached is not None:
            fundamentals[ticker] = {
                "per": cached.get("per"),
                "pbr": cached.get("pbr"),
                "dividend_yield": cached.get("dividend_yield"),
            }
        else:
            missing_tickers.append(ticker)

    if not missing_tickers:
        return fundamentals

    try:
        import yfinance as yf
    except ImportError:
        return fundamentals

    try:
        tickers_obj = yf.Tickers(" ".join(missing_tickers))
    except Exception:
        tickers_obj = None

    def _is_success_payload(payload: Dict[str, Optional[float]]) -> bool:
        return any(v is not None for v in payload.values())

    def _fetch_one(ticker: str) -> tuple[Dict[str, Optional[float]], bool]:
        try:
            info: Dict[str, Any] = {}
            if tickers_obj is not None:
                ticker_obj = tickers_obj.tickers.get(ticker)
                if ticker_obj is not None:
                    info = ticker_obj.info or {}
            if not info:
                info = yf.Ticker(ticker).info or {}

            payload = {
                "per": _to_optional_float(info.get("trailingPE")),
                "pbr": _to_optional_float(info.get("priceToBook")),
                "dividend_yield": _normalize_dividend_yield(info.get("dividendYield")),
            }
            return payload, _is_success_payload(payload)
        except Exception:
            return {
                "per": None,
                "pbr": None,
                "dividend_yield": None,
            }, False

    max_workers = min(8, len(missing_tickers))
    if max_workers <= 1:
        ticker = missing_tickers[0]
        fetched, success = _fetch_one(ticker)
        fundamentals[ticker] = fetched
        if success:
            _fundamental_cache.set("fundamental_us", ticker, fetched)
        return fundamentals

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_fetch_one, ticker): ticker for ticker in missing_tickers}
        try:
            for future in as_completed(future_map, timeout=10):
                ticker = future_map[future]
                try:
                    fetched, success = future.result(timeout=5)
                    fundamentals[ticker] = fetched
                    if success:
                        _fundamental_cache.set("fundamental_us", ticker, fetched)
                except Exception:
                    fundamentals[ticker] = {
                        "per": None,
                        "pbr": None,
                        "dividend_yield": None,
                    }
        except TimeoutError:
            logger.warning("US fundamentals fetch timed out; filling remaining with None")
            for future, ticker in future_map.items():
                if ticker not in fundamentals:
                    future.cancel()
                    fundamentals[ticker] = {
                        "per": None,
                        "pbr": None,
                        "dividend_yield": None,
                    }

    return fundamentals


def enrich_fundamentals(items: List[StrategyResultItem]) -> None:
    """Fill PER/PBR/dividend_yield for strategy result items (best effort)."""
    if not items:
        return

    unique_tickers = sorted({item.ticker for item in items if item.ticker})
    if not unique_tickers:
        return

    kr_tickers = [t for t in unique_tickers if _is_korean_ticker(t)]
    us_tickers = [t for t in unique_tickers if not _is_korean_ticker(t)]

    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    try:
        fundamentals.update(_fetch_kr_fundamentals(kr_tickers))
    except Exception as e:
        logger.warning("Failed to fetch KR fundamentals: %s", e)

    try:
        fundamentals.update(_fetch_us_fundamentals(us_tickers))
    except Exception as e:
        logger.warning("Failed to fetch US fundamentals: %s", e)

    for item in items:
        data = fundamentals.get(item.ticker, {})
        item.per = data.get("per")
        item.pbr = data.get("pbr")
        item.dividend_yield = data.get("dividend_yield")


def _sanitize_value(v: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


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
    probe_conditions: List[BaseCondition],
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


def _build_weighted_portfolio(
    final_items: List[StrategyResultItem],
    leaf_conditions: List[BaseCondition],
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


def _extract_ranking_score(item: StrategyResultItem, metric_key: str) -> Optional[float]:
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


def _build_ranking_outputs(
    final_items: List[StrategyResultItem],
    ranking_config: Optional[RankingConfig],
) -> tuple[List[RankedResultItem], Optional[LongShortBaskets]]:
    if not ranking_config:
        return [], None

    candidates = final_items[: int(ranking_config.max_assets)]
    scored_rows: List[tuple[StrategyResultItem, float]] = []
    for item in candidates:
        score = _extract_ranking_score(item, ranking_config.metric_key)
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

    baskets = LongShortBaskets(
        metric_key=ranking_config.metric_key,
        direction=ranking_config.direction,
        long=long_basket,
        short=short_basket,
    )
    return ranked_results, baskets


def get_available_conditions() -> List[ConditionInfo]:
    """Return list of available conditions with their parameter schemas."""
    conditions = []
    for key, meta in CONDITION_METADATA.items():
        params = [ConditionParamInfo(**p) for p in meta["params"]]
        conditions.append(
            ConditionInfo(
                key=key,
                label=meta["label"],
                description=meta.get("description", ""),
                category=meta["category"],
                params=params,
                recommended=meta.get("recommended", False),
                order=meta.get("order", 0),
            )
        )
    return conditions


def _coerce_param(value: Any, param_type: str) -> Any:
    """Coerce a parameter value to the expected type."""
    if value is None:
        return None
    if param_type == "int":
        return int(value)
    if param_type == "float":
        return float(value)
    if param_type == "bool":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return value


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


def _build_condition(condition_type: str, params: Dict[str, Any]) -> BaseCondition:
    """Instantiate a single condition from type key and params."""
    cls = CONDITION_CLASS_MAP.get(condition_type)
    if cls is None:
        raise ValueError(f"Unknown condition type: {condition_type}")

    # Coerce params to correct types based on metadata
    meta = CONDITION_METADATA.get(condition_type, {})
    meta_params = {p["name"]: p["type"] for p in meta.get("params", [])}

    coerced = {}
    for k, v in params.items():
        if k in meta_params:
            coerced[k] = _coerce_param(v, meta_params[k])
        else:
            coerced[k] = v

    return cls(**coerced)


def build_conditions_from_graph(graph: StrategyGraph) -> tuple[List[BaseCondition], str]:
    """
    Walk the strategy graph from Output node backward and build nested conditions.

    Returns:
        Tuple of (conditions list, universe name)
    """
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}

    # Build adjacency: target -> list of source node IDs
    # An edge from A -> B means A feeds into B
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    # Find the output node
    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    # Find universe from universe nodes
    universe = "KOSPI"  # default
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    def _resolve_node(node_id: str) -> Optional[BaseCondition]:
        """Recursively resolve a node to a BaseCondition."""
        node = nodes_by_id.get(node_id)
        if node is None:
            return None

        if node.data.node_type == "universe":
            return None

        if node.data.node_type == "sector":
            return None  # Sector filters tickers, not conditions

        if node.data.node_type == "condition":
            if not node.data.condition_type:
                raise ValueError(f"Condition node {node_id} has no condition_type")
            return _build_condition(node.data.condition_type, node.data.params)

        if node.data.node_type == "logic":
            operator = (node.data.logic_operator or "and").lower()
            # New approach: use child_node_ids (group container)
            child_ids = node.data.child_node_ids or []
            if child_ids:
                source_ids = child_ids
            else:
                # Backward compatibility: use edge-based incoming
                source_ids = incoming.get(node_id, [])
            sub_conditions = []
            for src_id in source_ids:
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)

            if not sub_conditions:
                return None

            if operator == "and":
                return AndCondition(sub_conditions) if len(sub_conditions) > 1 else sub_conditions[0]
            elif operator == "or":
                return OrCondition(sub_conditions) if len(sub_conditions) > 1 else sub_conditions[0]
            elif operator == "not":
                return NotCondition(sub_conditions[0])
            else:
                raise ValueError(f"Unknown logic operator: {operator}")

        if node.data.node_type == "output":
            # Resolve all incoming nodes to the output via edges
            sub_conditions = []
            resolved_ids = set()
            for src_id in incoming.get(node_id, []):
                resolved_ids.add(src_id)
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)

            # Also resolve top-level logic/condition nodes not connected
            # via edges (e.g., group nodes using child_node_ids containment)
            child_ids_set: set[str] = set()
            for n in graph.nodes:
                if n.data.child_node_ids:
                    child_ids_set.update(n.data.child_node_ids)

            for n in graph.nodes:
                if (
                    n.data.node_type in ("logic", "condition")
                    and n.id not in child_ids_set  # not a child of a group
                    and n.id not in resolved_ids  # not already resolved via edge
                ):
                    cond = _resolve_node(n.id)
                    if cond is not None:
                        sub_conditions.append(cond)

            return sub_conditions  # type: ignore

        return None

    # Resolve from output node
    resolved = _resolve_node(output_node.id)

    if isinstance(resolved, list):
        conditions = resolved
    elif resolved is not None:
        conditions = [resolved]
    else:
        conditions = []

    return conditions, universe


def build_flat_conditions_from_graph(
    graph: StrategyGraph,
) -> tuple[List[BaseCondition], str, Dict[str, dict]]:
    """
    Walk the strategy graph and extract leaf conditions into a flat list.

    Unlike build_conditions_from_graph() which creates nested composite conditions,
    this function keeps each condition separate so that per-node intermediate results
    can be computed after screening.

    Returns:
        Tuple of (leaf_conditions, universe, node_meta)
        - leaf_conditions: flat list of individual BaseCondition instances
        - universe: universe name string
        - node_meta: Dict[node_id, dict] where each entry has:
            - 'node_type': str
            - 'label': str
            - 'leaf_indices': List[int] - indices into leaf_conditions
            - 'operator': Optional[str] - 'and'/'or'/'not' for logic nodes
    """
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}

    # Build adjacency: target -> list of source node IDs
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    # Find the output node
    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    # Find universe
    universe = "KOSPI"
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    leaf_conditions: List[BaseCondition] = []
    node_meta: Dict[str, dict] = {}

    # Track which nodes are children of group containers
    child_ids_set: set[str] = set()
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)

    def _resolve_flat(node_id: str) -> List[int]:
        """Recursively resolve a node and return leaf condition indices."""
        if node_id in node_meta:
            return node_meta[node_id]["leaf_indices"]

        node = nodes_by_id.get(node_id)
        if node is None:
            return []

        if node.data.node_type == "universe":
            node_meta[node_id] = {
                "node_type": "universe",
                "label": node.data.universe or "Universe",
                "leaf_indices": [],
                "operator": None,
            }
            return []

        if node.data.node_type == "sector":
            node_meta[node_id] = {
                "node_type": "sector",
                "label": node.data.sector or "Sector",
                "leaf_indices": [],
                "operator": None,
            }
            return []

        if node.data.node_type == "condition":
            if not node.data.condition_type:
                raise ValueError(f"Condition node {node_id} has no condition_type")
            cond = _build_condition(node.data.condition_type, node.data.params)
            idx = len(leaf_conditions)
            leaf_conditions.append(cond)
            node_meta[node_id] = {
                "node_type": "condition",
                "label": node.data.condition_type,
                "leaf_indices": [idx],
                "operator": None,
            }
            return [idx]

        if node.data.node_type == "logic":
            operator = (node.data.logic_operator or "and").lower()
            # Use child_node_ids (group container) if available
            child_ids = node.data.child_node_ids or []
            if child_ids:
                source_ids = child_ids
            else:
                source_ids = incoming.get(node_id, [])

            collected_indices: List[int] = []
            for src_id in source_ids:
                collected_indices.extend(_resolve_flat(src_id))

            node_meta[node_id] = {
                "node_type": "logic",
                "label": operator.upper(),
                "leaf_indices": collected_indices,
                "operator": operator,
            }
            return collected_indices

        if node.data.node_type == "output":
            collected_indices = []
            resolved_ids: set[str] = set()
            for src_id in incoming.get(node_id, []):
                resolved_ids.add(src_id)
                collected_indices.extend(_resolve_flat(src_id))

            # Also resolve top-level nodes not connected via edges
            for n in graph.nodes:
                if (
                    n.data.node_type in ("logic", "condition")
                    and n.id not in child_ids_set
                    and n.id not in resolved_ids
                ):
                    collected_indices.extend(_resolve_flat(n.id))

            node_meta[node_id] = {
                "node_type": "output",
                "label": "Output",
                "leaf_indices": collected_indices,
                "operator": "and",
            }
            return collected_indices

        return []

    _resolve_flat(output_node.id)

    return leaf_conditions, universe, node_meta


def _passes_node(result: Any, meta: dict) -> bool:
    """Check whether a screening result passes a given node's conditions."""
    indices = meta["leaf_indices"]
    if not indices:
        return True  # universe node or no conditions

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
    return all(r.matched for r in relevant)  # default: 'and'


def _compute_node_survivors(
    node_id: str,
    all_results: list,
    nodes_by_id: Dict[str, StrategyNode],
    incoming: Dict[str, List[str]],
    node_meta: Dict[str, dict],
    child_ids_set: set,
    cache: Dict[str, set],
) -> set:
    """Compute the set of result indices that survive up to this node.

    Unlike _passes_node() which checks each node independently,
    this function walks the graph backward so that each node's result
    reflects cumulative filtering from upstream nodes.
    """
    if node_id in cache:
        return cache[node_id]

    node = nodes_by_id.get(node_id)
    if node is None:
        cache[node_id] = set()
        return set()

    all_indices = set(range(len(all_results)))

    if node.data.node_type == "universe":
        cache[node_id] = all_indices
        return all_indices

    if node.data.node_type == "sector":
        # Tickers are already pre-filtered by sector in execute_strategy,
        # so all results pass the sector node.
        cache[node_id] = all_indices
        return all_indices

    if node.data.node_type == "condition":
        meta = node_meta.get(node_id, {})
        leaf_idx = meta.get("leaf_indices", [])
        # Stocks passing this condition alone
        own_passers = set()
        for i, r in enumerate(all_results):
            if leaf_idx and leaf_idx[0] < len(r.condition_results):
                if r.condition_results[leaf_idx[0]].matched:
                    own_passers.add(i)
        # Intersect with upstream survivors (pipeline filtering)
        upstream_ids = incoming.get(node_id, [])
        if upstream_ids:
            upstream = set.intersection(*(
                _compute_node_survivors(
                    uid, all_results, nodes_by_id, incoming,
                    node_meta, child_ids_set, cache,
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
            _compute_node_survivors(
                sid, all_results, nodes_by_id, incoming,
                node_meta, child_ids_set, cache,
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

        # If group-based, intersect with upstream edges to the group itself
        if child_ids:
            upstream_ids = [
                uid for uid in incoming.get(node_id, [])
                if uid not in set(child_ids)
            ]
            if upstream_ids:
                upstream = set.intersection(*(
                    _compute_node_survivors(
                        uid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
                    )
                    for uid in upstream_ids
                ))
                combined = combined & upstream

        cache[node_id] = combined
        return combined

    if node.data.node_type == "output":
        child_sets = []
        resolved_ids: set[str] = set()
        for sid in incoming.get(node_id, []):
            resolved_ids.add(sid)
            if nodes_by_id.get(sid) and nodes_by_id[sid].data.node_type != "universe":
                child_sets.append(
                    _compute_node_survivors(
                        sid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
                    )
                )
        # Top-level nodes not connected via edges
        for n in nodes_by_id.values():
            if (
                n.data.node_type in ("logic", "condition")
                and n.id not in child_ids_set
                and n.id not in resolved_ids
            ):
                child_sets.append(
                    _compute_node_survivors(
                        n.id, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
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


def execute_strategy_with_progress(
    graph: StrategyGraph,
    universe_override: Optional[str] = None,
    universe_overrides: Optional[List[str]] = None,
    portfolio_construction: Optional[PortfolioConstructionConfig] = None,
    ranking_config: Optional[RankingConfig] = None,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    skip_enrich: bool = False,
) -> Dict[str, Any]:
    """Execute a visual strategy graph with an optional progress callback.

    Same as execute_strategy but forwards progress_callback to the screener.
    Set skip_enrich=True when the caller will enrich separately (e.g. streaming).
    """
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

    Args:
        graph: The strategy graph
        universe_override: Override the universe from graph
        universe_overrides: Multi-universe overrides (priority over universe_override)

    Returns:
        Dict with results, counts, universe, conditions used, node_results,
        optional weighted portfolio output, and optional ranking outputs
    """
    started_at = time.perf_counter()

    # Validate sector nodes early (only 1 allowed, must be connected)
    sector_nodes = [n for n in graph.nodes if n.data.node_type == "sector"]
    if len(sector_nodes) > 1:
        raise ValueError("Only one sector node is allowed per strategy graph")
    if sector_nodes:
        sector_name_raw = (sector_nodes[0].data.sector or "").strip()
        if not sector_name_raw:
            raise ValueError("Sector node must have a sector name")
        # Only apply if sector node is reachable from the output node
        _incoming = {n.id: [] for n in graph.nodes}
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
            sector_nodes = []  # Disconnected sector node — ignore

    leaf_conditions, _, node_meta = build_flat_conditions_from_graph(graph)

    if not leaf_conditions:
        raise ValueError("No conditions found in graph")

    screening_service = ScreeningService()
    resolve_started_at = time.perf_counter()
    resolved_universes, primary_universe = _resolve_execution_universes(
        graph=graph,
        screening_service=screening_service,
        universe_override=universe_override,
        universe_overrides=universe_overrides,
    )
    resolve_elapsed_ms = (time.perf_counter() - resolve_started_at) * 1000.0

    fetch_started_at = time.perf_counter()
    tickers = screening_service.get_tickers_for_universes(
        universe_input=resolved_universes,
        fail_fast=False,
    )
    fetch_elapsed_ms = (time.perf_counter() - fetch_started_at) * 1000.0
    total_count = len(tickers)

    if total_count > WARN_TICKERS_THRESHOLD:
        logger.warning(
            "strategy.guardrail warning: universe_size=%d exceeds warn threshold=%d",
            total_count,
            WARN_TICKERS_THRESHOLD,
        )
    if total_count > MAX_TICKERS_PER_RUN:
        raise ValueError(
            f"Target universe too large ({total_count}). Maximum allowed per run is {MAX_TICKERS_PER_RUN}"
        )

    # Apply sector filtering (already validated above)
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

        # Policy: apply sector filter only to KR tickers; keep non-KR tickers unchanged.
        tickers = [
            ticker for ticker in tickers
            if (not _is_korean_ticker(ticker)) or (ticker in sector_tickers)
        ]
        logger.info(
            "Sector filter '%s' on KR universes %s: %d -> %d tickers",
            sector_name,
            ",".join(kr_universes),
            total_count,
            len(tickers),
        )

    # Create screener with flat leaf conditions and run with return_all=True
    screener = StockScreener(
        conditions=leaf_conditions,
        max_workers=5,
        use_full_universe=True,
        use_cache=True,
    )

    eval_started_at = time.perf_counter()
    all_results = screener.run(
        tickers=tickers,
        show_progress=False,
        return_all=True,
        progress_callback=progress_callback,
    )
    eval_elapsed_ms = (time.perf_counter() - eval_started_at) * 1000.0

    # Rebuild graph structures for survivor computation
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)
    child_ids_set: set[str] = set()
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)

    # Compute per-node survivors using graph-aware cumulative filtering
    survivor_cache: Dict[str, set] = {}
    node_results: Dict[str, NodeIntermediateResult] = {}
    output_node_id = None

    for node_id, meta in node_meta.items():
        if meta["node_type"] == "output":
            output_node_id = node_id

        survivor_indices = _compute_node_survivors(
            node_id, all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, survivor_cache,
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

    # Final results are the stocks that survive the output node
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
                        matched=result.matched,
                        conditions=cond_details,
                    )
                )

    # Enrich only final results (intermediate nodes don't display PER/PBR).
    # skip_enrich=True lets streaming callers send progress before enriching.
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
    eval_throughput = (len(tickers) / eval_elapsed_ms * 1000.0) if eval_elapsed_ms > 0 else float(len(tickers))
    logger.info(
        (
            "strategy.metrics universes=%s total_tickers=%d screened=%d matched=%d "
            "resolve_ms=%.1f fetch_ms=%.1f eval_ms=%.1f total_ms=%.1f eval_tps=%.2f"
        ),
        ",".join(resolved_universes),
        total_count,
        len(tickers),
        len(final_items),
        resolve_elapsed_ms,
        fetch_elapsed_ms,
        eval_elapsed_ms,
        total_elapsed_ms,
        eval_throughput,
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
