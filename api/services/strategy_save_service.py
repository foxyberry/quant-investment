"""
Strategy Save Service.

Business logic for saving/loading strategy graphs as JSON files.
Provides CRUD operations for saved strategies.
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.schemas.strategy import (
    SavedStrategyResponse,
    StrategySaveRequest,
    StrategyUpdateRequest,
)

logger = logging.getLogger(__name__)


class StrategySaveService:
    """
    Service for managing saved strategy graphs.

    Uses JSON file persistence and in-memory cache with thread-safe writes.
    """

    DEFAULT_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "strategies.json"

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize strategy save service.

        Args:
            data_path: Path to strategies JSON file (default: data/strategies.json)
        """
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self._lock = threading.Lock()
        self._strategies: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load saved strategies from JSON file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    strategy_list = data.get("strategies", [])
                    self._strategies = {s["id"]: s for s in strategy_list}
                    logger.info(
                        f"Loaded {len(self._strategies)} strategies from {self.data_path}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load strategy data: {e}")
                self._strategies = {}
        else:
            # Create initial data file
            self._save()

    def _save(self) -> None:
        """Save strategies to JSON file."""
        with self._lock:
            try:
                self.data_path.parent.mkdir(parents=True, exist_ok=True)

                data = {
                    "strategies": list(self._strategies.values()),
                    "updated_at": datetime.now().isoformat(),
                }

                with open(self.data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                logger.debug(f"Saved strategy data to {self.data_path}")
            except Exception as e:
                logger.error(f"Failed to save strategy data: {e}")
                raise

    def list_strategies(self) -> List[SavedStrategyResponse]:
        """
        List all saved strategies.

        Returns:
            List of saved strategies
        """
        return [SavedStrategyResponse(**s) for s in self._strategies.values()]

    def get_strategy(self, strategy_id: str) -> Optional[SavedStrategyResponse]:
        """
        Get one saved strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            Saved strategy if found, otherwise None
        """
        strategy = self._strategies.get(strategy_id)
        if strategy is None:
            return None
        return SavedStrategyResponse(**strategy)

    def save_strategy(self, data: StrategySaveRequest) -> SavedStrategyResponse:
        """
        Save a new strategy.

        Args:
            data: Strategy save payload

        Returns:
            Created saved strategy
        """
        strategy_id = uuid.uuid4().hex
        now = datetime.now().isoformat()

        strategy = {
            "id": strategy_id,
            "name": data.name,
            "description": data.description,
            "graph": data.graph.model_dump(),
            "created_at": now,
            "updated_at": now,
        }

        self._strategies[strategy_id] = strategy
        self._save()
        logger.info(f"Saved strategy: {strategy_id}")

        return SavedStrategyResponse(**strategy)

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
        strategy = self._strategies.get(strategy_id)
        if strategy is None:
            return None

        if data.name is not None:
            strategy["name"] = data.name
        if data.description is not None:
            strategy["description"] = data.description
        if data.graph is not None:
            strategy["graph"] = data.graph.model_dump()

        strategy["updated_at"] = datetime.now().isoformat()

        self._save()
        logger.info(f"Updated strategy: {strategy_id}")
        return SavedStrategyResponse(**strategy)

    def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a saved strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            True if deleted, False if not found
        """
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            self._save()
            logger.info(f"Deleted strategy: {strategy_id}")
            return True
        return False


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
