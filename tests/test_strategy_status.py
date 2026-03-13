"""
Tests for strategy status lifecycle feature.

Verifies:
  - Status column default, CRUD with status, status-only PATCH
  - Status validation (valid/invalid values)
  - Migration function for existing databases
"""

import sys
import os
import uuid
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.models.strategy import Strategy, VALID_STATUSES
from api.schemas.strategy import (
    SavedStrategyResponse,
    StrategySaveRequest,
    StrategyStatusUpdateRequest,
    StrategyUpdateRequest,
    StrategyGraph,
    StrategyNode,
    StrategyNodeData,
    StrategyEdge,
    VALID_STRATEGY_STATUSES,
)
from api.services.strategy_save_service import StrategySaveService


# --- Fixtures ---

def _make_graph() -> StrategyGraph:
    return StrategyGraph(
        nodes=[
            StrategyNode(
                id="u1",
                data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"]),
            ),
            StrategyNode(
                id="o1",
                data=StrategyNodeData(node_type="output"),
            ),
        ],
        edges=[
            StrategyEdge(id="e1", source="u1", target="o1"),
        ],
    )


@pytest.fixture(autouse=True)
def _use_in_memory_db(monkeypatch):
    """Override database to use in-memory SQLite for tests."""
    from api import database
    from api.services import strategy_save_service

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "SessionLocal", TestSession)

    database.Base.metadata.create_all(bind=test_engine)

    # Reset singleton so each test gets a fresh service
    monkeypatch.setattr(strategy_save_service, "_strategy_save_service", None)

    yield
    database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def service() -> StrategySaveService:
    return StrategySaveService()


# --- Tests: Model ---

class TestStrategyModel:
    def test_valid_statuses_set(self):
        assert VALID_STATUSES == {"draft", "backtested", "validated", "production", "retired"}

    def test_default_status_column_exists(self):
        """Strategy model has a status column with default 'draft'."""
        col = Strategy.__table__.columns["status"]
        assert col.default.arg == "draft"
        assert not col.nullable


# --- Tests: Schema validation ---

class TestSchemaValidation:
    def test_status_update_valid(self):
        req = StrategyStatusUpdateRequest(status="backtested")
        assert req.status == "backtested"

    def test_status_update_all_valid_values(self):
        for status in VALID_STRATEGY_STATUSES:
            req = StrategyStatusUpdateRequest(status=status)
            assert req.status == status

    def test_status_update_invalid(self):
        with pytest.raises(ValueError, match="Invalid status"):
            StrategyStatusUpdateRequest(status="invalid_status")

    def test_save_request_default_status(self):
        req = StrategySaveRequest(name="test", graph=_make_graph())
        assert req.status == "draft"

    def test_save_request_custom_status(self):
        req = StrategySaveRequest(name="test", graph=_make_graph(), status="backtested")
        assert req.status == "backtested"

    def test_update_request_status_optional(self):
        req = StrategyUpdateRequest(name="updated")
        assert req.status is None

    def test_update_request_with_status(self):
        req = StrategyUpdateRequest(status="validated")
        assert req.status == "validated"

    def test_save_request_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid status"):
            StrategySaveRequest(name="test", graph=_make_graph(), status="bogus")

    def test_update_request_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid status"):
            StrategyUpdateRequest(status="bogus")

    def test_response_includes_status(self):
        resp = SavedStrategyResponse(
            id="abc",
            name="test",
            graph=_make_graph(),
            status="production",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert resp.status == "production"

    def test_response_default_status(self):
        resp = SavedStrategyResponse(
            id="abc",
            name="test",
            graph=_make_graph(),
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert resp.status == "draft"


# --- Tests: Service CRUD with status ---

class TestServiceStatus:
    def test_save_default_status(self, service):
        req = StrategySaveRequest(name="s1", graph=_make_graph())
        result = service.save_strategy(req)
        assert result.status == "draft"

    def test_save_custom_status(self, service):
        req = StrategySaveRequest(name="s2", graph=_make_graph(), status="backtested")
        result = service.save_strategy(req)
        assert result.status == "backtested"

    def test_update_status_via_update(self, service):
        req = StrategySaveRequest(name="s3", graph=_make_graph())
        saved = service.save_strategy(req)
        assert saved.status == "draft"

        update = StrategyUpdateRequest(status="validated")
        updated = service.update_strategy(saved.id, update)
        assert updated is not None
        assert updated.status == "validated"

    def test_update_status_dedicated(self, service):
        req = StrategySaveRequest(name="s4", graph=_make_graph())
        saved = service.save_strategy(req)

        updated = service.update_status(saved.id, "production")
        assert updated is not None
        assert updated.status == "production"

    def test_update_status_nonexistent(self, service):
        result = service.update_status("nonexistent_id", "draft")
        assert result is None

    def test_status_persists_on_get(self, service):
        req = StrategySaveRequest(name="s5", graph=_make_graph())
        saved = service.save_strategy(req)
        service.update_status(saved.id, "retired")

        fetched = service.get_strategy(saved.id)
        assert fetched is not None
        assert fetched.status == "retired"

    def test_status_in_list(self, service):
        req = StrategySaveRequest(name="s6", graph=_make_graph(), status="validated")
        service.save_strategy(req)

        strategies = service.list_strategies()
        assert len(strategies) >= 1
        found = [s for s in strategies if s.name == "s6"]
        assert found[0].status == "validated"

    def test_full_lifecycle(self, service):
        """Walk through draft → backtested → validated → production → retired."""
        req = StrategySaveRequest(name="lifecycle", graph=_make_graph())
        saved = service.save_strategy(req)
        assert saved.status == "draft"

        for status in ["backtested", "validated", "production", "retired"]:
            result = service.update_status(saved.id, status)
            assert result.status == status

    def test_invalid_transition_blocked(self, service):
        """production → backtested should be rejected."""
        req = StrategySaveRequest(name="transition_test", graph=_make_graph())
        saved = service.save_strategy(req)
        service.update_status(saved.id, "production")

        with pytest.raises(ValueError, match="Invalid transition"):
            service.update_status(saved.id, "backtested")

    def test_retired_can_revert_to_draft(self, service):
        req = StrategySaveRequest(name="revert_test", graph=_make_graph())
        saved = service.save_strategy(req)
        service.update_status(saved.id, "retired")

        result = service.update_status(saved.id, "draft")
        assert result.status == "draft"

    def test_same_status_noop(self, service):
        """Setting same status should succeed (no-op)."""
        req = StrategySaveRequest(name="noop_test", graph=_make_graph())
        saved = service.save_strategy(req)
        result = service.update_status(saved.id, "draft")
        assert result.status == "draft"

    def test_status_not_overwritten_on_name_update(self, service):
        req = StrategySaveRequest(name="s7", graph=_make_graph())
        saved = service.save_strategy(req)
        service.update_status(saved.id, "production")

        # Update name only — status should stay production
        updated = service.update_strategy(saved.id, StrategyUpdateRequest(name="s7_renamed"))
        assert updated.status == "production"


# --- Tests: Migration ---

class TestMigration:
    def test_migrate_strategy_status_noop_when_exists(self):
        """Migration should be a no-op when status column already exists."""
        from api.database import _migrate_strategy_status
        # Column already exists from create_all in fixture — should not raise
        _migrate_strategy_status()
