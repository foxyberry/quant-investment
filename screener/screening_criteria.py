from dataclasses import dataclass
from typing import List

@dataclass
class ScreeningCriteria:
    min_price: float = 5.0
    max_price: float = 500.0
    min_volume: int = 200_000
    min_market_cap: float = 1e9
    sectors: List[str] = None  # Optional sector filter (e.g., ["Technology", "Healthcare"])

    def __post_init__(self):
        if self.sectors is None:
            self.sectors = []
