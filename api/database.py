"""
Database engine, session factory, and initialization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
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
    import api.models.broker_credential  # noqa: F401 — register model with Base
    import api.models.execution_history  # noqa: F401 — register model with Base
    import api.models.macro_history  # noqa: F401 — register model with Base
    import api.models.portfolio  # noqa: F401 — register model with Base
    import api.models.screening_result  # noqa: F401 — register model with Base
    import api.models.strategy  # noqa: F401 — register model with Base
    import api.models.watchlist  # noqa: F401 — register model with Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    _migrate_trade_columns()
    _migrate_holding_metadata_columns()
    _migrate_buy_rule_template_id()
    _migrate_sell_rule_preset_id()

    _migrate_json_data()
    _migrate_portfolio_json()
    _migrate_saved_screening_to_execution_history()


def _get_column_names(conn, table_name: str):
    """Return a set of column names for *table_name*, or None if the table
    does not exist.  Works with both SQLite and PostgreSQL."""
    dialect = engine.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        if not rows:
            return None
        return {row[1] for row in rows}
    # PostgreSQL / other dialects
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = :tbl"
        ),
        {"tbl": table_name},
    ).fetchall()
    if not rows:
        return None
    return {row[0] for row in rows}


def _migrate_trade_columns() -> None:
    """Schema compatibility migration for legacy trades table."""
    try:
        with engine.begin() as conn:
            existing_columns = _get_column_names(conn, "trades")
            if existing_columns is None:
                return
            if "tax" not in existing_columns:
                conn.execute(text("ALTER TABLE trades ADD COLUMN tax FLOAT DEFAULT 0"))
                logger.info("Added missing trades.tax column for legacy DB compatibility")
    except Exception as e:
        logger.warning("Trade schema compatibility migration skipped: %s", e)


def _migrate_holding_metadata_columns() -> None:
    """Schema compatibility migration for legacy holdings metadata columns."""
    try:
        with engine.begin() as conn:
            existing_columns = _get_column_names(conn, "holdings")
            if existing_columns is None:
                return
            for col, col_type in [("sector", "VARCHAR(128)"), ("industry", "VARCHAR(128)"), ("country", "VARCHAR(64)"), ("exchange", "VARCHAR(32)")]:
                if col not in existing_columns:
                    conn.execute(text(f"ALTER TABLE holdings ADD COLUMN {col} {col_type}"))
                    logger.info("Added missing holdings.%s column for legacy DB compatibility", col)
    except Exception as e:
        logger.warning("Holding schema compatibility migration skipped: %s", e)


def _migrate_buy_rule_template_id() -> None:
    """Add template_id column to buy_rules for existing databases.

    Uses dialect-aware column introspection: PRAGMA for SQLite,
    information_schema for PostgreSQL.
    """
    try:
        with engine.begin() as conn:
            existing_columns = _get_column_names(conn, "buy_rules")
            if existing_columns is None:
                return  # table does not exist yet; create_all will handle it
            if "template_id" not in existing_columns:
                conn.execute(
                    text("ALTER TABLE buy_rules ADD COLUMN template_id INTEGER REFERENCES buy_rule_templates(id) ON DELETE SET NULL")
                )
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_buy_rules_template_id ON buy_rules (template_id)"))
                logger.info("Added buy_rules.template_id column")
            # Ensure unique constraint exists (safe for re-runs)
            conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS uq_buy_rules_item_template ON buy_rules (watchlist_item_id, template_id)")
            )
    except Exception as e:
        logger.warning("buy_rules template_id migration skipped: %s", e)


def _migrate_sell_rule_preset_id() -> None:
    """Add preset_id column to sell_rules for existing databases."""
    try:
        with engine.begin() as conn:
            existing_columns = _get_column_names(conn, "sell_rules")
            if existing_columns is None:
                return  # table does not exist yet; create_all will handle it
            if "preset_id" not in existing_columns:
                conn.execute(
                    text(
                        "ALTER TABLE sell_rules ADD COLUMN preset_id INTEGER "
                        "REFERENCES sell_rule_presets(id) ON DELETE SET NULL"
                    )
                )
                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_sell_rules_preset_id ON sell_rules (preset_id)")
                )
                logger.info("Added sell_rules.preset_id column")
    except Exception as e:
        logger.warning("sell_rules preset_id migration skipped: %s", e)


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
