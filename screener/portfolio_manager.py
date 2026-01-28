"""
Portfolio Manager Module
보유 종목 및 매도 조건 관리
"""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date


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
    custom_conditions: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, symbol: str, data: Dict) -> 'ConfigHolding':
        """딕셔너리에서 Holding 객체 생성"""
        buy_date = data.get('buy_date')
        if isinstance(buy_date, str):
            buy_date = datetime.strptime(buy_date, '%Y-%m-%d').date()
        elif isinstance(buy_date, datetime):
            buy_date = buy_date.date()

        return cls(
            symbol=symbol,
            name=data.get('name', symbol),
            buy_price=float(data.get('buy_price', 0)),
            quantity=int(data.get('quantity', 0)),
            buy_date=buy_date,
            custom_conditions=data.get('custom_conditions', {})
        )

    def to_dict(self) -> Dict:
        """Holding 객체를 딕셔너리로 변환"""
        result = {
            'name': self.name,
            'buy_price': self.buy_price,
            'quantity': self.quantity,
            'buy_date': self.buy_date.strftime('%Y-%m-%d')
        }
        if self.custom_conditions:
            result['custom_conditions'] = self.custom_conditions
        return result


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
        conditions = self.config.get('default_sell_conditions', {})
        return SellConditions.from_dict(conditions)

    def get_technical_signals_config(self) -> Dict[str, Any]:
        """기술적 매도 신호 설정 반환"""
        return self.config.get('technical_sell_signals', {})

    def get_holdings(self) -> List[ConfigHolding]:
        """모든 보유 종목 반환"""
        holdings = []
        holdings_data = self.config.get('holdings', {})

        if holdings_data is None:
            return holdings

        for symbol, data in holdings_data.items():
            if data is None:
                continue
            try:
                holding = ConfigHolding.from_dict(symbol, data)
                holdings.append(holding)
            except Exception as e:
                self.logger.warning(f"Failed to parse holding {symbol}: {e}")

        return holdings

    def get_holding(self, symbol: str) -> Optional[ConfigHolding]:
        """특정 종목 정보 반환"""
        holdings_data = self.config.get('holdings', {})
        if symbol in holdings_data and holdings_data[symbol]:
            return Holding.from_dict(symbol, holdings_data[symbol])
        return None

    def get_sell_conditions_for(self, symbol: str) -> SellConditions:
        """특정 종목의 매도 조건 반환 (커스텀 조건 우선)"""
        default = self.get_default_sell_conditions()
        holding = self.get_holding(symbol)

        if holding and holding.custom_conditions:
            # 커스텀 조건으로 기본값 오버라이드
            return SellConditions(
                stop_loss_pct=holding.custom_conditions.get('stop_loss_pct', default.stop_loss_pct),
                take_profit_pct=holding.custom_conditions.get('take_profit_pct', default.take_profit_pct),
                trailing_stop_pct=holding.custom_conditions.get('trailing_stop_pct', default.trailing_stop_pct)
            )
        return default

    def add_holding(self, symbol: str, buy_price: float, quantity: int,
                    buy_date: date = None, custom_conditions: Dict = None) -> bool:
        """종목 추가"""
        if buy_date is None:
            buy_date = date.today()

        if 'holdings' not in self.config or self.config['holdings'] is None:
            self.config['holdings'] = {}

        holding_data = {
            'buy_price': buy_price,
            'quantity': quantity,
            'buy_date': buy_date.strftime('%Y-%m-%d')
        }
        if custom_conditions:
            holding_data['custom_conditions'] = custom_conditions

        self.config['holdings'][symbol.upper()] = holding_data
        self.logger.info(f"Added holding: {symbol.upper()}")
        return self.save_config()

    def remove_holding(self, symbol: str) -> bool:
        """종목 제거"""
        holdings = self.config.get('holdings', {})
        if symbol.upper() in holdings:
            del holdings[symbol.upper()]
            self.logger.info(f"Removed holding: {symbol.upper()}")
            return self.save_config()
        return False

    def update_holding(self, symbol: str, **kwargs) -> bool:
        """종목 정보 업데이트"""
        holdings = self.config.get('holdings', {})
        symbol = symbol.upper()

        if symbol not in holdings:
            self.logger.warning(f"Holding not found: {symbol}")
            return False

        for key, value in kwargs.items():
            if key == 'buy_date' and isinstance(value, date):
                value = value.strftime('%Y-%m-%d')
            holdings[symbol][key] = value

        return self.save_config()

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
