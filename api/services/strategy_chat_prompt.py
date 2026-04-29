"""Prompt-building helpers for strategy chat."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_GRAPH_CHARS = 4000

_SYSTEM_PROMPT_BASE = """\
You are a quant strategy assistant for QuantCanvas, a visual strategy builder.

## Your Role
Help users build stock screening strategies by recommending which nodes to use \
and how to connect them. Explain conditions, parameters, and strategy logic \
in a clear, practical way.

## Node Types
- **Universe**: Market selection (KOSPI, KOSDAQ, SP500, NASDAQ100)
- **Sector**: Filter by industry sector
- **Condition**: Screening filter (see Available Conditions below)
- **Logic**: Combine conditions with AND / OR / NOT operators
- **Output**: Final result node (connects to the end of the pipeline)

## Strategy Flow
Universe → [Sector] → Condition(s) → [Logic groups] → Output

## Guidelines
- Recommend specific condition nodes with parameter values
- Explain why certain conditions work well together
- Keep responses concise and actionable
- Match the language of the user's message (Korean → Korean, English → English)
- Only recommend parameters explicitly listed below. \
If a parameter is not listed, answer "not available" instead of guessing.

## Response Format
When recommending conditions or strategies, end your response with a structured \
JSON block wrapped in an HTML comment. This helps the UI render interactive cards.

Format:
<!-- STRUCTURED_JSON
{
  "summary": "Brief strategy description",
  "suggestions": [
    {
      "condition_type": "condition_key",
      "params": {"param_name": value},
      "rationale": "Why this condition"
    }
  ],
  "warnings": ["Any cautions or limitations"]
}
-->

Rules for the structured block:
- Only include it when you recommend specific conditions or strategies
- Do not include it for general questions or explanations
- The JSON must be valid
- condition_type must be an exact key from Available Conditions
- params must use exact parameter names from the condition definition
- All human-readable text fields (summary, rationale, warnings) MUST be written \
in the same language as the user's message. If the user writes in Korean, \
these fields must also be in Korean.
"""

_cached_system_prompts: Dict[Optional[str], str] = {}
_i18n_label_cache: Dict[str, Dict[str, str]] = {}
_MESSAGES_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "messages"


def _load_i18n_labels(locale: Optional[str]) -> Dict[str, str]:
    """Load condition labels from web/messages/{locale}.json."""
    if not locale or locale == "en":
        return {}
    if locale in _i18n_label_cache:
        return _i18n_label_cache[locale]

    labels: Dict[str, str] = {}
    msg_file = _MESSAGES_DIR / f"{locale}.json"
    try:
        data = json.loads(msg_file.read_text(encoding="utf-8"))
        conditions = data.get("conditions", {})
        for key, val in conditions.items():
            if isinstance(val, dict) and "label" in val:
                labels[key] = val["label"]
    except Exception as exc:
        logger.warning("Failed to load i18n labels for %s: %s", locale, exc)

    _i18n_label_cache[locale] = labels
    return labels


def _get_detail_keys() -> set:
    """Return condition keys that deserve detailed info in the prompt."""
    from screener.conditions.composite import AndCondition, NotCondition, OrCondition
    from screener.conditions.registry import get_condition_class_map, get_condition_metadata
    from screener.presets import PRESET_REGISTRY

    metadata = get_condition_metadata()
    class_map = get_condition_class_map()
    class_to_key = {cls: key for key, cls in class_map.items() if key in metadata}

    def _flatten(conditions) -> set:
        keys = set()
        for condition in conditions:
            if isinstance(condition, (AndCondition, OrCondition)):
                keys.update(_flatten(condition.conditions))
            elif isinstance(condition, NotCondition):
                keys.update(_flatten([condition.condition]))
            else:
                key = class_to_key.get(type(condition))
                if key:
                    keys.add(key)
        return keys

    preset_keys = set()
    for name, func in PRESET_REGISTRY.items():
        try:
            preset_keys.update(_flatten(func()))
        except Exception as exc:
            logger.warning("Failed to extract conditions from preset %s: %s", name, exc)

    recommended_keys = {key for key, meta in metadata.items() if meta.get("recommended")}
    return preset_keys | recommended_keys


def _build_conditions_section(locale: Optional[str] = None) -> str:
    """Build the Available Conditions section from the condition registry."""
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    if not metadata:
        return ""

    detail_keys = _get_detail_keys()
    i18n_labels = _load_i18n_labels(locale)
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for key, meta in metadata.items():
        categories.setdefault(meta.get("category", "other"), []).append({"key": key, **meta})

    lines = [f"\n## Available Conditions ({len(metadata)} total)\n"]
    if i18n_labels:
        lines.append(
            "IMPORTANT: When mentioning conditions in your text response, "
            "always use the localized name (shown after '→') instead of the key.\n"
        )
    for category in sorted(categories):
        items = sorted(categories[category], key=lambda item: item["key"])
        lines.append(f"### {category} ({len(items)})")
        for item in items:
            key = item["key"]
            label = item.get("label", key)
            desc = item.get("description", "")
            params = item.get("params", [])
            param_str = ", ".join(
                f"{param['name']}({param['type']}, default={param.get('default', '?')})"
                for param in params
            )
            i18n_name = i18n_labels.get(key)
            name_part = f"{key} → {i18n_name}" if i18n_name else key
            if key in detail_keys:
                lines.append(f"- **{name_part}** ({label}): {desc}")
            else:
                lines.append(f"- {name_part} ({label}): {desc}" if desc else f"- {name_part} ({label})")
            if param_str:
                lines.append(f"  params: {param_str}")

    return "\n".join(lines)


def _build_presets_section() -> str:
    """Build the Strategy Presets section from the preset registry."""
    from screener.conditions.composite import AndCondition, NotCondition, OrCondition
    from screener.conditions.registry import get_condition_class_map, get_condition_metadata
    from screener.presets import PRESET_REGISTRY

    if not PRESET_REGISTRY:
        return ""

    class_map = get_condition_class_map()
    metadata = get_condition_metadata()
    class_to_key = {cls: key for key, cls in class_map.items() if key in metadata}

    def _describe_conditions(conditions) -> List[str]:
        parts = []
        for condition in conditions:
            if isinstance(condition, OrCondition):
                parts.append(f"OR({', '.join(_describe_conditions(condition.conditions))})")
            elif isinstance(condition, AndCondition):
                parts.append(f"AND({', '.join(_describe_conditions(condition.conditions))})")
            elif isinstance(condition, NotCondition):
                described = _describe_conditions([condition.condition])
                parts.append(f"NOT({described[0]})")
            else:
                key = class_to_key.get(type(condition), type(condition).__name__)
                meta_params = metadata.get(key, {}).get("params", [])
                param_vals = []
                for param in meta_params:
                    val = getattr(condition, param["name"], None)
                    if val is not None:
                        param_vals.append(f"{param['name']}={val}")
                parts.append(f"{key}({', '.join(param_vals)})" if param_vals else key)
        return parts

    lines = ["\n## Strategy Presets (ready-to-use templates)\n"]
    for name, func in PRESET_REGISTRY.items():
        try:
            conditions = func()
        except Exception as exc:
            logger.warning("Failed to build preset %s for prompt: %s", name, exc)
            continue
        doc = (func.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else name
        lines.append(f"- **{name}**: {summary}")
        lines.append(f"  conditions: {' + '.join(_describe_conditions(conditions))}")

    return "\n".join(lines)


def get_system_prompt(locale: Optional[str] = None) -> str:
    """Return the cached system prompt for the given locale."""
    if locale not in _cached_system_prompts:
        _cached_system_prompts[locale] = (
            _SYSTEM_PROMPT_BASE
            + _build_conditions_section(locale)
            + _build_presets_section()
        )
    return _cached_system_prompts[locale]


def build_system_with_graph(
    graph: Optional[dict[str, Any]] = None,
    locale: Optional[str] = None,
) -> str:
    """Return system prompt, optionally appending current graph context."""
    system = get_system_prompt(locale)
    if graph:
        graph_json = json.dumps(graph, ensure_ascii=False, indent=2)
        if len(graph_json) > _MAX_GRAPH_CHARS:
            graph_json = graph_json[:_MAX_GRAPH_CHARS] + "\n... (truncated)"
        system += f"\n\n## Current Strategy Graph\n```json\n{graph_json}\n```"
    return system
