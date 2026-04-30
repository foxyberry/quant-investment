"""History, persistence, and backfill helpers for MacroMarketService."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.macro_history import MacroHistory

logger = logging.getLogger(__name__)


def get_history(service, window: str = "60m") -> Dict[str, Any]:
    now_mono = time.monotonic()
    normalized = (window or "60m").strip().lower()

    with service._lock:
        cached = getattr(service, "_history_cache", {}).get(normalized)
        if cached:
            cached_at, cached_result = cached
            ttl = service._HISTORY_CACHE_TTL.get(normalized, 60)
            if (now_mono - cached_at) < ttl:
                return {"window": cached_result["window"], "points": list(cached_result["points"])}

    now = datetime.now(timezone.utc)
    delta = parse_window(service, window)
    min_ts = now - delta

    with service._lock:
        deque_min_ts = None
        if service._history:
            deque_min_ts = service._safe_datetime(service._history[0].get("timestamp"))

    if deque_min_ts is None or deque_min_ts > min_ts:
        flush_to_db(service)
        db_points = query_db_history(service, min_ts, now)
        if db_points:
            result = {"window": window, "points": downsample_points(service, db_points, window)}
            cache_history(service, normalized, now_mono, result)
            return result

    points = []
    with service._lock:
        for point in reversed(service._history):
            dt = service._safe_datetime(point.get("timestamp"))
            if not dt:
                continue
            if dt < min_ts:
                break
            points.append({
                "timestamp": point["timestamp"],
                "fx_value": point.get("fx_value"),
                "futures_value": point.get("futures_value"),
                "foreign_net": point.get("foreign_net"),
                "macro_score": point.get("macro_score"),
                "regime": point.get("regime", "unknown"),
                "vix": point.get("vix"),
            })
    points.reverse()

    result = {"window": window, "points": downsample_points(service, points, window)}
    cache_history(service, normalized, now_mono, result)
    return result


def cache_history(service, window: str, mono_time: float, result: Dict[str, Any]) -> None:
    with service._lock:
        if not hasattr(service, "_history_cache"):
            service._history_cache = {}
        service._history_cache[window] = (mono_time, result)


def downsample_points(service, points: List[Dict[str, Any]], window: str) -> List[Dict[str, Any]]:
    normalized = (window or "60m").strip().lower()
    bucket_sec = service._DOWNSAMPLE_BUCKETS.get(normalized, 0)
    target = service._DOWNSAMPLE_TARGETS.get(normalized, 0)
    if bucket_sec <= 0 or (target > 0 and len(points) <= target) or (target <= 0 and len(points) <= 500):
        return points

    buckets: Dict[int, Dict[str, Any]] = {}
    for point in points:
        ts_str = point.get("timestamp")
        if not ts_str:
            continue
        dt = service._safe_datetime(ts_str)
        if not dt:
            continue
        epoch = int(dt.timestamp())
        bucket_key = (epoch // bucket_sec) * bucket_sec
        buckets[bucket_key] = point

    downsampled = [buckets[key] for key in sorted(buckets)]
    return downsampled if downsampled else points


def run_history_collector(service, interval_sec: int = 60) -> None:
    logger.info("Macro history collector started (interval=%ds)", interval_sec)
    while True:
        try:
            service.get_bundle(force_refresh=True)
            flush_to_db(service)
        except Exception as exc:
            logger.warning("History collector tick failed: %s", exc)
        time.sleep(interval_sec)


def append_history(service, bundle: Dict[str, Any], now: datetime) -> None:
    signal = bundle.get("signal", {})
    fx = bundle.get("fx", {})
    futures = bundle.get("futures", {})
    flow = bundle.get("flow", {})

    vix_value: float | None = None
    try:
        from api.services.volatility_service import get_volatility_service

        vol = get_volatility_service().get_snapshot()
        if vol:
            vix_value = service._to_float(vol.get("vix"))
    except Exception as exc:
        logger.debug("VIX fetch for history point failed: %s", exc)

    point = {
        "timestamp": service._to_iso(now),
        "fx_value": service._to_float(fx.get("value")),
        "futures_value": service._to_float(futures.get("value")),
        "foreign_net": service._to_float(flow.get("foreign_net")),
        "macro_score": service._to_float(signal.get("macro_score")),
        "regime": signal.get("regime", "unknown"),
        "vix": vix_value,
    }
    should_flush = False
    with service._lock:
        service._history.append(point)
        service._db_buffer.append(point)
        service._db_tick_count += 1
        if hasattr(service, "_history_cache"):
            service._history_cache.clear()
        if service._db_tick_count >= service._DB_FLUSH_INTERVAL:
            should_flush = True

    if should_flush:
        flush_to_db(service)


def load_history_from_db(service) -> None:
    try:
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(MacroHistory)
                .order_by(desc(MacroHistory.timestamp))
                .limit(service._history.maxlen or 50_000)
                .all()
            )
            rows.reverse()
            for row in rows:
                ts = row.timestamp
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                service._history.append({
                    "timestamp": ts.isoformat() if ts else None,
                    "fx_value": row.fx_value,
                    "futures_value": row.futures_value,
                    "foreign_net": row.foreign_net,
                    "macro_score": row.macro_score,
                    "regime": row.regime or "unknown",
                    "vix": getattr(row, "vix", None),
                })
            if rows:
                logger.info("Loaded %d macro history rows from DB", len(rows))
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to load macro history from DB: %s", exc)


def backfill_history(service) -> None:
    try:
        db: Session = SessionLocal()
        try:
            latest = db.query(MacroHistory).order_by(desc(MacroHistory.timestamp)).first()
        finally:
            db.close()

        now = datetime.now(timezone.utc)
        if latest and latest.timestamp:
            last_ts = latest.timestamp
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            gap = now - last_ts
        else:
            gap = timedelta(days=service._BACKFILL_MAX_DAYS)
            last_ts = now - gap

        if gap < timedelta(hours=12):
            logger.info("Macro history gap < 12h, skipping backfill")
            return

        days_to_fill = min(int(gap.total_seconds() / 86400) + 1, service._BACKFILL_MAX_DAYS)
        start_date = (now - timedelta(days=days_to_fill)).date()
        end_date = (now - timedelta(days=1)).date()
        if start_date >= end_date:
            return

        logger.info(
            "Backfilling macro history from %s to %s (%d days gap)",
            start_date, end_date, days_to_fill,
        )

        fx_daily = fetch_fx_historical(service, start_date, end_date)
        futures_daily = fetch_futures_historical(service, days_to_fill + 5)
        backfill_points = merge_daily_backfill(service, fx_daily, futures_daily, last_ts)
        if not backfill_points:
            logger.info("No backfill points to insert")
            return

        db = SessionLocal()
        try:
            for point in backfill_points:
                ts = service._safe_datetime(point.get("timestamp"))
                if ts is None:
                    continue
                db.add(MacroHistory(
                    timestamp=ts,
                    fx_value=point.get("fx_value"),
                    futures_value=point.get("futures_value"),
                    foreign_net=None,
                    macro_score=point.get("macro_score"),
                    regime=point.get("regime"),
                ))
            db.commit()
            logger.info("Backfilled %d macro history points", len(backfill_points))
        finally:
            db.close()

        with service._lock:
            service._history.clear()
        load_history_from_db(service)
    except Exception as exc:
        logger.warning("Macro history backfill failed: %s", exc)


def fetch_fx_historical(_service, start_date: date, end_date: date) -> Dict[date, float]:
    try:
        import requests

        url = f"https://api.frankfurter.app/{start_date}..{end_date}?from=USD&to=KRW"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        result: Dict[date, float] = {}
        for date_str, rate_dict in data.get("rates", {}).items():
            parsed_date = date.fromisoformat(date_str)
            krw = rate_dict.get("KRW")
            if krw is not None:
                result[parsed_date] = float(krw)
        logger.info("Fetched %d daily FX rates for backfill", len(result))
        return result
    except Exception as exc:
        logger.warning("Failed to fetch historical FX rates: %s", exc)
        return {}


def fetch_futures_historical(service, days: int) -> Dict[date, float]:
    try:
        ohlcv = service.market_service.get_ohlcv(service.futures_ticker, days=days)
        if not ohlcv or not ohlcv.get("data"):
            return {}
        result: Dict[date, float] = {}
        for item in ohlcv["data"]:
            result[date.fromisoformat(item["time"])] = float(item["close"])
        logger.info("Fetched %d daily futures prices for backfill", len(result))
        return result
    except Exception as exc:
        logger.warning("Failed to fetch historical futures data: %s", exc)
        return {}


def merge_daily_backfill(
    service,
    fx_daily: Dict[date, float],
    futures_daily: Dict[date, float],
    last_ts: datetime,
) -> List[Dict[str, Any]]:
    all_dates = sorted(set(fx_daily.keys()) | set(futures_daily.keys()))
    if not all_dates:
        return []

    points: List[Dict[str, Any]] = []
    prev_fx = None
    prev_fut = None

    for current_date in all_dates:
        if current_date.weekday() > 4:
            continue

        fx_val = fx_daily.get(current_date)
        fut_val = futures_daily.get(current_date)

        fx_change = None
        if fx_val is not None and prev_fx is not None and prev_fx > 0:
            fx_change = ((fx_val - prev_fx) / prev_fx) * 100
        fut_change = None
        if fut_val is not None and prev_fut is not None and prev_fut > 0:
            fut_change = ((fut_val - prev_fut) / prev_fut) * 100

        fx_raw = service._clip((fx_change or 0) / 1.5, -1.0, 1.0)
        fut_raw = service._clip(-(fut_change or 0) / 3.0, -1.0, 1.0)

        numerator = 0.0
        denominator = 0.0
        if fx_val is not None:
            numerator += 0.55 * fx_raw
            denominator += 0.55
        if fut_val is not None:
            numerator += 0.45 * fut_raw
            denominator += 0.45

        macro_score = round(numerator / denominator, 4) if denominator > 0 else None
        regime = "unknown"
        if macro_score is not None:
            if macro_score >= 0.6:
                regime = "risk_off"
            elif macro_score <= -0.6:
                regime = "risk_on"
            else:
                regime = "neutral"

        n_hours = len(service._BACKFILL_HOURS_UTC)
        for hour_index, hour in enumerate(service._BACKFILL_HOURS_UTC):
            dt = datetime(current_date.year, current_date.month, current_date.day, hour, 0, tzinfo=timezone.utc)
            if dt <= last_ts:
                continue

            frac = hour_index / max(n_hours - 1, 1)
            h_fx = None
            if fx_val is not None:
                start_fx = prev_fx if prev_fx is not None else fx_val
                h_fx = round(start_fx + frac * (fx_val - start_fx), 2)
            h_fut = None
            if fut_val is not None:
                start_fut = prev_fut if prev_fut is not None else fut_val
                h_fut = round(start_fut + frac * (fut_val - start_fut), 2)

            points.append({
                "timestamp": dt.isoformat(),
                "fx_value": h_fx,
                "futures_value": h_fut,
                "foreign_net": None,
                "macro_score": macro_score,
                "regime": regime,
            })

        prev_fx = fx_val if fx_val is not None else prev_fx
        prev_fut = fut_val if fut_val is not None else prev_fut

    return points


def flush_to_db(service) -> None:
    with service._lock:
        if not service._db_buffer:
            return
        batch = service._db_buffer[:]
        service._db_buffer.clear()
        service._db_tick_count = 0
        if hasattr(service, "_history_cache"):
            service._history_cache.clear()

    try:
        db: Session = SessionLocal()
        try:
            for point in batch:
                ts = service._safe_datetime(point.get("timestamp"))
                if ts is None:
                    continue
                db.add(MacroHistory(
                    timestamp=ts,
                    fx_value=point.get("fx_value"),
                    futures_value=point.get("futures_value"),
                    foreign_net=point.get("foreign_net"),
                    macro_score=point.get("macro_score"),
                    regime=point.get("regime"),
                    vix=point.get("vix"),
                ))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to flush macro history to DB: %s", exc)
        with service._lock:
            service._db_buffer = batch + service._db_buffer


def query_db_history(service, min_ts: datetime, max_ts: datetime) -> List[Dict[str, Any]]:
    try:
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(MacroHistory)
                .filter(MacroHistory.timestamp >= min_ts, MacroHistory.timestamp <= max_ts)
                .order_by(MacroHistory.timestamp)
                .limit(service._DB_QUERY_LIMIT)
                .all()
            )
            return [
                {
                    "timestamp": (
                        row.timestamp.replace(tzinfo=timezone.utc)
                        if row.timestamp and row.timestamp.tzinfo is None
                        else row.timestamp
                    ).isoformat() if row.timestamp else None,
                    "fx_value": row.fx_value,
                    "futures_value": row.futures_value,
                    "foreign_net": row.foreign_net,
                    "macro_score": row.macro_score,
                    "regime": row.regime or "unknown",
                    "vix": getattr(row, "vix", None),
                }
                for row in rows
            ]
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to query macro history from DB: %s", exc)
        return []


def parse_window(service, window: str) -> timedelta:
    value = (window or "60m").strip().lower()
    try:
        if value.endswith("m"):
            delta = timedelta(minutes=max(int(value[:-1] or "60"), 1))
        elif value.endswith("h"):
            delta = timedelta(hours=max(int(value[:-1] or "1"), 1))
        elif value.endswith("d"):
            delta = timedelta(days=max(int(value[:-1] or "1"), 1))
        else:
            delta = timedelta(minutes=60)
        return min(delta, service._MAX_WINDOW)
    except ValueError:
        logger.warning("Invalid macro history window: %s. Falling back to 60m.", value)
    return timedelta(minutes=60)
