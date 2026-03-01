"""
Strategy Chat Schemas.

Pydantic models for the strategy chatbot SSE endpoint.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant"] = Field(
        ..., description="Message role: 'user' or 'assistant'"
    )
    content: str = Field(
        ..., max_length=4000, description="Message text"
    )


class StrategyChatRequest(BaseModel):
    """Request body for the strategy chat endpoint."""

    messages: list[ChatMessage] = Field(
        ..., max_length=50, description="Conversation history (max 50 turns)"
    )
    graph: Optional[dict[str, Any]] = Field(
        None,
        description="Current strategy graph (serialized nodes and edges)",
    )
