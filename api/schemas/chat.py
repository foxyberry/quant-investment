"""
Chat schemas for portfolio AI chatbot.

Defines request/response models for the portfolio analysis chatbot endpoint.
"""

from typing import List, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message with role and content."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Request body for the portfolio chatbot endpoint."""

    messages: List[ChatMessage]
    # When True, the service automatically injects current holdings
    # into the system prompt so Claude can reference them without
    # an explicit tool call.
    include_portfolio: bool = True
