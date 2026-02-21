"""
Agent Task Tracking Schemas.

Pydantic models for agent task CRUD operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentTaskCreateRequest(BaseModel):
    """Request to create an agent task."""

    task_id: str = Field(..., description="Claude Code task ID")
    session_id: Optional[str] = Field(None, description="Claude Code session ID")
    agent_type: Optional[str] = Field(None, description="Subagent type")
    team_name: Optional[str] = Field(None, description="Team name")
    subject: str = Field(..., description="Task subject")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[str] = Field("pending", description="Task status")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata")


class AgentTaskUpdateRequest(BaseModel):
    """Request to update an agent task."""

    task_id: str = Field(..., description="Claude Code task ID")
    session_id: Optional[str] = Field(None, description="Claude Code session ID")
    status: Optional[str] = Field(None, description="Task status")
    subject: Optional[str] = Field(None, description="Task subject")
    description: Optional[str] = Field(None, description="Task description")
    files_modified: Optional[List[str]] = Field(None, description="Modified files list")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Metadata to merge")


class AgentTaskResponse(BaseModel):
    """Agent task response model."""

    id: int
    task_id: str
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    team_name: Optional[str] = None
    subject: str
    description: Optional[str] = None
    status: str
    files_modified: Optional[List[str]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class AgentTaskListResponse(BaseModel):
    """Response listing agent tasks."""

    tasks: List[AgentTaskResponse]
    total_count: int
