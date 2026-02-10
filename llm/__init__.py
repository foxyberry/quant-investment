"""
LLM Module for Stock Analysis
Claude AI integration for quantitative analysis

This module provides Claude-based stock analysis capabilities.

Usage:
    from llm import ClaudeAnalyzer, AnalysisResult

    # Initialize analyzer (uses ANTHROPIC_API_KEY env var)
    analyzer = ClaudeAnalyzer()

    # Analyze a single stock
    result = analyzer.analyze_stock(
        ticker="AAPL",
        name="Apple Inc.",
        current_price=175.50,
        ma_240=165.30,
        technical={"rsi": 55, "macd_histogram": 0.5},
        fundamental={"pe_ratio": 28, "market_cap": "2.8T"}
    )

    print(f"Recommendation: {result.entry_recommendation}")
    print(f"Valuation Score: {result.valuation_score}/10")
    print(f"Risk Score: {result.risk_score}/10")

    # Batch analysis
    stocks = [
        {"ticker": "AAPL", "name": "Apple Inc.", ...},
        {"ticker": "MSFT", "name": "Microsoft Corp.", ...}
    ]
    results = analyzer.analyze_batch(stocks)

    # Use prompt templates directly
    from llm.prompts import format_valuation_prompt, SYSTEM_PROMPT
    prompt = format_valuation_prompt(ticker="AAPL", ...)

Environment Variables:
    ANTHROPIC_API_KEY: Anthropic API key for Claude access
"""

from .claude_client import (
    ClaudeAnalyzer,
    AnalysisResult,
    ClaudeAnalyzerError,
    APIKeyMissingError,
    APICallError,
    ResponseParseError,
)

from .stock_analyzer import (
    StockAnalyzer,
    StockProfile,
    FullAnalysisResult,
)

from .prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_KOREAN,
    VALUATION_PROMPT,
    QUICK_SCREEN_PROMPT,
    RISK_ASSESSMENT_PROMPT,
    ENTRY_TIMING_PROMPT,
    format_valuation_prompt,
    format_quick_screen_prompt,
    format_risk_assessment_prompt,
    format_entry_timing_prompt,
    format_market_cap,
    format_news_summary,
    VALUATION_RESPONSE_SCHEMA,
    QUICK_SCREEN_RESPONSE_SCHEMA,
    RISK_ASSESSMENT_RESPONSE_SCHEMA,
    ENTRY_TIMING_RESPONSE_SCHEMA,
)

__all__ = [
    # Main classes
    "ClaudeAnalyzer",
    "AnalysisResult",
    "StockAnalyzer",
    "StockProfile",
    "FullAnalysisResult",

    # Exceptions
    "ClaudeAnalyzerError",
    "APIKeyMissingError",
    "APICallError",
    "ResponseParseError",

    # Prompt templates
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_KOREAN",
    "VALUATION_PROMPT",
    "QUICK_SCREEN_PROMPT",
    "RISK_ASSESSMENT_PROMPT",
    "ENTRY_TIMING_PROMPT",

    # Prompt formatting functions
    "format_valuation_prompt",
    "format_quick_screen_prompt",
    "format_risk_assessment_prompt",
    "format_entry_timing_prompt",
    "format_market_cap",
    "format_news_summary",

    # Response schemas
    "VALUATION_RESPONSE_SCHEMA",
    "QUICK_SCREEN_RESPONSE_SCHEMA",
    "RISK_ASSESSMENT_RESPONSE_SCHEMA",
    "ENTRY_TIMING_RESPONSE_SCHEMA",
]
