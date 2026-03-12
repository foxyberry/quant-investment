"""FX rate collector.

Periodically fetches USD/KRW exchange rate and writes to a JSON file
for the macro monitor to consume (avoiding per-request external API calls).

Primary source: Naver Stock FX API (realtime during KRW market hours).
Fallback: Frankfurter (ECB daily rate) via ExchangeRateService.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = "data/market/fx_latest.json"
MARKET_INTERVAL_SEC = 60       # 1 min during market hours
OFF_HOURS_INTERVAL_SEC = 3600  # 1 hour outside market hours
OFF_HOURS_SLEEP_SEC = 60       # check every 60s if market opened


def _now_kst() -> datetime:
    """Return current time as timezone-aware datetime in KST."""
    import datetime as _dt
    return datetime.now(timezone.utc).astimezone(
        _dt.timezone(_dt.timedelta(hours=9))
    )


def _is_market_hours() -> bool:
    """Check if current KST time is within FX market hours (Mon-Fri, 09:00-15:40)."""
    now = _now_kst()
    if now.weekday() > 4:
        return False
    hour, minute = now.hour, now.minute
    if hour < 9:
        return False
    if hour > 15 or (hour == 15 and minute > 40):
        return False
    return True


# ---------------------------------------------------------------------------
# Source 1: Naver FX API (preferred during market hours)
# ---------------------------------------------------------------------------

def _fetch_naver_fx(reuters_code: str = "FX_USDKRW") -> Optional[Dict[str, Any]]:
    """Fetch realtime FX rate from Naver Stock front-API."""
    try:
        import requests
    except ImportError:
        return None

    url = (
        "https://m.stock.naver.com/front-api/marketIndex/productDetail"
        f"?category=exchange&reutersCode={reuters_code}"
    )
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        body = r.json()
        result = body.get("result") if body.get("isSuccess") else None
        if not result:
            return None

        value = _parse_price(result.get("closePrice"))
        if value is None:
            return None

        change_pct_raw = result.get("fluctuationsRatio")
        change_pct = _to_float(
            str(change_pct_raw).replace(",", "") if change_pct_raw is not None else None
        )

        return {
            "pair": "USD/KRW",
            "value": value,
            "change_pct": change_pct,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "naver",
        }
    except Exception as exc:
        logger.debug("Naver FX API failed for %s: %s", reuters_code, exc)
        return None


# ---------------------------------------------------------------------------
# Source 2: Frankfurter (ECB) via ExchangeRateService
# ---------------------------------------------------------------------------

def _fetch_frankfurter() -> Optional[Dict[str, Any]]:
    """Fetch FX rate from Frankfurter via ExchangeRateService."""
    try:
        from api.services.exchange_rate_service import get_exchange_rate_service
        svc = get_exchange_rate_service()
        rates = svc.get_rates(base="USD")
        value = rates.get("rates", {}).get("KRW")
        if value is None:
            return None
        return {
            "pair": "USD/KRW",
            "value": float(value),
            "change_pct": None,  # ECB doesn't provide intraday change
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "frankfurter",
        }
    except Exception as exc:
        logger.debug("Frankfurter FX fetch failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(raw: str | int | float | None) -> Optional[float]:
    """Parse Naver price string like '1,365.50' to float."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _to_float(raw: str | None) -> Optional[float]:
    """Safely convert string to float."""
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically via tmp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_fx_cache(
    path: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Read cached FX data from JSON file.

    Returns None if file doesn't exist or is unparseable.
    """
    p = Path(path or os.getenv("MACRO_FX_PATH", DEFAULT_OUTPUT_PATH))
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("FX cache read failed (%s): %s", p, exc)
        return None


# Stale thresholds (seconds) by source
STALE_NAVER_SEC = 600       # 10 min — naver updates every minute during market
STALE_FRANKFURTER_SEC = 5400  # 90 min — ECB daily rate, collector updates hourly


def is_fx_cache_stale(cache: Dict[str, Any]) -> bool:
    """Check if cached FX data is too stale to use."""
    updated_str = cache.get("updated_at")
    if not updated_str:
        return True
    try:
        updated = datetime.fromisoformat(updated_str)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        source = cache.get("source", "naver")
        threshold = STALE_NAVER_SEC if source == "naver" else STALE_FRANKFURTER_SEC
        return age > threshold
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# Main collector loop
# ---------------------------------------------------------------------------

def run_fx_collector(
    output_path: str | None = None,
    market_interval: int = MARKET_INTERVAL_SEC,
    off_hours_interval: int = OFF_HOURS_INTERVAL_SEC,
    off_hours_sleep: int = OFF_HOURS_SLEEP_SEC,
) -> None:
    """Run the FX collector loop (blocking, for daemon thread).

    During KRW market hours: fetches from Naver every `market_interval` seconds.
    Outside market hours: fetches from Frankfurter every `off_hours_interval` seconds,
    checking market status every `off_hours_sleep` seconds.
    """
    path = Path(
        output_path
        or os.getenv("MACRO_FX_PATH", DEFAULT_OUTPUT_PATH)
    )
    logger.info(
        "FX collector started → %s (market=%ds, off-hours=%ds)",
        path, market_interval, off_hours_interval,
    )

    last_off_hours_fetch = 0.0

    while True:
        try:
            if _is_market_hours():
                data = _fetch_naver_fx()
                if data is None:
                    # Naver failed, try Frankfurter as immediate fallback
                    data = _fetch_frankfurter()
                if data is not None:
                    _atomic_write_json(path, data)
                    logger.debug("FX updated: %s (source=%s)", data.get("value"), data.get("source"))
                time.sleep(market_interval)
            else:
                # Off-hours: update via Frankfurter at longer intervals
                now = time.monotonic()
                if now - last_off_hours_fetch >= off_hours_interval:
                    data = _fetch_frankfurter()
                    if data is not None:
                        _atomic_write_json(path, data)
                        logger.debug("FX off-hours updated: %s", data.get("value"))
                    last_off_hours_fetch = now
                time.sleep(off_hours_sleep)
        except Exception as exc:
            logger.error("FX collector error: %s", exc, exc_info=True)
            time.sleep(market_interval)
