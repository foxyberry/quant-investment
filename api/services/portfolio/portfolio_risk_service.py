"""
Portfolio Risk Service.

Handles sell-rule CRUD, preset management, rule evaluation engine,
and sell signal detection (combining DB rules with global thresholds).
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from api.database import SessionLocal
from api.models.portfolio import Holding, SellRule, SellRulePreset
from api.schemas.portfolio import (
    SellSignal,
    SellRuleCreate,
    SellRuleUpdate,
    SellRuleResponse,
    SellRuleEvaluateResult,
    SellRuleEvaluateResponse,
    SellRulePresetCreate,
    SellRulePresetUpdate,
    SellRulePresetResponse,
    SellRulePresetItem,
    _validate_sell_rule_params,
)
from portfolio.conditions import (
    TradingContext,
    StopLossCondition,
    TakeProfitCondition,
    TrailingStopCondition,
    HoldingPeriodCondition,
)
from api.services.portfolio.portfolio_execution_service import PortfolioExecutionService

logger = logging.getLogger(__name__)


class PortfolioRiskService(PortfolioExecutionService):
    """
    Extends PortfolioExecutionService with sell-rule and risk evaluation.

    Responsible for managing sell rules, presets, evaluating conditions,
    and producing sell signals.
    """

    # Map rule_type -> condition factory.  Each factory accepts the
    # rule's params dict and returns a BaseTradingCondition instance.
    _RULE_FACTORIES = {
        "stop_loss": lambda p: StopLossCondition(pct=abs(p["pct"]) / 100),
        "take_profit": lambda p: TakeProfitCondition(pct=abs(p["pct"]) / 100),
        "trailing_stop": lambda p: TrailingStopCondition(pct=abs(p["pct"]) / 100),
        "holding_period": lambda p: HoldingPeriodCondition(max_days=p["max_days"]),
    }

    # ── Sell signal detection ─────────────────────────────────────────

    def get_sell_signals(
        self,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> List[SellSignal]:
        """Get sell signals combining DB rules and global thresholds.

        For holdings with active DB rules: evaluate those rules.
        For holdings without rules: fall back to global stop_loss/take_profit.

        Args:
            stop_loss_pct: Global stop loss threshold (default: -10%)
            take_profit_pct: Global take profit threshold (default: +20%)

        Returns:
            List of SellSignal objects
        """
        stop_loss = stop_loss_pct if stop_loss_pct is not None else self.STOP_LOSS_PCT
        take_profit = take_profit_pct if take_profit_pct is not None else self.TAKE_PROFIT_PCT

        signals: List[SellSignal] = []
        holdings = self.get_all_holdings(with_prices=True)

        # Load DB rule evaluation results (read-only, no state mutation)
        rule_eval = self.evaluate_sell_rules(dry_run=True)
        # Only skip global fallback for tickers where evaluation succeeded
        tickers_with_rules: set[str] = set()
        for result in rule_eval.results:
            # Skip fallback only for successful evaluations (not errors/unavailable)
            if not (result.reason and result.reason.startswith("Evaluation error")):
                tickers_with_rules.add(result.ticker)
            if result.triggered:
                # Find matching holding for name/avg_price
                h = next((h for h in holdings if h.ticker == result.ticker), None)
                if h is None:
                    continue
                signals.append(SellSignal(
                    ticker=result.ticker,
                    name=h.name or h.ticker,
                    signal_type=result.rule_type,
                    reason=result.reason or "",
                    current_price=result.current_price or 0.0,
                    trigger_price=result.trigger_value,
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct or 0.0,
                    currency=h.currency,
                    rule_id=result.rule_id,
                ))

        # Fall back to global thresholds for holdings without DB rules
        for h in holdings:
            if h.ticker in tickers_with_rules:
                continue
            if h.pnl_pct is None or h.current_price is None:
                continue

            signal = None
            if h.pnl_pct <= stop_loss:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="stop_loss",
                    reason=f"Loss exceeded {stop_loss}% threshold (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + stop_loss / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                )
            elif h.pnl_pct >= take_profit:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="take_profit",
                    reason=f"Profit reached {take_profit}% target (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + take_profit / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                )

            if signal:
                signals.append(signal)

        return signals

    # ── Sell-rule CRUD ───────────────────────────────────────────────

    @staticmethod
    def _ticker_aliases(ticker: str) -> List[str]:
        """Build candidate ticker aliases for legacy/non-suffixed rows."""
        normalized = (ticker or "").strip().upper()
        if not normalized:
            return []

        aliases: Set[str] = {normalized}
        if normalized.endswith(".KS") or normalized.endswith(".KQ"):
            aliases.add(normalized.split(".")[0])
        elif "." not in normalized:
            aliases.add(f"{normalized}.KS")
            aliases.add(f"{normalized}.KQ")
        return list(aliases)

    def _resolve_holding_ticker(self, db, ticker: str) -> Optional[str]:
        """Resolve input ticker to an existing Holding.ticker value."""
        aliases = self._ticker_aliases(ticker)
        if not aliases:
            return None

        holding = db.query(Holding).filter(Holding.ticker == ticker).first()
        if holding is not None:
            return holding.ticker

        holding = db.query(Holding).filter(Holding.ticker.in_(aliases)).first()
        return holding.ticker if holding is not None else None

    def _sell_rule_to_response(self, r: SellRule) -> SellRuleResponse:
        """Convert a SellRule ORM instance to SellRuleResponse."""
        return SellRuleResponse(
            id=r.id, ticker=r.ticker, rule_type=r.rule_type,
            params=r.params, state_json=r.state_json, is_active=r.is_active,
            preset_id=r.preset_id,
            triggered_at=r.triggered_at, created_at=r.created_at,
            updated_at=r.updated_at,
        )

    def get_sell_rules(self, ticker: str) -> List[SellRuleResponse]:
        """Get all sell rules for a holding."""
        db = SessionLocal()
        try:
            aliases = self._ticker_aliases(ticker)
            if not aliases:
                return []
            rules = (
                db.query(SellRule)
                .filter(SellRule.ticker.in_(aliases))
                .order_by(SellRule.created_at)
                .all()
            )
            return [self._sell_rule_to_response(r) for r in rules]
        finally:
            db.close()

    def create_sell_rule(self, ticker: str, data: SellRuleCreate) -> SellRuleResponse:
        """Create a sell rule for a holding. Raises ValueError if holding not found."""
        db = SessionLocal()
        try:
            resolved_ticker = self._resolve_holding_ticker(db, ticker)
            if resolved_ticker is None:
                raise ValueError(f"Holding not found: {ticker}")

            rule = SellRule(
                ticker=resolved_ticker,
                rule_type=data.rule_type,
                params=data.params,
                is_active=data.is_active,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return self._sell_rule_to_response(rule)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_sell_rule(self, rule_id: int, data: SellRuleUpdate) -> SellRuleResponse:
        """Update a sell rule. Raises ValueError if not found or invalid params."""
        db = SessionLocal()
        try:
            rule = db.query(SellRule).filter(SellRule.id == rule_id).first()
            if rule is None:
                raise ValueError(f"Sell rule not found: {rule_id}")

            if data.params is not None:
                _validate_sell_rule_params(rule.rule_type, data.params)
                rule.params = data.params
            if data.is_active is not None:
                rule.is_active = data.is_active

            db.commit()
            db.refresh(rule)
            return self._sell_rule_to_response(rule)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_sell_rule(self, rule_id: int) -> bool:
        """Delete a sell rule. Returns True if deleted, False if not found."""
        db = SessionLocal()
        try:
            rule = db.query(SellRule).filter(SellRule.id == rule_id).first()
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

    # ── Sell-rule presets ────────────────────────────────────────────

    def _preset_to_response(self, preset: SellRulePreset, db) -> SellRulePresetResponse:
        """Convert a SellRulePreset ORM instance to SellRulePresetResponse."""
        linked_count = db.query(SellRule).filter(SellRule.preset_id == preset.id).count()
        return SellRulePresetResponse(
            id=preset.id,
            name=preset.name,
            description=preset.description,
            rules=[SellRulePresetItem(rule_type=r["rule_type"], params=r["params"]) for r in preset.rules],
            is_active=preset.is_active,
            linked_rules_count=linked_count,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
        )

    def list_sell_rule_presets(self) -> List[SellRulePresetResponse]:
        """List all sell rule presets."""
        db = SessionLocal()
        try:
            presets = db.query(SellRulePreset).order_by(SellRulePreset.created_at).all()
            return [self._preset_to_response(p, db) for p in presets]
        finally:
            db.close()

    def create_sell_rule_preset(self, data: SellRulePresetCreate) -> SellRulePresetResponse:
        """Create a sell rule preset. Raises ValueError on duplicate name."""
        db = SessionLocal()
        try:
            existing = db.query(SellRulePreset).filter(SellRulePreset.name == data.name).first()
            if existing:
                raise ValueError(f"Preset name already exists: {data.name}")

            preset = SellRulePreset(
                name=data.name,
                description=data.description,
                rules=[{"rule_type": r.rule_type, "params": r.params} for r in data.rules],
            )
            db.add(preset)
            db.commit()
            db.refresh(preset)
            return self._preset_to_response(preset, db)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_sell_rule_preset(self, preset_id: int, data: SellRulePresetUpdate) -> SellRulePresetResponse:
        """Update a sell rule preset. Raises ValueError if not found or name conflict."""
        db = SessionLocal()
        try:
            preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
            if preset is None:
                raise ValueError(f"Preset not found: {preset_id}")

            if data.name is not None and data.name != preset.name:
                conflict = db.query(SellRulePreset).filter(
                    SellRulePreset.name == data.name,
                    SellRulePreset.id != preset_id,
                ).first()
                if conflict:
                    raise ValueError(f"Preset name already exists: {data.name}")
                preset.name = data.name

            if data.description is not None:
                preset.description = data.description
            if data.rules is not None:
                preset.rules = [{"rule_type": r.rule_type, "params": r.params} for r in data.rules]
            if data.is_active is not None:
                preset.is_active = data.is_active

            db.commit()
            db.refresh(preset)
            return self._preset_to_response(preset, db)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_sell_rule_preset(self, preset_id: int) -> bool:
        """Delete a sell rule preset. Returns True if deleted, False if not found.

        Defensively nullifies preset_id on linked rules before deletion
        to ensure correct behavior regardless of SQLite FK pragma state.
        """
        db = SessionLocal()
        try:
            preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
            if preset is None:
                return False
            # Defensive: nullify preset_id on linked rules (SQLite may not enforce ON DELETE SET NULL)
            db.query(SellRule).filter(SellRule.preset_id == preset_id).update(
                {SellRule.preset_id: None}, synchronize_session="fetch"
            )
            db.delete(preset)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def apply_preset_to_holding(self, ticker: str, preset_id: int) -> List[SellRuleResponse]:
        """Apply a preset to a holding, creating sell rules from the preset.

        Raises ValueError if holding/preset not found, preset inactive, or already applied.
        """
        db = SessionLocal()
        try:
            resolved_ticker = self._resolve_holding_ticker(db, ticker)
            if resolved_ticker is None:
                raise ValueError(f"Holding not found: {ticker}")
            ticker = resolved_ticker

            preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
            if preset is None:
                raise ValueError(f"Preset not found: {preset_id}")
            if not preset.is_active:
                raise ValueError(f"Preset is inactive: {preset.name}")

            # Check if already applied
            existing = db.query(SellRule).filter(
                SellRule.ticker == ticker,
                SellRule.preset_id == preset_id,
            ).first()
            if existing:
                raise ValueError(f"Preset '{preset.name}' is already applied to {ticker}")

            # Validate all rules before creating any
            for rule_def in preset.rules:
                _validate_sell_rule_params(rule_def["rule_type"], rule_def["params"])

            # Create rules in a single transaction
            created_rules = []
            for rule_def in preset.rules:
                rule = SellRule(
                    ticker=ticker,
                    rule_type=rule_def["rule_type"],
                    params=rule_def["params"],
                    is_active=True,
                    preset_id=preset_id,
                )
                db.add(rule)
                created_rules.append(rule)

            db.commit()
            for r in created_rules:
                db.refresh(r)
            return [self._sell_rule_to_response(r) for r in created_rules]
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def bulk_apply_preset(self, preset_id: int, tickers: List[str]):
        """Apply a preset to multiple holdings at once.

        Returns a BulkApplyPresetResponse with per-ticker results.
        Individual failures do not abort the entire operation.

        Raises:
            PresetNotFoundError: if preset does not exist.
            PresetInactiveError: if preset is deactivated.
        """
        from api.schemas.portfolio import BulkApplyPresetResponse, BulkApplyPresetResultItem
        from api.services.portfolio.portfolio_core_service import PresetNotFoundError, PresetInactiveError

        db = SessionLocal()
        try:
            preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
            if preset is None:
                raise PresetNotFoundError(f"Preset not found: {preset_id}")
            if not preset.is_active:
                raise PresetInactiveError(f"Preset is inactive: {preset.name}")
        finally:
            db.close()

        results: List[BulkApplyPresetResultItem] = []
        for ticker in tickers:
            try:
                created_rules = self.apply_preset_to_holding(ticker, preset_id)
                results.append(BulkApplyPresetResultItem(
                    ticker=ticker,
                    success=True,
                    rules_created=len(created_rules),
                ))
            except ValueError as e:
                results.append(BulkApplyPresetResultItem(
                    ticker=ticker,
                    success=False,
                    error=str(e),
                ))
            except Exception:
                logger.exception("Unexpected error applying preset %d to %s", preset_id, ticker)
                results.append(BulkApplyPresetResultItem(
                    ticker=ticker,
                    success=False,
                    error="Internal error",
                ))

        succeeded = sum(1 for r in results if r.success)
        return BulkApplyPresetResponse(
            preset_id=preset_id,
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
        )

    def save_preset_from_holding(self, ticker: str, name: str, description: Optional[str] = None) -> SellRulePresetResponse:
        """Save current sell rules of a holding as a new preset.

        Creates a snapshot of rule_type + params; does NOT link existing rules to the preset.
        Raises ValueError if holding not found, no rules exist, duplicate rule_types, or name conflict.
        """
        db = SessionLocal()
        try:
            resolved_ticker = self._resolve_holding_ticker(db, ticker)
            if resolved_ticker is None:
                raise ValueError(f"Holding not found: {ticker}")

            rules = (
                db.query(SellRule)
                .filter(SellRule.ticker == resolved_ticker)
                .order_by(SellRule.created_at)
                .all()
            )
            if not rules:
                raise ValueError(f"No sell rules found for {ticker}")

            # Deduplicate: keep only the first rule per rule_type
            seen_types: set = set()
            deduped_rules = []
            for r in rules:
                if r.rule_type not in seen_types:
                    seen_types.add(r.rule_type)
                    deduped_rules.append(r)

            existing = db.query(SellRulePreset).filter(SellRulePreset.name == name).first()
            if existing:
                raise ValueError(f"Preset name already exists: {name}")

            preset = SellRulePreset(
                name=name,
                description=description,
                rules=[{"rule_type": r.rule_type, "params": r.params} for r in deduped_rules],
            )
            db.add(preset)
            db.commit()
            db.refresh(preset)
            return self._preset_to_response(preset, db)
        except ValueError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── Sell-rule evaluation engine ────────────────────────────────

    def evaluate_sell_rules(
        self, ticker: Optional[str] = None, *, dry_run: bool = False
    ) -> SellRuleEvaluateResponse:
        """Evaluate active sell rules against current market data.

        Args:
            ticker: If given, evaluate rules for this ticker only.
                    Otherwise evaluate all active rules.
            dry_run: If True, do not persist state changes (triggered_at,
                     high_watermark).  Used by get_sell_signals for read-only
                     evaluation.

        Returns:
            SellRuleEvaluateResponse with per-rule results.
        """
        db = SessionLocal()
        try:
            # 1. Load active, non-triggered rules
            q = db.query(SellRule).filter(
                SellRule.is_active.is_(True),
                SellRule.triggered_at.is_(None),
            )
            if ticker:
                aliases = self._ticker_aliases(ticker)
                if not aliases:
                    return SellRuleEvaluateResponse(results=[])
                q = q.filter(SellRule.ticker.in_(aliases))
            rules: List[SellRule] = q.all()

            if not rules:
                return SellRuleEvaluateResponse(results=[])

            # 2. Gather unique tickers and fetch current prices + holdings
            tickers = list({r.ticker for r in rules})
            prices = self._get_current_prices(tickers)

            # Load holdings for avg_price / bought_at
            holdings_map: Dict[str, Holding] = {}
            for h in db.query(Holding).filter(Holding.ticker.in_(tickers)).all():
                holdings_map[h.ticker] = h

            # 3. Evaluate each rule
            results: List[SellRuleEvaluateResult] = []
            now = datetime.utcnow()

            for rule in rules:
                try:
                    result = self._evaluate_single_rule(
                        rule, prices, holdings_map, now,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to evaluate sell rule %d (%s/%s): %s",
                        rule.id, rule.ticker, rule.rule_type, exc,
                    )
                    result = SellRuleEvaluateResult(
                        rule_id=rule.id,
                        ticker=rule.ticker,
                        rule_type=rule.rule_type,
                        triggered=False,
                        reason=f"Evaluation error: {exc}",
                    )
                results.append(result)

            if not dry_run:
                db.commit()
            else:
                db.rollback()  # discard any ORM-level mutations
            return SellRuleEvaluateResponse(results=results)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _evaluate_single_rule(
        self,
        rule: SellRule,
        prices: Dict[str, float],
        holdings_map: Dict[str, Holding],
        now: datetime,
    ) -> SellRuleEvaluateResult:
        """Evaluate one sell rule.  Raises on bad params so caller can isolate."""
        current_price = prices.get(rule.ticker)
        holding = holdings_map.get(rule.ticker)
        if current_price is None or holding is None:
            return SellRuleEvaluateResult(
                rule_id=rule.id,
                ticker=rule.ticker,
                rule_type=rule.rule_type,
                triggered=False,
                reason="Price or holding data unavailable",
            )

        # Build TradingContext
        state = rule.state_json or {}
        old_hwm = state.get("high_watermark")
        high_watermark = old_hwm
        if rule.rule_type == "trailing_stop":
            if high_watermark is None or current_price > high_watermark:
                high_watermark = current_price

        ctx = TradingContext(
            ticker=rule.ticker,
            current_price=current_price,
            avg_price=holding.avg_price,
            quantity=holding.quantity,
            high_since_buy=high_watermark,
            bought_at=datetime.combine(holding.bought_at, datetime.min.time())
            if holding.bought_at else None,
        )

        factory = self._RULE_FACTORIES.get(rule.rule_type)
        if factory is None:
            return SellRuleEvaluateResult(
                rule_id=rule.id,
                ticker=rule.ticker,
                rule_type=rule.rule_type,
                triggered=False,
                reason=f"Unknown rule_type: {rule.rule_type}",
            )

        condition = factory(rule.params)
        triggered = condition.should_sell(ctx)
        reason = condition.get_reason() if triggered else None

        # Persist trailing_stop state only when high_watermark actually changed
        if rule.rule_type == "trailing_stop" and high_watermark != old_hwm:
            rule.state_json = {**state, "high_watermark": high_watermark}

        if triggered:
            rule.triggered_at = now

        return SellRuleEvaluateResult(
            rule_id=rule.id,
            ticker=rule.ticker,
            rule_type=rule.rule_type,
            triggered=triggered,
            reason=reason,
            current_price=current_price,
            trigger_value=self._compute_trigger_value(rule, holding, high_watermark),
        )

    @staticmethod
    def _compute_trigger_value(
        rule: SellRule, holding: Holding, high_watermark: Optional[float]
    ) -> Optional[float]:
        """Compute the price threshold that triggered (or would trigger) the rule."""
        params = rule.params or {}
        if rule.rule_type == "stop_loss":
            # pct is negative (e.g. -10), threshold = avg * (1 - abs(pct)/100)
            return holding.avg_price * (1 - abs(params.get("pct", 0)) / 100)
        if rule.rule_type == "take_profit":
            # pct is positive (e.g. 20), threshold = avg * (1 + pct/100)
            return holding.avg_price * (1 + abs(params.get("pct", 0)) / 100)
        if rule.rule_type == "trailing_stop" and high_watermark:
            return high_watermark * (1 - abs(params.get("pct", 0)) / 100)
        return None
