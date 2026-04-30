"""Tool registry and execution helpers shared by chat/report services."""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_holdings",
        "description": (
            "현재 포트폴리오의 보유 종목 전체를 조회합니다. "
            "각 종목의 평균 단가, 현재가, 손익률 등을 반환합니다."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_price_history",
        "description": (
            "특정 종목의 OHLCV (시가/고가/저가/종가/거래량) 일별 데이터를 조회합니다. "
            "최근 N일치 데이터를 반환합니다 (최대 60행)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "days": {"type": "integer", "description": "조회 기간 (일수, 기본 60)", "default": 60},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_indicators",
        "description": (
            "특정 종목의 기술적 지표를 계산하여 반환합니다. "
            "RSI, MACD, 볼린저 밴드, 이동평균선, OBV 트렌드, 스토캐스틱 등을 포함합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "days": {"type": "integer", "description": "계산에 사용할 데이터 기간 (일수, 기본 120)", "default": 120},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "특정 종목의 최근 뉴스를 조회합니다. "
            "제목, 요약, 날짜, 출처를 반환합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: AAPL, 005930.KS)"},
                "limit": {"type": "integer", "description": "최대 뉴스 건수 (기본 5)", "default": 5},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_macro_context",
        "description": (
            "현재 거시경제 환경 데이터를 조회합니다. "
            "VIX, 매크로 점수, 시장 레짐, 환율(USD/KRW), 주요 지수 방향을 반환합니다."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def safe_last_series(series: Any) -> Optional[float]:
    try:
        if series is None or series.empty:
            return None
        val = series.iloc[-1]
        if pd.isna(val):
            return None
        f = float(val)
        return None if math.isnan(f) else f
    except Exception:
        return None


def run_get_holdings() -> Dict[str, Any]:
    from api.services.portfolio_service import get_portfolio_service

    service = get_portfolio_service()
    holdings = service.get_all_holdings(with_prices=True)
    rows = [
        {
            "ticker": h.ticker,
            "name": h.name,
            "quantity": h.quantity,
            "avg_price": h.avg_price,
            "current_price": h.current_price,
            "pnl_pct": h.pnl_pct,
            "currency": h.currency,
            "sector": h.sector,
        }
        for h in holdings
    ]
    return {"holdings": rows, "count": len(rows)}


def run_get_price_history(ticker: str, days: int = 60) -> Dict[str, Any]:
    from utils.data_cache import OHLCVCache

    cache = OHLCVCache()
    data = cache.get(ticker, days=days)
    if data is None or data.empty:
        return {"ticker": ticker, "rows": [], "note": "데이터 없음"}

    tail = data.tail(60)
    rows = []
    for idx, row in tail.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        rows.append(
            {
                "date": date_str,
                "open": safe_float(row.get("open")),
                "high": safe_float(row.get("high")),
                "low": safe_float(row.get("low")),
                "close": safe_float(row.get("close")),
                "volume": safe_float(row.get("volume")),
            }
        )
    return {"ticker": ticker, "rows": rows, "count": len(rows)}


def run_get_indicators(ticker: str, days: int = 120) -> Dict[str, Any]:
    from screener.indicators import calculate_indicators, calculate_stochastic, get_ma_distances
    from utils.data_cache import OHLCVCache

    cache = OHLCVCache()
    data = cache.get(ticker, days=days)
    if data is None or data.empty:
        return {"ticker": ticker, "error": "데이터 없음"}

    try:
        base = calculate_indicators(ticker, period=days, data=data)
    except Exception as exc:
        logger.warning("calculate_indicators failed for %s: %s", ticker, exc)
        base = {}

    stoch_k = stoch_d = None
    try:
        k_series, d_series = calculate_stochastic(data["high"], data["low"], data["close"])
        stoch_k = safe_last_series(k_series)
        stoch_d = safe_last_series(d_series)
    except Exception as exc:
        logger.warning("calculate_stochastic failed for %s: %s", ticker, exc)

    ma_distances: Dict[str, Any] = {}
    try:
        ma_distances = get_ma_distances(ticker, periods=[20, 60, 120, 240], data=data)
    except Exception as exc:
        logger.warning("get_ma_distances failed for %s: %s", ticker, exc)

    obv_trend = None
    try:
        close = data["close"]
        volume = data["volume"]
        obv = (volume * close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))).cumsum()
        if len(obv) >= 20:
            recent_obv = obv.iloc[-20:]
            slope = (recent_obv.iloc[-1] - recent_obv.iloc[0]) / 20
            obv_trend = "상승" if slope > 0 else "하락"
    except Exception as exc:
        logger.warning("OBV trend failed for %s: %s", ticker, exc)

    return {
        "ticker": ticker,
        "current_price": base.get("current_price"),
        "rsi": base.get("rsi"),
        "macd": {
            "value": base.get("macd"),
            "signal": base.get("macd_signal"),
            "histogram": base.get("macd_histogram"),
        },
        "bollinger_bands": {
            "upper": base.get("bb_upper"),
            "middle": base.get("bb_middle"),
            "lower": base.get("bb_lower"),
            "width": base.get("bb_width"),
        },
        "moving_averages": {
            "ma_20": base.get("ma_20"),
            "ma_60": base.get("ma_60"),
            "ma_120": base.get("ma_120"),
            "ma_240": base.get("ma_240"),
        },
        "ma_distances_pct": {
            str(period): info.get("distance_pct")
            for period, info in ma_distances.items()
        },
        "stochastic": {"k": stoch_k, "d": stoch_d},
        "obv_trend": obv_trend,
        "volume_ratio": base.get("volume_ratio"),
        "high_52w": base.get("high_52w"),
        "low_52w": base.get("low_52w"),
    }


def run_get_news(ticker: str, limit: int = 5) -> Dict[str, Any]:
    try:
        from news.aggregator import get_news as get_news

        items = get_news(ticker, limit=limit)
        rows = [
            {
                "title": item.title,
                "summary": getattr(item, "summary", None),
                "published_at": (
                    item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else None
                ),
                "source": getattr(item, "source", None),
                "url": getattr(item, "url", None),
            }
            for item in items
        ]
        return {"ticker": ticker, "news": rows, "count": len(rows)}
    except Exception as exc:
        logger.warning("News service unavailable: %s", exc)
        return {"ticker": ticker, "news": [], "note": "뉴스 서비스 사용 불가"}


def run_get_macro_context() -> Dict[str, Any]:
    try:
        from api.services.macro_service import get_macro_market_service

        bundle = get_macro_market_service().get_bundle()
        signal = bundle.get("signal", {})
        fx = bundle.get("fx", {})
        interpretation = bundle.get("interpretation", {})
        futures = bundle.get("futures", {})
        return {
            "macro_score": signal.get("score"),
            "regime": signal.get("regime"),
            "confidence_band": signal.get("confidence_band"),
            "entry_signal": interpretation.get("entry_signal"),
            "posture": interpretation.get("posture"),
            "usd_krw": fx.get("rate"),
            "usd_krw_change_pct": fx.get("change_pct"),
            "futures_change_pct": futures.get("change_pct"),
            "is_market_hours": bundle.get("is_market_hours"),
            "generated_at": bundle.get("generated_at"),
        }
    except Exception as exc:
        logger.warning("Macro service unavailable: %s", exc)
        return {"note": "매크로 데이터 사용 불가", "error": str(exc)}


TOOL_MAP = {
    "get_holdings": lambda inp: run_get_holdings(),
    "get_price_history": lambda inp: run_get_price_history(inp["ticker"], inp.get("days", 60)),
    "get_indicators": lambda inp: run_get_indicators(inp["ticker"], inp.get("days", 120)),
    "get_news": lambda inp: run_get_news(inp["ticker"], inp.get("limit", 5)),
    "get_macro_context": lambda inp: run_get_macro_context(),
}


def execute_tool(name: str, tool_input: Dict[str, Any]) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(tool_input)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc, exc_info=True)
        return json.dumps({"error": str(exc)})
