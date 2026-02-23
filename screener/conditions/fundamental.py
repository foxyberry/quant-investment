"""
Fundamental Conditions
펀더멘털 기반 스크리닝 조건

These conditions use yfinance fundamental data (Ticker.info, financial statements)
rather than OHLCV price data. A module-level cache avoids redundant API calls
when multiple fundamental conditions are evaluated for the same ticker in a
single screening run.

Usage:
    from screener.conditions.fundamental import (
        PERatioCondition, PBRatioCondition, PSRatioCondition, PCFRatioCondition,
        DividendYieldCondition, EarningsYieldCondition, EbitEvCondition,
        FcfYieldCondition, PegRatioCondition, DebtToEquityCondition,
        CurrentRatioCondition, RoeCondition, PiotroskiFScoreCondition,
        AltmanZScoreCondition, RoicCondition, clear_info_cache,
    )
"""

from io import StringIO
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from utils.fundamental_cache import FundamentalCache
from .base import BaseCondition, ConditionResult
from .registry import register_condition

# ---------------------------------------------------------------------------
# Module-level cache for yfinance .info dictionaries
# ---------------------------------------------------------------------------

_info_cache: Dict[str, Dict[str, Any]] = {}
_statement_cache: Dict[str, Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
_persistent_cache = FundamentalCache()

INFO_TTL_SECONDS = 24 * 60 * 60
STATEMENT_TTL_SECONDS = 7 * 24 * 60 * 60

_INFO_CACHE_MAXSIZE = 500
_STATEMENT_CACHE_MAXSIZE = 200
_EVICTION_BATCH = 100


def _evict_cache(cache: dict, maxsize: int, batch: int = _EVICTION_BATCH) -> None:
    """Remove oldest entries (FIFO) when cache exceeds maxsize."""
    if len(cache) > maxsize:
        keys_to_remove = list(cache.keys())[:batch]
        for key in keys_to_remove:
            cache.pop(key, None)


def _df_to_json_payload(df: pd.DataFrame) -> str:
    return df.to_json(orient="split", date_format="iso")


def _df_from_json_payload(payload: str) -> pd.DataFrame:
    return pd.read_json(StringIO(payload), orient="split")


def _get_info(ticker: str) -> dict:
    """Fetch and cache the yfinance info dict for *ticker*.

    Returns an empty dict when the API call yields ``None``.
    Uses per-key locking to prevent thundering herd on the same ticker.
    """
    if ticker in _info_cache:
        return _info_cache[ticker]

    lock = _persistent_cache._get_key_lock("yf_info", ticker)
    with lock:
        # Double-check after acquiring lock
        if ticker in _info_cache:
            return _info_cache[ticker]

        cached = _persistent_cache.get("yf_info", ticker, INFO_TTL_SECONDS)
        if cached is not None:
            _info_cache[ticker] = cached
            return _info_cache[ticker]

        info = yf.Ticker(ticker).info or {}
        _info_cache[ticker] = info
        _evict_cache(_info_cache, _INFO_CACHE_MAXSIZE)
        _persistent_cache.set("yf_info", ticker, info)
        return _info_cache[ticker]


def _get_financial_statements(ticker: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch and cache income/balance/cashflow statements for ticker.

    Uses per-key locking to prevent thundering herd on the same ticker.
    """
    if ticker in _statement_cache:
        return _statement_cache[ticker]

    lock = _persistent_cache._get_key_lock("yf_statements", ticker)
    with lock:
        # Double-check after acquiring lock
        if ticker in _statement_cache:
            return _statement_cache[ticker]

        cached = _persistent_cache.get("yf_statements", ticker, STATEMENT_TTL_SECONDS)
        if cached is not None:
            income_raw = cached.get("income_stmt")
            balance_raw = cached.get("balance_sheet")
            cashflow_raw = cached.get("cashflow")
            if income_raw and balance_raw and cashflow_raw:
                try:
                    bundle = (
                        _df_from_json_payload(income_raw),
                        _df_from_json_payload(balance_raw),
                        _df_from_json_payload(cashflow_raw),
                    )
                    _statement_cache[ticker] = bundle
                    return bundle
                except Exception:
                    pass

        t = yf.Ticker(ticker)
        income = t.income_stmt
        balance = t.balance_sheet
        cashflow = t.cashflow

        _statement_cache[ticker] = (income, balance, cashflow)
        _evict_cache(_statement_cache, _STATEMENT_CACHE_MAXSIZE)
        try:
            _persistent_cache.set(
                "yf_statements",
                ticker,
                {
                    "income_stmt": _df_to_json_payload(income),
                    "balance_sheet": _df_to_json_payload(balance),
                    "cashflow": _df_to_json_payload(cashflow),
                },
            )
        except Exception:
            # Non-critical: keep in-memory cache even if persistence fails.
            pass

        return _statement_cache[ticker]


def clear_info_cache(include_persistent: bool = False) -> None:
    """Clear in-memory caches used by fundamental conditions.

    Args:
        include_persistent: When True, also clear on-disk persistent cache
            for yfinance info/statements.
    """
    _info_cache.clear()
    _statement_cache.clear()
    if include_persistent:
        _persistent_cache.clear(namespace="yf_info")
        _persistent_cache.clear(namespace="yf_statements")


# ---------------------------------------------------------------------------
# Helper – range check used by every condition
# ---------------------------------------------------------------------------

def _in_range(
    value: float,
    lo: Optional[float],
    hi: Optional[float],
) -> bool:
    """Return True when *value* is within [lo, hi].

    ``None`` on either bound means that side is unbounded.
    """
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


# ===================================================================
# 1. PERatioCondition
# ===================================================================

@register_condition(
    key="pe_ratio",
    label="P/E Ratio",
    description="Price-to-Earnings ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_pe", "type": "float", "default": None, "description": "Min P/E"},
        {"name": "max_pe", "type": "float", "default": 15.0, "description": "Max P/E"},
    ],
)
class PERatioCondition(BaseCondition):
    """Price-to-Earnings (trailing P/E) screening condition.

    Excludes tickers with negative or zero trailing P/E (no valid earnings).
    """

    def __init__(
        self,
        min_pe: Optional[float] = None,
        max_pe: Optional[float] = 15.0,
    ):
        """
        Args:
            min_pe: Minimum acceptable trailing P/E (inclusive). None = no lower bound.
            max_pe: Maximum acceptable trailing P/E (inclusive). None = no upper bound.
        """
        self.min_pe = min_pe
        self.max_pe = max_pe

    @property
    def name(self) -> str:
        return f"pe_ratio_max{self.max_pe}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        pe = info.get("trailingPE")

        if pe is None or pe <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No valid P/E data"},
            )

        matched = _in_range(pe, self.min_pe, self.max_pe)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "pe_ratio": float(pe),
                "min_pe": self.min_pe,
                "max_pe": self.max_pe,
            },
        )

    def __repr__(self) -> str:
        return f"PERatioCondition(min_pe={self.min_pe}, max_pe={self.max_pe})"


# ===================================================================
# 2. PBRatioCondition
# ===================================================================

@register_condition(
    key="pb_ratio",
    label="P/B Ratio",
    description="Price-to-Book ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_pb", "type": "float", "default": None, "description": "Min P/B"},
        {"name": "max_pb", "type": "float", "default": 1.5, "description": "Max P/B"},
        {"name": "exclude_negative_bv", "type": "bool", "default": True, "description": "Exclude negative book value"},
    ],
)
class PBRatioCondition(BaseCondition):
    """Price-to-Book screening condition.

    Optionally excludes tickers with negative book value.
    """

    def __init__(
        self,
        min_pb: Optional[float] = None,
        max_pb: Optional[float] = 1.5,
        exclude_negative_bv: bool = True,
    ):
        """
        Args:
            min_pb: Minimum acceptable P/B (inclusive).
            max_pb: Maximum acceptable P/B (inclusive).
            exclude_negative_bv: If True, exclude tickers with priceToBook < 0.
        """
        self.min_pb = min_pb
        self.max_pb = max_pb
        self.exclude_negative_bv = exclude_negative_bv

    @property
    def name(self) -> str:
        return f"pb_ratio_max{self.max_pb}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        pb = info.get("priceToBook")

        if pb is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No valid P/B data"},
            )

        if self.exclude_negative_bv and pb < 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative book value", "pb_ratio": float(pb)},
            )

        matched = _in_range(pb, self.min_pb, self.max_pb)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "pb_ratio": float(pb),
                "min_pb": self.min_pb,
                "max_pb": self.max_pb,
            },
        )

    def __repr__(self) -> str:
        return (
            f"PBRatioCondition(min_pb={self.min_pb}, max_pb={self.max_pb}, "
            f"exclude_negative_bv={self.exclude_negative_bv})"
        )


# ===================================================================
# 3. PSRatioCondition
# ===================================================================

@register_condition(
    key="ps_ratio",
    label="P/S Ratio",
    description="Price-to-Sales ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_ps", "type": "float", "default": None, "description": "Min P/S"},
        {"name": "max_ps", "type": "float", "default": 2.0, "description": "Max P/S"},
    ],
)
class PSRatioCondition(BaseCondition):
    """Price-to-Sales (trailing 12 months) screening condition."""

    def __init__(
        self,
        min_ps: Optional[float] = None,
        max_ps: Optional[float] = 2.0,
    ):
        """
        Args:
            min_ps: Minimum acceptable P/S (inclusive).
            max_ps: Maximum acceptable P/S (inclusive).
        """
        self.min_ps = min_ps
        self.max_ps = max_ps

    @property
    def name(self) -> str:
        return f"ps_ratio_max{self.max_ps}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        ps = info.get("priceToSalesTrailing12Months")

        if ps is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No valid P/S data"},
            )

        matched = _in_range(ps, self.min_ps, self.max_ps)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "ps_ratio": float(ps),
                "min_ps": self.min_ps,
                "max_ps": self.max_ps,
            },
        )

    def __repr__(self) -> str:
        return f"PSRatioCondition(min_ps={self.min_ps}, max_ps={self.max_ps})"


# ===================================================================
# 4. PCFRatioCondition
# ===================================================================

@register_condition(
    key="pcf_ratio",
    label="P/CF Ratio",
    description="Price-to-Cash-Flow ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_pcf", "type": "float", "default": None, "description": "Min P/CF"},
        {"name": "max_pcf", "type": "float", "default": 10.0, "description": "Max P/CF"},
    ],
)
class PCFRatioCondition(BaseCondition):
    """Price-to-Cash-Flow screening condition.

    Calculated as ``currentPrice / (operatingCashflow / sharesOutstanding)``.
    Excludes tickers with negative operating cash flow.
    """

    def __init__(
        self,
        min_pcf: Optional[float] = None,
        max_pcf: Optional[float] = 10.0,
    ):
        """
        Args:
            min_pcf: Minimum acceptable P/CF (inclusive).
            max_pcf: Maximum acceptable P/CF (inclusive).
        """
        self.min_pcf = min_pcf
        self.max_pcf = max_pcf

    @property
    def name(self) -> str:
        return f"pcf_ratio_max{self.max_pcf}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)

        price = info.get("currentPrice")
        ocf = info.get("operatingCashflow")
        shares = info.get("sharesOutstanding")

        if price is None or ocf is None or shares is None or shares == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Missing data for P/CF calculation"},
            )

        if ocf <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative operating cash flow"},
            )

        pcf = price / (ocf / shares)
        matched = _in_range(pcf, self.min_pcf, self.max_pcf)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "pcf_ratio": float(pcf),
                "min_pcf": self.min_pcf,
                "max_pcf": self.max_pcf,
            },
        )

    def __repr__(self) -> str:
        return f"PCFRatioCondition(min_pcf={self.min_pcf}, max_pcf={self.max_pcf})"


# ===================================================================
# 5. DividendYieldCondition
# ===================================================================

@register_condition(
    key="dividend_yield",
    label="Dividend Yield",
    description="Dividend yield percentage filter",
    category="Fundamental",
    params=[
        {"name": "min_yield", "type": "float", "default": 3.0, "description": "Min yield %"},
        {"name": "max_yield", "type": "float", "default": None, "description": "Max yield %"},
    ],
)
class DividendYieldCondition(BaseCondition):
    """Dividend yield screening condition.

    yfinance reports ``dividendYield`` as a decimal (e.g. 0.03 = 3%).
    Thresholds and reported details use *percentage* units.
    """

    def __init__(
        self,
        min_yield: Optional[float] = 3.0,
        max_yield: Optional[float] = None,
    ):
        """
        Args:
            min_yield: Minimum dividend yield in % (inclusive).
            max_yield: Maximum dividend yield in % (inclusive).
        """
        self.min_yield = min_yield
        self.max_yield = max_yield

    @property
    def name(self) -> str:
        return f"dividend_yield_min{self.min_yield}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        raw = info.get("dividendYield")

        if raw is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No dividend yield data"},
            )

        yield_pct = raw * 100.0
        matched = _in_range(yield_pct, self.min_yield, self.max_yield)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "dividend_yield_pct": float(yield_pct),
                "min_yield": self.min_yield,
                "max_yield": self.max_yield,
            },
        )

    def __repr__(self) -> str:
        return f"DividendYieldCondition(min_yield={self.min_yield}%, max_yield={self.max_yield}%)"


# ===================================================================
# 6. EarningsYieldCondition
# ===================================================================

@register_condition(
    key="earnings_yield",
    label="Earnings Yield",
    description="Earnings yield (E/P) percentage filter",
    category="Fundamental",
    params=[
        {"name": "min_yield", "type": "float", "default": 8.0, "description": "Min yield %"},
        {"name": "max_yield", "type": "float", "default": None, "description": "Max yield %"},
    ],
)
class EarningsYieldCondition(BaseCondition):
    """Earnings yield screening condition.

    Calculated as ``trailingEps / currentPrice * 100``.
    Excludes tickers with negative earnings.
    """

    def __init__(
        self,
        min_yield: Optional[float] = 8.0,
        max_yield: Optional[float] = None,
    ):
        """
        Args:
            min_yield: Minimum earnings yield in % (inclusive).
            max_yield: Maximum earnings yield in % (inclusive).
        """
        self.min_yield = min_yield
        self.max_yield = max_yield

    @property
    def name(self) -> str:
        return f"earnings_yield_min{self.min_yield}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        eps = info.get("trailingEps")
        price = info.get("currentPrice")

        if eps is None or price is None or price == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Missing EPS or price data"},
            )

        if eps <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative earnings"},
            )

        earnings_yield = eps / price * 100.0
        matched = _in_range(earnings_yield, self.min_yield, self.max_yield)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "earnings_yield_pct": float(earnings_yield),
                "trailing_eps": float(eps),
                "current_price": float(price),
                "min_yield": self.min_yield,
                "max_yield": self.max_yield,
            },
        )

    def __repr__(self) -> str:
        return f"EarningsYieldCondition(min_yield={self.min_yield}%, max_yield={self.max_yield}%)"


# ===================================================================
# 7. EbitEvCondition
# ===================================================================

@register_condition(
    key="ebit_ev",
    label="EBIT/EV",
    description="EBIT / Enterprise Value yield filter",
    category="Fundamental",
    params=[
        {"name": "min_ebit_ev", "type": "float", "default": 10.0, "description": "Min EBIT/EV %"},
        {"name": "max_ebit_ev", "type": "float", "default": None, "description": "Max EBIT/EV %"},
    ],
)
class EbitEvCondition(BaseCondition):
    """EBIT / Enterprise Value yield screening condition.

    Calculated as ``ebitda / enterpriseValue * 100`` (using EBIT from info).
    Excludes tickers with negative EBIT or non-positive enterprise value.

    Note: yfinance .info exposes ``ebitda`` but not a separate ``ebit`` field
    consistently. We use the ``ebit`` key when available and fall back to
    ``ebitda`` when it is not.
    """

    def __init__(
        self,
        min_ebit_ev: Optional[float] = 10.0,
        max_ebit_ev: Optional[float] = None,
    ):
        """
        Args:
            min_ebit_ev: Minimum EBIT/EV in % (inclusive).
            max_ebit_ev: Maximum EBIT/EV in % (inclusive).
        """
        self.min_ebit_ev = min_ebit_ev
        self.max_ebit_ev = max_ebit_ev

    @property
    def name(self) -> str:
        return f"ebit_ev_min{self.min_ebit_ev}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)

        # Prefer explicit EBIT; fall back to EBITDA
        ebit = info.get("ebit") or info.get("ebitda")
        ev = info.get("enterpriseValue")

        if ebit is None or ev is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Missing EBIT or EV data"},
            )

        if ebit <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative EBIT"},
            )

        if ev <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Non-positive enterprise value"},
            )

        ebit_ev_pct = ebit / ev * 100.0
        matched = _in_range(ebit_ev_pct, self.min_ebit_ev, self.max_ebit_ev)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "ebit_ev_pct": float(ebit_ev_pct),
                "ebit": float(ebit),
                "enterprise_value": float(ev),
                "min_ebit_ev": self.min_ebit_ev,
                "max_ebit_ev": self.max_ebit_ev,
            },
        )

    def __repr__(self) -> str:
        return f"EbitEvCondition(min_ebit_ev={self.min_ebit_ev}%, max_ebit_ev={self.max_ebit_ev}%)"


# ===================================================================
# 8. FcfYieldCondition
# ===================================================================

@register_condition(
    key="fcf_yield",
    label="FCF Yield",
    description="Free Cash Flow yield filter",
    category="Fundamental",
    params=[
        {"name": "min_fcf_yield", "type": "float", "default": 5.0, "description": "Min FCF yield %"},
        {"name": "max_fcf_yield", "type": "float", "default": None, "description": "Max FCF yield %"},
    ],
)
class FcfYieldCondition(BaseCondition):
    """Free Cash Flow yield screening condition.

    Calculated as ``freeCashflow / marketCap * 100``.
    Excludes tickers with negative FCF.
    """

    def __init__(
        self,
        min_fcf_yield: Optional[float] = 5.0,
        max_fcf_yield: Optional[float] = None,
    ):
        """
        Args:
            min_fcf_yield: Minimum FCF yield in % (inclusive).
            max_fcf_yield: Maximum FCF yield in % (inclusive).
        """
        self.min_fcf_yield = min_fcf_yield
        self.max_fcf_yield = max_fcf_yield

    @property
    def name(self) -> str:
        return f"fcf_yield_min{self.min_fcf_yield}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        fcf = info.get("freeCashflow")
        mcap = info.get("marketCap")

        if fcf is None or mcap is None or mcap == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Missing FCF or market cap data"},
            )

        if fcf <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative free cash flow"},
            )

        fcf_yield_pct = fcf / mcap * 100.0
        matched = _in_range(fcf_yield_pct, self.min_fcf_yield, self.max_fcf_yield)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "fcf_yield_pct": float(fcf_yield_pct),
                "free_cashflow": float(fcf),
                "market_cap": float(mcap),
                "min_fcf_yield": self.min_fcf_yield,
                "max_fcf_yield": self.max_fcf_yield,
            },
        )

    def __repr__(self) -> str:
        return f"FcfYieldCondition(min_fcf_yield={self.min_fcf_yield}%, max_fcf_yield={self.max_fcf_yield}%)"


# ===================================================================
# 9. PegRatioCondition
# ===================================================================

@register_condition(
    key="peg_ratio",
    label="PEG Ratio",
    description="Price/Earnings-to-Growth ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_peg", "type": "float", "default": None, "description": "Min PEG"},
        {"name": "max_peg", "type": "float", "default": 1.0, "description": "Max PEG"},
    ],
)
class PegRatioCondition(BaseCondition):
    """PEG ratio screening condition.

    Excludes tickers with negative PEG (implies negative earnings growth).
    """

    def __init__(
        self,
        min_peg: Optional[float] = None,
        max_peg: Optional[float] = 1.0,
    ):
        """
        Args:
            min_peg: Minimum acceptable PEG (inclusive).
            max_peg: Maximum acceptable PEG (inclusive).
        """
        self.min_peg = min_peg
        self.max_peg = max_peg

    @property
    def name(self) -> str:
        return f"peg_ratio_max{self.max_peg}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        peg = info.get("pegRatio")

        if peg is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No PEG ratio data"},
            )

        if peg < 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative PEG (negative growth)", "peg_ratio": float(peg)},
            )

        matched = _in_range(peg, self.min_peg, self.max_peg)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "peg_ratio": float(peg),
                "min_peg": self.min_peg,
                "max_peg": self.max_peg,
            },
        )

    def __repr__(self) -> str:
        return f"PegRatioCondition(min_peg={self.min_peg}, max_peg={self.max_peg})"


# ===================================================================
# 10. DebtToEquityCondition
# ===================================================================

@register_condition(
    key="debt_to_equity",
    label="D/E Ratio",
    description="Debt-to-Equity ratio filter",
    category="Fundamental",
    params=[
        {"name": "min_de", "type": "float", "default": None, "description": "Min D/E %"},
        {"name": "max_de", "type": "float", "default": 100.0, "description": "Max D/E %"},
    ],
)
class DebtToEquityCondition(BaseCondition):
    """Debt-to-Equity ratio screening condition.

    yfinance returns ``debtToEquity`` as a percentage value (e.g. 50 = 50%).
    Excludes tickers with negative D/E (negative equity).
    """

    def __init__(
        self,
        min_de: Optional[float] = None,
        max_de: Optional[float] = 100.0,
    ):
        """
        Args:
            min_de: Minimum acceptable D/E in % (inclusive).
            max_de: Maximum acceptable D/E in % (inclusive).
        """
        self.min_de = min_de
        self.max_de = max_de

    @property
    def name(self) -> str:
        return f"debt_to_equity_max{self.max_de}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        de = info.get("debtToEquity")

        if de is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No D/E data"},
            )

        if de < 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Negative equity", "debt_to_equity": float(de)},
            )

        matched = _in_range(de, self.min_de, self.max_de)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "debt_to_equity": float(de),
                "min_de": self.min_de,
                "max_de": self.max_de,
            },
        )

    def __repr__(self) -> str:
        return f"DebtToEquityCondition(min_de={self.min_de}, max_de={self.max_de})"


# ===================================================================
# 11. CurrentRatioCondition
# ===================================================================

@register_condition(
    key="current_ratio",
    label="Current Ratio",
    description="Current ratio (liquidity) filter",
    category="Fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 1.0, "description": "Min ratio"},
        {"name": "max_ratio", "type": "float", "default": 3.0, "description": "Max ratio"},
    ],
)
class CurrentRatioCondition(BaseCondition):
    """Current ratio screening condition."""

    def __init__(
        self,
        min_ratio: Optional[float] = 1.0,
        max_ratio: Optional[float] = 3.0,
    ):
        """
        Args:
            min_ratio: Minimum acceptable current ratio (inclusive).
            max_ratio: Maximum acceptable current ratio (inclusive).
        """
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return f"current_ratio_{self.min_ratio}_{self.max_ratio}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        cr = info.get("currentRatio")

        if cr is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No current ratio data"},
            )

        matched = _in_range(cr, self.min_ratio, self.max_ratio)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_ratio": float(cr),
                "min_ratio": self.min_ratio,
                "max_ratio": self.max_ratio,
            },
        )

    def __repr__(self) -> str:
        return f"CurrentRatioCondition(min_ratio={self.min_ratio}, max_ratio={self.max_ratio})"


# ===================================================================
# 12. RoeCondition
# ===================================================================

@register_condition(
    key="roe",
    label="ROE",
    description="Return on Equity filter",
    category="Fundamental",
    params=[
        {"name": "min_roe", "type": "float", "default": 15.0, "description": "Min ROE %"},
        {"name": "max_roe", "type": "float", "default": None, "description": "Max ROE %"},
    ],
)
class RoeCondition(BaseCondition):
    """Return on Equity screening condition.

    yfinance returns ``returnOnEquity`` as a decimal (e.g. 0.15 = 15%).
    Thresholds and reported details use *percentage* units.
    Excludes tickers with negative equity.
    """

    def __init__(
        self,
        min_roe: Optional[float] = 15.0,
        max_roe: Optional[float] = None,
    ):
        """
        Args:
            min_roe: Minimum ROE in % (inclusive).
            max_roe: Maximum ROE in % (inclusive).
        """
        self.min_roe = min_roe
        self.max_roe = max_roe

    @property
    def name(self) -> str:
        return f"roe_min{self.min_roe}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)
        raw = info.get("returnOnEquity")

        if raw is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No ROE data"},
            )

        roe_pct = raw * 100.0
        matched = _in_range(roe_pct, self.min_roe, self.max_roe)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "roe_pct": float(roe_pct),
                "min_roe": self.min_roe,
                "max_roe": self.max_roe,
            },
        )

    def __repr__(self) -> str:
        return f"RoeCondition(min_roe={self.min_roe}%, max_roe={self.max_roe}%)"


# ===================================================================
# 13. PiotroskiFScoreCondition
# ===================================================================

@register_condition(
    key="piotroski_fscore",
    label="Piotroski F-Score",
    description="Piotroski F-Score (0-9) financial strength",
    category="Fundamental",
    params=[
        {"name": "min_score", "type": "int", "default": 7, "description": "Min F-Score"},
        {"name": "max_score", "type": "int", "default": None, "description": "Max F-Score"},
    ],
)
class PiotroskiFScoreCondition(BaseCondition):
    """Piotroski F-Score screening condition.

    The F-Score is the sum of 9 binary signals (0 or 1) derived from the
    most recent annual financial statements:

      1. ROA > 0
      2. Operating Cash Flow > 0
      3. ROA increased vs prior year
      4. CFO > Net Income (accrual quality)
      5. Long-term debt ratio decreased
      6. Current ratio increased
      7. No new shares issued
      8. Gross margin increased
      9. Asset turnover increased

    Missing data for any signal defaults that signal to 0.
    """

    def __init__(
        self,
        min_score: Optional[int] = 7,
        max_score: Optional[int] = None,
    ):
        """
        Args:
            min_score: Minimum acceptable F-Score (inclusive, 0-9).
            max_score: Maximum acceptable F-Score (inclusive, 0-9).
        """
        self.min_score = min_score
        self.max_score = max_score

    @property
    def name(self) -> str:
        return f"piotroski_f_score_min{self.min_score}"

    @property
    def required_days(self) -> int:
        return 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_get(df: pd.DataFrame, label: str, col_idx: int) -> Optional[float]:
        """Safely retrieve a value from a financial statement DataFrame.

        Args:
            df: Financial statement DataFrame (rows=items, cols=dates).
            label: Row label (e.g. 'Total Assets').
            col_idx: Column index (0 = most recent year).

        Returns:
            The numeric value or None if unavailable.
        """
        try:
            if label not in df.index:
                return None
            val = df.loc[label].iloc[col_idx]
            if pd.isna(val):
                return None
            return float(val)
        except (IndexError, KeyError):
            return None

    def _compute_signals(self, ticker: str) -> dict:
        """Compute the 9 Piotroski signals.

        Returns a dict with keys ``s1`` through ``s9`` (int 0 or 1) and
        ``f_score`` (sum).
        """
        income, balance, cashflow = _get_financial_statements(ticker)

        signals: dict = {}
        get = self._safe_get

        # --- Profitability signals (1-4) ---

        # Net Income (current & prior)
        ni_curr = get(income, "Net Income", 0)
        ni_prev = get(income, "Net Income", 1)

        # Total Assets (current & prior)
        ta_curr = get(balance, "Total Assets", 0)
        ta_prev = get(balance, "Total Assets", 1)

        # ROA current & prior
        roa_curr = (ni_curr / ta_curr) if (ni_curr is not None and ta_curr) else None
        roa_prev = (ni_prev / ta_prev) if (ni_prev is not None and ta_prev) else None

        # 1. ROA > 0
        signals["s1"] = 1 if (roa_curr is not None and roa_curr > 0) else 0

        # Operating Cash Flow
        cfo_curr = get(cashflow, "Operating Cash Flow", 0)

        # 2. Operating Cash Flow > 0
        signals["s2"] = 1 if (cfo_curr is not None and cfo_curr > 0) else 0

        # 3. ROA increased
        signals["s3"] = 1 if (roa_curr is not None and roa_prev is not None and roa_curr > roa_prev) else 0

        # 4. CFO > Net Income (accrual quality)
        signals["s4"] = 1 if (cfo_curr is not None and ni_curr is not None and cfo_curr > ni_curr) else 0

        # --- Leverage / Liquidity signals (5-7) ---

        # Long-term debt / Total Assets (current & prior)
        ltd_curr = get(balance, "Long Term Debt", 0)
        ltd_prev = get(balance, "Long Term Debt", 1)

        ltd_ratio_curr = (ltd_curr / ta_curr) if (ltd_curr is not None and ta_curr) else None
        ltd_ratio_prev = (ltd_prev / ta_prev) if (ltd_prev is not None and ta_prev) else None

        # 5. Long-term debt ratio decreased
        signals["s5"] = 1 if (
            ltd_ratio_curr is not None
            and ltd_ratio_prev is not None
            and ltd_ratio_curr < ltd_ratio_prev
        ) else 0

        # Current ratio (current & prior)
        ca_curr = get(balance, "Current Assets", 0)
        cl_curr = get(balance, "Current Liabilities", 0)
        ca_prev = get(balance, "Current Assets", 1)
        cl_prev = get(balance, "Current Liabilities", 1)

        cr_curr = (ca_curr / cl_curr) if (ca_curr is not None and cl_curr) else None
        cr_prev = (ca_prev / cl_prev) if (ca_prev is not None and cl_prev) else None

        # 6. Current ratio increased
        signals["s6"] = 1 if (cr_curr is not None and cr_prev is not None and cr_curr > cr_prev) else 0

        # Shares outstanding (current & prior)
        shares_curr = get(balance, "Ordinary Shares Number", 0)
        shares_prev = get(balance, "Ordinary Shares Number", 1)

        # 7. No new shares issued (shares did not increase)
        signals["s7"] = 1 if (
            shares_curr is not None
            and shares_prev is not None
            and shares_curr <= shares_prev
        ) else 0

        # --- Operating Efficiency signals (8-9) ---

        # Gross profit & Revenue (current & prior)
        gp_curr = get(income, "Gross Profit", 0)
        gp_prev = get(income, "Gross Profit", 1)
        rev_curr = get(income, "Total Revenue", 0)
        rev_prev = get(income, "Total Revenue", 1)

        gm_curr = (gp_curr / rev_curr) if (gp_curr is not None and rev_curr) else None
        gm_prev = (gp_prev / rev_prev) if (gp_prev is not None and rev_prev) else None

        # 8. Gross margin increased
        signals["s8"] = 1 if (gm_curr is not None and gm_prev is not None and gm_curr > gm_prev) else 0

        # Asset turnover (current & prior)
        at_curr = (rev_curr / ta_curr) if (rev_curr is not None and ta_curr) else None
        at_prev = (rev_prev / ta_prev) if (rev_prev is not None and ta_prev) else None

        # 9. Asset turnover increased
        signals["s9"] = 1 if (at_curr is not None and at_prev is not None and at_curr > at_prev) else 0

        signals["f_score"] = sum(signals[f"s{i}"] for i in range(1, 10))
        return signals

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        try:
            signals = self._compute_signals(ticker)
        except Exception as exc:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": f"Failed to compute F-Score: {exc}"},
            )

        f_score = signals["f_score"]
        matched = _in_range(f_score, self.min_score, self.max_score)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "f_score": f_score,
                **{k: v for k, v in signals.items() if k != "f_score"},
                "min_score": self.min_score,
                "max_score": self.max_score,
            },
        )

    def __repr__(self) -> str:
        return f"PiotroskiFScoreCondition(min_score={self.min_score}, max_score={self.max_score})"


# ===================================================================
# 14. AltmanZScoreCondition
# ===================================================================

@register_condition(
    key="altman_zscore",
    label="Altman Z-Score",
    description="Altman Z-Score bankruptcy risk filter",
    category="Fundamental",
    params=[
        {"name": "min_zscore", "type": "float", "default": 2.5, "description": "Min Z-Score"},
        {"name": "max_zscore", "type": "float", "default": None, "description": "Max Z-Score"},
    ],
)
class AltmanZScoreCondition(BaseCondition):
    """Altman Z-Score screening condition.

    Formula (original manufacturing model):
        Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E

    Where:
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Market Cap / Total Liabilities
        E = Total Revenue / Total Assets

    Interpretation:
        Z > 2.99  -> Safe zone
        1.81-2.99 -> Grey zone
        Z < 1.81  -> Distress zone
    """

    def __init__(
        self,
        min_zscore: Optional[float] = 2.5,
        max_zscore: Optional[float] = None,
    ):
        """
        Args:
            min_zscore: Minimum acceptable Z-Score (inclusive).
            max_zscore: Maximum acceptable Z-Score (inclusive).
        """
        self.min_zscore = min_zscore
        self.max_zscore = max_zscore

    @property
    def name(self) -> str:
        return f"altman_z_score_min{self.min_zscore}"

    @property
    def required_days(self) -> int:
        return 1

    @staticmethod
    def _safe_get(df: pd.DataFrame, label: str, col_idx: int = 0) -> Optional[float]:
        """Safely retrieve a value from a financial statement DataFrame."""
        try:
            if label not in df.index:
                return None
            val = df.loc[label].iloc[col_idx]
            if pd.isna(val):
                return None
            return float(val)
        except (IndexError, KeyError):
            return None

    def _compute_z_score(self, ticker: str) -> Optional[dict]:
        """Compute the Altman Z-Score components.

        Returns a dict with keys ``A`` through ``E``, ``z_score``, and raw
        values, or ``None`` when critical data is missing.
        """
        info = _get_info(ticker)
        income, balance, _ = _get_financial_statements(ticker)
        get = self._safe_get

        total_assets = get(balance, "Total Assets")
        if total_assets is None or total_assets == 0:
            return None

        # A = Working Capital / Total Assets
        current_assets = get(balance, "Current Assets")
        current_liabilities = get(balance, "Current Liabilities")
        if current_assets is None or current_liabilities is None:
            return None
        working_capital = current_assets - current_liabilities
        a = working_capital / total_assets

        # B = Retained Earnings / Total Assets
        retained_earnings = get(balance, "Retained Earnings")
        if retained_earnings is None:
            return None
        b = retained_earnings / total_assets

        # C = EBIT / Total Assets
        ebit = get(income, "EBIT")
        if ebit is None:
            ebit = get(income, "EBITDA")  # fallback
        if ebit is None:
            return None
        c = ebit / total_assets

        # D = Market Cap / Total Liabilities
        market_cap = info.get("marketCap")
        total_liabilities = get(balance, "Total Liabilities Net Minority Interest")
        if total_liabilities is None:
            total_liabilities = get(balance, "Total Liabilities")
        if market_cap is None or total_liabilities is None or total_liabilities == 0:
            return None
        d = market_cap / total_liabilities

        # E = Total Revenue / Total Assets
        total_revenue = get(income, "Total Revenue")
        if total_revenue is None:
            return None
        e = total_revenue / total_assets

        z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

        return {
            "A_working_capital_ta": float(a),
            "B_retained_earnings_ta": float(b),
            "C_ebit_ta": float(c),
            "D_market_cap_tl": float(d),
            "E_revenue_ta": float(e),
            "z_score": float(z_score),
        }

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        try:
            result = self._compute_z_score(ticker)
        except Exception as exc:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": f"Failed to compute Z-Score: {exc}"},
            )

        if result is None:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient financial data for Z-Score"},
            )

        z = result["z_score"]
        matched = _in_range(z, self.min_zscore, self.max_zscore)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                **result,
                "min_zscore": self.min_zscore,
                "max_zscore": self.max_zscore,
            },
        )

    def __repr__(self) -> str:
        return f"AltmanZScoreCondition(min_zscore={self.min_zscore}, max_zscore={self.max_zscore})"


# ===================================================================
# 15. RoicCondition
# ===================================================================

@register_condition(
    key="roic",
    label="ROIC",
    description="Return on Invested Capital filter",
    category="Fundamental",
    params=[
        {"name": "min_roic", "type": "float", "default": 15.0, "description": "Min ROIC %"},
        {"name": "max_roic", "type": "float", "default": None, "description": "Max ROIC %"},
    ],
)
class RoicCondition(BaseCondition):
    """Return on Invested Capital screening condition.

    ROIC = NOPAT / Invested Capital * 100

    Where:
        NOPAT = Operating Income * (1 - Tax Rate)
        Invested Capital = Total Debt + Total Stockholder Equity

    Excludes tickers with non-positive invested capital.
    """

    def __init__(
        self,
        min_roic: Optional[float] = 15.0,
        max_roic: Optional[float] = None,
    ):
        """
        Args:
            min_roic: Minimum ROIC in % (inclusive).
            max_roic: Maximum ROIC in % (inclusive).
        """
        self.min_roic = min_roic
        self.max_roic = max_roic

    @property
    def name(self) -> str:
        return f"roic_min{self.min_roic}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        info = _get_info(ticker)

        operating_income = info.get("operatingIncome") or info.get("ebitda", 0)
        if not operating_income:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No operating income data"},
            )

        tax_rate = info.get("effectiveTaxRate") or 0.21
        nopat = operating_income * (1 - tax_rate)

        total_debt = info.get("totalDebt", 0)
        total_equity = info.get("totalStockholderEquity", 0)
        invested_capital = total_debt + total_equity

        if invested_capital <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Non-positive invested capital"},
            )

        roic_pct = (nopat / invested_capital) * 100
        matched = _in_range(roic_pct, self.min_roic, self.max_roic)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "roic_pct": float(roic_pct),
                "nopat": float(nopat),
                "invested_capital": float(invested_capital),
                "min_roic": self.min_roic,
                "max_roic": self.max_roic,
            },
        )

    def __repr__(self) -> str:
        return f"RoicCondition(min_roic={self.min_roic}%, max_roic={self.max_roic}%)"
