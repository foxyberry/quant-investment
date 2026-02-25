from itertools import combinations

import pandas as pd

from screener.conditions.registry import get_condition_class_map, get_condition_metadata


LAGS = [1, 2, 3, 5, 10, 20, 60]


def _expected_keys() -> list[str]:
    keys: list[str] = []
    for field in ["close", "open", "high", "low"]:
        for left_lag, right_lag in combinations(LAGS, 2):
            keys.append(f"{field}_lag_{left_lag}_gt_{right_lag}")
            keys.append(f"{field}_lag_{left_lag}_lt_{right_lag}")

    for left_lag, right_lag in combinations(LAGS, 2):
        keys.append(f"volume_lag_{left_lag}_gt_{right_lag}")

    for short_period in [2, 3, 5, 10]:
        for long_period in [20, 60]:
            keys.append(f"volume_ma_ratio_{short_period}_{long_period}")

    for lookback_days in [1, 2, 3, 5, 10, 20]:
        keys.append(f"return_pct_{lookback_days}d_minmax")

    return keys


def _sample_df(length: int = 120) -> pd.DataFrame:
    idx = range(length)
    close = [100 + i * 0.5 for i in idx]
    return pd.DataFrame(
        {
            "open": [v - 0.3 for v in close],
            "high": [v + 1.0 for v in close],
            "low": [v - 1.0 for v in close],
            "close": close,
            "volume": [100000 + (i * 300) for i in idx],
        }
    )


def test_basic_catalog_keys_registered():
    metadata = get_condition_metadata()
    expected = _expected_keys()

    missing = [k for k in expected if k not in metadata]
    assert not missing, f"Missing catalog condition metadata keys: {missing[:10]}"


def test_basic_catalog_conditions_instantiable_and_evaluable():
    class_map = get_condition_class_map()
    df = _sample_df()

    for key in _expected_keys():
        cls = class_map[key]
        cond = cls()
        result = cond.evaluate("TEST", df)
        assert isinstance(bool(result.matched), bool)


def test_representative_logic_checks():
    class_map = get_condition_class_map()

    # close_lag_1_gt_3 should be true on increasing close series
    df_up = _sample_df(40)
    assert class_map["close_lag_1_gt_3"]().evaluate("TEST", df_up).matched is True

    # close_lag_1_lt_3 should be true on decreasing close series
    dec = list(reversed([100 + i * 0.5 for i in range(40)]))
    df_down = pd.DataFrame(
        {
            "open": [v - 0.3 for v in dec],
            "high": [v + 1.0 for v in dec],
            "low": [v - 1.0 for v in dec],
            "close": dec,
            "volume": [100000 + (i * 300) for i in range(40)],
        }
    )
    assert class_map["close_lag_1_lt_3"]().evaluate("TEST", df_down).matched is True

    # volume ratio should pass when recent volume is materially larger than long average
    vol = [100000] * 70 + [150000] * 10
    df_vol = pd.DataFrame(
        {
            "open": [100.0] * 80,
            "high": [101.0] * 80,
            "low": [99.0] * 80,
            "close": [100.0] * 80,
            "volume": vol,
        }
    )
    cond = class_map["volume_ma_ratio_2_20"](min_ratio=1.1, max_ratio=2.0)
    assert cond.evaluate("TEST", df_vol).matched is True
