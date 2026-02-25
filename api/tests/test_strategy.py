"""
Tests for strategy API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


class TestConditionsEndpoint:
    """Test GET /api/strategy/conditions."""

    def test_list_conditions(self):
        response = client.get("/api/strategy/conditions")
        assert response.status_code == 200
        data = response.json()
        assert "conditions" in data
        assert "categories" in data
        assert len(data["conditions"]) >= 25
        assert len(data["categories"]) >= 5

    def test_condition_structure(self):
        response = client.get("/api/strategy/conditions")
        data = response.json()
        cond = data["conditions"][0]
        assert "key" in cond
        assert "label" in cond
        assert "category" in cond
        assert "params" in cond

    def test_condition_params_structure(self):
        response = client.get("/api/strategy/conditions")
        data = response.json()
        # Find a condition with params
        cond = next(c for c in data["conditions"] if c["params"])
        param = cond["params"][0]
        assert "name" in param
        assert "type" in param
        assert "description" in param

    def test_return_turnaround_condition_exposed(self):
        response = client.get("/api/strategy/conditions")
        data = response.json()
        cond_map = {c["key"]: c for c in data["conditions"]}
        assert "return_turnaround" in cond_map


class TestRunStrategyEndpoint:
    """Test POST /api/strategy/run."""

    def test_invalid_graph_no_output(self):
        """Graph without output node should return 400."""
        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        }
                    ],
                    "edges": [],
                },
            },
        )
        assert response.status_code == 400

    def test_invalid_graph_no_conditions(self):
        """Graph with output but no conditions should return 400."""
        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "o1",
                            "data": {"node_type": "output"},
                        }
                    ],
                    "edges": [],
                },
            },
        )
        assert response.status_code == 400

    def test_invalid_condition_type(self):
        """Unknown condition type should return 400."""
        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "totally_fake_condition",
                                "params": {},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [{"id": "e1", "source": "c1", "target": "o1"}],
                },
            },
        )
        assert response.status_code == 400

    def test_valid_request_schema(self):
        """Valid graph structure should not return schema errors (may timeout/fail on execution but not 422)."""
        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "u1",
                            "data": {"node_type": "universe", "universe": "KOSPI"},
                        },
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [
                        {"id": "e1", "source": "u1", "target": "c1"},
                        {"id": "e2", "source": "c1", "target": "o1"},
                    ],
                },
            },
        )
        # Should not be a validation error (422)
        assert response.status_code != 422

    def test_invalid_universe_override_returns_standard_400(self):
        """Invalid override universe should return standard 400 message."""
        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [{"id": "e1", "source": "c1", "target": "o1"}],
                },
                "universe_overrides": ["INVALID"],
            },
        )
        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Invalid universe value(s): INVALID. Allowed values: KOSPI, KOSDAQ, SP500, NASDAQ100"
        )

    def test_multi_universe_override_is_normalized_and_reflected(self, monkeypatch):
        """Normalized override list should be returned with backward-compatible universe."""

        def _mock_execute_strategy(*args, **kwargs):
            return {
                "results": [],
                "total_count": 100,
                "matched_count": 0,
                "universe": "KOSPI",
                "conditions_used": [],
                "node_results": {},
            }

        monkeypatch.setattr("api.routers.strategy.execute_strategy", _mock_execute_strategy)

        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [{"id": "e1", "source": "c1", "target": "o1"}],
                },
                "universe_override": "kospi,kosdaq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["universe"] == "KOSPI"
        assert data["universes"] == ["KOSPI", "KOSDAQ"]

    def test_portfolio_construction_request_is_passed_and_response_contains_weights(self, monkeypatch):
        captured = {"portfolio_construction": None}

        def _mock_execute_strategy(*args, **kwargs):
            captured["portfolio_construction"] = kwargs.get("portfolio_construction")
            return {
                "results": [],
                "total_count": 10,
                "matched_count": 2,
                "universe": "SP500",
                "conditions_used": [],
                "node_results": {},
                "weighted_portfolio": [
                    {
                        "ticker": "AAPL",
                        "name": "Apple",
                        "weight": 0.5,
                        "current_price": 100.0,
                        "annualized_volatility": 0.2,
                    },
                    {
                        "ticker": "MSFT",
                        "name": "Microsoft",
                        "weight": 0.5,
                        "current_price": 200.0,
                        "annualized_volatility": 0.2,
                    },
                ],
                "portfolio_construction_result": {
                    "mode_requested": "risk_parity",
                    "mode_applied": "risk_parity",
                    "lookback_days": 60,
                    "assets_requested": 10,
                    "assets_used": 2,
                    "estimated_portfolio_volatility": 0.15,
                    "target_volatility": 0.12,
                    "suggested_gross_leverage": 0.8,
                    "fallback_reason": None,
                },
            }

        monkeypatch.setattr("api.routers.strategy.execute_strategy", _mock_execute_strategy)

        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [{"id": "e1", "source": "c1", "target": "o1"}],
                },
                "portfolio_construction": {
                    "mode": "risk_parity",
                    "lookback_days": 60,
                    "max_assets": 10,
                    "target_volatility": 0.12,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert captured["portfolio_construction"].mode == "risk_parity"
        assert len(data["weighted_portfolio"]) == 2
        assert data["portfolio_construction_result"]["mode_applied"] == "risk_parity"

    def test_ranking_config_request_is_passed_and_response_contains_long_short(self, monkeypatch):
        captured = {"ranking_config": None}

        def _mock_execute_strategy(*args, **kwargs):
            captured["ranking_config"] = kwargs.get("ranking_config")
            return {
                "results": [],
                "total_count": 10,
                "matched_count": 4,
                "universe": "SP500",
                "conditions_used": [],
                "node_results": {},
                "ranked_results": [
                    {"ticker": "MSFT", "name": "Microsoft", "score": 420.0, "rank": 1},
                    {"ticker": "AAPL", "name": "Apple", "score": 180.0, "rank": 2},
                    {"ticker": "TSLA", "name": "Tesla", "score": 120.0, "rank": 3},
                    {"ticker": "INTC", "name": "Intel", "score": 35.0, "rank": 4},
                ],
                "long_short_baskets": {
                    "metric_key": "current_price",
                    "direction": "desc",
                    "long": [
                        {"ticker": "MSFT", "name": "Microsoft", "score": 420.0, "side": "long", "weight": 1.0}
                    ],
                    "short": [
                        {"ticker": "INTC", "name": "Intel", "score": 35.0, "side": "short", "weight": 1.0}
                    ],
                },
            }

        monkeypatch.setattr("api.routers.strategy.execute_strategy", _mock_execute_strategy)

        response = client.post(
            "/api/strategy/run",
            json={
                "graph": {
                    "nodes": [
                        {
                            "id": "c1",
                            "data": {
                                "node_type": "condition",
                                "condition_type": "min_price",
                                "params": {"min_price": 5000},
                            },
                        },
                        {"id": "o1", "data": {"node_type": "output"}},
                    ],
                    "edges": [{"id": "e1", "source": "c1", "target": "o1"}],
                },
                "ranking_config": {
                    "metric_key": "current_price",
                    "direction": "desc",
                    "top_percent": 10,
                    "bottom_percent": 10,
                    "max_assets": 100,
                    "long_short": True,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert captured["ranking_config"].metric_key == "current_price"
        assert len(data["ranked_results"]) == 4
        assert data["long_short_baskets"]["long"][0]["ticker"] == "MSFT"
        assert data["long_short_baskets"]["short"][0]["ticker"] == "INTC"
