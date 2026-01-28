"""
News Aggregator
다중 뉴스 소스 통합

Usage:
    from news.aggregator import NewsAggregator

    aggregator = NewsAggregator()
    news = aggregator.get_news("AAPL")
    sentiment = aggregator.get_sentiment("AAPL")
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import defaultdict

from .provider import (
    BaseNewsProvider, NewsProvider, NewsItem, NewsSentiment, Sentiment
)
from .finnhub import FinnhubProvider
from .marketaux import MarketauxProvider


class NewsAggregator:
    """다중 뉴스 소스 통합 클래스"""

    def __init__(
        self,
        finnhub_key: Optional[str] = None,
        marketaux_key: Optional[str] = None,
        enable_finnhub: bool = True,
        enable_marketaux: bool = True
    ):
        """
        Args:
            finnhub_key: Finnhub API 키
            marketaux_key: Marketaux API 키
            enable_finnhub: Finnhub 활성화
            enable_marketaux: Marketaux 활성화
        """
        self.logger = logging.getLogger(__name__)
        self._providers: List[BaseNewsProvider] = []

        if enable_finnhub:
            try:
                provider = FinnhubProvider(api_key=finnhub_key)
                if provider.is_configured():
                    self._providers.append(provider)
                    self.logger.info("Finnhub provider enabled")
            except ImportError:
                self.logger.warning("Finnhub provider not available")

        if enable_marketaux:
            try:
                provider = MarketauxProvider(api_key=marketaux_key)
                if provider.is_configured():
                    self._providers.append(provider)
                    self.logger.info("Marketaux provider enabled")
            except ImportError:
                self.logger.warning("Marketaux provider not available")

    def add_provider(self, provider: BaseNewsProvider) -> None:
        """커스텀 제공자 추가"""
        self._providers.append(provider)

    def get_providers(self) -> List[str]:
        """활성화된 제공자 목록"""
        return [p.name for p in self._providers]

    def get_news(
        self,
        ticker: str,
        limit: int = 20,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        deduplicate: bool = True
    ) -> List[NewsItem]:
        """
        종목 뉴스 통합 조회

        Args:
            ticker: 종목 코드
            limit: 최대 뉴스 수
            from_date: 시작 날짜
            to_date: 종료 날짜
            deduplicate: 중복 제거 여부

        Returns:
            뉴스 아이템 목록 (최신순)
        """
        if not self._providers:
            self.logger.warning("No news providers configured")
            return []

        all_news: List[NewsItem] = []

        # Fetch from all providers
        for provider in self._providers:
            try:
                news = provider.get_news(
                    ticker=ticker,
                    limit=limit,
                    from_date=from_date,
                    to_date=to_date
                )
                all_news.extend(news)
                self.logger.debug(f"Fetched {len(news)} news from {provider.name}")
            except Exception as e:
                self.logger.error(f"Error fetching from {provider.name}: {e}")

        # Deduplicate
        if deduplicate:
            all_news = self._deduplicate(all_news)

        # Sort by date (newest first)
        all_news.sort(key=lambda x: x.published_at, reverse=True)

        return all_news[:limit]

    def _deduplicate(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        중복 뉴스 제거

        제목 유사도 기반으로 중복 판단
        """
        if not news_items:
            return []

        seen_titles: Dict[str, NewsItem] = {}
        unique_news = []

        for item in news_items:
            # Normalize title for comparison
            normalized = self._normalize_title(item.title)

            # Check for similar titles
            is_duplicate = False
            for seen_title in seen_titles:
                if self._is_similar(normalized, seen_title):
                    # Keep the one with more info (sentiment score)
                    existing = seen_titles[seen_title]
                    if item.sentiment_score is not None and existing.sentiment_score is None:
                        seen_titles[seen_title] = item
                        unique_news = [n for n in unique_news if n != existing]
                        unique_news.append(item)
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles[normalized] = item
                unique_news.append(item)

        return unique_news

    def _normalize_title(self, title: str) -> str:
        """제목 정규화"""
        # Remove common prefixes, lowercase, remove punctuation
        title = title.lower()
        for prefix in ["breaking:", "update:", "exclusive:"]:
            title = title.replace(prefix, "")
        return "".join(c for c in title if c.isalnum() or c.isspace()).strip()

    def _is_similar(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
        """제목 유사도 체크 (간단한 Jaccard 유사도)"""
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union >= threshold

    def get_sentiment(self, ticker: str) -> Optional[NewsSentiment]:
        """
        종목 감성 분석 (통합)

        여러 제공자의 결과를 평균
        """
        news_items = self.get_news(ticker, limit=50, deduplicate=True)

        if not news_items:
            return None

        positive = 0
        negative = 0
        neutral = 0
        scores = []

        for item in news_items:
            if item.sentiment == Sentiment.POSITIVE:
                positive += 1
            elif item.sentiment == Sentiment.NEGATIVE:
                negative += 1
            else:
                neutral += 1

            if item.sentiment_score is not None:
                scores.append(item.sentiment_score)

        avg_score = sum(scores) / len(scores) if scores else 0

        return NewsSentiment(
            ticker=ticker,
            total_count=len(news_items),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            avg_sentiment_score=avg_score,
            latest_news=news_items[:5],
        )

    def get_multi_sentiment(self, tickers: List[str]) -> Dict[str, NewsSentiment]:
        """
        여러 종목 감성 분석

        Args:
            tickers: 종목 코드 목록

        Returns:
            {ticker: NewsSentiment} 딕셔너리
        """
        results = {}

        for ticker in tickers:
            sentiment = self.get_sentiment(ticker)
            if sentiment:
                results[ticker] = sentiment

        return results

    def summary(self, ticker: str) -> str:
        """종목 뉴스 요약"""
        sentiment = self.get_sentiment(ticker)

        if not sentiment:
            return f"No news found for {ticker}"

        lines = [
            f"=== {ticker} News Summary ===",
            f"Total: {sentiment.total_count} articles",
            f"Positive: {sentiment.positive_count}",
            f"Negative: {sentiment.negative_count}",
            f"Neutral: {sentiment.neutral_count}",
            f"Avg Sentiment: {sentiment.avg_sentiment_score:+.2f}",
            f"Overall: {sentiment.overall_sentiment.value.upper()}",
            "",
            "Latest Headlines:",
        ]

        for news in sentiment.latest_news[:3]:
            emoji = "📈" if news.is_positive else "📉" if news.is_negative else "📰"
            lines.append(f"  {emoji} {news.title[:60]}...")

        return "\n".join(lines)


# Convenience functions
def get_news(ticker: str, limit: int = 10) -> List[NewsItem]:
    """뉴스 조회 (편의 함수)"""
    aggregator = NewsAggregator()
    return aggregator.get_news(ticker, limit=limit)


def get_sentiment(ticker: str) -> Optional[NewsSentiment]:
    """감성 분석 (편의 함수)"""
    aggregator = NewsAggregator()
    return aggregator.get_sentiment(ticker)
