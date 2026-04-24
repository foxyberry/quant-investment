"""
Portfolio Daily Report Service.

Generates a comprehensive daily portfolio report using Claude with tool_use,
persists it to the database, and can dispatch it to Slack.

Streaming protocol: SSE with JSON payloads (same as chat_service).
  {"type": "text",       "content": "..."}
  {"type": "tool_start", "name": "get_indicators", "input": {...}}
  {"type": "tool_end",   "name": "get_indicators"}
  {"type": "done"}
  {"type": "error",      "message": "..."}
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator, Dict, Optional

from api.database import SessionLocal
from api.services.chat_service import (
    _TOOLS,
    _execute_tool,
    _run_stream_round,
    _sse,
    _QUEUE_DONE,
    _MODEL,
    _PUT_TIMEOUT,
    _QUEUE_TIMEOUT,
    _TOOL_TIMEOUT,
    _safe_float,
)

# Report generation needs far more rounds than chat:
# get_macro_context + get_holdings + N*(get_indicators + get_news) per stock
# 20 stocks × 2 tools + 2 = 42 tool calls minimum → allow 60 rounds
_REPORT_MAX_TOOL_ROUNDS = 60

logger = logging.getLogger(__name__)

_REPORT_PROMPT_VERSION = "v2"

# Max output tokens per round for report (higher than chat to allow detailed per-batch writing)
_REPORT_MAX_TOKENS = 8192

# ── Report system prompt ───────────────────────────────────────────────────────

_REPORT_SYSTEM_PROMPT = """\
당신은 퀀트 투자 전문 AI입니다. 포트폴리오 전 종목의 종합 매매 대응 전략 리포트를 작성합니다.

## 필수 작업 순서 (반드시 이 순서대로 진행)

**Step 1** — `get_macro_context` + `get_holdings` 동시 호출 → 결과 수신 즉시 아래를 작성:
  - 리포트 헤더(날짜 포함)
  - 거시경제 환경 섹션

**Step 2** — holdings 목록을 **4개씩** 끊어 배치 처리 (전체 종목 완료까지 반복):
  1. 해당 배치 4개 종목의 `get_indicators` + `get_news` 동시 호출
  2. tool 결과 수신 즉시 해당 4개 종목 분석 내용을 작성
  3. 바로 다음 4개 종목 배치로 이동

**Step 3** — 전체 종목 분석 완료 후 핵심 액션 아이템 섹션 작성

## 핵심 규칙
- **절대 모든 데이터를 다 수집한 뒤 한번에 쓰지 말 것** — 배치마다 즉시 작성하고 진행
- 각 배치 tool 결과가 오면 그 자리에서 바로 해당 종목들 분석을 출력
- 수치 근거 필수 · 구체적 매매 가격/손절선 제시 · 한국어

## 리포트 형식

### 🌐 거시경제 환경
| 항목 | 수치/상태 |
|---|---|
> 종합 판단 한 줄

### 📋 종목별 분석 및 대응 전략
🟢 수익 +5% 이상 / 🟡 -5%~+5% / 🔴 손실 -5% 초과

#### {번호}. {🔴/🟡/🟢} {종목명} ({티커}) | 수익률 {±X.XX%}
| 지표 | 수치 |
|---|---|
📌 **판단:** 한 줄 핵심
→ 구체적 행동 지침 (가격, 손절선 포함)

### 🎯 오늘의 핵심 액션 아이템
우선순위별 3~5개 종목 행동 요약\
"""

# ── Report trigger message ─────────────────────────────────────────────────────

_REPORT_USER_MESSAGE = (
    "오늘 날짜 기준으로 포트폴리오 전 종목 데일리 리포트를 작성해주세요. "
    "Step 1: get_macro_context + get_holdings 동시 호출 후 거시경제 섹션 작성. "
    "Step 2: 보유 종목을 4개씩 배치로 나눠서, 각 배치의 get_indicators + get_news 호출 후 즉시 해당 종목들 분석 작성. "
    "Step 3: 전체 완료 후 핵심 액션 아이템 작성. "
    "모든 종목을 빠짐없이 처리하세요."
)


# ── Core streaming generator ───────────────────────────────────────────────────


async def stream_report(trigger: str = "manual") -> AsyncIterator[str]:
    """
    Generate a daily portfolio report and stream via SSE.

    Accumulates full content and persists to DB on completion.

    Args:
        trigger: "manual" or "scheduled"

    Yields:
        SSE-formatted strings: data: <json>\\n\\n
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

        anthropic_messages = [{"role": "user", "content": _REPORT_USER_MESSAGE}]
        loop = asyncio.get_running_loop()

        # Track accumulated text content for DB persistence
        full_content_parts: list[str] = []
        started_at = time.monotonic()

        for _round in range(_REPORT_MAX_TOOL_ROUNDS):
            queue: asyncio.Queue = asyncio.Queue()

            future = loop.run_in_executor(
                None,
                functools.partial(
                    _run_stream_round,
                    client,
                    _REPORT_SYSTEM_PROMPT,
                    anthropic_messages,
                    queue,
                    loop,
                    _REPORT_MAX_TOKENS,
                ),
            )

            tool_uses: list[dict] = []
            final_message = None

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_QUEUE_TIMEOUT)
                except asyncio.TimeoutError:
                    if future.done() and future.exception():
                        raise future.exception()  # type: ignore[misc]
                    yield _sse({"type": "error", "message": "응답 시간이 초과되었습니다."})
                    return

                if item is _QUEUE_DONE:
                    break
                if isinstance(item, tuple):
                    tool_uses, final_message = item
                elif isinstance(item, dict):
                    # Accumulate text content for DB persistence
                    if item.get("type") == "text":
                        full_content_parts.append(item["content"])
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
            yield _sse({"type": "error", "message": "도구 호출이 최대 횟수에 도달했습니다."})
            return

        # Persist completed report to DB
        duration_sec = time.monotonic() - started_at
        full_content = "".join(full_content_parts)
        if full_content:
            await asyncio.to_thread(_save_report_to_db, full_content, trigger, duration_sec)

        yield _sse({"type": "done"})

    except Exception as exc:
        logger.error("stream_report unexpected error: %s", exc, exc_info=True)
        yield _sse({"type": "error", "message": str(exc)})


# ── DB helpers ─────────────────────────────────────────────────────────────────


def _save_report_to_db(content: str, trigger: str, duration_sec: float) -> int:
    """Persist a completed report to the portfolio_reports table. Returns new row id."""
    from api.models.portfolio import PortfolioReport

    db = SessionLocal()
    try:
        report = PortfolioReport(
            generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            trigger=trigger,
            prompt_version=_REPORT_PROMPT_VERSION,
            content=content,
            duration_sec=_safe_float(duration_sec),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        logger.info("Report saved to DB: id=%d, trigger=%s, duration=%.1fs", report.id, trigger, duration_sec)
        return report.id
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save report to DB: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


def _row_to_summary(row: Any) -> Dict[str, Any]:
    return {
        "id": row.id,
        "generated_at": row.generated_at,
        "trigger": row.trigger,
        "duration_sec": row.duration_sec,
        "content_preview": (row.content or "")[:200],
    }


def _row_to_detail(row: Any) -> Dict[str, Any]:
    d = _row_to_summary(row)
    d["content"] = row.content
    return d


# ── Public query functions ─────────────────────────────────────────────────────


def get_latest_report() -> Optional[Dict[str, Any]]:
    """Return the most recently generated report, or None if none exist."""
    from api.models.portfolio import PortfolioReport

    db = SessionLocal()
    try:
        row = (
            db.query(PortfolioReport)
            .order_by(PortfolioReport.generated_at.desc())
            .first()
        )
        return _row_to_detail(row) if row else None
    finally:
        db.close()


def list_reports(limit: int = 30) -> list[Dict[str, Any]]:
    """Return a list of report summaries (id, generated_at, trigger, duration_sec, content[:200])."""
    from api.models.portfolio import PortfolioReport

    db = SessionLocal()
    try:
        rows = (
            db.query(PortfolioReport)
            .order_by(PortfolioReport.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_summary(r) for r in rows]
    finally:
        db.close()


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    """Return full report detail by id, or None if not found."""
    from api.models.portfolio import PortfolioReport

    db = SessionLocal()
    try:
        row = db.get(PortfolioReport, report_id)
        return _row_to_detail(row) if row else None
    finally:
        db.close()


def send_report_to_slack(report_id: int) -> bool:
    """Dispatch a report's content to Slack. Returns True on success."""
    from api.services.notification_dispatcher import dispatch

    report = get_report(report_id)
    if not report:
        logger.warning("send_report_to_slack: report id=%d not found", report_id)
        return False

    content = report.get("content", "")
    if not content:
        return False

    results = dispatch(content, channels=["slack"])
    return results.get("slack", False)


# ── Sync wrapper for scheduler ─────────────────────────────────────────────────


async def generate_and_send_slack_async(trigger: str = "scheduled") -> None:
    """
    Async: generate a report (full SSE stream consumed internally) then send to Slack.
    Designed to be called with asyncio.run() from a background thread.
    """
    logger.info("Starting scheduled report generation (trigger=%s)", trigger)

    full_content_parts: list[str] = []
    started_at = time.monotonic()

    try:
        import anthropic
        from api.config import get_settings

        settings = get_settings()
        api_key = settings.anthropic_api_key
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set; skipping scheduled report")
            return

        client = anthropic.Anthropic(api_key=api_key)
        anthropic_messages = [{"role": "user", "content": _REPORT_USER_MESSAGE}]
        loop = asyncio.get_running_loop()

        for _round in range(_REPORT_MAX_TOOL_ROUNDS):
            queue: asyncio.Queue = asyncio.Queue()

            future = loop.run_in_executor(
                None,
                functools.partial(
                    _run_stream_round,
                    client,
                    _REPORT_SYSTEM_PROMPT,
                    anthropic_messages,
                    queue,
                    loop,
                    _REPORT_MAX_TOKENS,
                ),
            )

            tool_uses: list[dict] = []
            final_message = None

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_QUEUE_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.error("Scheduler report queue timeout")
                    return

                if item is _QUEUE_DONE:
                    break
                if isinstance(item, tuple):
                    tool_uses, final_message = item
                elif isinstance(item, dict):
                    if item.get("type") == "text":
                        full_content_parts.append(item["content"])
                    elif item.get("type") == "error":
                        logger.error("Scheduler report SSE error: %s", item.get("message"))
                        return

            if final_message is None:
                return

            if not tool_uses:
                break

            stop_reason = getattr(final_message, "stop_reason", None)
            if stop_reason != "tool_use":
                break

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
            logger.error("Scheduler report: max tool rounds exhausted")
            return

        full_content = "".join(full_content_parts)
        if not full_content:
            logger.warning("Scheduler report: empty content generated")
            return

        duration_sec = time.monotonic() - started_at
        report_id = await asyncio.to_thread(_save_report_to_db, full_content, trigger, duration_sec)

        # Send to Slack
        success = await asyncio.to_thread(send_report_to_slack, report_id)
        if success:
            logger.info("Scheduled report dispatched to Slack (id=%d)", report_id)
        else:
            logger.warning("Scheduled report Slack dispatch failed (id=%d)", report_id)

    except Exception as exc:
        logger.error("generate_and_send_slack_async error: %s", exc, exc_info=True)


# ── Background generation (fire-and-forget, nav-safe) ────────────────────────

_generation_lock = __import__("threading").Lock()
_is_generating: bool = False


def start_background_report(trigger: str = "manual") -> bool:
    """Start a background report generation. Returns False if already generating."""
    global _is_generating
    with _generation_lock:
        if _is_generating:
            return False
        _is_generating = True

    import threading as _t

    def _run() -> None:
        global _is_generating
        try:
            asyncio.run(generate_and_send_slack_async(trigger))
        except Exception as exc:
            logger.error("Background report generation error: %s", exc, exc_info=True)
        finally:
            with _generation_lock:
                _is_generating = False

    _t.Thread(target=_run, daemon=True, name="bg-report").start()
    return True


def get_generation_status() -> bool:
    """Return True if a report is currently being generated."""
    return _is_generating


# ── Daily scheduler (runs in background daemon thread) ────────────────────────


def run_daily_report_scheduler() -> None:
    """Block in a loop, sleeping until 09:05 KST on weekdays, then generate + send report."""
    KST = timezone(timedelta(hours=9))

    logger.info("Daily report scheduler started (target: 09:05 KST, weekdays only)")

    while True:
        now = datetime.now(KST)
        target = now.replace(hour=9, minute=5, second=0, microsecond=0)

        # Advance to next 09:05 if already past today's
        if now >= target:
            target += timedelta(days=1)

        # Skip weekends: Monday=0 … Friday=4, Saturday=5, Sunday=6
        while target.weekday() >= 5:
            target += timedelta(days=1)

        sleep_sec = (target - now).total_seconds()
        logger.info(
            "Daily report scheduler: next run at %s KST (%.0f s from now)",
            target.strftime("%Y-%m-%d %H:%M:%S (%A)"),
            sleep_sec,
        )
        time.sleep(sleep_sec)

        try:
            asyncio.run(generate_and_send_slack_async("scheduled"))
        except Exception as exc:
            logger.error("Daily report scheduler error: %s", exc, exc_info=True)
