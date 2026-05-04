"""Tests for PortfolioManager sell-condition resolution."""

from __future__ import annotations

from pathlib import Path

from screener.portfolio_manager import PortfolioManager


class StubProvider:
    def __init__(
        self,
        *,
        default_sell_conditions: dict[str, float] | None = None,
        technical_signals_config: dict | None = None,
        technical_signals_enabled: bool = True,
        sell_condition_overrides: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self._default_sell_conditions = default_sell_conditions or {
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.15,
            "trailing_stop_pct": 0.08,
        }
        self._technical_signals_config = technical_signals_config or {}
        self._technical_signals_enabled = technical_signals_enabled
        self._sell_condition_overrides = sell_condition_overrides or {}

    def get_default_sell_conditions(self) -> dict[str, float]:
        return self._default_sell_conditions

    def get_technical_signals_config(self) -> dict:
        return self._technical_signals_config

    def is_technical_signals_enabled(self) -> bool:
        return self._technical_signals_enabled

    def get_holdings(self):
        return []

    def get_sell_condition_overrides(self, symbol: str) -> dict[str, float]:
        return self._sell_condition_overrides.get(symbol.upper(), {})


def _write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(body, encoding="utf-8")
    return config_path


def test_get_sell_conditions_for_returns_provider_defaults_without_holding_override(tmp_path):
    manager = PortfolioManager(
        config_path=str(_write_config(tmp_path, "")),
        provider=StubProvider(),
    )

    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08


def test_get_sell_conditions_for_merges_yaml_override_on_top_of_provider_defaults(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
holdings:
  AAPL:
    sell_conditions:
      take_profit_pct: 0.25
      trailing_stop_pct: 0.12
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path), provider=StubProvider())
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.25
    assert conditions.trailing_stop_pct == 0.12


def test_get_sell_conditions_for_supports_legacy_custom_conditions_key(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
holdings:
  TSLA:
    custom_conditions:
      stop_loss_pct: 0.03
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path), provider=StubProvider())
    conditions = manager.get_sell_conditions_for("tsla")

    assert conditions.stop_loss_pct == 0.03
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08


def test_get_sell_conditions_for_prefers_provider_overrides_over_yaml_override(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
holdings:
  AAPL:
    sell_conditions:
      trailing_stop_pct: 0.20
""".strip(),
    )

    manager = PortfolioManager(
        config_path=str(config_path),
        provider=StubProvider(
            sell_condition_overrides={"AAPL": {"trailing_stop_pct": 0.12}},
        ),
    )
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.trailing_stop_pct == 0.12
