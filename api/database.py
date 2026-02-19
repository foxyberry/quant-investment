"""
Database engine, session factory, and initialization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url)
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
    import api.models.strategy  # noqa: F401 — register model with Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    _migrate_json_data()


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
