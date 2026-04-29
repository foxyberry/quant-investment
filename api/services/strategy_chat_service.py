"""
Strategy Chat Service.

Provides streaming chat for strategy building assistance.
Supports Anthropic (preferred) and OpenAI (fallback) providers.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Generator, List, Optional

from api.services.strategy_chat_prompt import build_system_with_graph

logger = logging.getLogger(__name__)
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

        system = build_system_with_graph(graph, locale)

        try:
            with self.client.messages.stream(
                model="claude-sonnet-4-6",
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

        system = build_system_with_graph(graph, locale)
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
    Uses get_settings() so .env file values are correctly picked up.
    Only caches the instance once a valid API key is found.
    """
    global _instance
    if _instance is not None:
        return _instance

    # Use get_settings() to pick up .env values (os.environ misses .env-only keys)
    try:
        from api.config import get_settings
        settings = get_settings()
        anthropic_key = settings.anthropic_api_key or ""
    except Exception:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if anthropic_key:
        _instance = StrategyChatService(provider="anthropic", api_key=anthropic_key)
        logger.info("Strategy chat: using Anthropic provider")
    elif openai_key:
        _instance = StrategyChatService(provider="openai", api_key=openai_key)
        logger.info("Strategy chat: using OpenAI provider")
    else:
        # Don't cache — API key may become available after next request
        logger.warning("Strategy chat: no API key configured")
        return StrategyChatService(provider="none", api_key="")

    return _instance
