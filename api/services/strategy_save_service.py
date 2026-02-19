"""
Strategy Save Service.

Business logic for saving/loading strategy graphs backed by PostgreSQL.
Provides CRUD operations for saved strategies.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from api.database import SessionLocal
from api.models.strategy import Strategy
from api.schemas.strategy import (
    SavedStrategyResponse,
    StrategySaveRequest,
    StrategyUpdateRequest,
)

logger = logging.getLogger(__name__)


def _row_to_response(row: Strategy) -> SavedStrategyResponse:
    return SavedStrategyResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        graph=row.graph,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


class StrategySaveService:
    """
    Service for managing saved strategy graphs.

    Uses PostgreSQL via SQLAlchemy for persistence.
    """

    def list_strategies(self) -> List[SavedStrategyResponse]:
        """
        List all saved strategies.

        Returns:
            List of saved strategies
        """
        db = SessionLocal()
        try:
            rows = db.query(Strategy).order_by(Strategy.updated_at.desc()).all()
            return [_row_to_response(r) for r in rows]
        finally:
            db.close()

    def get_strategy(self, strategy_id: str) -> Optional[SavedStrategyResponse]:
        """
        Get one saved strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            Saved strategy if found, otherwise None
        """
        db = SessionLocal()
        try:
            row = db.get(Strategy, strategy_id)
            if row is None:
                return None
            return _row_to_response(row)
        finally:
            db.close()

    def save_strategy(self, data: StrategySaveRequest) -> SavedStrategyResponse:
        """
        Save a new strategy.

        Args:
            data: Strategy save payload

        Returns:
            Created saved strategy
        """
        strategy_id = uuid.uuid4().hex
        now = datetime.utcnow()

        row = Strategy(
            id=strategy_id,
            name=data.name,
            description=data.description,
            graph=data.graph.model_dump(),
            created_at=now,
            updated_at=now,
        )

        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Saved strategy: %s", strategy_id)
            return _row_to_response(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_strategy(
        self, strategy_id: str, data: StrategyUpdateRequest
    ) -> Optional[SavedStrategyResponse]:
        """
        Update an existing saved strategy.

        Args:
            strategy_id: Strategy ID
            data: Strategy update payload

        Returns:
            Updated strategy if found, otherwise None
        """
        db = SessionLocal()
        try:
            row = db.get(Strategy, strategy_id)
            if row is None:
                return None

            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            if data.graph is not None:
                row.graph = data.graph.model_dump()

            row.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(row)
            logger.info("Updated strategy: %s", strategy_id)
            return _row_to_response(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a saved strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            row = db.get(Strategy, strategy_id)
            if row is None:
                return False
            db.delete(row)
            db.commit()
            logger.info("Deleted strategy: %s", strategy_id)
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Singleton instance
_strategy_save_service: Optional[StrategySaveService] = None


def get_strategy_save_service() -> StrategySaveService:
    """
    Get or create strategy save service singleton.

    Returns:
        StrategySaveService instance
    """
    global _strategy_save_service
    if _strategy_save_service is None:
        _strategy_save_service = StrategySaveService()
    return _strategy_save_service
