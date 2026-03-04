"""
Strategy Chat Service.

Provides streaming chat with Claude for strategy building assistance.
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
"""

# Cached system prompt with conditions section
_cached_system_prompt: Optional[str] = None


def _build_conditions_section() -> str:
    """Build the Available Conditions section from the condition registry."""
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    if not metadata:
        return ""

    # Group by category
    cats: Dict[str, List[str]] = {}
    for key, meta in metadata.items():
        cat = meta.get("category", "other")
        label = meta.get("label", key)
        cats.setdefault(cat, []).append(f"{key} ({label})")

    lines = [f"\n## Available Conditions ({len(metadata)} total)\n"]
    for cat in sorted(cats):
        items = sorted(cats[cat])
        lines.append(f"- **{cat}** ({len(items)}): {', '.join(items)}")

    return "\n".join(lines)


def _get_system_prompt() -> str:
    """Return system prompt with dynamically injected condition list.

    The condition list is built once from the registry and cached for the
    lifetime of the process.
    """
    global _cached_system_prompt
    if _cached_system_prompt is None:
        conditions_section = _build_conditions_section()
        _cached_system_prompt = _SYSTEM_PROMPT_BASE + conditions_section
    return _cached_system_prompt


class StrategyChatService:
    """Streaming chat service using Anthropic API."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        graph: Optional[dict[str, Any]] = None,
    ) -> Generator[str, None, None]:
        """Stream chat response chunks from Claude.

        Args:
            messages: Conversation history [{"role": ..., "content": ...}]
            graph: Optional current strategy graph for context.

        Yields:
            Text chunks as they arrive from the API.

        Raises:
            Exception: Re-raised after logging if the Anthropic API call fails.
        """
        import anthropic

        system = _get_system_prompt()
        if graph:
            graph_json = json.dumps(graph, ensure_ascii=False, indent=2)
            if len(graph_json) > _MAX_GRAPH_CHARS:
                graph_json = graph_json[:_MAX_GRAPH_CHARS] + "\n... (truncated)"
            system += f"\n\n## Current Strategy Graph\n```json\n{graph_json}\n```"

        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        logger.info(
            "Strategy chat: %d messages, graph=%s", len(api_messages), bool(graph)
        )

        try:
            with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=api_messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError:
            logger.warning("Strategy chat: rate limit hit")
            raise
        except anthropic.APIConnectionError:
            logger.warning("Strategy chat: connection error")
            raise
        except anthropic.APIStatusError as e:
            logger.error("Strategy chat: API status error %s", e.status_code)
            raise


_instance: Optional[StrategyChatService] = None


def get_strategy_chat_service() -> StrategyChatService:
    """Return singleton StrategyChatService instance."""
    global _instance
    if _instance is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _instance = StrategyChatService(api_key=api_key)
    return _instance
