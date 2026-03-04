"""
Strategy Chat Service.

Provides streaming chat for strategy building assistance.
Supports Anthropic (preferred) and OpenAI (fallback) providers.
"""

import json
import logging
import os
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
"""

# Cached system prompt with conditions section
_cached_system_prompt: Optional[str] = None


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


def _build_conditions_section() -> str:
    """Build the Available Conditions section from the condition registry.

    Key/recommended conditions get description + params detail.
    Others get name only to keep the prompt compact.
    """
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    if not metadata:
        return ""

    detail_keys = _get_detail_keys()

    # Group by category
    cats: Dict[str, List[Dict]] = {}
    for key, meta in metadata.items():
        cat = meta.get("category", "other")
        cats.setdefault(cat, []).append({"key": key, **meta})

    lines = [f"\n## Available Conditions ({len(metadata)} total)\n"]
    for cat in sorted(cats):
        items = sorted(cats[cat], key=lambda x: x["key"])
        lines.append(f"### {cat} ({len(items)})")
        for item in items:
            key = item["key"]
            label = item.get("label", key)
            if key in detail_keys:
                desc = item.get("description", "")
                params = item.get("params", [])
                param_str = ", ".join(
                    f"{p['name']}({p['type']}, default={p.get('default', '?')})"
                    for p in params
                )
                lines.append(f"- **{key}** ({label}): {desc}")
                if param_str:
                    lines.append(f"  params: {param_str}")
            else:
                lines.append(f"- {key} ({label})")

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


def _get_system_prompt() -> str:
    """Return system prompt with dynamically injected conditions and presets.

    Built once from the registry/presets and cached for the process lifetime.
    """
    global _cached_system_prompt
    if _cached_system_prompt is None:
        conditions_section = _build_conditions_section()
        presets_section = _build_presets_section()
        _cached_system_prompt = (
            _SYSTEM_PROMPT_BASE + conditions_section + presets_section
        )
    return _cached_system_prompt


def _build_system_with_graph(graph: Optional[dict[str, Any]] = None) -> str:
    """Return system prompt, optionally appending the current graph context."""
    system = _get_system_prompt()
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
    ) -> Generator[str, None, None]:
        """Stream chat response chunks.

        Args:
            messages: Conversation history [{"role": ..., "content": ...}]
            graph: Optional current strategy graph for context.

        Yields:
            Text chunks as they arrive from the API.
        """
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        logger.info(
            "Strategy chat [%s]: %d messages, graph=%s",
            self._provider, len(api_messages), bool(graph),
        )

        if self._provider == "anthropic":
            yield from self._stream_anthropic(api_messages, graph)
        else:
            yield from self._stream_openai(api_messages, graph)

    def _stream_anthropic(
        self,
        messages: list[dict[str, str]],
        graph: Optional[dict[str, Any]],
    ) -> Generator[str, None, None]:
        import anthropic

        system = _build_system_with_graph(graph)

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
    ) -> Generator[str, None, None]:
        import openai

        system = _build_system_with_graph(graph)
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
