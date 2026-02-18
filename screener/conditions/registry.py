"""
Condition Registry - auto-registration via decorator.

Usage:
    @register_condition(
        key="min_price",
        label="Min Price",
        description="Stock price >= threshold",
        category="price",
        params=[
            {"name": "min_price", "type": "float", "default": 5000, "description": "Minimum price"},
        ],
    )
    class MinPriceCondition(BaseCondition):
        ...
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

_CLASS_MAP: Dict[str, Type] = {}
_METADATA: Dict[str, Dict[str, Any]] = {}


def register_condition(
    key: str,
    label: str,
    description: str = "",
    category: str = "",
    params: List[Dict[str, Any]] | None = None,
):
    """Decorator to register a condition class with its metadata."""

    def decorator(cls: Type) -> Type:
        _CLASS_MAP[key] = cls
        _METADATA[key] = {
            "label": label,
            "description": description,
            "category": category,
            "params": params or [],
        }
        return cls

    return decorator


def get_condition_class_map() -> Dict[str, Type]:
    """Return a copy of the registered condition class map."""
    return dict(_CLASS_MAP)


def get_condition_metadata() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the registered condition metadata."""
    return dict(_METADATA)
