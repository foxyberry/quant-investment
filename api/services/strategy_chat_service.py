"""
Strategy Chat Service.

Provides streaming chat with Claude for strategy building assistance.
"""

import json
import logging
import os
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# Max characters for graph JSON injected into system prompt
_MAX_GRAPH_CHARS = 4000

SYSTEM_PROMPT = """\
You are a quant strategy assistant for QuantCanvas, a visual strategy builder.

## Your Role
Help users build stock screening strategies by recommending which nodes to use \
and how to connect them. Explain conditions, parameters, and strategy logic \
in a clear, practical way.

## Node Types
- **Universe**: Market selection (KOSPI, KOSDAQ, SP500, NASDAQ100)
- **Sector**: Filter by industry sector
- **Condition**: Screening filter (48 types across categories: \
valuation, profitability, growth, momentum, stability, technical, volume)
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

        system = SYSTEM_PROMPT
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
