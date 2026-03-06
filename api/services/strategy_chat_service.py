"""
Strategy Chat Service.

Provides streaming chat for strategy building assistance.
Supports Anthropic (preferred) and OpenAI (fallback) providers.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Max characters for graph JSON injected into system prompt
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
"""

# Cached system prompt with conditions section — keyed by locale
_cached_system_prompts: Dict[Optional[str], str] = {}

# Cache of locale → {condition_key: localized_label}
_i18n_label_cache: Dict[str, Dict[str, str]] = {}

# Path to web/messages/ relative to project root
_MESSAGES_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "messages"


def _load_i18n_labels(locale: Optional[str]) -> Dict[str, str]:
    """Load condition labels from web/messages/{locale}.json.

    Returns a dict of condition_key → localized label.
    Falls back to empty dict on failure.
    """
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
    except Exception as e:
        logger.warning("Failed to load i18n labels for %s: %s", locale, e)

    _i18n_label_cache[locale] = labels
    return labels


def _get_detail_keys() -> set:
    """Return condition keys that deserve detailed info in the prompt.

    Includes recommended conditions and those used by presets.
    """
    from screener.conditions.registry import get_condition_metadata, get_condition_class_map
    from screener.presets import PRESET_REGISTRY
    from screener.conditions.composite import AndCondition, OrCondition, NotCondition

    metadata = get_condition_metadata()
    class_map = get_condition_class_map()

    # Reverse map: class -> key (skip aliases not in metadata)
    class_to_key = {cls: key for key, cls in class_map.items() if key in metadata}

    def _flatten(conditions) -> set:
        keys = set()
        for c in conditions:
            if isinstance(c, (AndCondition, OrCondition)):
                keys.update(_flatten(c.conditions))
            elif isinstance(c, NotCondition):
                keys.update(_flatten([c.condition]))
            else:
                cls = type(c)
                if cls in class_to_key:
                    keys.add(class_to_key[cls])
        return keys

    preset_keys = set()
    for name, func in PRESET_REGISTRY.items():
        try:
            preset_keys.update(_flatten(func()))
        except Exception as e:
            logger.warning("Failed to extract conditions from preset %s: %s", name, e)

    recommended_keys = {k for k, m in metadata.items() if m.get("recommended")}
    return preset_keys | recommended_keys


def _build_conditions_section(locale: Optional[str] = None) -> str:
    """Build the Available Conditions section from the condition registry.

    Key/recommended conditions get description + params detail.
    Others get name + params to keep the prompt compact.
    When locale is provided, includes localized label for each condition.
    """
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    if not metadata:
        return ""

    detail_keys = _get_detail_keys()
    i18n_labels = _load_i18n_labels(locale)

    # Group by category
    cats: Dict[str, List[Dict]] = {}
    for key, meta in metadata.items():
        cat = meta.get("category", "other")
        cats.setdefault(cat, []).append({"key": key, **meta})

    lines = [f"\n## Available Conditions ({len(metadata)} total)\n"]
    if i18n_labels:
        lines.append(
            "IMPORTANT: When mentioning conditions in your text response, "
            "always use the localized name (shown after '→') instead of the key.\n"
        )
    for cat in sorted(cats):
        items = sorted(cats[cat], key=lambda x: x["key"])
        lines.append(f"### {cat} ({len(items)})")
        for item in items:
            key = item["key"]
            label = item.get("label", key)
            desc = item.get("description", "")
            params = item.get("params", [])
            param_str = ", ".join(
                f"{p['name']}({p['type']}, default={p.get('default', '?')})"
                for p in params
            )
            # Include localized name if available
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
    from screener.presets import PRESET_REGISTRY
    from screener.conditions.registry import get_condition_class_map, get_condition_metadata
    from screener.conditions.composite import AndCondition, OrCondition, NotCondition

    if not PRESET_REGISTRY:
        return ""

    class_map = get_condition_class_map()
    metadata = get_condition_metadata()
    class_to_key = {cls: key for key, cls in class_map.items() if key in metadata}

    def _describe_conditions(conditions, depth=0) -> List[str]:
        parts = []
        for c in conditions:
            if isinstance(c, OrCondition):
                sub = _describe_conditions(c.conditions, depth + 1)
                parts.append(f"OR({', '.join(sub)})")
            elif isinstance(c, AndCondition):
                sub = _describe_conditions(c.conditions, depth + 1)
                parts.append(f"AND({', '.join(sub)})")
            elif isinstance(c, NotCondition):
                sub = _describe_conditions([c.condition], depth + 1)
                parts.append(f"NOT({sub[0]})")
            else:
                cls = type(c)
                key = class_to_key.get(cls, cls.__name__)
                # Extract instance params
                meta_params = metadata.get(key, {}).get("params", [])
                param_vals = []
                for p in meta_params:
                    val = getattr(c, p["name"], None)
                    if val is not None:
                        param_vals.append(f"{p['name']}={val}")
                if param_vals:
                    parts.append(f"{key}({', '.join(param_vals)})")
                else:
                    parts.append(key)
        return parts

    lines = ["\n## Strategy Presets (ready-to-use templates)\n"]
    for name, func in PRESET_REGISTRY.items():
        try:
            conditions = func()
        except Exception as e:
            logger.warning("Failed to build preset %s for prompt: %s", name, e)
            continue
        # Get docstring as description
        doc = (func.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else name
        cond_parts = _describe_conditions(conditions)

        lines.append(f"- **{name}**: {summary}")
        lines.append(f"  conditions: {' + '.join(cond_parts)}")

    return "\n".join(lines)


def _get_system_prompt(locale: Optional[str] = None) -> str:
    """Return system prompt with dynamically injected conditions and presets.

    Cached per locale for the process lifetime.
    """
    if locale not in _cached_system_prompts:
        conditions_section = _build_conditions_section(locale)
        presets_section = _build_presets_section()
        _cached_system_prompts[locale] = (
            _SYSTEM_PROMPT_BASE + conditions_section + presets_section
        )
    return _cached_system_prompts[locale]


def _build_system_with_graph(
    graph: Optional[dict[str, Any]] = None,
    locale: Optional[str] = None,
) -> str:
    """Return system prompt, optionally appending the current graph context."""
    system = _get_system_prompt(locale)
    if graph:
        graph_json = json.dumps(graph, ensure_ascii=False, indent=2)
        if len(graph_json) > _MAX_GRAPH_CHARS:
            graph_json = graph_json[:_MAX_GRAPH_CHARS] + "\n... (truncated)"
        system += f"\n\n## Current Strategy Graph\n```json\n{graph_json}\n```"
    return system


class StrategyChatService:
    """Streaming chat service with Anthropic/OpenAI provider selection."""

    def __init__(self, provider: str, api_key: str):
        self._provider = provider
        self._api_key = api_key
        self._client = None

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def client(self):
        if self._client is None:
            if self._provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            else:
                import openai
                self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        graph: Optional[dict[str, Any]] = None,
        locale: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream chat response chunks.

        Args:
            messages: Conversation history [{"role": ..., "content": ...}]
            graph: Optional current strategy graph for context.
            locale: Optional UI locale for localized condition names.

        Yields:
            Text chunks as they arrive from the API.
        """
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        logger.info(
            "Strategy chat [%s]: %d messages, graph=%s, locale=%s",
            self._provider, len(api_messages), bool(graph), locale,
        )

        if self._provider == "anthropic":
            yield from self._stream_anthropic(api_messages, graph, locale)
        else:
            yield from self._stream_openai(api_messages, graph, locale)

    def _stream_anthropic(
        self,
        messages: list[dict[str, str]],
        graph: Optional[dict[str, Any]],
        locale: Optional[str] = None,
    ) -> Generator[str, None, None]:
        import anthropic

        system = _build_system_with_graph(graph, locale)

        try:
            with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError:
            logger.warning("Strategy chat: Anthropic rate limit hit")
            raise
        except anthropic.APIConnectionError:
            logger.warning("Strategy chat: Anthropic connection error")
            raise
        except anthropic.APIStatusError as e:
            logger.error("Strategy chat: Anthropic API error %s", e.status_code)
            raise

    def _stream_openai(
        self,
        messages: list[dict[str, str]],
        graph: Optional[dict[str, Any]],
        locale: Optional[str] = None,
    ) -> Generator[str, None, None]:
        import openai

        system = _build_system_with_graph(graph, locale)
        oai_messages = [{"role": "system", "content": system}] + messages

        try:
            stream = self.client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=oai_messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except openai.RateLimitError:
            logger.warning("Strategy chat: OpenAI rate limit hit")
            raise
        except openai.APIConnectionError:
            logger.warning("Strategy chat: OpenAI connection error")
            raise
        except openai.APIStatusError as e:
            logger.error("Strategy chat: OpenAI API error %s", e.status_code)
            raise


_STRUCTURED_RE = re.compile(
    r"<!--\s*STRUCTURED_JSON\s*?\r?\n?(.*?)\r?\n?\s*-->",
    re.DOTALL,
)


def _validate_payload(payload: dict) -> Optional[dict]:
    """Validate and sanitize structured payload shape.

    Returns sanitized payload or None if invalid.
    """
    if not isinstance(payload, dict):
        return None
    result: dict = {}
    if "summary" in payload and isinstance(payload["summary"], str):
        result["summary"] = payload["summary"]
    if "suggestions" in payload and isinstance(payload["suggestions"], list):
        valid_suggestions = []
        for s in payload["suggestions"]:
            if not isinstance(s, dict):
                continue
            if not isinstance(s.get("condition_type"), str):
                continue
            params = s.get("params", {})
            if not isinstance(params, dict):
                params = {}
            valid_suggestions.append({
                "condition_type": s["condition_type"],
                "params": params,
                "rationale": str(s.get("rationale", "")),
            })
        if valid_suggestions:
            result["suggestions"] = valid_suggestions
    if "warnings" in payload and isinstance(payload["warnings"], list):
        result["warnings"] = [str(w) for w in payload["warnings"] if isinstance(w, str)]
    return result if result else None


def parse_structured_payload(text: str) -> tuple[str, Optional[dict]]:
    """Extract structured JSON payload from assistant response.

    Returns (clean_text, payload_dict_or_None).
    Always removes the structured block from text, even on parse failure.
    """
    match = _STRUCTURED_RE.search(text)
    if not match:
        return text, None
    clean = text[: match.start()].rstrip()
    try:
        raw = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse structured payload from chat response")
        return clean, None
    payload = _validate_payload(raw)
    return clean, payload


def validate_suggestions(
    suggestions: list[dict],
) -> list[dict]:
    """Validate condition suggestions against the condition registry.

    Returns a list of result dicts with 'condition_type', 'valid', 'errors'.
    """
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    results = []

    for s in suggestions:
        ctype = s.get("condition_type", "")
        params = s.get("params", {})
        errors: list[dict] = []

        if ctype not in metadata:
            results.append({
                "condition_type": ctype,
                "valid": False,
                "errors": [{"param": "condition_type", "message": f"Unknown condition: {ctype}"}],
            })
            continue

        meta = metadata[ctype]
        param_defs = {p["name"]: p for p in meta.get("params", [])}

        for pname, pval in params.items():
            if pname not in param_defs:
                errors.append({"param": pname, "message": f"Unknown parameter: {pname}"})
                continue
            pdef = param_defs[pname]
            ptype = pdef.get("type", "")
            if ptype in ("int", "integer") and not isinstance(pval, (int, float)):
                errors.append({"param": pname, "message": f"Expected number, got {type(pval).__name__}"})
            elif ptype == "float" and not isinstance(pval, (int, float)):
                errors.append({"param": pname, "message": f"Expected number, got {type(pval).__name__}"})
            elif ptype == "bool" and not isinstance(pval, bool):
                errors.append({"param": pname, "message": f"Expected boolean, got {type(pval).__name__}"})

            if "min" in pdef and isinstance(pval, (int, float)) and pval < pdef["min"]:
                errors.append({"param": pname, "message": f"Value {pval} below minimum {pdef['min']}"})
            if "max" in pdef and isinstance(pval, (int, float)) and pval > pdef["max"]:
                errors.append({"param": pname, "message": f"Value {pval} above maximum {pdef['max']}"})

        results.append({
            "condition_type": ctype,
            "valid": len(errors) == 0,
            "errors": errors,
        })

    return results


_instance: Optional[StrategyChatService] = None


def get_strategy_chat_service() -> StrategyChatService:
    """Return singleton StrategyChatService instance.

    Provider priority: ANTHROPIC_API_KEY > OPENAI_API_KEY.
    """
    global _instance
    if _instance is None:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")

        if anthropic_key:
            _instance = StrategyChatService(provider="anthropic", api_key=anthropic_key)
            logger.info("Strategy chat: using Anthropic provider")
        elif openai_key:
            _instance = StrategyChatService(provider="openai", api_key=openai_key)
            logger.info("Strategy chat: using OpenAI provider")
        else:
            _instance = StrategyChatService(provider="none", api_key="")
            logger.warning("Strategy chat: no API key configured")
    return _instance
