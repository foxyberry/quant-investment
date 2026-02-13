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
