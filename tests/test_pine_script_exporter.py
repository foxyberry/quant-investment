"""Tests for Pine Script v5 exporter."""

import pytest

from api.services.pine_script_exporter import export_pine_script


def _make_graph(*conditions):
    """Helper to build a graph dict with condition nodes."""
    nodes = []
    for i, (ct, params) in enumerate(conditions):
        nodes.append({
            "id": f"node-{i}",
            "data": {
                "node_type": "condition",
                "condition_type": ct,
                "params": params,
            },
        })
    return {"nodes": nodes, "edges": []}


class TestExportPineScript:
    """Tests for the export_pine_script function."""

    def test_single_ma_cross_up(self):
        graph = _make_graph(("ma_cross_up", {"short_period": 5, "long_period": 20, "ma_type": "SMA"}))
        code = export_pine_script(graph)
        assert "//@version=5" in code
        assert 'strategy("QuantCanvas Strategy"' in code
        assert "ta.sma(close, 5)" in code
        assert "ta.sma(close, 20)" in code
        assert "ta.crossover(maShort0, maLong0)" in code
        assert "strategy.entry" in code

    def test_ema_variant(self):
        graph = _make_graph(("ma_cross_up", {"short_period": 10, "long_period": 30, "ma_type": "EMA"}))
        code = export_pine_script(graph)
        assert "ta.ema(close, 10)" in code
        assert "ta.ema(close, 30)" in code

    def test_rsi_oversold(self):
        graph = _make_graph(("rsi_oversold", {"period": 14, "threshold": 25}))
        code = export_pine_script(graph)
        assert "ta.rsi(close, 14)" in code
        assert "rsiVal0 < 25" in code

    def test_rsi_overbought(self):
        graph = _make_graph(("rsi_overbought", {"period": 14, "threshold": 75}))
        code = export_pine_script(graph)
        assert "rsiVal0 > 75" in code

    def test_rsi_range(self):
        graph = _make_graph(("rsi_range", {"period": 14, "lower": 30, "upper": 70}))
        code = export_pine_script(graph)
        assert "rsiVal0 >= 30 and rsiVal0 <= 70" in code

    def test_macd_cross_up(self):
        graph = _make_graph(("macd_cross_up", {"fast_period": 12, "slow_period": 26, "signal_period": 9}))
        code = export_pine_script(graph)
        assert "ta.macd(close, 12, 26, 9)" in code
        assert "ta.crossover(macdLine0, signalLine0)" in code

    def test_macd_cross_down(self):
        graph = _make_graph(("macd_cross_down", {}))
        code = export_pine_script(graph)
        assert "ta.crossunder(macdLine0, signalLine0)" in code

    def test_bb_lower_touch(self):
        graph = _make_graph(("bb_lower_touch", {"period": 20, "std_dev": 2.0}))
        code = export_pine_script(graph)
        assert "ta.bb(close, 20, 2.0)" in code
        assert "close <= bbLower0" in code

    def test_bb_upper_touch(self):
        graph = _make_graph(("bb_upper_touch", {}))
        code = export_pine_script(graph)
        assert "close >= bbUpper0" in code

    def test_above_ma(self):
        graph = _make_graph(("above_ma", {"period": 50, "ma_type": "EMA"}))
        code = export_pine_script(graph)
        assert "ta.ema(close, 50)" in code
        assert "close > maLine0" in code

    def test_below_ma(self):
        graph = _make_graph(("below_ma", {"period": 200}))
        code = export_pine_script(graph)
        assert "ta.sma(close, 200)" in code
        assert "close < maLine0" in code

    def test_ma_touch(self):
        graph = _make_graph(("ma_touch", {"period": 20, "tolerance": 0.01}))
        code = export_pine_script(graph)
        assert "maTouchLine0" in code
        assert "0.01" in code

    def test_min_volume(self):
        graph = _make_graph(("min_volume", {"min_volume": 500000}))
        code = export_pine_script(graph)
        assert "volume >= 500000" in code

    def test_volume_above_avg(self):
        graph = _make_graph(("volume_above_avg", {"period": 20, "multiplier": 2.0}))
        code = export_pine_script(graph)
        assert "ta.sma(volume, 20)" in code
        assert "avgVol0 * 2.0" in code

    def test_multiple_conditions_combined_with_and(self):
        graph = _make_graph(
            ("rsi_oversold", {"period": 14, "threshold": 30}),
            ("ma_cross_up", {"short_period": 10, "long_period": 20}),
        )
        code = export_pine_script(graph)
        assert "(rsiVal0 < 30) and (ta.crossover(maShort1, maLong1))" in code

    def test_custom_strategy_name(self):
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, strategy_name="My RSI Strategy")
        assert 'strategy("My RSI Strategy"' in code

    def test_take_profit_and_stop_loss(self):
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, take_profit=0.05, stop_loss=0.03)
        assert "strategy.exit" in code
        assert "profit=close * 0.05" in code
        assert "loss=close * 0.03" in code

    def test_take_profit_only(self):
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, take_profit=0.1)
        assert "profit=close * 0.1" in code
        assert "loss=" not in code

    def test_stop_loss_only(self):
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, stop_loss=0.02)
        assert "loss=close * 0.02" in code
        assert "profit=" not in code

    def test_no_exportable_conditions_returns_stub(self):
        graph = _make_graph(("unknown_condition", {}))
        code = export_pine_script(graph)
        assert "//@version=5" in code
        assert "No exportable conditions found" in code
        assert "Skipped unsupported conditions: unknown_condition" in code
        # Should NOT contain strategy.entry (no real conditions)
        assert "strategy.entry" not in code

    def test_empty_graph_returns_stub(self):
        code = export_pine_script({"nodes": [], "edges": []})
        assert "//@version=5" in code
        assert "No exportable conditions found" in code
        assert "strategy.entry" not in code

    def test_skipped_conditions_in_comments(self):
        graph = _make_graph(
            ("rsi_oversold", {}),
            ("some_unknown", {}),
        )
        code = export_pine_script(graph)
        assert "Skipped unsupported condition: some_unknown" in code

    def test_default_params_used(self):
        """When params are empty, defaults should be used."""
        graph = _make_graph(("ma_cross_up", {}))
        code = export_pine_script(graph)
        assert "ta.sma(close, 10)" in code  # default short_period
        assert "ta.sma(close, 20)" in code  # default long_period


class TestUniqueVariableNames:
    """Tests that multiple conditions of the same type get unique variable names."""

    def test_two_rsi_conditions(self):
        """Two RSI conditions with different params should not conflict."""
        graph = _make_graph(
            ("rsi_oversold", {"period": 14, "threshold": 30}),
            ("rsi_overbought", {"period": 14, "threshold": 70}),
        )
        code = export_pine_script(graph)
        assert "rsiVal0 = ta.rsi(close, 14)" in code
        assert "rsiVal1 = ta.rsi(close, 14)" in code
        assert "rsiVal0 < 30" in code
        assert "rsiVal1 > 70" in code

    def test_two_ma_conditions_different_periods(self):
        """above_ma(20) + below_ma(50) should use maLine0 and maLine1."""
        graph = _make_graph(
            ("above_ma", {"period": 20}),
            ("below_ma", {"period": 50}),
        )
        code = export_pine_script(graph)
        assert "maLine0 = ta.sma(close, 20)" in code
        assert "maLine1 = ta.sma(close, 50)" in code
        assert "close > maLine0" in code
        assert "close < maLine1" in code

    def test_macd_plus_bb_no_collision(self):
        """MACD + BB conditions should both have their variables defined."""
        graph = _make_graph(
            ("macd_cross_up", {}),
            ("bb_lower_touch", {}),
        )
        code = export_pine_script(graph)
        assert "macdLine0" in code
        assert "signalLine0" in code
        assert "bbLower1" in code
        assert "ta.crossover(macdLine0, signalLine0)" in code
        assert "close <= bbLower1" in code

    def test_two_ma_cross_up_different_params(self):
        """Two ma_cross_up with different periods should both appear."""
        graph = _make_graph(
            ("ma_cross_up", {"short_period": 5, "long_period": 20}),
            ("ma_cross_up", {"short_period": 10, "long_period": 50}),
        )
        code = export_pine_script(graph)
        assert "maShort0 = ta.sma(close, 5)" in code
        assert "maLong0 = ta.sma(close, 20)" in code
        assert "maShort1 = ta.sma(close, 10)" in code
        assert "maLong1 = ta.sma(close, 50)" in code


class TestInputSanitization:
    """Tests that user inputs are properly sanitized."""

    def test_strategy_name_injection(self):
        """Strategy name with quotes/newlines should be sanitized."""
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, strategy_name='Evil"\nstrategy.entry("hack"')
        # The sanitized name should not break out of the string literal.
        # Quotes and newlines are stripped, so the name stays inside strategy("...")
        strategy_line = [l for l in code.split('\n') if l.startswith('strategy(')][0]
        # The strategy line should have exactly the opening and closing quotes
        # around the name, plus the overlay param quotes — no injected quotes
        assert strategy_line.startswith('strategy("Evilstrategy.entry(hack"')
        # No newline injection — the strategy() call is on a single line
        assert '\n' not in strategy_line

    def test_strategy_name_special_chars_stripped(self):
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph, strategy_name='Test\\nName')
        assert '\\n' not in code.split('\n')[1]

    def test_invalid_ma_type_defaults_to_sma(self):
        graph = _make_graph(("above_ma", {"period": 20, "ma_type": "INVALID"}))
        code = export_pine_script(graph)
        assert "ta.sma(close, 20)" in code

    def test_non_numeric_period_uses_default(self):
        graph = _make_graph(("rsi_oversold", {"period": "abc", "threshold": "xyz"}))
        code = export_pine_script(graph)
        assert "ta.rsi(close, 14)" in code  # default period
        assert "rsiVal0 < 30" in code  # default threshold

    def test_and_only_note_present(self):
        """Output should note that conditions are AND-only."""
        graph = _make_graph(("rsi_oversold", {}))
        code = export_pine_script(graph)
        assert "AND logic" in code
