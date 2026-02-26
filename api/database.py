"""
Database engine, session factory, and initialization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = get_settings().database_url
    parsed = make_url(url)
    kwargs = {}
    if parsed.drivername.startswith("sqlite"):
        # SQLite requires this for multi-threaded access (FastAPI)
        kwargs["connect_args"] = {"check_same_thread": False}
        # Ensure the data directory exists
        if parsed.database and parsed.database != ":memory:":
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Create a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and migrate legacy JSON data if present."""
    import api.models.agent_task  # noqa: F401 — register model with Base
    import api.models.execution_history  # noqa: F401 — register model with Base
    import api.models.portfolio  # noqa: F401 — register model with Base
    import api.models.screening_result  # noqa: F401 — register model with Base
    import api.models.strategy  # noqa: F401 — register model with Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    _migrate_json_data()
    _migrate_portfolio_json()
    _migrate_saved_screening_to_execution_history()


def _migrate_json_data() -> None:
    """One-time migration: import data/strategies.json into the DB."""
    json_path = Path(__file__).parent.parent / "data" / "strategies.json"
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("Could not read strategies JSON for migration: %s", e)
        return

    strategies = data.get("strategies", [])
    if not strategies:
        return

    from api.models.strategy import Strategy

    db = SessionLocal()
    migrated = 0
    skipped = 0
    try:
        existing_ids = {
            row[0] for row in db.query(Strategy.id).all()
        }

        for s in strategies:
            sid = s.get("id")
            if not sid or not s.get("name") or not s.get("graph"):
                logger.warning("Skipping malformed strategy record: %s", s.get("id", "<no id>"))
                skipped += 1
                continue

            if sid in existing_ids:
                skipped += 1
                continue

            row = Strategy(
                id=sid,
                name=s["name"],
                description=s.get("description"),
                graph=s["graph"],
            )
            if s.get("created_at"):
                try:
                    row.created_at = datetime.fromisoformat(s["created_at"])
                except (ValueError, TypeError):
                    pass
            if s.get("updated_at"):
                try:
                    row.updated_at = datetime.fromisoformat(s["updated_at"])
                except (ValueError, TypeError):
                    pass
            db.add(row)
            existing_ids.add(sid)
            migrated += 1

        if migrated > 0:
            db.commit()
        logger.info(
            "JSON migration: %d migrated, %d skipped", migrated, skipped
        )
    except Exception as e:
        db.rollback()
        logger.error("JSON migration failed: %s", e)
        return
    finally:
        db.close()

    if migrated > 0:
        migrated_path = json_path.with_suffix(".json.migrated")
        try:
            json_path.rename(migrated_path)
            logger.info("Renamed %s → %s", json_path, migrated_path)
        except OSError as e:
            logger.warning("Could not rename migrated file: %s", e)


def _migrate_portfolio_json() -> None:
    """One-time migration: import data/portfolio.json into the DB."""
    json_path = Path(__file__).parent.parent / "data" / "portfolio.json"
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("Could not read portfolio JSON for migration: %s", e)
        return

    holdings = data.get("holdings", [])
    if not holdings:
        return

    from api.models.portfolio import Holding

    db = SessionLocal()
    migrated = 0
    skipped = 0
    try:
        existing_tickers = {
            row[0] for row in db.query(Holding.ticker).all()
        }

        for h in holdings:
            ticker = h.get("ticker")
            if not ticker:
                logger.warning("Skipping portfolio record with no ticker")
                skipped += 1
                continue

            if ticker in existing_tickers:
                skipped += 1
                continue

            row = Holding(
                ticker=ticker,
                name=h.get("name"),
                quantity=h.get("quantity", 0),
                avg_price=h.get("avg_price", 0),
                currency=h.get("currency", "KRW"),
                note=h.get("note"),
            )
            bought_at = h.get("bought_at")
            if bought_at:
                try:
                    from datetime import date as date_type
                    row.bought_at = date_type.fromisoformat(bought_at)
                except (ValueError, TypeError):
                    pass
            db.add(row)
            existing_tickers.add(ticker)
            migrated += 1

        if migrated > 0:
            db.commit()
        logger.info(
            "Portfolio JSON migration: %d migrated, %d skipped", migrated, skipped
        )
    except Exception as e:
        db.rollback()
        logger.error("Portfolio JSON migration failed: %s", e)
        return
    finally:
        db.close()

    if migrated > 0:
        migrated_path = json_path.with_suffix(".json.migrated")
        try:
            json_path.rename(migrated_path)
            logger.info("Renamed %s → %s", json_path, migrated_path)
        except OSError as e:
            logger.warning("Could not rename migrated file: %s", e)


def _migrate_saved_screening_to_execution_history() -> None:
    """One-time migration: copy saved_screening_results rows into execution_history."""
    from api.models.execution_history import ExecutionHistory
    from api.models.screening_result import SavedScreeningResult
    from api.schemas.execution_history import compute_fingerprint

    db = SessionLocal()
    migrated = 0
    skipped = 0
    try:
        saved_count = db.query(SavedScreeningResult).count()
        if saved_count == 0:
            return

        existing_fps = {
            row[0]
            for row in db.query(ExecutionHistory.fingerprint).all()
        }

        rows = db.query(SavedScreeningResult).all()
        for row in rows:
            fp = compute_fingerprint(
                execution_type="screening",
                preset=row.preset,
                universes=row.universes or [],
                reference_date=row.reference_date,
                params=None,
            )
            if fp in existing_fps:
                skipped += 1
                continue

            eh = ExecutionHistory(
                id=row.id,
                execution_type="screening",
                preset=row.preset,
                universes=row.universes or [],
                reference_date=row.reference_date,
                params=None,
                graph=None,
                total_count=row.total_count,
                matched_count=row.matched_count,
                elapsed_ms=row.elapsed_ms,
                results=row.results or [],
                name=row.name,
                description=row.description,
                strategy_id=None,
                fingerprint=fp,
                created_at=row.created_at,
            )
            db.add(eh)
            existing_fps.add(fp)
            migrated += 1

        if migrated > 0:
            db.commit()
        logger.info(
            "Saved screening → execution_history migration: %d migrated, %d skipped",
            migrated, skipped,
        )
    except Exception as e:
        db.rollback()
        logger.error("Saved screening migration failed: %s", e)
    finally:
        db.close()
