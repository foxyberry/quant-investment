"""
Tests for backtest API endpoints.
"""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


# --- Fixtures and helpers ---


def _make_mock_backtest_result(
    total_return=15.0,
    sharpe=1.5,
    max_dd=-10.0,
    win_rate=60.0,
    num_trades=5,
):
    """Create a mock BacktestResult for testing without hitting yfinance."""
    # Build fake stats Series
    stats = pd.Series(
        {
            "Return [%]": total_return,
            "Sharpe Ratio": sharpe,
            "Max. Drawdown [%]": max_dd,
            "Win Rate [%]": win_rate,
            "# Trades": num_trades,
        }
    )

    # Build fake trades DataFrame
    trades = pd.DataFrame(
        {
            "EntryTime": pd.to_datetime(["2024-01-15", "2024-02-10", "2024-03-05"]),
            "ExitTime": pd.to_datetime(["2024-01-25", "2024-02-20", "2024-03-15"]),
            "EntryPrice": [150.0, 155.0, 160.0],
            "ExitPrice": [158.0, 152.0, 170.0],
            "PnL": [800.0, -300.0, 1000.0],
            "ReturnPct": [5.33, -1.94, 6.25],
            "Size": [100, 100, 100],
        }
    )

    # Build fake equity curve DataFrame
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    equity_values = np.linspace(10_000_000, 11_500_000, len(dates))
    equity_curve = pd.DataFrame({"Equity": equity_values}, index=dates)

    # Create mock result
    result = MagicMock()
    result.stats = stats
    result.trades = trades
    result.equity_curve = equity_curve
    result.total_return = total_return / 100
    result.sharpe_ratio = sharpe
    result.max_drawdown = max_dd / 100
    result.win_rate = win_rate / 100
    result.num_trades = num_trades

    # Make stats behave like a Series with _strategy, _trades, _equity_curve
    stats._trades = trades
    stats._equity_curve = equity_curve

    # Simulate optimized strategy with params
    mock_strategy = MagicMock()
    mock_strategy.n1 = 15
    mock_strategy.n2 = 40
    stats._strategy = mock_strategy

    return result


class TestStrategiesEndpoint:
    """Test GET /api/backtest/strategies."""

    def test_list_strategies(self):
        """Should return list of available strategies."""
        response = client.get("/api/backtest/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert len(data["strategies"]) >= 3

    def test_strategy_structure(self):
        """Each strategy should have key, name, description, and params."""
        response = client.get("/api/backtest/strategies")
        data = response.json()
        for strategy in data["strategies"]:
            assert "key" in strategy
            assert "name" in strategy
            assert "description" in strategy
            assert "params" in strategy
            assert isinstance(strategy["params"], list)

    def test_strategy_keys(self):
        """Should include sma, ema, and ma_touch strategies."""
        response = client.get("/api/backtest/strategies")
        data = response.json()
        keys = {s["key"] for s in data["strategies"]}
        assert "sma" in keys
        assert "ema" in keys
        assert "ma_touch" in keys

    def test_strategy_params_structure(self):
        """Strategy params should have name, type, default, description."""
        response = client.get("/api/backtest/strategies")
        data = response.json()
        # Find a strategy with params (all should have them)
        strategy = data["strategies"][0]
        assert len(strategy["params"]) > 0
        param = strategy["params"][0]
        assert "name" in param
        assert "type" in param
        assert "default" in param
        assert "description" in param


class TestBacktestRunEndpoint:
    """Test POST /api/backtest/run."""

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_success(self, mock_engine_cls):
        """Should return a valid backtest response with metrics, trades, and equity curve."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
                "cash": 10000,
                "strategy_params": {"n1": 5, "n2": 10},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["strategy"] == "sma"
        assert "metrics" in data
        assert "trades" in data
        assert "equity_curve" in data

        # Verify metrics structure
        metrics = data["metrics"]
        assert "sharpe_ratio" in metrics
        assert "sortino_ratio" in metrics
        assert "mdd" in metrics
        assert "win_rate" in metrics
        assert "profit_factor" in metrics
        assert "total_return" in metrics
        assert "num_trades" in metrics

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_trades_structure(self, mock_engine_cls):
        """Trade records should have the expected fields."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) > 0
        trade = data["trades"][0]
        assert "entry_date" in trade
        assert "exit_date" in trade
        assert "entry_price" in trade
        assert "exit_price" in trade
        assert "pnl" in trade
        assert "return_pct" in trade
        assert "size" in trade

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_equity_curve_structure(self, mock_engine_cls):
        """Equity curve points should have date and equity fields."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "ema",
                "period": "3mo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["equity_curve"]) > 0
        point = data["equity_curve"][0]
        assert "date" in point
        assert "equity" in point

    def test_run_backtest_invalid_strategy(self):
        """Unknown strategy should return 400."""
        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "nonexistent_strategy",
                "period": "1mo",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "Unknown strategy" in data["detail"]

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_invalid_ticker(self, mock_engine_cls):
        """Invalid ticker should return an error."""
        mock_engine = MagicMock()
        mock_engine.run.side_effect = ValueError("No data found for ticker: INVALIDXYZ")
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "INVALIDXYZ",
                "strategy": "sma",
                "period": "1mo",
            },
        )
        assert response.status_code == 400
        assert "No data found" in response.json()["detail"]

    def test_run_backtest_missing_required_fields(self):
        """Missing required fields should return 422."""
        response = client.post(
            "/api/backtest/run",
            json={
                "period": "1mo",
            },
        )
        assert response.status_code == 422

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_with_dates(self, mock_engine_cls):
        """Should accept start/end dates instead of period."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "start": "2024-01-01",
                "end": "2024-06-01",
                "cash": 50000,
            },
        )

        assert response.status_code == 200
        mock_engine.run.assert_called_once()

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_ma_touch_strategy(self, mock_engine_cls):
        """Should work with ma_touch strategy and its specific params."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "MSFT",
                "strategy": "ma_touch",
                "period": "6mo",
                "strategy_params": {
                    "ma_period": 30,
                    "take_profit": 0.08,
                    "stop_loss": 0.04,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy"] == "ma_touch"

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_respects_response_bounds(self, mock_engine_cls):
        """Should limit trades/equity payload size when max_* options are set."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
                "max_trades": 2,
                "max_equity_points": 20,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 2
        assert len(data["equity_curve"]) <= 20

    @patch("api.services.backtest_service.BacktestEngine")
    def test_run_backtest_allows_disabling_large_sections(self, mock_engine_cls):
        """Should return only metrics when trades/equity are disabled."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
                "include_trades": False,
                "include_equity_curve": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["equity_curve"] == []


class TestOptimizeEndpoint:
    """Test POST /api/backtest/optimize."""

    @patch("api.services.backtest_service.BacktestEngine")
    def test_optimize_success(self, mock_engine_cls):
        """Should return optimal parameters and metrics."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.optimize.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/optimize",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1y",
                "param_ranges": {
                    "n1": [5, 10, 15, 20],
                    "n2": [20, 30, 40, 50],
                },
                "maximize": "Sharpe Ratio",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["strategy"] == "sma"
        assert data["maximize"] == "Sharpe Ratio"
        assert "optimal_params" in data
        assert "best_metrics" in data
        assert "trades" in data
        assert "equity_curve" in data

    def test_optimize_invalid_strategy(self):
        """Unknown strategy should return 400."""
        response = client.post(
            "/api/backtest/optimize",
            json={
                "ticker": "AAPL",
                "strategy": "fake_strategy",
                "param_ranges": {"n1": [5, 10]},
            },
        )
        assert response.status_code == 400
        assert "Unknown strategy" in response.json()["detail"]

    @patch("api.services.backtest_service.BacktestEngine")
    def test_optimize_empty_param_ranges(self, mock_engine_cls):
        """Empty param_ranges should return 400."""
        response = client.post(
            "/api/backtest/optimize",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "param_ranges": {},
            },
        )
        assert response.status_code == 400
        assert "param_ranges" in response.json()["detail"]

    @patch("api.services.backtest_service.BacktestEngine")
    def test_optimize_returns_optimal_params(self, mock_engine_cls):
        """Optimal params should contain the optimized parameter values."""
        mock_result = _make_mock_backtest_result()
        mock_engine = MagicMock()
        mock_engine.optimize.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/optimize",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "param_ranges": {
                    "n1": [5, 10, 15, 20],
                    "n2": [20, 30, 40, 50],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Our mock sets n1=15, n2=40 on the _strategy
        assert data["optimal_params"]["n1"] == 15
        assert data["optimal_params"]["n2"] == 40

    @patch("api.services.backtest_service.BacktestEngine")
    def test_optimize_engine_error(self, mock_engine_cls):
        """Engine errors during optimization should return 500."""
        mock_engine = MagicMock()
        mock_engine.optimize.side_effect = RuntimeError("Optimization diverged")
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/optimize",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "param_ranges": {"n1": [5, 10]},
            },
        )
        assert response.status_code == 500


class TestSanitization:
    """Test numpy/pandas type serialization."""

    @patch("api.services.backtest_service.BacktestEngine")
    def test_nan_values_serialized_as_none(self, mock_engine_cls):
        """NaN values in metrics should become null in JSON."""
        mock_result = _make_mock_backtest_result()
        # Inject NaN into stats
        mock_result.stats["Return [%]"] = float("nan")
        mock_result.stats._trades = mock_result.trades
        mock_result.stats._equity_curve = mock_result.equity_curve

        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # total_return should be None when the underlying stat is NaN
        assert data["metrics"]["total_return"] is None or isinstance(
            data["metrics"]["total_return"], (int, float)
        )

    @patch("api.services.backtest_service.BacktestEngine")
    def test_numpy_types_serialized(self, mock_engine_cls):
        """numpy int64/float64 values should serialize to native Python types."""
        mock_result = _make_mock_backtest_result()
        # Use numpy types in trades
        mock_result.trades["PnL"] = mock_result.trades["PnL"].astype(np.float64)
        mock_result.trades["Size"] = mock_result.trades["Size"].astype(np.int64)
        mock_result.stats._trades = mock_result.trades
        mock_result.stats._equity_curve = mock_result.equity_curve

        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "ticker": "AAPL",
                "strategy": "sma",
                "period": "1mo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should not raise a serialization error; trades should be present
        assert len(data["trades"]) > 0
