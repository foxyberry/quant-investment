"""Sell rule CRUD and evaluation service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding, SellRule
from api.schemas.portfolio import (
    SellRuleEvaluateResult,
    SellRuleResponse,
    _validate_sell_rule_params,
)
from portfolio.conditions import (
    HoldingPeriodCondition,
    StopLossCondition,
    TakeProfitCondition,
    TrailingStopCondition,
    TradingContext,
)
from utils.data_cache import get_cache

logger = logging.getLogger(__name__)


def _rule_row_to_response(row: SellRule) -> SellRuleResponse:
    """Convert a SellRule ORM row to a SellRuleResponse."""
    return SellRuleResponse(
        id=row.id,
        ticker=row.ticker,
        rule_type=row.rule_type,
        params=json.loads(row.params) if row.params else {},
        state_json=json.loads(row.state_json) if row.state_json else None,
        is_active=row.is_active,
        triggered_at=row.triggered_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SellRuleService:
    """Manage per-holding sell rules: CRUD + on-demand evaluation."""

    # -- CRUD ---------------------------------------------------------------

    def get_rules_for_ticker(self, ticker: str) -> List[SellRuleResponse]:
        db = SessionLocal()
        try:
            rows = (
                db.query(SellRule)
                .filter(SellRule.ticker == ticker)
                .order_by(SellRule.created_at)
                .all()
            )
            return [_rule_row_to_response(r) for r in rows]
        finally:
            db.close()

    def create_rule(self, ticker: str, rule_type: str, params: dict, is_active: bool = True) -> SellRuleResponse:
        db = SessionLocal()
        try:
            holding = db.get(Holding, ticker)
            if not holding:
                raise ValueError(f"Holding not found: {ticker}")

            # Validate params (defense-in-depth; Pydantic also validates on the API layer)
            validated = _validate_sell_rule_params(rule_type, params)

            row = SellRule(
                ticker=ticker,
                rule_type=rule_type,
                params=json.dumps(validated),
                is_active=is_active,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _rule_row_to_response(row)
        finally:
            db.close()

    def update_rule(self, rule_id: int, params: Optional[dict] = None, is_active: Optional[bool] = None) -> Optional[SellRuleResponse]:
        db = SessionLocal()
        try:
            row = db.get(SellRule, rule_id)
            if not row:
                return None

            if params is not None:
                validated = _validate_sell_rule_params(row.rule_type, params)
                row.params = json.dumps(validated)

            if is_active is not None:
                row.is_active = is_active
                # Reset triggered state when re-activating
                if is_active and row.triggered_at:
                    row.triggered_at = None
                    row.state_json = None

            db.commit()
            db.refresh(row)
            return _rule_row_to_response(row)
        finally:
            db.close()

    def delete_rule(self, rule_id: int) -> bool:
        db = SessionLocal()
        try:
            row = db.get(SellRule, rule_id)
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True
        finally:
            db.close()

    # -- Evaluation ---------------------------------------------------------

    def get_tickers_with_rules(self) -> set[str]:
        """Return the set of tickers that have at least one active sell rule."""
        db = SessionLocal()
        try:
            rows = (
                db.query(SellRule.ticker)
                .filter(SellRule.is_active.is_(True))
                .distinct()
                .all()
            )
            return {r[0] for r in rows}
        finally:
            db.close()

    def evaluate_all(self, *, persist: bool = True) -> List[SellRuleEvaluateResult]:
        """Evaluate all active, non-triggered sell rules across holdings.

        Args:
            persist: If True, write state_json and triggered_at back to DB.
                     Set False for read-only evaluation (e.g. GET /sell-signals).
        """
        db = SessionLocal()
        try:
            rules = (
                db.query(SellRule)
                .filter(SellRule.is_active.is_(True), SellRule.triggered_at.is_(None))
                .all()
            )
            if not rules:
                return []

            # Collect unique tickers
            tickers = list({r.ticker for r in rules})

            # Fetch holdings + current prices
            holdings_map: dict[str, Holding] = {}
            prices_map: dict[str, float] = {}
            for ticker in tickers:
                h = db.get(Holding, ticker)
                if h:
                    holdings_map[ticker] = h
                    price = self._get_current_price(ticker)
                    if price is not None:
                        prices_map[ticker] = price

            results: list[SellRuleEvaluateResult] = []

            for rule in rules:
                holding = holdings_map.get(rule.ticker)
                if not holding:
                    continue
                current_price = prices_map.get(rule.ticker)
                if current_price is None:
                    continue

                triggered, reason = self._evaluate_single(rule, holding, current_price, db)
                pnl_pct = None
                if holding.avg_price and holding.avg_price > 0:
                    pnl_pct = round((current_price - holding.avg_price) / holding.avg_price * 100, 2)

                results.append(SellRuleEvaluateResult(
                    rule_id=rule.id,
                    ticker=rule.ticker,
                    rule_type=rule.rule_type,
                    triggered=triggered,
                    reason=reason,
                    current_price=current_price,
                    pnl_pct=pnl_pct,
                ))

            if persist:
                db.commit()  # persist any state_json / triggered_at updates
            else:
                db.rollback()  # discard state changes for read-only mode

            return results
        finally:
            db.close()

    def _evaluate_single(
        self, rule: SellRule, holding: Holding, current_price: float, db: Any
    ) -> tuple[bool, Optional[str]]:
        """Evaluate a single rule. Returns (triggered, reason). May update rule state."""
        try:
            params = json.loads(rule.params) if rule.params else {}
            state = json.loads(rule.state_json) if rule.state_json else {}
        except (json.JSONDecodeError, TypeError):
            return False, f"Invalid JSON in rule {rule.id}"

        # Build TradingContext
        bought_at_dt = None
        if holding.bought_at:
            bought_at_dt = datetime.combine(holding.bought_at, datetime.min.time())

        ctx = TradingContext(
            ticker=holding.ticker,
            current_price=current_price,
            avg_price=holding.avg_price,
            quantity=holding.quantity,
            high_since_buy=state.get("high_watermark"),
            bought_at=bought_at_dt,
        )

        triggered = False
        reason: Optional[str] = None

        try:
            if rule.rule_type == "stop_loss":
                cond = StopLossCondition(pct=params["pct"] / 100)  # conditions.py uses decimal
                triggered = cond.should_sell(ctx)
                if triggered:
                    reason = cond.get_reason()

            elif rule.rule_type == "take_profit":
                cond = TakeProfitCondition(pct=params["pct"] / 100)
                triggered = cond.should_sell(ctx)
                if triggered:
                    reason = cond.get_reason()

            elif rule.rule_type == "trailing_stop":
                # Update high watermark
                hwm = state.get("high_watermark", current_price)
                if current_price > hwm:
                    hwm = current_price
                state["high_watermark"] = hwm
                rule.state_json = json.dumps(state)

                ctx.high_since_buy = hwm
                cond = TrailingStopCondition(pct=params["pct"] / 100)
                triggered = cond.should_sell(ctx)
                if triggered:
                    reason = cond.get_reason()

            elif rule.rule_type == "holding_period":
                if not bought_at_dt:
                    return False, "Cannot evaluate holding_period: bought_at date is missing"
                cond = HoldingPeriodCondition(max_days=params["max_days"])
                triggered = cond.should_sell(ctx)
                if triggered:
                    reason = cond.get_reason()

        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Rule %d (%s) evaluation error: %s", rule.id, rule.rule_type, e)
            return False, f"Evaluation error: {e}"

        if triggered:
            rule.triggered_at = datetime.utcnow()

        return triggered, reason

    @staticmethod
    def _get_current_price(ticker: str) -> Optional[float]:
        """Fetch current price via data cache (yfinance)."""
        try:
            cache: Any = get_cache()
            df = cache.get(ticker, period="5d")
            if df is not None and not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception:
            logger.debug("Price fetch failed for %s", ticker, exc_info=True)
        return None


_sell_rule_service: Optional[SellRuleService] = None


def get_sell_rule_service() -> SellRuleService:
    global _sell_rule_service
    if _sell_rule_service is None:
        _sell_rule_service = SellRuleService()
    return _sell_rule_service
