"""Comprehensive unit tests for utils/ttl_cache.py.

Coverage targets
----------------
- Basic get/set round trip and miss behaviour
- TTL expiry with mocked monotonic clock
- LRU eviction when max_size is exceeded
- Sentinel distinction: cached None vs cache miss
- get_or_set — loader invocation, caching, None caching
- Thundering-herd prevention: only one loader per key at a time
- Stats (hits / misses / size)
- invalidate (single key) and clear (all keys)
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from utils.ttl_cache import TTLCache, _MISSING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cache(ttl: float = 60.0, max_size: int = 512) -> TTLCache:
    """Return a fresh TTLCache with sensible test defaults."""
    return TTLCache(ttl_seconds=ttl, max_size=max_size)


# ---------------------------------------------------------------------------
# 1. Basic get / set
# ---------------------------------------------------------------------------

class TestBasicGetSet:
    def test_set_then_get_returns_value(self):
        cache: TTLCache[str] = make_cache()
        cache.set("key1", "hello")
        assert cache.get("key1") == "hello"

    def test_get_missing_key_returns_none(self):
        cache: TTLCache[int] = make_cache()
        assert cache.get("nonexistent") is None

    def test_overwrite_existing_key(self):
        cache: TTLCache[int] = make_cache()
        cache.set("x", 1)
        cache.set("x", 2)
        assert cache.get("x") == 2

    def test_multiple_independent_keys(self):
        cache: TTLCache[str] = make_cache()
        cache.set("a", "alpha")
        cache.set("b", "beta")
        assert cache.get("a") == "alpha"
        assert cache.get("b") == "beta"

    def test_integer_value_round_trip(self):
        cache: TTLCache[int] = make_cache()
        cache.set("count", 42)
        assert cache.get("count") == 42

    def test_dict_value_round_trip(self):
        cache: TTLCache[dict] = make_cache()
        payload = {"per": 15.5, "pbr": 1.2}
        cache.set("ticker", payload)
        assert cache.get("ticker") == payload


# ---------------------------------------------------------------------------
# 2. TTL expiry
# ---------------------------------------------------------------------------

class TestTTLExpiry:
    def test_entry_valid_before_ttl(self):
        cache: TTLCache[str] = make_cache(ttl=10.0)
        base_time = 1000.0
        with patch("time.monotonic", return_value=base_time):
            cache.set("k", "v")
        # 5 seconds later — still valid
        with patch("time.monotonic", return_value=base_time + 5.0):
            assert cache.get("k") == "v"

    def test_entry_expired_after_ttl(self):
        cache: TTLCache[str] = make_cache(ttl=10.0)
        base_time = 1000.0
        with patch("time.monotonic", return_value=base_time):
            cache.set("k", "v")
        # 11 seconds later — expired
        with patch("time.monotonic", return_value=base_time + 11.0):
            assert cache.get("k") is None

    def test_expired_entry_counts_as_miss(self):
        cache: TTLCache[str] = make_cache(ttl=5.0)
        base_time = 2000.0
        with patch("time.monotonic", return_value=base_time):
            cache.set("expiring", "data")
        # Access while fresh — one hit
        with patch("time.monotonic", return_value=base_time + 1.0):
            cache.get("expiring")
        # Access after expiry — should be a miss
        with patch("time.monotonic", return_value=base_time + 6.0):
            cache.get("expiring")
        stats = cache.stats
        assert stats["misses"] >= 1

    def test_expired_entry_removed_from_store(self):
        cache: TTLCache[str] = make_cache(ttl=5.0)
        base_time = 3000.0
        with patch("time.monotonic", return_value=base_time):
            cache.set("gone", "soon")
        with patch("time.monotonic", return_value=base_time + 6.0):
            cache.get("gone")
        assert cache.stats["size"] == 0

    def test_entry_exactly_at_ttl_boundary_is_expired(self):
        """An entry whose age equals ttl exactly is treated as expired
        because the condition is ``age > ttl``."""
        cache: TTLCache[str] = make_cache(ttl=10.0)
        base_time = 500.0
        with patch("time.monotonic", return_value=base_time):
            cache.set("edge", "value")
        # Exactly at boundary: monotonic() - ts == ttl is NOT expired (> ttl is expired).
        # Age == ttl is still within TTL (boundary is exclusive).
        with patch("time.monotonic", return_value=base_time + 10.0):
            assert cache.get("edge") == "value"
        # One tick past TTL
        with patch("time.monotonic", return_value=base_time + 10.001):
            assert cache.get("edge") is None

    def test_different_keys_expire_independently(self):
        cache: TTLCache[str] = make_cache(ttl=5.0)
        base = 100.0
        with patch("time.monotonic", return_value=base):
            cache.set("early", "e")
        with patch("time.monotonic", return_value=base + 3.0):
            cache.set("late", "l")
        # At base+6: "early" expired, "late" still valid
        with patch("time.monotonic", return_value=base + 6.0):
            assert cache.get("early") is None
            assert cache.get("late") == "l"


# ---------------------------------------------------------------------------
# 3. LRU eviction
# ---------------------------------------------------------------------------

class TestLRUEviction:
    def test_oldest_key_evicted_when_over_capacity(self):
        cache: TTLCache[int] = make_cache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # triggers eviction of "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_size_never_exceeds_max(self):
        cache: TTLCache[int] = make_cache(max_size=3)
        for i in range(10):
            cache.set(str(i), i)
        assert cache.stats["size"] <= 3

    def test_access_promotes_key_to_most_recent(self):
        """Reading "a" should protect it from eviction when "d" is inserted."""
        cache: TTLCache[int] = make_cache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access "a" — it becomes MRU; "b" is now LRU
        cache.get("a")
        cache.set("d", 4)  # "b" should be evicted
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_overwrite_counts_as_access_not_new_entry(self):
        cache: TTLCache[int] = make_cache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Re-set "a" — promotes to MRU; "b" becomes LRU
        cache.set("a", 10)
        cache.set("d", 4)  # "b" should be evicted
        assert cache.get("b") is None
        assert cache.get("a") == 10

    def test_exact_capacity_no_eviction(self):
        cache: TTLCache[int] = make_cache(max_size=3)
        cache.set("x", 1)
        cache.set("y", 2)
        cache.set("z", 3)
        assert cache.stats["size"] == 3
        assert cache.get("x") == 1  # all keys still present


# ---------------------------------------------------------------------------
# 4. Sentinel / None caching
# ---------------------------------------------------------------------------

class TestSentinelNoneCache:
    def test_get_returns_none_for_miss(self):
        """Cache miss and cached-None both return None from get()."""
        cache: TTLCache[None] = make_cache()
        assert cache.get("missing") is None

    def test_set_none_value_is_stored(self):
        """set(key, None) stores an entry; _get_raw must NOT return _MISSING."""
        cache: TTLCache[None] = make_cache()
        cache.set("nullish", None)
        assert cache._get_raw("nullish") is not _MISSING

    def test_get_after_set_none_returns_none(self):
        cache: TTLCache[None] = make_cache()
        cache.set("nullish", None)
        # get() returns None — same as miss, but an entry exists
        assert cache.get("nullish") is None
        # Size confirms the entry is actually there
        assert cache.stats["size"] == 1

    def test_get_or_set_does_not_call_loader_for_cached_none(self):
        """If None was explicitly cached, get_or_set must NOT invoke loader."""
        cache: TTLCache[None] = make_cache()
        cache.set("cached_none", None)
        loader = MagicMock(return_value="should_not_be_called")
        result = cache.get_or_set("cached_none", loader)
        loader.assert_not_called()
        assert result is None

    def test_size_increases_after_set_none(self):
        cache: TTLCache[None] = make_cache()
        cache.set("n1", None)
        cache.set("n2", None)
        assert cache.stats["size"] == 2


# ---------------------------------------------------------------------------
# 5. get_or_set
# ---------------------------------------------------------------------------

class TestGetOrSet:
    def test_loader_called_on_cold_cache(self):
        cache: TTLCache[str] = make_cache()
        loader = MagicMock(return_value="loaded")
        result = cache.get_or_set("k", loader)
        assert result == "loaded"
        loader.assert_called_once()

    def test_loader_not_called_on_warm_cache(self):
        cache: TTLCache[str] = make_cache()
        cache.set("k", "cached")
        loader = MagicMock(return_value="should_not_be_called")
        result = cache.get_or_set("k", loader)
        assert result == "cached"
        loader.assert_not_called()

    def test_loaded_value_is_stored_for_subsequent_gets(self):
        cache: TTLCache[int] = make_cache()
        cache.get_or_set("num", lambda: 99)
        assert cache.get("num") == 99

    def test_get_or_set_caches_none_result(self):
        cache: TTLCache[None] = make_cache()
        loader = MagicMock(return_value=None)
        first = cache.get_or_set("n", loader)
        second_loader = MagicMock(return_value="second_call")
        second = cache.get_or_set("n", second_loader)
        assert first is None
        assert second is None
        loader.assert_called_once()
        second_loader.assert_not_called()

    def test_loader_exception_propagates(self):
        cache: TTLCache[str] = make_cache()

        def bad_loader():
            raise ValueError("loader failure")

        with pytest.raises(ValueError, match="loader failure"):
            cache.get_or_set("boom", bad_loader)

    def test_failed_loader_does_not_cache_value(self):
        cache: TTLCache[str] = make_cache()
        call_count = {"n": 0}

        def flaky_loader():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("first call fails")
            return "recovered"

        with pytest.raises(RuntimeError):
            cache.get_or_set("flaky", flaky_loader)

        result = cache.get_or_set("flaky", flaky_loader)
        assert result == "recovered"
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# 6. Thundering herd prevention
# ---------------------------------------------------------------------------

class TestThunderingHerd:
    def test_only_one_loader_executes_for_same_key(self):
        """Under concurrent load the loader for a given key should run exactly once."""
        cache: TTLCache[str] = make_cache()
        loader_call_count = {"n": 0}
        barrier = threading.Barrier(10)

        def slow_loader():
            loader_call_count["n"] += 1
            time.sleep(0.05)
            return "value"

        def worker():
            barrier.wait()  # all threads start simultaneously
            return cache.get_or_set("shared_key", slow_loader)

        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(worker) for _ in range(10)]
            results = [f.result() for f in futures]

        assert loader_call_count["n"] == 1
        assert all(r == "value" for r in results)

    def test_different_keys_load_concurrently(self):
        """Loaders for *different* keys should not block each other.

        Strategy: key1's loader blocks inside an Event.wait() until key2's
        loader has already been entered.  If the per-key lock for key1 were
        accidentally blocking key2, the test would deadlock and time out.
        """
        cache: TTLCache[int] = make_cache()

        key2_entered = threading.Event()   # set when key2 loader starts
        key1_can_exit = threading.Event()  # set after key2 loader starts

        def loader_key1():
            # Wait until key2's loader has started (proves they run in parallel)
            key2_entered.wait(timeout=5.0)
            key1_can_exit.set()
            return 1

        def loader_key2():
            key2_entered.set()
            # Wait for key1 to have received the signal so both loaders overlap
            key1_can_exit.wait(timeout=5.0)
            return 2

        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(cache.get_or_set, "key1", loader_key1)
            f2 = ex.submit(cache.get_or_set, "key2", loader_key2)
            r1 = f1.result(timeout=10.0)
            r2 = f2.result(timeout=10.0)

        assert r1 == 1
        assert r2 == 2
        # Both events must have fired, confirming true overlap
        assert key2_entered.is_set()
        assert key1_can_exit.is_set()

    def test_thundering_herd_with_none_result(self):
        """Even when loader returns None, only one loader must execute."""
        cache: TTLCache[None] = make_cache()
        call_count = {"n": 0}
        barrier = threading.Barrier(5)

        def none_loader():
            call_count["n"] += 1
            time.sleep(0.03)
            return None

        def worker():
            barrier.wait()
            return cache.get_or_set("none_key", none_loader)

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(worker) for _ in range(5)]
            results = [f.result() for f in futures]

        assert call_count["n"] == 1
        assert all(r is None for r in results)


# ---------------------------------------------------------------------------
# 7. Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_initial_stats_are_zero(self):
        cache: TTLCache[int] = make_cache()
        s = cache.stats
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["size"] == 0

    def test_hit_increments_hits(self):
        cache: TTLCache[int] = make_cache()
        cache.set("h", 1)
        cache.get("h")
        assert cache.stats["hits"] == 1

    def test_miss_increments_misses(self):
        cache: TTLCache[int] = make_cache()
        cache.get("missing")
        assert cache.stats["misses"] == 1

    def test_size_reflects_current_entries(self):
        cache: TTLCache[int] = make_cache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.stats["size"] == 2

    def test_expired_entry_causes_miss(self):
        cache: TTLCache[str] = make_cache(ttl=1.0)
        base = 900.0
        with patch("time.monotonic", return_value=base):
            cache.set("expiring", "val")
        with patch("time.monotonic", return_value=base + 0.5):
            cache.get("expiring")  # hit
        with patch("time.monotonic", return_value=base + 2.0):
            cache.get("expiring")  # miss (expired)
        s = cache.stats
        assert s["hits"] == 1
        assert s["misses"] == 1

    def test_multiple_hits_and_misses_accumulate(self):
        cache: TTLCache[str] = make_cache()
        cache.set("x", "val")
        for _ in range(5):
            cache.get("x")        # 5 hits
        for _ in range(3):
            cache.get("absent")   # 3 misses
        s = cache.stats
        assert s["hits"] == 5
        assert s["misses"] == 3

    def test_stats_size_decreases_after_eviction(self):
        cache: TTLCache[int] = make_cache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.stats["size"] == 2
        cache.set("c", 3)  # evicts "a"
        assert cache.stats["size"] == 2

    def test_get_or_set_miss_then_hit_stats(self):
        cache: TTLCache[int] = make_cache()
        cache.get_or_set("k", lambda: 7)   # miss + load + set
        cache.get_or_set("k", lambda: 99)  # hit, loader not called
        s = cache.stats
        assert s["hits"] >= 1
        assert s["misses"] >= 1


# ---------------------------------------------------------------------------
# 8. Invalidate and clear
# ---------------------------------------------------------------------------

class TestInvalidateAndClear:
    def test_invalidate_removes_single_key(self):
        cache: TTLCache[int] = make_cache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_invalidate_nonexistent_key_is_noop(self):
        cache: TTLCache[int] = make_cache()
        cache.invalidate("ghost")  # should not raise
        assert cache.stats["size"] == 0

    def test_invalidate_reduces_size(self):
        cache: TTLCache[int] = make_cache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate("a")
        assert cache.stats["size"] == 1

    def test_clear_removes_all_entries(self):
        cache: TTLCache[int] = make_cache()
        for i in range(5):
            cache.set(str(i), i)
        cache.clear()
        assert cache.stats["size"] == 0

    def test_clear_allows_fresh_set(self):
        cache: TTLCache[str] = make_cache()
        cache.set("k", "old")
        cache.clear()
        cache.set("k", "new")
        assert cache.get("k") == "new"

    def test_clear_does_not_reset_stats(self):
        """clear() removes entries but does not zero-out hit/miss counters."""
        cache: TTLCache[str] = make_cache()
        cache.set("k", "v")
        cache.get("k")   # 1 hit
        cache.get("x")   # 1 miss
        cache.clear()
        s = cache.stats
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["size"] == 0

    def test_invalidate_then_reload_via_get_or_set(self):
        cache: TTLCache[int] = make_cache()
        cache.set("key", 1)
        cache.invalidate("key")
        result = cache.get_or_set("key", lambda: 99)
        assert result == 99

    def test_clear_empty_cache_is_noop(self):
        cache: TTLCache[int] = make_cache()
        cache.clear()  # should not raise
        assert cache.stats["size"] == 0
