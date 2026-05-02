"""Tests for PortfolioManager sell-condition resolution."""

from __future__ import annotations

from pathlib import Path

from screener.portfolio_manager import PortfolioManager


def _write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(body, encoding="utf-8")
    return config_path


def test_get_sell_conditions_for_returns_defaults_without_holding_override(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
default_sell_conditions:
  stop_loss_pct: 0.05
  take_profit_pct: 0.15
  trailing_stop_pct: 0.08
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08


def test_get_sell_conditions_for_merges_sell_conditions_override(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
default_sell_conditions:
  stop_loss_pct: 0.05
  take_profit_pct: 0.15
  trailing_stop_pct: 0.08
holdings:
  AAPL:
    sell_conditions:
      take_profit_pct: 0.25
      trailing_stop_pct: 0.12
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.25
    assert conditions.trailing_stop_pct == 0.12


def test_get_sell_conditions_for_supports_legacy_custom_conditions_key(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
default_sell_conditions:
  stop_loss_pct: 0.05
  take_profit_pct: 0.15
  trailing_stop_pct: 0.08
holdings:
  TSLA:
    custom_conditions:
      stop_loss_pct: 0.03
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("tsla")

    assert conditions.stop_loss_pct == 0.03
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08
