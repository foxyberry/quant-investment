"""
Portfolio Manager Module
보유 종목 및 매도 조건 관리
"""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import date


@dataclass
class ConfigHolding:
    """
    YAML 설정 파일의 보유 종목 정보

    Note: 런타임 포트폴리오 관리에는 portfolio.holdings.Holding 사용
    """
    symbol: str
    name: str
    buy_price: float
    quantity: int
    buy_date: date

    def to_dict(self) -> Dict:
        """Holding 객체를 딕셔너리로 변환"""
        return {
            'name': self.name,
            'buy_price': self.buy_price,
            'quantity': self.quantity,
            'buy_date': self.buy_date.strftime('%Y-%m-%d'),
        }


@dataclass
class SellConditions:
    """매도 조건"""
    stop_loss_pct: float = 0.05      # 5% 손절
    take_profit_pct: float = 0.15    # 15% 익절
    trailing_stop_pct: float = 0.08  # 8% 트레일링 스탑

    @classmethod
    def from_dict(cls, data: Dict) -> 'SellConditions':
        return cls(
            stop_loss_pct=data.get('stop_loss_pct', 0.05),
            take_profit_pct=data.get('take_profit_pct', 0.15),
            trailing_stop_pct=data.get('trailing_stop_pct', 0.08)
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
        }


class PortfolioManager:
    """포트폴리오 관리 클래스"""

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent

        if config_path is None:
            config_path = self.project_root / "config" / "portfolio.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """포트폴리오 설정 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.logger.info(f"Portfolio config loaded from {self.config_path}")
                return config or {}
        except FileNotFoundError:
            self.logger.warning(f"Portfolio config not found: {self.config_path}")
            return self._get_default_config()
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'default_sell_conditions': {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.15,
                'trailing_stop_pct': 0.08
            },
            'technical_sell_signals': {},
            'holdings': {}
        }

    def save_config(self) -> bool:
        """설정을 YAML 파일로 저장"""
        try:
            # holdings를 직렬화 가능한 형태로 변환
            save_config = self.config.copy()
            if 'holdings' in save_config:
                holdings_dict = {}
                for symbol, holding in save_config['holdings'].items():
                    if isinstance(holding, ConfigHolding):
                        holdings_dict[symbol] = holding.to_dict()
                    else:
                        holdings_dict[symbol] = holding
                save_config['holdings'] = holdings_dict

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(save_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            self.logger.info(f"Portfolio config saved to {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            return False

    def get_default_sell_conditions(self) -> SellConditions:
        """기본 매도 조건 반환"""
        from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service

        conditions = get_portfolio_alert_config_service().get_default_sell_conditions()
        return SellConditions.from_dict(conditions)

    def get_technical_signals_config(self) -> Dict[str, Any]:
        """기술적 매도 신호 설정 반환"""
        from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service

        return get_portfolio_alert_config_service().get_technical_signals_config()

    def is_technical_signals_enabled(self) -> bool:
        """기술적 매도 신호 평가 활성화 여부 반환"""
        from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service

        return bool(get_portfolio_alert_config_service().get_config().technical_signals)

    def get_holdings(self) -> List[ConfigHolding]:
        """모든 보유 종목 반환 (DB에서 조회)"""
        try:
            from api.database import SessionLocal
            from api.models.portfolio import Holding as DBHolding
            db = SessionLocal()
            try:
                rows = db.query(DBHolding).filter(DBHolding.quantity > 0).all()
                return [
                    ConfigHolding(
                        symbol=row.ticker,
                        name=row.name or row.ticker,
                        buy_price=float(row.avg_price or 0),
                        quantity=int(row.quantity),
                        buy_date=row.bought_at or date.today(),
                    )
                    for row in rows
                ]
            finally:
                db.close()
        except Exception as e:
            self.logger.warning(f"Failed to load holdings from DB: {e}")
            return []

    def get_holding(self, symbol: str) -> Optional[ConfigHolding]:
        """특정 종목 정보 반환 (DB에서 조회)"""
        for h in self.get_holdings():
            if h.symbol == symbol or h.symbol.upper() == symbol.upper():
                return h
        return None

    def get_sell_conditions_for(self, symbol: str) -> SellConditions:
        """종목의 매도 조건 반환.

        Priority:
        1. DB-backed per-holding SellRule overrides
        2. Legacy YAML holding overrides (temporary compatibility)
        3. DB-backed global defaults
        """
        defaults = self.get_default_sell_conditions().to_dict()
        merged = defaults.copy()
        db_override_keys: set[str] = set()

        try:
            from api.database import SessionLocal
            from api.models.portfolio import SellRule

            db = SessionLocal()
            try:
                symbol_upper = symbol.upper()
                aliases = {symbol_upper}
                if symbol_upper.endswith(('.KS', '.KQ')):
                    aliases.add(symbol_upper.split('.')[0])
                elif '.' not in symbol_upper:
                    aliases.add(f"{symbol_upper}.KS")
                    aliases.add(f"{symbol_upper}.KQ")

                rules = (
                    db.query(SellRule)
                    .filter(SellRule.ticker.in_(list(aliases)), SellRule.is_active.is_(True))
                    .order_by(SellRule.created_at.asc())
                    .all()
                )
            finally:
                db.close()

            for rule in rules:
                params = rule.params or {}
                if rule.rule_type == 'stop_loss' and params.get('pct') is not None:
                    merged['stop_loss_pct'] = abs(float(params['pct'])) / 100
                    db_override_keys.add('stop_loss_pct')
                elif rule.rule_type == 'take_profit' and params.get('pct') is not None:
                    merged['take_profit_pct'] = abs(float(params['pct'])) / 100
                    db_override_keys.add('take_profit_pct')
                elif rule.rule_type == 'trailing_stop' and params.get('pct') is not None:
                    merged['trailing_stop_pct'] = abs(float(params['pct'])) / 100
                    db_override_keys.add('trailing_stop_pct')
        except Exception as e:
            self.logger.warning(f"Failed to load sell rule overrides from DB: {e}")

        holdings = self.config.get('holdings', {}) or {}
        holding_config = None
        for ticker, config in holdings.items():
            if ticker.upper() == symbol.upper():
                holding_config = config or {}
                break

        if holding_config:
            overrides = (
                holding_config.get('sell_conditions')
                or holding_config.get('custom_conditions')
                or {}
            )
            for key in ('stop_loss_pct', 'take_profit_pct', 'trailing_stop_pct'):
                if key in overrides and overrides[key] is not None and key not in db_override_keys:
                    merged[key] = overrides[key]
        return SellConditions.from_dict(merged)

    def add_holding(self, symbol: str, buy_price: float, quantity: int,
                    buy_date: date = None, custom_conditions: Dict = None) -> bool:
        """종목 추가 — DB를 통해 관리. 이 메서드는 하위 호환용."""
        self.logger.warning("PortfolioManager.add_holding is deprecated. Use the API.")
        return False

    def remove_holding(self, symbol: str) -> bool:
        """종목 제거 — DB를 통해 관리. 이 메서드는 하위 호환용."""
        self.logger.warning("PortfolioManager.remove_holding is deprecated. Use the API.")
        return False

    def update_holding(self, symbol: str, **kwargs) -> bool:
        """종목 정보 업데이트 — DB를 통해 관리. 이 메서드는 하위 호환용."""
        self.logger.warning("PortfolioManager.update_holding is deprecated. Use the API.")
        return False

    def get_symbols(self) -> List[str]:
        """보유 종목 심볼 목록 반환"""
        holdings = self.get_holdings()
        return [h.symbol for h in holdings]

    def calculate_pnl(self, symbol: str, current_price: float) -> Dict[str, float]:
        """손익 계산"""
        holding = self.get_holding(symbol)
        if not holding:
            return {}

        pnl_amount = (current_price - holding.buy_price) * holding.quantity
        pnl_pct = (current_price - holding.buy_price) / holding.buy_price
        total_value = current_price * holding.quantity
        cost_basis = holding.buy_price * holding.quantity

        return {
            'symbol': symbol,
            'buy_price': holding.buy_price,
            'current_price': current_price,
            'quantity': holding.quantity,
            'cost_basis': cost_basis,
            'current_value': total_value,
            'pnl_amount': pnl_amount,
            'pnl_pct': pnl_pct
        }

    def summary(self) -> str:
        """포트폴리오 요약 출력"""
        holdings = self.get_holdings()
        if not holdings:
            return "No holdings in portfolio"

        lines = ["Portfolio Summary", "=" * 50]
        for h in holdings:
            lines.append(f"{h.symbol}: {h.quantity} shares @ ${h.buy_price:.2f} (bought {h.buy_date})")

        return "\n".join(lines)
