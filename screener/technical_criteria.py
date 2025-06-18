from dataclasses import dataclass
from typing import List

@dataclass
class TechnicalCriteria:
    breakout_threshold: float = 1.05
    stop_loss_threshold: float = 0.95
    volume_threshold: float = 1.5
    lookback_days: int = 20
    
