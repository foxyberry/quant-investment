"""
Stock Analysis Prompt Templates
주식 분석 프롬프트 템플릿

This module provides structured prompt templates for Claude to analyze stocks.
Prompts are designed to request JSON output for easy parsing.

Usage:
    from llm.prompts.stock_analysis import (
        SYSTEM_PROMPT,
        format_valuation_prompt,
        format_quick_screen_prompt
    )

    prompt = format_valuation_prompt(
        ticker="AAPL",
        name="Apple Inc.",
        current_price=175.50,
        ma_240=168.20,
        technical={"rsi": 45.2, "macd": 1.5, ...},
        fundamental={"pe_ratio": 28.5, "roe": 147.5, ...}
    )
"""

from typing import Dict, Any, List, Optional, Union


# =============================================================================
# System Prompts
# =============================================================================

SYSTEM_PROMPT = """You are a professional equity analyst with expertise in both fundamental and technical analysis.
Your task is to analyze stocks and provide actionable investment recommendations.
Always respond in valid JSON format as specified in the user prompt.
Be objective, data-driven, and highlight both opportunities and risks."""

SYSTEM_PROMPT_KOREAN = """당신은 펀더멘털 분석과 기술적 분석 모두에 전문성을 갖춘 전문 주식 애널리스트입니다.
주식을 분석하고 실행 가능한 투자 추천을 제공하는 것이 당신의 역할입니다.
사용자 프롬프트에 지정된 대로 항상 유효한 JSON 형식으로 응답하세요.
객관적이고 데이터 기반으로 분석하며, 기회와 위험을 모두 강조하세요."""


# =============================================================================
# Main Analysis Prompts
# =============================================================================

VALUATION_PROMPT = """
Analyze this stock for potential investment opportunity.

## Stock Information
- Ticker: {ticker}
- Company: {name}
- Current Price: {currency}{current_price}
- 240-day MA: {currency}{ma_240}
- Distance from 240d MA: {distance_pct}

## Technical Indicators
- RSI (14): {rsi} ({rsi_signal})
- MACD: {macd} (Signal: {macd_signal}, Cross: {macd_cross})
- Bollinger Bands: {bb_position} (Upper: {bb_upper}, Lower: {bb_lower})
- Stochastic: K={stochastic_k}, D={stochastic_d}
- Volume Ratio: {volume_ratio} (vs 20-day avg)

## Fundamental Data
- P/E Ratio: {pe_ratio}
- P/B Ratio: {pb_ratio}
- ROE: {roe}
- Profit Margin: {profit_margin}
- Debt/Equity: {debt_to_equity}
- Dividend Yield: {dividend_yield}
- Market Cap: {market_cap_str}
- Sector: {sector}
- Industry: {industry}

## Recent News Summary
{news_summary}

## Analysis Required
Provide your analysis in the following JSON format:
{{
    "valuation_score": <1-10, where 10 is extremely undervalued>,
    "risk_score": <1-10, where 10 is highest risk>,
    "entry_recommendation": "<BUY|WAIT|AVOID>",
    "target_price": <your 12-month target price or null>,
    "stop_loss_price": <suggested stop loss price>,
    "reasoning": "<2-3 sentence summary of your analysis>",
    "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "catalysts": ["<catalyst 1>", "<catalyst 2>"],
    "technical_view": "<bullish|neutral|bearish>",
    "fundamental_view": "<undervalued|fair|overvalued>"
}}

Important:
- Consider the stock is touching its 240-day MA (potential support/resistance)
- Evaluate if current price offers good risk/reward
- Be specific about entry timing
"""

QUICK_SCREEN_PROMPT = """
Quickly evaluate these {count} stocks touching their 240-day MA.
Rate each stock's investment potential.

{stocks_summary}

For each stock, provide a brief JSON array:
[
    {{
        "ticker": "<ticker>",
        "score": <1-10>,
        "action": "<BUY|WAIT|AVOID>",
        "one_liner": "<one sentence reason>"
    }},
    ...
]

Focus on:
- Risk/reward at current levels
- Technical setup quality
- Fundamental value
"""

RISK_ASSESSMENT_PROMPT = """
Perform a detailed risk assessment for this stock.

## Stock Information
- Ticker: {ticker}
- Company: {name}
- Sector: {sector}
- Market Cap: {market_cap_str}

## Price Metrics
- Current Price: {currency}{current_price}
- 52-Week High: {currency}{high_52w}
- 52-Week Low: {currency}{low_52w}
- Distance from High: {distance_from_high}
- Volatility (20d): {volatility}

## Financial Health
- Debt/Equity: {debt_to_equity}
- Current Ratio: {current_ratio}
- Interest Coverage: {interest_coverage}
- Free Cash Flow: {fcf}

## Market Conditions
{market_context}

Provide your risk analysis in the following JSON format:
{{
    "overall_risk_level": "<LOW|MEDIUM|HIGH|VERY_HIGH>",
    "risk_score": <1-10, where 10 is highest risk>,
    "max_recommended_position_pct": <suggested max portfolio allocation %>,
    "suggested_stop_loss_pct": <suggested stop loss % from entry>,
    "risk_factors": [
        {{
            "category": "<MARKET|COMPANY|SECTOR|FINANCIAL|TECHNICAL>",
            "description": "<risk description>",
            "severity": "<LOW|MEDIUM|HIGH>",
            "mitigation": "<how to mitigate this risk>"
        }}
    ],
    "key_warning_signs": ["<warning 1>", "<warning 2>"],
    "risk_summary": "<2-3 sentence summary of risk profile>"
}}
"""

ENTRY_TIMING_PROMPT = """
Analyze the optimal entry timing for this stock.

## Stock Information
- Ticker: {ticker}
- Current Price: {currency}{current_price}
- Trend: {trend_direction}

## Support/Resistance Levels
{support_resistance}

## Technical Setup
- RSI: {rsi}
- MACD: {macd} (Signal: {macd_signal})
- Stochastic: K={stochastic_k}, D={stochastic_d}
- 20-day MA: {currency}{ma_20}
- 60-day MA: {currency}{ma_60}
- 240-day MA: {currency}{ma_240}

## Volume Analysis
- Current Volume: {volume}
- 20-day Avg Volume: {volume_ma}
- Volume Trend: {volume_trend}

## Recent Price Action
{recent_price_action}

Provide your entry timing analysis in the following JSON format:
{{
    "entry_timing": "<IMMEDIATE|WAIT_FOR_DIP|WAIT_FOR_BREAKOUT|AVOID>",
    "confidence": <1-10>,
    "ideal_entry_price": <suggested entry price>,
    "entry_zone": {{
        "lower": <lower bound of entry zone>,
        "upper": <upper bound of entry zone>
    }},
    "stop_loss": <suggested stop loss price>,
    "take_profit_targets": [<target 1>, <target 2>, <target 3>],
    "time_horizon": "<DAYS|WEEKS|MONTHS>",
    "key_levels_to_watch": [
        {{
            "price": <price level>,
            "type": "<SUPPORT|RESISTANCE>",
            "significance": "<LOW|MEDIUM|HIGH>"
        }}
    ],
    "entry_triggers": ["<trigger 1>", "<trigger 2>"],
    "avoid_if": ["<condition 1>", "<condition 2>"],
    "reasoning": "<2-3 sentence explanation of timing recommendation>"
}}
"""


# =============================================================================
# Helper Functions
# =============================================================================

def _safe_format(value: Any, fmt: str = ".2f", default: str = "N/A") -> str:
    """Safely format a value, returning default if None or invalid."""
    if value is None:
        return default
    try:
        if fmt.endswith("f"):
            return f"{float(value):{fmt}}"
        elif fmt.endswith("d"):
            return f"{int(value):{fmt}}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return default


def _safe_pct(value: Any, default: str = "N/A") -> str:
    """Safely format a percentage value."""
    if value is None:
        return default
    try:
        return f"{float(value):+.1f}%"
    except (ValueError, TypeError):
        return default


def format_market_cap(market_cap: Optional[float]) -> str:
    """
    Format market cap into readable string (e.g., $2.5T, $150B, $500M).

    Args:
        market_cap: Market capitalization in raw number

    Returns:
        Formatted string like "$2.5T", "$150B", "$500M", or "N/A"
    """
    if market_cap is None:
        return "N/A"

    try:
        market_cap = float(market_cap)
    except (ValueError, TypeError):
        return "N/A"

    if market_cap >= 1_000_000_000_000:  # Trillion
        return f"${market_cap / 1_000_000_000_000:.1f}T"
    elif market_cap >= 1_000_000_000:  # Billion
        return f"${market_cap / 1_000_000_000:.1f}B"
    elif market_cap >= 1_000_000:  # Million
        return f"${market_cap / 1_000_000:.1f}M"
    elif market_cap >= 1_000:  # Thousand
        return f"${market_cap / 1_000:.1f}K"
    else:
        return f"${market_cap:.0f}"


def format_news_summary(news: Optional[Dict[str, Any]]) -> str:
    """
    Format news data into a readable summary for the prompt.

    Args:
        news: Dictionary containing news data with keys like:
            - headlines: List of headline strings
            - sentiment: Overall sentiment score or label
            - positive_count, negative_count, neutral_count
            - latest_news: List of news items

    Returns:
        Formatted news summary string
    """
    if not news:
        return "No recent news available."

    lines = []

    # Add sentiment overview if available
    if "avg_sentiment_score" in news:
        score = news["avg_sentiment_score"]
        if score > 0.2:
            sentiment_label = "Positive"
        elif score < -0.2:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"
        lines.append(f"Overall Sentiment: {sentiment_label} ({score:+.2f})")

    # Add counts if available
    pos = news.get("positive_count", 0)
    neg = news.get("negative_count", 0)
    neu = news.get("neutral_count", 0)
    total = pos + neg + neu
    if total > 0:
        lines.append(f"News Distribution: {pos} positive, {neg} negative, {neu} neutral (total: {total})")

    # Add headlines
    headlines = news.get("headlines", [])
    if not headlines and "latest_news" in news:
        headlines = [item.get("title", "") for item in news["latest_news"][:5]]

    if headlines:
        lines.append("\nRecent Headlines:")
        for i, headline in enumerate(headlines[:5], 1):
            if headline:
                # Truncate long headlines
                if len(headline) > 80:
                    headline = headline[:77] + "..."
                lines.append(f"  {i}. {headline}")

    return "\n".join(lines) if lines else "No recent news available."


def _get_rsi_signal(rsi: Optional[float]) -> str:
    """Get RSI signal interpretation."""
    if rsi is None:
        return "N/A"
    if rsi >= 70:
        return "Overbought"
    elif rsi >= 60:
        return "Strong"
    elif rsi >= 40:
        return "Neutral"
    elif rsi >= 30:
        return "Weak"
    else:
        return "Oversold"


def _get_macd_cross(macd: Optional[float], macd_signal: Optional[float]) -> str:
    """Determine MACD cross status."""
    if macd is None or macd_signal is None:
        return "N/A"
    diff = macd - macd_signal
    if abs(diff) < 0.01:  # Near crossover
        return "Crossing"
    elif diff > 0:
        return "Bullish"
    else:
        return "Bearish"


def _get_bb_position(
    current_price: Optional[float],
    bb_upper: Optional[float],
    bb_lower: Optional[float]
) -> str:
    """Determine Bollinger Band position."""
    if current_price is None or bb_upper is None or bb_lower is None:
        return "N/A"

    bb_range = bb_upper - bb_lower
    if bb_range <= 0:
        return "N/A"

    position = (current_price - bb_lower) / bb_range

    if position >= 0.9:
        return "Near Upper Band"
    elif position >= 0.6:
        return "Upper Half"
    elif position >= 0.4:
        return "Middle"
    elif position >= 0.1:
        return "Lower Half"
    else:
        return "Near Lower Band"


def format_valuation_prompt(
    ticker: str,
    name: str,
    current_price: float,
    ma_240: float,
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
    news: Optional[Dict[str, Any]] = None,
    currency: str = "$"
) -> str:
    """
    Format the valuation prompt with stock data.

    Args:
        ticker: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        ma_240: 240-day moving average
        technical: Dictionary with technical indicators:
            - rsi, macd, macd_signal, macd_histogram
            - bb_upper, bb_lower, bb_middle
            - stochastic_k, stochastic_d
            - volume, volume_ma, volume_ratio
        fundamental: Dictionary with fundamental data:
            - pe_ratio, pb_ratio, roe, profit_margin
            - debt_to_equity, dividend_yield, market_cap
            - sector, industry
        news: Optional dictionary with news data
        currency: Currency symbol (default: "$")

    Returns:
        Formatted prompt string ready for Claude
    """
    # Calculate distance from 240d MA
    if ma_240 and ma_240 > 0:
        distance_pct = ((current_price - ma_240) / ma_240) * 100
        distance_str = f"{distance_pct:+.1f}%"
    else:
        distance_str = "N/A"

    # Extract technical indicators with safe defaults
    rsi = technical.get("rsi")
    macd = technical.get("macd")
    macd_signal = technical.get("macd_signal")
    bb_upper = technical.get("bb_upper")
    bb_lower = technical.get("bb_lower")
    stochastic_k = technical.get("stochastic_k")
    stochastic_d = technical.get("stochastic_d")
    volume_ratio = technical.get("volume_ratio")

    # Format fundamental data
    market_cap = fundamental.get("market_cap")

    return VALUATION_PROMPT.format(
        ticker=ticker,
        name=name if name else ticker,
        currency=currency,
        current_price=_safe_format(current_price, ".2f"),
        ma_240=_safe_format(ma_240, ".2f"),
        distance_pct=distance_str,
        rsi=_safe_format(rsi, ".1f"),
        rsi_signal=_get_rsi_signal(rsi),
        macd=_safe_format(macd, ".2f"),
        macd_signal=_safe_format(macd_signal, ".2f"),
        macd_cross=_get_macd_cross(macd, macd_signal),
        bb_position=_get_bb_position(current_price, bb_upper, bb_lower),
        bb_upper=_safe_format(bb_upper, ".2f"),
        bb_lower=_safe_format(bb_lower, ".2f"),
        stochastic_k=_safe_format(stochastic_k, ".1f"),
        stochastic_d=_safe_format(stochastic_d, ".1f"),
        volume_ratio=_safe_format(volume_ratio, ".2f"),
        pe_ratio=_safe_format(fundamental.get("pe_ratio"), ".1f"),
        pb_ratio=_safe_format(fundamental.get("pb_ratio"), ".2f"),
        roe=_safe_format(fundamental.get("roe"), ".1f"),
        profit_margin=_safe_format(fundamental.get("profit_margin"), ".1f"),
        debt_to_equity=_safe_format(fundamental.get("debt_to_equity"), ".2f"),
        dividend_yield=_safe_format(fundamental.get("dividend_yield"), ".2f"),
        market_cap_str=format_market_cap(market_cap),
        sector=fundamental.get("sector", "N/A") or "N/A",
        industry=fundamental.get("industry", "N/A") or "N/A",
        news_summary=format_news_summary(news)
    )


def format_quick_screen_prompt(stocks: List[Dict[str, Any]]) -> str:
    """
    Format the quick screening prompt for multiple stocks.

    Args:
        stocks: List of stock dictionaries, each containing:
            - ticker: Stock symbol
            - name: Company name
            - current_price: Current price
            - ma_240: 240-day MA
            - distance_pct: Distance from 240d MA (%)
            - rsi: RSI value
            - sector: Sector name
            - pe_ratio: P/E ratio (optional)

    Returns:
        Formatted prompt string for batch screening
    """
    if not stocks:
        return "No stocks provided for screening."

    lines = []
    for i, stock in enumerate(stocks, 1):
        ticker = stock.get("ticker", "N/A")
        name = stock.get("name", ticker)
        price = _safe_format(stock.get("current_price"), ".2f")
        ma_240 = _safe_format(stock.get("ma_240"), ".2f")
        distance = _safe_pct(stock.get("distance_pct"))
        rsi = _safe_format(stock.get("rsi"), ".1f")
        sector = stock.get("sector", "N/A") or "N/A"
        pe = _safe_format(stock.get("pe_ratio"), ".1f")

        lines.append(
            f"{i}. {ticker} ({name})\n"
            f"   Price: ${price} | 240d MA: ${ma_240} | Distance: {distance}\n"
            f"   RSI: {rsi} | Sector: {sector} | P/E: {pe}"
        )

    stocks_summary = "\n\n".join(lines)

    return QUICK_SCREEN_PROMPT.format(
        count=len(stocks),
        stocks_summary=stocks_summary
    )


def format_risk_assessment_prompt(
    ticker: str,
    name: str,
    current_price: float,
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
    market_context: str = "Normal market conditions.",
    currency: str = "$"
) -> str:
    """
    Format the risk assessment prompt.

    Args:
        ticker: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        technical: Dictionary with technical data including volatility, 52w high/low
        fundamental: Dictionary with financial health metrics
        market_context: Description of current market conditions
        currency: Currency symbol

    Returns:
        Formatted risk assessment prompt
    """
    high_52w = technical.get("high_52w")
    low_52w = technical.get("low_52w")

    # Calculate distance from 52w high
    if high_52w and high_52w > 0:
        dist_from_high = ((current_price - high_52w) / high_52w) * 100
        dist_from_high_str = f"{dist_from_high:.1f}%"
    else:
        dist_from_high_str = "N/A"

    return RISK_ASSESSMENT_PROMPT.format(
        ticker=ticker,
        name=name if name else ticker,
        sector=fundamental.get("sector", "N/A") or "N/A",
        market_cap_str=format_market_cap(fundamental.get("market_cap")),
        currency=currency,
        current_price=_safe_format(current_price, ".2f"),
        high_52w=_safe_format(high_52w, ".2f"),
        low_52w=_safe_format(low_52w, ".2f"),
        distance_from_high=dist_from_high_str,
        volatility=_safe_format(technical.get("volatility"), ".1f"),
        debt_to_equity=_safe_format(fundamental.get("debt_to_equity"), ".2f"),
        current_ratio=_safe_format(fundamental.get("current_ratio"), ".2f"),
        interest_coverage=_safe_format(fundamental.get("interest_coverage"), ".2f"),
        fcf=_safe_format(fundamental.get("free_cash_flow"), ".0f"),
        market_context=market_context
    )


def format_entry_timing_prompt(
    ticker: str,
    current_price: float,
    technical: Dict[str, Any],
    support_resistance: Optional[str] = None,
    recent_price_action: Optional[str] = None,
    currency: str = "$"
) -> str:
    """
    Format the entry timing analysis prompt.

    Args:
        ticker: Stock ticker symbol
        current_price: Current stock price
        technical: Dictionary with technical indicators
        support_resistance: Description of key S/R levels
        recent_price_action: Description of recent price action
        currency: Currency symbol

    Returns:
        Formatted entry timing prompt
    """
    # Determine trend direction
    ma_20 = technical.get("ma_20")
    ma_60 = technical.get("ma_60")
    ma_240 = technical.get("ma_240")

    if ma_20 and ma_60 and ma_240:
        if current_price > ma_20 > ma_60 > ma_240:
            trend = "Strong Uptrend"
        elif current_price > ma_20 > ma_60:
            trend = "Uptrend"
        elif current_price < ma_20 < ma_60 < ma_240:
            trend = "Strong Downtrend"
        elif current_price < ma_20 < ma_60:
            trend = "Downtrend"
        else:
            trend = "Sideways/Consolidating"
    else:
        trend = "N/A"

    # Volume trend
    volume = technical.get("volume")
    volume_ma = technical.get("volume_ma")
    if volume and volume_ma:
        ratio = volume / volume_ma
        if ratio > 1.5:
            volume_trend = "High (above average)"
        elif ratio > 1.0:
            volume_trend = "Slightly above average"
        elif ratio > 0.7:
            volume_trend = "Slightly below average"
        else:
            volume_trend = "Low (below average)"
    else:
        volume_trend = "N/A"

    # Default support/resistance if not provided
    if not support_resistance:
        support_resistance = "Not specified - analyze from price levels"

    # Default recent price action if not provided
    if not recent_price_action:
        recent_price_action = "Not specified - analyze from technical indicators"

    return ENTRY_TIMING_PROMPT.format(
        ticker=ticker,
        currency=currency,
        current_price=_safe_format(current_price, ".2f"),
        trend_direction=trend,
        support_resistance=support_resistance,
        rsi=_safe_format(technical.get("rsi"), ".1f"),
        macd=_safe_format(technical.get("macd"), ".2f"),
        macd_signal=_safe_format(technical.get("macd_signal"), ".2f"),
        stochastic_k=_safe_format(technical.get("stochastic_k"), ".1f"),
        stochastic_d=_safe_format(technical.get("stochastic_d"), ".1f"),
        ma_20=_safe_format(ma_20, ".2f"),
        ma_60=_safe_format(ma_60, ".2f"),
        ma_240=_safe_format(ma_240, ".2f"),
        volume=_safe_format(volume, ".0f"),
        volume_ma=_safe_format(volume_ma, ".0f"),
        volume_trend=volume_trend,
        recent_price_action=recent_price_action
    )


# =============================================================================
# Response Schemas (for documentation and validation)
# =============================================================================

VALUATION_RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "valuation_score", "risk_score", "entry_recommendation",
        "reasoning", "key_risks", "catalysts", "technical_view", "fundamental_view"
    ],
    "properties": {
        "valuation_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "risk_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "entry_recommendation": {"type": "string", "enum": ["BUY", "WAIT", "AVOID"]},
        "target_price": {"type": ["number", "null"]},
        "stop_loss_price": {"type": "number"},
        "reasoning": {"type": "string"},
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "catalysts": {"type": "array", "items": {"type": "string"}},
        "technical_view": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
        "fundamental_view": {"type": "string", "enum": ["undervalued", "fair", "overvalued"]}
    }
}

QUICK_SCREEN_RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["ticker", "score", "action", "one_liner"],
        "properties": {
            "ticker": {"type": "string"},
            "score": {"type": "integer", "minimum": 1, "maximum": 10},
            "action": {"type": "string", "enum": ["BUY", "WAIT", "AVOID"]},
            "one_liner": {"type": "string"}
        }
    }
}

RISK_ASSESSMENT_RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "overall_risk_level", "risk_score", "max_recommended_position_pct",
        "suggested_stop_loss_pct", "risk_factors", "risk_summary"
    ],
    "properties": {
        "overall_risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]},
        "risk_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "max_recommended_position_pct": {"type": "number"},
        "suggested_stop_loss_pct": {"type": "number"},
        "risk_factors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                    "mitigation": {"type": "string"}
                }
            }
        },
        "key_warning_signs": {"type": "array", "items": {"type": "string"}},
        "risk_summary": {"type": "string"}
    }
}

ENTRY_TIMING_RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "entry_timing", "confidence", "ideal_entry_price", "entry_zone",
        "stop_loss", "take_profit_targets", "reasoning"
    ],
    "properties": {
        "entry_timing": {"type": "string", "enum": ["IMMEDIATE", "WAIT_FOR_DIP", "WAIT_FOR_BREAKOUT", "AVOID"]},
        "confidence": {"type": "integer", "minimum": 1, "maximum": 10},
        "ideal_entry_price": {"type": "number"},
        "entry_zone": {
            "type": "object",
            "properties": {
                "lower": {"type": "number"},
                "upper": {"type": "number"}
            }
        },
        "stop_loss": {"type": "number"},
        "take_profit_targets": {"type": "array", "items": {"type": "number"}},
        "time_horizon": {"type": "string", "enum": ["DAYS", "WEEKS", "MONTHS"]},
        "key_levels_to_watch": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "price": {"type": "number"},
                    "type": {"type": "string", "enum": ["SUPPORT", "RESISTANCE"]},
                    "significance": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]}
                }
            }
        },
        "entry_triggers": {"type": "array", "items": {"type": "string"}},
        "avoid_if": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"}
    }
}
