"""
Agent Task Service.

Business logic for tracking agent tasks backed by PostgreSQL.
"""

import logging
from datetime import datetime
from typing import List, Optional

from api.database import SessionLocal
from api.models.agent_task import AgentTask
from api.schemas.agent_task import (
    AgentTaskCreateRequest,
    AgentTaskResponse,
    AgentTaskUpdateRequest,
)

logger = logging.getLogger(__name__)


def _row_to_response(row: AgentTask) -> AgentTaskResponse:
    return AgentTaskResponse(
        id=row.id,
        task_id=row.task_id,
        session_id=row.session_id,
        agent_type=row.agent_type,
        team_name=row.team_name,
        subject=row.subject,
        description=row.description,
        status=row.status,
        files_modified=row.files_modified,
        metadata_json=row.metadata_json,
        started_at=row.started_at.isoformat() if row.started_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


class AgentTaskService:
    """Service for managing agent task tracking."""

    def create_task(self, data: AgentTaskCreateRequest) -> AgentTaskResponse:
        now = datetime.utcnow()
        row = AgentTask(
            task_id=data.task_id,
            session_id=data.session_id,
            agent_type=data.agent_type,
            team_name=data.team_name,
            subject=data.subject,
            description=data.description,
            status=data.status or "pending",
            metadata_json=data.metadata_json,
            created_at=now,
            updated_at=now,
        )
        if row.status == "in_progress":
            row.started_at = now

        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Created agent task: %s (task_id=%s)", row.id, row.task_id)
            return _row_to_response(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_task(self, task_id: str, data: AgentTaskUpdateRequest) -> Optional[AgentTaskResponse]:
        db = SessionLocal()
        try:
            row = db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
            if row is None:
                return None

            now = datetime.utcnow()

            if data.status is not None:
                old_status = row.status
                row.status = data.status
                if data.status == "in_progress" and old_status != "in_progress":
                    row.started_at = now
                if data.status == "completed" and old_status != "completed":
                    row.completed_at = now

            if data.subject is not None:
                row.subject = data.subject
            if data.description is not None:
                row.description = data.description
            if data.files_modified is not None:
                row.files_modified = data.files_modified
            if data.metadata_json is not None:
                # Merge metadata
                existing = row.metadata_json or {}
                existing.update(data.metadata_json)
                row.metadata_json = existing
            if data.session_id is not None:
                row.session_id = data.session_id

            row.updated_at = now

            db.commit()
            db.refresh(row)
            logger.info("Updated agent task: task_id=%s", task_id)
            return _row_to_response(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_task(self, task_id: str) -> Optional[AgentTaskResponse]:
        db = SessionLocal()
        try:
            row = db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
            if row is None:
                return None
            return _row_to_response(row)
        finally:
            db.close()

    def list_tasks(
        self,
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        session_id: Optional[str] = None,
        team_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[AgentTaskResponse], int]:
        db = SessionLocal()
        try:
            query = db.query(AgentTask)

            if status:
                query = query.filter(AgentTask.status == status)
            if agent_type:
                query = query.filter(AgentTask.agent_type == agent_type)
            if session_id:
                query = query.filter(AgentTask.session_id == session_id)
            if team_name:
                query = query.filter(AgentTask.team_name == team_name)

            total = query.count()
            rows = query.order_by(AgentTask.created_at.desc()).offset(offset).limit(limit).all()
            return [_row_to_response(r) for r in rows], total
        finally:
            db.close()

    def delete_task(self, task_id: str) -> bool:
        db = SessionLocal()
        try:
            row = db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
            if row is None:
                return False
            db.delete(row)
            db.commit()
            logger.info("Deleted agent task: task_id=%s", task_id)
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Singleton instance
_agent_task_service: Optional[AgentTaskService] = None


def get_agent_task_service() -> AgentTaskService:
    global _agent_task_service
    if _agent_task_service is None:
        _agent_task_service = AgentTaskService()
    return _agent_task_service
