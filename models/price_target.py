"""
Price Target Model
목표가 관리 모델

Usage:
    from models.price_target import PriceTargets

    targets = PriceTargets()
    targets.set("005930.KS", buy=70000, sell=80000, stop_loss=65000, take_profit=90000)

    target = targets.get("005930.KS")
    print(f"Buy: {target.buy}, Stop Loss: {target.stop_loss}")
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import yaml


@dataclass
class PriceTarget:
    """가격 목표 데이터"""
    ticker: str
    buy: Optional[float] = None
    sell: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Percentage-based targets (alternative)
    stop_loss_pct: Optional[float] = None  # e.g., -7% from buy
    take_profit_pct: Optional[float] = None  # e.g., +15% from buy

    note: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

        # Validation
        self._validate()

    def _validate(self):
        """목표가 유효성 검증"""
        if self.buy and self.stop_loss:
            if self.stop_loss >= self.buy:
                raise ValueError(f"stop_loss ({self.stop_loss}) must be less than buy ({self.buy})")

        if self.buy and self.take_profit:
            if self.take_profit <= self.buy:
                raise ValueError(f"take_profit ({self.take_profit}) must be greater than buy ({self.buy})")

        if self.stop_loss and self.take_profit:
            if self.stop_loss >= self.take_profit:
                raise ValueError(f"stop_loss ({self.stop_loss}) must be less than take_profit ({self.take_profit})")

    def calculate_from_pct(self, buy_price: float) -> "PriceTarget":
        """
        퍼센트 기반 목표가 계산

        Args:
            buy_price: 매수 가격

        Returns:
            계산된 PriceTarget
        """
        new_target = PriceTarget(
            ticker=self.ticker,
            buy=buy_price,
            note=self.note,
        )

        if self.stop_loss_pct:
            new_target.stop_loss = buy_price * (1 + self.stop_loss_pct)

        if self.take_profit_pct:
            new_target.take_profit = buy_price * (1 + self.take_profit_pct)

        return new_target

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "ticker": self.ticker,
            "buy": self.buy,
            "sell": self.sell,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "note": self.note,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriceTarget":
        """딕셔너리에서 생성"""
        return cls(
            ticker=data["ticker"],
            buy=data.get("buy"),
            sell=data.get("sell"),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            stop_loss_pct=data.get("stop_loss_pct"),
            take_profit_pct=data.get("take_profit_pct"),
            note=data.get("note"),
            updated_at=data.get("updated_at"),
        )


class PriceTargets:
    """가격 목표 관리 클래스"""

    DEFAULT_PATH = Path(__file__).parent.parent / "config" / "price_targets.yaml"

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = Path(filepath) if filepath else self.DEFAULT_PATH
        self._targets: Dict[str, PriceTarget] = {}
        self._load()

    def _load(self):
        """파일에서 로드"""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                targets = data.get("price_targets", [])
                for target_data in targets:
                    target = PriceTarget.from_dict(target_data)
                    self._targets[target.ticker] = target
            except Exception as e:
                print(f"Warning: Failed to load price targets: {e}")

    def _save(self):
        """파일에 저장"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "price_targets": [t.to_dict() for t in self._targets.values()]
        }

        with open(self.filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def set(
        self,
        ticker: str,
        buy: Optional[float] = None,
        sell: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        note: Optional[str] = None
    ) -> PriceTarget:
        """
        가격 목표 설정

        Args:
            ticker: 종목 코드
            buy: 매수 목표가
            sell: 매도 목표가
            stop_loss: 손절가
            take_profit: 익절가
            stop_loss_pct: 손절 퍼센트 (e.g., -0.07 for -7%)
            take_profit_pct: 익절 퍼센트 (e.g., 0.15 for +15%)
            note: 메모

        Returns:
            설정된 PriceTarget
        """
        target = PriceTarget(
            ticker=ticker,
            buy=buy,
            sell=sell,
            stop_loss=stop_loss,
            take_profit=take_profit,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            note=note,
        )
        self._targets[ticker] = target
        self._save()
        return target

    def get(self, ticker: str) -> Optional[PriceTarget]:
        """가격 목표 조회"""
        return self._targets.get(ticker)

    def remove(self, ticker: str) -> bool:
        """가격 목표 삭제"""
        if ticker in self._targets:
            del self._targets[ticker]
            self._save()
            return True
        return False

    def get_all(self) -> Dict[str, PriceTarget]:
        """모든 가격 목표"""
        return self._targets.copy()

    def check_alerts(self, ticker: str, current_price: float) -> Dict[str, Any]:
        """
        현재가 대비 알림 체크

        Returns:
            {
                "ticker": str,
                "current_price": float,
                "alerts": [{"type": str, "message": str}, ...]
            }
        """
        target = self.get(ticker)
        if not target:
            return {"ticker": ticker, "current_price": current_price, "alerts": []}

        alerts = []

        # Buy alert
        if target.buy and current_price <= target.buy:
            alerts.append({
                "type": "BUY",
                "message": f"Price ({current_price:,.0f}) reached buy target ({target.buy:,.0f})"
            })

        # Stop loss alert
        if target.stop_loss and current_price <= target.stop_loss:
            alerts.append({
                "type": "STOP_LOSS",
                "message": f"Price ({current_price:,.0f}) hit stop loss ({target.stop_loss:,.0f})"
            })

        # Take profit alert
        if target.take_profit and current_price >= target.take_profit:
            alerts.append({
                "type": "TAKE_PROFIT",
                "message": f"Price ({current_price:,.0f}) reached take profit ({target.take_profit:,.0f})"
            })

        # Approaching targets (within 5%)
        if target.buy and current_price > target.buy:
            distance_pct = (current_price - target.buy) / target.buy
            if distance_pct <= 0.05:
                alerts.append({
                    "type": "APPROACHING_BUY",
                    "message": f"Price approaching buy target ({distance_pct:.1%} away)"
                })

        return {
            "ticker": ticker,
            "current_price": current_price,
            "target": target.to_dict(),
            "alerts": alerts
        }

    def __contains__(self, ticker: str) -> bool:
        return ticker in self._targets

    def __len__(self) -> int:
        return len(self._targets)


# Convenience functions
def set_price_targets(
    ticker: str,
    buy: Optional[float] = None,
    sell: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
) -> PriceTarget:
    """가격 목표 설정 (편의 함수)"""
    targets = PriceTargets()
    return targets.set(ticker, buy=buy, sell=sell, stop_loss=stop_loss, take_profit=take_profit)


def get_price_targets(ticker: str) -> Optional[PriceTarget]:
    """가격 목표 조회 (편의 함수)"""
    targets = PriceTargets()
    return targets.get(ticker)
