"""API-side DB provider for PortfolioManager runtime data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Protocol

from api.database import SessionLocal
from api.models.portfolio import Holding as DBHolding
from api.models.portfolio import SellRule
from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service
from screener.portfolio_manager import ConfigHolding, PortfolioDataProvider, PortfolioManager


class PortfolioConfigServiceLike(Protocol):
    def get_default_sell_conditions(self) -> dict[str, float]:
        ...

    def get_technical_signals_config(self) -> dict[str, Any]:
        ...

    def get_config(self) -> Any:
        ...


@dataclass
class DBPortfolioDataProvider(PortfolioDataProvider):
    """Read portfolio runtime settings and holdings from the DB-backed API layer."""

    session_factory: Callable[[], Any] = SessionLocal
    config_service: PortfolioConfigServiceLike | None = None

    def __post_init__(self) -> None:
        if self.config_service is None:
            self.config_service = get_portfolio_alert_config_service()

    def get_default_sell_conditions(self) -> dict[str, float]:
        return self.config_service.get_default_sell_conditions()

    def get_technical_signals_config(self) -> dict[str, Any]:
        return self.config_service.get_technical_signals_config()

    def is_technical_signals_enabled(self) -> bool:
        return bool(self.config_service.get_config().technical_signals)

    def get_holdings(self) -> list[ConfigHolding]:
        db = self.session_factory()
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

    def get_sell_condition_overrides(self, symbol: str) -> dict[str, float]:
        db = self.session_factory()
        rules: list[SellRule] = []
        try:
            symbol_upper = symbol.upper()
            aliases = {symbol_upper}
            if symbol_upper.endswith((".KS", ".KQ")):
                aliases.add(symbol_upper.split(".")[0])
            elif "." not in symbol_upper:
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

        overrides: dict[str, float] = {}
        for rule in rules:
            params = rule.params or {}
            pct = params.get("pct")
            if pct is None:
                continue
            normalized_pct = abs(float(pct)) / 100
            if rule.rule_type == "stop_loss":
                overrides["stop_loss_pct"] = normalized_pct
            elif rule.rule_type == "take_profit":
                overrides["take_profit_pct"] = normalized_pct
            elif rule.rule_type == "trailing_stop":
                overrides["trailing_stop_pct"] = normalized_pct

        return overrides


def build_db_portfolio_manager(config_path: str | None = None) -> PortfolioManager:
    """Construct a PortfolioManager with the DB-backed API provider."""
    return PortfolioManager(config_path=config_path, provider=DBPortfolioDataProvider())
