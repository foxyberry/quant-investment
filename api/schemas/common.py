"""
Common schemas for API responses.

Provides generic response wrappers and shared schema definitions.
"""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for response data (응답 데이터 제네릭 타입)
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper.

    Provides a consistent structure for all API responses.

    Attributes:
        success: Whether the request was successful
        data: Response payload (generic type)
        message: Optional message describing the response
        timestamp: Response timestamp in UTC
    """

    success: bool = Field(default=True, description="Whether the request was successful")
    data: Optional[T] = Field(default=None, description="Response payload")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(),
        description="Response timestamp (UTC)",
    )


class ErrorDetail(BaseModel):
    """
    Error detail information.

    Attributes:
        field: Field name that caused the error (optional)
        message: Error message
        code: Error code for programmatic handling
    """

    field: Optional[str] = Field(default=None, description="Field name that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")


class ErrorResponse(BaseModel):
    """
    Error response schema.

    Used for returning structured error information.

    Attributes:
        success: Always False for error responses
        error: Main error message
        details: List of detailed error information
        timestamp: Error timestamp in UTC
    """

    success: bool = Field(default=False, description="Always False for errors")
    error: str = Field(..., description="Main error message")
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Detailed error information",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(),
        description="Error timestamp (UTC)",
    )


class HealthResponse(BaseModel):
    """
    Health check response schema.

    Attributes:
        status: Health status (healthy, degraded, unhealthy)
        timestamp: Check timestamp in UTC
        version: Application version
        details: Additional health check details
    """

    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "degraded", "unhealthy"],
    )
    timestamp: datetime = Field(..., description="Check timestamp (UTC)")
    version: str = Field(..., description="Application version")
    details: Optional[dict] = Field(
        default=None,
        description="Additional health check details",
    )
