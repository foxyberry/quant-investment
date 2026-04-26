"""
Portfolio AI Chatbot Service.

Implements a streaming Claude-powered chatbot that analyzes the user's portfolio
using tool_use to pull live holdings, price history, technical indicators,
news, and macro data.

Streaming protocol: SSE with JSON payloads.
  {"type": "text",       "content": "..."}
  {"type": "tool_start", "name": "get_indicators", "input": {...}}
  {"type": "tool_end",   "name": "get_indicators"}
  {"type": "done"}
  {"type": "error",      "message": "..."}
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, AsyncIterator, Dict, List, Optional

import asyncio
import pandas as pd

logger = logging.getLogger(__name__)

# Maximum conversation turns forwarded to Claude (sliding window, prevents context overflow)
_MAX_HISTORY_MESSAGES = 20

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 퀀트 투자 전문 AI 어시스턴트입니다. \
사용자의 포트폴리오를 분석하고 매수/매도 타이밍, 기술적 분석, 리스크 관리에 대해 \
구체적이고 실용적인 조언을 제공합니다.

원칙:
- 한국어로 답변합니다.
- 수치 기반 근거를 반드시 제시합니다.
- 투자 결정은 최종적으로 사용자의 책임임을 명시합니다.
- 제공된 도구를 적극 활용해 실제 데이터 기반으로 분석합니다.
- 불확실한 내용은 명확히 불확실하다고 밝힙니다."""

# ── Tool definitions (sent to Claude) ─────────────────────────────────────────

_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_holdings",
        "description": (
            "현재 포트폴리오의 보유 종목 전체를 조회합니다. "
            "각 종목의 평균 단가, 현재가, 손익률 등을 반환합니다."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_price_history",
        "description": (
            "특정 종목의 OHLCV (시가/고가/저가/종가/거래량) 일별 데이터를 조회합니다. "
            "최근 N일치 데이터를 반환합니다 (최대 60행)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "days": {"type": "integer", "description": "조회 기간 (일수, 기본 60)", "default": 60},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_indicators",
        "description": (
            "특정 종목의 기술적 지표를 계산하여 반환합니다. "
            "RSI, MACD, 볼린저 밴드, 이동평균선, OBV 트렌드, 스토캐스틱 등을 포함합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "days": {"type": "integer", "description": "계산에 사용할 데이터 기간 (일수, 기본 120)", "default": 120},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "특정 종목의 최근 뉴스를 조회합니다. "
            "제목, 요약, 날짜, 출처를 반환합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "limit": {"type": "integer", "description": "최대 뉴스 건수 (기본 5)", "default": 5},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_macro_context",
        "description": (
            "현재 거시경제 환경 데이터를 조회합니다. "
            "VIX, 매크로 점수, 시장 레짐, 환율(USD/KRW), 주요 지수 방향을 반환합니다."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ── Tool implementations ───────────────────────────────────────────────────────


def _run_get_holdings() -> Dict[str, Any]:
    from api.services.portfolio_service import get_portfolio_service

    service = get_portfolio_service()
    holdings = service.get_all_holdings(with_prices=True)
    rows = [
        {
            "ticker": h.ticker,
            "name": h.name,
            "quantity": h.quantity,
            "avg_price": h.avg_price,
            "current_price": h.current_price,
            "pnl_pct": h.pnl_pct,
            "currency": h.currency,
            "sector": h.sector,
        }
        for h in holdings
    ]
    return {"holdings": rows, "count": len(rows)}


def _run_get_price_history(ticker: str, days: int = 60) -> Dict[str, Any]:
    from utils.data_cache import OHLCVCache

    cache = OHLCVCache()
    data = cache.get(ticker, days=days)
    if data is None or data.empty:
        return {"ticker": ticker, "rows": [], "note": "데이터 없음"}

    tail = data.tail(60)
    rows = []
    for idx, row in tail.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        rows.append(
            {
                "date": date_str,
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                "volume": _safe_float(row.get("volume")),
            }
        )
    return {"ticker": ticker, "rows": rows, "count": len(rows)}


def _run_get_indicators(ticker: str, days: int = 120) -> Dict[str, Any]:
    from utils.data_cache import OHLCVCache
    from discovery.indicators import calculate_indicators, calculate_stochastic, get_ma_distances

    cache = OHLCVCache()
    data = cache.get(ticker, days=days)
    if data is None or data.empty:
        return {"ticker": ticker, "error": "데이터 없음"}

    try:
        base = calculate_indicators(ticker, period=days, data=data)
    except Exception as exc:
        logger.warning("calculate_indicators failed for %s: %s", ticker, exc)
        base = {}

    stoch_k = stoch_d = None
    try:
        k_series, d_series = calculate_stochastic(data["high"], data["low"], data["close"])
        stoch_k = _safe_last_series(k_series)
        stoch_d = _safe_last_series(d_series)
    except Exception as exc:
        logger.warning("calculate_stochastic failed for %s: %s", ticker, exc)

    ma_distances: Dict[str, Any] = {}
    try:
        ma_distances = get_ma_distances(ticker, periods=[20, 60, 120, 240], data=data)
    except Exception as exc:
        logger.warning("get_ma_distances failed for %s: %s", ticker, exc)

    obv_trend = None
    try:
        close = data["close"]
        volume = data["volume"]
        obv = (volume * close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
        if len(obv) >= 20:
            recent_obv = obv.iloc[-20:]
            slope = (recent_obv.iloc[-1] - recent_obv.iloc[0]) / 20
            obv_trend = "상승" if slope > 0 else "하락"
    except Exception as exc:
        logger.warning("OBV trend failed for %s: %s", ticker, exc)

    return {
        "ticker": ticker,
        "current_price": base.get("current_price"),
        "rsi": base.get("rsi"),
        "macd": {
            "value": base.get("macd"),
            "signal": base.get("macd_signal"),
            "histogram": base.get("macd_histogram"),
        },
        "bollinger_bands": {
            "upper": base.get("bb_upper"),
            "middle": base.get("bb_middle"),
            "lower": base.get("bb_lower"),
            "width": base.get("bb_width"),
        },
        "moving_averages": {
            "ma_20": base.get("ma_20"),
            "ma_60": base.get("ma_60"),
            "ma_120": base.get("ma_120"),
            "ma_240": base.get("ma_240"),
        },
        "ma_distances_pct": {
            str(period): info.get("distance_pct")
            for period, info in ma_distances.items()
        },
        "stochastic": {"k": stoch_k, "d": stoch_d},
        "obv_trend": obv_trend,
        "volume_ratio": base.get("volume_ratio"),
        "high_52w": base.get("high_52w"),
        "low_52w": base.get("low_52w"),
    }


def _run_get_news(ticker: str, limit: int = 5) -> Dict[str, Any]:
    try:
        from news.aggregator import get_news as _get_news

        items = _get_news(ticker, limit=limit)
        rows = [
            {
                "title": item.title,
                "summary": getattr(item, "summary", None),
                "published_at": (
                    item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else None
                ),
                "source": getattr(item, "source", None),
                "url": getattr(item, "url", None),
            }
            for item in items
        ]
        return {"ticker": ticker, "news": rows, "count": len(rows)}
    except Exception as exc:
        logger.warning("News service unavailable: %s", exc)
        return {"ticker": ticker, "news": [], "note": "뉴스 서비스 사용 불가"}


def _run_get_macro_context() -> Dict[str, Any]:
    try:
        from api.services.macro_market_service import get_macro_market_service

        bundle = get_macro_market_service().get_bundle()
        signal = bundle.get("signal", {})
        fx = bundle.get("fx", {})
        interpretation = bundle.get("interpretation", {})
        futures = bundle.get("futures", {})
        return {
            "macro_score": signal.get("score"),
            "regime": signal.get("regime"),
            "confidence_band": signal.get("confidence_band"),
            "entry_signal": interpretation.get("entry_signal"),
            "posture": interpretation.get("posture"),
            "usd_krw": fx.get("rate"),
            "usd_krw_change_pct": fx.get("change_pct"),
            "futures_change_pct": futures.get("change_pct"),
            "is_market_hours": bundle.get("is_market_hours"),
            "generated_at": bundle.get("generated_at"),
        }
    except Exception as exc:
        logger.warning("Macro service unavailable: %s", exc)
        return {"note": "매크로 데이터 사용 불가", "error": str(exc)}


# ── Tool dispatcher ────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "get_holdings": lambda inp: _run_get_holdings(),
    "get_price_history": lambda inp: _run_get_price_history(inp["ticker"], inp.get("days", 60)),
    "get_indicators": lambda inp: _run_get_indicators(inp["ticker"], inp.get("days", 120)),
    "get_news": lambda inp: _run_get_news(inp["ticker"], inp.get("limit", 5)),
    "get_macro_context": lambda inp: _run_get_macro_context(),
}


def _execute_tool(name: str, tool_input: Dict[str, Any]) -> str:
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(tool_input)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc, exc_info=True)
        return json.dumps({"error": str(exc)})


# ── Helper utilities ───────────────────────────────────────────────────────────


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _safe_last_series(series: Any) -> Optional[float]:
    try:
        if series is None or series.empty:
            return None
        val = series.iloc[-1]
        if pd.isna(val):
            return None
        f = float(val)
        return None if math.isnan(f) else f
    except Exception:
        return None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_holdings_context(holdings_json: str) -> str:
    return f"\n\n[현재 포트폴리오 현황]\n{holdings_json}"


# ── Core streaming round (runs in thread) ─────────────────────────────────────

_QUEUE_DONE = object()
_PUT_TIMEOUT = 30  # seconds
_MODEL = "claude-sonnet-4-6"


def _run_stream_round(
    client: Any,
    system: str,
    anthropic_messages: list,
    queue: "asyncio.Queue[Any]",
    loop: asyncio.AbstractEventLoop,
    max_tokens: int = 4096,
) -> None:
    """
    Execute one synchronous Claude streaming round in a background thread.

    Routes content_block_delta and content_block_stop events by block index
    so that multi-tool responses are correctly handled.

    Puts SSE payload dicts, a result tuple, then _QUEUE_DONE into *queue*.
    Always guarantees _QUEUE_DONE is enqueued — even on unexpected exceptions.
    """
    import anthropic as _anthropic

    def _put(item: Any) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(item), loop).result(timeout=_PUT_TIMEOUT)

    # Map block_index → tool_use entry for correct multi-tool routing
    tool_uses: list[dict] = []
    index_to_tool: dict[int, dict] = {}
    final_message = None

    try:
        with client.messages.stream(
            model=_MODEL,
            max_tokens=max_tokens,
            system=system,
            tools=_TOOLS,
            messages=anthropic_messages,
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", None)
                block_index = getattr(event, "index", None)

                if event_type == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block and block.type == "tool_use":
                        entry = {
                            "id": block.id,
                            "name": block.name,
                            "input_json": "",
                            "_block_index": block_index,
                        }
                        tool_uses.append(entry)
                        if block_index is not None:
                            index_to_tool[block_index] = entry
                        _put({"type": "tool_start", "name": block.name, "input": {}})

                elif event_type == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta is None:
                        continue
                    delta_type = getattr(delta, "type", None)

                    if delta_type == "text_delta":
                        text = getattr(delta, "text", "")
                        if text:
                            _put({"type": "text", "content": text})

                    elif delta_type == "input_json_delta":
                        # Route by block index to avoid corrupting multi-tool inputs
                        target = index_to_tool.get(block_index) if block_index is not None else (tool_uses[-1] if tool_uses else None)
                        if target is not None:
                            target["input_json"] += getattr(delta, "partial_json", "")

                elif event_type == "content_block_stop":
                    # Only emit tool_end for tool_use blocks; text block stops are ignored.
                    # Using block_index lookup ensures we never fire tool_end for a text block.
                    if block_index is not None and block_index in index_to_tool:
                        target = index_to_tool[block_index]
                        try:
                            target["input"] = json.loads(target["input_json"] or "{}")
                        except json.JSONDecodeError:
                            target["input"] = {}
                        _put({"type": "tool_end", "name": target["name"]})

            final_message = stream.get_final_message()

    except _anthropic.APIError as exc:
        logger.error("Anthropic API error: %s", exc)
        _put({"type": "error", "message": f"API 오류: {str(exc)}"})
    except Exception as exc:
        # Catch all unexpected errors (network, SSL, etc.) so _QUEUE_DONE is always sent
        logger.error("Unexpected error in stream round: %s", exc, exc_info=True)
        _put({"type": "error", "message": f"스트림 오류: {str(exc)}"})

    _put((tool_uses, final_message))
    _put(_QUEUE_DONE)


# ── Main streaming generator ───────────────────────────────────────────────────

_TOOL_TIMEOUT = 30.0   # seconds per tool call
_QUEUE_TIMEOUT = 60.0  # seconds to wait for next queue item
_MAX_TOOL_ROUNDS = 8


async def stream_chat(messages: list, include_portfolio: bool = True) -> AsyncIterator[str]:
    """
    Stream a chat response using Claude with tool_use.

    Yields SSE-formatted strings: data: <json>\\n\\n
    """
    try:
        import anthropic
        from api.config import get_settings

        settings = get_settings()
        api_key = settings.anthropic_api_key
        if not api_key:
            yield _sse({"type": "error", "message": "ANTHROPIC_API_KEY가 설정되지 않았습니다."})
            return

        client = anthropic.Anthropic(api_key=api_key)

        # Build system prompt with optional portfolio context
        system = _SYSTEM_PROMPT
        if include_portfolio:
            try:
                holdings_data = await asyncio.to_thread(_run_get_holdings)
                holdings_str = json.dumps(holdings_data, ensure_ascii=False, default=str)
                system += _build_holdings_context(holdings_str)
            except Exception as exc:
                logger.warning("Failed to inject portfolio context: %s", exc)

        # Sliding window: cap the *initial* history sent to Claude.
        # Note: tool-round turns appended inside the loop below are NOT capped —
        # they grow with each tool call (bounded by _MAX_TOOL_ROUNDS).
        windowed = messages[-_MAX_HISTORY_MESSAGES:] if len(messages) > _MAX_HISTORY_MESSAGES else messages
        anthropic_messages = [{"role": m.role, "content": m.content} for m in windowed]

        loop = asyncio.get_running_loop()

        for _round in range(_MAX_TOOL_ROUNDS):
            queue: asyncio.Queue = asyncio.Queue()

            future = loop.run_in_executor(
                None,
                _run_stream_round,
                client,
                system,
                anthropic_messages,
                queue,
                loop,
            )

            tool_uses: list[dict] = []
            final_message = None

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_QUEUE_TIMEOUT)
                except asyncio.TimeoutError:
                    # Check if the thread crashed without putting _QUEUE_DONE
                    if future.done() and future.exception():
                        raise future.exception()  # type: ignore[misc]
                    yield _sse({"type": "error", "message": "응답 시간이 초과되었습니다."})
                    return

                if item is _QUEUE_DONE:
                    break
                if isinstance(item, tuple):
                    tool_uses, final_message = item
                elif isinstance(item, dict):
                    yield _sse(item)
                    if item.get("type") == "error":
                        return

            if final_message is None:
                return

            if not tool_uses:
                break

            stop_reason = getattr(final_message, "stop_reason", None)
            if stop_reason != "tool_use":
                break

            # Build assistant turn
            assistant_content = []
            for block in final_message.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    matching = next((t for t in tool_uses if t.get("id") == block.id), None)
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": matching.get("input", {}) if matching else {},
                        }
                    )

            anthropic_messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools with per-tool timeout
            tool_results = []
            for tool_use_block in final_message.content:
                if tool_use_block.type != "tool_use":
                    continue
                matching = next((t for t in tool_uses if t.get("id") == tool_use_block.id), None)
                tool_input = matching.get("input", {}) if matching else {}
                try:
                    result_json = await asyncio.wait_for(
                        asyncio.to_thread(_execute_tool, tool_use_block.name, tool_input),
                        timeout=_TOOL_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    result_json = json.dumps({"error": f"{tool_use_block.name} 조회 시간 초과"})
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": result_json,
                    }
                )

            anthropic_messages.append({"role": "user", "content": tool_results})

        else:
            # Exhausted MAX_TOOL_ROUNDS
            yield _sse({"type": "error", "message": "도구 호출이 최대 횟수에 도달했습니다. 질문을 더 간단하게 나눠서 시도해주세요."})
            return

        yield _sse({"type": "done"})

    except Exception as exc:
        logger.error("stream_chat unexpected error: %s", exc, exc_info=True)
        yield _sse({"type": "error", "message": str(exc)})
