"""
Execution history API schemas.

Pydantic models for execution history request/response validation
and a fingerprint utility for duplicate detection.
"""

import hashlib
import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def compute_fingerprint(
    execution_type: str,
    preset: str,
    universes: List[str],
    reference_date: Optional[str],
    params: Optional[Dict[str, Any]],
) -> str:
    """Compute a SHA-256 fingerprint for duplicate detection.

    Builds a canonical JSON string from the execution parameters
    and returns its hex digest.
    """
    canonical = {
        "execution_type": execution_type,
        "preset": preset,
        "universes": sorted(universes),
        "reference_date": reference_date,
        "params": params,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ExecutionHistoryCreate(BaseModel):
    """Request payload for recording an execution history entry."""

    execution_type: Literal["screening", "strategy"] = Field(
        ..., description="Type of execution: 'screening' or 'strategy'"
    )
    preset: str = Field(..., description="Preset name used for execution")
    universes: List[str] = Field(..., description="List of universe identifiers")
    reference_date: Optional[str] = Field(
        None, description="Reference date string (e.g. '2025-01-15')"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Optional override parameters"
    )
    graph: Optional[Dict[str, Any]] = Field(
        None, description="Inline strategy graph for sample: presets"
    )
    total_count: int = Field(..., ge=0, description="Total number of stocks evaluated")
    matched_count: int = Field(..., ge=0, description="Number of matched stocks")
    elapsed_ms: Optional[float] = Field(
        None, description="Execution time in milliseconds"
    )
    results: List[Dict[str, Any]] = Field(
        ..., description="Full results array"
    )
    name: Optional[str] = Field(
        None, max_length=255, description="Optional user-given name"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Optional description"
    )
    strategy_id: Optional[str] = Field(
        None, description="Linked strategy ID if applicable"
    )


class ExecutionHistorySummary(BaseModel):
    """Lightweight summary of an execution history entry (excludes results)."""

    id: str
    execution_type: str
    preset: str
    universes: List[str]
    reference_date: Optional[str] = None
    total_count: int
    matched_count: int
    elapsed_ms: Optional[float] = None
    name: Optional[str] = None
    description: Optional[str] = None
    strategy_id: Optional[str] = None
    created_at: str


class ExecutionHistoryDetail(ExecutionHistorySummary):
    """Full execution history entry including results data."""

    results: List[Dict[str, Any]]


class ExecutionHistoryListResponse(BaseModel):
    """Paginated list of execution history summaries."""

    items: List[ExecutionHistorySummary]
    total_count: int


class DuplicateCheckResponse(BaseModel):
    """Response for duplicate execution check via fingerprint."""

    exists: bool
    existing_id: Optional[str] = None
    created_at: Optional[str] = None
