"""
Exchange rate schemas for API responses.
"""

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field


class ExchangeRatesResponse(BaseModel):
    """
    Exchange rates response schema.

    Attributes:
        base: Base currency code.
        rates: Currency -> rate map where 1 base equals rate[currency].
        updated_at: Timestamp when rates were last updated.
    """

    base: str = Field(..., description="Base currency code", examples=["USD"])
    rates: Dict[str, float] = Field(..., description="Currency rate map")
    updated_at: datetime = Field(..., description="Rates update timestamp")
