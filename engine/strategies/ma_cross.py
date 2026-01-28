"""
Moving Average Crossover Strategies
이동평균선 크로스오버 전략

Strategies:
    - SmaCross: 단순 이동평균선 크로스오버
    - EmaCross: 지수 이동평균선 크로스오버
"""

from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd


def SMA(values: pd.Series, n: int) -> pd.Series:
    """Simple Moving Average"""
    return values.rolling(n).mean()


def EMA(values: pd.Series, n: int) -> pd.Series:
    """Exponential Moving Average"""
    return values.ewm(span=n, adjust=False).mean()


class SmaCross(Strategy):
    """
    단순 이동평균선 크로스오버 전략

    - 골든크로스 (단기 > 장기): 매수
    - 데드크로스 (단기 < 장기): 매도

    Parameters:
        n1: 단기 이평선 기간 (기본 10)
        n2: 장기 이평선 기간 (기본 20)
    """
    n1 = 10  # 단기 이평선
    n2 = 20  # 장기 이평선

    def init(self):
        close = pd.Series(self.data.Close)
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        # 골든크로스: 매수
        if crossover(self.sma1, self.sma2):
            self.buy()
        # 데드크로스: 매도
        elif crossover(self.sma2, self.sma1):
            self.sell()


class EmaCross(Strategy):
    """
    지수 이동평균선 크로스오버 전략

    - 골든크로스 (단기 > 장기): 매수
    - 데드크로스 (단기 < 장기): 매도

    Parameters:
        n1: 단기 이평선 기간 (기본 12)
        n2: 장기 이평선 기간 (기본 26)
    """
    n1 = 12  # 단기 이평선
    n2 = 26  # 장기 이평선

    def init(self):
        close = pd.Series(self.data.Close)
        self.ema1 = self.I(EMA, close, self.n1)
        self.ema2 = self.I(EMA, close, self.n2)

    def next(self):
        # 골든크로스: 매수
        if crossover(self.ema1, self.ema2):
            self.buy()
        # 데드크로스: 매도
        elif crossover(self.ema2, self.ema1):
            self.sell()


class MaTouchStrategy(Strategy):
    """
    이동평균선 터치 전략

    - 가격이 MA 아래로 떨어졌다가 다시 터치할 때 매수
    - 일정 수익률 도달 시 매도

    Parameters:
        ma_period: 이동평균선 기간 (기본 20)
        take_profit: 익절 비율 (기본 0.05 = 5%)
        stop_loss: 손절 비율 (기본 0.03 = 3%)
    """
    ma_period = 20
    take_profit = 0.05
    stop_loss = 0.03

    def init(self):
        close = pd.Series(self.data.Close)
        self.ma = self.I(SMA, close, self.ma_period)
        self.entry_price = None

    def next(self):
        price = self.data.Close[-1]
        ma = self.ma[-1]

        if not self.position:
            # 가격이 MA 근처에서 반등할 때 매수
            # (전일 MA 아래, 금일 MA 근접)
            if len(self.data.Close) > 1:
                prev_close = self.data.Close[-2]
                prev_ma = self.ma[-2]

                # 전일 MA 아래였고, 금일 MA에 근접 (2% 이내)
                if prev_close < prev_ma and abs(price - ma) / ma < 0.02:
                    self.buy()
                    self.entry_price = price
        else:
            # 포지션 있을 때
            if self.entry_price:
                pnl = (price - self.entry_price) / self.entry_price

                # 익절
                if pnl >= self.take_profit:
                    self.sell()
                    self.entry_price = None
                # 손절
                elif pnl <= -self.stop_loss:
                    self.sell()
                    self.entry_price = None
