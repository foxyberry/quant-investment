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

from functools import partial
from typing import Any, Callable, Dict, List, Type, Union

_CLASS_MAP: Dict[str, Union[Type, Callable]] = {}
_METADATA: Dict[str, Dict[str, Any]] = {}


def register_condition(
    key: str,
    label: str,
    description: str = "",
    category: str = "",
    params: List[Dict[str, Any]] | None = None,
    recommended: bool = False,
    order: int = 0,
    is_pairs: bool = False,
):
    """Decorator to register a condition class with its metadata."""

    def decorator(cls: Type) -> Type:
        _CLASS_MAP[key] = cls
        _METADATA[key] = {
            "label": label,
            "description": description,
            "category": category,
            "params": params or [],
            "recommended": recommended,
            "order": order,
            "is_pairs": is_pairs,
        }
        return cls

    return decorator


def get_condition_class_map() -> Dict[str, Type]:
    """Return a copy of the registered condition class map."""
    return dict(_CLASS_MAP)


def get_condition_metadata() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the registered condition metadata."""
    return dict(_METADATA)


def register_alias(alias_key: str, cls: Type, **default_kwargs: Any) -> None:
    """Register a legacy alias key that maps to *cls* with fixed defaults.

    The alias is added to ``_CLASS_MAP`` only (not ``_METADATA``), so it
    won't appear in the node palette but will still resolve when loading
    saved strategies that reference old condition keys.

    If *default_kwargs* are provided, a ``functools.partial`` is stored so
    that ``_CLASS_MAP[alias_key]()`` produces the correct variant-specific
    defaults (e.g. ``short_period=2, long_period=20``).
    """
    if default_kwargs:
        _CLASS_MAP[alias_key] = partial(cls, **default_kwargs)
    else:
        _CLASS_MAP[alias_key] = cls
