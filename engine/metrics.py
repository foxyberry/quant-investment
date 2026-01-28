"""
Performance Metrics Calculator
백테스트 성능 지표 계산 모듈

Metrics:
    - Sharpe Ratio: 위험 조정 수익률
    - Sortino Ratio: 하방 위험 조정 수익률
    - Maximum Drawdown (MDD): 최대 낙폭
    - Win Rate: 승률
    - Profit Factor: 손익비
    - CAGR: 연평균 복리 수익률
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import pandas as pd
import numpy as np


# PnL column name variants
PNL_COLUMN_NAMES: List[str] = ['PnL', 'pnl', 'profit', 'Profit', 'ReturnPct']


def find_pnl_column(df: pd.DataFrame) -> Optional[str]:
    """
    데이터프레임에서 PnL 컬럼 찾기

    Args:
        df: 거래 내역 DataFrame

    Returns:
        PnL 컬럼명 또는 None
    """
    for col in PNL_COLUMN_NAMES:
        if col in df.columns:
            return col
    return None


@dataclass
class PerformanceMetrics:
    """성능 지표 데이터 클래스"""
    sharpe_ratio: float
    sortino_ratio: float
    mdd: float
    win_rate: float
    profit_factor: float
    cagr: float
    total_return: float
    num_trades: int
    avg_trade_return: float
    max_consecutive_wins: int
    max_consecutive_losses: int

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'mdd': self.mdd,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'cagr': self.cagr,
            'total_return': self.total_return,
            'num_trades': self.num_trades,
            'avg_trade_return': self.avg_trade_return,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
        }

    def summary(self) -> str:
        """결과 요약 문자열"""
        lines = [
            "=" * 60,
            "PERFORMANCE METRICS",
            "=" * 60,
            f"{'Total Return:':<25} {self.total_return:>10.2%}",
            f"{'CAGR:':<25} {self.cagr:>10.2%}",
            f"{'Sharpe Ratio:':<25} {self.sharpe_ratio:>10.2f}",
            f"{'Sortino Ratio:':<25} {self.sortino_ratio:>10.2f}",
            f"{'Max Drawdown (MDD):':<25} {self.mdd:>10.2%}",
            "-" * 60,
            f"{'Win Rate:':<25} {self.win_rate:>10.2%}",
            f"{'Profit Factor:':<25} {self.profit_factor:>10.2f}",
            f"{'# Trades:':<25} {self.num_trades:>10d}",
            f"{'Avg Trade Return:':<25} {self.avg_trade_return:>10.2%}",
            f"{'Max Consecutive Wins:':<25} {self.max_consecutive_wins:>10d}",
            f"{'Max Consecutive Losses:':<25} {self.max_consecutive_losses:>10d}",
            "=" * 60,
        ]
        return "\n".join(lines)


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    샤프 비율 계산

    Args:
        returns: 일별 수익률 시리즈
        risk_free_rate: 무위험 수익률 (연율, 기본 2%)
        periods_per_year: 연간 거래일 수 (기본 252)

    Returns:
        샤프 비율
    """
    if returns.empty or returns.std() == 0:
        return 0.0

    excess_returns = returns - (risk_free_rate / periods_per_year)
    return np.sqrt(periods_per_year) * excess_returns.mean() / returns.std()


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    소르티노 비율 계산 (하방 위험만 고려)

    Args:
        returns: 일별 수익률 시리즈
        risk_free_rate: 무위험 수익률 (연율)
        periods_per_year: 연간 거래일 수

    Returns:
        소르티노 비율
    """
    if returns.empty:
        return 0.0

    excess_returns = returns - (risk_free_rate / periods_per_year)
    downside_returns = returns[returns < 0]

    if downside_returns.empty or downside_returns.std() == 0:
        return 0.0 if excess_returns.mean() <= 0 else float('inf')

    downside_std = np.sqrt((downside_returns ** 2).mean())
    return np.sqrt(periods_per_year) * excess_returns.mean() / downside_std


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    최대 낙폭 (MDD) 계산

    Args:
        equity_curve: 자산 가치 시리즈

    Returns:
        최대 낙폭 (0~1 사이 값, 예: 0.15 = 15% 낙폭)
    """
    if equity_curve.empty:
        return 0.0

    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return abs(drawdown.min())


def calculate_cagr(
    initial_value: float,
    final_value: float,
    years: float
) -> float:
    """
    연평균 복리 수익률 (CAGR) 계산

    Args:
        initial_value: 초기 자산
        final_value: 최종 자산
        years: 투자 기간 (년)

    Returns:
        CAGR
    """
    if initial_value <= 0 or years <= 0:
        return 0.0

    return (final_value / initial_value) ** (1 / years) - 1


def calculate_win_rate(trades: pd.DataFrame) -> float:
    """
    승률 계산

    Args:
        trades: 거래 내역 DataFrame (PnL 컬럼 필요)

    Returns:
        승률 (0~1)
    """
    if trades.empty:
        return 0.0

    pnl_col = find_pnl_column(trades)
    if pnl_col is None:
        return 0.0

    wins = (trades[pnl_col] > 0).sum()
    return wins / len(trades)


def calculate_profit_factor(trades: pd.DataFrame) -> float:
    """
    손익비 (Profit Factor) 계산

    Args:
        trades: 거래 내역 DataFrame

    Returns:
        손익비 (총 이익 / 총 손실)
    """
    if trades.empty:
        return 0.0

    pnl_col = find_pnl_column(trades)
    if pnl_col is None:
        return 0.0

    gross_profit = trades[trades[pnl_col] > 0][pnl_col].sum()
    gross_loss = abs(trades[trades[pnl_col] < 0][pnl_col].sum())

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def calculate_consecutive_wins_losses(trades: pd.DataFrame) -> tuple:
    """
    최대 연속 승/패 계산

    Args:
        trades: 거래 내역 DataFrame

    Returns:
        (최대 연속 승, 최대 연속 패)
    """
    if trades.empty:
        return 0, 0

    pnl_col = find_pnl_column(trades)
    if pnl_col is None:
        return 0, 0

    wins = trades[pnl_col] > 0

    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    for win in wins:
        if win:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)

    return max_wins, max_losses


def calculate_metrics(
    backtest_result,
    risk_free_rate: float = 0.02
) -> PerformanceMetrics:
    """
    백테스트 결과에서 모든 성능 지표 계산

    Args:
        backtest_result: BacktestResult 객체 또는 Backtesting.py stats
        risk_free_rate: 무위험 수익률 (연율)

    Returns:
        PerformanceMetrics 객체
    """
    # Extract data from result
    if hasattr(backtest_result, 'stats'):
        stats = backtest_result.stats
        trades = backtest_result.trades
        equity_curve = backtest_result.equity_curve
    else:
        stats = backtest_result
        trades = stats._trades if hasattr(stats, '_trades') else pd.DataFrame()
        equity_curve = stats._equity_curve if hasattr(stats, '_equity_curve') else pd.DataFrame()

    # Calculate returns from equity curve
    if isinstance(equity_curve, pd.DataFrame) and 'Equity' in equity_curve.columns:
        equity = equity_curve['Equity']
    elif isinstance(equity_curve, pd.Series):
        equity = equity_curve
    else:
        equity = pd.Series([1.0])

    returns = equity.pct_change().dropna()

    # Calculate metrics
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    sortino = calculate_sortino_ratio(returns, risk_free_rate)
    mdd = calculate_max_drawdown(equity)
    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)
    max_wins, max_losses = calculate_consecutive_wins_losses(trades)

    # Get values from stats
    total_return = stats.get('Return [%]', 0) / 100 if hasattr(stats, 'get') else 0
    num_trades = int(stats.get('# Trades', 0)) if hasattr(stats, 'get') else len(trades)

    # Calculate CAGR
    if len(equity) > 1:
        days = (equity.index[-1] - equity.index[0]).days
        years = days / 365.25 if days > 0 else 1
        cagr = calculate_cagr(equity.iloc[0], equity.iloc[-1], years)
    else:
        cagr = 0.0

    # Average trade return
    if not trades.empty:
        pnl_col = None
        for col in ['ReturnPct', 'PnL', 'pnl', 'profit']:
            if col in trades.columns:
                pnl_col = col
                break
        avg_trade_return = trades[pnl_col].mean() / 100 if pnl_col else 0.0
    else:
        avg_trade_return = 0.0

    return PerformanceMetrics(
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        mdd=mdd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        cagr=cagr,
        total_return=total_return,
        num_trades=num_trades,
        avg_trade_return=avg_trade_return,
        max_consecutive_wins=max_wins,
        max_consecutive_losses=max_losses,
    )
