"""
Analysis Service.

Business logic for stock analysis operations.
Integrates data enrichment modules and LLM analysis.
"""

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from api.schemas.analysis import (
    EnrichedStock,
    ReportSummary,
    ReportDetail,
    AnalysisResult,
)

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis"


class AnalysisService:
    """
    Analysis service for stock data enrichment and analysis.

    Provides methods for:
    - Enriching stock data with technical, fundamental, and news information
    - Retrieving stored analysis reports
    - Retrieving enriched JSON data
    """

    def __init__(self):
        """Initialize the analysis service."""
        # Lazy-loaded enrichers
        self._technical_enricher = None
        self._fundamental_enricher = None
        self._news_enricher = None
        self._cache = None
        self._stock_analyzer = None

        # Check if Claude API is available
        self._claude_available = bool(os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def cache(self):
        """Get or create OHLCV cache instance."""
        if self._cache is None:
            from utils.data_cache import OHLCVCache
            self._cache = OHLCVCache()
        return self._cache

    @property
    def technical_enricher(self):
        """Get or create technical enricher instance."""
        if self._technical_enricher is None:
            from data_enrichment import TechnicalEnricher
            self._technical_enricher = TechnicalEnricher()
        return self._technical_enricher

    @property
    def fundamental_enricher(self):
        """Get or create fundamental enricher instance."""
        if self._fundamental_enricher is None:
            from data_enrichment import FundamentalEnricher
            self._fundamental_enricher = FundamentalEnricher()
        return self._fundamental_enricher

    @property
    def news_enricher(self):
        """Get or create news enricher instance."""
        if self._news_enricher is None:
            from data_enrichment import NewsEnricher
            self._news_enricher = NewsEnricher(max_articles=10, days=7)
        return self._news_enricher

    @property
    def stock_analyzer(self):
        """Get or create stock analyzer instance (requires Claude API)."""
        if self._stock_analyzer is None and self._claude_available:
            try:
                from llm import StockAnalyzer
                self._stock_analyzer = StockAnalyzer()
            except Exception as e:
                logger.warning(f"Failed to initialize StockAnalyzer: {e}")
                self._stock_analyzer = None
        return self._stock_analyzer

    def enrich_stock(self, ticker: str, include_news: bool = True) -> EnrichedStock:
        """
        Enrich a single stock with technical, fundamental, and news data.

        This operation may take 10-30 seconds depending on data sources.

        Args:
            ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
            include_news: Whether to include news enrichment

        Returns:
            EnrichedStock with all enriched data

        Raises:
            ValueError: If ticker data cannot be fetched
        """
        logger.info(f"Enriching stock: {ticker}")

        # Get OHLCV data
        data = self.cache.get(ticker, days=250)
        if data is None or data.empty:
            raise ValueError(f"No OHLCV data available for {ticker}")

        # Calculate current price and MA
        current_price = float(data["close"].iloc[-1])

        ma_240 = None
        if len(data) >= 240:
            ma_240 = float(data["close"].tail(240).mean())
        elif len(data) >= 20:
            ma_240 = float(data["close"].mean())

        # Calculate distance percentage
        distance_pct = None
        if ma_240 and ma_240 > 0:
            distance_pct = (current_price - ma_240) / ma_240 * 100

        def _load_technical() -> Dict[str, Any]:
            try:
                return self.technical_enricher.enrich(ticker, data)
            except Exception as e:
                logger.warning(f"Technical enrichment failed for {ticker}: {e}")
                return {}

        def _load_fundamental() -> Dict[str, Any]:
            try:
                return self.fundamental_enricher.enrich(ticker)
            except Exception as e:
                logger.warning(f"Fundamental enrichment failed for {ticker}: {e}")
                return {}

        def _load_news() -> Optional[Dict[str, Any]]:
            if not include_news:
                return None
            try:
                return self.news_enricher.enrich(ticker, name=None)
            except Exception as e:
                logger.warning(f"News enrichment failed for {ticker}: {e}")
                return None

        max_workers = 3 if include_news else 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            technical_future = executor.submit(_load_technical)
            fundamental_future = executor.submit(_load_fundamental)
            news_future = executor.submit(_load_news) if include_news else None

            technical = technical_future.result()
            fundamental = fundamental_future.result()
            news = news_future.result() if news_future else None

        name = fundamental.get("name") if isinstance(fundamental, dict) else None

        return EnrichedStock(
            ticker=ticker,
            name=name or ticker,
            current_price=current_price,
            ma_240=ma_240,
            distance_pct=distance_pct,
            technical=technical,
            fundamental=fundamental,
            news=news,
        )

    def analyze_stock(
        self,
        ticker: str,
        include_news: bool = True
    ) -> Optional[AnalysisResult]:
        """
        Analyze a single stock using Claude AI.

        This operation requires ANTHROPIC_API_KEY environment variable.
        May take 30+ seconds due to API calls.

        Args:
            ticker: Stock ticker symbol
            include_news: Whether to include news in analysis

        Returns:
            AnalysisResult if Claude API is available, None otherwise

        Raises:
            ValueError: If ticker data cannot be fetched
        """
        if not self._claude_available or self.stock_analyzer is None:
            logger.warning("Claude API not available for analysis")
            return None

        try:
            # Use stock analyzer which handles all enrichment and analysis
            result = self.stock_analyzer.analyze(ticker)

            return AnalysisResult(
                ticker=result.ticker,
                name=result.name,
                current_price=result.current_price,
                valuation_score=result.valuation_score,
                risk_score=result.risk_score,
                entry_recommendation=result.entry_recommendation,
                reasoning=result.reasoning,
                key_risks=result.key_risks,
                catalysts=result.catalysts,
            )
        except Exception as e:
            logger.error(f"Analysis failed for {ticker}: {e}")
            raise ValueError(f"Analysis failed: {str(e)}")

    def get_reports(self) -> List[ReportSummary]:
        """
        Get list of available analysis reports.

        Returns:
            List of ReportSummary objects
        """
        reports = []

        if not DATA_ANALYSIS_DIR.exists():
            return reports

        # Find all report markdown files
        for report_file in DATA_ANALYSIS_DIR.glob("report_*.md"):
            # Extract date from filename (report_YYYYMMDD.md)
            match = re.match(r"report_(\d{8})\.md", report_file.name)
            if not match:
                continue

            date_str = match.group(1)

            # Read file to extract summary info
            try:
                content = report_file.read_text(encoding="utf-8")
                summary = self._parse_report_summary(date_str, content)
                reports.append(summary)
            except Exception as e:
                logger.warning(f"Failed to parse report {report_file}: {e}")

        # Sort by date descending
        reports.sort(key=lambda x: x.date, reverse=True)

        return reports

    def _parse_report_summary(self, date_str: str, content: str) -> ReportSummary:
        """
        Parse report content to extract summary information.

        Args:
            date_str: Report date string (YYYYMMDD)
            content: Report markdown content

        Returns:
            ReportSummary object
        """
        # Default values
        market = "Unknown"
        total_stocks = 0
        buy_count = 0
        wait_count = 0
        avoid_count = 0

        # Parse market from content
        market_match = re.search(r"\*\*\uc2dc\uc7a5\*\*:\s*(.+)", content)
        if market_match:
            market = market_match.group(1).strip()

        # Parse stock count
        stock_count_match = re.search(
            r"\*\*\uc885\ubaa9 \uc218\*\*:\s*(\d+)",
            content
        )
        if stock_count_match:
            total_stocks = int(stock_count_match.group(1))

        # Count recommendations from table
        buy_count = len(re.findall(r"\*\*BUY\*\*", content))
        wait_count = len(re.findall(r"\*\*WAIT\*\*", content))
        avoid_count = len(re.findall(r"\*\*AVOID\*\*", content))

        return ReportSummary(
            date=date_str,
            market=market,
            total_stocks=total_stocks,
            buy_count=buy_count,
            wait_count=wait_count,
            avoid_count=avoid_count,
        )

    def get_report(self, date: str, market: str = None) -> Optional[ReportDetail]:
        """
        Get a specific analysis report by date.

        Args:
            date: Report date (YYYYMMDD format)
            market: Optional market filter (KOSPI, SP500, etc.)

        Returns:
            ReportDetail if found, None otherwise
        """
        report_path = DATA_ANALYSIS_DIR / f"report_{date}.md"

        if not report_path.exists():
            return None

        try:
            content = report_path.read_text(encoding="utf-8")

            # If market filter is specified, extract only that section
            if market:
                content = self._extract_market_section(content, market)

            # Try to get associated enriched data
            stocks = []
            enriched_path = DATA_ANALYSIS_DIR / f"enriched_{market.lower() if market else 'sp500'}_{date}.json"
            if enriched_path.exists():
                try:
                    with open(enriched_path, "r", encoding="utf-8") as f:
                        enriched_data = json.load(f)
                        stocks = enriched_data.get("stocks", [])
                except Exception as e:
                    logger.warning(f"Failed to load enriched data: {e}")

            return ReportDetail(
                date=date,
                market=market or "All",
                content=content,
                stocks=stocks,
            )
        except Exception as e:
            logger.error(f"Failed to read report {date}: {e}")
            return None

    def _extract_market_section(self, content: str, market: str) -> str:
        """
        Extract a specific market section from report content.

        Args:
            content: Full report content
            market: Market name to extract

        Returns:
            Extracted section or full content if not found
        """
        # Look for market-specific header patterns
        patterns = [
            rf"# {market} .*?(?=# [A-Z]|\Z)",
            rf"## {market} .*?(?=## [A-Z]|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return content

    def get_enriched_data(
        self,
        date: str,
        market: str = "sp500"
    ) -> Optional[Dict[str, Any]]:
        """
        Get enriched JSON data for a specific date and market.

        Args:
            date: Data date (YYYYMMDD format)
            market: Market name (sp500, kospi, etc.)

        Returns:
            Dict with enriched data if found, None otherwise
        """
        market_lower = market.lower()
        enriched_path = DATA_ANALYSIS_DIR / f"enriched_{market_lower}_{date}.json"

        if not enriched_path.exists():
            return None

        try:
            with open(enriched_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load enriched data for {date}/{market}: {e}")
            return None

    def list_enriched_files(self) -> List[Dict[str, str]]:
        """
        List all available enriched data files.

        Returns:
            List of dicts with date and market info
        """
        files = []

        if not DATA_ANALYSIS_DIR.exists():
            return files

        for json_file in DATA_ANALYSIS_DIR.glob("enriched_*.json"):
            # Parse filename: enriched_{market}_{date}.json
            match = re.match(
                r"enriched_([a-z0-9]+)_(\d{8})\.json",
                json_file.name
            )
            if match:
                files.append({
                    "market": match.group(1).upper(),
                    "date": match.group(2),
                    "file": json_file.name,
                })

        # Sort by date descending
        files.sort(key=lambda x: x["date"], reverse=True)

        return files

    def is_claude_available(self) -> bool:
        """Check if Claude API is available for analysis."""
        return self._claude_available


# Singleton instance
_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """
    Get or create the analysis service singleton.

    Returns:
        AnalysisService instance
    """
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
