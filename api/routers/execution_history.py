"""
Execution History router.

Provides endpoints for execution history (screening & strategy results).
Mounted at /api/reports/executions.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from pydantic import BaseModel, Field

from api.schemas.execution_history import (
    ExecutionHistoryCreate,
    ExecutionHistoryDetail,
    ExecutionHistoryListResponse,
    DuplicateCheckResponse,
)
from api.services.execution_history_service import get_execution_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/executions", tags=["Execution History"])

_ID_PATH = Path(..., min_length=1, max_length=32, pattern=r"^[a-f0-9]{1,32}$")


@router.get(
    "",
    response_model=ExecutionHistoryListResponse,
    summary="List Execution History",
    description="List execution history records with optional filtering by type.",
)
def list_executions(
    execution_type: Optional[str] = Query(
        None, description="Filter by execution type: 'screening' or 'strategy'"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
) -> ExecutionHistoryListResponse:
    """List execution history with pagination and optional type filter."""
    svc = get_execution_history_service()
    return svc.list_executions(execution_type=execution_type, limit=limit, offset=offset)


@router.get(
    "/check-duplicate",
    response_model=DuplicateCheckResponse,
    summary="Check Duplicate Execution",
    description="Check if an execution with the same parameters already exists.",
)
def check_duplicate(
    execution_type: str = Query(..., description="'screening' or 'strategy'"),
    preset: str = Query(..., description="Preset name"),
    universes: str = Query(..., description="Comma-separated universe list"),
    reference_date: Optional[str] = Query(None, description="Reference date"),
    params: Optional[str] = Query(None, description="JSON-encoded params dict"),
) -> DuplicateCheckResponse:
    """Check if a duplicate execution exists based on fingerprint."""
    universe_list = [u.strip() for u in universes.split(",") if u.strip()]
    parsed_params = None
    if params:
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in params")
    svc = get_execution_history_service()
    return svc.check_duplicate(
        execution_type=execution_type,
        preset=preset,
        universes=universe_list,
        reference_date=reference_date,
        params=parsed_params,
    )


@router.post(
    "",
    response_model=ExecutionHistoryDetail,
    status_code=201,
    summary="Save Execution Result",
    description="Save an execution result (screening or strategy) to history.",
)
def save_execution(data: ExecutionHistoryCreate) -> ExecutionHistoryDetail:
    """Save a new execution result to history."""
    svc = get_execution_history_service()
    return svc.save_execution(data)


@router.get(
    "/{execution_id}",
    response_model=ExecutionHistoryDetail,
    summary="Get Execution Detail",
    description="Get a single execution history record with full results.",
)
def get_execution(execution_id: str = _ID_PATH) -> ExecutionHistoryDetail:
    """Get execution detail by ID."""
    svc = get_execution_history_service()
    result = svc.get_execution(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


class ExecutionUpdateRequest(BaseModel):
    """Request body for partial execution update."""
    name: str = Field(..., max_length=255, description="New name for the execution")


@router.patch(
    "/{execution_id}",
    response_model=ExecutionHistoryDetail,
    summary="Update Execution",
    description="Partially update an execution history record (e.g., rename).",
)
def update_execution(
    data: ExecutionUpdateRequest,
    execution_id: str = _ID_PATH,
) -> ExecutionHistoryDetail:
    """Update execution name."""
    svc = get_execution_history_service()
    result = svc.update_execution(execution_id, name=data.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@router.delete(
    "/{execution_id}",
    status_code=204,
    summary="Delete Execution",
    description="Delete an execution history record.",
)
def delete_execution(execution_id: str = _ID_PATH):
    """Delete an execution history record by ID."""
    svc = get_execution_history_service()
    if not svc.delete_execution(execution_id):
        raise HTTPException(status_code=404, detail="Execution not found")
