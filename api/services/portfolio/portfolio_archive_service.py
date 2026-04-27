"""
Portfolio Archive Service.

Handles snapshotting of holdings into named archives and retrieving/deleting them.
"""

import logging
import math
from typing import Dict, List, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding, SellRule, PortfolioArchive, PortfolioArchiveItem
from api.schemas.portfolio import (
    ArchiveCreate,
    ArchiveItemResponse,
    ArchiveSummary,
    ArchiveDetailResponse,
)
from api.services.portfolio.portfolio_core_service import PortfolioCoreService  # noqa: E402

logger = logging.getLogger(__name__)


class PortfolioArchiveService(PortfolioCoreService):
    """
    Extends PortfolioCoreService with portfolio archive operations.

    Responsible for snapshotting, listing, retrieving, and deleting archives.
    """

    def create_archive(self, data: ArchiveCreate) -> ArchiveDetailResponse:
        """Snapshot current holdings into a new portfolio archive.

        Reads all rows from the holdings table and persists them as
        PortfolioArchiveItem records linked to a new PortfolioArchive row.
        Current prices are not fetched here; items are stored with
        avg_price only (current_price=None, pnl_pct=None).

        Args:
            data: Archive name and optional description.

        Returns:
            ArchiveDetailResponse with the newly created archive and its items.
        """
        db = SessionLocal()
        try:
            holdings: List[Holding] = db.query(Holding).all()

            archive = PortfolioArchive(
                name=data.name,
                description=data.description,
                total_holdings=len(holdings),
            )
            db.add(archive)
            db.flush()  # obtain archive.id before inserting items

            for h in holdings:
                item = PortfolioArchiveItem(
                    archive_id=archive.id,
                    ticker=h.ticker,
                    name=h.name,
                    quantity=h.quantity,
                    avg_price=h.avg_price,
                    currency=h.currency,
                    bought_at=h.bought_at,
                    sector=h.sector,
                    industry=h.industry,
                    country=h.country,
                    exchange=h.exchange,
                )
                db.add(item)

            if data.clear_after:
                db.query(SellRule).delete(synchronize_session=False)
                db.query(Holding).delete(synchronize_session=False)

            db.commit()
            db.refresh(archive)

            item_responses = [
                ArchiveItemResponse(
                    ticker=item.ticker,
                    name=item.name,
                    quantity=item.quantity,
                    avg_price=item.avg_price,
                    currency=item.currency,
                    bought_at=item.bought_at,
                    sector=item.sector,
                    current_price=None,
                    pnl_pct=None,
                )
                for item in archive.items
            ]

            return ArchiveDetailResponse(
                id=archive.id,
                name=archive.name,
                description=archive.description,
                archived_at=archive.archived_at,
                total_holdings=archive.total_holdings,
                items=item_responses,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def list_archives(self) -> List[ArchiveSummary]:
        """Return all archives ordered by most recent first.

        Returns:
            List of ArchiveSummary (no items included).
        """
        db = SessionLocal()
        try:
            archives: List[PortfolioArchive] = (
                db.query(PortfolioArchive)
                .order_by(PortfolioArchive.archived_at.desc())
                .all()
            )
            return [
                ArchiveSummary(
                    id=a.id,
                    name=a.name,
                    description=a.description,
                    archived_at=a.archived_at,
                    total_holdings=a.total_holdings,
                )
                for a in archives
            ]
        finally:
            db.close()

    def get_archive(
        self, archive_id: int, with_prices: bool = False
    ) -> Optional[ArchiveDetailResponse]:
        """Return a single archive with all its items.

        When with_prices is True, fetches the current price for each item
        and computes pnl_pct = ((current_price - avg_price) / avg_price) * 100.

        Args:
            archive_id: Primary key of the archive.
            with_prices: Whether to enrich items with live prices.

        Returns:
            ArchiveDetailResponse, or None if not found.
        """
        db = SessionLocal()
        try:
            archive: Optional[PortfolioArchive] = (
                db.query(PortfolioArchive)
                .filter(PortfolioArchive.id == archive_id)
                .first()
            )
            if archive is None:
                return None

            prices: Dict[str, float] = {}
            if with_prices:
                tickers = [item.ticker for item in archive.items]
                if tickers:
                    prices = self._get_current_prices(tickers)

            item_responses = []
            for item in archive.items:
                current_price: Optional[float] = prices.get(item.ticker) if with_prices else None
                pnl_pct: Optional[float] = None
                if (
                    with_prices
                    and current_price is not None
                    and item.avg_price
                    and not math.isnan(current_price)
                    and not math.isinf(current_price)
                ):
                    pnl_pct = ((current_price - item.avg_price) / item.avg_price) * 100

                item_responses.append(
                    ArchiveItemResponse(
                        ticker=item.ticker,
                        name=item.name,
                        quantity=item.quantity,
                        avg_price=item.avg_price,
                        currency=item.currency,
                        bought_at=item.bought_at,
                        sector=item.sector,
                        current_price=current_price,
                        pnl_pct=pnl_pct,
                    )
                )

            return ArchiveDetailResponse(
                id=archive.id,
                name=archive.name,
                description=archive.description,
                archived_at=archive.archived_at,
                total_holdings=archive.total_holdings,
                items=item_responses,
            )
        finally:
            db.close()

    def delete_archive(self, archive_id: int) -> bool:
        """Delete an archive and all its items (CASCADE).

        Args:
            archive_id: Primary key of the archive to delete.

        Returns:
            True if deleted, False if not found.
        """
        db = SessionLocal()
        try:
            archive: Optional[PortfolioArchive] = (
                db.query(PortfolioArchive)
                .filter(PortfolioArchive.id == archive_id)
                .first()
            )
            if archive is None:
                return False
            db.delete(archive)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
