"""
Execution History Service.

Business logic for saving/loading execution history (screening & strategy results).
Provides CRUD operations with duplicate detection via fingerprint.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import defer

from api.database import SessionLocal
from api.models.execution_history import ExecutionHistory
from api.schemas.execution_history import (
    ExecutionHistoryCreate,
    ExecutionHistoryDetail,
    ExecutionHistoryListResponse,
    ExecutionHistorySummary,
    DuplicateCheckResponse,
    compute_fingerprint,
)

logger = logging.getLogger(__name__)


def _row_to_summary(row: ExecutionHistory) -> ExecutionHistorySummary:
    return ExecutionHistorySummary(
        id=row.id,
        execution_type=row.execution_type,
        preset=row.preset,
        universes=row.universes or [],
        reference_date=row.reference_date,
        total_count=row.total_count,
        matched_count=row.matched_count,
        elapsed_ms=row.elapsed_ms,
        name=row.name,
        description=row.description,
        strategy_id=row.strategy_id,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


def _row_to_detail(row: ExecutionHistory) -> ExecutionHistoryDetail:
    return ExecutionHistoryDetail(
        id=row.id,
        execution_type=row.execution_type,
        preset=row.preset,
        universes=row.universes or [],
        reference_date=row.reference_date,
        total_count=row.total_count,
        matched_count=row.matched_count,
        elapsed_ms=row.elapsed_ms,
        name=row.name,
        description=row.description,
        strategy_id=row.strategy_id,
        created_at=row.created_at.isoformat() if row.created_at else "",
        results=row.results or [],
    )


class ExecutionHistoryService:
    """Service for managing execution history records."""

    def list_executions(
        self,
        execution_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ExecutionHistoryListResponse:
        """
        List execution history records (lightweight, without results column).

        Args:
            execution_type: Filter by type ('screening' or 'strategy'), None for all
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            Paginated list of execution history summaries
        """
        db = SessionLocal()
        try:
            query = db.query(ExecutionHistory).options(
                defer(ExecutionHistory.results),
                defer(ExecutionHistory.graph),
            )
            if execution_type:
                query = query.filter(ExecutionHistory.execution_type == execution_type)

            total = query.count()
            rows = (
                query.order_by(ExecutionHistory.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return ExecutionHistoryListResponse(
                items=[_row_to_summary(r) for r in rows],
                total_count=total,
            )
        finally:
            db.close()

    def get_execution(self, execution_id: str) -> Optional[ExecutionHistoryDetail]:
        """
        Get a single execution history record by ID.

        Args:
            execution_id: Execution history ID

        Returns:
            Full execution detail if found, otherwise None
        """
        db = SessionLocal()
        try:
            row = db.get(ExecutionHistory, execution_id)
            if row is None:
                return None
            return _row_to_detail(row)
        finally:
            db.close()

    def check_duplicate(
        self,
        execution_type: str,
        preset: str,
        universes: List[str],
        reference_date: Optional[str],
        params: Optional[Dict[str, Any]],
    ) -> DuplicateCheckResponse:
        """
        Check if an execution with the same fingerprint already exists.

        Args:
            execution_type: 'screening' or 'strategy'
            preset: Preset name
            universes: Universe list
            reference_date: Reference date string
            params: Optional parameters

        Returns:
            DuplicateCheckResponse with exists flag and existing ID if found
        """
        fp = compute_fingerprint(execution_type, preset, universes, reference_date, params)
        db = SessionLocal()
        try:
            row = (
                db.query(ExecutionHistory)
                .filter(ExecutionHistory.fingerprint == fp)
                .order_by(ExecutionHistory.created_at.desc())
                .first()
            )
            if row is None:
                return DuplicateCheckResponse(exists=False)
            return DuplicateCheckResponse(
                exists=True,
                existing_id=row.id,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        finally:
            db.close()

    def save_execution(self, data: ExecutionHistoryCreate) -> ExecutionHistoryDetail:
        """
        Save a new execution history record.

        Args:
            data: Execution history payload

        Returns:
            Created execution history detail
        """
        execution_id = uuid.uuid4().hex
        now = datetime.utcnow()
        fp = compute_fingerprint(
            data.execution_type,
            data.preset,
            data.universes,
            data.reference_date,
            data.params,
        )

        row = ExecutionHistory(
            id=execution_id,
            execution_type=data.execution_type,
            preset=data.preset,
            universes=data.universes,
            reference_date=data.reference_date,
            params=data.params,
            graph=data.graph,
            total_count=data.total_count,
            matched_count=data.matched_count,
            elapsed_ms=data.elapsed_ms,
            results=data.results,
            name=data.name,
            description=data.description,
            strategy_id=data.strategy_id,
            fingerprint=fp,
            created_at=now,
        )

        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Saved execution history: %s (type=%s)", execution_id, data.execution_type)
            return _row_to_detail(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_execution(
        self, execution_id: str, name: Optional[str] = None
    ) -> Optional[ExecutionHistoryDetail]:
        """Update mutable fields of an execution record."""
        db = SessionLocal()
        try:
            row = db.get(ExecutionHistory, execution_id)
            if row is None:
                return None
            if name is not None:
                row.name = name
            db.commit()
            db.refresh(row)
            return _row_to_detail(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_execution(self, execution_id: str) -> bool:
        """
        Delete an execution history record by ID.

        Args:
            execution_id: Execution history ID

        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            row = db.get(ExecutionHistory, execution_id)
            if row is None:
                return False
            db.delete(row)
            db.commit()
            logger.info("Deleted execution history: %s", execution_id)
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Singleton instance
_execution_history_service: Optional[ExecutionHistoryService] = None


def get_execution_history_service() -> ExecutionHistoryService:
    """Get or create execution history service singleton."""
    global _execution_history_service
    if _execution_history_service is None:
        _execution_history_service = ExecutionHistoryService()
    return _execution_history_service
