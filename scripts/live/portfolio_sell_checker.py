#!/usr/bin/env python3
"""
Portfolio Sell Checker
보유 종목의 매도 신호를 확인하는 스크립트

Usage:
    python scripts/live/portfolio_sell_checker.py
    python scripts/live/portfolio_sell_checker.py --verbose
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.portfolio_manager import PortfolioManager, Holding, SellConditions
from utils.fetch import get_historical_data
from utils.timezone_utils import get_current_market_time


class Signal(Enum):
    """매도 신호 레벨"""
    SELL = "SELL"       # 매도 조건 충족
    WATCH = "WATCH"     # 주의 필요
    HOLD = "HOLD"       # 유지


@dataclass
class SellCheckResult:
    """매도 체크 결과"""
    symbol: str
    name: str
    buy_price: float
    current_price: float
    pnl_pct: float
    signal: Signal
    reasons: List[str]
    conditions: SellConditions


class PortfolioSellChecker:
    """포트폴리오 매도 신호 체커"""

    def __init__(self, verbose: bool = False):
        self.logger = self._setup_logger(verbose)
        self.pm = PortfolioManager()

    def _setup_logger(self, verbose: bool) -> logging.Logger:
        logger = logging.getLogger(__name__)
        level = logging.DEBUG if verbose else logging.INFO
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(handler)

        return logger

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회 (yfinance 직접 사용)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="5d")

            if data is not None and not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            self.logger.warning(f"Failed to get price for {symbol}: {e}")
        return None

    def get_price_data(self, symbol: str, days: int = 60) -> Optional[Dict]:
        """가격 데이터 조회 (이평선 계산용)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y", auto_adjust=True)

            if data is not None and len(data) >= 20:
                close = data['Close']
                return {
                    'current': float(close.iloc[-1]),
                    'high_52w': float(close.max()) if len(close) >= 252 else float(close.max()),
                    'ma_20': float(close.rolling(20).mean().iloc[-1]),
                    'ma_60': float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None,
                    'prev_ma_20': float(close.rolling(20).mean().iloc[-2]),
                    'prev_ma_60': float(close.rolling(60).mean().iloc[-2]) if len(close) >= 60 else None,
                }
        except Exception as e:
            self.logger.warning(f"Failed to get price data for {symbol}: {e}")
        return None

    def check_price_conditions(self, holding: Holding, current_price: float,
                                conditions: SellConditions) -> List[str]:
        """가격 기반 매도 조건 체크"""
        reasons = []
        buy_price = holding.buy_price
        pnl_pct = (current_price - buy_price) / buy_price

        # 손절 체크
        if pnl_pct <= -conditions.stop_loss_pct:
            reasons.append(f"Stop loss triggered ({pnl_pct:.1%} <= -{conditions.stop_loss_pct:.1%})")

        # 익절 체크
        if pnl_pct >= conditions.take_profit_pct:
            reasons.append(f"Take profit reached ({pnl_pct:.1%} >= {conditions.take_profit_pct:.1%})")

        return reasons

    def check_technical_conditions(self, symbol: str, price_data: Dict) -> List[str]:
        """기술적 매도 조건 체크"""
        reasons = []
        tech_config = self.pm.get_technical_signals_config()

        if not price_data:
            return reasons

        current = price_data['current']
        ma_20 = price_data.get('ma_20')
        ma_60 = price_data.get('ma_60')
        prev_ma_20 = price_data.get('prev_ma_20')
        prev_ma_60 = price_data.get('prev_ma_60')

        # 20일 이평선 하향 돌파
        below_ma_config = tech_config.get('below_ma', {})
        if below_ma_config.get('enabled', False) and ma_20:
            if current < ma_20:
                reasons.append(f"Below {below_ma_config.get('period', 20)}-day MA (${current:.2f} < ${ma_20:.2f})")

        # 데스크로스 체크 (단기 < 장기)
        ma_cross_config = tech_config.get('ma_cross', {})
        if ma_cross_config.get('enabled', False) and ma_20 and ma_60 and prev_ma_20 and prev_ma_60:
            if ma_cross_config.get('signal') == 'death_cross':
                # 어제는 단기 >= 장기였는데, 오늘 단기 < 장기 (데스크로스)
                if prev_ma_20 >= prev_ma_60 and ma_20 < ma_60:
                    reasons.append(f"Death cross detected (MA20 crossed below MA60)")

        return reasons

    def check_holding(self, holding: Holding) -> Optional[SellCheckResult]:
        """단일 종목 매도 신호 체크"""
        symbol = holding.symbol
        conditions = self.pm.get_sell_conditions_for(symbol)

        # 현재가 조회
        current_price = self.get_current_price(symbol)
        if current_price is None:
            self.logger.warning(f"Could not get price for {symbol}")
            return None

        # 손익 계산
        pnl_pct = (current_price - holding.buy_price) / holding.buy_price

        # 가격 기반 조건 체크
        price_reasons = self.check_price_conditions(holding, current_price, conditions)

        # 기술적 조건 체크
        price_data = self.get_price_data(symbol)
        tech_reasons = self.check_technical_conditions(symbol, price_data)

        # 모든 이유 합치기
        all_reasons = price_reasons + tech_reasons

        # 신호 결정
        if price_reasons:  # 가격 조건 충족 = 매도
            signal = Signal.SELL
        elif tech_reasons:  # 기술적 조건만 = 주의
            signal = Signal.WATCH
        else:
            signal = Signal.HOLD

        return SellCheckResult(
            symbol=symbol,
            name=holding.name,
            buy_price=holding.buy_price,
            current_price=current_price,
            pnl_pct=pnl_pct,
            signal=signal,
            reasons=all_reasons if all_reasons else ["All conditions OK"],
            conditions=conditions
        )

    def check_all(self) -> List[SellCheckResult]:
        """모든 보유 종목 체크"""
        holdings = self.pm.get_holdings()
        results = []

        for holding in holdings:
            result = self.check_holding(holding)
            if result:
                results.append(result)

        return results

    def print_results(self, results: List[SellCheckResult]):
        """결과 출력"""
        now = get_current_market_time()
        print()
        print("=" * 80)
        print(f"PORTFOLIO SELL CHECK - {now.strftime('%Y-%m-%d %H:%M')} ET")
        print("=" * 80)
        print()

        if not results:
            print("No holdings to check. Add holdings to config/portfolio.yaml")
            return

        # 헤더
        print(f"{'종목명':<12} {'매수가':>12} {'현재가':>12} {'수익률':>8} {'신호':<6} 사유")
        print("-" * 80)

        # 결과 정렬: SELL > WATCH > HOLD
        signal_order = {Signal.SELL: 0, Signal.WATCH: 1, Signal.HOLD: 2}
        results.sort(key=lambda x: (signal_order[x.signal], -abs(x.pnl_pct)))

        sell_count = 0
        watch_count = 0
        hold_count = 0

        for r in results:
            # 이모지 및 색상
            if r.signal == Signal.SELL:
                emoji = "\U0001F534"  # 빨간 원
                sell_count += 1
            elif r.signal == Signal.WATCH:
                emoji = "\U0001F7E1"  # 노란 원
                watch_count += 1
            else:
                emoji = "\U0001F7E2"  # 초록 원
                hold_count += 1

            pnl_str = f"{r.pnl_pct:+.1%}"
            reason = r.reasons[0] if r.reasons else ""

            # 종목명 (최대 10자)
            name_display = r.name[:10] if len(r.name) > 10 else r.name

            print(f"{emoji} {name_display:<10} {r.buy_price:>12,.0f} {r.current_price:>12,.0f} {pnl_str:>8} {r.signal.value:<6} {reason}")

            # 추가 이유가 있으면 출력
            for extra_reason in r.reasons[1:]:
                print(f"{'':>56} {extra_reason}")

        print("-" * 80)
        print(f"Summary: {sell_count} SELL, {watch_count} WATCH, {hold_count} HOLD")
        print()


def main():
    parser = argparse.ArgumentParser(description="Check portfolio for sell signals")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    args = parser.parse_args()

    checker = PortfolioSellChecker(verbose=args.verbose)

    # 포트폴리오 확인
    holdings = checker.pm.get_holdings()
    if not holdings:
        print("\nNo holdings found in config/portfolio.yaml")
        print("Add your holdings first:")
        print("  holdings:")
        print("    AAPL:")
        print("      buy_price: 150.00")
        print("      quantity: 10")
        print("      buy_date: '2025-06-15'")
        return

    results = checker.check_all()
    checker.print_results(results)


if __name__ == "__main__":
    main()
