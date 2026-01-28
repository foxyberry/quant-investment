"""
Price Monitor
실시간 가격 모니터링

Usage:
    from portfolio.monitor import PriceMonitor

    monitor = PriceMonitor(interval=10)
    monitor.add("005930.KS")
    monitor.add("AAPL")

    def on_update(data):
        print(f"{data['ticker']}: {data['price']}")

    monitor.on_update(on_update)
    monitor.start()
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

import yfinance as yf


@dataclass
class PriceData:
    """가격 데이터"""
    ticker: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    volume: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "prev_close": self.prev_close,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
        }


class PriceMonitor:
    """가격 모니터링 클래스"""

    def __init__(self, interval: int = 60):
        """
        Args:
            interval: 폴링 간격 (초)
        """
        self.interval = interval
        self.logger = logging.getLogger(__name__)

        self._tickers: List[str] = []
        self._prices: Dict[str, PriceData] = {}
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add(self, ticker: str) -> None:
        """모니터링 종목 추가"""
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            self.logger.info(f"Added ticker to monitor: {ticker}")

    def remove(self, ticker: str) -> None:
        """모니터링 종목 제거"""
        if ticker in self._tickers:
            self._tickers.remove(ticker)
            if ticker in self._prices:
                del self._prices[ticker]
            self.logger.info(f"Removed ticker from monitor: {ticker}")

    def get_tickers(self) -> List[str]:
        """모니터링 중인 종목 목록"""
        return self._tickers.copy()

    def on_update(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        가격 업데이트 콜백 등록

        Args:
            callback: PriceData.to_dict() 형태의 데이터를 받는 함수
        """
        self._callbacks.append(callback)

    def get_price(self, ticker: str) -> Optional[PriceData]:
        """현재 저장된 가격 조회"""
        return self._prices.get(ticker)

    def get_all_prices(self) -> Dict[str, float]:
        """모든 종목의 현재가 딕셔너리"""
        return {ticker: data.price for ticker, data in self._prices.items()}

    def fetch_prices(self) -> Dict[str, PriceData]:
        """모든 종목 가격 조회 (1회)"""
        if not self._tickers:
            return {}

        results = {}

        try:
            # Batch fetch for efficiency
            tickers_str = " ".join(self._tickers)
            data = yf.download(
                tickers_str,
                period="2d",
                interval="1d",
                progress=False,
                threads=True
            )

            for ticker in self._tickers:
                try:
                    if len(self._tickers) == 1:
                        close_data = data['Close']
                        volume_data = data['Volume']
                    else:
                        close_data = data['Close'][ticker]
                        volume_data = data['Volume'][ticker]

                    if close_data.empty:
                        continue

                    current_price = float(close_data.iloc[-1])
                    prev_close = float(close_data.iloc[-2]) if len(close_data) > 1 else current_price
                    volume = int(volume_data.iloc[-1]) if not volume_data.empty else 0

                    change = current_price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close > 0 else 0

                    price_data = PriceData(
                        ticker=ticker,
                        price=current_price,
                        prev_close=prev_close,
                        change=change,
                        change_pct=change_pct,
                        volume=volume,
                        timestamp=datetime.now()
                    )
                    results[ticker] = price_data

                except Exception as e:
                    self.logger.warning(f"Failed to fetch {ticker}: {e}")

        except Exception as e:
            self.logger.error(f"Batch fetch failed: {e}")
            # Fallback to individual fetch
            for ticker in self._tickers:
                try:
                    price_data = self._fetch_single(ticker)
                    if price_data:
                        results[ticker] = price_data
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {ticker}: {e}")

        return results

    def _fetch_single(self, ticker: str) -> Optional[PriceData]:
        """단일 종목 가격 조회"""
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="2d")

            if hist.empty:
                return None

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            volume = int(hist['Volume'].iloc[-1])

            change = current_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0

            return PriceData(
                ticker=ticker,
                price=current_price,
                prev_close=prev_close,
                change=change,
                change_pct=change_pct,
                volume=volume,
                timestamp=datetime.now()
            )
        except Exception as e:
            self.logger.warning(f"Failed to fetch {ticker}: {e}")
            return None

    def _poll_loop(self):
        """폴링 루프"""
        while self._running:
            try:
                prices = self.fetch_prices()

                for ticker, price_data in prices.items():
                    old_price = self._prices.get(ticker)
                    self._prices[ticker] = price_data

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(price_data.to_dict())
                        except Exception as e:
                            self.logger.error(f"Callback error: {e}")

                self.logger.debug(f"Fetched {len(prices)} prices")

            except Exception as e:
                self.logger.error(f"Poll loop error: {e}")

            # Wait for next interval
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def start(self) -> None:
        """모니터링 시작"""
        if self._running:
            self.logger.warning("Monitor already running")
            return

        if not self._tickers:
            self.logger.warning("No tickers to monitor")
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"Price monitor started (interval: {self.interval}s)")

    def stop(self) -> None:
        """모니터링 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self.logger.info("Price monitor stopped")

    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self._running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
