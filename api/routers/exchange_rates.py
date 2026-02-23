"""
Exchange rate router.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from api.schemas.exchange_rate import ExchangeRatesResponse
from api.services.exchange_rate_service import get_exchange_rate_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/exchange-rates",
    tags=["Exchange Rates"],
)


@router.get(
    "",
    response_model=ExchangeRatesResponse,
    summary="Get Exchange Rates",
    description="Get latest exchange rates for a base currency (cached for 1 hour).",
)
async def get_exchange_rates(
    base: str = Query(default="USD", min_length=3, max_length=3, description="Base currency"),
) -> ExchangeRatesResponse:
    """
    Return exchange rates relative to the requested base currency.
    """
    service = get_exchange_rate_service()
    try:
        result = service.get_rates(base=base)
        return ExchangeRatesResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Failed to get exchange rates: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get exchange rates: {e}")
