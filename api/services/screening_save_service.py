"""
Screening Save Service.

Business logic for saving/loading screening results backed by the database.
Provides CRUD operations for saved screening results.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import defer

from api.database import SessionLocal
from api.models.screening_result import SavedScreeningResult
from api.schemas.screening import (
    SaveScreeningResultRequest,
    SavedScreeningResultResponse,
    SavedScreeningResultSummary,
)

logger = logging.getLogger(__name__)


def _row_to_summary(row: SavedScreeningResult) -> SavedScreeningResultSummary:
    return SavedScreeningResultSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        preset=row.preset,
        universes=row.universes or [],
        reference_date=row.reference_date,
        total_count=row.total_count,
        matched_count=row.matched_count,
        elapsed_ms=row.elapsed_ms,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


def _row_to_response(row: SavedScreeningResult) -> SavedScreeningResultResponse:
    return SavedScreeningResultResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        preset=row.preset,
        universes=row.universes or [],
        reference_date=row.reference_date,
        total_count=row.total_count,
        matched_count=row.matched_count,
        elapsed_ms=row.elapsed_ms,
        created_at=row.created_at.isoformat() if row.created_at else "",
        results=row.results or [],
    )


class ScreeningSaveService:
    """
    Service for managing saved screening results.

    Uses the database via SQLAlchemy for persistence.
    """

    def list_results(self) -> List[SavedScreeningResultSummary]:
        """
        List all saved screening results (lightweight, without results column).

        Returns:
            List of saved screening result summaries
        """
        db = SessionLocal()
        try:
            rows = (
                db.query(SavedScreeningResult)
                .options(defer(SavedScreeningResult.results))
                .order_by(SavedScreeningResult.created_at.desc())
                .all()
            )
            return [_row_to_summary(r) for r in rows]
        finally:
            db.close()

    def get_result(self, result_id: str) -> Optional[SavedScreeningResultResponse]:
        """
        Get one saved screening result by ID.

        Args:
            result_id: Screening result ID

        Returns:
            Saved screening result if found, otherwise None
        """
        db = SessionLocal()
        try:
            row = db.get(SavedScreeningResult, result_id)
            if row is None:
                return None
            return _row_to_response(row)
        finally:
            db.close()

    def save_result(
        self, data: SaveScreeningResultRequest
    ) -> SavedScreeningResultResponse:
        """
        Save a new screening result.

        Args:
            data: Screening result save payload

        Returns:
            Created saved screening result
        """
        result_id = uuid.uuid4().hex
        now = datetime.utcnow()

        row = SavedScreeningResult(
            id=result_id,
            name=data.name,
            description=data.description,
            preset=data.preset,
            universes=data.universes,
            reference_date=data.reference_date,
            total_count=data.total_count,
            matched_count=data.matched_count,
            elapsed_ms=data.elapsed_ms,
            results=[item.model_dump() for item in data.results],
            created_at=now,
        )

        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Saved screening result: %s", result_id)
            return _row_to_response(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_result(self, result_id: str) -> bool:
        """
        Delete a saved screening result by ID.

        Args:
            result_id: Screening result ID

        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            row = db.get(SavedScreeningResult, result_id)
            if row is None:
                return False
            db.delete(row)
            db.commit()
            logger.info("Deleted screening result: %s", result_id)
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Singleton instance
_screening_save_service: Optional[ScreeningSaveService] = None


def get_screening_save_service() -> ScreeningSaveService:
    """
    Get or create screening save service singleton.

    Returns:
        ScreeningSaveService instance
    """
    global _screening_save_service
    if _screening_save_service is None:
        _screening_save_service = ScreeningSaveService()
    return _screening_save_service
