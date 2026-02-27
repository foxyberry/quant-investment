from unittest.mock import patch

from screener.us_fetcher import UsStockFetcher


def _make_symbols(count: int):
    return [
        {"symbol": f"T{i}", "name": f"Ticker {i}", "sector": "Test"}
        for i in range(count)
    ]


def test_sp500_invalid_cache_is_ignored_and_refreshed():
    fetcher = UsStockFetcher(use_cache=True)
    invalid_cached = _make_symbols(52)
    refreshed = _make_symbols(503)

    with (
        patch.object(fetcher, "_load_cache", return_value=invalid_cached),
        patch.object(fetcher, "_fetch_sp500_from_remote", return_value=refreshed),
        patch.object(fetcher, "_save_cache") as save_cache,
    ):
        symbols = fetcher.get_sp500_symbols(refresh=False)

    assert len(symbols) == 503
    save_cache.assert_called_once_with(refreshed)


def test_sp500_invalid_result_does_not_write_cache():
    fetcher = UsStockFetcher(use_cache=True)
    invalid_result = _make_symbols(52)

    with (
        patch.object(fetcher, "_load_cache", return_value=None),
        patch.object(fetcher, "_fetch_sp500_from_remote", return_value=invalid_result),
        patch.object(fetcher, "_save_cache") as save_cache,
    ):
        symbols = fetcher.get_sp500_symbols(refresh=False)

    assert len(symbols) == 52
    save_cache.assert_not_called()


def test_nasdaq100_invalid_cache_is_ignored_and_refreshed():
    fetcher = UsStockFetcher(use_cache=True)
    invalid_cached = _make_symbols(52)
    refreshed = _make_symbols(101)

    with (
        patch.object(fetcher, "_load_nasdaq100_cache", return_value=invalid_cached),
        patch.object(fetcher, "_fetch_nasdaq100_from_remote", return_value=refreshed),
        patch.object(fetcher, "_save_nasdaq100_cache") as save_cache,
    ):
        symbols = fetcher.get_nasdaq100_symbols(refresh=False)

    assert len(symbols) == 101
    save_cache.assert_called_once_with(refreshed)
