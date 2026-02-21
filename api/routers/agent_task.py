"""
Agent Task Router.

Endpoints for tracking agent task execution.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.schemas.agent_task import (
    AgentTaskCreateRequest,
    AgentTaskListResponse,
    AgentTaskResponse,
    AgentTaskUpdateRequest,
)
from api.services.agent_task_service import get_agent_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-tasks", tags=["Agent Tasks"])


@router.post(
    "",
    response_model=AgentTaskResponse,
    status_code=201,
    summary="Create agent task",
    description="Create a new agent task record (called by PostToolUse hook).",
)
async def create_task(data: AgentTaskCreateRequest) -> AgentTaskResponse:
    service = get_agent_task_service()
    try:
        return service.create_task(data)
    except Exception as e:
        logger.error(f"Failed to create agent task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create agent task: {str(e)}")


@router.put(
    "/{task_id}",
    response_model=AgentTaskResponse,
    summary="Update agent task",
    description="Update an existing agent task (called by PostToolUse hook).",
)
async def update_task(task_id: str, data: AgentTaskUpdateRequest) -> AgentTaskResponse:
    service = get_agent_task_service()
    try:
        result = service.update_task(task_id, data)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Agent task not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update agent task: {str(e)}")


@router.get(
    "",
    response_model=AgentTaskListResponse,
    summary="List agent tasks",
    description="List agent tasks with optional filters.",
)
async def list_tasks(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    session_id: Optional[str] = None,
    team_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> AgentTaskListResponse:
    service = get_agent_task_service()
    try:
        tasks, total = service.list_tasks(
            status=status,
            agent_type=agent_type,
            session_id=session_id,
            team_name=team_name,
            limit=limit,
            offset=offset,
        )
        return AgentTaskListResponse(tasks=tasks, total_count=total)
    except Exception as e:
        logger.error(f"Failed to list agent tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list agent tasks: {str(e)}")


@router.get(
    "/{task_id}",
    response_model=AgentTaskResponse,
    summary="Get agent task",
    description="Get a single agent task by task_id.",
)
async def get_task(task_id: str) -> AgentTaskResponse:
    service = get_agent_task_service()
    try:
        result = service.get_task(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Agent task not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent task: {str(e)}")


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Delete agent task",
    description="Delete an agent task by task_id.",
)
async def delete_task(task_id: str) -> None:
    service = get_agent_task_service()
    try:
        success = service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent task not found: {task_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete agent task: {str(e)}")
