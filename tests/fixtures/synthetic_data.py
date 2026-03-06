"""
Synthetic data factory for condition testing.

Provides deterministic DataFrame builders with various shapes
(uptrend, downtrend, flat, volume_spike, etc.) and column profiles
(price_only, price_volume, fundamental, etc.).

All functions use fixed random seeds for reproducibility.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Column profiles
# ---------------------------------------------------------------------------

_FUNDAMENTAL_DEFAULTS: dict[str, float] = {
    "pe_ratio": 15.0,
    "pb_ratio": 1.5,
    "ps_ratio": 2.0,
    "pcf_ratio": 10.0,
    "market_cap": 1e11,
    "dividend_yield": 0.02,
    "earnings_yield": 0.07,
    "ebit_ev": 0.08,
    "fcf_yield": 0.05,
    "peg_ratio": 1.2,
    "debt_to_equity": 0.5,
    "current_ratio": 2.0,
    "roe": 0.15,
    "roic": 0.12,
    "roa": 0.08,
    "net_margin": 0.10,
    "gross_margin": 0.40,
    "operating_margin": 0.15,
    "free_cash_flow_margin": 0.08,
    "payout_ratio": 0.30,
    "price_to_tangible_book": 2.0,
    "ev_to_sales": 3.0,
    "ev_to_ebitda": 12.0,
    "book_to_market": 0.5,
    "eps_cagr_3y": 0.10,
    "eps_growth_yoy": 0.15,
    "revenue_cagr_3y": 0.08,
    "revenue_growth_yoy": 0.12,
    "revenue_stability": 0.85,
    "earnings_stability": 0.80,
    "debt_service_coverage": 2.5,
    "net_debt_to_ebitda": 1.5,
    "interest_coverage": 8.0,
    "cash_conversion": 0.90,
    "roce": 0.14,
    "receivables_turnover": 8.0,
    "inventory_turnover": 6.0,
    "asset_turnover": 0.8,
    "cashflow_to_debt": 0.35,
    "dividend_growth_5y": 0.05,
    "shareholder_yield": 0.04,
    "net_share_issuance": -0.01,
    "buyback_yield": 0.02,
    "insider_net_buying": 0.005,
    "short_float_pct": 0.05,
    "short_interest_ratio": 3.0,
    "earnings_surprise": 0.05,
    "accruals_ratio": -0.03,
    "asset_growth_rate": 0.08,
    "gross_profitability": 0.30,
    "quality_score": 0.75,
    "shares_outstanding": 1e9,
}


def _add_ohlcv(df: pd.DataFrame, close: np.ndarray, volume: np.ndarray | None = None) -> pd.DataFrame:
    """Populate OHLCV columns from close array."""
    n = len(close)
    rng = np.random.RandomState(42)
    df["close"] = close
    df["open"] = close * (1 + rng.uniform(-0.005, 0.005, n))
    df["high"] = np.maximum(df["open"], close) * (1 + rng.uniform(0, 0.02, n))
    df["low"] = np.minimum(df["open"], close) * (1 - rng.uniform(0, 0.02, n))
    if volume is not None:
        df["volume"] = volume
    else:
        df["volume"] = rng.randint(500_000, 5_000_000, n).astype(float)
    return df


def _make_index(days: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-02", periods=days, freq="B")


# ---------------------------------------------------------------------------
# Shape builders — return (close, volume_or_None)
# ---------------------------------------------------------------------------

def _random_walk(days: int, start: float = 100.0, daily_pct: float = 0.01, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    returns = rng.normal(0, daily_pct, days)
    prices = start * np.cumprod(1 + returns)
    return np.maximum(prices, 0.01)


def _uptrend(days: int, start: float = 50.0, daily_gain: float = 0.02) -> np.ndarray:
    return start * np.cumprod(np.full(days, 1 + daily_gain))


def _downtrend(days: int, start: float = 200.0, daily_loss: float = 0.02) -> np.ndarray:
    return start * np.cumprod(np.full(days, 1 - daily_loss))


def _flat(days: int, price: float = 100.0, noise: float = 0.001, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return price * (1 + rng.normal(0, noise, days))


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def build_fixture(
    shape: str = "random_walk",
    days: int = 200,
    profile: str = "price_volume",
    seed: int = 42,
) -> pd.DataFrame:
    """Build a synthetic DataFrame for condition testing.

    Parameters
    ----------
    shape : str
        One of: random_walk, strong_uptrend, strong_downtrend,
        flat, volume_spike, gap_up, v_recovery.
    days : int
        Number of trading days.
    profile : str
        Column set: price_only, price_volume, price_volume_shares, fundamental.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame with DatetimeIndex and requested columns.
    """
    idx = _make_index(days)
    df = pd.DataFrame(index=idx)
    volume = None

    if shape == "random_walk":
        close = _random_walk(days, seed=seed)
    elif shape == "strong_uptrend":
        close = _uptrend(days)
    elif shape == "strong_downtrend":
        close = _downtrend(days)
    elif shape == "flat":
        close = _flat(days, seed=seed)
    elif shape == "volume_spike":
        close = _random_walk(days, seed=seed)
        rng = np.random.RandomState(seed)
        vol = rng.randint(500_000, 2_000_000, days).astype(float)
        # Last 20 days: 5x spike
        vol[-20:] *= 5
        volume = vol
    elif shape == "gap_up":
        close = _flat(days, seed=seed)
        # Insert 10% gap at day 100
        close[100:] *= 1.10
    elif shape == "v_recovery":
        half = days // 2
        down = _downtrend(half, start=200.0, daily_loss=0.015)
        up = _uptrend(days - half, start=down[-1], daily_gain=0.015)
        close = np.concatenate([down, up])
    else:
        raise ValueError(f"Unknown shape: {shape}")

    _add_ohlcv(df, close, volume)

    # Add columns based on profile
    if profile in ("price_volume_shares", "fundamental"):
        df["shares_outstanding"] = _FUNDAMENTAL_DEFAULTS["shares_outstanding"]

    if profile == "fundamental":
        for col, val in _FUNDAMENTAL_DEFAULTS.items():
            if col not in df.columns:
                df[col] = val

    return df
