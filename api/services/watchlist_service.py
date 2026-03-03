"""
Watchlist Service.

Business logic for watchlist management and buy signal evaluation.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from api.database import SessionLocal
from api.models.watchlist import BuyRule, BuyRuleTemplate, WatchlistItem
from api.schemas.watchlist import (
    BuyRuleCreate,
    BuyRuleResponse,
    BuyRuleTemplateCreate,
    BuyRuleTemplateResponse,
    BuyRuleTemplateUpdate,
    BuyRuleUpdate,
    BuySignal,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistItemUpdate,
    _validate_buy_rule_params,
)
from utils.data_cache import get_cache

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for managing watchlist items and buy rules."""

    def __init__(self) -> None:
        self._cache = get_cache()

    # ── WatchlistItem CRUD ─────────────────────────────────────────

    def get_all_items(self, *, with_prices: bool = True) -> List[WatchlistItemResponse]:
        """Return all watchlist items with optional current prices."""
        db: Session = SessionLocal()
        try:
            rows = db.query(WatchlistItem).order_by(WatchlistItem.added_at.desc()).all()
            if not rows:
                return []

            tickers = [r.ticker for r in rows]
            prices: Dict[str, float] = {}
            change_pcts: Dict[str, Optional[float]] = {}
            currencies: Dict[str, str] = {}

            if with_prices and tickers:
                prices, change_pcts, currencies = self._fetch_market_data(tickers)

            return [
                self._item_to_response(row, prices, change_pcts, currencies, db)
                for row in rows
            ]
        finally:
            db.close()

    def get_item(self, item_id: int) -> Optional[WatchlistItemResponse]:
        """Get a single watchlist item by ID."""
        db: Session = SessionLocal()
        try:
            row = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
            if row is None:
                return None
            prices, change_pcts, currencies = self._fetch_market_data([row.ticker])
            return self._item_to_response(row, prices, change_pcts, currencies, db)
        finally:
            db.close()

    def get_item_by_ticker(self, ticker: str) -> Optional[WatchlistItemResponse]:
        """Get a single watchlist item by ticker."""
        db: Session = SessionLocal()
        try:
            row = db.query(WatchlistItem).filter(
                WatchlistItem.ticker == ticker.upper()
            ).first()
            if row is None:
                return None
            prices, change_pcts, currencies = self._fetch_market_data([row.ticker])
            return self._item_to_response(row, prices, change_pcts, currencies, db)
        finally:
            db.close()

    def create_item(self, data: WatchlistItemCreate) -> WatchlistItemResponse:
        """Add a new watchlist item. Raises ValueError if ticker already exists."""
        db: Session = SessionLocal()
        try:
            ticker = data.ticker.strip().upper()
            existing = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first()
            if existing:
                raise ValueError(f"Ticker {ticker} already in watchlist")

            row = WatchlistItem(
                ticker=ticker,
                name=data.name,
                target_price=data.target_price,
                note=data.note,
                tags=data.tags,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            prices, change_pcts, currencies = self._fetch_market_data([row.ticker])
            return self._item_to_response(row, prices, change_pcts, currencies, db)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_item(
        self, item_id: int, data: WatchlistItemUpdate
    ) -> Optional[WatchlistItemResponse]:
        """Update a watchlist item. Returns None if not found."""
        db: Session = SessionLocal()
        try:
            row = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
            if row is None:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for key, val in update_data.items():
                setattr(row, key, val)

            db.commit()
            db.refresh(row)

            prices, change_pcts, currencies = self._fetch_market_data([row.ticker])
            return self._item_to_response(row, prices, change_pcts, currencies, db)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_item(self, item_id: int) -> bool:
        """Delete a watchlist item and its rules. Returns False if not found."""
        db: Session = SessionLocal()
        try:
            row = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── BuyRule CRUD ───────────────────────────────────────────────

    def get_rules_for_item(self, item_id: int) -> List[BuyRuleResponse]:
        """Get all buy rules for a watchlist item."""
        db: Session = SessionLocal()
        try:
            rules = (
                db.query(BuyRule)
                .filter(BuyRule.watchlist_item_id == item_id)
                .order_by(BuyRule.created_at)
                .all()
            )
            return [self._rule_to_response(r) for r in rules]
        finally:
            db.close()

    def create_rule(self, item_id: int, data: BuyRuleCreate) -> BuyRuleResponse:
        """Create a buy rule for a watchlist item."""
        _validate_buy_rule_params(data.rule_type, data.params)

        db: Session = SessionLocal()
        try:
            item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
            if item is None:
                raise ValueError(f"Watchlist item {item_id} not found")

            rule = BuyRule(
                watchlist_item_id=item_id,
                rule_type=data.rule_type,
                params=data.params,
                is_active=data.is_active,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return self._rule_to_response(rule)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_rule(self, rule_id: int, data: BuyRuleUpdate) -> Optional[BuyRuleResponse]:
        """Update a buy rule. Returns None if not found."""
        db: Session = SessionLocal()
        try:
            rule = db.query(BuyRule).filter(BuyRule.id == rule_id).first()
            if rule is None:
                return None

            if data.params is not None:
                _validate_buy_rule_params(rule.rule_type, data.params)
                rule.params = data.params
            if data.is_active is not None:
                rule.is_active = data.is_active

            db.commit()
            db.refresh(rule)
            return self._rule_to_response(rule)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a buy rule. Returns False if not found."""
        db: Session = SessionLocal()
        try:
            rule = db.query(BuyRule).filter(BuyRule.id == rule_id).first()
            if rule is None:
                return False
            db.delete(rule)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── BuyRuleTemplate CRUD ──────────────────────────────────────

    def list_templates(self) -> List[BuyRuleTemplateResponse]:
        """Return all buy rule templates with linked rule counts."""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(BuyRuleTemplate)
                .order_by(BuyRuleTemplate.created_at.desc())
                .all()
            )
            if not rows:
                return []

            # Batch count to avoid N+1
            count_rows = (
                db.query(BuyRule.template_id, func.count(BuyRule.id))
                .filter(BuyRule.template_id.isnot(None))
                .group_by(BuyRule.template_id)
                .all()
            )
            count_map = {tid: cnt for tid, cnt in count_rows}

            return [
                self._template_to_response(t, linked_count=count_map.get(t.id, 0))
                for t in rows
            ]
        finally:
            db.close()

    def create_template(self, data: BuyRuleTemplateCreate) -> BuyRuleTemplateResponse:
        """Create a new buy rule template."""
        _validate_buy_rule_params(data.rule_type, data.params)

        db: Session = SessionLocal()
        try:
            existing = (
                db.query(BuyRuleTemplate)
                .filter(BuyRuleTemplate.name == data.name)
                .first()
            )
            if existing:
                raise ValueError(f"Template name '{data.name}' already exists")

            row = BuyRuleTemplate(
                name=data.name,
                rule_type=data.rule_type,
                params=data.params,
                description=data.description,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._template_to_response(row, db)
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Template name '{data.name}' already exists")
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_template(
        self, template_id: int, data: BuyRuleTemplateUpdate
    ) -> Optional[BuyRuleTemplateResponse]:
        """Update a template. Returns None if not found."""
        db: Session = SessionLocal()
        try:
            row = db.query(BuyRuleTemplate).filter(BuyRuleTemplate.id == template_id).first()
            if row is None:
                return None

            update_data = data.model_dump(exclude_unset=True)
            if "params" in update_data and update_data["params"] is not None:
                _validate_buy_rule_params(row.rule_type, update_data["params"])
            if "name" in update_data and update_data["name"] is not None:
                dup = (
                    db.query(BuyRuleTemplate)
                    .filter(BuyRuleTemplate.name == update_data["name"], BuyRuleTemplate.id != template_id)
                    .first()
                )
                if dup:
                    raise ValueError(f"Template name '{update_data['name']}' already exists")

            for key, val in update_data.items():
                setattr(row, key, val)

            db.commit()
            db.refresh(row)
            return self._template_to_response(row, db)
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Template name '{data.name}' already exists")
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_template(self, template_id: int) -> bool:
        """Delete a template. Returns False if not found."""
        db: Session = SessionLocal()
        try:
            row = db.query(BuyRuleTemplate).filter(BuyRuleTemplate.id == template_id).first()
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_rule_from_template(
        self, item_id: int, template_id: int, is_active: bool = True
    ) -> BuyRuleResponse:
        """Create a buy rule from a template, copying params and linking template_id."""
        db: Session = SessionLocal()
        try:
            item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
            if item is None:
                raise ValueError(f"Watchlist item {item_id} not found")

            template = db.query(BuyRuleTemplate).filter(BuyRuleTemplate.id == template_id).first()
            if template is None:
                raise ValueError(f"Template {template_id} not found")

            if not template.is_active:
                raise ValueError(f"Template {template_id} is inactive")

            # Prevent duplicate: same item + same template (app-level guard)
            existing = (
                db.query(BuyRule)
                .filter(
                    BuyRule.watchlist_item_id == item_id,
                    BuyRule.template_id == template_id,
                )
                .first()
            )
            if existing:
                raise ValueError(
                    f"Template {template_id} is already linked to item {item_id} (rule #{existing.id})"
                )

            rule = BuyRule(
                watchlist_item_id=item_id,
                template_id=template_id,
                rule_type=template.rule_type,
                params=dict(template.params),  # copy params
                is_active=is_active,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return self._rule_to_response(rule)
        except IntegrityError:
            db.rollback()
            raise ValueError(
                f"Template {template_id} is already linked to item {item_id}"
            )
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── Buy Signal Evaluation ──────────────────────────────────────

    def evaluate_buy_signals(self) -> List[BuySignal]:
        """Evaluate all active buy rules and return triggered signals."""
        db: Session = SessionLocal()
        try:
            items = (
                db.query(WatchlistItem)
                .options(joinedload(WatchlistItem.buy_rules))
                .all()
            )
            if not items:
                return []

            tickers = [item.ticker for item in items]
            prices, _, currencies = self._fetch_market_data(tickers)

            signals: List[BuySignal] = []

            for item in items:
                active_rules = [
                    r for r in item.buy_rules if r.is_active
                ]
                current_price = prices.get(item.ticker)
                currency = currencies.get(item.ticker)

                # Check target_price on the item itself
                if item.target_price and current_price is not None:
                    if current_price <= item.target_price:
                        signals.append(BuySignal(
                            ticker=item.ticker,
                            name=item.name,
                            signal_type="target_price",
                            reason=f"Current price {current_price:,.0f} is at or below target {item.target_price:,.0f}",
                            current_price=current_price,
                            target_price=item.target_price,
                            currency=currency,
                        ))

                # Check rule-based signals
                for rule in active_rules:
                    try:
                        triggered, reason = self._evaluate_single(
                            rule, item, current_price, db
                        )
                        if triggered and reason:
                            signals.append(BuySignal(
                                ticker=item.ticker,
                                name=item.name,
                                signal_type=rule.rule_type,
                                reason=reason,
                                current_price=current_price,
                                target_price=item.target_price,
                                currency=currency,
                                rule_id=rule.id,
                            ))
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(
                            "Failed to evaluate buy rule %d (%s) for %s: %s",
                            rule.id, rule.rule_type, item.ticker, e,
                        )

            # Read-only evaluation — don't persist state changes
            db.rollback()
            return signals
        finally:
            db.close()

    def _evaluate_single(
        self,
        rule: BuyRule,
        item: WatchlistItem,
        current_price: Optional[float],
        db: Session,
    ) -> tuple[bool, Optional[str]]:
        """Evaluate a single buy rule. Returns (triggered, reason)."""
        params = rule.params or {}

        if rule.rule_type == "target_price":
            price_target = params.get("price")
            if isinstance(price_target, bool) or not isinstance(price_target, (int, float)):
                return False, None
            if current_price is None:
                return False, None
            if current_price <= price_target:
                return True, f"Price {current_price:,.0f} reached target {price_target:,.0f}"
            return False, None

        elif rule.rule_type == "rsi_oversold":
            rsi_threshold = params.get("rsi", 30)
            if isinstance(rsi_threshold, bool) or not isinstance(rsi_threshold, (int, float)):
                return False, None

            rsi_value = self._get_rsi(item.ticker)
            if rsi_value is None:
                return False, None
            if rsi_value <= rsi_threshold:
                return True, f"RSI {rsi_value:.1f} is below threshold {rsi_threshold}"
            return False, None

        return False, None

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_rsi(self, ticker: str, period: int = 14) -> Optional[float]:
        """Calculate current RSI for a ticker."""
        try:
            data = self._cache.get(ticker, days=60, force_refresh=False)
            if data is None or data.empty or len(data) < period + 1:
                return None

            close = data["close"]
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            last_rsi = rsi.iloc[-1]
            if last_rsi is None or (hasattr(last_rsi, '__float__') and str(last_rsi) == 'nan'):
                return None
            return float(last_rsi)
        except Exception as e:
            logger.warning("Failed to compute RSI for %s: %s", ticker, e)
            return None

    def _fetch_market_data(
        self, tickers: List[str]
    ) -> tuple[Dict[str, float], Dict[str, Optional[float]], Dict[str, str]]:
        """Fetch current prices, change percentages, and currencies for tickers."""
        prices: Dict[str, float] = {}
        change_pcts: Dict[str, Optional[float]] = {}
        currencies: Dict[str, str] = {}

        for ticker in tickers:
            # Always infer currency from ticker suffix, regardless of cache success
            currencies[ticker] = self._infer_currency(ticker)
            try:
                data = self._cache.get(ticker, days=5, force_refresh=False)
                if data is not None and not data.empty:
                    price = float(data["close"].iloc[-1])
                    prices[ticker] = price

                    if len(data) >= 2:
                        prev = float(data["close"].iloc[-2])
                        if prev > 0:
                            change_pcts[ticker] = ((price - prev) / prev) * 100
            except Exception as e:
                logger.warning("Failed to fetch market data for %s: %s", ticker, e)

        return prices, change_pcts, currencies

    @staticmethod
    def _infer_currency(ticker: str) -> str:
        """Infer currency from ticker suffix convention."""
        upper = ticker.upper()
        if upper.endswith(".KS") or upper.endswith(".KQ"):
            return "KRW"
        if upper.endswith(".T"):
            return "JPY"
        if upper.endswith(".HK"):
            return "HKD"
        if upper.endswith(".L"):
            return "GBP"
        return "USD"

    @staticmethod
    def _item_to_response(
        row: WatchlistItem,
        prices: Dict[str, float],
        change_pcts: Dict[str, Optional[float]],
        currencies: Dict[str, str],
        db: Session,
    ) -> WatchlistItemResponse:
        """Convert ORM WatchlistItem to response schema."""
        active_rules = [r for r in row.buy_rules if r.is_active]
        return WatchlistItemResponse(
            id=row.id,
            ticker=row.ticker,
            name=row.name,
            target_price=row.target_price,
            current_price=prices.get(row.ticker),
            change_pct=change_pcts.get(row.ticker),
            currency=currencies.get(row.ticker),
            note=row.note,
            tags=row.tags,
            buy_rules_count=len(row.buy_rules),
            added_at=row.added_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _rule_to_response(rule: BuyRule) -> BuyRuleResponse:
        """Convert ORM BuyRule to response schema."""
        return BuyRuleResponse(
            id=rule.id,
            watchlist_item_id=rule.watchlist_item_id,
            template_id=rule.template_id,
            rule_type=rule.rule_type,
            params=rule.params or {},
            state_json=rule.state_json,
            is_active=rule.is_active,
            triggered_at=rule.triggered_at,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )

    @staticmethod
    def _template_to_response(
        template: BuyRuleTemplate,
        db: Optional[Session] = None,
        linked_count: Optional[int] = None,
    ) -> BuyRuleTemplateResponse:
        """Convert ORM BuyRuleTemplate to response schema."""
        if linked_count is None and db is not None:
            linked_count = (
                db.query(BuyRule)
                .filter(BuyRule.template_id == template.id)
                .count()
            )
        return BuyRuleTemplateResponse(
            id=template.id,
            name=template.name,
            rule_type=template.rule_type,
            params=template.params or {},
            description=template.description,
            is_active=template.is_active,
            linked_rules_count=linked_count or 0,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


# ── Singleton accessor ─────────────────────────────────────────────

_service: Optional[WatchlistService] = None


def get_watchlist_service() -> WatchlistService:
    global _service
    if _service is None:
        _service = WatchlistService()
    return _service
