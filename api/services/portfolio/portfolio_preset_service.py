"""Preset management helpers for PortfolioRiskService."""

from __future__ import annotations

import logging
from typing import List, Optional

from api.database import SessionLocal
from api.models.portfolio import SellRule, SellRulePreset
from api.schemas.portfolio import (
    SellRulePresetCreate,
    SellRulePresetItem,
    SellRulePresetResponse,
    SellRulePresetUpdate,
    SellRuleResponse,
)

logger = logging.getLogger(__name__)


def preset_to_response(service, preset: SellRulePreset, db) -> SellRulePresetResponse:
    linked_count = db.query(SellRule).filter(SellRule.preset_id == preset.id).count()
    return SellRulePresetResponse(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        rules=[SellRulePresetItem(rule_type=rule["rule_type"], params=rule["params"]) for rule in preset.rules],
        is_active=preset.is_active,
        linked_rules_count=linked_count,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )


def list_sell_rule_presets(service) -> List[SellRulePresetResponse]:
    db = SessionLocal()
    try:
        presets = db.query(SellRulePreset).order_by(SellRulePreset.created_at).all()
        return [preset_to_response(service, preset, db) for preset in presets]
    finally:
        db.close()


def create_sell_rule_preset(service, data: SellRulePresetCreate) -> SellRulePresetResponse:
    db = SessionLocal()
    try:
        existing = db.query(SellRulePreset).filter(SellRulePreset.name == data.name).first()
        if existing:
            raise ValueError(f"Preset name already exists: {data.name}")

        preset = SellRulePreset(
            name=data.name,
            description=data.description,
            rules=[{"rule_type": rule.rule_type, "params": rule.params} for rule in data.rules],
        )
        db.add(preset)
        db.commit()
        db.refresh(preset)
        return preset_to_response(service, preset, db)
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_sell_rule_preset(
    service,
    preset_id: int,
    data: SellRulePresetUpdate,
) -> SellRulePresetResponse:
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
            preset.rules = [{"rule_type": rule.rule_type, "params": rule.params} for rule in data.rules]
        if data.is_active is not None:
            preset.is_active = data.is_active

        db.commit()
        db.refresh(preset)
        return preset_to_response(service, preset, db)
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_sell_rule_preset(_service, preset_id: int) -> bool:
    db = SessionLocal()
    try:
        preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
        if preset is None:
            return False
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


def apply_preset_to_holding(service, ticker: str, preset_id: int) -> List[SellRuleResponse]:
    db = SessionLocal()
    try:
        resolved_ticker = service._resolve_holding_ticker(db, ticker)
        if resolved_ticker is None:
            raise ValueError(f"Holding not found: {ticker}")
        ticker = resolved_ticker

        preset = db.query(SellRulePreset).filter(SellRulePreset.id == preset_id).first()
        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")
        if not preset.is_active:
            raise ValueError(f"Preset is inactive: {preset.name}")

        existing = db.query(SellRule).filter(
            SellRule.ticker == ticker,
            SellRule.preset_id == preset_id,
        ).first()
        if existing:
            raise ValueError(f"Preset '{preset.name}' is already applied to {ticker}")

        for rule_def in preset.rules:
            service._validate_rule_params(rule_def["rule_type"], rule_def["params"])

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
        for rule in created_rules:
            db.refresh(rule)
        return [service._sell_rule_to_response(rule) for rule in created_rules]
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def bulk_apply_preset(service, preset_id: int, tickers: List[str]):
    from api.schemas.portfolio import BulkApplyPresetResponse, BulkApplyPresetResultItem
    from api.services.portfolio.portfolio_core_service import PresetInactiveError, PresetNotFoundError

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
            created_rules = apply_preset_to_holding(service, ticker, preset_id)
            results.append(BulkApplyPresetResultItem(
                ticker=ticker,
                success=True,
                rules_created=len(created_rules),
            ))
        except ValueError as exc:
            results.append(BulkApplyPresetResultItem(
                ticker=ticker,
                success=False,
                error=str(exc),
            ))
        except Exception:
            logger.exception("Unexpected error applying preset %d to %s", preset_id, ticker)
            results.append(BulkApplyPresetResultItem(
                ticker=ticker,
                success=False,
                error="Internal error",
            ))

    succeeded = sum(1 for result in results if result.success)
    return BulkApplyPresetResponse(
        preset_id=preset_id,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


def save_preset_from_holding(
    service,
    ticker: str,
    name: str,
    description: Optional[str] = None,
) -> SellRulePresetResponse:
    db = SessionLocal()
    try:
        resolved_ticker = service._resolve_holding_ticker(db, ticker)
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

        seen_types: set = set()
        deduped_rules = []
        for rule in rules:
            if rule.rule_type not in seen_types:
                seen_types.add(rule.rule_type)
                deduped_rules.append(rule)

        existing = db.query(SellRulePreset).filter(SellRulePreset.name == name).first()
        if existing:
            raise ValueError(f"Preset name already exists: {name}")

        preset = SellRulePreset(
            name=name,
            description=description,
            rules=[{"rule_type": rule.rule_type, "params": rule.params} for rule in deduped_rules],
        )
        db.add(preset)
        db.commit()
        db.refresh(preset)
        return preset_to_response(service, preset, db)
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
