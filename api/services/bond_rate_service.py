"""Bond rate aggregation service for macro bundle enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from api.services.ecos_service import EcosService, get_ecos_service
from api.services.fred_service import FredService, get_fred_service


class BondRateService:
    """Aggregates US/KR bond indicators from FRED and ECOS."""

    def __init__(self, fred: FredService, ecos: EcosService):
        self.fred = fred
        self.ecos = ecos

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a bond-rate snapshot."""
        us_10y, obs_date = self.fred.get_series_with_date("DGS10")
        us_2y = self.fred.get_series("DGS2")
        us_spread_2_10 = self.fred.get_series("T10Y2Y")

        # Calculate spread from individual yields when T10Y2Y is unavailable
        if us_spread_2_10 is None and us_10y is not None and us_2y is not None:
            us_spread_2_10 = round(us_10y - us_2y, 4)

        kr_10y_obs_date: Optional[str] = None
        kr_10y = self.ecos.get_stat_value("817Y002", "010210000")
        kr_3y = self.ecos.get_stat_value("817Y002", "010200000")
        if kr_10y is None:
            # FRED (OECD) monthly series as a fallback when ECOS is unavailable.
            kr_10y, kr_10y_obs_date = self.fred.get_series_with_date("IRLTLT01KRM156N")

        kr_us_spread = None
        if kr_10y is not None and us_10y is not None:
            kr_us_spread = round(kr_10y - us_10y, 4)

        inverted = None
        if us_spread_2_10 is not None:
            inverted = us_spread_2_10 < 0

        # Use FRED observation date as source_updated_at if available
        source_updated_at = obs_date or kr_10y_obs_date
        if obs_date and kr_10y_obs_date:
            try:
                us_dt = datetime.fromisoformat(obs_date)
                kr_dt = datetime.fromisoformat(kr_10y_obs_date)
                source_updated_at = max(us_dt, kr_dt).date().isoformat()
            except ValueError:
                source_updated_at = obs_date
        if source_updated_at is None:
            source_updated_at = datetime.now(timezone.utc).isoformat()

        # Stale if all values are None (API keys missing or both sources down)
        all_none = all(v is None for v in (us_10y, us_2y, kr_10y, kr_3y))
        stale = all_none

        return {
            "us_10y": us_10y,
            "us_2y": us_2y,
            "us_spread_2_10": us_spread_2_10,
            "inverted": inverted,
            "kr_10y": kr_10y,
            "kr_3y": kr_3y,
            "kr_us_spread_10y": kr_us_spread,
            "source_updated_at": source_updated_at,
            "stale": stale,
        }


_bond_rate_service: Optional[BondRateService] = None


def get_bond_rate_service() -> BondRateService:
    """Return singleton BondRateService instance."""
    global _bond_rate_service
    if _bond_rate_service is None:
        _bond_rate_service = BondRateService(
            fred=get_fred_service(),
            ecos=get_ecos_service(),
        )
    return _bond_rate_service
