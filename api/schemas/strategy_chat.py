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
    locale: Optional[str] = Field(
        None,
        description="UI locale for localized condition names (e.g. 'ko', 'en', 'zh')",
    )


class SuggestionValidation(BaseModel):
    """A single condition suggestion to validate."""

    condition_type: str = Field(..., description="Condition key from registry")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameter key-value pairs"
    )


class ValidatePayloadRequest(BaseModel):
    """Request to validate a structured payload from the assistant."""

    suggestions: list[SuggestionValidation] = Field(
        ..., max_length=20, description="Conditions to validate"
    )


class ParamError(BaseModel):
    """A single parameter validation error."""

    param: str
    message: str


class SuggestionResult(BaseModel):
    """Validation result for one suggestion."""

    condition_type: str
    valid: bool
    errors: list[ParamError] = Field(default_factory=list)


class ValidatePayloadResponse(BaseModel):
    """Response from payload validation."""

    results: list[SuggestionResult]
    all_valid: bool
