"""
Pairs Trading Conditions
team:quant 페어 트레이딩 조건

Conditions that evaluate two tickers simultaneously for
correlation, spread z-score, and cointegration signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import PairsCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str, reason: str = "Insufficient data") -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": reason})


def _align_close(
    data1: pd.DataFrame, data2: pd.DataFrame, min_overlap: int
) -> tuple[pd.Series, pd.Series] | None:
    """Extract aligned close price series from two DataFrames.

    Returns None if overlap is less than *min_overlap* rows.
    """
    c1 = data1["close"].dropna()
    c2 = data2["close"].dropna()
    common = c1.index.intersection(c2.index)
    if len(common) < min_overlap:
        return None
    return c1.loc[common].astype(float), c2.loc[common].astype(float)


# ---------------------------------------------------------------------------
# 1. Correlation Condition
# ---------------------------------------------------------------------------

@register_condition(
    key="pair_correlation",
    label="Pair Correlation",
    description="Rolling Pearson correlation between two tickers",
    category="pairs",
    params=[
        {"name": "ticker2", "type": "ticker", "default": "", "description": "Companion ticker"},
        {"name": "period", "type": "int", "default": 60, "description": "Rolling window (days)"},
        {"name": "min_correlation", "type": "float", "default": 0.7, "description": "Minimum correlation"},
    ],
    is_pairs=True,
)
class PairCorrelationCondition(PairsCondition):
    def __init__(self, ticker2: str = "", period: int = 60, min_correlation: float = 0.7):
        self._ticker2 = ticker2
        self.period = period
        self.min_correlation = min_correlation

    @property
    def name(self) -> str:
        return "pair_correlation"

    @property
    def required_days(self) -> int:
        return self.period + 20

    def evaluate_pair(
        self, ticker1: str, data1: pd.DataFrame, ticker2: str, data2: pd.DataFrame,
    ) -> ConditionResult:
        aligned = _align_close(data1, data2, self.period)
        if aligned is None:
            return _insufficient(self.name, f"Need {self.period} overlapping days")

        c1, c2 = aligned
        corr = c1.tail(self.period).corr(c2.tail(self.period))

        if np.isnan(corr):
            return _insufficient(self.name, "Correlation is NaN")

        matched = corr >= self.min_correlation
        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "ticker1": ticker1,
                "ticker2": ticker2,
                "correlation": round(float(corr), 4),
                "min_correlation": self.min_correlation,
                "period": self.period,
            },
        )


# ---------------------------------------------------------------------------
# 2. Spread Z-Score Condition
# ---------------------------------------------------------------------------

@register_condition(
    key="pair_spread_zscore",
    label="Spread Z-Score",
    description="Log spread z-score for mean-reversion entry/exit",
    category="pairs",
    params=[
        {"name": "ticker2", "type": "ticker", "default": "", "description": "Companion ticker"},
        {"name": "period", "type": "int", "default": 60, "description": "Lookback window (days)"},
        {"name": "zscore_entry", "type": "float", "default": 2.0, "description": "Z-score entry threshold"},
        {"name": "direction", "type": "str", "default": "long_spread", "description": "long_spread or short_spread"},
    ],
    is_pairs=True,
)
class PairSpreadZScoreCondition(PairsCondition):
    def __init__(
        self,
        ticker2: str = "",
        period: int = 60,
        zscore_entry: float = 2.0,
        direction: str = "long_spread",
    ):
        self._ticker2 = ticker2
        self.period = period
        self.zscore_entry = zscore_entry
        self.direction = direction

    @property
    def name(self) -> str:
        return "pair_spread_zscore"

    @property
    def required_days(self) -> int:
        return self.period + 20

    def evaluate_pair(
        self, ticker1: str, data1: pd.DataFrame, ticker2: str, data2: pd.DataFrame,
    ) -> ConditionResult:
        aligned = _align_close(data1, data2, self.period)
        if aligned is None:
            return _insufficient(self.name, f"Need {self.period} overlapping days")

        c1, c2 = aligned
        # Log spread: log(price_A) - log(price_B)
        spread = np.log(c1) - np.log(c2)
        window = spread.tail(self.period)

        mean = window.mean()
        std = window.std()
        if std == 0 or np.isnan(std):
            return _insufficient(self.name, "Spread has zero variance")

        current_z = (spread.iloc[-1] - mean) / std

        if self.direction == "long_spread":
            matched = current_z <= -self.zscore_entry
        else:
            matched = current_z >= self.zscore_entry

        return ConditionResult(
            matched=bool(matched),
            condition_name=self.name,
            details={
                "ticker1": ticker1,
                "ticker2": ticker2,
                "zscore": round(float(current_z), 4),
                "zscore_entry": self.zscore_entry,
                "direction": self.direction,
                "spread_mean": round(float(mean), 4),
                "spread_std": round(float(std), 4),
            },
        )


# ---------------------------------------------------------------------------
# 3. Cointegration Condition (Engle-Granger)
# ---------------------------------------------------------------------------

@register_condition(
    key="pair_cointegration",
    label="Cointegration Test",
    description="Engle-Granger cointegration test between two tickers",
    category="pairs",
    params=[
        {"name": "ticker2", "type": "ticker", "default": "", "description": "Companion ticker"},
        {"name": "period", "type": "int", "default": 252, "description": "Lookback window (days)"},
        {"name": "pvalue_threshold", "type": "float", "default": 0.05, "description": "Max p-value"},
    ],
    is_pairs=True,
)
class PairCointegrationCondition(PairsCondition):
    def __init__(self, ticker2: str = "", period: int = 252, pvalue_threshold: float = 0.05):
        self._ticker2 = ticker2
        self.period = period
        self.pvalue_threshold = pvalue_threshold

    @property
    def name(self) -> str:
        return "pair_cointegration"

    @property
    def required_days(self) -> int:
        return self.period + 20

    def evaluate_pair(
        self, ticker1: str, data1: pd.DataFrame, ticker2: str, data2: pd.DataFrame,
    ) -> ConditionResult:
        aligned = _align_close(data1, data2, self.period)
        if aligned is None:
            return _insufficient(self.name, f"Need {self.period} overlapping days")

        c1, c2 = aligned
        c1_arr = c1.tail(self.period).values
        c2_arr = c2.tail(self.period).values

        # Engle-Granger: OLS regression then ADF test on residuals
        try:
            pvalue = self._engle_granger_pvalue(c1_arr, c2_arr)
        except Exception:
            return _insufficient(self.name, "Cointegration test failed")

        matched = pvalue < self.pvalue_threshold
        return ConditionResult(
            matched=bool(matched),
            condition_name=self.name,
            details={
                "ticker1": ticker1,
                "ticker2": ticker2,
                "pvalue": round(float(pvalue), 4),
                "pvalue_threshold": self.pvalue_threshold,
                "period": self.period,
            },
        )

    @staticmethod
    def _engle_granger_pvalue(y: np.ndarray, x: np.ndarray) -> float:
        """Simplified Engle-Granger test without statsmodels dependency.

        Runs OLS regression y = a + b*x, then ADF(residuals).
        Uses Dickey-Fuller critical values approximation for p-value.
        """
        n = len(y)
        # OLS: y = a + b*x
        x_mean = x.mean()
        y_mean = y.mean()
        b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
        a = y_mean - b * x_mean
        residuals = y - (a + b * x)

        # ADF test on residuals (no trend, lag=1)
        dr = np.diff(residuals)
        r_lag = residuals[:-1]

        if len(dr) < 3:
            return 1.0

        # OLS: dr = gamma * r_lag + epsilon
        gamma = np.sum(dr * r_lag) / np.sum(r_lag ** 2)
        eps = dr - gamma * r_lag
        se_gamma = np.sqrt(np.sum(eps ** 2) / (len(eps) - 1) / np.sum(r_lag ** 2))

        if se_gamma == 0:
            return 1.0

        adf_stat = gamma / se_gamma

        # Approximate p-value from MacKinnon critical values (n=2, no trend)
        # -3.90 → 1%, -3.34 → 5%, -3.04 → 10%
        if adf_stat < -3.90:
            return 0.005
        elif adf_stat < -3.34:
            return 0.03
        elif adf_stat < -3.04:
            return 0.07
        elif adf_stat < -2.58:
            return 0.15
        else:
            return 0.5
