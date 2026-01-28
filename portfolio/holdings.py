"""
Holdings Management
보유 종목 관리

Usage:
    from portfolio.holdings import Portfolio

    portfolio = Portfolio()
    portfolio.add("005930.KS", name="삼성전자", quantity=10, avg_price=70000)

    holding = portfolio.get("005930.KS")
    print(f"Quantity: {holding.quantity}, Avg Price: {holding.avg_price}")
"""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date


@dataclass
class Holding:
    """단일 보유 종목 정보"""
    ticker: str
    name: str
    quantity: int
    avg_price: float
    bought_at: date
    note: Optional[str] = None
    transactions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "bought_at": self.bought_at.isoformat(),
            "note": self.note,
            "transactions": self.transactions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Holding":
        """딕셔너리에서 생성"""
        bought_at = data.get("bought_at")
        if isinstance(bought_at, str):
            bought_at = date.fromisoformat(bought_at)
        elif isinstance(bought_at, datetime):
            bought_at = bought_at.date()
        elif bought_at is None:
            bought_at = date.today()

        return cls(
            ticker=data["ticker"],
            name=data.get("name", data["ticker"]),
            quantity=int(data.get("quantity", 0)),
            avg_price=float(data.get("avg_price", 0)),
            bought_at=bought_at,
            note=data.get("note"),
            transactions=data.get("transactions", []),
        )

    @property
    def total_cost(self) -> float:
        """총 매수 금액"""
        return self.quantity * self.avg_price

    def calculate_pnl(self, current_price: float) -> Dict[str, float]:
        """손익 계산"""
        current_value = self.quantity * current_price
        pnl_amount = current_value - self.total_cost
        pnl_pct = (pnl_amount / self.total_cost * 100) if self.total_cost > 0 else 0

        return {
            "current_price": current_price,
            "current_value": current_value,
            "cost_basis": self.total_cost,
            "pnl_amount": pnl_amount,
            "pnl_pct": pnl_pct,
        }


class Portfolio:
    """포트폴리오 관리 클래스"""

    DEFAULT_PATH = Path(__file__).parent.parent / "config" / "portfolio.yaml"

    def __init__(self, filepath: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.filepath = Path(filepath) if filepath else self.DEFAULT_PATH
        self._holdings: Dict[str, Holding] = {}
        self._load()

    def _load(self):
        """파일에서 로드"""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                holdings = data.get("holdings", [])
                for holding_data in holdings:
                    holding = Holding.from_dict(holding_data)
                    self._holdings[holding.ticker] = holding
                self.logger.info(f"Loaded {len(self._holdings)} holdings")
            except Exception as e:
                self.logger.warning(f"Failed to load portfolio: {e}")

    def _save(self):
        """파일에 저장"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "holdings": [h.to_dict() for h in self._holdings.values()]
        }

        with open(self.filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def add(
        self,
        ticker: str,
        quantity: int,
        avg_price: float,
        name: Optional[str] = None,
        bought_at: Optional[date] = None,
        note: Optional[str] = None
    ) -> Holding:
        """
        종목 추가 또는 추가 매수

        추가 매수 시 평균 매수가 자동 계산
        """
        if bought_at is None:
            bought_at = date.today()

        if name is None:
            name = ticker

        existing = self._holdings.get(ticker)

        if existing:
            # 추가 매수: 평균 매수가 계산
            total_cost = existing.total_cost + (quantity * avg_price)
            new_quantity = existing.quantity + quantity
            new_avg_price = total_cost / new_quantity if new_quantity > 0 else 0

            existing.quantity = new_quantity
            existing.avg_price = new_avg_price
            existing.transactions.append({
                "type": "BUY",
                "quantity": quantity,
                "price": avg_price,
                "date": bought_at.isoformat(),
            })
            if note:
                existing.note = note

            holding = existing
        else:
            # 신규 추가
            holding = Holding(
                ticker=ticker,
                name=name,
                quantity=quantity,
                avg_price=avg_price,
                bought_at=bought_at,
                note=note,
                transactions=[{
                    "type": "BUY",
                    "quantity": quantity,
                    "price": avg_price,
                    "date": bought_at.isoformat(),
                }]
            )
            self._holdings[ticker] = holding

        self._save()
        self.logger.info(f"Added/Updated holding: {ticker} ({quantity} @ {avg_price})")
        return holding

    def get(self, ticker: str) -> Optional[Holding]:
        """종목 조회"""
        return self._holdings.get(ticker)

    def remove(self, ticker: str) -> bool:
        """종목 전체 매도/삭제"""
        if ticker in self._holdings:
            del self._holdings[ticker]
            self._save()
            self.logger.info(f"Removed holding: {ticker}")
            return True
        return False

    def sell(
        self,
        ticker: str,
        quantity: int,
        price: Optional[float] = None
    ) -> Optional[Holding]:
        """
        부분 매도

        Args:
            ticker: 종목 코드
            quantity: 매도 수량
            price: 매도 가격 (기록용)

        Returns:
            업데이트된 Holding 또는 None (전량 매도 시)
        """
        holding = self._holdings.get(ticker)
        if not holding:
            self.logger.warning(f"Holding not found: {ticker}")
            return None

        if quantity >= holding.quantity:
            # 전량 매도
            self.remove(ticker)
            return None

        # 부분 매도
        holding.quantity -= quantity
        holding.transactions.append({
            "type": "SELL",
            "quantity": quantity,
            "price": price,
            "date": date.today().isoformat(),
        })

        self._save()
        self.logger.info(f"Sold {quantity} shares of {ticker}")
        return holding

    def update(
        self,
        ticker: str,
        quantity: Optional[int] = None,
        avg_price: Optional[float] = None,
        name: Optional[str] = None,
        note: Optional[str] = None
    ) -> Optional[Holding]:
        """종목 정보 업데이트"""
        holding = self._holdings.get(ticker)
        if not holding:
            self.logger.warning(f"Holding not found: {ticker}")
            return None

        if quantity is not None:
            holding.quantity = quantity
        if avg_price is not None:
            holding.avg_price = avg_price
        if name is not None:
            holding.name = name
        if note is not None:
            holding.note = note

        self._save()
        return holding

    def get_all(self) -> List[Holding]:
        """모든 보유 종목"""
        return list(self._holdings.values())

    def get_tickers(self) -> List[str]:
        """보유 종목 코드 목록"""
        return list(self._holdings.keys())

    def total_value(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """
        포트폴리오 총 가치 계산

        Args:
            prices: {ticker: current_price} 딕셔너리

        Returns:
            총 가치, 총 손익 등
        """
        total_cost = 0
        total_current = 0
        details = []

        for holding in self._holdings.values():
            current_price = prices.get(holding.ticker, holding.avg_price)
            pnl = holding.calculate_pnl(current_price)

            total_cost += pnl["cost_basis"]
            total_current += pnl["current_value"]
            details.append({
                "ticker": holding.ticker,
                "name": holding.name,
                **pnl
            })

        total_pnl = total_current - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_cost": total_cost,
            "total_value": total_current,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "holdings": details,
        }

    def summary(self) -> str:
        """포트폴리오 요약"""
        holdings = self.get_all()
        if not holdings:
            return "No holdings in portfolio"

        lines = [
            "=" * 60,
            "PORTFOLIO SUMMARY",
            "=" * 60,
        ]

        for h in holdings:
            lines.append(
                f"{h.ticker}: {h.quantity} shares @ {h.avg_price:,.0f} "
                f"(Total: {h.total_cost:,.0f})"
            )

        lines.append("=" * 60)
        lines.append(f"Total Holdings: {len(holdings)}")

        return "\n".join(lines)

    def __contains__(self, ticker: str) -> bool:
        return ticker in self._holdings

    def __len__(self) -> int:
        return len(self._holdings)
