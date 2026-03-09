"""Investor flow data collector.

Collects market-level foreign/institution/individual net trading values
for KOSPI and writes them to a JSON file for the macro monitor to consume.

Primary source: Naver Finance polling API (realtime during market hours).
Fallback: pykrx (KRX scraper).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _now_kst() -> datetime:
    """Return current time as a timezone-aware datetime in KST."""
    import datetime as _dt

    return datetime.now(timezone.utc).astimezone(_dt.timezone(_dt.timedelta(hours=9)))


def _is_market_hours() -> bool:
    """Check if current KST time is within market hours (Mon-Fri, 09:00-15:40)."""
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
# Source 1: Naver Finance polling API (preferred)
# ---------------------------------------------------------------------------

def _fetch_naver(market: str = "KOSPI") -> dict | None:
    """Fetch investor flow from Naver Finance realtime polling API.

    Returns dict with foreign_net, institution_net, individual_net (unit: KRW)
    or None on failure.
    """
    try:
        import requests
    except ImportError:
        return None

    url = "https://polling.finance.naver.com/api/realtime/domestic/stock/marketInvestor"
    params = {"queryType": "market", "marketType": market}
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        body = r.json()
        datas = body.get("datas") or []
        if not datas:
            logger.debug("Naver polling returned empty datas for %s", market)
            return None

        # datas is a list of investor entries; structure:
        # {"investorName": "외국인", "tradBuyVal": ..., "tradSellVal": ..., "netBuyVal": ...}
        flow: dict[str, float | None] = {"foreign_net": None, "institution_net": None, "individual_net": None}
        for entry in datas:
            name = entry.get("investorName", "")
            # netBuyVal is in 백만원 (million KRW) — convert to raw KRW
            net_raw = entry.get("netBuyVal")
            if net_raw is None:
                continue
            try:
                net_val = float(net_raw) * 1_000_000  # 백만원 → 원
            except (TypeError, ValueError):
                continue

            if "외국인" in name:
                flow["foreign_net"] = net_val
            elif "기관" in name:
                flow["institution_net"] = net_val
            elif "개인" in name:
                flow["individual_net"] = net_val

        if flow["foreign_net"] is None and flow["institution_net"] is None:
            return None

        return {
            "market": market,
            "foreign_net": flow["foreign_net"],
            "institution_net": flow["institution_net"],
            "individual_net": flow["individual_net"],
            "window_min": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.debug("Naver polling failed for %s: %s", market, exc)
        return None


# ---------------------------------------------------------------------------
# Source 2: pykrx fallback
# ---------------------------------------------------------------------------

def _fetch_pykrx(market: str = "KOSPI") -> dict | None:
    """Fetch today's investor flow data from pykrx (KRX scraper)."""
    try:
        from pykrx.stock import get_market_trading_value_by_date
    except ImportError:
        return None

    now = _now_kst()
    today_str = now.strftime("%Y%m%d")

    try:
        df = get_market_trading_value_by_date(today_str, today_str, market)
        if df is None or df.empty:
            return None

        row = df.iloc[-1]

        def _get_val(candidates: list[str]) -> float | None:
            for c in candidates:
                if c in row.index:
                    try:
                        return float(row[c])
                    except (TypeError, ValueError):
                        pass
            return None

        foreign = _get_val(["외국인합계", "외국인합계(등록+비등록)", "외국인"])
        institution = _get_val(["기관합계", "기관"])
        individual = _get_val(["개인", "개인합계"])

        if foreign is None and institution is None:
            return None

        return {
            "market": market,
            "foreign_net": foreign,
            "institution_net": institution,
            "individual_net": individual,
            "window_min": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("pykrx fetch failed for %s: %s", market, exc)
        return None


# ---------------------------------------------------------------------------
# Combined fetch with fallback
# ---------------------------------------------------------------------------

def _fetch_investor_flow(market: str = "KOSPI") -> dict | None:
    """Try Naver first, then pykrx as fallback."""
    result = _fetch_naver(market)
    if result is not None:
        return result
    return _fetch_pykrx(market)


# ---------------------------------------------------------------------------
# Atomic file writer
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main collector loop
# ---------------------------------------------------------------------------

def run_investor_flow_collector(
    output_path: str | None = None,
    market: str = "KOSPI",
    interval_sec: int = 300,
    off_hours_sleep: int = 60,
) -> None:
    """Run the investor flow collector loop (blocking, for daemon thread).

    During market hours (Mon-Fri 09:00-15:40 KST), fetches every `interval_sec`.
    Outside market hours, sleeps `off_hours_sleep` seconds before rechecking.
    """
    path = Path(output_path or os.getenv("MACRO_INVESTOR_FLOW_PATH", "data/market/investor_flow_latest.json"))
    logger.info("Investor flow collector started → %s (market=%s, interval=%ds)", path, market, interval_sec)

    while True:
        try:
            if not _is_market_hours():
                time.sleep(off_hours_sleep)
                continue

            data = _fetch_investor_flow(market)
            if data is not None:
                _atomic_write_json(path, data)
                logger.debug("Investor flow updated: foreign=%s", data.get("foreign_net"))

            time.sleep(interval_sec)
        except Exception as exc:
            logger.error("Investor flow collector error: %s", exc, exc_info=True)
            time.sleep(interval_sec)
