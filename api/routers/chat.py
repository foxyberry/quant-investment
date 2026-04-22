"""
Portfolio AI Chatbot router.

Exposes POST /api/chat/portfolio as a Server-Sent Events (SSE) streaming endpoint.
The endpoint streams Claude's analysis of the user's portfolio in real-time.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.config import get_settings
from api.schemas.chat import ChatRequest
from api.services.chat_service import stream_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "/portfolio",
    summary="Portfolio AI Chatbot",
    description=(
        "Stream an AI-powered portfolio analysis response via SSE. "
        "Requires ANTHROPIC_API_KEY to be set. "
        "Each SSE event is a JSON object with a 'type' field: "
        "'text' | 'tool_start' | 'tool_end' | 'done' | 'error'."
    ),
)
async def portfolio_chat(request: ChatRequest) -> StreamingResponse:
    """
    Portfolio AI chatbot endpoint (SSE streaming).

    Returns a StreamingResponse with Content-Type text/event-stream.
    Each event is a JSON payload:
      - {"type": "text",       "content": "..."}
      - {"type": "tool_start", "name": "get_indicators", "input": {...}}
      - {"type": "tool_end",   "name": "get_indicators"}
      - {"type": "done"}
      - {"type": "error",      "message": "..."}

    Args:
        request: ChatRequest with messages and portfolio context flag.

    Returns:
        StreamingResponse with SSE content.

    Raises:
        HTTPException 503: When ANTHROPIC_API_KEY is not configured.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "ANTHROPIC_API_KEY가 설정되지 않아 챗봇 서비스를 사용할 수 없습니다. "
                "서버 환경 변수 ANTHROPIC_API_KEY를 설정해 주세요."
            ),
        )

    async def event_generator():
        try:
            async for chunk in stream_chat(
                messages=request.messages,
                include_portfolio=request.include_portfolio,
            ):
                yield chunk
        except Exception as exc:
            logger.error("Chat stream generator error: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
