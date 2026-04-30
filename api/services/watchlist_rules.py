"""Rule and template CRUD helpers for WatchlistService."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.watchlist import BuyRule, BuyRuleTemplate, WatchlistItem
from api.schemas.watchlist import (
    BuyRuleCreate,
    BuyRuleResponse,
    BuyRuleTemplateCreate,
    BuyRuleTemplateResponse,
    BuyRuleTemplateUpdate,
    BuyRuleUpdate,
    _validate_buy_rule_params,
)


def get_rules_for_item(service, item_id: int) -> List[BuyRuleResponse]:
    db: Session = SessionLocal()
    try:
        rules = (
            db.query(BuyRule)
            .filter(BuyRule.watchlist_item_id == item_id)
            .order_by(BuyRule.created_at)
            .all()
        )
        return [service._rule_to_response(rule) for rule in rules]
    finally:
        db.close()


def create_rule(service, item_id: int, data: BuyRuleCreate) -> BuyRuleResponse:
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
        return service._rule_to_response(rule)
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_rule(service, rule_id: int, data: BuyRuleUpdate) -> Optional[BuyRuleResponse]:
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
        return service._rule_to_response(rule)
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_rule(_service, rule_id: int) -> bool:
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


def list_templates(service) -> List[BuyRuleTemplateResponse]:
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(BuyRuleTemplate)
            .order_by(BuyRuleTemplate.created_at.desc())
            .all()
        )
        if not rows:
            return []

        count_rows = (
            db.query(BuyRule.template_id, func.count(BuyRule.id))
            .filter(BuyRule.template_id.isnot(None))
            .group_by(BuyRule.template_id)
            .all()
        )
        count_map = {template_id: count for template_id, count in count_rows}

        return [
            service._template_to_response(template, linked_count=count_map.get(template.id, 0))
            for template in rows
        ]
    finally:
        db.close()


def create_template(service, data: BuyRuleTemplateCreate) -> BuyRuleTemplateResponse:
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
        return service._template_to_response(row, db)
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
    service,
    template_id: int,
    data: BuyRuleTemplateUpdate,
) -> Optional[BuyRuleTemplateResponse]:
    db: Session = SessionLocal()
    try:
        row = db.query(BuyRuleTemplate).filter(BuyRuleTemplate.id == template_id).first()
        if row is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "params" in update_data and update_data["params"] is not None:
            _validate_buy_rule_params(row.rule_type, update_data["params"])
        if "name" in update_data and update_data["name"] is not None:
            duplicate = (
                db.query(BuyRuleTemplate)
                .filter(BuyRuleTemplate.name == update_data["name"], BuyRuleTemplate.id != template_id)
                .first()
            )
            if duplicate:
                raise ValueError(f"Template name '{update_data['name']}' already exists")

        for key, val in update_data.items():
            setattr(row, key, val)

        db.commit()
        db.refresh(row)
        return service._template_to_response(row, db)
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


def delete_template(_service, template_id: int) -> bool:
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
    service,
    item_id: int,
    template_id: int,
    is_active: bool = True,
) -> BuyRuleResponse:
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
            params=dict(template.params),
            is_active=is_active,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return service._rule_to_response(rule)
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Template {template_id} is already linked to item {item_id}")
    except ValueError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
