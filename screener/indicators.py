"""
Technical Indicators Calculator
기술적 지표 계산 모듈

Usage:
    from discovery.indicators import calculate_indicators

    indicators = calculate_indicators("005930.KS", period=365)
    print(f"RSI: {indicators['rsi']}")
    print(f"MACD: {indicators['macd']}")
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

from utils.fetch import get_ohlcv


@dataclass
class TechnicalIndicators:
    """기술적 지표 데이터"""
    # Moving Averages
    ma_5: float
    ma_20: float
    ma_60: float
    ma_120: float
    ma_240: float

    # RSI
    rsi: float

    # MACD
    macd: float
    macd_signal: float
    macd_histogram: float

    # Bollinger Bands
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float

    # Volume
    volume: float
    volume_ma: float
    volume_ratio: float

    # Price info
    current_price: float
    prev_close: float
    change_pct: float

    # Additional
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ma_5": self.ma_5,
            "ma_20": self.ma_20,
            "ma_60": self.ma_60,
            "ma_120": self.ma_120,
            "ma_240": self.ma_240,
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "bb_width": self.bb_width,
            "volume": self.volume,
            "volume_ma": self.volume_ma,
            "volume_ratio": self.volume_ratio,
            "current_price": self.current_price,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "high_52w": self.high_52w,
            "low_52w": self.low_52w,
        }


def calculate_indicators(
    ticker: str,
    period: int = 365,
    data: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    기술적 지표 계산

    Args:
        ticker: 종목 코드
        period: 데이터 기간 (일)
        data: 가격 데이터 (없으면 자동 조회)

    Returns:
        지표 딕셔너리
    """
    if data is None:
        data = get_ohlcv(ticker, days=period)

    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']

    # Moving Averages
    ma_5 = _safe_last(close.rolling(5).mean())
    ma_20 = _safe_last(close.rolling(20).mean())
    ma_60 = _safe_last(close.rolling(60).mean())
    ma_120 = _safe_last(close.rolling(120).mean())
    ma_240 = _safe_last(close.rolling(240).mean())

    # RSI
    rsi = _safe_last(_calculate_rsi(close, 14))

    # MACD
    macd_line, signal_line, histogram = _calculate_macd(close)
    macd = _safe_last(macd_line)
    macd_signal = _safe_last(signal_line)
    macd_histogram = _safe_last(histogram)

    # Bollinger Bands
    bb_middle = _safe_last(close.rolling(20).mean())
    bb_std = _safe_last(close.rolling(20).std())
    bb_upper = bb_middle + (2 * bb_std) if bb_std else None
    bb_lower = bb_middle - (2 * bb_std) if bb_std else None
    bb_width = ((bb_upper - bb_lower) / bb_middle * 100) if bb_middle and bb_upper and bb_lower else None

    # Volume
    current_volume = _safe_last(volume)
    volume_ma = _safe_last(volume.rolling(20).mean())
    volume_ratio = (current_volume / volume_ma) if volume_ma else None

    # Price
    current_price = _safe_last(close)
    prev_close = close.iloc[-2] if len(close) > 1 else None
    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else None

    # 52-week high/low
    if len(close) >= 252:
        high_52w = high.tail(252).max()
        low_52w = low.tail(252).min()
    else:
        high_52w = high.max()
        low_52w = low.min()

    return {
        "ma_5": ma_5,
        "ma_20": ma_20,
        "ma_60": ma_60,
        "ma_120": ma_120,
        "ma_240": ma_240,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_histogram": macd_histogram,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
        "bb_width": bb_width,
        "volume": current_volume,
        "volume_ma": volume_ma,
        "volume_ratio": volume_ratio,
        "current_price": current_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "high_52w": float(high_52w) if high_52w else None,
        "low_52w": float(low_52w) if low_52w else None,
    }


def calculate_all_mas(
    ticker: str,
    periods: list = [5, 10, 20, 60, 120, 200, 240],
    data: Optional[pd.DataFrame] = None
) -> Dict[int, float]:
    """
    여러 기간의 이동평균선 계산

    Args:
        ticker: 종목 코드
        periods: 계산할 MA 기간 목록
        data: 가격 데이터

    Returns:
        {period: ma_value} 딕셔너리
    """
    if data is None:
        max_period = max(periods) + 50
        data = get_ohlcv(ticker, days=max_period)

    close = data['close']
    result = {}

    for period in periods:
        ma = close.rolling(period).mean()
        result[period] = _safe_last(ma)

    return result


def get_ma_distances(
    ticker: str,
    periods: list = [20, 60, 120, 240],
    data: Optional[pd.DataFrame] = None
) -> Dict[int, Dict[str, float]]:
    """
    현재가와 각 MA간의 거리 계산

    Returns:
        {period: {"ma": value, "distance_pct": pct}} 딕셔너리
    """
    if data is None:
        max_period = max(periods) + 50
        data = get_ohlcv(ticker, days=max_period)

    close = data['close']
    current_price = close.iloc[-1]

    result = {}
    for period in periods:
        ma = _safe_last(close.rolling(period).mean())
        if ma:
            distance_pct = (current_price - ma) / ma * 100
            result[period] = {
                "ma": ma,
                "distance_pct": distance_pct,
                "above": current_price > ma
            }

    return result


# ============================================================
# Helper Functions
# ============================================================

def _safe_last(series: pd.Series) -> Optional[float]:
    """시리즈의 마지막 값을 안전하게 반환"""
    if series is None or series.empty:
        return None
    val = series.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> tuple:
    """MACD 계산"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def _calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV (On-Balance Volume) 계산"""
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]

    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]

    return obv


# ============================================================
# Exported Indicator Functions (for accumulation screening)
# ============================================================

def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    OBV (On-Balance Volume) 계산

    Args:
        close: 종가 시리즈
        volume: 거래량 시리즈

    Returns:
        OBV 시리즈
    """
    return _calculate_obv(close, volume)


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> tuple:
    """
    스토캐스틱 오실레이터 계산

    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        k_period: %K 기간 (기본 14)
        d_period: %D 기간 (기본 3)

    Returns:
        (stoch_k, stoch_d) 튜플
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(window=d_period).mean()

    return stoch_k, stoch_d


def calculate_vpci(
    close: pd.Series,
    volume: pd.Series,
    short_period: int = 5,
    long_period: int = 20
) -> pd.Series:
    """
    VPCI (Volume Price Confirmation Indicator) 계산

    VPCI는 가격과 거래량의 상관관계를 측정하여
    매집/분산 구간을 탐지하는 지표

    Args:
        close: 종가 시리즈
        volume: 거래량 시리즈
        short_period: 단기 EMA 기간 (기본 5)
        long_period: 장기 EMA 기간 (기본 20)

    Returns:
        VPCI 시리즈
    """
    # Volume Weighted Moving Averages
    vwma_short = (close * volume).rolling(short_period).sum() / volume.rolling(short_period).sum()
    vwma_long = (close * volume).rolling(long_period).sum() / volume.rolling(long_period).sum()

    # Simple Moving Averages
    sma_short = close.rolling(short_period).mean()
    sma_long = close.rolling(long_period).mean()

    # VPC (Volume Price Confirmation)
    vpc = vwma_long - sma_long

    # VPR (Volume Price Ratio)
    vpr = vwma_short / sma_short

    # VM (Volume Multiplier)
    volume_sma = volume.rolling(short_period).mean()
    volume_sma_long = volume.rolling(long_period).mean()
    vm = volume_sma / volume_sma_long

    # VPCI = VPC * VPR * VM
    vpci = vpc * vpr * vm

    return vpci


def calculate_bollinger_width(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.Series:
    """
    볼린저 밴드 폭 계산 (% 기준)

    Args:
        close: 종가 시리즈
        period: 이동평균 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2.0)

    Returns:
        볼린저 밴드 폭 (%) 시리즈
    """
    middle = close.rolling(period).mean()
    std = close.rolling(period).std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    # 폭을 중심선 대비 % 로 계산
    width_pct = ((upper - lower) / middle) * 100

    return width_pct
