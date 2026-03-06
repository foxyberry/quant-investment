# Condition Test Strategy

> Date: 2026-03-06
> Status: Draft
> Author: Claude Code + Codex (discussion-based design)

## 1. Problem Statement

The project has **131 condition classes** (164+ registered keys) across 19 modules in `screener/conditions/`.

Current test gaps:

| Issue | Detail |
|-------|--------|
| **28 classes have zero tests** | ma.py(5), rsi.py(3), breakout.py(4), composite.py(3), fundamental.py(15), price.py(4), volume.py(4) |
| **No correctness verification** | Most tests only check `"key" in result.details` — never assert `result.matched` |
| **No parametrized testing** | Every test hardcodes a single scenario |
| **No integration test** | Full `StockScreener` pipeline never tested with real conditions |
| **No regression snapshots** | No golden files to detect unintended behavior changes |

In short: tests prove "it runs" but not "it judges correctly."

## 2. Design Principles

1. **Don't re-implement the indicator in the test** — use extreme synthetic patterns where the outcome is obvious
2. **Layer tests by purpose** — contract vs. semantics vs. integration
3. **Scale via automation** — registry-driven parametrize, not manual per-condition test files
4. **Minimize maintenance cost** — golden snapshots store stable subsets only

## 3. Test Architecture (5 Layers)

### L0: Interface Contract Tests (all 131 conditions)

**Purpose:** Every condition obeys the `BaseCondition` contract.

**Checks:**
- `evaluate()` returns `ConditionResult` without exception
- `result.matched` is `bool`
- `result.details` is `dict` with expected keys
- Insufficient data → `matched=False` + `error` in details
- Input DataFrame is not mutated (defensive copy check)
- `required_days` returns positive int

**Implementation:**
- Single file: `tests/test_condition_contract.py`
- `pytest.mark.parametrize` driven from `get_condition_metadata()`
- Registry `test_defaults` field provides instantiation params
- `inspect.signature` fallback for simple classes with all-default params

```python
# Pseudocode
@pytest.mark.parametrize("key,meta", get_condition_metadata().items())
def test_contract(key, meta):
    cond = create_instance(meta)
    data = build_fixture(meta.get("test_profile", "price_volume"))
    result = cond.evaluate("TEST", data)
    assert isinstance(result.matched, bool)
    assert isinstance(result.details, dict)
```

**ROI:** High discovery / Low cost / Low maintenance

---

### L1: Semantic Correctness Tests (per-group templates)

**Purpose:** Verify `matched` is True when it should be, False when it shouldn't.

**Approach — Extreme Pattern Method:**
- Don't calculate expected RSI = 28.3 → instead create 50-day monotonic decline → RSI is **definitely** below 30
- Avoid boundary values (29-31); use extremes (10/90) with wide margin

**Synthetic Data Templates:**

| Profile | Shape | Use For |
|---------|-------|---------|
| `strong_uptrend` | 120d monotonic +2%/day | MA cross up, momentum, golden cross |
| `strong_downtrend` | 120d monotonic -2%/day | RSI oversold, death cross, stop loss |
| `flat_consolidation` | 120d ±0.1% random walk | Bollinger squeeze, low volatility |
| `volume_spike` | 100d normal + 20d 5x volume | Volume spike, breakout with volume |
| `gap_up` | 100d flat + gap +10% | Gap breakout, overnight return |
| `v_recovery` | 60d down + 60d up | Return turnaround, bottom breakout |
| `high_pe_stock` | fundamental data with PE=50 | Fundamental overvaluation filters |
| `value_stock` | fundamental data with PE=8, PB=0.5 | Value condition filters |

**Per-condition:** minimum 2 scenarios — `should_match` + `should_not_match`

**Implementation:**
- `tests/test_condition_semantics.py`
- Group-based parametrize with scenario templates
- `tests/fixtures/synthetic_data.py` — shared data factory

**ROI:** Highest bug discovery / Medium cost / Medium maintenance

---

### L2: Differential Tests (standard indicators only)

**Purpose:** Cross-validate against independent reference implementation.

**Scope:** Only conditions with well-defined formulas and available reference libraries:
- MA (SMA/EMA) — `pandas.DataFrame.rolling().mean()` / `.ewm().mean()`
- RSI — `pandas_ta.rsi()` or manual Wilder smoothing
- MACD — `pandas_ta.macd()`
- ATR — `pandas_ta.atr()`
- Bollinger Bands — `pandas_ta.bbands()`
- Stochastic — `pandas_ta.stoch()`

**Implementation:**
- `tests/test_condition_differential.py`
- Compare `result.details["rsi"]` vs `pandas_ta.rsi(data["close"])[-1]`
- Tolerance: `abs(ours - reference) < 0.01` (for percentage values)

**ROI:** Very high for deep bugs / Medium-high cost / Medium maintenance

---

### L3: Metamorphic / Property-based Tests

**Purpose:** Catch logic flaws without computing expected values.

**Properties:**
1. **Scale invariance:** Multiplying all prices by K shouldn't change RSI, percent-based conditions
2. **Monotonicity:** Adding more "up" days to a strong uptrend shouldn't flip a momentum condition from True to False
3. **Suffix stability:** Prepending extra burn-in data shouldn't change the latest evaluation
4. **Negation consistency:** If `rsi_oversold(threshold=30)` matches, `rsi_overbought(threshold=30)` should not match

**Implementation:**
- `tests/test_condition_properties.py`
- Uses `hypothesis` library for automated data generation
- Start with 5-10 core conditions, expand gradually

**ROI:** High discovery for subtle bugs / Medium-high cost / Medium maintenance

---

### L4: Integration Smoke Tests (StockScreener pipeline)

**Purpose:** Verify conditions work correctly when composed in the real pipeline.

**Scenarios:**
1. Single condition → correct filter
2. AND composition → intersection
3. OR composition → union
4. Mixed fundamental + technical conditions
5. Empty universe → graceful handling

**Implementation:**
- `tests/test_screener_integration.py`
- Fixed synthetic universe (5-10 stocks with known characteristics)
- Fixed conditions with known expected pass/fail per stock
- Assert final matched set equals expected set

**ROI:** High for pipeline bugs / Medium cost / Medium maintenance

---

### L5: Golden Snapshot (regression detection)

**Purpose:** Detect any unintended behavior change across all conditions.

**What to store:**
```json
{
  "version": 1,
  "generated_at": "2026-03-06T00:00:00Z",
  "fixture": "standard_120d_mixed",
  "items": [
    {
      "condition_key": "rsi_oversold",
      "params": {"rsi_period": 14, "threshold": 30},
      "matched": true,
      "details_subset": {"rsi": 12.34}
    }
  ]
}
```

**Storage:** `tests/fixtures/golden/conditions_snapshot.v1.json`

**Update workflow:**
1. CI default: mismatch → test failure
2. Intentional change: `pytest --update-golden` regenerates snapshot
3. PR must explain why snapshot changed (condition logic change / bug fix / param change)

**Numeric tolerance:** Round floats to 4 decimal places before comparison.

**ROI:** Very high for regression / Low cost / Medium maintenance (update process)

---

## 4. Column Dependency Management

Each condition depends on different DataFrame columns. This must be explicit.

**Registry extension:**
```python
@register_condition(
    key="turnover_ratio_min",
    ...,
    test_defaults={"min_turnover_ratio": 0.01},
    test_profile="price_volume_shares",
    required_columns=["close", "volume", "shares_outstanding"],
)
```

**Test profiles → fixture factory:**

| Profile | Columns |
|---------|---------|
| `price_only` | open, high, low, close |
| `price_volume` | open, high, low, close, volume |
| `price_volume_shares` | + shares_outstanding |
| `fundamental` | + pe_ratio, pb_ratio, market_cap, ... |
| `fundamental_statements` | + revenue, net_income, total_assets, ... |

`tests/fixtures/synthetic_data.py` provides `build_fixture(profile, shape, days)`.

---

## 5. Implementation Roadmap

### Phase 1: Foundation (immediate)

| Task | Files | Description |
|------|-------|-------------|
| Add `test_defaults` to registry | `screener/conditions/registry.py` + all condition modules | Add default params for test instantiation |
| Synthetic data factory | `tests/fixtures/synthetic_data.py` | Shared data builder with profiles + shapes |
| L0 contract test | `tests/test_condition_contract.py` | Parametrized contract test for all 131 conditions |
| Fill 28 missing conditions | Same file or `test_condition_semantics.py` | At minimum L0 + L1 for untested conditions |

**Success criteria:** `pytest tests/test_condition_contract.py` — 131/131 pass

### Phase 2: Correctness (1-2 weeks after Phase 1)

| Task | Files | Description |
|------|-------|-------------|
| L1 semantic tests | `tests/test_condition_semantics.py` | True/False pair per condition with extreme patterns |
| Upgrade existing tests | `tests/test_*_batch*.py` | Add `matched` assertions to existing detail-only tests |
| L4 integration smoke | `tests/test_screener_integration.py` | 5 pipeline scenarios |
| L5 golden snapshot v1 | `tests/fixtures/golden/`, `tests/test_condition_golden.py` | Baseline snapshot |

**Success criteria:** Every condition has at least 1 True + 1 False semantic test

### Phase 3: Deep Verification (ongoing)

| Task | Files | Description |
|------|-------|-------------|
| L2 differential | `tests/test_condition_differential.py` | MA/RSI/MACD/ATR/BB/Stoch vs pandas_ta |
| L3 property-based | `tests/test_condition_properties.py` | hypothesis-driven invariant tests |
| CI separation | `.github/workflows/` | PR: L0+L1+L4 smoke / Nightly: L2+L3+full L4+golden |

**Success criteria:** Standard indicators match reference within tolerance

---

## 6. File Structure

```
tests/
├── fixtures/
│   ├── synthetic_data.py          # Shared data factory
│   └── golden/
│       └── conditions_snapshot.v1.json
├── test_condition_contract.py     # L0: all 131 conditions
├── test_condition_semantics.py    # L1: True/False pairs
├── test_condition_differential.py # L2: vs pandas_ta
├── test_condition_properties.py   # L3: hypothesis
├── test_screener_integration.py   # L4: pipeline smoke
├── test_condition_golden.py       # L5: snapshot regression
└── test_*_batch*.py               # Existing (to be upgraded)
```

---

## 7. Non-Goals

- 100% branch coverage per condition (diminishing returns)
- Testing with real market data in CI (flaky, slow)
- Replacing existing batch test files (upgrade in place)
- Testing UI rendering of condition results (separate concern)
