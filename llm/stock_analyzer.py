"""
Integrated Stock Analyzer
통합 주식 분석기

Combines data enrichment and Claude analysis into a single pipeline.

Usage:
    from llm import StockAnalyzer

    analyzer = StockAnalyzer()

    # Analyze single stock
    result = analyzer.analyze("AAPL", current_price=175.50, ma_240=168.20)

    # Analyze with pre-fetched data
    result = analyzer.analyze_with_data(stock_profile)
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .claude_client import ClaudeAnalyzer, AnalysisResult
from .prompts import (
    format_valuation_prompt,
    format_entry_timing_prompt,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class StockProfile:
    """Complete stock profile for analysis"""
    ticker: str
    name: str
    current_price: float
    ma_240: float
    currency: str = "$"
    technical: Dict[str, Any] = field(default_factory=dict)
    fundamental: Dict[str, Any] = field(default_factory=dict)
    news: Dict[str, Any] = field(default_factory=dict)

    @property
    def distance_pct(self) -> float:
        """Distance from 240d MA as percentage"""
        if self.ma_240 and self.ma_240 > 0:
            return (self.current_price - self.ma_240) / self.ma_240 * 100
        return 0.0


@dataclass
class FullAnalysisResult:
    """Complete analysis result with all data"""
    ticker: str
    name: str
    current_price: float
    ma_240: float
    distance_pct: float

    # Claude analysis
    valuation_score: float
    risk_score: float
    entry_recommendation: str
    reasoning: str
    key_risks: List[str]
    catalysts: List[str]

    # Additional fields
    technical_view: str = "neutral"
    fundamental_view: str = "fair"
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None

    # Raw data for reference
    technical: Dict[str, Any] = field(default_factory=dict)
    fundamental: Dict[str, Any] = field(default_factory=dict)
    news: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'ticker': self.ticker,
            'name': self.name,
            'current_price': self.current_price,
            'ma_240': self.ma_240,
            'distance_pct': self.distance_pct,
            'valuation_score': self.valuation_score,
            'risk_score': self.risk_score,
            'entry_recommendation': self.entry_recommendation,
            'reasoning': self.reasoning,
            'key_risks': self.key_risks,
            'catalysts': self.catalysts,
            'technical_view': self.technical_view,
            'fundamental_view': self.fundamental_view,
            'target_price': self.target_price,
            'stop_loss_price': self.stop_loss_price,
            'technical': self.technical,
            'fundamental': self.fundamental,
            'analyzed_at': self.analyzed_at,
        }


class StockAnalyzer:
    """
    Integrated stock analyzer using data enrichment and Claude.

    Orchestrates the full analysis pipeline:
    1. Fetch OHLCV data (from cache)
    2. Enrich with technical indicators
    3. Enrich with fundamental data
    4. Enrich with news
    5. Analyze with Claude
    """

    def __init__(
        self,
        claude_model: str = None,
        max_tokens: int = 1500,
        use_cache: bool = True
    ):
        """
        Initialize stock analyzer.

        Args:
            claude_model: Model to use (None = auto-detect based on provider)
            max_tokens: Max tokens for AI response
            use_cache: Use OHLCV cache
        """
        self.claude = ClaudeAnalyzer(model=claude_model, max_tokens=max_tokens)
        self.use_cache = use_cache

        # Lazy load enrichers
        self._technical_enricher = None
        self._fundamental_enricher = None
        self._news_enricher = None
        self._cache = None

    @property
    def technical_enricher(self):
        if self._technical_enricher is None:
            from data_enrichment import TechnicalEnricher
            self._technical_enricher = TechnicalEnricher()
        return self._technical_enricher

    @property
    def fundamental_enricher(self):
        if self._fundamental_enricher is None:
            from data_enrichment import FundamentalEnricher
            self._fundamental_enricher = FundamentalEnricher()
        return self._fundamental_enricher

    @property
    def news_enricher(self):
        if self._news_enricher is None:
            from data_enrichment import NewsEnricher
            self._news_enricher = NewsEnricher(max_articles=10, days=7)
        return self._news_enricher

    @property
    def cache(self):
        if self._cache is None:
            from utils.data_cache import OHLCVCache
            self._cache = OHLCVCache()
        return self._cache

    def _get_currency(self, ticker: str) -> str:
        """Get currency symbol for ticker"""
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            return "₩"
        return "$"

    def enrich_stock(
        self,
        ticker: str,
        name: str = None,
        current_price: float = None,
        ma_240: float = None,
        days: int = 250
    ) -> StockProfile:
        """
        Enrich a stock with technical, fundamental, and news data.

        Args:
            ticker: Stock ticker
            name: Company name (fetched if not provided)
            current_price: Current price (fetched if not provided)
            ma_240: 240-day MA (calculated if not provided)
            days: Days of data to fetch

        Returns:
            StockProfile with all enriched data
        """
        # Get OHLCV data
        data = self.cache.get(ticker, days=days)
        if data is None or data.empty:
            raise ValueError(f"No data available for {ticker}")

        # Get current price and MA
        if current_price is None:
            current_price = float(data['close'].iloc[-1])

        if ma_240 is None and len(data) >= 240:
            ma_240 = float(data['close'].tail(240).mean())
        elif ma_240 is None:
            ma_240 = float(data['close'].mean())

        # Enrich in parallel
        technical = {}
        fundamental = {}
        news = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.technical_enricher.enrich, ticker, data): 'technical',
                executor.submit(self.fundamental_enricher.enrich, ticker): 'fundamental',
                executor.submit(self.news_enricher.enrich, ticker, name): 'news',
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    if key == 'technical':
                        technical = result
                    elif key == 'fundamental':
                        fundamental = result
                        # Get name from fundamental if not provided
                        if name is None:
                            name = fundamental.get('name', ticker)
                    else:
                        news = result
                except Exception as e:
                    logger.warning(f"Failed to enrich {key} for {ticker}: {e}")

        if name is None:
            name = ticker

        return StockProfile(
            ticker=ticker,
            name=name,
            current_price=current_price,
            ma_240=ma_240,
            currency=self._get_currency(ticker),
            technical=technical,
            fundamental=fundamental,
            news=news,
        )

    def analyze(
        self,
        ticker: str,
        name: str = None,
        current_price: float = None,
        ma_240: float = None,
        locale: str = None,
    ) -> FullAnalysisResult:
        """
        Analyze a single stock (fetches all data automatically).

        Args:
            ticker: Stock ticker
            name: Company name (optional)
            current_price: Current price (optional, fetched if not provided)
            ma_240: 240-day MA (optional, calculated if not provided)
            locale: Response language locale (e.g., "ko", "zh")

        Returns:
            FullAnalysisResult with complete analysis
        """
        # Enrich stock data
        profile = self.enrich_stock(ticker, name, current_price, ma_240)

        # Analyze with AI
        return self.analyze_with_profile(profile, locale=locale)

    def analyze_with_profile(self, profile: StockProfile, locale: str = None) -> FullAnalysisResult:
        """
        Analyze a stock using pre-enriched profile.

        Args:
            profile: StockProfile with all data
            locale: Response language locale (e.g., "ko", "zh")

        Returns:
            FullAnalysisResult
        """
        # Call AI for analysis
        result = self.claude.analyze_stock(
            ticker=profile.ticker,
            name=profile.name,
            current_price=profile.current_price,
            ma_240=profile.ma_240,
            technical=profile.technical,
            fundamental=profile.fundamental,
            news=profile.news,
            locale=locale,
        )

        return FullAnalysisResult(
            ticker=profile.ticker,
            name=profile.name,
            current_price=profile.current_price,
            ma_240=profile.ma_240,
            distance_pct=profile.distance_pct,
            valuation_score=result.valuation_score,
            risk_score=result.risk_score,
            entry_recommendation=result.entry_recommendation,
            reasoning=result.reasoning,
            key_risks=result.key_risks,
            catalysts=result.catalysts,
            technical_view=getattr(result, 'technical_view', 'neutral'),
            fundamental_view=getattr(result, 'fundamental_view', 'fair'),
            target_price=getattr(result, 'target_price', None),
            stop_loss_price=getattr(result, 'stop_loss_price', None),
            technical=profile.technical,
            fundamental=profile.fundamental,
            news=profile.news,
        )

    def analyze_batch(
        self,
        tickers: List[str],
        show_progress: bool = True
    ) -> List[FullAnalysisResult]:
        """
        Analyze multiple stocks.

        Args:
            tickers: List of stock tickers
            show_progress: Show progress output

        Returns:
            List of FullAnalysisResult
        """
        results = []
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            if show_progress:
                print(f"  Analyzing {ticker} ({i}/{total})...")

            try:
                result = self.analyze(ticker)
                results.append(result)

                if show_progress:
                    print(f"    → {result.entry_recommendation} "
                          f"(Valuation: {result.valuation_score}/10, "
                          f"Risk: {result.risk_score}/10)")

            except Exception as e:
                logger.error(f"Failed to analyze {ticker}: {e}")
                if show_progress:
                    print(f"    → Error: {e}")

        return results

    def get_recommendations(
        self,
        results: List[FullAnalysisResult],
        min_valuation: float = 6.0,
        max_risk: float = 7.0,
        action: str = "BUY"
    ) -> List[FullAnalysisResult]:
        """
        Filter results by criteria.

        Args:
            results: List of analysis results
            min_valuation: Minimum valuation score
            max_risk: Maximum risk score
            action: Filter by recommendation (BUY, WAIT, AVOID)

        Returns:
            Filtered and sorted list
        """
        filtered = [
            r for r in results
            if r.valuation_score >= min_valuation
            and r.risk_score <= max_risk
            and r.entry_recommendation == action
        ]

        # Sort by valuation score (highest first)
        return sorted(filtered, key=lambda x: x.valuation_score, reverse=True)
