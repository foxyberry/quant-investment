"""
Backtesting Engine
Backtesting.py 기반 백테스팅 엔진

Usage:
    from engine import BacktestEngine
    from engine.strategies import SmaCross

    engine = BacktestEngine()
    result = engine.run(
        strategy=SmaCross,
        ticker="005930.KS",
        period="1y",
        cash=10_000_000
    )
    print(result.summary())
"""

import sys
from pathlib import Path
from typing import Optional, Type, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

import pandas as pd
import numpy as np

from backtesting import Backtest, Strategy

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class BacktestResult:
    """백테스트 결과"""
    stats: pd.Series
    trades: pd.DataFrame
    equity_curve: pd.DataFrame

    @property
    def total_return(self) -> float:
        """총 수익률"""
        return self.stats.get('Return [%]', 0) / 100

    @property
    def sharpe_ratio(self) -> float:
        """샤프 비율"""
        return self.stats.get('Sharpe Ratio', 0)

    @property
    def max_drawdown(self) -> float:
        """최대 낙폭"""
        return self.stats.get('Max. Drawdown [%]', 0) / 100

    @property
    def win_rate(self) -> float:
        """승률"""
        return self.stats.get('Win Rate [%]', 0) / 100

    @property
    def num_trades(self) -> int:
        """거래 횟수"""
        return int(self.stats.get('# Trades', 0))

    def summary(self) -> str:
        """결과 요약 문자열"""
        lines = [
            "=" * 50,
            "BACKTEST RESULTS",
            "=" * 50,
            f"Total Return:    {self.total_return:>10.2%}",
            f"Sharpe Ratio:    {self.sharpe_ratio:>10.2f}",
            f"Max Drawdown:    {self.max_drawdown:>10.2%}",
            f"Win Rate:        {self.win_rate:>10.2%}",
            f"# Trades:        {self.num_trades:>10d}",
            "=" * 50,
        ]
        return "\n".join(lines)


class BacktestEngine:
    """
    백테스팅 엔진

    Backtesting.py를 래핑하여 한국/미국 주식 백테스트 지원
    """

    def __init__(self, commission: float = 0.001, margin: float = 1.0):
        """
        Args:
            commission: 거래 수수료 (기본 0.1%)
            margin: 마진 비율 (기본 1.0 = 현금 거래)
        """
        self.commission = commission
        self.margin = margin

    def fetch_data(
        self,
        ticker: str,
        period: str = "1y",
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        주가 데이터 조회

        Args:
            ticker: 종목 코드 (예: "005930.KS", "AAPL")
            period: 기간 (예: "1y", "6mo", "3mo")
            start: 시작일 (YYYY-MM-DD)
            end: 종료일 (YYYY-MM-DD)

        Returns:
            OHLCV DataFrame (columns: Open, High, Low, Close, Volume)
        """
        import yfinance as yf

        ticker_obj = yf.Ticker(ticker)

        if start and end:
            data = ticker_obj.history(start=start, end=end, auto_adjust=True)
        else:
            data = ticker_obj.history(period=period, auto_adjust=True)

        if data.empty:
            raise ValueError(f"No data found for ticker: {ticker}")

        # Backtesting.py requires specific column names
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        data.index = pd.to_datetime(data.index)

        # Remove timezone info if present
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        return data

    def run(
        self,
        strategy: Type[Strategy],
        ticker: str,
        period: str = "1y",
        start: Optional[str] = None,
        end: Optional[str] = None,
        cash: float = 10_000_000,
        data: Optional[pd.DataFrame] = None,
        **strategy_params
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            strategy: 전략 클래스 (backtesting.Strategy 상속)
            ticker: 종목 코드
            period: 기간
            start: 시작일
            end: 종료일
            cash: 초기 자금
            data: 직접 제공하는 데이터 (없으면 자동 조회)
            **strategy_params: 전략 파라미터

        Returns:
            BacktestResult 객체
        """
        # Fetch data if not provided
        if data is None:
            data = self.fetch_data(ticker, period, start, end)

        # Create backtest
        bt = Backtest(
            data,
            strategy,
            cash=cash,
            commission=self.commission,
            margin=self.margin,
            exclusive_orders=True,
            trade_on_close=True,
            finalize_trades=True
        )

        # Run backtest
        stats = bt.run(**strategy_params)

        # Extract results
        return BacktestResult(
            stats=stats,
            trades=stats._trades if hasattr(stats, '_trades') else pd.DataFrame(),
            equity_curve=stats._equity_curve if hasattr(stats, '_equity_curve') else pd.DataFrame()
        )

    def optimize(
        self,
        strategy: Type[Strategy],
        ticker: str,
        period: str = "1y",
        cash: float = 10_000_000,
        maximize: str = 'Sharpe Ratio',
        constraint: Optional[callable] = None,
        **param_ranges
    ) -> BacktestResult:
        """
        파라미터 최적화

        Args:
            strategy: 전략 클래스
            ticker: 종목 코드
            period: 기간
            cash: 초기 자금
            maximize: 최적화 목표 지표
            constraint: 제약 조건 함수
            **param_ranges: 파라미터 범위 (예: n1=range(5, 30, 5))

        Returns:
            최적화된 결과
        """
        data = self.fetch_data(ticker, period)

        bt = Backtest(
            data,
            strategy,
            cash=cash,
            commission=self.commission,
            margin=self.margin,
            exclusive_orders=True,
            trade_on_close=True,
            finalize_trades=True
        )

        stats = bt.optimize(
            maximize=maximize,
            constraint=constraint,
            **param_ranges
        )

        return BacktestResult(
            stats=stats,
            trades=stats._trades if hasattr(stats, '_trades') else pd.DataFrame(),
            equity_curve=stats._equity_curve if hasattr(stats, '_equity_curve') else pd.DataFrame()
        )
