"""
Evaluator Helpers
평가기 헬퍼 함수

공통으로 사용되는 기술적 지표 계산 함수
"""

import pandas as pd
import numpy as np


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI 계산

    Args:
        close: 종가 시리즈
        period: RSI 기간 (기본: 14)

    Returns:
        RSI 시리즈
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ma(close: pd.Series, period: int) -> pd.Series:
    """
    이동평균 계산

    Args:
        close: 종가 시리즈
        period: MA 기간

    Returns:
        MA 시리즈
    """
    return close.rolling(period).mean()


def calculate_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_mult: float = 2.0
) -> tuple:
    """
    볼린저 밴드 계산

    Args:
        close: 종가 시리즈
        period: 기간
        std_mult: 표준편차 배수

    Returns:
        (upper_band, middle_band, lower_band)
    """
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()

    upper_band = ma + (std_mult * std)
    lower_band = ma - (std_mult * std)

    return upper_band, ma, lower_band


def is_valid_data(value) -> bool:
    """데이터 유효성 체크"""
    return not (pd.isna(value) or value is None or np.isnan(value))
