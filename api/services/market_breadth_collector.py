"""Market breadth data collector.

Collects advance/decline counts for KOSPI from Naver Finance
and writes them to a JSON file for the macro monitor to consume.

Primary source: finance.naver.com/sise/sise_index.naver (HTML scraping).
"""

from __future__ import annotations

import json
import logging
import os
import re
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
# Source: Naver Finance sise_index page (HTML scraping)
# ---------------------------------------------------------------------------

_AD_PATTERN = re.compile(
    r'<span class="blind">(상한종목수|상승종목수|보합종목수|하락종목수|하한종목수)</span>'
    r'.*?<span>(\d[\d,]*)</span>',
    re.DOTALL,
)

_LABEL_MAP = {
    "상한종목수": "limit_up",
    "상승종목수": "advancing",
    "보합종목수": "unchanged",
    "하락종목수": "declining",
    "하한종목수": "limit_down",
}


def _fetch_breadth_naver(market: str = "KOSPI") -> dict | None:
    """Scrape advance/decline counts from Naver sise_index page."""
    try:
        import requests
    except ImportError:
        return None

    url = f"https://finance.naver.com/sise/sise_index.naver?code={market}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html",
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        html = r.text

        counts: dict[str, int] = {}
        for match in _AD_PATTERN.finditer(html):
            label_kr = match.group(1)
            value_str = match.group(2).replace(",", "")
            key = _LABEL_MAP.get(label_kr)
            if key:
                counts[key] = int(value_str)

        advancing = counts.get("advancing", 0) + counts.get("limit_up", 0)
        declining = counts.get("declining", 0) + counts.get("limit_down", 0)
        unchanged = counts.get("unchanged", 0)
        total = advancing + declining + unchanged

        if total == 0:
            logger.debug("Naver breadth returned zero total for %s", market)
            return None

        ad_ratio = round(advancing / declining, 3) if declining > 0 else None

        return {
            "market": market,
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "total": total,
            "ad_ratio": ad_ratio,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.debug("Naver breadth scrape failed for %s: %s", market, exc)
        return None


# ---------------------------------------------------------------------------
# Atomic file writer (same pattern as investor_flow_collector)
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

def run_market_breadth_collector(
    output_path: str | None = None,
    market: str = "KOSPI",
    interval_sec: int = 300,
    off_hours_sleep: int = 60,
) -> None:
    """Run the market breadth collector loop (blocking, for daemon thread).

    During market hours (Mon-Fri 09:00-15:40 KST), fetches every `interval_sec`.
    Outside market hours, sleeps `off_hours_sleep` seconds before rechecking.
    """
    path = Path(output_path or os.getenv("MACRO_BREADTH_PATH", "data/market/market_breadth_latest.json"))
    logger.info("Market breadth collector started → %s (market=%s, interval=%ds)", path, market, interval_sec)

    while True:
        try:
            if not _is_market_hours():
                time.sleep(off_hours_sleep)
                continue

            data = _fetch_breadth_naver(market)
            if data is not None:
                _atomic_write_json(path, data)
                logger.debug("Market breadth updated: advancing=%s declining=%s", data.get("advancing"), data.get("declining"))

            time.sleep(interval_sec)
        except Exception as exc:
            logger.error("Market breadth collector error: %s", exc, exc_info=True)
            time.sleep(interval_sec)
