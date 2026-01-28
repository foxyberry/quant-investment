"""
Buy Decision Logic
매수 결정 로직

Usage:
    from discovery.decision import analyze_buy_signal

    decision = analyze_buy_signal("005930.KS")
    print(f"Recommendation: {decision.recommendation}")
    print(f"Score: {decision.score}")
    print(f"Reasons: {decision.reasons}")
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from discovery.indicators import calculate_indicators, get_ma_distances
from utils.fetch import get_ohlcv


class Recommendation(Enum):
    """매수 추천 등급"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    WAIT = "WAIT"


class RiskLevel(Enum):
    """위험 수준"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class BuyDecision:
    """매수 결정 결과"""
    ticker: str
    recommendation: str
    score: int  # 0-100
    risk_level: str
    reasons: List[str]
    indicators: Dict[str, Any]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "recommendation": self.recommendation,
            "score": self.score,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "indicators": self.indicators,
            "details": self.details,
        }

    def summary(self) -> str:
        """결과 요약 문자열"""
        lines = [
            "=" * 50,
            f"BUY DECISION: {self.ticker}",
            "=" * 50,
            f"Recommendation: {self.recommendation}",
            f"Score: {self.score}/100",
            f"Risk Level: {self.risk_level}",
            "-" * 50,
            "Reasons:",
        ]
        for reason in self.reasons:
            lines.append(f"  - {reason}")
        lines.append("=" * 50)
        return "\n".join(lines)


# Scoring weights (configurable)
DEFAULT_WEIGHTS = {
    "rsi": 15,
    "macd": 15,
    "ma_position": 20,
    "ma_distance": 15,
    "volume": 10,
    "trend": 15,
    "bollinger": 10,
}


def analyze_buy_signal(
    ticker: str,
    weights: Optional[Dict[str, int]] = None,
    data: Optional[Any] = None
) -> BuyDecision:
    """
    매수 신호 종합 분석

    Args:
        ticker: 종목 코드
        weights: 점수 가중치 (기본값 사용 시 None)
        data: 가격 데이터 (없으면 자동 조회)

    Returns:
        BuyDecision 객체
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Get data and indicators
    if data is None:
        data = get_ohlcv(ticker, days=365)

    indicators = calculate_indicators(ticker, data=data)
    ma_distances = get_ma_distances(ticker, data=data)

    # Calculate individual scores
    scores = {}
    reasons = []

    # RSI Score (0-100)
    rsi_score, rsi_reason = _score_rsi(indicators.get("rsi"))
    scores["rsi"] = rsi_score
    if rsi_reason:
        reasons.append(rsi_reason)

    # MACD Score
    macd_score, macd_reason = _score_macd(
        indicators.get("macd"),
        indicators.get("macd_signal"),
        indicators.get("macd_histogram")
    )
    scores["macd"] = macd_score
    if macd_reason:
        reasons.append(macd_reason)

    # MA Position Score
    ma_score, ma_reason = _score_ma_position(ma_distances, indicators.get("current_price"))
    scores["ma_position"] = ma_score
    if ma_reason:
        reasons.append(ma_reason)

    # MA Distance Score (closer to support MA = higher score)
    distance_score, distance_reason = _score_ma_distance(ma_distances)
    scores["ma_distance"] = distance_score
    if distance_reason:
        reasons.append(distance_reason)

    # Volume Score
    volume_score, volume_reason = _score_volume(indicators.get("volume_ratio"))
    scores["volume"] = volume_score
    if volume_reason:
        reasons.append(volume_reason)

    # Trend Score
    trend_score, trend_reason = _score_trend(data)
    scores["trend"] = trend_score
    if trend_reason:
        reasons.append(trend_reason)

    # Bollinger Band Score
    bb_score, bb_reason = _score_bollinger(
        indicators.get("current_price"),
        indicators.get("bb_lower"),
        indicators.get("bb_upper"),
        indicators.get("bb_middle")
    )
    scores["bollinger"] = bb_score
    if bb_reason:
        reasons.append(bb_reason)

    # Calculate weighted total score
    total_weight = sum(weights.values())
    weighted_score = sum(
        scores.get(key, 50) * weight / total_weight
        for key, weight in weights.items()
    )
    final_score = int(weighted_score)

    # Determine recommendation
    if final_score >= 75:
        recommendation = Recommendation.STRONG_BUY.value
    elif final_score >= 60:
        recommendation = Recommendation.BUY.value
    elif final_score >= 40:
        recommendation = Recommendation.HOLD.value
    else:
        recommendation = Recommendation.WAIT.value

    # Determine risk level
    risk_level = _assess_risk(indicators, ma_distances)

    return BuyDecision(
        ticker=ticker,
        recommendation=recommendation,
        score=final_score,
        risk_level=risk_level.value,
        reasons=reasons,
        indicators=indicators,
        details={
            "scores": scores,
            "weights": weights,
            "ma_distances": {k: v for k, v in ma_distances.items()},
        }
    )


# ============================================================
# Scoring Functions
# ============================================================

def _score_rsi(rsi: Optional[float]) -> tuple:
    """RSI 점수화"""
    if rsi is None:
        return 50, None

    if rsi <= 30:
        return 90, f"RSI oversold ({rsi:.1f}) - Strong buy signal"
    elif rsi <= 40:
        return 70, f"RSI low ({rsi:.1f}) - Potential buying opportunity"
    elif rsi <= 60:
        return 50, None  # Neutral
    elif rsi <= 70:
        return 35, f"RSI elevated ({rsi:.1f}) - Caution advised"
    else:
        return 15, f"RSI overbought ({rsi:.1f}) - Consider waiting"


def _score_macd(macd: Optional[float], signal: Optional[float], histogram: Optional[float]) -> tuple:
    """MACD 점수화"""
    if macd is None or signal is None:
        return 50, None

    if histogram is None:
        histogram = macd - signal

    # Bullish: MACD above signal and histogram positive/increasing
    if macd > signal and histogram > 0:
        return 80, "MACD bullish crossover - Buy signal"
    elif macd > signal:
        return 65, "MACD above signal line"
    elif histogram > 0 or (histogram < 0 and macd > signal * 0.95):
        return 45, None  # Neutral
    else:
        return 25, "MACD bearish - Sell pressure"


def _score_ma_position(ma_distances: Dict, current_price: Optional[float]) -> tuple:
    """MA 위치 점수화"""
    if not ma_distances or current_price is None:
        return 50, None

    # Check position relative to key MAs
    above_count = sum(1 for d in ma_distances.values() if d.get("above", False))
    total = len(ma_distances)

    if total == 0:
        return 50, None

    ratio = above_count / total

    if ratio >= 0.8:
        return 75, f"Price above {above_count}/{total} MAs - Strong uptrend"
    elif ratio >= 0.5:
        return 60, f"Price above {above_count}/{total} MAs - Moderate trend"
    elif ratio >= 0.25:
        return 40, f"Price below most MAs - Weak trend"
    else:
        return 30, f"Price below {total - above_count}/{total} MAs - Potential support test"


def _score_ma_distance(ma_distances: Dict) -> tuple:
    """MA 거리 점수화 (지지선 근접 시 높은 점수)"""
    if not ma_distances:
        return 50, None

    # Find closest MA below price (support)
    supports = [(p, d) for p, d in ma_distances.items()
                if d.get("distance_pct", 0) > 0 and d.get("distance_pct", 100) < 10]

    if supports:
        closest_period, closest_data = min(supports, key=lambda x: x[1]["distance_pct"])
        distance = closest_data["distance_pct"]

        if distance <= 2:
            return 85, f"Near {closest_period}-day MA support ({distance:.1f}%)"
        elif distance <= 5:
            return 70, f"Approaching {closest_period}-day MA ({distance:.1f}%)"
        else:
            return 55, None

    # Check if price is below MAs (potential bounce)
    below = [(p, d) for p, d in ma_distances.items() if d.get("distance_pct", 0) < 0]
    if below:
        closest_period, closest_data = max(below, key=lambda x: x[1]["distance_pct"])
        distance = abs(closest_data["distance_pct"])

        if distance <= 5:
            return 75, f"Below {closest_period}-day MA - Potential bounce ({distance:.1f}%)"
        elif distance <= 10:
            return 60, f"Below {closest_period}-day MA ({distance:.1f}%)"

    return 50, None


def _score_volume(volume_ratio: Optional[float]) -> tuple:
    """거래량 점수화"""
    if volume_ratio is None:
        return 50, None

    if volume_ratio >= 2.0:
        return 80, f"High volume ({volume_ratio:.1f}x average) - Strong interest"
    elif volume_ratio >= 1.5:
        return 65, f"Above average volume ({volume_ratio:.1f}x)"
    elif volume_ratio >= 0.8:
        return 50, None  # Normal
    else:
        return 35, f"Low volume ({volume_ratio:.1f}x) - Weak conviction"


def _score_trend(data) -> tuple:
    """트렌드 점수화"""
    if data is None or len(data) < 20:
        return 50, None

    close = data['close']

    # 20-day trend
    recent_change = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100

    if recent_change >= 10:
        return 70, f"Strong uptrend ({recent_change:.1f}% in 20 days)"
    elif recent_change >= 5:
        return 60, f"Uptrend ({recent_change:.1f}% in 20 days)"
    elif recent_change >= -5:
        return 50, None  # Sideways
    elif recent_change >= -10:
        return 40, f"Downtrend ({recent_change:.1f}% in 20 days)"
    else:
        return 30, f"Strong downtrend ({recent_change:.1f}% in 20 days) - Caution"


def _score_bollinger(
    current_price: Optional[float],
    bb_lower: Optional[float],
    bb_upper: Optional[float],
    bb_middle: Optional[float]
) -> tuple:
    """볼린저 밴드 점수화"""
    if None in [current_price, bb_lower, bb_upper, bb_middle]:
        return 50, None

    bb_range = bb_upper - bb_lower
    if bb_range == 0:
        return 50, None

    # Position within bands (0 = lower, 1 = upper)
    position = (current_price - bb_lower) / bb_range

    if position <= 0.1:
        return 85, "Near lower Bollinger Band - Potential bounce"
    elif position <= 0.3:
        return 70, "Lower half of Bollinger Bands"
    elif position <= 0.7:
        return 50, None  # Middle
    elif position <= 0.9:
        return 35, "Upper half of Bollinger Bands"
    else:
        return 20, "Near upper Bollinger Band - Overbought"


def _assess_risk(indicators: Dict, ma_distances: Dict) -> RiskLevel:
    """위험 수준 평가"""
    risk_factors = 0

    # High RSI = higher risk
    rsi = indicators.get("rsi")
    if rsi and rsi > 70:
        risk_factors += 2
    elif rsi and rsi > 60:
        risk_factors += 1

    # Far from MA support = higher risk
    if ma_distances:
        min_distance = min(
            abs(d.get("distance_pct", 0)) for d in ma_distances.values()
            if d.get("distance_pct", 0) > 0
        ) if any(d.get("distance_pct", 0) > 0 for d in ma_distances.values()) else 100

        if min_distance > 20:
            risk_factors += 2
        elif min_distance > 10:
            risk_factors += 1

    # Low volume = uncertainty
    volume_ratio = indicators.get("volume_ratio")
    if volume_ratio and volume_ratio < 0.5:
        risk_factors += 1

    if risk_factors >= 3:
        return RiskLevel.HIGH
    elif risk_factors >= 1:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW
