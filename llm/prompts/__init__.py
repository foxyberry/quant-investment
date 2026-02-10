"""
LLM Prompts for Stock Analysis
주식 분석을 위한 LLM 프롬프트

This module provides structured prompt templates for Claude to analyze stocks.
All prompts are designed to request JSON output for easy parsing.

Usage:
    from llm.prompts import (
        SYSTEM_PROMPT,
        VALUATION_PROMPT,
        format_valuation_prompt,
        format_quick_screen_prompt,
        format_market_cap,
        format_news_summary
    )

    # Format a complete valuation prompt
    prompt = format_valuation_prompt(
        ticker="AAPL",
        name="Apple Inc.",
        current_price=175.50,
        ma_240=168.20,
        technical={"rsi": 45.2, "macd": 1.5, ...},
        fundamental={"pe_ratio": 28.5, "roe": 147.5, ...}
    )

    # Quick screen multiple stocks
    batch_prompt = format_quick_screen_prompt([
        {"ticker": "AAPL", "current_price": 175.5, ...},
        {"ticker": "MSFT", "current_price": 380.2, ...}
    ])
"""

from .stock_analysis import (
    # System prompts
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_KOREAN,

    # Main prompts (raw templates)
    VALUATION_PROMPT,
    QUICK_SCREEN_PROMPT,
    RISK_ASSESSMENT_PROMPT,
    ENTRY_TIMING_PROMPT,

    # Formatting functions
    format_valuation_prompt,
    format_quick_screen_prompt,
    format_risk_assessment_prompt,
    format_entry_timing_prompt,

    # Helper functions
    format_market_cap,
    format_news_summary,

    # Response schemas (for validation)
    VALUATION_RESPONSE_SCHEMA,
    QUICK_SCREEN_RESPONSE_SCHEMA,
    RISK_ASSESSMENT_RESPONSE_SCHEMA,
    ENTRY_TIMING_RESPONSE_SCHEMA,
)

__all__ = [
    # System prompts
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_KOREAN",

    # Main prompts
    "VALUATION_PROMPT",
    "QUICK_SCREEN_PROMPT",
    "RISK_ASSESSMENT_PROMPT",
    "ENTRY_TIMING_PROMPT",

    # Formatting functions
    "format_valuation_prompt",
    "format_quick_screen_prompt",
    "format_risk_assessment_prompt",
    "format_entry_timing_prompt",

    # Helper functions
    "format_market_cap",
    "format_news_summary",

    # Response schemas
    "VALUATION_RESPONSE_SCHEMA",
    "QUICK_SCREEN_RESPONSE_SCHEMA",
    "RISK_ASSESSMENT_RESPONSE_SCHEMA",
    "ENTRY_TIMING_RESPONSE_SCHEMA",
]
